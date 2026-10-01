"""Registered health API and native PostgreSQL restart proof for tax-budget evidence."""

from __future__ import annotations

import json
import uuid
from contextlib import closing
from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient

from src.api.dependencies import get_mandate_repository
from src.api.main import app
from src.core.mandates import (
    DpmMandateConstraintSet,
    DpmMandateDigitalTwin,
    DpmMandateHealthInput,
    DpmMandateReviewPolicy,
)
from src.infrastructure.mandates.postgres import PostgresDpmMandateRepository
from tests.integration.dpm.postgres_prerequisite import postgres_dsn_or_skip

TENANT = "tenant-tax-health-postgres"
AS_OF = date(2026, 5, 3)


def _health_input(mandate_id: str, used: Decimal) -> DpmMandateHealthInput:
    twin = DpmMandateDigitalTwin(
        mandate_id=mandate_id,
        portfolio_id=f"pf-{mandate_id}",
        mandate_version="tax-policy-1",
        as_of_date=AS_OF,
        base_currency="SGD",
        reference_currency="SGD",
        risk_profile="BALANCED",
        investment_objective="LONG_TERM_TOTAL_RETURN",
        time_horizon="LONG_TERM",
        model_portfolio_id="model-tax-health",
        constraints=DpmMandateConstraintSet(
            cash_band_min_weight=Decimal("0.02"),
            cash_band_max_weight=Decimal("0.10"),
            turnover_budget=Decimal("0.15"),
            tax_budget_base=Decimal("1000"),
            tax_budget_period_start=date(2026, 1, 1),
        ),
        review_policy=DpmMandateReviewPolicy(next_review_due_date=date(2026, 6, 30)),
    )
    return DpmMandateHealthInput(
        twin=twin,
        current_weights={"EQ_1": Decimal("0.6")},
        target_weights={"EQ_1": Decimal("0.6")},
        cash_weight=Decimal("0.05"),
        turnover_budget_used=Decimal("0.13"),
        tax_budget_used_base=used,
        tax_budget_used_currency="SGD",
        tax_budget_used_period_start=date(2026, 1, 1),
        tax_budget_used_as_of_date=AS_OF,
        tax_budget_usage_source_ref="caller:realized-gain-ledger:2026-05-03",
    )


def test_registered_tax_health_survives_postgres_restart_and_preserves_both_findings() -> None:
    dsn = postgres_dsn_or_skip("tax-budget mandate-health PostgreSQL HTTP proof")
    mandate_id = f"mandate-tax-{uuid.uuid4().hex}"
    repository = PostgresDpmMandateRepository(dsn=dsn)
    prior_overrides = dict(app.dependency_overrides)
    app.dependency_overrides[get_mandate_repository] = lambda: repository
    route = f"/api/v1/mandates/{mandate_id}/health/recalculate?tenant_id={TENANT}"
    read_route = f"/api/v1/mandates/{mandate_id}/health?tenant_id={TENANT}"
    try:
        with TestClient(app) as client:
            accepted = client.post(
                route, json=_health_input(mandate_id, Decimal("999.99")).model_dump(mode="json")
            )
            exceeded = client.post(
                route, json=_health_input(mandate_id, Decimal("1000.01")).model_dump(mode="json")
            )
            assert accepted.status_code == exceeded.status_code == 200
            assert accepted.json()["health_state"] == "PENDING_REVIEW"
            assert exceeded.json()["health_state"] == "BLOCKED"
            assert exceeded.json()["health_score"] == 94
            assert (
                client.get(
                    f"/api/v1/mandates/{mandate_id}/health?tenant_id=foreign-tax-health"
                ).status_code
                == 404
            )
        restarted = PostgresDpmMandateRepository(dsn=dsn)
        app.dependency_overrides[get_mandate_repository] = lambda: restarted
        with TestClient(app) as client:
            persisted = client.get(read_route)
            invalid = client.post(
                route,
                json={
                    **_health_input(mandate_id, Decimal("1000.01")).model_dump(mode="json"),
                    "tax_budget_used_base": "NaN",
                },
            )
            after_invalid = client.get(read_route)
        assert persisted.status_code == after_invalid.status_code == 200
        assert persisted.json() == exceeded.json() == after_invalid.json()
        assert invalid.status_code == 422
        score = next(
            item
            for item in persisted.json()["dimension_scores"]
            if item["dimension"] == "TAX_TURNOVER"
        )
        assert score["reason_code"] == "TAX_BUDGET_EXCEEDED"
        assert score["budget_assessments"][0]["remaining_value"] == "-0.01"
        assert score["budget_assessments"][0]["basis"] == "DECLARED_PERIOD_MATCHED"
        assert score["budget_assessments"][1]["reason_code"] == "TURNOVER_BUDGET_NEAR_LIMIT"
        exceptions, _ = restarted.list_monitoring_exceptions(
            monitoring_run_id=None,
            mandate_id=mandate_id,
            portfolio_id=None,
            state=None,
            limit=20,
            cursor=None,
            tenant_id=TENANT,
        )
        assert {item.reason_code for item in exceptions} == {
            "TAX_BUDGET_EXCEEDED",
            "TURNOVER_BUDGET_NEAR_LIMIT",
        }
        by_reason = {item.reason_code: item for item in exceptions}
        assert by_reason["TAX_BUDGET_EXCEEDED"].measured_value == "1000.01"
        assert by_reason["TAX_BUDGET_EXCEEDED"].threshold_value == "1000"
        assert by_reason["TAX_BUDGET_EXCEEDED"].budget_assessment.remaining_value == (
            Decimal("-0.01")
        )
        assert by_reason["TAX_BUDGET_EXCEEDED"].budget_assessment.usage_source_ref == (
            "caller:realized-gain-ledger:2026-05-03"
        )
        assert by_reason["TURNOVER_BUDGET_NEAR_LIMIT"].measured_value == "0.13"
        assert by_reason["TURNOVER_BUDGET_NEAR_LIMIT"].threshold_value == "0.15"
        with closing(restarted._connect()) as connection:
            row = connection.execute(
                "SELECT tenant_id, payload_json FROM dpm_mandate_health_snapshots "
                "WHERE mandate_id = %s",
                (mandate_id,),
            ).fetchone()
        assert row["tenant_id"] == TENANT
        assert (
            json.loads(row["payload_json"])["health_snapshot_id"]
            == (persisted.json()["health_snapshot_id"])
        )
    finally:
        app.dependency_overrides = prior_overrides
        with closing(repository._connect()) as connection:
            for table in (
                "dpm_monitoring_exceptions",
                "dpm_mandate_health_snapshots",
                "dpm_mandate_snapshots",
            ):
                connection.execute(f"DELETE FROM {table} WHERE mandate_id = %s", (mandate_id,))
            connection.commit()
