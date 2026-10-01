from __future__ import annotations

from copy import deepcopy
from typing import Any

from fastapi.testclient import TestClient
import pytest

from src.api.dependencies import (
    get_construction_repository,
    get_risk_authority_client,
    get_wave_repository,
)
from src.api.main import app
from src.api.routers.rebalance_runs import get_dpm_run_support_service
from src.core.rebalance_runs.service import DpmRunSupportService
from src.core.waves import (
    DpmRebalanceWave,
    DpmRebalanceWaveItem,
    DpmWaveAggregateMetrics,
    DpmWaveSourceRef,
    DpmWaveTrigger,
)
from src.infrastructure.construction import InMemoryConstructionRepository
from src.infrastructure.rebalance_runs import InMemoryDpmRunRepository
from src.infrastructure.waves import InMemoryDpmWaveRepository

TENANT_ID = "tenant-sg"
WAVE_ID = "dwv_async_simulation"
ITEM_ID = "dwi_async_simulation"
PORTFOLIO_ID = "PB_SG_GLOBAL_BAL_001"
BASE_PATH = "/api/v1/rebalance/waves"


def _rebalance_request(*, target_weight: str = "0.80") -> dict[str, object]:
    return {
        "portfolio_snapshot": {
            "portfolio_id": PORTFOLIO_ID,
            "base_currency": "SGD",
            "positions": [{"instrument_id": "EQ_1", "quantity": "100"}],
            "cash_balances": [{"currency": "SGD", "amount": "5000"}],
        },
        "market_data_snapshot": {
            "prices": [{"instrument_id": "EQ_1", "price": "100", "currency": "SGD"}],
            "fx_rates": [],
        },
        "model_portfolio": {"targets": [{"instrument_id": "EQ_1", "weight": target_weight}]},
        "shelf_entries": [{"instrument_id": "EQ_1", "status": "APPROVED"}],
        "options": {"target_method": "HEURISTIC"},
    }


def _source_checked_wave() -> DpmRebalanceWave:
    item = DpmRebalanceWaveItem(
        wave_item_id=ITEM_ID,
        portfolio_id=PORTFOLIO_ID,
        mandate_id="MANDATE_PB_SG_GLOBAL_BAL_001",
        model_portfolio_id="MODEL_PB_SG_GLOBAL_BAL_DPM",
        state="SOURCE_READY",
        reason_codes=["AFFECTED_PORTFOLIO_SOURCE_READY"],
        source_refs=[
            DpmWaveSourceRef(
                source_system="lotus-core",
                source_type="DPM_SOURCE_READINESS",
                source_id="source-readiness-001",
                source_version="v1",
                supportability_state="READY",
                content_hash="sha256:source-v1",
            )
        ],
    )
    return DpmRebalanceWave(
        wave_id=WAVE_ID,
        state="SOURCE_CHECKED",
        trigger=DpmWaveTrigger(
            trigger_type="EXPLICIT_PORTFOLIO_LIST",
            trigger_id="manual-async-simulation",
            rationale="Exercise durable asynchronous simulation.",
        ),
        as_of_date="2026-05-03",
        created_by="pm_001",
        correlation_id="corr-wave-async",
        items=[item],
        aggregate_metrics=DpmWaveAggregateMetrics(
            item_count=1,
            state_counts={"SOURCE_READY": 1},
            ready_item_count=1,
            blocked_item_count=0,
            review_required_item_count=0,
            source_degraded_item_count=0,
        ),
    )


def _client(
    repository: InMemoryDpmWaveRepository,
    construction_repository: InMemoryConstructionRepository | None = None,
) -> TestClient:
    app.dependency_overrides[get_wave_repository] = lambda: repository
    app.dependency_overrides[get_construction_repository] = lambda: (
        construction_repository or InMemoryConstructionRepository()
    )
    app.dependency_overrides[get_dpm_run_support_service] = lambda: DpmRunSupportService(
        repository=InMemoryDpmRunRepository()
    )
    app.dependency_overrides[get_risk_authority_client] = lambda: None
    app.openapi_schema = None
    return TestClient(app, headers={"X-Tenant-Id": TENANT_ID})


def _admission_payload(*, target_weight: str = "0.80") -> dict[str, object]:
    return {
        "actor_id": "pm_001",
        "max_concurrency": 4,
        "max_attempts": 3,
        "item_inputs": [
            {
                "wave_item_id": ITEM_ID,
                "stateless_input": _rebalance_request(target_weight=target_weight),
            }
        ],
    }


def _admit(client: TestClient, *, idempotency_key: str = "async-wave-001") -> Any:
    return client.post(
        f"{BASE_PATH}/{WAVE_ID}/simulation-operations",
        headers={"Idempotency-Key": idempotency_key},
        json=_admission_payload(),
    )


def teardown_function() -> None:
    app.dependency_overrides.clear()
    app.openapi_schema = None


def test_async_simulation_admission_is_durable_idempotent_and_conflict_safe() -> None:
    repository = InMemoryDpmWaveRepository()
    repository.save_wave(
        wave=_source_checked_wave(),
        idempotency_key=None,
        request_hash=None,
        tenant_id=TENANT_ID,
    )
    client = _client(repository)

    accepted = _admit(client)
    assert accepted.status_code == 202
    payload = accepted.json()
    assert payload["status"] == "PENDING"
    assert payload["counts"] == {
        "PENDING": 1,
        "RUNNING": 0,
        "SUCCEEDED": 0,
        "FAILED": 0,
        "CANCELLED": 0,
    }
    persisted_wave = repository.get_wave(wave_id=WAVE_ID, tenant_id=TENANT_ID)
    assert persisted_wave is not None
    assert persisted_wave.state == "SIMULATING"

    replay = _admit(client)
    assert replay.status_code == 202
    assert replay.json()["operation_id"] == payload["operation_id"]
    assert replay.json()["idempotent_replay"] is True

    conflict = client.post(
        f"{BASE_PATH}/{WAVE_ID}/simulation-operations",
        headers={"Idempotency-Key": "async-wave-001"},
        json=_admission_payload(target_weight="0.70"),
    )
    assert conflict.status_code == 409
    assert conflict.json()["detail"]["code"] == "DPM_WAVE_SIMULATION_IDEMPOTENCY_CONFLICT"


def test_async_simulation_worker_publishes_financial_result_and_reconciles_wave() -> None:
    repository = InMemoryDpmWaveRepository()
    construction_repository = InMemoryConstructionRepository()
    repository.save_wave(
        wave=_source_checked_wave(),
        idempotency_key=None,
        request_hash=None,
        tenant_id=TENANT_ID,
    )
    client = _client(repository, construction_repository)
    operation_id = _admit(client).json()["operation_id"]

    worked = client.post(
        f"{BASE_PATH}/simulation-operations/{operation_id}/work",
        json={"worker_id": "worker-01", "max_items": 4, "lease_seconds": 30},
    )

    assert worked.status_code == 200
    assert worked.json()["claimed_count"] == 1
    assert worked.json()["completed_count"] == 1
    assert worked.json()["failed_count"] == 0
    assert worked.json()["operation"]["status"] == "SUCCEEDED"
    results = client.get(f"{BASE_PATH}/simulation-operations/{operation_id}/results")
    assert results.status_code == 200
    assert results.json()["items"][0]["status"] == "SUCCEEDED"
    assert results.json()["items"][0]["item_state"] == "SIMULATED"
    assert results.json()["items"][0]["alternative_set_id"] is not None
    persisted_wave = repository.get_wave(wave_id=WAVE_ID, tenant_id=TENANT_ID)
    assert persisted_wave is not None
    assert persisted_wave.state == "SIMULATED"
    assert persisted_wave.items[0].alternative_set_id is not None
    assert (
        len(construction_repository.list_alternative_sets(portfolio_id=PORTFOLIO_ID, limit=10)) == 1
    )


@pytest.mark.parametrize(
    "item_input",
    [
        {"wave_item_id": ITEM_ID, "portfolio_id": "FOREIGN_PORTFOLIO"},
        {"wave_item_id": "unknown-wave-item", "portfolio_id": PORTFOLIO_ID},
    ],
)
def test_async_simulation_rejects_conflicting_selectors_without_construction_artifact(
    item_input: dict[str, str],
) -> None:
    repository = InMemoryDpmWaveRepository()
    construction_repository = InMemoryConstructionRepository()
    repository.save_wave(
        wave=_source_checked_wave(), idempotency_key=None, request_hash=None, tenant_id=TENANT_ID
    )
    client = _client(repository, construction_repository)
    payload = _admission_payload()
    payload["item_inputs"][0].update(item_input)  # type: ignore[index]

    refused = client.post(
        f"{BASE_PATH}/{WAVE_ID}/simulation-operations",
        headers={"Idempotency-Key": f"selector-{item_input['wave_item_id']}"},
        json=payload,
    )

    assert refused.status_code == 422
    assert refused.json()["detail"]["code"] in {
        "DPM_WAVE_SIMULATION_INPUT_IDENTITY_CONFLICT",
        "DPM_WAVE_SIMULATION_INPUT_ITEM_NOT_FOUND",
    }
    assert repository.get_wave(wave_id=WAVE_ID, tenant_id=TENANT_ID).state == "SOURCE_CHECKED"  # type: ignore[union-attr]
    assert construction_repository.list_alternative_sets(portfolio_id=PORTFOLIO_ID, limit=10) == []
    assert (
        construction_repository.list_alternative_sets(portfolio_id="FOREIGN_PORTFOLIO", limit=10)
        == []
    )


def test_simulation_rejects_foreign_nested_portfolio_before_async_or_sync_execution() -> None:
    for path, headers in [
        (f"{BASE_PATH}/{WAVE_ID}/simulation-operations", {"Idempotency-Key": "foreign-async"}),
        (f"{BASE_PATH}/{WAVE_ID}/simulate", {}),
    ]:
        repository = InMemoryDpmWaveRepository()
        construction_repository = InMemoryConstructionRepository()
        repository.save_wave(
            wave=_source_checked_wave(),
            idempotency_key=None,
            request_hash=None,
            tenant_id=TENANT_ID,
        )
        client = _client(repository, construction_repository)
        payload = _admission_payload()
        payload["item_inputs"][0]["stateless_input"]["portfolio_snapshot"]["portfolio_id"] = (  # type: ignore[index]
            "FOREIGN_PORTFOLIO"
        )

        refused = client.post(path, headers=headers, json=payload)

        assert refused.status_code == 422
        assert refused.json()["detail"]["code"] == "DPM_WAVE_SIMULATION_INPUT_IDENTITY_CONFLICT"
        assert repository.get_wave(wave_id=WAVE_ID, tenant_id=TENANT_ID).state == "SOURCE_CHECKED"  # type: ignore[union-attr]
        assert (
            construction_repository.list_alternative_sets(
                portfolio_id="FOREIGN_PORTFOLIO", limit=10
            )
            == []
        )


def test_simulation_operation_openapi_documents_observed_not_found_and_conflict_errors() -> None:
    repository = InMemoryDpmWaveRepository()
    repository.save_wave(
        wave=_source_checked_wave(), idempotency_key=None, request_hash=None, tenant_id=TENANT_ID
    )
    client = _client(repository)
    schema = client.app.openapi()
    paths = schema["paths"]
    admission = paths[f"{BASE_PATH}/{{wave_id}}/simulation-operations"]["post"]["responses"]
    assert {"404", "409"}.issubset(admission)
    assert admission["409"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "/DpmWaveOperationProblemResponse"
    )
    for suffix, method in [
        ("{operation_id}", "get"),
        ("{operation_id}/results", "get"),
        ("{operation_id}/work", "post"),
        ("{operation_id}/retry", "post"),
        ("{operation_id}/cancel", "post"),
    ]:
        response = paths[f"{BASE_PATH}/simulation-operations/{suffix}"][method]["responses"]
        assert "404" in response
        assert response["404"]["content"]["application/json"]["schema"]["$ref"].endswith(
            "/DpmWaveOperationProblemResponse"
        )


def test_async_simulation_fails_closed_when_source_identity_changes_after_admission() -> None:
    repository = InMemoryDpmWaveRepository()
    repository.save_wave(
        wave=_source_checked_wave(),
        idempotency_key=None,
        request_hash=None,
        tenant_id=TENANT_ID,
    )
    client = _client(repository)
    operation_id = _admit(client).json()["operation_id"]
    admitted_wave = repository.get_wave(wave_id=WAVE_ID, tenant_id=TENANT_ID)
    assert admitted_wave is not None
    changed_item = admitted_wave.items[0].model_copy(deep=True)
    changed_item.source_refs = deepcopy(changed_item.source_refs)
    changed_item.source_refs[0].content_hash = "sha256:source-v2"
    changed_wave = admitted_wave.model_copy(
        update={"items": [changed_item], "version": admitted_wave.version + 1}, deep=True
    )
    repository.update_wave(
        wave=changed_wave,
        expected_version=admitted_wave.version,
        tenant_id=TENANT_ID,
    )

    worked = client.post(
        f"{BASE_PATH}/simulation-operations/{operation_id}/work",
        json={"worker_id": "worker-01", "max_items": 1, "lease_seconds": 30},
    )

    assert worked.status_code == 200
    assert worked.json()["failed_count"] == 1
    results = client.get(f"{BASE_PATH}/simulation-operations/{operation_id}/results").json()
    assert results["items"][0]["status"] == "FAILED"
    assert results["items"][0]["retryable"] is False
    assert results["items"][0]["error_code"] == ("DPM_WAVE_SIMULATION_SOURCE_REVISION_CONFLICT")
    persisted_wave = repository.get_wave(wave_id=WAVE_ID, tenant_id=TENANT_ID)
    assert persisted_wave is not None
    assert persisted_wave.state == "SIMULATION_FAILED"


def test_async_simulation_operation_is_tenant_isolated_and_cancellable() -> None:
    repository = InMemoryDpmWaveRepository()
    repository.save_wave(
        wave=_source_checked_wave(),
        idempotency_key=None,
        request_hash=None,
        tenant_id=TENANT_ID,
    )
    client = _client(repository)
    operation_id = _admit(client).json()["operation_id"]

    hidden = client.get(
        f"{BASE_PATH}/simulation-operations/{operation_id}",
        headers={"X-Tenant-Id": "tenant-other"},
    )
    assert hidden.status_code == 404

    cancelled = client.post(
        f"{BASE_PATH}/simulation-operations/{operation_id}/cancel",
        json={"reason_code": "OPERATOR_CANCELLED"},
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "CANCELLED"
    assert cancelled.json()["counts"]["CANCELLED"] == 1
    persisted_wave = repository.get_wave(wave_id=WAVE_ID, tenant_id=TENANT_ID)
    assert persisted_wave is not None
    assert persisted_wave.state == "SIMULATION_FAILED"


def test_async_simulation_rejects_non_executable_wave_before_admission() -> None:
    repository = InMemoryDpmWaveRepository()
    wave = _source_checked_wave().model_copy(update={"state": "CREATED"})
    repository.save_wave(wave=wave, idempotency_key=None, request_hash=None, tenant_id=TENANT_ID)
    client = _client(repository)

    response = _admit(client)

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "DPM_WAVE_SIMULATION_INVALID_STATE"


def test_async_simulation_operation_routes_fail_closed_for_unknown_or_wrong_tenant_operation() -> (
    None
):
    repository = InMemoryDpmWaveRepository()
    repository.save_wave(
        wave=_source_checked_wave(),
        idempotency_key=None,
        request_hash=None,
        tenant_id=TENANT_ID,
    )
    client = _client(repository)
    unknown = "wso_missing"

    assert client.get(f"{BASE_PATH}/simulation-operations/{unknown}").status_code == 404
    assert client.get(f"{BASE_PATH}/simulation-operations/{unknown}/results").status_code == 404
    assert (
        client.post(
            f"{BASE_PATH}/simulation-operations/{unknown}/work",
            json={"worker_id": "worker-01", "max_items": 1, "lease_seconds": 30},
        ).status_code
        == 404
    )
    assert (
        client.post(f"{BASE_PATH}/simulation-operations/{unknown}/retry", json={}).status_code
        == 404
    )
    assert (
        client.post(
            f"{BASE_PATH}/simulation-operations/{unknown}/cancel",
            json={"reason_code": "OPERATOR_CANCELLED"},
        ).status_code
        == 404
    )


def test_async_simulation_results_and_retry_are_safe_before_any_failed_work() -> None:
    repository = InMemoryDpmWaveRepository()
    repository.save_wave(
        wave=_source_checked_wave(),
        idempotency_key=None,
        request_hash=None,
        tenant_id=TENANT_ID,
    )
    client = _client(repository)
    operation_id = _admit(client).json()["operation_id"]

    results = client.get(
        f"{BASE_PATH}/simulation-operations/{operation_id}/results?limit=1&offset=0"
    )
    assert results.status_code == 200
    assert results.json()["total_count"] == 1
    assert results.json()["next_offset"] is None

    retry = client.post(f"{BASE_PATH}/simulation-operations/{operation_id}/retry", json={})
    assert retry.status_code == 200
    assert retry.json()["status"] == "PENDING"
