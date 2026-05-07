from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import cast

import pytest
from fastapi.testclient import TestClient

from src.api.dependencies import (
    get_construction_repository,
    get_mandate_repository,
    get_proof_pack_repository,
    get_wave_repository,
)
from src.api.main import app
from src.api.request_models import RebalanceRequest
from src.api.routers.rebalance_runs import get_dpm_run_support_service
from src.api.services import construction_service, proof_pack_service, wave_service
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
from src.core.waves import (
    DpmWaveAlreadyExistsError,
    DpmRebalanceWave,
    DpmRebalanceWaveItem,
    DpmWaveAggregateMetrics,
    DpmWaveHandoffRef,
    DpmWaveTrigger,
    DpmWaveVersionConflictError,
    WaveItemState,
    WaveState,
)


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


def _wave_item(
    *,
    wave_item_id: str,
    portfolio_id: str,
    state: WaveItemState,
    reason_codes: list[str] | None = None,
    diagnostics: dict[str, object] | None = None,
) -> DpmRebalanceWaveItem:
    return DpmRebalanceWaveItem(
        wave_item_id=wave_item_id,
        portfolio_id=portfolio_id,
        state=state,
        reason_codes=reason_codes or [],
        diagnostics=diagnostics or {},
    )


def _save_supportability_wave(
    repository: InMemoryDpmWaveRepository,
    *,
    wave_id: str,
    state: WaveState,
    items: list[DpmRebalanceWaveItem],
) -> None:
    state_counts: dict[str, int] = {}
    for item in items:
        state_counts[item.state] = state_counts.get(item.state, 0) + 1
    repository.save_wave(
        wave=DpmRebalanceWave(
            wave_id=wave_id,
            state=state,
            trigger=DpmWaveTrigger(
                trigger_type="EXPLICIT_PORTFOLIO_LIST",
                trigger_id=f"supportability-{wave_id}",
                rationale="Exercise operator supportability diagnostics.",
            ),
            as_of_date="2026-05-03",
            created_by="pm_001",
            correlation_id=f"corr-{wave_id}",
            items=items,
            aggregate_metrics=DpmWaveAggregateMetrics(
                item_count=len(items),
                state_counts=state_counts,
                ready_item_count=sum(
                    1
                    for item in items
                    if item.state
                    in {
                        "SOURCE_READY",
                        "SIMULATED",
                        "SELECTED",
                        "PROOF_PACK_READY",
                        "APPROVED",
                        "STAGED",
                        "HANDOFF_READY",
                    }
                ),
                blocked_item_count=sum(
                    1 for item in items if item.state in {"SOURCE_BLOCKED", "SIMULATION_BLOCKED"}
                ),
                review_required_item_count=sum(
                    1 for item in items if item.state == "REVIEW_REQUIRED"
                ),
                source_degraded_item_count=sum(
                    1 for item in items if item.state == "SOURCE_DEGRADED"
                ),
            ),
        ),
        idempotency_key=None,
        request_hash=None,
    )


class _SaveConflictWaveRepository(InMemoryDpmWaveRepository):
    def save_wave(
        self,
        *,
        wave: DpmRebalanceWave,
        idempotency_key: str | None,
        request_hash: str | None,
    ) -> None:
        raise DpmWaveAlreadyExistsError("duplicate durable wave id")


class _VersionConflictWaveRepository(InMemoryDpmWaveRepository):
    def update_wave(self, *, wave: DpmRebalanceWave, expected_version: int) -> None:
        raise DpmWaveVersionConflictError("stale durable wave version")


def _save_wave_for_service(
    repository: InMemoryDpmWaveRepository,
    *,
    wave_id: str,
    state: WaveState,
    item_state: WaveItemState,
    diagnostics: dict[str, object] | None = None,
) -> DpmRebalanceWave:
    item = DpmRebalanceWaveItem(
        wave_item_id=f"dwi_{wave_id}",
        portfolio_id=PORTFOLIO_ID,
        mandate_id=MANDATE_ID,
        model_portfolio_id="MODEL_PB_SG_GLOBAL_BAL_DPM",
        state=item_state,
        diagnostics=diagnostics or {},
    )
    wave = DpmRebalanceWave(
        wave_id=wave_id,
        state=state,
        trigger=DpmWaveTrigger(
            trigger_type="EXPLICIT_PORTFOLIO_LIST",
            trigger_id=f"manual-{wave_id}",
            rationale="Exercise governed service edge behavior.",
        ),
        as_of_date="2026-05-03",
        created_by="pm_001",
        correlation_id=f"corr-{wave_id}",
        items=[item],
        aggregate_metrics=DpmWaveAggregateMetrics(
            item_count=1,
            state_counts={item.state: 1},
            ready_item_count=1 if item.state in {"SOURCE_READY", "SIMULATED", "SELECTED"} else 0,
            blocked_item_count=1 if item.state in {"SOURCE_BLOCKED", "SIMULATION_BLOCKED"} else 0,
            review_required_item_count=1 if item.state == "REVIEW_REQUIRED" else 0,
            source_degraded_item_count=1 if item.state == "SOURCE_DEGRADED" else 0,
        ),
    )
    repository.save_wave(wave=wave, idempotency_key=None, request_hash=None)
    return wave


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
    assert payload["supportability"]["supportability_state"] == "blocked"
    assert payload["supportability"]["reason"] == "wave_blocked_items"
    assert payload["supportability"]["issue_counts"] == {"critical": 1, "warning": 0, "info": 1}
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
    assert first_payload["supportability"]["supportability_state"] == "blocked"
    assert first_payload["supportability"]["reason"] == "wave_blocked_items"
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


def test_wave_cancel_is_durable_idempotent_and_rejects_handoff_ready_waves() -> None:
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
            headers={"Idempotency-Key": "idem-wave-cancel-created"},
        )
        wave_id = created.json()["wave"]["wave_id"]
        cancelled = client.post(
            f"/api/v1/rebalance/waves/{wave_id}/cancel",
            json={
                "actor_id": "pm_001",
                "reason_code": "PM_CANCELLED_BEFORE_REVIEW",
                "comment": "Cancelled before downstream work.",
            },
            headers={"X-Correlation-Id": "corr-wave-cancel-created"},
        )
        replay = client.post(
            f"/api/v1/rebalance/waves/{wave_id}/cancel",
            json={"actor_id": "pm_001", "reason_code": "PM_CANCELLED_BEFORE_REVIEW"},
        )

        handoff_ready = client.post(
            "/api/v1/rebalance/waves",
            json={**_request(), "portfolios": [{"portfolio_id": PORTFOLIO_ID}]},
            headers={"Idempotency-Key": "idem-wave-cancel-handoff"},
        )
        handoff_wave_id = handoff_ready.json()["wave"]["wave_id"]
        checked = client.post(
            f"/api/v1/rebalance/waves/{handoff_wave_id}/source-check",
            json={"actor_id": "pm_001"},
        )
        wave_item_id = checked.json()["wave"]["items"][0]["wave_item_id"]
        client.post(
            f"/api/v1/rebalance/waves/{handoff_wave_id}/simulate",
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
            f"/api/v1/rebalance/waves/{handoff_wave_id}/items/{wave_item_id}/select",
            json={
                "alternative_id": "alt_min_turnover",
                "actor_id": "pm_001",
                "reason_code": "LOWER_TURNOVER_WITH_ACCEPTABLE_DRIFT",
            },
        )
        client.post(
            f"/api/v1/rebalance/waves/{handoff_wave_id}/approve",
            json={"actor_id": "pm_001", "reason_code": "PROOF_PACK_REVIEWED"},
        )
        client.post(
            f"/api/v1/rebalance/waves/{handoff_wave_id}/stage",
            json={"actor_id": "ops_001", "reason_code": "READY_FOR_OPERATIONS_REVIEW"},
        )
        client.post(
            f"/api/v1/rebalance/waves/{handoff_wave_id}/handoff",
            json={"actor_id": "ops_001", "reason_code": "OPERATIONS_PACKAGE_PREPARED"},
        )
        invalid = client.post(
            f"/api/v1/rebalance/waves/{handoff_wave_id}/cancel",
            json={"actor_id": "pm_001", "reason_code": "PM_CANCELLED_TOO_LATE"},
        )

    assert cancelled.status_code == 200
    payload = cancelled.json()
    assert payload["wave"]["state"] == "CANCELLED"
    assert payload["wave"]["items"][0]["state"] == "EXCLUDED"
    assert payload["wave"]["items"][0]["diagnostics"]["cancel_actor_id"] == "pm_001"
    assert payload["wave"]["items"][0]["diagnostics"]["external_execution_claimed"] is False
    assert payload["wave"]["events"][-1]["reason_code"] == "WAVE_CANCELLED"
    assert replay.json()["idempotent_replay"] is True
    persisted = wave_repository.get_wave(wave_id=wave_id)
    assert persisted is not None
    assert persisted.state == "CANCELLED"
    assert invalid.status_code == 422
    assert invalid.json()["detail"]["code"] == "DPM_WAVE_CANCEL_INVALID_STATE"


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


def test_wave_services_translate_durable_write_conflicts_to_governed_errors() -> None:
    mandate_repository = InMemoryDpmMandateRepository()
    ready_twin = _twin()
    mandate_repository.save_mandate_snapshot(ready_twin)
    _save_ready_health(mandate_repository, ready_twin)

    create_conflict_repository = _SaveConflictWaveRepository()
    with pytest.raises(wave_service.DpmWaveValidationError) as create_exc:
        wave_service.create_wave(
            trigger_type="EXPLICIT_PORTFOLIO_LIST",
            trigger_id="manual-conflict-create",
            rationale="Exercise durable create conflict handling.",
            as_of_date="2026-05-03",
            actor_id="pm_001",
            correlation_id="corr-conflict-create",
            portfolios=[{"portfolio_id": PORTFOLIO_ID}],
            idempotency_key="idem-conflict-create",
            mandate_repository=mandate_repository,
            wave_repository=create_conflict_repository,
        )
    assert create_exc.value.code == "WAVE_CREATE_CONFLICT"

    source_repository = _VersionConflictWaveRepository()
    _save_wave_for_service(
        source_repository,
        wave_id="dwv_conflict_source",
        state="CREATED",
        item_state="CANDIDATE",
    )
    with pytest.raises(wave_service.DpmWaveValidationError) as source_exc:
        wave_service.source_check_wave(
            wave_id="dwv_conflict_source",
            actor_id="pm_001",
            correlation_id="corr-conflict-source",
            mandate_repository=mandate_repository,
            wave_repository=source_repository,
        )
    assert source_exc.value.code == "DPM_WAVE_VERSION_CONFLICT"

    simulate_repository = _VersionConflictWaveRepository()
    simulate_wave = _save_wave_for_service(
        simulate_repository,
        wave_id="dwv_conflict_simulate",
        state="SOURCE_CHECKED",
        item_state="SOURCE_READY",
    )
    with pytest.raises(wave_service.DpmWaveValidationError) as simulate_exc:
        wave_service.simulate_wave(
            wave_id=simulate_wave.wave_id,
            actor_id="pm_001",
            correlation_id="corr-conflict-simulate",
            item_inputs={simulate_wave.items[0].wave_item_id: _rebalance_request(PORTFOLIO_ID)},
            methods=None,
            construction_repository=InMemoryConstructionRepository(),
            run_service=_run_service(),
            wave_repository=simulate_repository,
        )
    assert simulate_exc.value.code == "DPM_WAVE_VERSION_CONFLICT"

    approval_repository = _VersionConflictWaveRepository()
    _save_wave_for_service(
        approval_repository,
        wave_id="dwv_conflict_approve",
        state="SIMULATED",
        item_state="SELECTED",
    )
    stage_repository = _VersionConflictWaveRepository()
    _save_wave_for_service(
        stage_repository,
        wave_id="dwv_conflict_stage",
        state="APPROVED",
        item_state="APPROVED",
    )
    handoff_repository = _VersionConflictWaveRepository()
    _save_wave_for_service(
        handoff_repository,
        wave_id="dwv_conflict_handoff",
        state="STAGED",
        item_state="STAGED",
    )
    cancel_repository = _VersionConflictWaveRepository()
    _save_wave_for_service(
        cancel_repository,
        wave_id="dwv_conflict_cancel",
        state="CREATED",
        item_state="CANDIDATE",
    )

    command_cases = [
        (
            wave_service.approve_wave,
            {"wave_id": "dwv_conflict_approve", "wave_repository": approval_repository},
        ),
        (
            wave_service.stage_wave,
            {"wave_id": "dwv_conflict_stage", "wave_repository": stage_repository},
        ),
        (
            wave_service.handoff_wave,
            {"wave_id": "dwv_conflict_handoff", "wave_repository": handoff_repository},
        ),
        (
            wave_service.cancel_wave,
            {"wave_id": "dwv_conflict_cancel", "wave_repository": cancel_repository},
        ),
    ]
    for command, extra_kwargs in command_cases:
        with pytest.raises(wave_service.DpmWaveValidationError) as exc:
            command(
                actor_id="pm_001",
                reason_code="CONFLICT_TEST",
                comment="Conflict test comment.",
                correlation_id="corr-conflict-command",
                **extra_kwargs,
            )
        assert exc.value.code == "DPM_WAVE_VERSION_CONFLICT"


def test_wave_selection_translates_durable_write_conflict_to_governed_error() -> None:
    construction_repository = InMemoryConstructionRepository()
    normal_repository = InMemoryDpmWaveRepository()
    source_checked = _save_wave_for_service(
        normal_repository,
        wave_id="dwv_conflict_select",
        state="SOURCE_CHECKED",
        item_state="SOURCE_READY",
    )
    wave_service.simulate_wave(
        wave_id=source_checked.wave_id,
        actor_id="pm_001",
        correlation_id="corr-conflict-select-simulate",
        item_inputs={
            source_checked.items[0].wave_item_id: RebalanceRequest.model_validate(
                _rebalance_request(PORTFOLIO_ID)
            )
        },
        methods=None,
        construction_repository=construction_repository,
        run_service=_run_service(),
        wave_repository=normal_repository,
    )
    simulated = normal_repository.get_wave(wave_id=source_checked.wave_id)
    assert simulated is not None
    assert simulated.items[0].alternative_set_id is not None

    conflict_repository = _VersionConflictWaveRepository()
    conflict_repository.save_wave(wave=simulated, idempotency_key=None, request_hash=None)

    with pytest.raises(wave_service.DpmWaveValidationError) as exc:
        wave_service.select_wave_item_alternative(
            wave_id=simulated.wave_id,
            wave_item_id=simulated.items[0].wave_item_id,
            alternative_id="alt_min_turnover",
            actor_id="pm_001",
            reason_code="CONFLICT_TEST",
            comment="Selection conflict.",
            correlation_id="corr-conflict-select",
            generate_proof_pack=False,
            construction_repository=construction_repository,
            proof_pack_repository=InMemoryDpmProofPackRepository(),
            mandate_repository=InMemoryDpmMandateRepository(),
            run_service=_run_service(),
            wave_repository=conflict_repository,
        )

    assert exc.value.code == "DPM_WAVE_VERSION_CONFLICT"


def test_wave_services_reject_no_eligible_approval_stage_and_handoff() -> None:
    cases = [
        (
            wave_service.approve_wave,
            "dwv_no_approval",
            "SIMULATED",
            "SOURCE_BLOCKED",
            "DPM_WAVE_APPROVAL_NO_ELIGIBLE_ITEMS",
        ),
        (
            wave_service.stage_wave,
            "dwv_no_stage",
            "APPROVED",
            "SOURCE_BLOCKED",
            "DPM_WAVE_STAGE_NO_ELIGIBLE_ITEMS",
        ),
        (
            wave_service.handoff_wave,
            "dwv_no_handoff",
            "STAGED",
            "EXCLUDED",
            "DPM_WAVE_HANDOFF_NO_ELIGIBLE_ITEMS",
        ),
    ]
    for command, wave_id, wave_state, item_state, expected_code in cases:
        repository = InMemoryDpmWaveRepository()
        _save_wave_for_service(
            repository,
            wave_id=wave_id,
            state=wave_state,
            item_state=item_state,
        )

        with pytest.raises(wave_service.DpmWaveValidationError) as exc:
            command(
                wave_id=wave_id,
                actor_id="pm_001",
                reason_code="NO_ELIGIBLE_ITEM",
                comment=None,
                correlation_id=f"corr-{wave_id}",
                wave_repository=repository,
            )

        assert exc.value.code == expected_code


def test_wave_api_maps_missing_and_create_conflict_edges() -> None:
    with _client(InMemoryDpmMandateRepository(), _SaveConflictWaveRepository()) as client:
        create_conflict = client.post(
            "/api/v1/rebalance/waves",
            json={**_request(), "portfolios": [{"portfolio_id": PORTFOLIO_ID}]},
            headers={"Idempotency-Key": "idem-router-create-conflict"},
        )

    assert create_conflict.status_code == 409
    assert create_conflict.json()["detail"]["code"] == "WAVE_CREATE_CONFLICT"

    with _client(
        InMemoryDpmMandateRepository(),
        InMemoryDpmWaveRepository(),
        InMemoryConstructionRepository(),
        InMemoryDpmProofPackRepository(),
        _run_service(),
    ) as client:
        missing_items = client.get("/api/v1/rebalance/waves/dwv_missing/items")
        missing_simulate = client.post(
            "/api/v1/rebalance/waves/dwv_missing/simulate",
            json={
                "actor_id": "pm_001",
                "item_inputs": [
                    {
                        "portfolio_id": PORTFOLIO_ID,
                        "stateless_input": _rebalance_request(PORTFOLIO_ID),
                    }
                ],
            },
        )
        missing_approve = client.post(
            "/api/v1/rebalance/waves/dwv_missing/approve",
            json={"actor_id": "pm_001", "reason_code": "MISSING"},
        )
        missing_stage = client.post(
            "/api/v1/rebalance/waves/dwv_missing/stage",
            json={"actor_id": "ops_001", "reason_code": "MISSING"},
        )
        missing_handoff = client.post(
            "/api/v1/rebalance/waves/dwv_missing/handoff",
            json={"actor_id": "ops_001", "reason_code": "MISSING"},
        )
        missing_cancel = client.post(
            "/api/v1/rebalance/waves/dwv_missing/cancel",
            json={"actor_id": "pm_001", "reason_code": "MISSING"},
        )
        missing_proof_pack = client.get("/api/v1/rebalance/waves/dwv_missing/proof-pack")

    responses = [
        missing_items,
        missing_simulate,
        missing_approve,
        missing_stage,
        missing_handoff,
        missing_cancel,
        missing_proof_pack,
    ]
    assert [response.status_code for response in responses] == [404] * len(responses)
    assert {response.json()["detail"]["code"] for response in responses} == {"DPM_WAVE_NOT_FOUND"}


def test_wave_supportability_filters_and_private_helper_edges() -> None:
    repository = InMemoryDpmWaveRepository()
    _save_supportability_wave(
        repository,
        wave_id="dwv_filter_ready",
        state="HANDOFF_READY",
        items=[
            _wave_item(
                wave_item_id="dwi_filter_ready",
                portfolio_id="PB_SG_FILTER_READY",
                state="HANDOFF_READY",
            )
        ],
    )
    _save_supportability_wave(
        repository,
        wave_id="dwv_filter_blocked",
        state="SOURCE_CHECKED",
        items=[
            _wave_item(
                wave_item_id="dwi_filter_blocked",
                portfolio_id="PB_SG_FILTER_BLOCKED",
                state="SIMULATION_BLOCKED",
            )
        ],
    )
    blocked = wave_service.wave_supportability(
        wave_id="dwv_filter_blocked",
        wave_repository=repository,
    )
    excluded_issue = wave_service._supportability_issue(  # noqa: SLF001
        wave_id="dwv_filter_excluded",
        item=_wave_item(
            wave_item_id="dwi_excluded",
            portfolio_id="PB_SG_EXCLUDED",
            state="EXCLUDED",
        ),
        item_index=0,
    )

    ready_search = wave_service.search_waves(
        wave_repository=repository,
        supportability_state="ready",
    )
    source_refs = wave_service._source_refs_from_portfolio(  # noqa: SLF001
        {"portfolio_id": PORTFOLIO_ID, "source_refs": "not-a-list"}
    )
    optional_text = wave_service._optional_str(123)  # noqa: SLF001

    assert [item["wave_id"] for item in ready_search] == ["dwv_filter_ready"]
    assert blocked["issues"][0]["source_owner"] == "lotus-manage-construction"
    assert excluded_issue is None
    assert source_refs == []
    assert optional_text == "123"


def test_wave_append_event_rejects_identity_and_state_mismatches() -> None:
    wave = DpmRebalanceWave(
        wave_id="dwv_append_edge",
        state="SIMULATED",
        trigger=DpmWaveTrigger(
            trigger_type="EXPLICIT_PORTFOLIO_LIST",
            trigger_id="manual-append-edge",
            rationale="Exercise item-level event append guards.",
        ),
        as_of_date="2026-05-03",
        created_by="pm_001",
        correlation_id="corr-append-edge",
        items=[],
        aggregate_metrics=DpmWaveAggregateMetrics(
            item_count=0,
            state_counts={},
            ready_item_count=0,
            blocked_item_count=0,
            review_required_item_count=0,
            source_degraded_item_count=0,
        ),
    )
    event = wave_service._event(  # noqa: SLF001
        wave_id=wave.wave_id,
        from_state=wave.state,
        to_state=wave.state,
        actor_id="pm_001",
        correlation_id="corr-append-edge",
        reason_code="EDGE_EVENT",
        event_type="ITEM_SELECTION",
        metadata={},
    )

    with pytest.raises(wave_service.DpmWaveValidationError) as wave_exc:
        wave_service._append_event(  # noqa: SLF001
            wave=wave,
            event=event.model_copy(update={"wave_id": "dwv_other"}),
        )
    assert wave_exc.value.code == "DPM_WAVE_EVENT_WAVE_MISMATCH"

    with pytest.raises(wave_service.DpmWaveValidationError) as state_exc:
        wave_service._append_event(  # noqa: SLF001
            wave=wave,
            event=event.model_copy(update={"to_state": "APPROVED"}),
        )
    assert state_exc.value.code == "DPM_WAVE_EVENT_STATE_MISMATCH"


def test_wave_supportability_reports_product_safe_operator_diagnostics() -> None:
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
            headers={"Idempotency-Key": "idem-wave-supportability"},
        )
        wave_id = created.json()["wave"]["wave_id"]
        client.post(
            f"/api/v1/rebalance/waves/{wave_id}/source-check",
            json={"actor_id": "pm_001"},
        )
        supportability = client.get(f"/api/v1/rebalance/waves/{wave_id}/supportability")
        missing = client.get("/api/v1/rebalance/waves/dwv_missing/supportability")
        metrics = client.get("/metrics")

    assert supportability.status_code == 200
    payload = supportability.json()
    assert payload["supportability_state"] == "blocked"
    assert payload["reason"] == "wave_blocked_items"
    assert payload["issue_counts"]["critical"] == 1
    assert payload["issue_counts"]["info"] == 1
    assert payload["issues"][0]["support_ref"].startswith(f"wave:{wave_id}:item:")
    assert {issue["source_owner"] for issue in payload["issues"]} >= {"lotus-manage"}
    assert "REFRESH_MANDATE_DIGITAL_TWIN" in payload["operator_actions"]
    payload_text = supportability.text
    assert PORTFOLIO_ID not in payload_text
    assert "PB_SG_CALLER_REF_ONLY_003" not in payload_text
    assert "source_refs" not in payload

    assert missing.status_code == 404
    assert missing.json()["detail"]["code"] == "DPM_WAVE_NOT_FOUND"
    assert metrics.status_code == 200
    assert "lotus_manage_wave_supportability_total" in metrics.text
    assert 'surface="rebalance/waves/supportability"' in metrics.text
    assert 'supportability_state="blocked"' in metrics.text
    assert 'reason="wave_blocked_items"' in metrics.text
    assert PORTFOLIO_ID not in metrics.text
    assert "PB_SG_CALLER_REF_ONLY_003" not in metrics.text


def test_wave_supportability_service_reports_ready_and_info_only_postures() -> None:
    repository = InMemoryDpmWaveRepository()
    _save_supportability_wave(
        repository,
        wave_id="dwv_support_ready",
        state="HANDOFF_READY",
        items=[
            _wave_item(
                wave_item_id="dwi_handoff_ready",
                portfolio_id="PB_SG_CONFIDENTIAL_READY",
                state="HANDOFF_READY",
            )
        ],
    )
    _save_supportability_wave(
        repository,
        wave_id="dwv_support_info",
        state="CREATED",
        items=[
            _wave_item(
                wave_item_id="dwi_candidate",
                portfolio_id="PB_SG_CONFIDENTIAL_CANDIDATE",
                state="CANDIDATE",
            ),
            _wave_item(
                wave_item_id="dwi_source_ready",
                portfolio_id="PB_SG_CONFIDENTIAL_SOURCE_READY",
                state="SOURCE_READY",
            ),
        ],
    )

    ready = wave_service.wave_supportability(
        wave_id="dwv_support_ready",
        wave_repository=repository,
    )
    info_only = wave_service.wave_supportability(
        wave_id="dwv_support_info",
        wave_repository=repository,
    )

    assert ready["supportability_state"] == "ready"
    assert ready["reason"] == "wave_supportability_ready"
    assert ready["issues"] == []
    assert ready["operator_actions"] == ["CONTINUE_GOVERNED_WAVE_WORKFLOW"]

    assert info_only["supportability_state"] == "ready"
    assert info_only["issue_counts"] == {"critical": 0, "warning": 0, "info": 2}
    info_issues = cast(list[dict[str, object]], info_only["issues"])
    assert [issue["reason_codes"] for issue in info_issues] == [
        ["SOURCE_CHECK_PENDING"],
        ["SIMULATION_PENDING"],
    ]
    assert info_only["operator_actions"] == ["CONTINUE_GOVERNED_WAVE_WORKFLOW"]
    assert "PB_SG_CONFIDENTIAL" not in str(info_only)


def test_wave_supportability_service_reports_degraded_and_blocked_actions() -> None:
    repository = InMemoryDpmWaveRepository()
    _save_supportability_wave(
        repository,
        wave_id="dwv_support_degraded",
        state="SIMULATED",
        items=[
            _wave_item(
                wave_item_id="dwi_source_degraded",
                portfolio_id="PB_SG_CONFIDENTIAL_DEGRADED",
                state="SOURCE_DEGRADED",
            ),
            _wave_item(
                wave_item_id="dwi_review",
                portfolio_id="PB_SG_CONFIDENTIAL_REVIEW",
                state="REVIEW_REQUIRED",
            ),
            _wave_item(
                wave_item_id="dwi_selected_degraded",
                portfolio_id="PB_SG_CONFIDENTIAL_PROOF",
                state="PROOF_PACK_READY",
                diagnostics={"proof_pack_state": "DEGRADED"},
            ),
        ],
    )
    _save_supportability_wave(
        repository,
        wave_id="dwv_support_blocked",
        state="SIMULATION_FAILED",
        items=[
            _wave_item(
                wave_item_id="dwi_source_blocked",
                portfolio_id="PB_SG_CONFIDENTIAL_SOURCE_BLOCKED",
                state="SOURCE_BLOCKED",
            ),
            _wave_item(
                wave_item_id="dwi_simulation_blocked",
                portfolio_id="PB_SG_CONFIDENTIAL_SIM_BLOCKED",
                state="SIMULATION_BLOCKED",
                diagnostics={
                    "source_owner": "lotus-risk",
                    "required_action": "REFRESH_RISK_INPUTS",
                },
            ),
        ],
    )

    degraded = wave_service.wave_supportability(
        wave_id="dwv_support_degraded",
        wave_repository=repository,
    )
    blocked = wave_service.wave_supportability(
        wave_id="dwv_support_blocked",
        wave_repository=repository,
    )

    assert degraded["supportability_state"] == "degraded"
    assert degraded["reason"] == "wave_degraded_items"
    assert degraded["issue_counts"] == {"critical": 0, "warning": 3, "info": 0}
    assert degraded["operator_actions"] == [
        "PERFORM_HUMAN_REVIEW",
        "REFRESH_SOURCE_EVIDENCE",
        "REVIEW_DEGRADED_PROOF_PACK",
    ]
    degraded_issues = cast(list[dict[str, object]], degraded["issues"])
    blocked_issues = cast(list[dict[str, object]], blocked["issues"])
    assert {issue["source_owner"] for issue in degraded_issues} == {
        "lotus-manage",
        "lotus-manage-proof-pack",
    }
    assert "PB_SG_CONFIDENTIAL" not in str(degraded)

    assert blocked["supportability_state"] == "blocked"
    assert blocked["reason"] == "wave_blocked_items"
    assert blocked["issue_counts"] == {"critical": 2, "warning": 0, "info": 0}
    assert blocked["operator_actions"] == ["REFRESH_RISK_INPUTS", "REPAIR_SOURCE_DATA"]
    assert blocked_issues[1]["source_owner"] == "lotus-risk"
    assert blocked_issues[1]["remediation_route"] == "REFRESH_RISK_INPUTS"
    assert "PB_SG_CONFIDENTIAL" not in str(blocked)


def test_wave_simulation_rollup_treats_degraded_and_review_items_as_partial() -> None:
    result_state = wave_service._simulation_result_state(  # noqa: SLF001
        [
            _wave_item(
                wave_item_id="dwi_simulated",
                portfolio_id="PB_SG_SIMULATED",
                state="SIMULATED",
            ),
            _wave_item(
                wave_item_id="dwi_degraded",
                portfolio_id="PB_SG_DEGRADED",
                state="SOURCE_DEGRADED",
            ),
            _wave_item(
                wave_item_id="dwi_review",
                portfolio_id="PB_SG_REVIEW",
                state="REVIEW_REQUIRED",
            ),
        ]
    )

    assert result_state == "PARTIALLY_SIMULATED"


def test_wave_read_apis_return_durable_search_detail_items_and_proof_pack_posture() -> None:
    mandate_repository = InMemoryDpmMandateRepository()
    wave_repository = InMemoryDpmWaveRepository()
    wave = DpmRebalanceWave(
        wave_id="dwv_read_001",
        state="HANDOFF_READY",
        trigger=DpmWaveTrigger(
            trigger_type="EXPLICIT_PORTFOLIO_LIST",
            trigger_id="manual-wave-read-001",
            rationale="Retrieve a completed wave for command-center evidence.",
        ),
        as_of_date="2026-05-03",
        created_by="pm_001",
        correlation_id="corr-wave-read-001",
        version=7,
        items=[
            DpmRebalanceWaveItem(
                wave_item_id="dwi_read_ready",
                portfolio_id=PORTFOLIO_ID,
                state="HANDOFF_READY",
                selected_alternative_id="alt_min_turnover",
                proof_pack_id="dpp_read_ready",
                reason_codes=[
                    "CONSTRUCTION_ALTERNATIVE_SELECTED",
                    "PROOF_PACK_READY",
                    "WAVE_ITEM_HANDOFF_READY",
                ],
                diagnostics={
                    "proof_pack_state": "READY",
                    "external_execution_claimed": False,
                },
            )
        ],
        aggregate_metrics=DpmWaveAggregateMetrics(
            item_count=1,
            state_counts={"HANDOFF_READY": 1},
            ready_item_count=1,
            blocked_item_count=0,
            review_required_item_count=0,
            source_degraded_item_count=0,
        ),
        handoff_refs=[
            DpmWaveHandoffRef(
                handoff_ref_id="dwh_read_001",
                wave_id="dwv_read_001",
                item_ids=["dwi_read_ready"],
                actor_id="ops_001",
                reason_code="READY_FOR_OPERATIONS_REVIEW",
                correlation_id="corr-wave-read-handoff",
                external_execution_claimed=False,
                content_hash="sha256:read-handoff",
            )
        ],
    )
    wave_repository.save_wave(wave=wave, idempotency_key=None, request_hash=None)

    with _client(mandate_repository, wave_repository) as client:
        search = client.get(
            "/api/v1/rebalance/waves",
            params={
                "state": "HANDOFF_READY",
                "trigger_type": "EXPLICIT_PORTFOLIO_LIST",
                "as_of_date": "2026-05-03",
                "supportability_state": "ready",
            },
        )
        detail = client.get("/api/v1/rebalance/waves/dwv_read_001")
        items = client.get("/api/v1/rebalance/waves/dwv_read_001/items")
        proof_pack = client.get("/api/v1/rebalance/waves/dwv_read_001/proof-pack")
        missing = client.get("/api/v1/rebalance/waves/dwv_missing")

    assert search.status_code == 200
    search_payload = search.json()
    assert search_payload["returned_count"] == 1
    assert search_payload["items"][0]["wave_id"] == "dwv_read_001"
    assert search_payload["items"][0]["supportability_state"] == "ready"
    assert search_payload["items"][0]["aggregate_metrics"]["state_counts"] == {"HANDOFF_READY": 1}

    assert detail.status_code == 200
    detail_payload = detail.json()
    assert detail_payload["wave"]["wave_id"] == "dwv_read_001"
    assert detail_payload["supportability"]["supportability_state"] == "ready"
    assert detail_payload["proof_pack_posture"]["linked_item_count"] == 1

    assert items.status_code == 200
    items_payload = items.json()
    assert items_payload["items"][0]["proof_pack_id"] == "dpp_read_ready"
    assert items_payload["aggregate_metrics"]["ready_item_count"] == 1

    assert proof_pack.status_code == 200
    proof_payload = proof_pack.json()
    assert proof_payload["ready_proof_pack_count"] == 1
    assert proof_payload["external_execution_claimed"] is False
    assert proof_payload["handoff_refs"][0]["handoff_ref_id"] == "dwh_read_001"

    assert missing.status_code == 404
    assert missing.json()["detail"]["code"] == "DPM_WAVE_NOT_FOUND"


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
    search = openapi["paths"]["/api/v1/rebalance/waves"]["get"]
    detail = openapi["paths"]["/api/v1/rebalance/waves/{wave_id}"]["get"]
    items = openapi["paths"]["/api/v1/rebalance/waves/{wave_id}/items"]["get"]
    proof_pack = openapi["paths"]["/api/v1/rebalance/waves/{wave_id}/proof-pack"]["get"]
    source_check = openapi["paths"]["/api/v1/rebalance/waves/{wave_id}/source-check"]["post"]
    approve = openapi["paths"]["/api/v1/rebalance/waves/{wave_id}/approve"]["post"]
    stage = openapi["paths"]["/api/v1/rebalance/waves/{wave_id}/stage"]["post"]
    handoff = openapi["paths"]["/api/v1/rebalance/waves/{wave_id}/handoff"]["post"]
    cancel = openapi["paths"]["/api/v1/rebalance/waves/{wave_id}/cancel"]["post"]
    supportability = openapi["paths"]["/api/v1/rebalance/waves/{wave_id}/supportability"]["get"]
    assert preview["tags"] == ["lotus-manage Rebalance Waves"]
    assert create["tags"] == ["lotus-manage Rebalance Waves"]
    assert search["tags"] == ["lotus-manage Rebalance Waves"]
    assert detail["tags"] == ["lotus-manage Rebalance Waves"]
    assert items["tags"] == ["lotus-manage Rebalance Waves"]
    assert proof_pack["tags"] == ["lotus-manage Rebalance Waves"]
    assert source_check["tags"] == ["lotus-manage Rebalance Waves"]
    assert approve["tags"] == ["lotus-manage Rebalance Waves"]
    assert stage["tags"] == ["lotus-manage Rebalance Waves"]
    assert handoff["tags"] == ["lotus-manage Rebalance Waves"]
    assert cancel["tags"] == ["lotus-manage Rebalance Waves"]
    assert supportability["tags"] == ["lotus-manage Rebalance Waves"]
    assert preview["responses"]["200"]["content"]["application/json"]["example"]["durable"] is False
    assert create["responses"]["201"]["content"]["application/json"]["example"]["durable"] is True
    assert (
        source_check["responses"]["200"]["content"]["application/json"]["example"]["wave"]["state"]
        == "SOURCE_CHECKED"
    )
    assert "422" in preview["responses"]
    assert "409" in create["responses"]
    assert "durable RFC-0041 waves" in search["description"]
    assert "does not regenerate downstream" in detail["description"]
    assert "without UI-side recomputation" in items["description"]
    assert "does not rebuild proof packs" in proof_pack["description"]
    assert "404" in source_check["responses"]
    assert "409" in source_check["responses"]
    assert "422" in source_check["responses"]
    assert "does not claim external order execution" in stage["description"]
    assert "external_execution_claimed=false" in handoff["description"]
    assert "does not cancel external orders" in cancel["description"]
    assert "excludes portfolio identifiers" in supportability["description"]
