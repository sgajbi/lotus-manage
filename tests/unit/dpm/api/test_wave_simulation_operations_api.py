from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
import json

from fastapi import Request

from fastapi.testclient import TestClient
import pytest

from src.api.dependencies import (
    get_construction_repository,
    get_risk_authority_client,
    get_wave_repository,
    get_operation_risk_authority_client,
)
from src.api.main import app
from src.api.routers.rebalance_runs import get_dpm_run_support_service
from src.api.services import wave_construction_selection, wave_simulation_operations
from src.api.services.wave_errors import DpmWaveValidationError
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
from src.core.integration_ports import LotusRiskAuthorityUnavailableError

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


def _active_no_buy_authority_context() -> dict[str, object]:
    return {
        "client_restriction_required": True,
        "client_restriction_context": {
            "supportability_status": "READY",
            "source_system": "lotus-core",
            "source_product_name": "ClientRestrictionProfile",
            "source_product_version": "v1",
            "source_id": "restriction-1",
            "content_hash": "sha256:restriction-1",
            "portfolio_id": PORTFOLIO_ID,
            "client_id": "client-1",
            "mandate_id": "MANDATE_PB_SG_GLOBAL_BAL_001",
            "as_of_date": "2026-05-03",
            "restriction_count": 1,
            "restrictions": [
                {
                    "restriction_scope": "instrument",
                    "restriction_code": "NO_EQ_BUY",
                    "restriction_status": "active",
                    "restriction_source": "client_mandate",
                    "applies_to_buy": True,
                    "applies_to_sell": False,
                    "instrument_ids": ["EQ_1"],
                    "effective_from": "2026-01-01",
                    "restriction_version": 1,
                }
            ],
        },
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


def test_async_risk_context_is_admitted_immutable_and_not_replaced_by_worker(monkeypatch):
    for name, value in {
        "ENTERPRISE_ENFORCE_AUTHZ": "true",
        "ENTERPRISE_POLICY_VERSION": "synthetic-policy-v1",
        "PRINCIPAL_RESOLUTION_POSTURE": "header-trust",
        "ENVIRONMENT": "local",
        "APP_PERSISTENCE_PROFILE": "LOCAL",
        "DPM_RISK_CONSUMER_SERVICE_IDENTITY": "manage-local-consumer",
        "DPM_RISK_BASE_URL": "http://risk.test",
        "DPM_RISK_REQUIRED_CAPABILITIES_JSON": json.dumps(
            {
                "concentration": "risk.concentration",
                "regime_scenario": "risk.regime",
                "risk_event_cohort": "risk.cohort",
            }
        ),
        "ENTERPRISE_CAPABILITY_RULES_JSON": json.dumps({"POST /api/v1": "manage.write"}),
    }.items():
        monkeypatch.setenv(name, value)
    repository = InMemoryDpmWaveRepository()
    repository.save_wave(
        wave=_source_checked_wave(), idempotency_key=None, request_hash=None, tenant_id=TENANT_ID
    )
    headers = {
        "X-Actor-Id": "pm_001",
        "X-Role": "PM",
        "X-Correlation-Id": "corr-admission",
        "X-Service-Identity": "caller",
        "X-Capabilities": "manage.write,risk.concentration",
        "Idempotency-Key": "risk-custody-admission",
    }
    with _client(repository) as client:
        accepted = client.post(
            f"{BASE_PATH}/{WAVE_ID}/simulation-operations",
            headers=headers,
            json=_admission_payload(),
        )
        assert accepted.status_code == 202, accepted.text
        operation_id = accepted.json()["operation_id"]
        stored = repository.get_simulation_operation(tenant_id=TENANT_ID, operation_id=operation_id)
        assert stored.risk_authority_context.actor_id == "pm_001"
        assert stored.risk_authority_context_hash == stored.risk_authority_context.fingerprint()
        assert "risk_authority_context" not in accepted.json()
        assert "risk_authority_context_hash" not in accepted.json()
        from pydantic import ValidationError

        for changes in (
            {"risk_authority_context_hash": "sha256:altered"},
            {"risk_authority_context": None},
            {"actor_id": "impostor"},
            {"tenant_id": "foreign"},
            {"correlation_id": "different-admission"},
        ):
            with pytest.raises(ValidationError):
                type(stored).model_validate({**stored.model_dump(mode="json"), **changes})
        with pytest.raises(ValidationError):
            stored.risk_authority_context = None
        with pytest.raises(ValidationError):
            stored.risk_authority_context.actor_id = "impostor"
        replay = client.post(
            f"{BASE_PATH}/{WAVE_ID}/simulation-operations",
            headers=headers,
            json=_admission_payload(),
        )
        assert replay.status_code == 202
        assert replay.json()["idempotent_replay"]
        conflict = client.post(
            f"{BASE_PATH}/{WAVE_ID}/simulation-operations",
            headers={**headers, "X-Capabilities": "manage.write,risk.regime"},
            json=_admission_payload(),
        )
        assert conflict.status_code == 409
        body = {**_admission_payload(), "actor_id": "body-impostor"}
        assert (
            client.post(
                f"{BASE_PATH}/{WAVE_ID}/simulation-operations",
                headers={**headers, "Idempotency-Key": "actor-conflict"},
                json=body,
            ).status_code
            == 422
        )

        worker = Request({"type": "http"})
        worker.state.risk_authority_context = stored.risk_authority_context.model_copy(
            update={"actor_id": "worker-B", "grants": ()}
        )
        adapter = get_operation_risk_authority_client(worker, operation_id, repository)
        assert adapter._authority_context == stored.risk_authority_context
        outgoing = adapter._authority_headers("concentration", "corr-worker-attempt")
        assert outgoing["X-Actor-Id"] == "pm_001"
        assert outgoing["X-Capabilities"] == "risk.concentration"
        from src.api.services import construction_service

        seen_contexts = []
        generate = construction_service.generate_construction_alternative_set

        def capture_generation(**arguments):
            seen_contexts.append(arguments["risk_authority_context"])
            return generate(**arguments)

        monkeypatch.setattr(
            construction_service, "generate_construction_alternative_set", capture_generation
        )
        worked = client.post(
            f"{BASE_PATH}/simulation-operations/{operation_id}/work",
            headers={
                **headers,
                "X-Actor-Id": "worker-B",
                "X-Capabilities": "manage.write",
                "X-Correlation-Id": "worker-trace",
            },
            json={"worker_id": "worker-B", "max_items": 1},
        )
        assert worked.status_code == 200 and worked.json()["completed_count"] == 1, worked.text
        assert seen_contexts == [stored.risk_authority_context]
        worker.state.risk_authority_context = stored.risk_authority_context.model_copy(
            update={"tenant_id": "foreign"}
        )
        refused = get_operation_risk_authority_client(worker, operation_id, repository)
        with pytest.raises(LotusRiskAuthorityUnavailableError):
            refused._authority_headers("concentration", "corr-worker-attempt")
        monkeypatch.setenv("ENTERPRISE_POLICY_VERSION", "changed-policy")
        worker.state.risk_authority_context = stored.risk_authority_context
        refused = get_operation_risk_authority_client(worker, operation_id, repository)
        with pytest.raises(LotusRiskAuthorityUnavailableError):
            refused._authority_headers("concentration", "corr-worker-attempt")


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
        len(
            construction_repository.list_alternative_sets(
                portfolio_id=PORTFOLIO_ID,
                tenant_id=TENANT_ID,
                limit=10,
            )
        )
        == 1
    )


def test_transient_worker_failure_retries_real_financial_work(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = InMemoryDpmWaveRepository()
    construction_repository = InMemoryConstructionRepository()
    repository.save_wave(
        wave=_source_checked_wave(), idempotency_key=None, request_hash=None, tenant_id=TENANT_ID
    )
    client = _client(repository, construction_repository)
    operation_id = _admit(client).json()["operation_id"]
    real_simulate = wave_simulation_operations.simulate_item

    def fail_once(**_: Any) -> DpmRebalanceWaveItem:
        raise TimeoutError("transient dependency failure")

    monkeypatch.setattr(wave_simulation_operations, "simulate_item", fail_once)
    failed = client.post(
        f"{BASE_PATH}/simulation-operations/{operation_id}/work",
        json={"worker_id": "first-worker", "max_items": 1, "lease_seconds": 30},
    )
    assert failed.status_code == 200
    assert failed.json()["failed_count"] == 1
    wave = repository.get_wave(wave_id=WAVE_ID, tenant_id=TENANT_ID)
    assert wave is not None
    assert wave.state == "SIMULATING"
    assert wave.items[0].state == "SOURCE_READY"
    retry = client.post(f"{BASE_PATH}/simulation-operations/{operation_id}/retry", json={})
    assert retry.status_code == 200
    monkeypatch.setattr(wave_simulation_operations, "simulate_item", real_simulate)
    completed = client.post(
        f"{BASE_PATH}/simulation-operations/{operation_id}/work",
        json={"worker_id": "replacement-worker", "max_items": 1, "lease_seconds": 30},
    )
    assert completed.status_code == 200
    assert completed.json()["completed_count"] == 1
    assert completed.json()["operation"]["status"] == "SUCCEEDED"
    records = repository.list_simulation_items(
        tenant_id=TENANT_ID, operation_id=operation_id, limit=10, offset=0
    ).items
    assert records[0].attempt_count == 2
    assert records[0].result_item is not None
    assert records[0].result_item.state == "SIMULATED"
    alternative_sets = construction_repository.list_alternative_sets(
        tenant_id=TENANT_ID, portfolio_id=PORTFOLIO_ID, limit=10
    )
    assert len(alternative_sets) == 1
    heuristic = next(
        alternative
        for alternative in alternative_sets[0].alternatives
        if alternative.method.value == "HEURISTIC_EXPLAINABLE"
    )
    assert heuristic.diagnostics["proposed_changes"][0]["quantity"] == "20"


def test_exhausted_failure_and_fresh_admission_have_truthful_distinct_identities(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = InMemoryDpmWaveRepository()
    repository.save_wave(
        wave=_source_checked_wave(), idempotency_key=None, request_hash=None, tenant_id=TENANT_ID
    )
    client = _client(repository)
    request = {**_admission_payload(), "max_attempts": 1}
    admitted = client.post(
        f"{BASE_PATH}/{WAVE_ID}/simulation-operations",
        headers={"Idempotency-Key": "first-admission"},
        json=request,
    )
    assert admitted.status_code == 202
    operation_id = admitted.json()["operation_id"]

    def fail(**_: Any) -> DpmRebalanceWaveItem:
        raise TimeoutError("dependency unavailable")

    monkeypatch.setattr(wave_simulation_operations, "simulate_item", fail)
    failed = client.post(
        f"{BASE_PATH}/simulation-operations/{operation_id}/work",
        json={"worker_id": "last-attempt", "max_items": 1, "lease_seconds": 30},
    )
    assert failed.status_code == 200
    assert failed.json()["operation"]["status"] == "FAILED"
    record = client.get(f"{BASE_PATH}/simulation-operations/{operation_id}/results").json()[
        "items"
    ][0]
    assert record["retryable"] is False
    assert record["error_code"] == "DPM_WAVE_SIMULATION_RETRY_EXHAUSTED"
    retry = client.post(f"{BASE_PATH}/simulation-operations/{operation_id}/retry", json={})
    assert retry.status_code == 200
    assert retry.json()["status"] == "FAILED"
    wave = repository.get_wave(wave_id=WAVE_ID, tenant_id=TENANT_ID)
    assert wave is not None
    assert wave.state == "SIMULATION_FAILED"

    # A new source check may make the same wave eligible again. Keep old admission durable.
    refreshed = _source_checked_wave().model_copy(update={"version": wave.version + 1})
    repository.update_wave(wave=refreshed, expected_version=wave.version, tenant_id=TENANT_ID)
    fresh = client.post(
        f"{BASE_PATH}/{WAVE_ID}/simulation-operations",
        headers={"Idempotency-Key": "second-admission"},
        json=request,
    )
    assert fresh.status_code == 202
    assert fresh.json()["operation_id"] != operation_id
    assert fresh.json()["correlation_id"] != admitted.json()["correlation_id"]
    replay = client.post(
        f"{BASE_PATH}/{WAVE_ID}/simulation-operations",
        headers={"Idempotency-Key": "second-admission"},
        json=request,
    )
    assert replay.status_code == 202
    assert replay.json()["correlation_id"] == fresh.json()["correlation_id"]
    assert replay.json()["idempotent_replay"] is True
    old_results = client.get(f"{BASE_PATH}/simulation-operations/{operation_id}/results")
    assert old_results.status_code == 200
    active_wave = repository.get_wave(wave_id=WAVE_ID, tenant_id=TENANT_ID)
    assert active_wave is not None
    assert active_wave.state == "SIMULATING"
    assert active_wave.items[0].state == "SOURCE_READY"
    original = repository.get_simulation_operation(tenant_id=TENANT_ID, operation_id=operation_id)
    assert original is not None
    assert original.status == "FAILED"


def test_serial_batch_claims_each_item_when_execution_starts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = InMemoryDpmWaveRepository()
    construction_repository = InMemoryConstructionRepository()
    wave = _source_checked_wave()
    items = [
        wave.items[0].model_copy(
            update={"wave_item_id": f"{ITEM_ID}-{index}", "portfolio_id": f"{PORTFOLIO_ID}-{index}"}
        )
        for index in range(3)
    ]
    wave = wave.model_copy(update={"items": items})
    repository.save_wave(wave=wave, idempotency_key=None, request_hash=None, tenant_id=TENANT_ID)
    client = _client(repository, construction_repository)
    payload = _admission_payload()
    inputs = []
    for item in items:
        request = _rebalance_request()
        request["portfolio_snapshot"]["portfolio_id"] = item.portfolio_id  # type: ignore[index]
        inputs.append({"wave_item_id": item.wave_item_id, "stateless_input": request})
    payload["item_inputs"] = inputs
    accepted = client.post(
        f"{BASE_PATH}/{WAVE_ID}/simulation-operations",
        headers={"Idempotency-Key": "serial-batch-leases"},
        json=payload,
    )
    assert accepted.status_code == 202
    operation_id = accepted.json()["operation_id"]
    clock_time = datetime.now(UTC)

    class ControlledClock:
        @staticmethod
        def now(_: Any) -> datetime:
            return clock_time

    real_simulate = wave_simulation_operations.simulate_item

    def slow_simulate(**kwargs: Any) -> DpmRebalanceWaveItem:
        nonlocal clock_time
        result = real_simulate(**kwargs)
        clock_time += timedelta(seconds=20)
        return result

    monkeypatch.setattr(wave_simulation_operations, "datetime", ControlledClock)
    monkeypatch.setattr(wave_simulation_operations, "simulate_item", slow_simulate)
    worked = client.post(
        f"{BASE_PATH}/simulation-operations/{operation_id}/work",
        json={"worker_id": "serial-worker", "max_items": 3, "lease_seconds": 30},
    )
    assert worked.status_code == 200
    assert worked.json()["claimed_count"] == worked.json()["completed_count"] == 3
    assert worked.json()["failed_count"] == 0
    assert worked.json()["operation"]["status"] == "SUCCEEDED"
    records = repository.list_simulation_items(
        tenant_id=TENANT_ID, operation_id=operation_id, limit=10, offset=0
    ).items
    assert all(record.status == "SUCCEEDED" and record.attempt_count == 1 for record in records)
    assert all(record.result_item and record.result_item.state == "SIMULATED" for record in records)
    assert len({record.claimed_at for record in records}) == 3


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
    assert (
        construction_repository.list_alternative_sets(
            portfolio_id=PORTFOLIO_ID,
            tenant_id=TENANT_ID,
            limit=10,
        )
        == []
    )


def test_async_simulation_preserves_tenant_cash_target_and_blocks_restricted_selection() -> None:
    repository = InMemoryDpmWaveRepository()
    construction_repository = InMemoryConstructionRepository()
    repository.save_wave(
        wave=_source_checked_wave(),
        idempotency_key=None,
        request_hash=None,
        tenant_id=TENANT_ID,
    )
    client = _client(repository, construction_repository)
    payload = _admission_payload(target_weight="1.0")
    payload["methods"] = ["HEURISTIC_EXPLAINABLE"]
    item_input = payload["item_inputs"][0]  # type: ignore[index]
    item_input["authority_context"] = _active_no_buy_authority_context()  # type: ignore[index]
    item_input["stateless_input"]["options"]["cash_reserve_target_weight"] = "0.02"  # type: ignore[index]

    accepted = client.post(
        f"{BASE_PATH}/{WAVE_ID}/simulation-operations",
        headers={"Idempotency-Key": "policy-bound-wave"},
        json=payload,
    )
    operation_id = accepted.json()["operation_id"]
    worked = client.post(
        f"{BASE_PATH}/simulation-operations/{operation_id}/work",
        json={"worker_id": "worker-policy", "max_items": 1, "lease_seconds": 30},
    )

    assert accepted.status_code == 202
    assert worked.status_code == 200
    assert worked.json()["completed_count"] == 1
    alternative_set = construction_repository.list_alternative_sets(
        portfolio_id=PORTFOLIO_ID,
        tenant_id=TENANT_ID,
        limit=10,
    )[0]
    alternative = alternative_set.alternatives[0]
    assert alternative_set.tenant_id == TENANT_ID
    assert alternative_set.status.value == "BLOCKED"
    assert alternative.method_status.value == "BLOCKED"
    assert alternative.diagnostics["authority_context"]["client_restriction_required"] is True
    assert alternative.comparison_metrics.cash_weight_after == Decimal("0.0200")
    assert alternative.diagnostics["proposed_changes"][0]["quantity"] == "47"
    assert any(
        trace.constraint == "CLIENT_RESTRICTION" and trace.status.value == "BLOCKED"
        for trace in alternative.constraint_trace
    )

    with pytest.raises(
        DpmWaveValidationError,
        match="A blocked construction alternative cannot be selected",
    ) as refused:
        wave_construction_selection.select_construction_alternative_for_wave(
            repository=construction_repository,
            alternative_set_id=alternative_set.alternative_set_id,
            alternative_id=alternative.alternative_id,
            actor_id="pm_001",
            reason_code="POLICY_REVIEW",
            comment=None,
            correlation_id="corr-policy-selection",
            tenant_id=TENANT_ID,
        )

    assert refused.value.code == "DPM_WAVE_CONSTRUCTION_ALTERNATIVE_BLOCKED"
    persisted = repository.get_wave(wave_id=WAVE_ID, tenant_id=TENANT_ID)
    assert persisted is not None
    assert persisted.items[0].state == "SIMULATED"
    assert persisted.items[0].selected_alternative_id is None
    assert (
        construction_repository.list_alternative_sets(
            portfolio_id="FOREIGN_PORTFOLIO",
            tenant_id=TENANT_ID,
            limit=10,
        )
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
                portfolio_id="FOREIGN_PORTFOLIO",
                tenant_id=TENANT_ID,
                limit=10,
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
