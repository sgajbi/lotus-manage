from fastapi.testclient import TestClient

from src.api.dependencies import get_construction_repository, get_db_session
from src.api.main import app
import src.api.services.rebalance_simulation_service as rebalance_service
from src.core.dpm_source_context import DpmCoreExecutionContext
from src.infrastructure.construction import InMemoryConstructionRepository
from tests.shared.factories import valid_api_payload


async def override_get_db_session():
    yield None


def _client(repository: InMemoryConstructionRepository):
    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_construction_repository] = lambda: repository
    return TestClient(app)


def _payload() -> dict:
    payload = valid_api_payload()
    payload["portfolio_snapshot"]["positions"] = [{"instrument_id": "EQ_1", "quantity": "50"}]
    payload["portfolio_snapshot"]["cash_balances"] = [{"currency": "SGD", "amount": "5000.00"}]
    payload["model_portfolio"]["targets"] = [{"instrument_id": "EQ_1", "weight": "0.50"}]
    return {"input_mode": "stateless", "stateless_input": payload}


def _stateful_input_payload() -> dict[str, object]:
    return {
        "portfolio_id": "PB_SG_GLOBAL_BAL_001",
        "as_of": "2026-05-03",
        "mandate_id": "MANDATE_PB_SG_GLOBAL_BAL_001",
        "model_portfolio_id": "MODEL_PB_SG_GLOBAL_BAL_DPM",
        "tenant_id": "tenant_001",
        "booking_center_code": "SG",
    }


def _core_execution_context(*, supportability_state: str = "DEGRADED") -> DpmCoreExecutionContext:
    return DpmCoreExecutionContext.model_validate(
        {
            "portfolio_snapshot": {
                "snapshot_id": "core-pf-snap-001",
                "portfolio_id": "PB_SG_GLOBAL_BAL_001",
                "base_currency": "SGD",
                "positions": [{"instrument_id": "EQ_1", "quantity": "50"}],
                "cash_balances": [{"currency": "SGD", "amount": "5000"}],
            },
            "market_data_snapshot": {
                "snapshot_id": "core-md-snap-001",
                "prices": [{"instrument_id": "EQ_1", "price": "100", "currency": "SGD"}],
                "fx_rates": [],
            },
            "model_portfolio": {"targets": [{"instrument_id": "EQ_1", "weight": "0.50"}]},
            "shelf_entries": [{"instrument_id": "EQ_1", "status": "APPROVED"}],
            "policy_context": {
                "recommended_policy_pack_id": "dpm_standard_v1",
                "tenant_id": "tenant_001",
                "booking_center_code": "SG",
                "mandate_id": "MANDATE_PB_SG_GLOBAL_BAL_001",
            },
            "source_lineage": {
                "portfolio_snapshot_id": "core-pf-snap-001",
                "market_data_snapshot_id": "core-md-snap-001",
                "model_portfolio_id": "MODEL_PB_SG_GLOBAL_BAL_DPM",
                "model_portfolio_version": "2026-05-03",
                "shelf_version": "shelf_sg_v1",
                "integration_policy_version": "dpm-core-context.v1",
                "source_lineage_bundle_id": "lineage-bundle-001",
            },
            "supportability": {
                "state": supportability_state,
                "reason": "DPM_CORE_CONTEXT_DEGRADED",
                "freshness_bucket": "same_day",
            },
        }
    )


class _FakeCoreResolver:
    def resolve_execution_context(self, *, stateful_input, correlation_id):
        return _core_execution_context(supportability_state="DEGRADED")


def test_generate_construction_alternative_set_first_wave_and_replay() -> None:
    repository = InMemoryConstructionRepository()
    with _client(repository) as client:
        first = client.post(
            "/api/v1/construction/alternative-sets/generate",
            json=_payload(),
            headers={
                "Idempotency-Key": "idem-construction-001",
                "X-Correlation-Id": "corr-construction-001",
            },
        )
        second = client.post(
            "/api/v1/construction/alternative-sets/generate",
            json=_payload(),
            headers={
                "Idempotency-Key": "idem-construction-001",
                "X-Correlation-Id": "corr-construction-001",
            },
        )

    app.dependency_overrides = {}

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    body = first.json()
    assert body["request_hash"].startswith("sha256:")
    assert body["input_mode"] == "stateless"
    assert [alternative["method"] for alternative in body["alternatives"]] == [
        "DO_NOTHING_BASELINE",
        "HEURISTIC_EXPLAINABLE",
        "MIN_TURNOVER",
        "TAX_AWARE",
    ]
    assert body["alternatives"][0]["comparison_metrics"]["trade_count"] == 0
    assert body["alternatives"][2]["diagnostics"]["method_plan"]["effective_method"] == (
        "MIN_TURNOVER"
    )
    assert body["alternatives"][3]["method_status"] == "READY"
    assert (
        "AUTHORITATIVE_TRANSACTION_COST_UNAVAILABLE"
        in body["alternatives"][3]["diagnostics"]["enrichment_summary"]["reason_codes"]
    )


def test_generate_construction_alternative_set_surfaces_pending_review_for_turnover_budget() -> (
    None
):
    repository = InMemoryConstructionRepository()
    payload = _payload()
    payload["stateless_input"]["model_portfolio"]["targets"] = [
        {"instrument_id": "EQ_1", "weight": "0.0"}
    ]

    with _client(repository) as client:
        response = client.post(
            "/api/v1/construction/alternative-sets/generate",
            json=payload,
            headers={"Idempotency-Key": "idem-construction-pending"},
        )

    app.dependency_overrides = {}

    assert response.status_code == 200
    min_turnover = response.json()["alternatives"][2]
    assert min_turnover["method"] == "MIN_TURNOVER"
    assert min_turnover["method_status"] == "PENDING_REVIEW"
    assert (
        "TURNOVER_BUDGET_DROPPED_INTENTS"
        in min_turnover["diagnostics"]["enrichment_summary"]["reason_codes"]
    )


def test_generate_construction_alternative_set_surfaces_blocked_method_status() -> None:
    repository = InMemoryConstructionRepository()
    payload = _payload()
    payload["stateless_input"]["market_data_snapshot"]["prices"] = []

    with _client(repository) as client:
        response = client.post(
            "/api/v1/construction/alternative-sets/generate",
            json=payload,
            headers={"Idempotency-Key": "idem-construction-blocked"},
        )

    app.dependency_overrides = {}

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "BLOCKED"
    assert {alternative["method_status"] for alternative in body["alternatives"]} == {"BLOCKED"}
    assert body["alternatives"][0]["diagnostics"]["data_quality"]["price_missing"] == ["EQ_1"]


def test_generate_construction_alternative_set_preserves_degraded_stateful_source(
    monkeypatch,
) -> None:
    repository = InMemoryConstructionRepository()
    monkeypatch.setenv("DPM_STATEFUL_CORE_SOURCING_ENABLED", "true")
    monkeypatch.setattr(
        rebalance_service,
        "build_core_resolver_client",
        lambda: _FakeCoreResolver(),
    )

    with _client(repository) as client:
        response = client.post(
            "/api/v1/construction/alternative-sets/generate",
            json={
                "input_mode": "stateful",
                "stateful_input": _stateful_input_payload(),
            },
            headers={"Idempotency-Key": "idem-construction-stateful-degraded"},
        )

    app.dependency_overrides = {}

    assert response.status_code == 200
    body = response.json()
    assert body["input_mode"] == "stateful"
    assert body["source_supportability_state"] == "DEGRADED"


def test_generate_construction_alternative_set_idempotency_conflict() -> None:
    repository = InMemoryConstructionRepository()
    changed = _payload()
    changed["stateless_input"]["options"] = {"max_turnover_pct": "0.05"}

    with _client(repository) as client:
        created = client.post(
            "/api/v1/construction/alternative-sets/generate",
            json=_payload(),
            headers={"Idempotency-Key": "idem-construction-conflict"},
        )
        conflict = client.post(
            "/api/v1/construction/alternative-sets/generate",
            json=changed,
            headers={"Idempotency-Key": "idem-construction-conflict"},
        )

    app.dependency_overrides = {}

    assert created.status_code == 200
    assert conflict.status_code == 409
    assert conflict.json()["detail"] == "CONSTRUCTION_IDEMPOTENCY_KEY_CONFLICT"


def test_read_and_select_construction_alternative_set() -> None:
    repository = InMemoryConstructionRepository()
    with _client(repository) as client:
        created = client.post(
            "/api/v1/construction/alternative-sets/generate",
            json=_payload(),
            headers={"Idempotency-Key": "idem-construction-select"},
        )
        alternative_set_id = created.json()["alternative_set_id"]
        read_back = client.get(f"/api/v1/construction/alternative-sets/{alternative_set_id}")
        selection = client.post(
            f"/api/v1/construction/alternative-sets/{alternative_set_id}/selections",
            json={
                "alternative_id": "alt_min_turnover",
                "actor_id": "pm_001",
                "reason_code": "LOWER_TURNOVER_WITH_ACCEPTABLE_DRIFT",
                "comment": "Lower turnover is preferred for this review cycle.",
            },
            headers={"X-Correlation-Id": "corr-construction-select"},
        )
        missing_alternative = client.post(
            f"/api/v1/construction/alternative-sets/{alternative_set_id}/selections",
            json={
                "alternative_id": "alt_not_real",
                "actor_id": "pm_001",
                "reason_code": "INVALID",
            },
        )

    app.dependency_overrides = {}

    assert read_back.status_code == 200
    assert read_back.json()["alternative_set_id"] == alternative_set_id
    assert selection.status_code == 200
    assert selection.json()["alternative_id"] == "alt_min_turnover"
    assert selection.json()["correlation_id"] == "corr-construction-select"
    assert repository.get_selection(alternative_set_id=alternative_set_id) is not None
    assert missing_alternative.status_code == 404
    assert missing_alternative.json()["detail"] == "CONSTRUCTION_ALTERNATIVE_NOT_FOUND"
