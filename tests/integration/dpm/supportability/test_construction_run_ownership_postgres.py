"""Registered construction API proof of durable tenant-owned run records."""

from __future__ import annotations

import uuid
from contextlib import closing
from decimal import Decimal

from fastapi.testclient import TestClient

from src.api.dependencies import get_construction_repository
from src.api.main import app
from src.api.routers.rebalance_runs import get_dpm_run_support_service
from src.core.rebalance_runs.service import DpmRunSupportService
from src.infrastructure.construction.postgres import PostgresConstructionRepository
from src.infrastructure.rebalance_runs.postgres import PostgresDpmRunRepository
from tests.integration.dpm.postgres_prerequisite import postgres_dsn_or_skip
from tests.shared.factories import valid_api_payload


def test_registered_construction_run_owner_survives_repository_reconstruction() -> None:
    dsn = postgres_dsn_or_skip("construction-run tenant ownership")
    construction_repository = PostgresConstructionRepository(dsn=dsn)
    run_repository = PostgresDpmRunRepository(dsn=dsn)
    original_overrides = dict(app.dependency_overrides)
    app.dependency_overrides[get_construction_repository] = lambda: construction_repository
    app.dependency_overrides[get_dpm_run_support_service] = lambda: DpmRunSupportService(
        repository=run_repository
    )
    run_ids: set[str] = set()
    cleanup_run_ids: set[str] = set()
    alternative_set_ids: set[str] = set()
    nonce = uuid.uuid4().hex
    headers = {
        "Idempotency-Key": f"construction-owner-{nonce}",
        "X-Tenant-Id": "tenant-construction-a",
        "X-Correlation-Id": f"corr-construction-{nonce}",
    }
    payload = valid_api_payload()
    payload["portfolio_snapshot"]["positions"] = [{"instrument_id": "EQ_1", "quantity": "100"}]
    payload["portfolio_snapshot"]["cash_balances"] = [{"currency": "SGD", "amount": "5000.00"}]
    payload["model_portfolio"]["targets"][0]["weight"] = "0.80"
    request = {
        "input_mode": "stateless",
        "stateless_input": payload,
        "methods": ["DO_NOTHING_BASELINE", "HEURISTIC_EXPLAINABLE", "MIN_TURNOVER"],
    }
    try:
        with TestClient(app) as client:
            created = client.post(
                "/api/v1/construction/alternative-sets/generate", json=request, headers=headers
            )
            assert created.status_code == 200
            alternative_set_id = created.json()["alternative_set_id"]
            alternative_set_ids.add(alternative_set_id)
            alternatives = {
                alternative["method"]: alternative for alternative in created.json()["alternatives"]
            }
            baseline = alternatives["DO_NOTHING_BASELINE"]
            heuristic = alternatives["HEURISTIC_EXPLAINABLE"]
            assert baseline["rebalance_run_id"] is None
            assert baseline["evaluation_context"] == {
                "rebalance_run_id": heuristic["rebalance_run_id"],
                "state_basis": "BEFORE",
            }
            assert baseline["intent_ids"] == []
            assert baseline["diagnostics"]["proposed_changes"] == []
            assert Decimal(baseline["comparison_metrics"]["cash_weight_after"]) == Decimal("0.3333")
            assert baseline["comparison_metrics"]["trade_count"] == 0
            assert heuristic["diagnostics"]["proposed_changes"][0]["action"] == "BUY"
            assert Decimal(heuristic["diagnostics"]["proposed_changes"][0]["quantity"]) == Decimal(
                "20"
            )
            run_ids = {
                alternative["rebalance_run_id"]
                for alternative in created.json()["alternatives"]
                if alternative["rebalance_run_id"] is not None
            }
            cleanup_run_ids.update(run_ids)
            assert len(run_ids) == 2
            for run_id in run_ids:
                assert (
                    client.get(
                        f"/api/v1/rebalance/runs/{run_id}",
                        headers={"X-Tenant-Id": "tenant-construction-a"},
                    ).status_code
                    == 200
                )
                assert (
                    client.get(
                        f"/api/v1/rebalance/runs/{run_id}",
                        headers={"X-Tenant-Id": "tenant-construction-b"},
                    ).status_code
                    == 404
                )
            assert (
                client.post(
                    "/api/v1/construction/alternative-sets/generate", json=request, headers=headers
                ).json()
                == created.json()
            )
            assert (
                client.get(
                    f"/api/v1/construction/alternative-sets/{alternative_set_id}",
                    headers={"X-Tenant-Id": "tenant-construction-b"},
                ).status_code
                == 404
            )
            selection_request = {
                "alternative_id": created.json()["alternatives"][0]["alternative_id"],
                "actor_id": "pm-construction-owner-proof",
                "reason_code": "TENANT_FENCE_PROOF",
            }
            assert (
                client.post(
                    f"/api/v1/construction/alternative-sets/{alternative_set_id}/selections",
                    json=selection_request,
                    headers={"X-Tenant-Id": "tenant-construction-b"},
                ).status_code
                == 404
            )
            selected = client.post(
                f"/api/v1/construction/alternative-sets/{alternative_set_id}/selections",
                json=selection_request,
                headers={"X-Tenant-Id": "tenant-construction-a"},
            )
            assert selected.status_code == 200
            assert selected.json()["tenant_id"] == "tenant-construction-a"

            foreign_created = client.post(
                "/api/v1/construction/alternative-sets/generate",
                json=request,
                headers={**headers, "X-Tenant-Id": "tenant-construction-b"},
            )
            assert foreign_created.status_code == 200
            assert foreign_created.json()["alternative_set_id"] != alternative_set_id
            assert foreign_created.json()["tenant_id"] == "tenant-construction-b"
            alternative_set_ids.add(foreign_created.json()["alternative_set_id"])
            cleanup_run_ids.update(
                alternative["rebalance_run_id"]
                for alternative in foreign_created.json()["alternatives"]
                if alternative["rebalance_run_id"] is not None
            )

        restarted_repository = PostgresDpmRunRepository(dsn=dsn)
        restarted_construction_repository = PostgresConstructionRepository(dsn=dsn)
        app.dependency_overrides[get_construction_repository] = lambda: (
            restarted_construction_repository
        )
        app.dependency_overrides[get_dpm_run_support_service] = lambda: DpmRunSupportService(
            repository=restarted_repository
        )
        with TestClient(app) as client:
            retained = client.get(
                f"/api/v1/construction/alternative-sets/{alternative_set_id}",
                headers={"X-Tenant-Id": "tenant-construction-a"},
            )
            assert retained.json() == created.json()
            assert (
                client.post(
                    "/api/v1/construction/alternative-sets/generate", json=request, headers=headers
                ).json()
                == created.json()
            )
            retained_selection = restarted_construction_repository.get_selection(
                alternative_set_id=alternative_set_id, tenant_id="tenant-construction-a"
            )
            assert retained_selection.alternative_id == baseline["alternative_id"]
            assert (
                client.get(
                    f"/api/v1/construction/alternative-sets/{alternative_set_id}",
                    headers={"X-Tenant-Id": "tenant-construction-a"},
                ).status_code
                == 200
            )
            assert (
                client.get(
                    f"/api/v1/construction/alternative-sets/{alternative_set_id}",
                    headers={"X-Tenant-Id": "tenant-construction-b"},
                ).status_code
                == 404
            )
            for run_id in run_ids:
                assert (
                    client.get(
                        f"/api/v1/rebalance/runs/{run_id}",
                        headers={"X-Tenant-Id": "tenant-construction-a"},
                    ).status_code
                    == 200
                )
                assert (
                    client.get(
                        f"/api/v1/rebalance/runs/{run_id}",
                        headers={"X-Tenant-Id": "tenant-construction-b"},
                    ).status_code
                    == 404
                )
        with closing(restarted_repository._connect()) as connection:
            rows = [
                connection.execute(
                    "SELECT tenant_id, result_json FROM dpm_runs WHERE rebalance_run_id = %s",
                    (run_id,),
                ).fetchone()
                for run_id in run_ids
            ]
            assert all(
                row is not None and row["tenant_id"] == "tenant-construction-a" for row in rows
            )
            assert all(
                connection.execute(
                    "SELECT COUNT(*) FROM dpm_lineage_edges "
                    "WHERE target_entity_id = %s AND tenant_id = %s",
                    (run_id, "tenant-construction-a"),
                ).fetchone()["count"]
                >= 1
                for run_id in run_ids
            )
            assert all(
                restarted_repository.get_run(rebalance_run_id=run_id).tenant_id
                == "tenant-construction-a"
                for run_id in run_ids
            )
            run = restarted_repository.get_run(rebalance_run_id=next(iter(run_ids)))
            assert Decimal(run.result_json["before"]["total_value"]["amount"]) == Decimal("15000")
    finally:
        app.dependency_overrides = original_overrides
        with closing(run_repository._connect()) as connection:
            for run_id in cleanup_run_ids:
                connection.execute(
                    "DELETE FROM dpm_lineage_edges WHERE target_entity_id = %s", (run_id,)
                )
                connection.execute(
                    "DELETE FROM dpm_run_artifacts WHERE rebalance_run_id = %s", (run_id,)
                )
                connection.execute("DELETE FROM dpm_runs WHERE rebalance_run_id = %s", (run_id,))
            connection.commit()
        if alternative_set_ids:
            with closing(construction_repository._connect()) as connection:
                for alternative_set_id in alternative_set_ids:
                    connection.execute(
                        "DELETE FROM dpm_construction_alternative_selections "
                        "WHERE alternative_set_id = %s",
                        (alternative_set_id,),
                    )
                    connection.execute(
                        "DELETE FROM dpm_construction_alternative_sets "
                        "WHERE alternative_set_id = %s",
                        (alternative_set_id,),
                    )
                connection.commit()
