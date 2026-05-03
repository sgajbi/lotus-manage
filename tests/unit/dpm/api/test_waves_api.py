from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient

from src.api.dependencies import get_mandate_repository, get_wave_repository
from src.api.main import app
from src.core.mandates import (
    DpmMandateConstraintSet,
    DpmMandateDigitalTwin,
    DpmMandateReviewPolicy,
)
from src.infrastructure.mandates import InMemoryDpmMandateRepository
from src.infrastructure.waves import InMemoryDpmWaveRepository


MANDATE_ID = "MANDATE_PB_SG_GLOBAL_BAL_001"
PORTFOLIO_ID = "PB_SG_GLOBAL_BAL_001"


def _twin() -> DpmMandateDigitalTwin:
    return DpmMandateDigitalTwin(
        mandate_id=MANDATE_ID,
        portfolio_id=PORTFOLIO_ID,
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
    assert preview["tags"] == ["lotus-manage Rebalance Waves"]
    assert create["tags"] == ["lotus-manage Rebalance Waves"]
    assert preview["responses"]["200"]["content"]["application/json"]["example"]["durable"] is False
    assert create["responses"]["201"]["content"]["application/json"]["example"]["durable"] is True
    assert "422" in preview["responses"]
    assert "409" in create["responses"]
