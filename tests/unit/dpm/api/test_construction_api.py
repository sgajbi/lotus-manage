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


def _transaction_cost_authority_context_payload() -> dict:
    return {
        "transaction_cost_context": {
            "supportability_status": "READY",
            "source_system": "lotus-core",
            "source_product_name": "TransactionCostCurve",
            "source_product_version": "v1",
            "source_id": "transaction-cost-scope-001",
            "content_hash": "sha256:transaction-cost-curve",
            "as_of_date": "2026-05-03",
            "window_start_date": "2026-02-02",
            "window_end_date": "2026-05-03",
            "returned_curve_point_count": 1,
            "missing_security_ids": [],
            "curve_points": [
                {
                    "security_id": "EQ_1",
                    "transaction_type": "BUY",
                    "currency": "SGD",
                    "observation_count": 3,
                    "total_notional": "30000.0000",
                    "total_cost": "15.0000",
                    "average_cost_bps": "5.0000",
                    "min_cost_bps": "4.5000",
                    "max_cost_bps": "5.5000",
                    "first_observed_date": "2026-04-01",
                    "last_observed_date": "2026-05-03",
                    "sample_transaction_ids": ["TXN-1", "TXN-2"],
                }
            ],
            "reason_codes": ["TRANSACTION_COST_CURVE_READY"],
        }
    }


def _esg_authority_context_payload() -> dict:
    return {
        "client_restriction_context": {
            "supportability_status": "READY",
            "source_system": "lotus-core",
            "source_product_name": "ClientRestrictionProfile",
            "source_product_version": "v1",
            "source_id": "sha256:client-restrictions",
            "content_hash": "sha256:client-restrictions",
            "portfolio_id": "PB_SG_GLOBAL_BAL_001",
            "client_id": "CIF_SG_000184",
            "mandate_id": "MANDATE_PB_SG_GLOBAL_BAL_001",
            "as_of_date": "2026-05-03",
            "restriction_count": 1,
            "missing_data_families": [],
            "restrictions": [
                {
                    "restriction_scope": "instrument",
                    "restriction_code": "NO_PRIVATE_CREDIT_BUY",
                    "restriction_status": "active",
                    "restriction_source": "client_mandate",
                    "applies_to_buy": True,
                    "applies_to_sell": False,
                    "instrument_ids": ["PRIVATE_CREDIT_FUND"],
                    "asset_classes": [],
                    "issuer_ids": [],
                    "country_codes": [],
                    "effective_from": "2026-01-01",
                    "effective_to": None,
                    "restriction_version": 1,
                    "source_record_id": "client-restriction:1",
                }
            ],
            "reason_codes": ["CLIENT_RESTRICTION_PROFILE_READY"],
        },
        "sustainability_preference_context": {
            "supportability_status": "READY",
            "source_system": "lotus-core",
            "source_product_name": "SustainabilityPreferenceProfile",
            "source_product_version": "v1",
            "source_id": "sha256:sustainability-preferences",
            "content_hash": "sha256:sustainability-preferences",
            "portfolio_id": "PB_SG_GLOBAL_BAL_001",
            "client_id": "CIF_SG_000184",
            "mandate_id": "MANDATE_PB_SG_GLOBAL_BAL_001",
            "as_of_date": "2026-05-03",
            "preference_count": 1,
            "missing_data_families": [],
            "preferences": [
                {
                    "preference_framework": "LOTUS_SUSTAINABILITY_V1",
                    "preference_code": "MIN_SUSTAINABLE_ALLOCATION",
                    "preference_status": "active",
                    "preference_source": "client_mandate",
                    "minimum_allocation": "0.2000000000",
                    "maximum_allocation": None,
                    "applies_to_asset_classes": ["Equity"],
                    "exclusion_codes": [],
                    "positive_tilt_codes": [],
                    "effective_from": "2026-01-01",
                    "effective_to": None,
                    "preference_version": 1,
                    "source_record_id": "sustainability:1",
                }
            ],
            "reason_codes": ["SUSTAINABILITY_PREFERENCE_PROFILE_READY"],
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


def _core_execution_context(
    *,
    supportability_state: str = "DEGRADED",
    include_transaction_cost_curve: bool = False,
    include_cashflow_projection: bool = False,
    include_external_hedge_readiness: bool = False,
    cashflow_data_quality_status: str = "COMPLETE",
) -> DpmCoreExecutionContext:
    payload = {
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
    if include_transaction_cost_curve:
        payload["transaction_cost_curve"] = {
            "product_name": "TransactionCostCurve",
            "product_version": "v1",
            "portfolio_id": "PB_SG_GLOBAL_BAL_001",
            "as_of_date": "2026-05-03",
            "window": {"start_date": "2026-02-02", "end_date": "2026-05-03"},
            "curve_points": [
                {
                    "portfolio_id": "PB_SG_GLOBAL_BAL_001",
                    "security_id": "EQ_1",
                    "transaction_type": "BUY",
                    "currency": "SGD",
                    "observation_count": 2,
                    "total_notional": "10000.0000000000",
                    "total_cost": "5.0000000000",
                    "average_cost_bps": "5.0000",
                    "min_cost_bps": "4.5000",
                    "max_cost_bps": "5.5000",
                    "first_observed_date": "2026-04-01",
                    "last_observed_date": "2026-05-03",
                    "sample_transaction_ids": ["TXN-EQ1-001", "TXN-EQ1-002"],
                }
            ],
            "page": {
                "page_size": 250,
                "sort_key": "security_id:asc,transaction_type:asc,currency:asc",
                "returned_component_count": 1,
                "request_scope_fingerprint": "transaction-cost-scope-001",
                "next_page_token": None,
            },
            "supportability": {
                "state": "READY",
                "reason": "TRANSACTION_COST_CURVE_READY",
                "requested_security_count": 1,
                "returned_curve_point_count": 1,
                "missing_security_ids": [],
            },
            "lineage": {
                "source_system": "transactions",
                "contract_version": "rfc_040_wtbd_007_v1",
            },
            "data_quality_status": "COMPLETE",
            "latest_evidence_timestamp": "2026-05-03T09:00:00Z",
            "source_batch_fingerprint": "sha256:transaction-cost-curve",
        }
    if include_cashflow_projection:
        payload["portfolio_cashflow_projection"] = {
            "product_name": "PortfolioCashflowProjection",
            "product_version": "v1",
            "portfolio_id": "PB_SG_GLOBAL_BAL_001",
            "as_of_date": "2026-05-03",
            "range_start_date": "2026-05-03",
            "range_end_date": "2026-08-01",
            "include_projected": True,
            "portfolio_currency": "SGD",
            "points": [
                {
                    "projection_date": "2026-05-10",
                    "net_cashflow": "-50.0000000000",
                    "projected_cumulative_cashflow": "-50.0000000000",
                }
            ],
            "total_net_cashflow": "-50.0000000000",
            "projection_days": 90,
            "data_quality_status": cashflow_data_quality_status,
            "latest_evidence_timestamp": "2026-05-03T09:00:00Z",
            "source_batch_fingerprint": "sha256:cashflow-projection",
        }
    if include_external_hedge_readiness:
        payload["external_hedge_execution_readiness"] = {
            "product_name": "ExternalHedgeExecutionReadiness",
            "product_version": "v1",
            "portfolio_id": "PB_SG_GLOBAL_BAL_001",
            "client_id": "CIF_SG_000184",
            "mandate_id": "MANDATE_PB_SG_GLOBAL_BAL_001",
            "as_of_date": "2026-05-03",
            "reporting_currency": "SGD",
            "exposure_currencies": ["USD"],
            "readiness_checks": [],
            "supportability": {
                "state": "UNAVAILABLE",
                "reason": "EXTERNAL_TREASURY_SOURCE_NOT_INGESTED",
                "missing_data_families": [
                    "external_currency_exposure",
                    "external_hedge_policy",
                    "external_fx_forward_curve",
                    "external_eligible_hedge_instrument",
                    "external_hedge_execution_readiness",
                ],
                "blocked_capabilities": [
                    "hedge_advice",
                    "forward_pricing",
                    "counterparty_selection",
                    "best_execution",
                    "oms_acknowledgement",
                    "fills",
                    "settlement",
                    "autonomous_treasury_action",
                ],
            },
            "lineage": {
                "source_system": "external-bank-treasury",
                "integration_status": "not_ingested",
                "runtime_posture": "fail_closed",
            },
            "data_quality_status": "MISSING",
            "source_batch_fingerprint": "sha256:external-hedge-readiness",
        }
    return DpmCoreExecutionContext.model_validate(payload)


class _FakeCoreResolver:
    def resolve_execution_context(self, *, stateful_input, correlation_id):
        return _core_execution_context(supportability_state="DEGRADED")


class _TransactionCostCoreResolver:
    def resolve_execution_context(self, *, stateful_input, correlation_id):
        return _core_execution_context(
            supportability_state="READY",
            include_transaction_cost_curve=True,
            include_cashflow_projection=True,
        )


class _DegradedCashflowCoreResolver:
    def resolve_execution_context(self, *, stateful_input, correlation_id):
        return _core_execution_context(
            supportability_state="READY",
            include_cashflow_projection=True,
            cashflow_data_quality_status="DEGRADED",
        )


class _ExternalHedgeReadinessCoreResolver:
    def resolve_execution_context(self, *, stateful_input, correlation_id):
        return _core_execution_context(
            supportability_state="READY",
            include_external_hedge_readiness=True,
        )


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


def test_cost_aware_method_applies_source_owned_cost_curve_to_candidate_notional() -> None:
    repository = InMemoryConstructionRepository()
    payload = _payload()
    payload["stateless_input"]["model_portfolio"]["targets"] = [
        {"instrument_id": "EQ_1", "weight": "1.0"}
    ]
    payload["methods"] = ["COST_AWARE"]
    payload["authority_context"] = _transaction_cost_authority_context_payload()

    with _client(repository) as client:
        response = client.post(
            "/api/v1/construction/alternative-sets/generate",
            json=payload,
            headers={"Idempotency-Key": "idem-construction-cost-aware"},
        )

    app.dependency_overrides = {}

    assert response.status_code == 200
    alternative = response.json()["alternatives"][0]
    assert alternative["method"] == "COST_AWARE"
    assert alternative["method_status"] == "READY"
    assert alternative["comparison_metrics"]["estimated_transaction_cost"] == {
        "amount": "2.5000",
        "currency": "SGD",
    }
    assert any(term["term"] == "ESTIMATED_COST" for term in alternative["objective_trace"])
    cost_trace = next(
        trace
        for trace in alternative["constraint_trace"]
        if trace["constraint"] == "ESTIMATED_COST"
    )
    assert cost_trace["source_family"] == "TRANSACTION_COST"
    assert "TRANSACTION_COST_CURVE_APPLIED_TO_CANDIDATE_NOTIONALS" in cost_trace["reason_codes"]
    assert (
        "AUTHORITATIVE_TRANSACTION_COST_UNAVAILABLE"
        not in alternative["diagnostics"]["enrichment_summary"]["reason_codes"]
    )


def test_cost_aware_method_degrades_without_source_owned_cost_curve() -> None:
    repository = InMemoryConstructionRepository()
    payload = _payload()
    payload["stateless_input"]["model_portfolio"]["targets"] = [
        {"instrument_id": "EQ_1", "weight": "1.0"}
    ]
    payload["methods"] = ["COST_AWARE"]

    with _client(repository) as client:
        response = client.post(
            "/api/v1/construction/alternative-sets/generate",
            json=payload,
            headers={"Idempotency-Key": "idem-construction-cost-aware-degraded"},
        )

    app.dependency_overrides = {}

    assert response.status_code == 200
    alternative = response.json()["alternatives"][0]
    reason_codes = alternative["diagnostics"]["enrichment_summary"]["reason_codes"]
    assert alternative["method"] == "COST_AWARE"
    assert alternative["method_status"] == "DEGRADED"
    assert alternative["comparison_metrics"]["estimated_transaction_cost"] is None
    assert "AUTHORITATIVE_TRANSACTION_COST_UNAVAILABLE" in reason_codes
    assert "TRANSACTION_COST_CURVE_UNAVAILABLE" in reason_codes


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
    esg_reasons = alternatives["ESG_AWARE"]["diagnostics"]["enrichment_summary"]["reason_codes"]
    assert "CLIENT_RESTRICTION_PROFILE_UNAVAILABLE" in esg_reasons
    assert "SUSTAINABILITY_PREFERENCE_PROFILE_UNAVAILABLE" in esg_reasons
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
    reason_codes = alternative["diagnostics"]["enrichment_summary"]["reason_codes"]
    assert "CLIENT_RESTRICTION_PROFILE_UNAVAILABLE" in reason_codes
    assert "SUSTAINABILITY_PREFERENCE_PROFILE_UNAVAILABLE" in reason_codes


def test_esg_aware_uses_source_profiles_when_available() -> None:
    repository = InMemoryConstructionRepository()
    payload = _payload()
    payload["methods"] = ["ESG_AWARE"]
    payload["stateless_input"]["shelf_entries"][0]["asset_class"] = "Equity"
    payload["authority_context"] = _esg_authority_context_payload()

    with _client(repository) as client:
        response = client.post(
            "/api/v1/construction/alternative-sets/generate",
            json=payload,
            headers={"Idempotency-Key": "idem-construction-esg-source-backed"},
        )

    app.dependency_overrides = {}

    assert response.status_code == 200
    alternative = response.json()["alternatives"][0]
    reason_codes = alternative["diagnostics"]["enrichment_summary"]["reason_codes"]
    assert alternative["method"] == "ESG_AWARE"
    assert alternative["method_status"] == "READY"
    assert "CLIENT_RESTRICTION_PROFILE_APPLIED" in reason_codes
    assert "SUSTAINABILITY_PREFERENCE_PROFILE_APPLIED" in reason_codes
    constraints = {trace["constraint"]: trace for trace in alternative["constraint_trace"]}
    assert constraints["CLIENT_RESTRICTION"]["status"] == "READY"
    assert constraints["SUSTAINABILITY_PREFERENCE"]["status"] == "READY"


def test_esg_aware_blocks_restricted_candidate_buy() -> None:
    repository = InMemoryConstructionRepository()
    payload = _payload()
    payload["stateless_input"]["portfolio_snapshot"]["positions"] = []
    payload["stateless_input"]["model_portfolio"]["targets"] = [
        {"instrument_id": "PRIVATE_CREDIT_FUND", "weight": "0.50"}
    ]
    payload["stateless_input"]["market_data_snapshot"]["prices"] = [
        {"instrument_id": "PRIVATE_CREDIT_FUND", "price": "100", "currency": "SGD"}
    ]
    payload["stateless_input"]["shelf_entries"] = [
        {"instrument_id": "PRIVATE_CREDIT_FUND", "status": "APPROVED", "asset_class": "Credit"}
    ]
    payload["methods"] = ["ESG_AWARE"]
    payload["authority_context"] = _esg_authority_context_payload()

    with _client(repository) as client:
        response = client.post(
            "/api/v1/construction/alternative-sets/generate",
            json=payload,
            headers={"Idempotency-Key": "idem-construction-esg-restricted-buy"},
        )

    app.dependency_overrides = {}

    assert response.status_code == 200
    alternative = response.json()["alternatives"][0]
    reason_codes = alternative["diagnostics"]["enrichment_summary"]["reason_codes"]
    assert alternative["method_status"] == "BLOCKED"
    assert "CLIENT_RESTRICTION_VIOLATION_NO_PRIVATE_CREDIT_BUY" in reason_codes


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


def test_stateful_construction_attaches_core_transaction_cost_curve(monkeypatch) -> None:
    repository = InMemoryConstructionRepository()
    monkeypatch.setenv("DPM_STATEFUL_CORE_SOURCING_ENABLED", "true")
    monkeypatch.setattr(
        rebalance_service,
        "build_core_resolver_client",
        lambda: _TransactionCostCoreResolver(),
    )

    with _client(repository) as client:
        response = client.post(
            "/api/v1/construction/alternative-sets/generate",
            json={
                "input_mode": "stateful",
                "stateful_input": _stateful_input_payload(),
            },
            headers={"Idempotency-Key": "idem-construction-stateful-cost-curve"},
        )

    app.dependency_overrides = {}

    assert response.status_code == 200
    body = response.json()
    alternative = next(
        item for item in body["alternatives"] if item["method"] == "HEURISTIC_EXPLAINABLE"
    )
    cost_context = alternative["diagnostics"]["authority_context"]["transaction_cost_context"]
    reason_codes = alternative["diagnostics"]["enrichment_summary"]["reason_codes"]
    assert body["input_mode"] == "stateful"
    assert body["source_supportability_state"] == "READY"
    assert cost_context["source_system"] == "lotus-core"
    assert cost_context["source_product_name"] == "TransactionCostCurve"
    assert cost_context["returned_curve_point_count"] == 1
    assert cost_context["curve_points"][0]["average_cost_bps"] == "5.0000"
    assert "TRANSACTION_COST_CURVE_READY" in reason_codes
    assert "AUTHORITATIVE_TRANSACTION_COST_UNAVAILABLE" not in reason_codes


def test_stateful_construction_attaches_core_cashflow_projection(monkeypatch) -> None:
    repository = InMemoryConstructionRepository()
    monkeypatch.setenv("DPM_STATEFUL_CORE_SOURCING_ENABLED", "true")
    monkeypatch.setattr(
        rebalance_service,
        "build_core_resolver_client",
        lambda: _TransactionCostCoreResolver(),
    )

    with _client(repository) as client:
        response = client.post(
            "/api/v1/construction/alternative-sets/generate",
            json={
                "input_mode": "stateful",
                "stateful_input": _stateful_input_payload(),
                "methods": ["LIQUIDITY_AWARE"],
            },
            headers={"Idempotency-Key": "idem-construction-stateful-cashflow"},
        )

    app.dependency_overrides = {}

    assert response.status_code == 200
    body = response.json()
    alternative = body["alternatives"][0]
    liquidity_context = alternative["diagnostics"]["authority_context"]["liquidity_context"]
    cashflow_projection = liquidity_context["cashflow_projection"]
    reason_codes = alternative["diagnostics"]["enrichment_summary"]["reason_codes"]
    assert alternative["method"] == "LIQUIDITY_AWARE"
    assert cashflow_projection["source_system"] == "lotus-core"
    assert cashflow_projection["source_product_name"] == "PortfolioCashflowProjection"
    assert cashflow_projection["include_projected"] is True
    assert cashflow_projection["total_net_cashflow"] == {
        "amount": "-50.0000000000",
        "currency": "SGD",
    }
    assert "CASHFLOW_PROJECTION_CONTEXT_PRESENT" in reason_codes


def test_stateful_currency_overlay_preserves_external_hedge_readiness_fail_closed(
    monkeypatch,
) -> None:
    repository = InMemoryConstructionRepository()
    monkeypatch.setenv("DPM_STATEFUL_CORE_SOURCING_ENABLED", "true")
    monkeypatch.setattr(
        rebalance_service,
        "build_core_resolver_client",
        lambda: _ExternalHedgeReadinessCoreResolver(),
    )

    with _client(repository) as client:
        response = client.post(
            "/api/v1/construction/alternative-sets/generate",
            json={
                "input_mode": "stateful",
                "stateful_input": _stateful_input_payload(),
                "methods": ["CURRENCY_OVERLAY"],
            },
            headers={"Idempotency-Key": "idem-construction-stateful-hedge-readiness"},
        )

    app.dependency_overrides = {}

    assert response.status_code == 200
    body = response.json()
    alternative = body["alternatives"][0]
    currency_context = alternative["diagnostics"]["authority_context"]["currency_overlay_context"]
    reason_codes = alternative["diagnostics"]["enrichment_summary"]["reason_codes"]
    assert alternative["method"] == "CURRENCY_OVERLAY"
    assert alternative["method_status"] == "BLOCKED"
    assert currency_context["source_system"] == "lotus-core"
    assert currency_context["source_product_name"] == "ExternalHedgeExecutionReadiness"
    assert currency_context["supportability_status"] == "BLOCKED"
    assert "external_hedge_policy" in currency_context["missing_data_families"]
    assert "oms_acknowledgement" in currency_context["blocked_capabilities"]
    assert "EXTERNAL_TREASURY_SOURCE_NOT_INGESTED" in reason_codes
    assert "EXTERNAL_HEDGE_EXECUTION_READINESS_FAIL_CLOSED" in reason_codes
    assert "CURRENCY_OVERLAY_CONTEXT_BLOCKED" in reason_codes


def test_stateful_construction_marks_degraded_core_cashflow_projection(monkeypatch) -> None:
    repository = InMemoryConstructionRepository()
    monkeypatch.setenv("DPM_STATEFUL_CORE_SOURCING_ENABLED", "true")
    monkeypatch.setattr(
        rebalance_service,
        "build_core_resolver_client",
        lambda: _DegradedCashflowCoreResolver(),
    )

    with _client(repository) as client:
        response = client.post(
            "/api/v1/construction/alternative-sets/generate",
            json={
                "input_mode": "stateful",
                "stateful_input": _stateful_input_payload(),
                "methods": ["LIQUIDITY_AWARE"],
            },
            headers={"Idempotency-Key": "idem-construction-stateful-cashflow-degraded"},
        )

    app.dependency_overrides = {}

    assert response.status_code == 200
    body = response.json()
    alternative = body["alternatives"][0]
    cashflow_projection = alternative["diagnostics"]["authority_context"]["liquidity_context"][
        "cashflow_projection"
    ]
    assert cashflow_projection["data_quality_status"] == "DEGRADED"
    assert alternative["method_status"] == "DEGRADED"


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
