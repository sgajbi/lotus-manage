from fastapi.testclient import TestClient

from src.api.dependencies import (
    get_construction_repository,
    get_db_session,
    get_risk_authority_client,
)
from src.api.main import app
import src.api.services.construction_service as construction_service
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


class _ReadyRiskAuthorityClient:
    def concentration_context(self, *, result, correlation_id):
        from src.core.construction.models import AuthoritativeRiskContext
        from src.core.construction.vocabulary import ConstructionMethodStatus

        return AuthoritativeRiskContext(
            supportability_status=ConstructionMethodStatus.READY,
            source_system="lotus-risk",
            concentration_breaches=0,
            concentration_hhi_delta="125.50",
            top_position_weight_proposed="0.2450",
            issuer_coverage_status="complete",
            reason_codes=["LOTUS_RISK_CONCENTRATION_CALCULATION_COMPLETE"],
        )

    def regime_scenario_context(
        self,
        *,
        result,
        portfolio_id,
        as_of_date,
        correlation_id,
        scenario_pack_id="CIO_REGIME_2026_Q2",
        maximum_allowed_loss_pct="0.12",
    ):
        from src.core.construction.models import AuthoritativeRegimeStressContext
        from src.core.construction.vocabulary import ConstructionMethodStatus

        return AuthoritativeRegimeStressContext(
            supportability_status=ConstructionMethodStatus.READY,
            source_system="lotus-risk",
            scenario_pack_id=scenario_pack_id,
            worst_case_loss_pct="0.08",
            maximum_allowed_loss_pct=maximum_allowed_loss_pct,
            reason_codes=["REGIME_SCENARIO_PACK_READY"],
        )


def _authority_context_payload() -> dict:
    return {
        "liquidity_context": {
            "supportability_status": "READY",
            "source_system": "lotus-manage-settlement-engine",
            "policy_id": "liquidity-policy.v1",
            "minimum_cash_weight": "0.03",
            "allowed_liquidity_tiers": ["L1", "L2", "L3"],
            "cashflow_projection": {
                "source_product_name": "PortfolioCashflowProjection",
                "source_product_version": "v1",
                "source_system": "lotus-core",
                "total_net_cashflow": {"amount": "5000.00", "currency": "SGD"},
                "projection_start": "2026-05-03",
                "projection_end": "2026-06-03",
                "include_projected": True,
                "latest_evidence_timestamp": "2026-05-03T09:30:00Z",
                "source_batch_fingerprint": ("cashflow-projection:PB_SG_GLOBAL_BAL_001:2026-05-03"),
                "data_quality_status": "READY",
                "reason_codes": ["CORE_CASHFLOW_PROJECTION_READY"],
            },
            "reason_codes": ["LIQUIDITY_POLICY_READY"],
        },
        "currency_overlay_context": {
            "supportability_status": "READY",
            "source_system": "lotus-manage-fx-policy",
            "policy_id": "currency-overlay-policy.v1",
            "hedge_ratio_min": "0.00",
            "hedge_ratio_max": "1.00",
            "eligible_currencies": ["USD"],
            "reason_codes": ["CURRENCY_OVERLAY_POLICY_READY"],
        },
        "regime_stress_context": {
            "supportability_status": "READY",
            "source_system": "lotus-risk-scenario-pack",
            "scenario_pack_id": "CIO_REGIME_2026_Q2",
            "worst_case_loss_pct": "0.08",
            "maximum_allowed_loss_pct": "0.12",
            "reason_codes": ["REGIME_SCENARIO_PACK_READY"],
        },
    }


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


def test_advanced_methods_degrade_truthfully_when_authority_is_absent() -> None:
    repository = InMemoryConstructionRepository()
    payload = _payload()
    payload["stateless_input"]["shelf_entries"][0]["attributes"] = {
        "sector": "GLOBAL_EQUITY",
        "esg_profile": "ARTICLE_8",
    }
    payload["methods"] = [
        "SOLVER_CONSTRAINED",
        "LIQUIDITY_AWARE",
        "RISK_AWARE",
        "ESG_AWARE",
        "CURRENCY_OVERLAY",
        "REGIME_STRESS_AWARE",
    ]

    with _client(repository) as client:
        response = client.post(
            "/api/v1/construction/alternative-sets/generate",
            json=payload,
            headers={"Idempotency-Key": "idem-construction-authority-absent"},
        )

    app.dependency_overrides = {}

    assert response.status_code == 200
    alternatives = {
        alternative["method"]: alternative for alternative in response.json()["alternatives"]
    }
    assert set(alternatives) == set(payload["methods"])
    assert alternatives["SOLVER_CONSTRAINED"]["diagnostics"]["method_plan"]["requested_method"] == (
        "SOLVER_CONSTRAINED"
    )
    assert (
        "SETTLEMENT_AWARENESS_ENABLED"
        in (alternatives["LIQUIDITY_AWARE"]["diagnostics"]["enrichment_summary"]["reason_codes"])
    )
    assert (
        "RISK_AUTHORITY_NOT_CONNECTED"
        in (alternatives["RISK_AWARE"]["diagnostics"]["enrichment_summary"]["reason_codes"])
    )
    assert (
        "ESG_RESTRICTION_AWARE_CONSTRUCTION_DEFERRED"
        in (alternatives["ESG_AWARE"]["diagnostics"]["enrichment_summary"]["reason_codes"])
    )
    assert (
        "REGIME_SCENARIO_PACK_UNAVAILABLE"
        in (
            alternatives["REGIME_STRESS_AWARE"]["diagnostics"]["enrichment_summary"]["reason_codes"]
        )
    )


def test_authority_backed_methods_are_ready_with_required_evidence(monkeypatch) -> None:
    repository = InMemoryConstructionRepository()
    payload = _payload()
    payload["stateless_input"]["portfolio_snapshot"]["base_currency"] = "SGD"
    payload["stateless_input"]["portfolio_snapshot"]["positions"] = [
        {"instrument_id": "EQ_1", "quantity": "100"},
        {"instrument_id": "EQ_US", "quantity": "100"},
    ]
    payload["stateless_input"]["portfolio_snapshot"]["cash_balances"] = [
        {"currency": "SGD", "amount": "20000"},
        {"currency": "USD", "amount": "10000"},
    ]
    payload["stateless_input"]["market_data_snapshot"]["prices"] = [
        {"instrument_id": "EQ_1", "price": "100", "currency": "SGD"},
        {"instrument_id": "EQ_US", "price": "50", "currency": "USD"},
    ]
    payload["stateless_input"]["market_data_snapshot"]["fx_rates"] = [
        {"pair": "USD/SGD", "rate": "1.35"},
        {"pair": "SGD/USD", "rate": "0.7407407407"},
    ]
    payload["stateless_input"]["model_portfolio"]["targets"] = [
        {"instrument_id": "EQ_1", "weight": "0.25"},
        {"instrument_id": "EQ_US", "weight": "0.25"},
    ]
    payload["stateless_input"]["shelf_entries"] = [
        {"instrument_id": "EQ_1", "status": "APPROVED", "liquidity_tier": "L1"},
        {"instrument_id": "EQ_US", "status": "APPROVED", "liquidity_tier": "L1"},
    ]
    payload["methods"] = [
        "SOLVER_CONSTRAINED",
        "RISK_AWARE",
        "LIQUIDITY_AWARE",
        "CURRENCY_OVERLAY",
        "REGIME_STRESS_AWARE",
    ]
    payload["authority_context"] = _authority_context_payload()
    monkeypatch.setattr(construction_service, "has_solver_dependencies", lambda: True)
    app.dependency_overrides[get_risk_authority_client] = lambda: _ReadyRiskAuthorityClient()

    with _client(repository) as client:
        response = client.post(
            "/api/v1/construction/alternative-sets/generate",
            json=payload,
            headers={"Idempotency-Key": "idem-construction-authority-backed"},
        )

    app.dependency_overrides = {}

    assert response.status_code == 200
    alternatives = {
        alternative["method"]: alternative for alternative in response.json()["alternatives"]
    }
    assert set(alternatives) == set(payload["methods"])
    assert alternatives["RISK_AWARE"]["method_status"] == "READY"
    assert alternatives["LIQUIDITY_AWARE"]["method_status"] == "READY"
    assert alternatives["CURRENCY_OVERLAY"]["method_status"] == "READY"
    assert alternatives["REGIME_STRESS_AWARE"]["method_status"] == "READY"
    assert (
        "LOTUS_RISK_CONCENTRATION_CALCULATION_COMPLETE"
        in alternatives["RISK_AWARE"]["diagnostics"]["enrichment_summary"]["reason_codes"]
    )
    assert (
        "REGIME_SCENARIO_PACK_READY"
        in alternatives["REGIME_STRESS_AWARE"]["diagnostics"]["enrichment_summary"]["reason_codes"]
    )
    liquidity_reasons = alternatives["LIQUIDITY_AWARE"]["diagnostics"]["enrichment_summary"][
        "reason_codes"
    ]
    assert "CORE_CASHFLOW_PROJECTION_READY" in liquidity_reasons
    assert "CASHFLOW_PROJECTION_READY" in liquidity_reasons
    assert (
        "LOTUS_RISK_CONCENTRATION_CALCULATION_COMPLETE"
        not in alternatives["LIQUIDITY_AWARE"]["diagnostics"]["enrichment_summary"]["reason_codes"]
    )


def test_liquidity_aware_method_uses_core_cashflow_projection_for_policy_review() -> None:
    repository = InMemoryConstructionRepository()
    payload = _payload()
    payload["stateless_input"]["portfolio_snapshot"]["base_currency"] = "SGD"
    payload["stateless_input"]["portfolio_snapshot"]["positions"] = [
        {"instrument_id": "EQ_1", "quantity": "100"}
    ]
    payload["stateless_input"]["portfolio_snapshot"]["cash_balances"] = [
        {"currency": "SGD", "amount": "20000"}
    ]
    payload["stateless_input"]["market_data_snapshot"]["prices"] = [
        {"instrument_id": "EQ_1", "price": "100", "currency": "SGD"}
    ]
    payload["stateless_input"]["model_portfolio"]["targets"] = [
        {"instrument_id": "EQ_1", "weight": "0.25"}
    ]
    payload["stateless_input"]["shelf_entries"] = [
        {"instrument_id": "EQ_1", "status": "APPROVED", "liquidity_tier": "L1"}
    ]
    payload["methods"] = ["LIQUIDITY_AWARE"]
    authority_context = _authority_context_payload()
    authority_context["liquidity_context"]["minimum_cash_weight"] = "0.20"
    authority_context["liquidity_context"]["cashflow_projection"]["total_net_cashflow"] = {
        "amount": "-20000.00",
        "currency": "SGD",
    }
    payload["authority_context"] = authority_context

    with _client(repository) as client:
        response = client.post(
            "/api/v1/construction/alternative-sets/generate",
            json=payload,
            headers={"Idempotency-Key": "idem-construction-liquidity-cashflow"},
        )

    app.dependency_overrides = {}

    assert response.status_code == 200
    alternative = response.json()["alternatives"][0]
    reason_codes = alternative["diagnostics"]["enrichment_summary"]["reason_codes"]
    assert alternative["method"] == "LIQUIDITY_AWARE"
    assert alternative["method_status"] == "PENDING_REVIEW"
    assert "CORE_CASHFLOW_PROJECTION_READY" in reason_codes
    assert "CASHFLOW_PROJECTION_ADJUSTED_CASH_BELOW_POLICY" in reason_codes


def test_regime_stress_aware_pending_review_when_scenario_loss_exceeds_policy() -> None:
    repository = InMemoryConstructionRepository()
    payload = _payload()
    payload["methods"] = ["REGIME_STRESS_AWARE"]
    authority_context = _authority_context_payload()
    authority_context["regime_stress_context"]["worst_case_loss_pct"] = "0.18"
    authority_context["regime_stress_context"]["maximum_allowed_loss_pct"] = "0.12"
    payload["authority_context"] = authority_context

    with _client(repository) as client:
        response = client.post(
            "/api/v1/construction/alternative-sets/generate",
            json=payload,
            headers={"Idempotency-Key": "idem-construction-regime-breach"},
        )

    app.dependency_overrides = {}

    assert response.status_code == 200
    alternative = response.json()["alternatives"][0]
    assert alternative["method"] == "REGIME_STRESS_AWARE"
    assert alternative["method_status"] == "PENDING_REVIEW"


def test_regime_stress_aware_resolves_lotus_risk_scenario_pack_when_configured() -> None:
    repository = InMemoryConstructionRepository()
    payload = _payload()
    payload["methods"] = ["REGIME_STRESS_AWARE"]
    app.dependency_overrides[get_risk_authority_client] = lambda: _ReadyRiskAuthorityClient()

    with _client(repository) as client:
        response = client.post(
            "/api/v1/construction/alternative-sets/generate",
            json=payload,
            headers={"Idempotency-Key": "idem-construction-regime-source-backed"},
        )

    app.dependency_overrides = {}

    assert response.status_code == 200
    alternative = response.json()["alternatives"][0]
    authority_context = alternative["diagnostics"]["authority_context"]
    reason_codes = alternative["diagnostics"]["enrichment_summary"]["reason_codes"]
    assert alternative["method"] == "REGIME_STRESS_AWARE"
    assert alternative["method_status"] == "READY"
    assert authority_context["regime_stress_context"]["source_system"] == "lotus-risk"
    assert authority_context["regime_stress_context"]["scenario_pack_id"] == "CIO_REGIME_2026_Q2"
    assert "REGIME_SCENARIO_PACK_READY" in reason_codes
    assert "REGIME_SCENARIO_PACK_UNAVAILABLE" not in reason_codes


def test_solver_constrained_falls_back_when_solver_unavailable(monkeypatch) -> None:
    repository = InMemoryConstructionRepository()
    payload = _payload()
    payload["methods"] = ["SOLVER_CONSTRAINED"]
    monkeypatch.setattr(construction_service, "has_solver_dependencies", lambda: False)

    with _client(repository) as client:
        response = client.post(
            "/api/v1/construction/alternative-sets/generate",
            json=payload,
            headers={"Idempotency-Key": "idem-construction-solver-fallback"},
        )

    app.dependency_overrides = {}

    assert response.status_code == 200
    alternative = response.json()["alternatives"][0]
    assert alternative["method"] == "SOLVER_CONSTRAINED"
    assert alternative["method_status"] == "PENDING_REVIEW"
    assert alternative["diagnostics"]["method_plan"]["effective_method"] == "HEURISTIC_EXPLAINABLE"
    assert alternative["diagnostics"]["method_plan"]["reason_codes"] == [
        "SOLVER_UNAVAILABLE_FALLBACK_HEURISTIC"
    ]


def test_currency_overlay_blocks_missing_fx_source() -> None:
    repository = InMemoryConstructionRepository()
    payload = _payload()
    payload["stateless_input"]["portfolio_snapshot"]["base_currency"] = "SGD"
    payload["stateless_input"]["market_data_snapshot"]["prices"] = [
        {"instrument_id": "EQ_1", "price": "100.00", "currency": "USD"}
    ]
    payload["methods"] = ["CURRENCY_OVERLAY"]

    with _client(repository) as client:
        response = client.post(
            "/api/v1/construction/alternative-sets/generate",
            json=payload,
            headers={"Idempotency-Key": "idem-construction-currency-missing"},
        )

    app.dependency_overrides = {}

    assert response.status_code == 200
    alternative = response.json()["alternatives"][0]
    assert alternative["method"] == "CURRENCY_OVERLAY"
    assert alternative["method_status"] == "BLOCKED"
    assert (
        "CURRENCY_OVERLAY_FX_SOURCE_MISSING"
        in (alternative["diagnostics"]["enrichment_summary"]["reason_codes"])
    )


def test_esg_aware_degrades_when_profile_source_is_missing() -> None:
    repository = InMemoryConstructionRepository()
    payload = _payload()
    payload["methods"] = ["ESG_AWARE"]

    with _client(repository) as client:
        response = client.post(
            "/api/v1/construction/alternative-sets/generate",
            json=payload,
            headers={"Idempotency-Key": "idem-construction-esg-missing"},
        )

    app.dependency_overrides = {}

    assert response.status_code == 200
    alternative = response.json()["alternatives"][0]
    assert alternative["method"] == "ESG_AWARE"
    assert alternative["method_status"] == "DEGRADED"
    assert (
        "ESG_RESTRICTION_AWARE_CONSTRUCTION_DEFERRED"
        in (alternative["diagnostics"]["enrichment_summary"]["reason_codes"])
    )


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
