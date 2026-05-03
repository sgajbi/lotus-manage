from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from src.api.dependencies import (
    get_construction_repository,
    get_mandate_repository,
    get_proof_pack_repository,
    get_wave_repository,
)
from src.api.main import app
from src.api.routers.rebalance_runs import get_dpm_run_support_service
from src.api.services import construction_service, proof_pack_service
from src.core.mandates import (
    DpmMandateConstraintSet,
    DpmMandateDigitalTwin,
    DpmMandateHealthInput,
    DpmMandateReviewPolicy,
    DpmSourceProductLineage,
    calculate_mandate_health,
)
from src.core.rebalance_runs.service import DpmRunSupportService
from src.infrastructure.mandates import InMemoryDpmMandateRepository
from src.infrastructure.construction import InMemoryConstructionRepository
from src.infrastructure.proof_packs import InMemoryDpmProofPackRepository
from src.infrastructure.rebalance_runs import InMemoryDpmRunRepository
from src.infrastructure.waves import InMemoryDpmWaveRepository
from src.core.waves import DpmRebalanceWave


MANDATE_ID = "MANDATE_PB_SG_GLOBAL_BAL_001"
PORTFOLIO_ID = "PB_SG_GLOBAL_BAL_001"


def _twin(
    *,
    mandate_id: str = MANDATE_ID,
    portfolio_id: str = PORTFOLIO_ID,
) -> DpmMandateDigitalTwin:
    return DpmMandateDigitalTwin(
        mandate_id=mandate_id,
        portfolio_id=portfolio_id,
        mandate_version="3",
        as_of_date=date(2026, 5, 3),
        base_currency="SGD",
        reference_currency="SGD",
        risk_profile="BALANCED",
        investment_objective="LONG_TERM_TOTAL_RETURN",
        time_horizon="LONG_TERM",
        model_portfolio_id="MODEL_PB_SG_GLOBAL_BAL_DPM",
        constraints=DpmMandateConstraintSet(
            cash_band_min_weight=Decimal("0.02"),
            cash_band_max_weight=Decimal("0.10"),
            turnover_budget=Decimal("0.15"),
        ),
        review_policy=DpmMandateReviewPolicy(next_review_due_date=date(2026, 6, 30)),
        source_lineage=[
            DpmSourceProductLineage(
                product_name="DPM_CORE_MANDATE_BINDING",
                product_version="1.0.0",
                source_record_id=f"core-binding-{portfolio_id.lower()}",
                data_quality_status="READY",
            )
        ],
    )


def _save_ready_health(
    repository: InMemoryDpmMandateRepository,
    twin: DpmMandateDigitalTwin,
) -> None:
    repository.save_health_snapshot(
        calculate_mandate_health(
            DpmMandateHealthInput(
                twin=twin,
                current_weights={"CASH": Decimal("0.05")},
                target_weights={"CASH": Decimal("0.05")},
                cash_weight=Decimal("0.05"),
            )
        )
    )


def _request() -> dict[str, object]:
    return {
        "trigger_type": "EXPLICIT_PORTFOLIO_LIST",
        "trigger_id": "manual-wave-001",
        "rationale": "Review explicit affected portfolio list.",
        "as_of_date": "2026-05-03",
        "actor_id": "pm_001",
        "portfolios": [
            {
                "portfolio_id": PORTFOLIO_ID,
                "source_refs": [
                    {
                        "source_system": "lotus-manage",
                        "source_type": "AFFECTED_PORTFOLIO_MANIFEST",
                        "source_id": "manifest_001",
                        "source_version": "1.0.0",
                        "supportability_state": "READY",
                    }
                ],
            },
            {"portfolio_id": "PB_SG_UNSOURCED_002"},
        ],
    }


def _rebalance_request(portfolio_id: str = PORTFOLIO_ID) -> dict[str, object]:
    return {
        "portfolio_snapshot": {
            "portfolio_id": portfolio_id,
            "base_currency": "SGD",
            "positions": [{"instrument_id": "EQ_1", "quantity": "100"}],
            "cash_balances": [{"currency": "SGD", "amount": "5000"}],
        },
        "market_data_snapshot": {
            "prices": [{"instrument_id": "EQ_1", "price": "100", "currency": "SGD"}],
            "fx_rates": [],
        },
        "model_portfolio": {"targets": [{"instrument_id": "EQ_1", "weight": "0.80"}]},
        "shelf_entries": [{"instrument_id": "EQ_1", "status": "APPROVED"}],
        "options": {"target_method": "HEURISTIC"},
    }


def _client(
    mandate_repository: InMemoryDpmMandateRepository,
    wave_repository: InMemoryDpmWaveRepository,
    construction_repository: InMemoryConstructionRepository | None = None,
    proof_pack_repository: InMemoryDpmProofPackRepository | None = None,
    run_service: DpmRunSupportService | None = None,
) -> TestClient:
    app.dependency_overrides[get_mandate_repository] = lambda: mandate_repository
    app.dependency_overrides[get_wave_repository] = lambda: wave_repository
    if construction_repository is not None:
        app.dependency_overrides[get_construction_repository] = lambda: construction_repository
    if proof_pack_repository is not None:
        app.dependency_overrides[get_proof_pack_repository] = lambda: proof_pack_repository
    if run_service is not None:
        app.dependency_overrides[get_dpm_run_support_service] = lambda: run_service
    app.openapi_schema = None
    return TestClient(app)


def _run_service() -> DpmRunSupportService:
    return DpmRunSupportService(repository=InMemoryDpmRunRepository())


def teardown_function() -> None:
    app.dependency_overrides.clear()
    app.openapi_schema = None


def test_wave_preview_returns_source_backed_and_blocked_items_without_persistence() -> None:
    mandate_repository = InMemoryDpmMandateRepository()
    mandate_repository.save_mandate_snapshot(_twin())
    wave_repository = InMemoryDpmWaveRepository()

    with _client(mandate_repository, wave_repository) as client:
        response = client.post(
            "/api/v1/rebalance/waves/preview",
            json=_request(),
            headers={"X-Correlation-Id": "corr-wave-test-001"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["durable"] is False
    assert payload["wave"]["state"] == "PREVIEWED"
    assert payload["wave"]["aggregate_metrics"]["state_counts"] == {
        "CANDIDATE": 1,
        "SOURCE_BLOCKED": 1,
    }
    assert payload["wave"]["items"][0]["mandate_id"] == MANDATE_ID
    assert payload["wave"]["items"][1]["reason_codes"] == ["MISSING_AFFECTED_PORTFOLIO_SOURCE"]
    assert wave_repository.get_wave(wave_id=payload["wave"]["wave_id"]) is None


def test_wave_create_persists_and_replays_by_idempotency_key() -> None:
    mandate_repository = InMemoryDpmMandateRepository()
    wave_repository = InMemoryDpmWaveRepository()

    with _client(mandate_repository, wave_repository) as client:
        first = client.post(
            "/api/v1/rebalance/waves",
            json=_request(),
            headers={"Idempotency-Key": "idem-wave-001"},
        )
        second = client.post(
            "/api/v1/rebalance/waves",
            json=_request(),
            headers={"Idempotency-Key": "idem-wave-001"},
        )

    assert first.status_code == 201
    assert second.status_code == 201
    first_payload = first.json()
    second_payload = second.json()
    assert first_payload["durable"] is True
    assert first_payload["idempotent_replay"] is False
    assert second_payload["idempotent_replay"] is True
    assert second_payload["wave"]["wave_id"] == first_payload["wave"]["wave_id"]
    assert wave_repository.get_wave(wave_id=first_payload["wave"]["wave_id"]) is not None


def test_wave_source_check_classifies_mixed_items_and_attaches_authoritative_refs() -> None:
    mandate_repository = InMemoryDpmMandateRepository()
    ready_twin = _twin()
    degraded_twin = _twin(
        mandate_id="MANDATE_PB_SG_NEEDS_HEALTH_002",
        portfolio_id="PB_SG_NEEDS_HEALTH_002",
    )
    mandate_repository.save_mandate_snapshot(ready_twin)
    mandate_repository.save_mandate_snapshot(degraded_twin)
    _save_ready_health(mandate_repository, ready_twin)
    wave_repository = InMemoryDpmWaveRepository()
    source_check_request = {
        **_request(),
        "portfolios": [
            {"portfolio_id": PORTFOLIO_ID},
            {"portfolio_id": "PB_SG_NEEDS_HEALTH_002"},
            {
                "portfolio_id": "PB_SG_CALLER_REF_ONLY_003",
                "source_refs": [
                    {
                        "source_system": "caller",
                        "source_type": "AFFECTED_PORTFOLIO_MANIFEST",
                        "source_id": "manifest-caller-only",
                        "source_version": "1.0.0",
                        "supportability_state": "READY",
                    }
                ],
            },
        ],
    }

    with _client(mandate_repository, wave_repository) as client:
        created = client.post(
            "/api/v1/rebalance/waves",
            json=source_check_request,
            headers={"Idempotency-Key": "idem-wave-source-check-001"},
        )
        wave_id = created.json()["wave"]["wave_id"]
        checked = client.post(
            f"/api/v1/rebalance/waves/{wave_id}/source-check",
            json={"actor_id": "pm_001"},
            headers={"X-Correlation-Id": "corr-source-check-001"},
        )
        replayed = client.post(
            f"/api/v1/rebalance/waves/{wave_id}/source-check",
            json={"actor_id": "pm_001"},
        )

    assert created.status_code == 201
    assert checked.status_code == 200
    payload = checked.json()
    assert payload["durable"] is True
    assert payload["idempotent_replay"] is False
    assert payload["wave"]["state"] == "SOURCE_CHECKED"
    assert payload["wave"]["aggregate_metrics"]["state_counts"] == {
        "SOURCE_READY": 1,
        "SOURCE_DEGRADED": 1,
        "SOURCE_BLOCKED": 1,
    }
    assert payload["wave"]["aggregate_metrics"]["ready_item_count"] == 1
    items_by_portfolio = {item["portfolio_id"]: item for item in payload["wave"]["items"]}
    ready_item = items_by_portfolio[PORTFOLIO_ID]
    assert ready_item["state"] == "SOURCE_READY"
    assert {ref["source_type"] for ref in ready_item["source_refs"]} >= {
        "MANDATE_DIGITAL_TWIN",
        "DPM_MANDATE_HEALTH_SNAPSHOT",
        "DPM_SOURCE_READINESS",
        "DPM_CORE_MANDATE_BINDING",
    }
    assert items_by_portfolio["PB_SG_NEEDS_HEALTH_002"]["state"] == "SOURCE_DEGRADED"
    assert items_by_portfolio["PB_SG_NEEDS_HEALTH_002"]["diagnostics"] == {
        "source_posture": "candidate_evidence_available",
        "source_owner": "lotus-manage",
        "required_action": "RUN_MANDATE_HEALTH_REFRESH",
        "missing_source_family": "MANDATE_HEALTH",
    }
    caller_only_item = items_by_portfolio["PB_SG_CALLER_REF_ONLY_003"]
    assert caller_only_item["state"] == "SOURCE_BLOCKED"
    assert caller_only_item["reason_codes"] == ["MANDATE_DIGITAL_TWIN_MISSING"]
    assert caller_only_item["diagnostics"]["source_owner"] == "lotus-manage"
    assert caller_only_item["diagnostics"]["source_owner_upstream"] == "lotus-core"

    replay_payload = replayed.json()
    assert replayed.status_code == 200
    assert replay_payload["idempotent_replay"] is True
    assert replay_payload["wave"]["version"] == payload["wave"]["version"]
    assert replay_payload["wave"]["events"] == payload["wave"]["events"]


def test_wave_source_check_reports_missing_and_invalid_state_errors() -> None:
    mandate_repository = InMemoryDpmMandateRepository()
    wave_repository = InMemoryDpmWaveRepository()

    with _client(mandate_repository, wave_repository) as client:
        missing = client.post(
            "/api/v1/rebalance/waves/dwv_missing/source-check",
            json={"actor_id": "pm_001"},
        )
        draft = client.post(
            "/api/v1/rebalance/waves/preview",
            json=_request(),
        )
        wave_repository.save_wave(
            wave=DpmRebalanceWave.model_validate(draft.json()["wave"]),
            idempotency_key=None,
            request_hash=None,
        )
        invalid = client.post(
            f"/api/v1/rebalance/waves/{draft.json()['wave']['wave_id']}/source-check",
            json={"actor_id": "pm_001"},
        )

    assert missing.status_code == 404
    assert missing.json()["detail"]["code"] == "DPM_WAVE_NOT_FOUND"
    assert invalid.status_code == 422
    assert invalid.json()["detail"]["code"] == "DPM_WAVE_SOURCE_CHECK_INVALID_STATE"


def test_wave_simulate_selects_alternative_and_links_proof_pack_after_reload() -> None:
    mandate_repository = InMemoryDpmMandateRepository()
    ready_twin = _twin()
    mandate_repository.save_mandate_snapshot(ready_twin)
    _save_ready_health(mandate_repository, ready_twin)
    wave_repository = InMemoryDpmWaveRepository()
    construction_repository = InMemoryConstructionRepository()
    proof_pack_repository = InMemoryDpmProofPackRepository()
    run_service = _run_service()

    with _client(
        mandate_repository,
        wave_repository,
        construction_repository,
        proof_pack_repository,
        run_service,
    ) as client:
        created = client.post(
            "/api/v1/rebalance/waves",
            json={**_request(), "portfolios": [{"portfolio_id": PORTFOLIO_ID}]},
            headers={"Idempotency-Key": "idem-wave-sim-select-001"},
        )
        wave_id = created.json()["wave"]["wave_id"]
        checked = client.post(
            f"/api/v1/rebalance/waves/{wave_id}/source-check",
            json={"actor_id": "pm_001"},
        )
        wave_item_id = checked.json()["wave"]["items"][0]["wave_item_id"]
        simulated = client.post(
            f"/api/v1/rebalance/waves/{wave_id}/simulate",
            json={
                "actor_id": "pm_001",
                "methods": ["DO_NOTHING_BASELINE", "HEURISTIC_EXPLAINABLE", "MIN_TURNOVER"],
                "item_inputs": [
                    {
                        "wave_item_id": wave_item_id,
                        "stateless_input": _rebalance_request(PORTFOLIO_ID),
                    }
                ],
            },
            headers={"X-Correlation-Id": "corr-wave-sim-select"},
        )
        simulated_replay = client.post(
            f"/api/v1/rebalance/waves/{wave_id}/simulate",
            json={"actor_id": "pm_001", "item_inputs": []},
        )
        selected = client.post(
            f"/api/v1/rebalance/waves/{wave_id}/items/{wave_item_id}/select",
            json={
                "alternative_id": "alt_min_turnover",
                "actor_id": "pm_001",
                "reason_code": "LOWER_TURNOVER_WITH_ACCEPTABLE_DRIFT",
                "comment": "Chosen for lower turnover.",
            },
            headers={"X-Correlation-Id": "corr-wave-select"},
        )

    assert simulated.status_code == 200
    simulated_payload = simulated.json()
    assert simulated_payload["wave"]["state"] == "SIMULATED"
    simulated_item = simulated_payload["wave"]["items"][0]
    assert simulated_item["state"] == "SIMULATED"
    assert simulated_item["alternative_set_id"].startswith("cas_")
    assert simulated_item["diagnostics"]["alternative_count"] == 3
    assert simulated_replay.json()["idempotent_replay"] is True

    assert selected.status_code == 200
    selected_item = selected.json()["wave"]["items"][0]
    assert selected_item["state"] == "PROOF_PACK_READY"
    assert selected_item["selected_alternative_id"] == "alt_min_turnover"
    assert selected_item["proof_pack_id"].startswith("dpp_")
    persisted = wave_repository.get_wave(wave_id=wave_id)
    assert persisted is not None
    assert persisted.items[0].selected_alternative_id == "alt_min_turnover"
    assert persisted.items[0].proof_pack_id == selected_item["proof_pack_id"]
    assert (
        proof_pack_repository.get_proof_pack(proof_pack_id=selected_item["proof_pack_id"])
        is not None
    )


def test_wave_simulation_preserves_blocked_items_and_degrades_missing_inputs() -> None:
    mandate_repository = InMemoryDpmMandateRepository()
    ready_twin = _twin()
    mandate_repository.save_mandate_snapshot(ready_twin)
    _save_ready_health(mandate_repository, ready_twin)
    wave_repository = InMemoryDpmWaveRepository()

    with _client(
        mandate_repository,
        wave_repository,
        InMemoryConstructionRepository(),
        InMemoryDpmProofPackRepository(),
        _run_service(),
    ) as client:
        created = client.post(
            "/api/v1/rebalance/waves",
            json={
                **_request(),
                "portfolios": [
                    {"portfolio_id": PORTFOLIO_ID},
                    {"portfolio_id": "PB_SG_CALLER_REF_ONLY_003"},
                ],
            },
            headers={"Idempotency-Key": "idem-wave-sim-blocked-001"},
        )
        wave_id = created.json()["wave"]["wave_id"]
        checked = client.post(
            f"/api/v1/rebalance/waves/{wave_id}/source-check",
            json={"actor_id": "pm_001"},
        )
        simulated = client.post(
            f"/api/v1/rebalance/waves/{wave_id}/simulate",
            json={"actor_id": "pm_001", "item_inputs": []},
        )

    assert checked.status_code == 200
    assert simulated.status_code == 200
    payload = simulated.json()
    assert payload["wave"]["state"] == "SIMULATION_FAILED"
    assert payload["wave"]["aggregate_metrics"]["state_counts"] == {
        "SIMULATION_BLOCKED": 1,
        "SOURCE_BLOCKED": 1,
    }
    items_by_portfolio = {item["portfolio_id"]: item for item in payload["wave"]["items"]}
    assert items_by_portfolio[PORTFOLIO_ID]["reason_codes"] == ["CONSTRUCTION_INPUT_MISSING"]
    assert items_by_portfolio["PB_SG_CALLER_REF_ONLY_003"]["reason_codes"] == [
        "MANDATE_DIGITAL_TWIN_MISSING"
    ]


def test_wave_simulation_reports_invalid_state_and_partial_result() -> None:
    mandate_repository = InMemoryDpmMandateRepository()
    ready_twin = _twin()
    second_twin = _twin(
        mandate_id="MANDATE_PB_SG_READY_002",
        portfolio_id="PB_SG_READY_002",
    )
    mandate_repository.save_mandate_snapshot(ready_twin)
    mandate_repository.save_mandate_snapshot(second_twin)
    _save_ready_health(mandate_repository, ready_twin)
    _save_ready_health(mandate_repository, second_twin)
    wave_repository = InMemoryDpmWaveRepository()

    with _client(
        mandate_repository,
        wave_repository,
        InMemoryConstructionRepository(),
        InMemoryDpmProofPackRepository(),
        _run_service(),
    ) as client:
        draft = client.post(
            "/api/v1/rebalance/waves",
            json={**_request(), "portfolios": [{"portfolio_id": PORTFOLIO_ID}]},
            headers={"Idempotency-Key": "idem-wave-invalid-sim-state"},
        )
        invalid = client.post(
            f"/api/v1/rebalance/waves/{draft.json()['wave']['wave_id']}/simulate",
            json={"actor_id": "pm_001", "item_inputs": []},
        )

        created = client.post(
            "/api/v1/rebalance/waves",
            json={
                **_request(),
                "portfolios": [
                    {"portfolio_id": PORTFOLIO_ID},
                    {"portfolio_id": "PB_SG_READY_002"},
                ],
            },
            headers={"Idempotency-Key": "idem-wave-partial-sim"},
        )
        wave_id = created.json()["wave"]["wave_id"]
        checked = client.post(
            f"/api/v1/rebalance/waves/{wave_id}/source-check",
            json={"actor_id": "pm_001"},
        )
        items_by_portfolio = {
            item["portfolio_id"]: item for item in checked.json()["wave"]["items"]
        }
        partial = client.post(
            f"/api/v1/rebalance/waves/{wave_id}/simulate",
            json={
                "actor_id": "pm_001",
                "item_inputs": [
                    {
                        "wave_item_id": items_by_portfolio[PORTFOLIO_ID]["wave_item_id"],
                        "stateless_input": _rebalance_request(PORTFOLIO_ID),
                    }
                ],
            },
        )

    assert invalid.status_code == 422
    assert invalid.json()["detail"]["code"] == "DPM_WAVE_SIMULATION_INVALID_STATE"
    assert partial.status_code == 200
    assert partial.json()["wave"]["state"] == "PARTIALLY_SIMULATED"
    assert partial.json()["wave"]["aggregate_metrics"]["state_counts"] == {
        "SIMULATED": 1,
        "SIMULATION_BLOCKED": 1,
    }


def test_wave_simulation_degrades_generation_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    mandate_repository = InMemoryDpmMandateRepository()
    ready_twin = _twin()
    mandate_repository.save_mandate_snapshot(ready_twin)
    _save_ready_health(mandate_repository, ready_twin)
    wave_repository = InMemoryDpmWaveRepository()

    def fail_generation(**_: object) -> None:
        raise RuntimeError("construction unavailable")

    monkeypatch.setattr(
        construction_service,
        "generate_construction_alternative_set",
        fail_generation,
    )

    with _client(
        mandate_repository,
        wave_repository,
        InMemoryConstructionRepository(),
        InMemoryDpmProofPackRepository(),
        _run_service(),
    ) as client:
        created = client.post(
            "/api/v1/rebalance/waves",
            json={**_request(), "portfolios": [{"portfolio_id": PORTFOLIO_ID}]},
            headers={"Idempotency-Key": "idem-wave-sim-generation-fails"},
        )
        wave_id = created.json()["wave"]["wave_id"]
        checked = client.post(
            f"/api/v1/rebalance/waves/{wave_id}/source-check",
            json={"actor_id": "pm_001"},
        )
        wave_item_id = checked.json()["wave"]["items"][0]["wave_item_id"]
        simulated = client.post(
            f"/api/v1/rebalance/waves/{wave_id}/simulate",
            json={
                "actor_id": "pm_001",
                "item_inputs": [
                    {
                        "wave_item_id": wave_item_id,
                        "stateless_input": _rebalance_request(PORTFOLIO_ID),
                    }
                ],
            },
        )

    assert simulated.status_code == 200
    item = simulated.json()["wave"]["items"][0]
    assert simulated.json()["wave"]["state"] == "SIMULATION_FAILED"
    assert item["state"] == "SIMULATION_BLOCKED"
    assert item["reason_codes"] == ["CONSTRUCTION_ALTERNATIVE_GENERATION_FAILED"]
    assert item["diagnostics"]["construction_error"] == "RuntimeError"


def test_wave_selection_degrades_when_proof_pack_generation_is_not_requested() -> None:
    mandate_repository = InMemoryDpmMandateRepository()
    ready_twin = _twin()
    mandate_repository.save_mandate_snapshot(ready_twin)
    _save_ready_health(mandate_repository, ready_twin)
    wave_repository = InMemoryDpmWaveRepository()

    with _client(
        mandate_repository,
        wave_repository,
        InMemoryConstructionRepository(),
        InMemoryDpmProofPackRepository(),
        _run_service(),
    ) as client:
        created = client.post(
            "/api/v1/rebalance/waves",
            json={**_request(), "portfolios": [{"portfolio_id": PORTFOLIO_ID}]},
            headers={"Idempotency-Key": "idem-wave-select-degraded-001"},
        )
        wave_id = created.json()["wave"]["wave_id"]
        checked = client.post(
            f"/api/v1/rebalance/waves/{wave_id}/source-check",
            json={"actor_id": "pm_001"},
        )
        wave_item_id = checked.json()["wave"]["items"][0]["wave_item_id"]
        client.post(
            f"/api/v1/rebalance/waves/{wave_id}/simulate",
            json={
                "actor_id": "pm_001",
                "item_inputs": [
                    {
                        "wave_item_id": wave_item_id,
                        "stateless_input": _rebalance_request(PORTFOLIO_ID),
                    }
                ],
            },
        )
        selected = client.post(
            f"/api/v1/rebalance/waves/{wave_id}/items/{wave_item_id}/select",
            json={
                "alternative_id": "alt_min_turnover",
                "actor_id": "pm_001",
                "reason_code": "LOWER_TURNOVER_WITH_ACCEPTABLE_DRIFT",
                "generate_proof_pack": False,
            },
        )

    assert selected.status_code == 200
    selected_item = selected.json()["wave"]["items"][0]
    assert selected_item["state"] == "SELECTED"
    assert selected_item["proof_pack_id"] is None
    assert selected_item["diagnostics"]["proof_pack_state"] == "DEGRADED"
    assert (
        selected_item["diagnostics"]["proof_pack_reason_code"]
        == "PROOF_PACK_GENERATION_NOT_REQUESTED"
    )


def test_wave_selection_reports_invalid_item_and_alternative_errors() -> None:
    mandate_repository = InMemoryDpmMandateRepository()
    ready_twin = _twin()
    mandate_repository.save_mandate_snapshot(ready_twin)
    _save_ready_health(mandate_repository, ready_twin)
    wave_repository = InMemoryDpmWaveRepository()

    with _client(
        mandate_repository,
        wave_repository,
        InMemoryConstructionRepository(),
        InMemoryDpmProofPackRepository(),
        _run_service(),
    ) as client:
        created = client.post(
            "/api/v1/rebalance/waves",
            json={**_request(), "portfolios": [{"portfolio_id": PORTFOLIO_ID}]},
            headers={"Idempotency-Key": "idem-wave-select-errors"},
        )
        wave_id = created.json()["wave"]["wave_id"]
        invalid_state = client.post(
            f"/api/v1/rebalance/waves/{wave_id}/items/dwi_missing/select",
            json={
                "alternative_id": "alt_min_turnover",
                "actor_id": "pm_001",
                "reason_code": "LOWER_TURNOVER_WITH_ACCEPTABLE_DRIFT",
            },
        )
        checked = client.post(
            f"/api/v1/rebalance/waves/{wave_id}/source-check",
            json={"actor_id": "pm_001"},
        )
        wave_item_id = checked.json()["wave"]["items"][0]["wave_item_id"]
        client.post(
            f"/api/v1/rebalance/waves/{wave_id}/simulate",
            json={
                "actor_id": "pm_001",
                "item_inputs": [
                    {
                        "wave_item_id": wave_item_id,
                        "stateless_input": _rebalance_request(PORTFOLIO_ID),
                    }
                ],
            },
        )
        missing_item = client.post(
            f"/api/v1/rebalance/waves/{wave_id}/items/dwi_missing/select",
            json={
                "alternative_id": "alt_min_turnover",
                "actor_id": "pm_001",
                "reason_code": "LOWER_TURNOVER_WITH_ACCEPTABLE_DRIFT",
            },
        )
        bad_alternative = client.post(
            f"/api/v1/rebalance/waves/{wave_id}/items/{wave_item_id}/select",
            json={
                "alternative_id": "alt_unknown",
                "actor_id": "pm_001",
                "reason_code": "LOWER_TURNOVER_WITH_ACCEPTABLE_DRIFT",
            },
        )

    assert invalid_state.status_code == 422
    assert invalid_state.json()["detail"]["code"] == "DPM_WAVE_SELECTION_INVALID_STATE"
    assert missing_item.status_code == 404
    assert missing_item.json()["detail"]["code"] == "DPM_WAVE_ITEM_NOT_FOUND"
    assert bad_alternative.status_code == 404
    assert bad_alternative.json()["detail"]["code"] == "DPM_CONSTRUCTION_ALTERNATIVE_NOT_FOUND"


def test_wave_selection_rejects_items_without_generated_alternatives() -> None:
    mandate_repository = InMemoryDpmMandateRepository()
    ready_twin = _twin()
    second_twin = _twin(
        mandate_id="MANDATE_PB_SG_READY_003",
        portfolio_id="PB_SG_READY_003",
    )
    mandate_repository.save_mandate_snapshot(ready_twin)
    mandate_repository.save_mandate_snapshot(second_twin)
    _save_ready_health(mandate_repository, ready_twin)
    _save_ready_health(mandate_repository, second_twin)
    wave_repository = InMemoryDpmWaveRepository()

    with _client(
        mandate_repository,
        wave_repository,
        InMemoryConstructionRepository(),
        InMemoryDpmProofPackRepository(),
        _run_service(),
    ) as client:
        created = client.post(
            "/api/v1/rebalance/waves",
            json={
                **_request(),
                "portfolios": [
                    {"portfolio_id": PORTFOLIO_ID},
                    {"portfolio_id": "PB_SG_READY_003"},
                ],
            },
            headers={"Idempotency-Key": "idem-wave-select-no-alts"},
        )
        wave_id = created.json()["wave"]["wave_id"]
        checked = client.post(
            f"/api/v1/rebalance/waves/{wave_id}/source-check",
            json={"actor_id": "pm_001"},
        )
        items_by_portfolio = {
            item["portfolio_id"]: item for item in checked.json()["wave"]["items"]
        }
        client.post(
            f"/api/v1/rebalance/waves/{wave_id}/simulate",
            json={
                "actor_id": "pm_001",
                "item_inputs": [
                    {
                        "wave_item_id": items_by_portfolio[PORTFOLIO_ID]["wave_item_id"],
                        "stateless_input": _rebalance_request(PORTFOLIO_ID),
                    }
                ],
            },
        )
        blocked_item_id = items_by_portfolio["PB_SG_READY_003"]["wave_item_id"]
        selected = client.post(
            f"/api/v1/rebalance/waves/{wave_id}/items/{blocked_item_id}/select",
            json={
                "alternative_id": "alt_min_turnover",
                "actor_id": "pm_001",
                "reason_code": "LOWER_TURNOVER_WITH_ACCEPTABLE_DRIFT",
            },
        )

    assert selected.status_code == 422
    assert selected.json()["detail"]["code"] == "DPM_WAVE_ITEM_ALTERNATIVES_MISSING"


def test_wave_selection_degrades_when_proof_pack_generation_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mandate_repository = InMemoryDpmMandateRepository()
    ready_twin = _twin()
    mandate_repository.save_mandate_snapshot(ready_twin)
    _save_ready_health(mandate_repository, ready_twin)
    wave_repository = InMemoryDpmWaveRepository()

    def fail_proof_pack(**_: object) -> None:
        raise RuntimeError("proof pack unavailable")

    monkeypatch.setattr(
        proof_pack_service,
        "generate_proof_pack_from_selected_alternative",
        fail_proof_pack,
    )

    with _client(
        mandate_repository,
        wave_repository,
        InMemoryConstructionRepository(),
        InMemoryDpmProofPackRepository(),
        _run_service(),
    ) as client:
        created = client.post(
            "/api/v1/rebalance/waves",
            json={**_request(), "portfolios": [{"portfolio_id": PORTFOLIO_ID}]},
            headers={"Idempotency-Key": "idem-wave-proof-pack-fails"},
        )
        wave_id = created.json()["wave"]["wave_id"]
        checked = client.post(
            f"/api/v1/rebalance/waves/{wave_id}/source-check",
            json={"actor_id": "pm_001"},
        )
        wave_item_id = checked.json()["wave"]["items"][0]["wave_item_id"]
        client.post(
            f"/api/v1/rebalance/waves/{wave_id}/simulate",
            json={
                "actor_id": "pm_001",
                "item_inputs": [
                    {
                        "wave_item_id": wave_item_id,
                        "stateless_input": _rebalance_request(PORTFOLIO_ID),
                    }
                ],
            },
        )
        selected = client.post(
            f"/api/v1/rebalance/waves/{wave_id}/items/{wave_item_id}/select",
            json={
                "alternative_id": "alt_min_turnover",
                "actor_id": "pm_001",
                "reason_code": "LOWER_TURNOVER_WITH_ACCEPTABLE_DRIFT",
            },
        )

    assert selected.status_code == 200
    item = selected.json()["wave"]["items"][0]
    assert item["state"] == "SELECTED"
    assert item["proof_pack_id"] is None
    assert item["diagnostics"]["proof_pack_state"] == "DEGRADED"
    assert item["diagnostics"]["proof_pack_reason_code"] == "PROOF_PACK_GENERATION_FAILED"
    assert item["diagnostics"]["proof_pack_error"] == "RuntimeError"


def test_wave_approval_staging_and_handoff_are_durable_and_idempotent() -> None:
    mandate_repository = InMemoryDpmMandateRepository()
    ready_twin = _twin()
    mandate_repository.save_mandate_snapshot(ready_twin)
    _save_ready_health(mandate_repository, ready_twin)
    wave_repository = InMemoryDpmWaveRepository()

    with _client(
        mandate_repository,
        wave_repository,
        InMemoryConstructionRepository(),
        InMemoryDpmProofPackRepository(),
        _run_service(),
    ) as client:
        created = client.post(
            "/api/v1/rebalance/waves",
            json={**_request(), "portfolios": [{"portfolio_id": PORTFOLIO_ID}]},
            headers={"Idempotency-Key": "idem-wave-approval-handoff"},
        )
        wave_id = created.json()["wave"]["wave_id"]
        checked = client.post(
            f"/api/v1/rebalance/waves/{wave_id}/source-check",
            json={"actor_id": "pm_001"},
        )
        wave_item_id = checked.json()["wave"]["items"][0]["wave_item_id"]
        client.post(
            f"/api/v1/rebalance/waves/{wave_id}/simulate",
            json={
                "actor_id": "pm_001",
                "item_inputs": [
                    {
                        "wave_item_id": wave_item_id,
                        "stateless_input": _rebalance_request(PORTFOLIO_ID),
                    }
                ],
            },
        )
        client.post(
            f"/api/v1/rebalance/waves/{wave_id}/items/{wave_item_id}/select",
            json={
                "alternative_id": "alt_min_turnover",
                "actor_id": "pm_001",
                "reason_code": "LOWER_TURNOVER_WITH_ACCEPTABLE_DRIFT",
            },
        )
        approved = client.post(
            f"/api/v1/rebalance/waves/{wave_id}/approve",
            json={
                "actor_id": "pm_001",
                "reason_code": "PROOF_PACK_REVIEWED",
                "comment": "Approved after proof-pack review.",
            },
        )
        approved_replay = client.post(
            f"/api/v1/rebalance/waves/{wave_id}/approve",
            json={"actor_id": "pm_001", "reason_code": "PROOF_PACK_REVIEWED"},
        )
        staged = client.post(
            f"/api/v1/rebalance/waves/{wave_id}/stage",
            json={
                "actor_id": "ops_001",
                "reason_code": "READY_FOR_OPERATIONS_REVIEW",
            },
        )
        staged_replay = client.post(
            f"/api/v1/rebalance/waves/{wave_id}/stage",
            json={
                "actor_id": "ops_001",
                "reason_code": "READY_FOR_OPERATIONS_REVIEW",
            },
        )
        handoff = client.post(
            f"/api/v1/rebalance/waves/{wave_id}/handoff",
            json={
                "actor_id": "ops_001",
                "reason_code": "OPERATIONS_PACKAGE_PREPARED",
            },
        )
        handoff_replay = client.post(
            f"/api/v1/rebalance/waves/{wave_id}/handoff",
            json={
                "actor_id": "ops_001",
                "reason_code": "OPERATIONS_PACKAGE_PREPARED",
            },
        )

    assert approved.status_code == 200
    approved_payload = approved.json()
    assert approved_payload["wave"]["state"] == "APPROVED"
    assert approved_payload["wave"]["items"][0]["state"] == "APPROVED"
    assert approved_payload["wave"]["items"][0]["diagnostics"]["approval_actor_id"] == "pm_001"
    assert approved_replay.json()["idempotent_replay"] is True
    assert approved_replay.json()["wave"]["version"] == approved_payload["wave"]["version"]

    assert staged.status_code == 200
    staged_payload = staged.json()
    assert staged_payload["wave"]["state"] == "STAGED"
    assert staged_payload["wave"]["items"][0]["state"] == "STAGED"
    assert staged_payload["wave"]["items"][0]["diagnostics"]["external_execution_claimed"] is False
    assert staged_replay.json()["idempotent_replay"] is True

    assert handoff.status_code == 200
    handoff_payload = handoff.json()
    assert handoff_payload["wave"]["state"] == "HANDOFF_READY"
    assert handoff_payload["wave"]["items"][0]["state"] == "HANDOFF_READY"
    assert len(handoff_payload["wave"]["handoff_refs"]) == 1
    handoff_ref = handoff_payload["wave"]["handoff_refs"][0]
    assert handoff_ref["item_ids"] == [wave_item_id]
    assert handoff_ref["external_execution_claimed"] is False
    assert handoff_ref["content_hash"].startswith("sha256:")
    assert handoff_replay.json()["idempotent_replay"] is True
    assert handoff_replay.json()["wave"]["handoff_refs"] == handoff_payload["wave"]["handoff_refs"]

    persisted = wave_repository.get_wave(wave_id=wave_id)
    assert persisted is not None
    assert persisted.state == "HANDOFF_READY"
    assert len(persisted.handoff_refs) == 1
    assert [event.event_type for event in persisted.events][-3:] == [
        "STATE_TRANSITION",
        "STATE_TRANSITION",
        "STATE_TRANSITION",
    ]


def test_wave_approval_excludes_blocked_items_and_stages_only_approved_items() -> None:
    mandate_repository = InMemoryDpmMandateRepository()
    ready_twin = _twin()
    blocked_twin = _twin(
        mandate_id="MANDATE_PB_SG_READY_BUT_MISSING_INPUT",
        portfolio_id="PB_SG_READY_BUT_MISSING_INPUT",
    )
    mandate_repository.save_mandate_snapshot(ready_twin)
    mandate_repository.save_mandate_snapshot(blocked_twin)
    _save_ready_health(mandate_repository, ready_twin)
    _save_ready_health(mandate_repository, blocked_twin)
    wave_repository = InMemoryDpmWaveRepository()

    with _client(
        mandate_repository,
        wave_repository,
        InMemoryConstructionRepository(),
        InMemoryDpmProofPackRepository(),
        _run_service(),
    ) as client:
        created = client.post(
            "/api/v1/rebalance/waves",
            json={
                **_request(),
                "portfolios": [
                    {"portfolio_id": PORTFOLIO_ID},
                    {"portfolio_id": "PB_SG_READY_BUT_MISSING_INPUT"},
                ],
            },
            headers={"Idempotency-Key": "idem-wave-approval-exceptions"},
        )
        wave_id = created.json()["wave"]["wave_id"]
        checked = client.post(
            f"/api/v1/rebalance/waves/{wave_id}/source-check",
            json={"actor_id": "pm_001"},
        )
        items_by_portfolio = {
            item["portfolio_id"]: item for item in checked.json()["wave"]["items"]
        }
        ready_item_id = items_by_portfolio[PORTFOLIO_ID]["wave_item_id"]
        blocked_item_id = items_by_portfolio["PB_SG_READY_BUT_MISSING_INPUT"]["wave_item_id"]
        client.post(
            f"/api/v1/rebalance/waves/{wave_id}/simulate",
            json={
                "actor_id": "pm_001",
                "item_inputs": [
                    {
                        "wave_item_id": ready_item_id,
                        "stateless_input": _rebalance_request(PORTFOLIO_ID),
                    }
                ],
            },
        )
        client.post(
            f"/api/v1/rebalance/waves/{wave_id}/items/{ready_item_id}/select",
            json={
                "alternative_id": "alt_min_turnover",
                "actor_id": "pm_001",
                "reason_code": "LOWER_TURNOVER_WITH_ACCEPTABLE_DRIFT",
            },
        )
        approved = client.post(
            f"/api/v1/rebalance/waves/{wave_id}/approve",
            json={"actor_id": "pm_001", "reason_code": "APPROVE_READY_ITEMS_ONLY"},
        )
        staged = client.post(
            f"/api/v1/rebalance/waves/{wave_id}/stage",
            json={"actor_id": "ops_001", "reason_code": "STAGE_APPROVED_ITEMS_ONLY"},
        )
        handoff = client.post(
            f"/api/v1/rebalance/waves/{wave_id}/handoff",
            json={"actor_id": "ops_001", "reason_code": "HANDOFF_APPROVED_ITEMS_ONLY"},
        )

    assert approved.status_code == 200
    assert approved.json()["wave"]["state"] == "APPROVED_WITH_EXCEPTIONS"
    approved_items = {item["wave_item_id"]: item for item in approved.json()["wave"]["items"]}
    assert approved_items[ready_item_id]["state"] == "APPROVED"
    assert approved_items[blocked_item_id]["state"] == "SIMULATION_BLOCKED"

    assert staged.status_code == 200
    staged_items = {item["wave_item_id"]: item for item in staged.json()["wave"]["items"]}
    assert staged_items[ready_item_id]["state"] == "STAGED"
    assert staged_items[blocked_item_id]["state"] == "SIMULATION_BLOCKED"

    assert handoff.status_code == 200
    handoff_ref = handoff.json()["wave"]["handoff_refs"][0]
    assert handoff_ref["item_ids"] == [ready_item_id]
    assert blocked_item_id not in handoff_ref["item_ids"]


def test_wave_workflow_commands_reject_invalid_states_and_empty_eligibility() -> None:
    mandate_repository = InMemoryDpmMandateRepository()
    wave_repository = InMemoryDpmWaveRepository()

    with _client(
        mandate_repository,
        wave_repository,
        InMemoryConstructionRepository(),
        InMemoryDpmProofPackRepository(),
        _run_service(),
    ) as client:
        created = client.post(
            "/api/v1/rebalance/waves",
            json={**_request(), "portfolios": [{"portfolio_id": PORTFOLIO_ID}]},
            headers={"Idempotency-Key": "idem-wave-workflow-errors"},
        )
        wave_id = created.json()["wave"]["wave_id"]
        approve_invalid = client.post(
            f"/api/v1/rebalance/waves/{wave_id}/approve",
            json={"actor_id": "pm_001", "reason_code": "TOO_EARLY"},
        )
        stage_invalid = client.post(
            f"/api/v1/rebalance/waves/{wave_id}/stage",
            json={"actor_id": "ops_001", "reason_code": "TOO_EARLY"},
        )
        handoff_invalid = client.post(
            f"/api/v1/rebalance/waves/{wave_id}/handoff",
            json={"actor_id": "ops_001", "reason_code": "TOO_EARLY"},
        )

    assert approve_invalid.status_code == 422
    assert approve_invalid.json()["detail"]["code"] == "DPM_WAVE_APPROVAL_INVALID_STATE"
    assert stage_invalid.status_code == 422
    assert stage_invalid.json()["detail"]["code"] == "DPM_WAVE_STAGE_INVALID_STATE"
    assert handoff_invalid.status_code == 422
    assert handoff_invalid.json()["detail"]["code"] == "DPM_WAVE_HANDOFF_INVALID_STATE"


def test_wave_preview_rejects_unsupported_trigger_without_fallback() -> None:
    with _client(InMemoryDpmMandateRepository(), InMemoryDpmWaveRepository()) as client:
        response = client.post(
            "/api/v1/rebalance/waves/preview",
            json={**_request(), "trigger_type": "CIO_MODEL_CHANGE"},
        )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "NOT_SUPPORTED_TRIGGER"


def test_wave_openapi_documents_preview_and_create() -> None:
    with _client(InMemoryDpmMandateRepository(), InMemoryDpmWaveRepository()) as client:
        openapi = client.get("/openapi.json").json()

    preview = openapi["paths"]["/api/v1/rebalance/waves/preview"]["post"]
    create = openapi["paths"]["/api/v1/rebalance/waves"]["post"]
    source_check = openapi["paths"]["/api/v1/rebalance/waves/{wave_id}/source-check"]["post"]
    approve = openapi["paths"]["/api/v1/rebalance/waves/{wave_id}/approve"]["post"]
    stage = openapi["paths"]["/api/v1/rebalance/waves/{wave_id}/stage"]["post"]
    handoff = openapi["paths"]["/api/v1/rebalance/waves/{wave_id}/handoff"]["post"]
    assert preview["tags"] == ["lotus-manage Rebalance Waves"]
    assert create["tags"] == ["lotus-manage Rebalance Waves"]
    assert source_check["tags"] == ["lotus-manage Rebalance Waves"]
    assert approve["tags"] == ["lotus-manage Rebalance Waves"]
    assert stage["tags"] == ["lotus-manage Rebalance Waves"]
    assert handoff["tags"] == ["lotus-manage Rebalance Waves"]
    assert preview["responses"]["200"]["content"]["application/json"]["example"]["durable"] is False
    assert create["responses"]["201"]["content"]["application/json"]["example"]["durable"] is True
    assert (
        source_check["responses"]["200"]["content"]["application/json"]["example"]["wave"]["state"]
        == "SOURCE_CHECKED"
    )
    assert "422" in preview["responses"]
    assert "409" in create["responses"]
    assert "404" in source_check["responses"]
    assert "409" in source_check["responses"]
    assert "422" in source_check["responses"]
    assert "does not claim external order execution" in stage["description"]
    assert "external_execution_claimed=false" in handoff["description"]
