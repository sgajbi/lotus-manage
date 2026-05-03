from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient

from src.api.dependencies import get_mandate_repository, get_wave_repository
from src.api.main import app
from src.core.mandates import (
    DpmMandateConstraintSet,
    DpmMandateDigitalTwin,
    DpmMandateHealthInput,
    DpmMandateReviewPolicy,
    DpmSourceProductLineage,
    calculate_mandate_health,
)
from src.infrastructure.mandates import InMemoryDpmMandateRepository
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


def _client(
    mandate_repository: InMemoryDpmMandateRepository,
    wave_repository: InMemoryDpmWaveRepository,
) -> TestClient:
    app.dependency_overrides[get_mandate_repository] = lambda: mandate_repository
    app.dependency_overrides[get_wave_repository] = lambda: wave_repository
    app.openapi_schema = None
    return TestClient(app)


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
    assert preview["tags"] == ["lotus-manage Rebalance Waves"]
    assert create["tags"] == ["lotus-manage Rebalance Waves"]
    assert source_check["tags"] == ["lotus-manage Rebalance Waves"]
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
