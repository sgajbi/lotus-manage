"""Registered health HTTP and native PostgreSQL restart proof for turnover usage."""

from __future__ import annotations

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

TENANT = "tenant-turnover-health-postgres"
AS_OF = date(2026, 5, 3)


def _health_input(mandate_id: str, used: Decimal | None) -> DpmMandateHealthInput:
    twin = DpmMandateDigitalTwin(
        mandate_id=mandate_id,
        portfolio_id=f"pf-{mandate_id}",
        mandate_version="turnover-policy-1",
        as_of_date=AS_OF,
        base_currency="SGD",
        reference_currency="SGD",
        risk_profile="BALANCED",
        investment_objective="LONG_TERM_TOTAL_RETURN",
        time_horizon="LONG_TERM",
        model_portfolio_id="model-turnover-health",
        constraints=DpmMandateConstraintSet(
            cash_band_min_weight=Decimal("0.02"),
            cash_band_max_weight=Decimal("0.10"),
            turnover_budget=Decimal("0.15"),
            turnover_budget_period_start=date(2026, 1, 1),
        ),
        review_policy=DpmMandateReviewPolicy(next_review_due_date=date(2026, 6, 30)),
    )
    return DpmMandateHealthInput(
        twin=twin,
        current_weights={"EQ_1": Decimal("0.6")},
        target_weights={"EQ_1": Decimal("0.6")},
        cash_weight=Decimal("0.05"),
        turnover_budget_used=used,
        turnover_budget_used_period_start=date(2026, 1, 1),
        turnover_budget_used_as_of_date=AS_OF,
        turnover_budget_usage_source_ref="caller:turnover-ledger:2026-05-03",
    )


def test_turnover_missing_and_excess_are_durable_and_not_release_ready() -> None:
    dsn = postgres_dsn_or_skip("turnover-budget mandate-health PostgreSQL HTTP proof")
    mandate_id = f"mandate-turnover-{uuid.uuid4().hex}"
    repository = PostgresDpmMandateRepository(dsn=dsn)
    prior_overrides = dict(app.dependency_overrides)
    app.dependency_overrides[get_mandate_repository] = lambda: repository
    route = f"/api/v1/mandates/{mandate_id}/health/recalculate?tenant_id={TENANT}"
    read_route = f"/api/v1/mandates/{mandate_id}/health?tenant_id={TENANT}"
    try:
        with TestClient(app) as client:
            measured_zero = client.post(
                route, json=_health_input(mandate_id, Decimal("0")).model_dump(mode="json")
            )
            missing = client.post(
                route, json=_health_input(mandate_id, None).model_dump(mode="json")
            )
            exceeded = client.post(
                route, json=_health_input(mandate_id, Decimal("0.1501")).model_dump(mode="json")
            )
            assert [response.status_code for response in (measured_zero, missing, exceeded)] == [
                200,
                200,
                200,
            ]
            assert [
                response.json()["health_state"] for response in (measured_zero, missing, exceeded)
            ] == ["READY", "PENDING_REVIEW", "BLOCKED"]
            assert (
                client.get(
                    f"/api/v1/mandates/{mandate_id}/health?tenant_id=foreign-turnover-health"
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
                    **_health_input(mandate_id, Decimal("0.1501")).model_dump(mode="json"),
                    "turnover_budget_used": "NaN",
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
        assert score["reason_code"] == "TURNOVER_BUDGET_EXCEEDED"
        turnover = score["budget_assessments"][1]
        assert turnover["measured_value"] == "0.1501"
        assert turnover["threshold_value"] == "0.15"
        assert turnover["remaining_value"] == "-0.0001"
        assert turnover["basis"] == "DECLARED_PERIOD_MATCHED"
        assert turnover["usage_source_ref"] == "caller:turnover-ledger:2026-05-03"
        exceptions, _ = restarted.list_monitoring_exceptions(
            monitoring_run_id=None,
            mandate_id=mandate_id,
            portfolio_id=None,
            state=None,
            limit=20,
            cursor=None,
            tenant_id=TENANT,
        )
        finding = next(
            item for item in exceptions if item.reason_code == "TURNOVER_BUDGET_EXCEEDED"
        )
        assert finding.budget_assessment.remaining_value == Decimal("-0.0001")
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
