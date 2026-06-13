from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from src.core.construction import (
    AuthoritativeClientRestrictionContext,
    AuthoritativeClientRestrictionRule,
    AuthoritativePerformanceContext,
    AuthoritativeRegimeStressContext,
    AuthoritativeRiskContext,
    AuthoritativeSustainabilityPreference,
    AuthoritativeSustainabilityPreferenceContext,
    AuthoritativeTransactionCostContext,
    AuthoritativeTransactionCostPoint,
    ConstructionAuthorityContext,
    ConstructionAlternativeSelection,
    build_alternative_set,
    build_rebalance_result_alternative,
)
from src.core.models import (
    CashLadderBreach,
    EngineOptions,
    ExcludedInstrument,
    FundingPlanEntry,
    GateDecision,
    GateDecisionSummary,
    GateReason,
    Money,
    RebalanceResult,
    RuleResult,
    TaxImpact,
)
from src.core.mandates import (
    DpmMandateDigitalTwin,
    DpmMandateHealthInput,
    MandateHealthState,
    calculate_mandate_health,
)
from src.core.proof_packs import (
    ProofPackSourceValidationError,
    build_proof_pack_from_run,
    build_proof_pack_from_selected_alternative,
)
from src.core.proof_packs import builder as builder_module
from src.core.proof_packs.models import DpmProofPackSourceRef
from src.core.proof_packs.source_analytics import (
    ProofPackAnalyticsFamily,
    ProofPackSourceAnalytics,
    _authority_reason_codes,
    _authority_source_ref,
    _degraded_context_reason_codes,
    _missing_regime_stress_governance_evidence,
    _performance_source_facts,
    _performance_source_metrics,
    _regime_source_reason_posture,
    _regime_stress_governance_posture_facts,
    _regime_stress_source_facts,
    _regime_stress_source_metrics,
    _risk_source_facts,
    _risk_source_metrics,
    _transaction_cost_source_facts,
    _transaction_cost_source_metrics,
    source_analytics_for_alternative,
    source_analytics_for_context,
)
from src.core.construction.vocabulary import ConstructionMethodStatus
from src.core.rebalance.engine import run_simulation
from src.core.rebalance_runs.models import DpmRunRecord, DpmRunWorkflowDecisionRecord
from tests.shared.factories import (
    cash,
    market_data_snapshot,
    model_portfolio,
    portfolio_snapshot,
    position,
    price,
    shelf_entry,
    target,
)


CREATED_AT = datetime(2026, 5, 3, 9, 30, tzinfo=timezone.utc)


def _ready_rebalance_result() -> RebalanceResult:
    portfolio = portfolio_snapshot(
        portfolio_id="pf_proof_pack_1",
        base_currency="USD",
        positions=[position("EQ_A", "10")],
        cash_balances=[cash("USD", "0")],
    )
    market_data = market_data_snapshot(
        prices=[
            price("EQ_A", "100", "USD"),
            price("EQ_B", "100", "USD"),
        ]
    )
    model = model_portfolio(
        targets=[
            target("EQ_A", "0.50"),
            target("EQ_B", "0.50"),
        ]
    )
    shelf = [
        shelf_entry("EQ_A", status="APPROVED", asset_class="EQUITY"),
        shelf_entry("EQ_B", status="APPROVED", asset_class="EQUITY"),
    ]
    return run_simulation(
        portfolio=portfolio,
        market_data=market_data,
        model=model,
        shelf=shelf,
        options=EngineOptions(),
        request_hash="sha256:proof-pack-test",
        correlation_id="corr-proof-pack-test",
    )


def _run_record(*, result: RebalanceResult | None = None) -> DpmRunRecord:
    resolved_result = result or _ready_rebalance_result()
    return DpmRunRecord(
        rebalance_run_id=resolved_result.rebalance_run_id,
        correlation_id=resolved_result.correlation_id,
        request_hash="sha256:proof-pack-test",
        idempotency_key="idem-proof-pack-test",
        portfolio_id="pf_proof_pack_1",
        created_at=CREATED_AT,
        result_json=resolved_result.model_dump(mode="json"),
    )


def _mandate_twin() -> DpmMandateDigitalTwin:
    return DpmMandateDigitalTwin.model_validate(
        {
            "mandate_id": "mandate_001",
            "portfolio_id": "pf_proof_pack_1",
            "mandate_version": "3",
            "as_of_date": "2026-05-03",
            "base_currency": "USD",
            "reference_currency": "USD",
            "risk_profile": "BALANCED",
            "investment_objective": "LONG_TERM_TOTAL_RETURN",
            "time_horizon": "LONG_TERM",
            "model_portfolio_id": "MODEL_DPM_BALANCED",
            "model_portfolio_version": "2026.04",
            "constraints": {
                "cash_band_min_weight": "0.00",
                "cash_band_max_weight": "0.10",
                "turnover_budget": "0.15",
            },
            "review_policy": {"review_frequency": "QUARTERLY"},
        }
    )


def _section(pack, section_type: str):
    return next(section for section in pack.sections if section.section_type == section_type)


def _source_ref() -> DpmProofPackSourceRef:
    return DpmProofPackSourceRef(
        source_system="lotus-risk",
        source_type="RiskMetricsReport",
        source_id="risk-report:pf_proof_pack_1:2026-05-03",
        supportability_state="READY",
        content_hash="sha256:risk-report-proof",
    )


def test_source_analytics_section_payload_returns_degraded_missing_context() -> None:
    state, summary, facts, metrics, reason_codes = builder_module._source_analytics_section_payload(
        source_analytics={},
        family="risk",
        missing_summary="No risk-authoritative enrichment is attached.",
        missing_reason_code="DPM_RISK_AUTHORITY_CONTEXT_MISSING",
    )

    assert state == "DEGRADED"
    assert summary == "No risk-authoritative enrichment is attached."
    assert facts == {}
    assert metrics == {}
    assert reason_codes == ["DPM_RISK_AUTHORITY_CONTEXT_MISSING"]


def test_source_analytics_section_payload_preserves_context_and_can_sort_reason_codes() -> None:
    analytics = ProofPackSourceAnalytics(
        family="regime_stress",
        state="PENDING_REVIEW",
        summary="Scenario evidence is attached.",
        facts={"scenario_pack_id": "CIO_REGIME_2026_Q2"},
        metrics={"worst_case_loss_pct": "0.1800"},
        reason_codes=["Z_REASON", "A_REASON", "Z_REASON"],
        source_ref=_source_ref(),
        source_hash_key="regime_stress_context",
        content_hash="sha256:regime-stress-context",
    )

    state, summary, facts, metrics, reason_codes = builder_module._source_analytics_section_payload(
        source_analytics={"regime_stress": analytics},
        family="regime_stress",
        missing_summary="Scenario/regime authority context is not attached.",
        missing_reason_code="DPM_SCENARIO_CONTEXT_MISSING",
        sort_reason_codes=True,
    )

    assert state == "PENDING_REVIEW"
    assert summary == "Scenario evidence is attached."
    assert facts == {"scenario_pack_id": "CIO_REGIME_2026_Q2"}
    assert metrics == {"worst_case_loss_pct": "0.1800"}
    assert reason_codes == ["A_REASON", "Z_REASON"]


def test_adapter_section_payload_returns_ready_contract_reference() -> None:
    state, summary, facts, metrics, reason_codes = builder_module._adapter_section_payload(
        summary="Report input adapter is available.",
        adapter_contract="DpmProofPackReportInput",
    )

    assert state == "READY"
    assert summary == "Report input adapter is available."
    assert facts == {"adapter_contract": "DpmProofPackReportInput"}
    assert metrics == {}
    assert reason_codes == []


def test_decision_summary_section_payload_projects_reason_and_actor() -> None:
    result = _ready_rebalance_result()

    state, summary, facts, metrics, reason_codes = builder_module._decision_summary_section_payload(
        result=result,
        selected_alternative=None,
        reason="Review rebalance.",
        created_by="pm_001",
    )

    assert state == "READY"
    assert summary == "Decision evidence assembled from manage run and actor rationale."
    assert facts == {
        "actor": "pm_001",
        "reason": "Review rebalance.",
        "source_run_status": result.status,
        "selected_alternative_id": None,
    }
    assert metrics == {}
    assert reason_codes == []


def test_pre_run_source_analytics_payload_dispatches_configured_family() -> None:
    analytics = ProofPackSourceAnalytics(
        family="risk",
        state="READY",
        summary="Risk evidence is attached.",
        facts={"risk_report_id": "risk-report-001"},
        metrics={"volatility": "0.1200"},
        reason_codes=[],
        source_ref=_source_ref(),
        source_hash_key="risk_context",
        content_hash="sha256:risk-context",
    )

    state, summary, facts, metrics, reason_codes = builder_module._pre_run_source_analytics_payload(
        section_type="risk_impact",
        source_analytics={"risk": analytics},
    )

    assert state == "READY"
    assert summary == "Risk evidence is attached."
    assert facts == {"risk_report_id": "risk-report-001"}
    assert metrics == {"volatility": "0.1200"}
    assert reason_codes == []


def test_pre_run_adapter_payload_dispatches_configured_adapter_contract() -> None:
    state, summary, facts, metrics, reason_codes = builder_module._pre_run_adapter_payload(
        section_type="ai_refs",
    )

    assert state == "READY"
    assert summary == (
        "AI evidence input adapter is available with forbidden-action and forbidden-field guardrails."
    )
    assert facts == {"adapter_contract": "DpmProofPackAiEvidenceInput"}
    assert metrics == {}
    assert reason_codes == []


def test_pre_run_core_section_payload_dispatches_decision_summary() -> None:
    result = _ready_rebalance_result()

    state, summary, facts, metrics, reason_codes = builder_module._pre_run_core_section_payload(
        section_type="decision_summary",
        result=result,
        alternative_set=None,
        selected_alternative=None,
        selection=None,
        reason="Approve governed rebalance.",
        mandate_id=None,
        mandate_twin=None,
        mandate_health=None,
        mandate_evidence_gap_codes=[],
        created_by="pm_001",
    )

    assert state == "READY"
    assert summary == "Decision evidence assembled from manage run and actor rationale."
    assert facts == {
        "actor": "pm_001",
        "reason": "Approve governed rebalance.",
        "source_run_status": result.status,
        "selected_alternative_id": None,
    }
    assert metrics == {}
    assert reason_codes == []


def test_pre_run_section_payload_returns_decision_summary_missing_reason() -> None:
    result = _ready_rebalance_result()

    state, summary, facts, metrics, reason_codes = builder_module._pre_run_section_payload(
        section_type="decision_summary",
        result=result,
        alternative_set=None,
        selected_alternative=None,
        selection=None,
        reason=None,
        mandate_id=None,
        mandate_twin=None,
        mandate_health=None,
        mandate_evidence_gap_codes=[],
        created_by="pm_001",
        source_analytics={},
    )

    assert state == "DEGRADED"
    assert summary == "Decision evidence assembled from manage run and actor rationale."
    assert facts == {
        "actor": "pm_001",
        "reason": None,
        "source_run_status": result.status,
        "selected_alternative_id": None,
    }
    assert metrics == {}
    assert reason_codes == ["DPM_PROOF_PACK_REASON_MISSING"]


def test_pre_run_section_payload_ignores_run_required_sections() -> None:
    assert (
        builder_module._pre_run_section_payload(
            section_type="trade_intents",
            result=_ready_rebalance_result(),
            alternative_set=None,
            selected_alternative=None,
            selection=None,
            reason="Review rebalance.",
            mandate_id=None,
            mandate_twin=None,
            mandate_health=None,
            mandate_evidence_gap_codes=[],
            created_by="pm_001",
            source_analytics={},
        )
        is None
    )


def test_run_state_section_payload_blocks_missing_trade_intents() -> None:
    result = _ready_rebalance_result().model_copy(update={"intents": []})

    state, summary, facts, metrics, reason_codes = builder_module._run_state_section_payload(
        section_type="trade_intents",
        result=result,
    )

    assert state == "BLOCKED"
    assert summary == "No trade intents are available for pre-trade proof."
    assert facts == {"intent_ids": []}
    assert metrics == {"trade_count": 0}
    assert reason_codes == ["DPM_TRADE_INTENTS_MISSING"]


def test_trade_intents_section_payload_projects_ready_and_blocked_states() -> None:
    ready = _ready_rebalance_result()
    blocked = ready.model_copy(update={"intents": []})

    ready_state, _summary, ready_facts, ready_metrics, ready_reasons = (
        builder_module._trade_intents_section_payload(ready)
    )
    blocked_state, _summary, blocked_facts, blocked_metrics, blocked_reasons = (
        builder_module._trade_intents_section_payload(blocked)
    )

    assert ready_state == "READY"
    assert ready_facts["intent_ids"] == [intent.intent_id for intent in ready.intents]
    assert ready_metrics == {"trade_count": len(ready.intents)}
    assert ready_reasons == []
    assert blocked_state == "BLOCKED"
    assert blocked_facts == {"intent_ids": []}
    assert blocked_metrics == {"trade_count": 0}
    assert blocked_reasons == ["DPM_TRADE_INTENTS_MISSING"]


def test_after_state_section_payload_marks_blocked_runs() -> None:
    ready = _ready_rebalance_result()
    blocked = ready.model_copy(update={"status": "BLOCKED"})

    ready_state, _summary, _facts, ready_metrics, ready_reasons = (
        builder_module._after_state_section_payload(ready)
    )
    blocked_state, _summary, _facts, blocked_metrics, blocked_reasons = (
        builder_module._after_state_section_payload(blocked)
    )

    assert ready_state == "READY"
    assert ready_metrics == {"position_count": len(ready.after_simulated.positions)}
    assert ready_reasons == []
    assert blocked_state == "BLOCKED"
    assert blocked_metrics == {"position_count": len(blocked.after_simulated.positions)}
    assert blocked_reasons == ["DPM_AFTER_STATE_BLOCKED"]


def test_run_state_section_payload_ignores_unrelated_sections() -> None:
    assert (
        builder_module._run_state_section_payload(
            section_type="tax_impact",
            result=_ready_rebalance_result(),
        )
        is None
    )


def test_run_diagnostics_section_payload_returns_ready_liquidity_posture() -> None:
    state, summary, facts, metrics, reason_codes = builder_module._run_diagnostics_section_payload(
        section_type="liquidity_and_cash",
        result=_ready_rebalance_result(),
    )

    assert state == "READY"
    assert summary == "Liquidity and cash posture captured from run diagnostics."
    assert facts["cash_ladder_breaches"] == []
    assert metrics == {"breach_count": 0}
    assert reason_codes == []


def test_run_diagnostics_section_payload_returns_currency_overlay_fallback() -> None:
    state, summary, facts, metrics, reason_codes = builder_module._run_diagnostics_section_payload(
        section_type="currency_overlay_evidence",
        result=_ready_rebalance_result(),
    )

    assert state == "DEGRADED"
    assert summary == "Currency-overlay authority context is not attached."
    assert facts == {}
    assert metrics == {}
    assert reason_codes == ["DPM_CURRENCY_OVERLAY_CONTEXT_MISSING"]


def test_liquidity_and_cash_section_payload_marks_cash_breaches() -> None:
    result = _ready_rebalance_result()
    result = result.model_copy(
        update={
            "diagnostics": result.diagnostics.model_copy(
                update={
                    "cash_ladder_breaches": [
                        CashLadderBreach(
                            date_offset=2,
                            currency="USD",
                            projected_balance=Decimal("-25"),
                            allowed_floor=Decimal("0"),
                            reason_code="OVERDRAFT_ON_T_PLUS_2",
                        )
                    ]
                }
            )
        }
    )

    state, _summary, facts, metrics, reason_codes = (
        builder_module._liquidity_and_cash_section_payload(result)
    )

    assert state == "BLOCKED"
    assert facts["cash_ladder_breaches"][0]["reason_code"] == "OVERDRAFT_ON_T_PLUS_2"
    assert metrics == {"breach_count": 1}
    assert reason_codes == ["DPM_CASH_LADDER_BREACH"]


def test_fx_funding_plan_section_payload_marks_missing_pairs() -> None:
    result = _ready_rebalance_result()
    result = result.model_copy(
        update={
            "diagnostics": result.diagnostics.model_copy(
                update={
                    "missing_fx_pairs": ["USD/SGD"],
                    "funding_plan": [
                        FundingPlanEntry(
                            target_currency="SGD",
                            required=Decimal("100"),
                            available_before_fx=Decimal("25"),
                            fx_needed=Decimal("75"),
                            fx_pair=None,
                            funding_currency=None,
                        )
                    ],
                }
            )
        }
    )

    state, _summary, facts, metrics, reason_codes = builder_module._fx_funding_plan_section_payload(
        result
    )

    assert state == "BLOCKED"
    assert facts["missing_fx_pairs"] == ["USD/SGD"]
    assert facts["funding_plan"][0]["target_currency"] == "SGD"
    assert metrics == {"missing_fx_pair_count": 1}
    assert reason_codes == ["DPM_REQUIRED_FX_PAIR_MISSING"]


def test_run_policy_section_payload_returns_direct_run_drift_fallback() -> None:
    state, summary, facts, metrics, reason_codes = builder_module._run_policy_section_payload(
        section_type="drift_impact",
        result=_ready_rebalance_result(),
        selected_alternative=None,
    )

    assert state == "DEGRADED"
    assert summary == "Direct-run proof has no construction comparison drift trace."
    assert facts == {}
    assert metrics == {}
    assert reason_codes == ["DPM_DRIFT_COMPARISON_UNAVAILABLE"]


def test_run_policy_section_payload_returns_missing_tax_impact_posture() -> None:
    state, summary, facts, metrics, reason_codes = builder_module._run_policy_section_payload(
        section_type="tax_impact",
        result=_ready_rebalance_result(),
        selected_alternative=None,
    )

    assert state == "DEGRADED"
    assert summary == "Tax impact is not available for this run."
    assert facts == {}
    assert metrics == {}
    assert reason_codes == ["DPM_TAX_IMPACT_MISSING"]


def test_drift_impact_section_payload_preserves_selected_alternative_metrics() -> None:
    alternative = build_rebalance_result_alternative(result=_ready_rebalance_result())
    alternative_set = build_alternative_set(
        alternative_set_id="cas_drift_policy",
        portfolio_id="pf_proof_pack_1",
        as_of="2026-05-03",
        alternatives=[alternative],
    )
    selected_alternative = alternative_set.alternatives[0]

    state, summary, facts, metrics, reason_codes = builder_module._drift_impact_section_payload(
        selected_alternative=selected_alternative
    )

    assert state == "READY"
    assert summary == "Drift impact captured from construction comparison metrics."
    assert facts == {}
    assert metrics == selected_alternative.comparison_metrics.model_dump(mode="json")
    assert reason_codes == []


def test_rule_results_section_payload_blocks_on_hard_failed_policy_rule() -> None:
    result = _ready_rebalance_result().model_copy(
        update={
            "rule_results": [
                RuleResult(
                    rule_id="NO_SHORTING",
                    severity="HARD",
                    status="FAIL",
                    measured=Decimal("-1"),
                    threshold={"minimum_weight": Decimal("0")},
                    reason_code="DPM_NO_SHORTING",
                )
            ]
        }
    )

    state, summary, facts, metrics, reason_codes = builder_module._rule_results_section_payload(
        result=result
    )

    assert state == "BLOCKED"
    assert summary == "Rule results captured from manage policy engine."
    assert facts["rule_results"][0]["rule_id"] == "NO_SHORTING"
    assert metrics == {"fail_count": 1}
    assert reason_codes == ["DPM_NO_SHORTING"]


def test_run_bound_section_payload_dispatches_state_policy_and_diagnostics() -> None:
    result = _ready_rebalance_result().model_copy(update={"intents": []})

    trade_state, _trade_summary, _trade_facts, trade_metrics, trade_reasons = (
        builder_module._run_bound_section_payload(
            section_type="trade_intents",
            result=result,
            selected_alternative=None,
            source_analytics={},
        )
    )
    tax_state, tax_summary, _tax_facts, _tax_metrics, tax_reasons = (
        builder_module._run_bound_section_payload(
            section_type="tax_impact",
            result=result,
            selected_alternative=None,
            source_analytics={},
        )
    )
    liquidity_state, liquidity_summary, _facts, liquidity_metrics, liquidity_reasons = (
        builder_module._run_bound_section_payload(
            section_type="liquidity_and_cash",
            result=result,
            selected_alternative=None,
            source_analytics={},
        )
    )

    assert trade_state == "BLOCKED"
    assert trade_metrics == {"trade_count": 0}
    assert trade_reasons == ["DPM_TRADE_INTENTS_MISSING"]
    assert tax_state == "DEGRADED"
    assert tax_summary == "Tax impact is not available for this run."
    assert tax_reasons == ["DPM_TAX_IMPACT_MISSING"]
    assert liquidity_state == "READY"
    assert liquidity_summary == "Liquidity and cash posture captured from run diagnostics."
    assert liquidity_metrics == {"breach_count": 0}
    assert liquidity_reasons == []


def test_run_bound_section_payload_ignores_unhandled_sections() -> None:
    assert (
        builder_module._run_bound_section_payload(
            section_type="lineage",
            result=_ready_rebalance_result(),
            selected_alternative=None,
            source_analytics={},
        )
        is None
    )


def test_approval_requirements_section_payload_orders_workflow_decisions() -> None:
    result = _ready_rebalance_result().model_copy(update={"status": "PENDING_REVIEW"})
    later = DpmRunWorkflowDecisionRecord(
        decision_id="dwd_later",
        run_id=result.rebalance_run_id,
        action="APPROVE",
        reason_code="LATER",
        actor_id="pm_002",
        decided_at=datetime(2026, 5, 3, 10, 0, tzinfo=timezone.utc),
        correlation_id="corr-later",
    )
    earlier = DpmRunWorkflowDecisionRecord(
        decision_id="dwd_earlier",
        run_id=result.rebalance_run_id,
        action="REQUEST_CHANGES",
        reason_code="EARLIER",
        actor_id="pm_001",
        decided_at=datetime(2026, 5, 3, 9, 0, tzinfo=timezone.utc),
        correlation_id="corr-earlier",
    )

    state, summary, facts, metrics, reason_codes = (
        builder_module._approval_requirements_section_payload(
            result=result,
            workflow_decisions=[later, earlier],
        )
    )

    assert state == "PENDING_REVIEW"
    assert summary == "Approval posture captured from run status and gate decision."
    assert [decision["decision_id"] for decision in facts["workflow_decisions"]] == [
        "dwd_earlier",
        "dwd_later",
    ]
    assert metrics == {"workflow_decision_count": 2}
    assert reason_codes == []


def test_approval_requirements_section_payload_blocks_for_blocked_run() -> None:
    result = _ready_rebalance_result().model_copy(update={"status": "BLOCKED"})

    state, _summary, facts, metrics, reason_codes = (
        builder_module._approval_requirements_section_payload(
            result=result,
            workflow_decisions=[],
        )
    )

    assert state == "BLOCKED"
    assert facts["workflow_decisions"] == []
    assert metrics == {"workflow_decision_count": 0}
    assert reason_codes == []


def test_approval_section_state_uses_gate_required_review_and_blocked_precedence() -> None:
    result = _ready_rebalance_result()
    review_gate = GateDecision(
        gate="MANDATE_APPROVAL_REQUIRED",
        recommended_next_step="REQUEST_MANDATE_APPROVAL",
        reasons=[],
        summary=GateDecisionSummary(
            hard_fail_count=0,
            soft_fail_count=1,
            new_high_suitability_count=0,
            new_medium_suitability_count=0,
        ),
    )
    blocked_gate = review_gate.model_copy(
        update={"gate": "BLOCKED", "recommended_next_step": "FIX_INPUT"}
    )

    assert (
        builder_module._approval_section_state(result=result, gate=review_gate) == "PENDING_REVIEW"
    )
    assert builder_module._approval_section_state(result=result, gate=blocked_gate) == "BLOCKED"
    assert (
        builder_module._approval_section_state(
            result=result.model_copy(update={"status": "BLOCKED"}),
            gate=review_gate,
        )
        == "BLOCKED"
    )


def test_approval_support_helpers_serialize_ordered_facts_and_reason_codes() -> None:
    result = _ready_rebalance_result()
    later = DpmRunWorkflowDecisionRecord(
        decision_id="dwd_later",
        run_id=result.rebalance_run_id,
        action="APPROVE",
        reason_code="LATER",
        actor_id="pm_002",
        decided_at=datetime(2026, 5, 3, 10, 0, tzinfo=timezone.utc),
        correlation_id="corr-later",
    )
    earlier = later.model_copy(
        update={
            "decision_id": "dwd_earlier",
            "reason_code": "EARLIER",
            "actor_id": "pm_001",
            "decided_at": datetime(2026, 5, 3, 9, 0, tzinfo=timezone.utc),
            "correlation_id": "corr-earlier",
        }
    )
    gate = GateDecision(
        gate="COMPLIANCE_REVIEW_REQUIRED",
        recommended_next_step="COMPLIANCE_REVIEW",
        reasons=[
            GateReason(
                reason_code="DPM_COMPLIANCE_REVIEW_REQUIRED",
                severity="HIGH",
                source="SUITABILITY",
            )
        ],
        summary=GateDecisionSummary(
            hard_fail_count=0,
            soft_fail_count=0,
            new_high_suitability_count=1,
            new_medium_suitability_count=0,
        ),
    )

    facts = builder_module._approval_workflow_decision_facts([later, earlier])

    assert [fact["decision_id"] for fact in facts] == ["dwd_earlier", "dwd_later"]
    assert builder_module._approval_gate_fact(gate)["gate"] == "COMPLIANCE_REVIEW_REQUIRED"
    assert builder_module._approval_reason_codes(gate) == ["DPM_COMPLIANCE_REVIEW_REQUIRED"]
    assert builder_module._approval_reason_codes(None) == []


def test_proof_pack_governance_section_payload_orders_workflow_decisions() -> None:
    result = _ready_rebalance_result().model_copy(update={"status": "PENDING_REVIEW"})
    later = DpmRunWorkflowDecisionRecord(
        decision_id="dwd_later",
        run_id=result.rebalance_run_id,
        action="APPROVE",
        reason_code="LATER",
        actor_id="pm_002",
        decided_at=datetime(2026, 5, 3, 10, 0, tzinfo=timezone.utc),
        correlation_id="corr-later",
    )
    earlier = DpmRunWorkflowDecisionRecord(
        decision_id="dwd_earlier",
        run_id=result.rebalance_run_id,
        action="REQUEST_CHANGES",
        reason_code="EARLIER",
        actor_id="pm_001",
        decided_at=datetime(2026, 5, 3, 9, 0, tzinfo=timezone.utc),
        correlation_id="corr-earlier",
    )

    state, summary, facts, metrics, reason_codes = (
        builder_module._proof_pack_governance_section_payload(
            section_type="approval_requirements",
            result=result,
            run=_run_record(result=result),
            selection=None,
            source_ref_count=3,
            workflow_decisions=[later, earlier],
        )
    )

    assert state == "PENDING_REVIEW"
    assert summary == "Approval posture captured from run status and gate decision."
    assert [decision["decision_id"] for decision in facts["workflow_decisions"]] == [
        "dwd_earlier",
        "dwd_later",
    ]
    assert metrics == {"workflow_decision_count": 2}
    assert reason_codes == []


def test_proof_pack_governance_section_payload_tracks_lineage_refs() -> None:
    result = _ready_rebalance_result()

    state, summary, facts, metrics, reason_codes = (
        builder_module._proof_pack_governance_section_payload(
            section_type="lineage",
            result=result,
            run=_run_record(result=result),
            selection=None,
            source_ref_count=7,
            workflow_decisions=[],
        )
    )

    assert state == "READY"
    assert summary == "Lineage identifiers captured from source run and source artifacts."
    assert facts["source_system"] == result.lineage.source_system
    assert metrics == {"source_ref_count": 7}
    assert reason_codes == []


def test_operations_handoff_section_payload_marks_non_ready_for_review() -> None:
    result = _ready_rebalance_result().model_copy(update={"status": "PENDING_REVIEW"})

    state, summary, facts, metrics, reason_codes = (
        builder_module._operations_handoff_section_payload(result=result)
    )

    assert state == "PENDING_REVIEW"
    assert summary == "Operations handoff reflects current pre-trade readiness."
    assert facts == {"run_status": "PENDING_REVIEW"}
    assert metrics == {}
    assert reason_codes == ["DPM_OPERATIONS_REVIEW_REQUIRED"]


def test_decision_timeline_section_payload_projects_run_and_selection_refs() -> None:
    result = _ready_rebalance_result()
    run = _run_record(result=result)

    state, summary, facts, metrics, reason_codes = (
        builder_module._decision_timeline_section_payload(
            run=run,
            selection=None,
        )
    )

    assert state == "READY"
    assert summary == (
        "Timeline generated from source run, selection, and proof-pack generation events."
    )
    assert facts == {"run_created_at": run.created_at.isoformat(), "selection_id": None}
    assert metrics == {}
    assert reason_codes == []


def test_supportability_section_payload_is_ready_placeholder() -> None:
    assert builder_module._supportability_section_payload() == (
        "READY",
        "Supportability summary is generated for every proof pack.",
        {},
        {},
        [],
    )


def test_mandate_context_section_payload_blocks_missing_identity() -> None:
    state, summary, facts, metrics, reason_codes = builder_module._mandate_context_section_payload(
        mandate_id=None,
        mandate_twin=None,
        mandate_health=None,
        mandate_evidence_gap_codes=[],
    )

    assert state == "BLOCKED"
    assert summary == "Mandate identity is required before proof-pack promotion."
    assert facts == {"mandate_id": None}
    assert metrics == {}
    assert reason_codes == ["DPM_PROOF_PACK_MANDATE_ID_MISSING"]


def test_mandate_context_section_payload_projects_health_evidence() -> None:
    mandate_twin = _mandate_twin()
    mandate_health = calculate_mandate_health(DpmMandateHealthInput(twin=mandate_twin))

    state, summary, facts, metrics, reason_codes = builder_module._mandate_context_section_payload(
        mandate_id=mandate_twin.mandate_id,
        mandate_twin=mandate_twin,
        mandate_health=mandate_health,
        mandate_evidence_gap_codes=[],
    )

    assert state == "PENDING_REVIEW"
    assert summary == (
        "Mandate digital-twin and health evidence are attached from persisted RFC-0038 truth."
    )
    assert facts["mandate_id"] == mandate_twin.mandate_id
    assert facts["health_snapshot_id"] == mandate_health.health_snapshot_id
    assert metrics["dimension_count"] == len(mandate_health.dimension_scores)
    assert metrics["source_lineage_count"] == len(mandate_twin.source_lineage)
    assert reason_codes == [reason.reason_code for reason in mandate_health.top_reasons]


def test_selected_alternative_section_payload_degrades_without_selection() -> None:
    state, summary, facts, metrics, reason_codes = (
        builder_module._selected_alternative_section_payload(
            alternative_set=None,
            selected_alternative=None,
            selection=None,
        )
    )

    assert state == "DEGRADED"
    assert summary == "Direct-run proof pack has no selected construction alternative."
    assert facts == {}
    assert metrics == {}
    assert reason_codes == ["DPM_DIRECT_RUN_NO_SELECTED_ALTERNATIVE"]


def test_selected_alternative_section_payload_projects_method_trace() -> None:
    result = _ready_rebalance_result()
    alternative = build_rebalance_result_alternative(result=result)
    alternative_set = build_alternative_set(
        alternative_set_id="cas_selected_section",
        portfolio_id="pf_proof_pack_1",
        as_of="2026-05-03",
        alternatives=[alternative],
    ).model_copy(update={"generated_at": CREATED_AT})
    selection = ConstructionAlternativeSelection(
        selection_id="sel_selected_section",
        alternative_set_id=alternative_set.alternative_set_id,
        alternative_id=alternative.alternative_id,
        actor_id="pm_001",
        reason_code="MODEL_DRIFT_REVIEW",
    )

    state, summary, facts, metrics, reason_codes = (
        builder_module._selected_alternative_section_payload(
            alternative_set=alternative_set,
            selected_alternative=alternative,
            selection=selection,
        )
    )

    assert state == "READY"
    assert summary == "Selected construction alternative captured with method and trace evidence."
    assert facts["alternative_set_id"] == "cas_selected_section"
    assert facts["selected_alternative_id"] == alternative.alternative_id
    assert facts["selection_id"] == "sel_selected_section"
    assert facts["objective_trace"]
    assert facts["constraint_trace"]
    assert metrics == alternative.comparison_metrics.model_dump(mode="json")
    assert reason_codes == []


def test_decision_timeline_orders_source_workflow_and_generated_events() -> None:
    result = _ready_rebalance_result()
    run = _run_record(result=result)
    alternative = build_rebalance_result_alternative(result=result)
    alternative_set = build_alternative_set(
        alternative_set_id="cas_timeline_order",
        portfolio_id="pf_proof_pack_1",
        as_of="2026-05-03",
        alternatives=[alternative],
    ).model_copy(update={"generated_at": CREATED_AT})
    selection = ConstructionAlternativeSelection(
        selection_id="sel_timeline_order",
        alternative_set_id=alternative_set.alternative_set_id,
        alternative_id=alternative.alternative_id,
        selected_at=CREATED_AT,
        actor_id="pm_001",
        reason_code="MODEL_DRIFT_REVIEW",
    )
    decision = DpmRunWorkflowDecisionRecord(
        decision_id="dwd_timeline_order",
        run_id=run.rebalance_run_id,
        action="APPROVE",
        reason_code="REVIEW_APPROVED",
        comment="Evidence reviewed.",
        actor_id="reviewer_001",
        decided_at=CREATED_AT,
        correlation_id="corr-timeline-order",
    )

    timeline = builder_module._decision_timeline(
        proof_pack_id="dpp_timeline_order",
        generated_at=CREATED_AT.isoformat(),
        source_type="SELECTED_ALTERNATIVE",
        run=run,
        alternative_set=alternative_set,
        selected_alternative=alternative,
        selection=selection,
        workflow_decisions=[decision],
        created_by="pm_001",
    )

    assert [event.event_type for event in timeline.events] == [
        "REBALANCE_RUN_CREATED",
        "ALTERNATIVE_SET_GENERATED",
        "SELECTED_ALTERNATIVE",
        "WORKFLOW_DECISION",
        "PROOF_PACK_GENERATED",
    ]


def test_selected_alternative_timeline_event_falls_back_to_creator_without_selection() -> None:
    alternative = build_rebalance_result_alternative(result=_ready_rebalance_result())

    event = builder_module._selected_alternative_timeline_event(
        selected_alternative=alternative,
        selection=None,
        generated_at=CREATED_AT.isoformat(),
        created_by="pm_fallback",
    )

    assert event.event_id == f"{alternative.alternative_id}:selected"
    assert event.event_time == CREATED_AT.isoformat()
    assert event.actor == "pm_fallback"
    assert event.status == alternative.method_status
    assert event.reason_codes == []


def test_workflow_decision_timeline_events_project_review_evidence() -> None:
    decision = DpmRunWorkflowDecisionRecord(
        decision_id="dwd_timeline_review",
        run_id="rr_timeline_review",
        action="REJECT",
        reason_code="REMEDIATION_REQUIRED",
        comment="Fix source evidence.",
        actor_id="reviewer_002",
        decided_at=CREATED_AT,
        correlation_id="corr-timeline-review",
    )

    events = builder_module._workflow_decision_timeline_events([decision])

    assert len(events) == 1
    assert events[0].event_id == "dwd_timeline_review:workflow_decision"
    assert events[0].event_type == "WORKFLOW_DECISION"
    assert events[0].event_time == CREATED_AT.isoformat()
    assert events[0].actor == "reviewer_002"
    assert events[0].status == "REJECT"
    assert events[0].reason_codes == ["REMEDIATION_REQUIRED"]


def test_source_readiness_section_payload_blocks_missing_run() -> None:
    state, summary, facts, metrics, reason_codes = builder_module._source_readiness_section_payload(
        result=None
    )

    assert state == "BLOCKED"
    assert summary == "No source run is available."
    assert facts == {}
    assert metrics == {}
    assert reason_codes == ["DPM_SOURCE_RUN_MISSING"]


def test_source_readiness_section_payload_degrades_on_lineage_state() -> None:
    result = _ready_rebalance_result()
    result = result.model_copy(
        update={
            "lineage": result.lineage.model_copy(
                update={
                    "input_mode": "stateful",
                    "source_system": "lotus-core",
                    "source_supportability_state": "DEGRADED",
                }
            )
        }
    )

    state, summary, facts, metrics, reason_codes = builder_module._source_readiness_section_payload(
        result=result
    )

    assert state == "DEGRADED"
    assert summary == "Source readiness captured from run lineage."
    assert facts == {
        "input_mode": "stateful",
        "source_system": "lotus-core",
        "source_supportability_state": "DEGRADED",
    }
    assert metrics == {}
    assert reason_codes == ["DPM_SOURCE_READINESS_DEGRADED"]


def test_turnover_and_cost_section_payload_degrades_without_selected_metrics() -> None:
    state, summary, facts, metrics, reason_codes = (
        builder_module._turnover_and_cost_section_payload(
            selected_alternative=None,
            source_analytics={},
        )
    )

    assert state == "DEGRADED"
    assert summary == "Turnover and cost evidence captured when construction metrics are available."
    assert facts == {}
    assert metrics == {}
    assert reason_codes == ["DPM_TURNOVER_COST_METRICS_MISSING"]


def test_turnover_and_cost_section_payload_merges_source_cost_context() -> None:
    result = _ready_rebalance_result()
    alternative = build_rebalance_result_alternative(result=result)
    cost_context = AuthoritativeTransactionCostContext(
        supportability_status="READY",
        source_system="lotus-core",
        source_id="transaction-cost-scope-001",
        content_hash="sha256:transaction-cost-curve-proof",
        as_of_date="2026-05-03",
        window_start_date="2026-02-02",
        window_end_date="2026-05-03",
        returned_curve_point_count=1,
        reason_codes=["TRANSACTION_COST_CURVE_READY"],
        curve_points=[
            AuthoritativeTransactionCostPoint(
                security_id="EQ_B",
                transaction_type="BUY",
                currency="USD",
                observation_count=3,
                total_notional=Decimal("30000"),
                total_cost=Decimal("15"),
                average_cost_bps=Decimal("5.0000"),
                min_cost_bps=Decimal("4.5000"),
                max_cost_bps=Decimal("5.5000"),
                first_observed_date="2026-04-01",
                last_observed_date="2026-05-03",
            )
        ],
    )
    transaction_cost = source_analytics_for_context(
        source_context=cost_context.model_dump(mode="json", exclude_none=True),
        family="transaction_cost",
    )

    assert transaction_cost is not None

    state, summary, facts, metrics, reason_codes = (
        builder_module._turnover_and_cost_section_payload(
            selected_alternative=alternative,
            source_analytics={"transaction_cost": transaction_cost},
        )
    )

    assert state == "READY"
    assert (
        summary
        == "Turnover metrics and source-owned observed transaction-cost evidence are attached."
    )
    assert facts["source_system"] == "lotus-core"
    assert facts["curve_points"][0]["average_cost_bps"] == "5.0000"
    assert metrics["returned_curve_point_count"] == 1
    assert metrics["represented_observation_count"] == 3
    assert metrics["estimated_transaction_cost"] is None
    assert reason_codes == ["TRANSACTION_COST_CURVE_READY"]


def test_eligibility_and_restrictions_section_payload_reports_universe_exclusions() -> None:
    result = _ready_rebalance_result()
    result = result.model_copy(
        update={
            "universe": result.universe.model_copy(
                update={
                    "excluded": [
                        ExcludedInstrument(
                            instrument_id="PRIVATE_CREDIT_FUND",
                            reason_code="SHELF_NOT_APPROVED",
                            details="Instrument is outside the approved shelf.",
                        )
                    ]
                }
            )
        }
    )

    state, summary, facts, metrics, reason_codes = (
        builder_module._eligibility_and_restrictions_section_payload(
            result=result,
            source_analytics={},
        )
    )

    assert state == "PENDING_REVIEW"
    assert summary == "Eligibility and restriction evidence captured from source run universe."
    assert facts["excluded"][0]["instrument_id"] == "PRIVATE_CREDIT_FUND"
    assert metrics == {"excluded_count": 1}
    assert reason_codes == ["DPM_UNIVERSE_EXCLUSIONS_PRESENT"]


def test_eligibility_and_restrictions_section_payload_merges_restriction_context() -> None:
    result = _ready_rebalance_result()
    result = result.model_copy(
        update={
            "universe": result.universe.model_copy(
                update={
                    "excluded": [
                        ExcludedInstrument(
                            instrument_id="PRIVATE_CREDIT_FUND",
                            reason_code="CLIENT_RESTRICTION",
                        )
                    ]
                }
            )
        }
    )
    restriction_context = AuthoritativeClientRestrictionContext(
        supportability_status="READY",
        source_system="lotus-core",
        source_id="sha256:client-restrictions",
        content_hash="sha256:client-restrictions",
        portfolio_id="pf_proof_pack_1",
        client_id="client_001",
        mandate_id="mandate_001",
        as_of_date="2026-05-03",
        restriction_count=1,
        reason_codes=["CLIENT_RESTRICTION_PROFILE_READY"],
        restrictions=[
            AuthoritativeClientRestrictionRule(
                restriction_scope="instrument",
                restriction_code="NO_PRIVATE_CREDIT_BUY",
                restriction_status="active",
                restriction_source="client_mandate",
                applies_to_buy=True,
                applies_to_sell=False,
                instrument_ids=["PRIVATE_CREDIT_FUND"],
                effective_from="2026-01-01",
                restriction_version=1,
            )
        ],
    )
    restriction = source_analytics_for_context(
        source_context=restriction_context.model_dump(mode="json", exclude_none=True),
        family="client_restriction",
    )

    assert restriction is not None

    state, summary, facts, metrics, reason_codes = (
        builder_module._eligibility_and_restrictions_section_payload(
            result=result,
            source_analytics={"client_restriction": restriction},
        )
    )

    assert state == "PENDING_REVIEW"
    assert (
        summary == "Eligibility evidence and source-owned client restriction profile are attached."
    )
    assert facts["source_product_name"] == "ClientRestrictionProfile"
    assert facts["restrictions"][0]["restriction_code"] == "NO_PRIVATE_CREDIT_BUY"
    assert facts["excluded"][0]["instrument_id"] == "PRIVATE_CREDIT_FUND"
    assert metrics == {"restriction_count": 1, "excluded_count": 1}
    assert reason_codes == [
        "CLIENT_RESTRICTION_PROFILE_READY",
        "DPM_UNIVERSE_EXCLUSIONS_PRESENT",
    ]


def test_run_source_context_section_payload_dispatches_source_context_sections() -> None:
    result = _ready_rebalance_result()

    scenario_state, scenario_summary, _facts, scenario_metrics, scenario_reasons = (
        builder_module._run_source_context_section_payload(
            section_type="scenario_and_regime_evidence",
            result=result,
            source_analytics={},
        )
    )
    eligibility_state, eligibility_summary, eligibility_facts, eligibility_metrics, reasons = (
        builder_module._run_source_context_section_payload(
            section_type="eligibility_and_restrictions",
            result=result,
            source_analytics={},
        )
    )

    assert scenario_state == "DEGRADED"
    assert scenario_summary == "Scenario/regime authority context is not attached."
    assert scenario_metrics == {}
    assert scenario_reasons == ["DPM_SCENARIO_CONTEXT_MISSING"]
    assert eligibility_state == "READY"
    assert (
        eligibility_summary
        == "Eligibility and restriction evidence captured from source run universe."
    )
    assert eligibility_facts == {"excluded": []}
    assert eligibility_metrics == {"excluded_count": 0}
    assert reasons == []


def test_run_source_context_section_payload_ignores_unhandled_sections() -> None:
    assert (
        builder_module._run_source_context_section_payload(
            section_type="lineage",
            result=_ready_rebalance_result(),
            source_analytics={},
        )
        is None
    )


def test_direct_run_proof_pack_generates_every_section_with_truthful_states() -> None:
    run = _run_record()
    decision = DpmRunWorkflowDecisionRecord(
        decision_id="dwd_proof_pack_1",
        run_id=run.rebalance_run_id,
        action="APPROVE",
        reason_code="REVIEW_APPROVED",
        comment="Evidence reviewed.",
        actor_id="reviewer_001",
        decided_at=CREATED_AT,
        correlation_id="corr-workflow-proof-pack",
    )
    pack = build_proof_pack_from_run(
        run=run,
        created_by="pm_001",
        reason="Rebalance back to model after drift review.",
        created_at=CREATED_AT,
        mandate_id="mandate_001",
        mandate_twin=_mandate_twin(),
        mandate_health=calculate_mandate_health(DpmMandateHealthInput(twin=_mandate_twin())),
        workflow_decisions=[decision],
    )

    assert pack.source_type == "REBALANCE_RUN"
    assert len(pack.sections) == 27
    assert pack.content_hash.startswith("sha256:")
    assert pack.source_hashes["rebalance_run"].startswith("sha256:")
    assert _section(pack, "before_state").state == "READY"
    assert _section(pack, "mandate_context").state == "PENDING_REVIEW"
    assert pack.source_hashes["mandate_twin"].startswith("sha256:")
    assert pack.source_hashes["mandate_health"].startswith("sha256:")
    assert _section(pack, "trade_intents").metrics["trade_count"] == 2
    assert _section(pack, "approval_requirements").metrics["workflow_decision_count"] == 1
    assert any(event.event_type == "WORKFLOW_DECISION" for event in pack.decision_timeline.events)
    assert _section(pack, "selected_alternative").state == "DEGRADED"
    assert "DPM_DIRECT_RUN_NO_SELECTED_ALTERNATIVE" in pack.supportability.reason_codes
    assert _section(pack, "reporting_refs").state == "READY"
    assert _section(pack, "reporting_refs").facts["adapter_contract"] == "DpmProofPackReportInput"
    assert _section(pack, "ai_refs").state == "READY"
    assert _section(pack, "ai_refs").facts["adapter_contract"] == "DpmProofPackAiEvidenceInput"
    assert pack.status == "PENDING_REVIEW"


def test_missing_mandate_identity_blocks_promotion_without_hiding_other_evidence() -> None:
    pack = build_proof_pack_from_run(
        run=_run_record(),
        created_by="pm_001",
        reason="Rebalance back to model after drift review.",
        created_at=CREATED_AT,
    )

    mandate = _section(pack, "mandate_context")
    assert mandate.state == "BLOCKED"
    assert "DPM_PROOF_PACK_MANDATE_ID_MISSING" in mandate.reason_codes
    assert pack.status == "BLOCKED"
    assert _section(pack, "before_state").state == "READY"


def test_mandate_context_degrades_when_only_identifier_is_available() -> None:
    pack = build_proof_pack_from_run(
        run=_run_record(),
        created_by="pm_001",
        reason="Rebalance back to model after drift review.",
        created_at=CREATED_AT,
        mandate_id="mandate_001",
    )

    mandate = _section(pack, "mandate_context")
    assert mandate.state == "DEGRADED"
    assert mandate.reason_codes == ["DPM_MANDATE_TWIN_EVIDENCE_MISSING"]
    assert "mandate_twin" not in pack.source_hashes


def test_mandate_context_degrades_when_health_snapshot_is_missing() -> None:
    mandate_twin = _mandate_twin()
    pack = build_proof_pack_from_run(
        run=_run_record(),
        created_by="pm_001",
        reason="Rebalance back to model after drift review.",
        created_at=CREATED_AT,
        mandate_id=mandate_twin.mandate_id,
        mandate_twin=mandate_twin,
    )

    mandate = _section(pack, "mandate_context")
    assert mandate.state == "DEGRADED"
    assert "DPM_MANDATE_HEALTH_EVIDENCE_MISSING" in mandate.reason_codes
    assert pack.source_hashes["mandate_twin"].startswith("sha256:")
    assert "mandate_health" not in pack.source_hashes


@pytest.mark.parametrize(
    ("health_state", "source_readiness_state", "expected_section_state"),
    [
        (MandateHealthState.READY, "READY", "READY"),
        (MandateHealthState.READY, "DEGRADED", "DEGRADED"),
        (MandateHealthState.BLOCKED, "READY", "BLOCKED"),
    ],
)
def test_mandate_context_state_follows_health_and_source_readiness(
    health_state: MandateHealthState,
    source_readiness_state: str,
    expected_section_state: str,
) -> None:
    mandate_twin = _mandate_twin()
    mandate_health = calculate_mandate_health(DpmMandateHealthInput(twin=mandate_twin)).model_copy(
        update={
            "health_state": health_state,
            "source_readiness_state": source_readiness_state,
            "top_reasons": [],
        }
    )

    pack = build_proof_pack_from_run(
        run=_run_record(),
        created_by="pm_001",
        reason="Rebalance back to model after drift review.",
        created_at=CREATED_AT,
        mandate_id=mandate_twin.mandate_id,
        mandate_twin=mandate_twin,
        mandate_health=mandate_health,
    )

    assert _section(pack, "mandate_context").state == expected_section_state


def test_builder_covers_trade_tax_approval_and_defensive_source_edges() -> None:
    base_result = _ready_rebalance_result()
    no_intent_pack = build_proof_pack_from_run(
        run=_run_record(result=base_result.model_copy(update={"intents": []})),
        created_by="pm_001",
        reason=None,
        created_at=CREATED_AT,
        mandate_id="mandate_001",
    )
    tax_pack = build_proof_pack_from_run(
        run=_run_record(
            result=base_result.model_copy(
                update={
                    "tax_impact": TaxImpact(
                        total_realized_gain=Money(amount=Decimal("0"), currency="USD"),
                        total_realized_loss=Money(amount=Decimal("0"), currency="USD"),
                    )
                }
            )
        ),
        created_by="pm_001",
        reason=None,
        created_at=CREATED_AT,
        mandate_id="mandate_001",
    )
    pending_pack = build_proof_pack_from_run(
        run=_run_record(result=base_result.model_copy(update={"status": "PENDING_REVIEW"})),
        created_by="pm_001",
        reason=None,
        created_at=CREATED_AT,
        mandate_id="mandate_001",
    )
    blocked_pack = build_proof_pack_from_run(
        run=_run_record(result=base_result.model_copy(update={"status": "BLOCKED"})),
        created_by="pm_001",
        reason=None,
        created_at=CREATED_AT,
        mandate_id="mandate_001",
    )

    assert _section(no_intent_pack, "trade_intents").state == "BLOCKED"
    assert _section(tax_pack, "tax_impact").state == "READY"
    assert _section(pending_pack, "approval_requirements").state == "PENDING_REVIEW"
    assert _section(blocked_pack, "approval_requirements").state == "BLOCKED"
    assert builder_module._aggregate_status({}) == "READY"
    with pytest.raises(ProofPackSourceValidationError, match="DPM_PROOF_PACK_SOURCE_MISSING"):
        builder_module._resolve_portfolio_id(run=None, alternative_set=None)
    with pytest.raises(ProofPackSourceValidationError, match="DPM_PROOF_PACK_SOURCE_MISSING"):
        builder_module._as_of_date(run=None, alternative_set=None)
    with pytest.raises(ProofPackSourceValidationError, match="DPM_PROOF_PACK_SOURCE_MISSING"):
        builder_module._proof_pack_id(
            source_type="REBALANCE_RUN",
            run=None,
            alternative_set=None,
            selected_alternative=None,
        )
    with pytest.raises(AssertionError, match="Unhandled proof-pack section type"):
        builder_module._section_payload(
            section_type="unsupported",
            result=base_result,
            run=_run_record(result=base_result),
            run_artifact_hash=None,
            alternative_set=None,
            selected_alternative=None,
            selection=None,
            reason=None,
            mandate_id="mandate_001",
            mandate_twin=None,
            mandate_health=None,
            mandate_evidence_gap_codes=[],
            created_by="pm_001",
            source_ref_count=0,
            source_analytics={},
            workflow_decisions=[],
        )


def test_proof_pack_build_context_prefers_explicit_correlation_then_falls_back_to_run() -> None:
    result = _ready_rebalance_result()
    run = _run_record(result=result)
    selection = ConstructionAlternativeSelection(
        selection_id="sel_context_corr",
        alternative_set_id="cas_context_corr",
        alternative_id="alt_context_corr",
        selected_at=CREATED_AT,
        actor_id="pm_001",
        reason_code="MODEL_DRIFT_REVIEW",
        correlation_id="corr-selection-context",
    )

    explicit = builder_module._proof_pack_build_context(
        source_type="REBALANCE_RUN",
        run=run,
        alternative_set=None,
        selected_alternative=None,
        selection=selection,
        correlation_id="corr-explicit-context",
        created_at=CREATED_AT,
        mandate_twin=None,
        mandate_health=None,
        direct_regime_stress_context=None,
    )
    selected = builder_module._proof_pack_build_context(
        source_type="REBALANCE_RUN",
        run=run,
        alternative_set=None,
        selected_alternative=None,
        selection=selection,
        correlation_id=None,
        created_at=CREATED_AT,
        mandate_twin=None,
        mandate_health=None,
        direct_regime_stress_context=None,
    )
    run_fallback = builder_module._proof_pack_build_context(
        source_type="REBALANCE_RUN",
        run=run,
        alternative_set=None,
        selected_alternative=None,
        selection=None,
        correlation_id=None,
        created_at=CREATED_AT,
        mandate_twin=None,
        mandate_health=None,
        direct_regime_stress_context=None,
    )

    assert explicit.correlation_id == "corr-explicit-context"
    assert selected.correlation_id == "corr-selection-context"
    assert run_fallback.correlation_id == result.correlation_id


def test_proof_pack_build_context_attaches_direct_regime_source_hashes_and_refs() -> None:
    result = _ready_rebalance_result()
    alternative = build_rebalance_result_alternative(result=result)
    alternative_set = build_alternative_set(
        alternative_set_id="cas_context_direct_regime",
        portfolio_id="pf_proof_pack_1",
        as_of="2026-05-03",
        alternatives=[alternative],
    ).model_copy(update={"generated_at": CREATED_AT})

    context = builder_module._proof_pack_build_context(
        source_type="SELECTED_ALTERNATIVE",
        run=_run_record(result=result),
        alternative_set=alternative_set,
        selected_alternative=alternative,
        selection=None,
        correlation_id=None,
        created_at=CREATED_AT,
        mandate_twin=None,
        mandate_health=None,
        direct_regime_stress_context=AuthoritativeRegimeStressContext(
            supportability_status="READY",
            source_system="lotus-risk",
            scenario_pack_id="CIO_REGIME_CONTEXT_Q3",
            worst_case_loss_pct=Decimal("0.0700"),
            maximum_allowed_loss_pct=Decimal("0.1200"),
            cio_approval_ref="CIO-APPROVAL-CONTEXT-Q3",
            effective_from=date(2026, 7, 1),
            reason_codes=["REGIME_SCENARIO_WITHIN_POLICY"],
        ),
    )

    assert context.proof_pack_id == (
        f"dpp_{alternative_set.alternative_set_id}_{alternative.alternative_id}"
    )
    assert context.portfolio_id == "pf_proof_pack_1"
    assert context.source_hashes["regime_stress_context"].startswith("sha256:")
    assert context.source_analytics["regime_stress"].facts["scenario_pack_id"] == (
        "CIO_REGIME_CONTEXT_Q3"
    )
    assert any(
        ref.source_system == "lotus-risk"
        and ref.source_type == "RegimeScenarioPackEvaluation"
        and ref.source_id == "CIO_REGIME_CONTEXT_Q3"
        for ref in context.source_refs
    )


def test_source_refs_preserve_manage_artifact_and_mandate_supportability() -> None:
    result = _ready_rebalance_result()
    run = _run_record(result=result)
    alternative = build_rebalance_result_alternative(result=result)
    alternative_set = build_alternative_set(
        alternative_set_id="cas_source_refs",
        portfolio_id="pf_proof_pack_1",
        as_of="2026-05-03",
        alternatives=[alternative],
    )
    mandate_twin = _mandate_twin().model_copy(update={"field_gap_codes": ["MISSING_REVIEW"]})
    mandate_health = calculate_mandate_health(DpmMandateHealthInput(twin=mandate_twin))

    refs = builder_module._source_refs(
        run=run,
        alternative_set=alternative_set,
        selected_alternative=alternative,
        source_hashes={
            "rebalance_run": "sha256:run",
            "alternative_set": "sha256:set",
            "selected_alternative": "sha256:alternative",
            "mandate_twin": "sha256:twin",
            "mandate_health": "sha256:health",
        },
        mandate_twin=mandate_twin,
        mandate_health=mandate_health,
    )

    refs_by_type = {ref.source_type: ref for ref in refs}
    assert list(refs_by_type) == [
        "DPM_REBALANCE_RUN",
        "DPM_CONSTRUCTION_ALTERNATIVE_SET",
        "DPM_CONSTRUCTION_ALTERNATIVE",
        "DPM_MANDATE_DIGITAL_TWIN",
        "DPM_MANDATE_HEALTH_SNAPSHOT",
    ]
    assert refs_by_type["DPM_REBALANCE_RUN"].supportability_state == result.status
    assert refs_by_type["DPM_MANDATE_DIGITAL_TWIN"].supportability_state == "DEGRADED"
    assert refs_by_type["DPM_MANDATE_HEALTH_SNAPSHOT"].source_id == (
        mandate_health.health_snapshot_id
    )
    assert refs_by_type["DPM_MANDATE_HEALTH_SNAPSHOT"].content_hash == "sha256:health"


def test_proof_pack_hash_is_deterministic_for_equivalent_inputs() -> None:
    mandate_twin = _mandate_twin()
    kwargs = {
        "run": _run_record(),
        "created_by": "pm_001",
        "reason": "Rebalance back to model after drift review.",
        "created_at": CREATED_AT,
        "mandate_id": "mandate_001",
        "mandate_twin": mandate_twin,
        "mandate_health": calculate_mandate_health(DpmMandateHealthInput(twin=mandate_twin)),
    }

    first = build_proof_pack_from_run(**kwargs)
    second = build_proof_pack_from_run(**kwargs)

    assert first.content_hash == second.content_hash
    assert first.supportability.section_hashes == second.supportability.section_hashes


def test_selected_alternative_proof_pack_captures_method_trace_and_selection_event() -> None:
    result = _ready_rebalance_result()
    alternative = build_rebalance_result_alternative(result=result)
    alternative_set = build_alternative_set(
        alternative_set_id="cas_proof_pack_1",
        portfolio_id="pf_proof_pack_1",
        as_of="2026-05-03",
        alternatives=[alternative],
    ).model_copy(update={"generated_at": CREATED_AT})
    selection = ConstructionAlternativeSelection(
        selection_id="sel_proof_pack_1",
        alternative_set_id="cas_proof_pack_1",
        alternative_id=alternative.alternative_id,
        selected_at=CREATED_AT,
        actor_id="pm_001",
        reason_code="MODEL_DRIFT_REVIEW",
        comment="Use explainable heuristic.",
        correlation_id="corr-selection-proof-pack",
    )

    pack = build_proof_pack_from_selected_alternative(
        alternative_set=alternative_set,
        selected_alternative_id=alternative.alternative_id,
        run=_run_record(result=result),
        selection=selection,
        created_by="pm_001",
        reason="Use selected alternative after drift review.",
        created_at=CREATED_AT,
        mandate_id="mandate_001",
    )

    selected = _section(pack, "selected_alternative")
    assert pack.source_type == "SELECTED_ALTERNATIVE"
    assert pack.alternative_set_id == "cas_proof_pack_1"
    assert pack.selected_alternative_id == alternative.alternative_id
    assert pack.correlation_id == "corr-selection-proof-pack"
    assert selected.state == "READY"
    assert selected.facts["method"] == "HEURISTIC_EXPLAINABLE"
    assert selected.facts["objective_trace"]
    assert selected.facts["constraint_trace"]
    assert pack.source_hashes["selected_alternative"].startswith("sha256:")
    assert [event.event_type for event in pack.decision_timeline.events] == [
        "REBALANCE_RUN_CREATED",
        "ALTERNATIVE_SET_GENERATED",
        "SELECTED_ALTERNATIVE",
        "PROOF_PACK_GENERATED",
    ]


def test_selected_alternative_for_proof_pack_resolves_selected_alternative() -> None:
    result = _ready_rebalance_result()
    alternative = build_rebalance_result_alternative(result=result)
    alternative_set = build_alternative_set(
        alternative_set_id="cas_proof_pack_1",
        portfolio_id="pf_proof_pack_1",
        as_of="2026-05-03",
        alternatives=[alternative],
    )
    selection = ConstructionAlternativeSelection(
        selection_id="sel_proof_pack_1",
        alternative_set_id=alternative_set.alternative_set_id,
        alternative_id=alternative.alternative_id,
        actor_id="pm_001",
        reason_code="MODEL_DRIFT_REVIEW",
    )

    selected = builder_module._selected_alternative_for_proof_pack(
        alternative_set=alternative_set,
        selected_alternative_id=alternative.alternative_id,
        selection=selection,
    )

    assert selected == alternative


def test_validate_selected_alternative_selection_rejects_mismatched_ids() -> None:
    with pytest.raises(
        ProofPackSourceValidationError,
        match="DPM_SELECTED_ALTERNATIVE_SELECTION_MISMATCH",
    ):
        builder_module._validate_selected_alternative_selection(
            alternative_set_id="cas_proof_pack_1",
            selected_alternative_id="ca_selected",
            selection=ConstructionAlternativeSelection(
                selection_id="sel_proof_pack_1",
                alternative_set_id="cas_proof_pack_1",
                alternative_id="ca_different",
                actor_id="pm_001",
                reason_code="MODEL_DRIFT_REVIEW",
            ),
        )

    with pytest.raises(
        ProofPackSourceValidationError,
        match="DPM_SELECTED_ALTERNATIVE_SET_MISMATCH",
    ):
        builder_module._validate_selected_alternative_selection(
            alternative_set_id="cas_proof_pack_1",
            selected_alternative_id="ca_selected",
            selection=ConstructionAlternativeSelection(
                selection_id="sel_proof_pack_2",
                alternative_set_id="cas_different",
                alternative_id="ca_selected",
                actor_id="pm_001",
                reason_code="MODEL_DRIFT_REVIEW",
            ),
        )


def test_selected_alternative_proof_pack_attaches_source_owned_risk_and_performance() -> None:
    result = _ready_rebalance_result()
    authority_context = ConstructionAuthorityContext(
        risk_context=AuthoritativeRiskContext(
            supportability_status="READY",
            source_system="lotus-risk",
            source_product_name="RiskMetricsReport",
            source_product_version="v1",
            source_id="risk-report:pf_proof_pack_1:2026-05-03",
            content_hash="sha256:risk-report-proof",
            tracking_error=Decimal("0.031"),
            concentration_breaches=0,
            concentration_hhi_delta=Decimal("-0.012"),
            top_position_weight_proposed=Decimal("0.50"),
            issuer_coverage_status="READY",
        ),
        performance_context=AuthoritativePerformanceContext(
            supportability_status="DEGRADED",
            source_system="lotus-performance",
            source_product_name="PerformanceBenchmarkContext",
            source_product_version="v1",
            source_id="performance-context:pf_proof_pack_1:2026-05-03",
            content_hash="sha256:performance-context-proof",
            benchmark_id="BM_GLOBAL_BALANCED_USD",
            active_return=Decimal("-0.007"),
            underperformance_flag=True,
            reason_codes=["PERFORMANCE_ATTRIBUTION_WINDOW_PARTIAL"],
        ),
    )
    alternative = build_rebalance_result_alternative(result=result).model_copy(
        update={
            "diagnostics": {
                "authority_context": authority_context.model_dump(
                    mode="json",
                    exclude_none=True,
                )
            }
        }
    )
    alternative_set = build_alternative_set(
        alternative_set_id="cas_source_analytics_1",
        portfolio_id="pf_proof_pack_1",
        as_of="2026-05-03",
        alternatives=[alternative],
    ).model_copy(update={"generated_at": CREATED_AT})

    pack = build_proof_pack_from_selected_alternative(
        alternative_set=alternative_set,
        selected_alternative_id=alternative.alternative_id,
        run=_run_record(result=result),
        created_by="pm_001",
        reason="Use source-owned analytics for proof-pack review.",
        created_at=CREATED_AT,
        mandate_id="mandate_001",
    )

    risk = _section(pack, "risk_impact")
    performance = _section(pack, "performance_context")

    assert risk.state == "READY"
    assert risk.facts["source_system"] == "lotus-risk"
    assert risk.metrics["tracking_error"] == "0.031"
    assert risk.metrics["concentration_breaches"] == 0
    assert risk.metrics["concentration_hhi_delta"] == "-0.012"
    assert performance.state == "DEGRADED"
    assert performance.facts["source_system"] == "lotus-performance"
    assert performance.facts["benchmark_id"] == "BM_GLOBAL_BALANCED_USD"
    assert performance.metrics["active_return"] == "-0.007"
    assert performance.metrics["underperformance_flag"] is True
    assert performance.reason_codes == ["PERFORMANCE_ATTRIBUTION_WINDOW_PARTIAL"]
    assert pack.source_hashes["risk_context"] == "sha256:risk-report-proof"
    assert pack.source_hashes["performance_context"] == "sha256:performance-context-proof"
    assert any(
        ref.source_system == "lotus-risk" and ref.source_type == "RiskMetricsReport"
        for ref in pack.sections[0].source_refs
    )
    assert any(
        ref.source_system == "lotus-performance"
        and ref.source_type == "PerformanceBenchmarkContext"
        for ref in pack.sections[0].source_refs
    )


def test_selected_alternative_proof_pack_distinguishes_estimated_and_source_owned_cost() -> None:
    result = _ready_rebalance_result()
    authority_context = ConstructionAuthorityContext(
        transaction_cost_context=AuthoritativeTransactionCostContext(
            supportability_status="READY",
            source_system="lotus-core",
            source_product_name="TransactionCostCurve",
            source_product_version="v1",
            source_id="transaction-cost-scope-001",
            content_hash="sha256:transaction-cost-curve-proof",
            as_of_date="2026-05-03",
            window_start_date="2026-02-02",
            window_end_date="2026-05-03",
            returned_curve_point_count=1,
            reason_codes=["TRANSACTION_COST_CURVE_READY"],
            curve_points=[
                AuthoritativeTransactionCostPoint(
                    security_id="EQ_B",
                    transaction_type="BUY",
                    currency="USD",
                    observation_count=3,
                    total_notional=Decimal("30000"),
                    total_cost=Decimal("15"),
                    average_cost_bps=Decimal("5.0000"),
                    min_cost_bps=Decimal("4.5000"),
                    max_cost_bps=Decimal("5.5000"),
                    first_observed_date="2026-04-01",
                    last_observed_date="2026-05-03",
                    sample_transaction_ids=["TXN-1", "TXN-2"],
                )
            ],
        )
    )
    alternative = build_rebalance_result_alternative(result=result).model_copy(
        update={
            "diagnostics": {
                "authority_context": authority_context.model_dump(
                    mode="json",
                    exclude_none=True,
                )
            }
        }
    )
    alternative_set = build_alternative_set(
        alternative_set_id="cas_transaction_cost_1",
        portfolio_id="pf_proof_pack_1",
        as_of="2026-05-03",
        alternatives=[alternative],
    ).model_copy(update={"generated_at": CREATED_AT})

    pack = build_proof_pack_from_selected_alternative(
        alternative_set=alternative_set,
        selected_alternative_id=alternative.alternative_id,
        run=_run_record(result=result),
        created_by="pm_001",
        reason="Use source-owned cost evidence for proof-pack review.",
        created_at=CREATED_AT,
        mandate_id="mandate_001",
    )

    turnover = _section(pack, "turnover_and_cost")

    assert turnover.state == "READY"
    assert turnover.metrics["estimated_transaction_cost"] is None
    assert turnover.metrics["returned_curve_point_count"] == 1
    assert turnover.metrics["represented_observation_count"] == 3
    assert turnover.facts["source_product_name"] == "TransactionCostCurve"
    assert turnover.facts["curve_points"][0]["average_cost_bps"] == "5.0000"
    assert "TRANSACTION_COST_CURVE_READY" in turnover.reason_codes
    assert pack.source_hashes["transaction_cost_context"] == "sha256:transaction-cost-curve-proof"
    assert any(
        ref.source_system == "lotus-core" and ref.source_type == "TransactionCostCurve"
        for ref in pack.sections[0].source_refs
    )


def test_selected_alternative_proof_pack_preserves_restriction_and_sustainability_sources() -> None:
    result = _ready_rebalance_result()
    authority_context = ConstructionAuthorityContext(
        client_restriction_context=AuthoritativeClientRestrictionContext(
            supportability_status="READY",
            source_system="lotus-core",
            source_product_name="ClientRestrictionProfile",
            source_product_version="v1",
            source_id="sha256:client-restrictions",
            content_hash="sha256:client-restrictions",
            portfolio_id="pf_proof_pack_1",
            client_id="client_001",
            mandate_id="mandate_001",
            as_of_date="2026-05-03",
            restriction_count=1,
            reason_codes=["CLIENT_RESTRICTION_PROFILE_READY"],
            restrictions=[
                AuthoritativeClientRestrictionRule(
                    restriction_scope="instrument",
                    restriction_code="NO_PRIVATE_CREDIT_BUY",
                    restriction_status="active",
                    restriction_source="client_mandate",
                    applies_to_buy=True,
                    applies_to_sell=False,
                    instrument_ids=["PRIVATE_CREDIT_FUND"],
                    effective_from="2026-01-01",
                    restriction_version=1,
                    source_record_id="client-restriction:1",
                )
            ],
        ),
        sustainability_preference_context=AuthoritativeSustainabilityPreferenceContext(
            supportability_status="PENDING_REVIEW",
            source_system="lotus-core",
            source_product_name="SustainabilityPreferenceProfile",
            source_product_version="v1",
            source_id="sha256:sustainability-preferences",
            content_hash="sha256:sustainability-preferences",
            portfolio_id="pf_proof_pack_1",
            client_id="client_001",
            mandate_id="mandate_001",
            as_of_date="2026-05-03",
            preference_count=1,
            reason_codes=["SUSTAINABILITY_CLASSIFICATION_EVIDENCE_REQUIRED"],
            preferences=[
                AuthoritativeSustainabilityPreference(
                    preference_framework="LOTUS_SUSTAINABILITY_V1",
                    preference_code="MIN_SUSTAINABLE_ALLOCATION",
                    preference_status="active",
                    preference_source="client_mandate",
                    minimum_allocation=Decimal("0.20"),
                    applies_to_asset_classes=["Equity"],
                    exclusion_codes=["THERMAL_COAL"],
                    positive_tilt_codes=["LOW_CARBON_TRANSITION"],
                    effective_from="2026-01-01",
                    preference_version=1,
                    source_record_id="sustainability:1",
                )
            ],
        ),
    )
    alternative = build_rebalance_result_alternative(result=result).model_copy(
        update={
            "diagnostics": {
                "authority_context": authority_context.model_dump(
                    mode="json",
                    exclude_none=True,
                )
            }
        }
    )
    alternative_set = build_alternative_set(
        alternative_set_id="cas_client_esg_1",
        portfolio_id="pf_proof_pack_1",
        as_of="2026-05-03",
        alternatives=[alternative],
    ).model_copy(update={"generated_at": CREATED_AT})

    pack = build_proof_pack_from_selected_alternative(
        alternative_set=alternative_set,
        selected_alternative_id=alternative.alternative_id,
        run=_run_record(result=result),
        created_by="pm_001",
        reason="Use source-owned restriction and sustainability evidence for proof-pack review.",
        created_at=CREATED_AT,
        mandate_id="mandate_001",
    )

    restrictions = _section(pack, "eligibility_and_restrictions")
    sustainability = _section(pack, "sustainability_controls")

    assert restrictions.state == "READY"
    assert restrictions.facts["source_product_name"] == "ClientRestrictionProfile"
    assert restrictions.metrics["restriction_count"] == 1
    assert restrictions.facts["restrictions"][0]["restriction_code"] == "NO_PRIVATE_CREDIT_BUY"
    assert sustainability.state == "PENDING_REVIEW"
    assert sustainability.facts["source_product_name"] == "SustainabilityPreferenceProfile"
    assert sustainability.metrics["preference_count"] == 1
    assert "SUSTAINABILITY_CLASSIFICATION_EVIDENCE_REQUIRED" in sustainability.reason_codes
    assert pack.source_hashes["client_restriction_context"] == "sha256:client-restrictions"
    assert pack.source_hashes["sustainability_preference_context"] == (
        "sha256:sustainability-preferences"
    )
    assert any(
        ref.source_system == "lotus-core" and ref.source_type == "ClientRestrictionProfile"
        for ref in pack.sections[0].source_refs
    )
    assert any(
        ref.source_system == "lotus-core" and ref.source_type == "SustainabilityPreferenceProfile"
        for ref in pack.sections[0].source_refs
    )


def test_selected_alternative_proof_pack_preserves_regime_scenario_pack_source() -> None:
    result = _ready_rebalance_result()
    authority_context = ConstructionAuthorityContext(
        regime_stress_context=AuthoritativeRegimeStressContext(
            supportability_status="PENDING_REVIEW",
            source_system="lotus-risk",
            scenario_pack_id="CIO_REGIME_2026_Q2",
            worst_case_loss_pct=Decimal("0.1800"),
            maximum_allowed_loss_pct=Decimal("0.1200"),
            cio_approval_status="approved",
            cio_approval_ref="CIO-APPROVAL-2026-Q2",
            approved_by="cio_001",
            approved_at="2026-04-30T09:00:00Z",
            effective_from=date(2026, 5, 1),
            effective_to=date(2026, 6, 30),
            effective_period_status="active",
            applicability_status="applicable",
            applicability_scope=["DISCRETIONARY_PRIVATE_BANKING_BALANCED"],
            portfolio_applicability_ref="CIO-APPROVAL-2026-Q2-APP-pf_proof_pack_1",
            methodology_ref="docs/methodologies/metrics/regime-scenario-pack-evaluation.md",
            applicable_portfolio_ids=["pf_proof_pack_1"],
            applicable_mandate_ids=["mandate_001"],
            reason_codes=["REGIME_SCENARIO_LOSS_EXCEEDS_POLICY"],
        )
    )
    alternative = build_rebalance_result_alternative(result=result).model_copy(
        update={
            "diagnostics": {
                "authority_context": authority_context.model_dump(
                    mode="json",
                    exclude_none=True,
                )
            }
        }
    )
    alternative_set = build_alternative_set(
        alternative_set_id="cas_regime_scenario_1",
        portfolio_id="pf_proof_pack_1",
        as_of="2026-05-03",
        alternatives=[alternative],
    ).model_copy(update={"generated_at": CREATED_AT})

    pack = build_proof_pack_from_selected_alternative(
        alternative_set=alternative_set,
        selected_alternative_id=alternative.alternative_id,
        run=_run_record(result=result),
        created_by="pm_001",
        reason="Use source-owned scenario-pack evidence for proof-pack review.",
        created_at=CREATED_AT,
        mandate_id="mandate_001",
    )

    scenario = _section(pack, "scenario_and_regime_evidence")

    assert scenario.state == "PENDING_REVIEW"
    assert scenario.facts["source_system"] == "lotus-risk"
    assert scenario.facts["source_product_name"] == "RegimeScenarioPackEvaluation"
    assert scenario.facts["source_product_version"] == "v1"
    assert scenario.facts["scenario_pack_id"] == "CIO_REGIME_2026_Q2"
    assert scenario.facts["cio_approval_status"] == "approved"
    assert scenario.facts["cio_approval_ref"] == "CIO-APPROVAL-2026-Q2"
    assert scenario.facts["approved_by"] == "cio_001"
    assert scenario.facts["approved_at"] == "2026-04-30T09:00:00Z"
    assert scenario.facts["effective_from"] == "2026-05-01"
    assert scenario.facts["effective_to"] == "2026-06-30"
    assert scenario.facts["effective_period_status"] == "active"
    assert scenario.facts["applicability_status"] == "applicable"
    assert scenario.facts["applicability_scope"] == ["DISCRETIONARY_PRIVATE_BANKING_BALANCED"]
    assert scenario.facts["portfolio_applicability_ref"] == (
        "CIO-APPROVAL-2026-Q2-APP-pf_proof_pack_1"
    )
    assert (
        scenario.facts["methodology_ref"]
        == "docs/methodologies/metrics/regime-scenario-pack-evaluation.md"
    )
    assert scenario.facts["applicable_portfolio_ids"] == ["pf_proof_pack_1"]
    assert scenario.facts["applicable_mandate_ids"] == ["mandate_001"]
    assert scenario.facts["approval_evidence_projected"] is True
    assert scenario.facts["effective_period_projected"] is True
    assert scenario.facts["applicability_evidence_projected"] is True
    assert scenario.facts["scenario_evidence_posture"] == {
        "cio_approval": "PROJECTED",
        "effective_period": "PROJECTED",
        "applicability": "PROJECTED",
        "source_reason_posture": "READY",
    }
    assert scenario.metrics["worst_case_loss_pct"] == "0.1800"
    assert scenario.metrics["maximum_allowed_loss_pct"] == "0.1200"
    assert scenario.reason_codes == ["REGIME_SCENARIO_LOSS_EXCEEDS_POLICY"]
    assert pack.source_hashes["regime_stress_context"].startswith("sha256:")
    assert any(
        ref.source_system == "lotus-risk"
        and ref.source_type == "RegimeScenarioPackEvaluation"
        and ref.source_id == "CIO_REGIME_2026_Q2"
        for ref in pack.sections[0].source_refs
    )


def test_selected_alternative_proof_pack_accepts_direct_regime_scenario_pack_source() -> None:
    result = _ready_rebalance_result()
    alternative = build_rebalance_result_alternative(result=result)
    alternative_set = build_alternative_set(
        alternative_set_id="cas_direct_regime_scenario_1",
        portfolio_id="pf_proof_pack_1",
        as_of="2026-05-03",
        alternatives=[alternative],
    ).model_copy(update={"generated_at": CREATED_AT})

    pack = build_proof_pack_from_selected_alternative(
        alternative_set=alternative_set,
        selected_alternative_id=alternative.alternative_id,
        run=_run_record(result=result),
        created_by="pm_001",
        reason="Attach source-owned scenario-pack evidence directly to the proof pack.",
        created_at=CREATED_AT,
        mandate_id="mandate_001",
        direct_regime_stress_context=AuthoritativeRegimeStressContext(
            supportability_status="READY",
            source_system="lotus-risk",
            scenario_pack_id="CIO_REGIME_2026_Q3",
            worst_case_loss_pct=Decimal("0.0700"),
            maximum_allowed_loss_pct=Decimal("0.1200"),
            cio_approval_ref="CIO-APPROVAL-2026-Q3",
            effective_from=date(2026, 7, 1),
            applicable_mandate_ids=["mandate_001"],
            reason_codes=["REGIME_SCENARIO_WITHIN_POLICY"],
        ),
    )

    scenario = _section(pack, "scenario_and_regime_evidence")

    assert scenario.state == "READY"
    assert scenario.facts["source_system"] == "lotus-risk"
    assert scenario.facts["source_product_name"] == "RegimeScenarioPackEvaluation"
    assert scenario.facts["scenario_pack_id"] == "CIO_REGIME_2026_Q3"
    assert scenario.facts["cio_approval_ref"] == "CIO-APPROVAL-2026-Q3"
    assert scenario.facts["effective_from"] == "2026-07-01"
    assert scenario.facts["applicable_mandate_ids"] == ["mandate_001"]
    assert scenario.facts["approval_evidence_projected"] is True
    assert scenario.facts["effective_period_projected"] is True
    assert scenario.facts["applicability_evidence_projected"] is True
    assert scenario.facts["scenario_evidence_posture"] == {
        "cio_approval": "PROJECTED",
        "effective_period": "PROJECTED",
        "applicability": "PROJECTED",
        "source_reason_posture": "READY",
    }
    assert scenario.metrics["worst_case_loss_pct"] == "0.0700"
    assert scenario.metrics["maximum_allowed_loss_pct"] == "0.1200"
    assert scenario.reason_codes == ["REGIME_SCENARIO_WITHIN_POLICY"]
    assert pack.source_hashes["regime_stress_context"].startswith("sha256:")
    assert any(
        ref.source_system == "lotus-risk"
        and ref.source_type == "RegimeScenarioPackEvaluation"
        and ref.source_id == "CIO_REGIME_2026_Q3"
        for ref in pack.sections[0].source_refs
    )


def test_source_analytics_degraded_and_blocked_context_fallbacks() -> None:
    result = _ready_rebalance_result()
    authority_context = ConstructionAuthorityContext(
        risk_context=AuthoritativeRiskContext(
            supportability_status="DEGRADED",
            source_system="lotus-risk",
        ),
        performance_context=AuthoritativePerformanceContext(
            supportability_status="DEGRADED",
            source_system="lotus-performance",
        ),
        transaction_cost_context=AuthoritativeTransactionCostContext(
            supportability_status="DEGRADED",
            source_system="lotus-core",
            as_of_date="2026-05-03",
            window_start_date="2026-04-03",
            window_end_date="2026-05-03",
            returned_curve_point_count=0,
        ),
        client_restriction_context=AuthoritativeClientRestrictionContext(
            supportability_status="BLOCKED",
            source_system="lotus-core",
            portfolio_id="pf_proof_pack_1",
            client_id="client_001",
            mandate_id="mandate_001",
            as_of_date="2026-05-03",
            restriction_count=0,
        ),
        sustainability_preference_context=AuthoritativeSustainabilityPreferenceContext(
            supportability_status="PENDING_REVIEW",
            source_system="lotus-core",
            portfolio_id="pf_proof_pack_1",
            client_id="client_001",
            mandate_id="mandate_001",
            as_of_date="2026-05-03",
            preference_count=0,
        ),
        regime_stress_context=AuthoritativeRegimeStressContext(
            supportability_status="DEGRADED",
            source_system="lotus-risk",
            scenario_pack_id="CIO_REGIME_2026_Q2",
            worst_case_loss_pct=Decimal("0.0800"),
            maximum_allowed_loss_pct=Decimal("0.1200"),
        ),
    )
    alternative = build_rebalance_result_alternative(result=result).model_copy(
        update={
            "diagnostics": {
                "authority_context": authority_context.model_dump(
                    mode="json",
                    exclude_none=True,
                )
            }
        }
    )

    risk = source_analytics_for_alternative(alternative=alternative, family="risk")
    performance = source_analytics_for_alternative(alternative=alternative, family="performance")
    transaction_cost = source_analytics_for_alternative(
        alternative=alternative,
        family="transaction_cost",
    )
    restriction = source_analytics_for_alternative(
        alternative=alternative,
        family="client_restriction",
    )
    sustainability = source_analytics_for_alternative(
        alternative=alternative,
        family="sustainability_preference",
    )
    regime_stress = source_analytics_for_alternative(
        alternative=alternative,
        family="regime_stress",
    )

    assert risk is not None
    assert risk.reason_codes == ["DPM_RISK_AUTHORITY_CONTEXT_DEGRADED"]
    assert performance is not None
    assert performance.reason_codes == ["DPM_PERFORMANCE_CONTEXT_DEGRADED"]
    assert transaction_cost is not None
    assert transaction_cost.reason_codes == ["DPM_TRANSACTION_COST_CONTEXT_DEGRADED"]
    assert restriction is not None
    assert restriction.state == "BLOCKED"
    assert restriction.reason_codes == ["DPM_CLIENT_RESTRICTION_CONTEXT_DEGRADED"]
    assert sustainability is not None
    assert sustainability.state == "PENDING_REVIEW"
    assert sustainability.reason_codes == ["DPM_SUSTAINABILITY_PREFERENCE_CONTEXT_DEGRADED"]
    assert regime_stress is not None
    assert regime_stress.reason_codes == [
        "DPM_REGIME_STRESS_CONTEXT_DEGRADED",
        "REGIME_SCENARIO_APPLICABILITY_EVIDENCE_MISSING",
        "REGIME_SCENARIO_CIO_APPROVAL_EVIDENCE_MISSING",
        "REGIME_SCENARIO_EFFECTIVE_PERIOD_EVIDENCE_MISSING",
    ]


def test_risk_source_analytics_helpers_project_facts_metrics_and_degraded_reason() -> None:
    context = AuthoritativeRiskContext(
        supportability_status="DEGRADED",
        source_system="lotus-risk",
        source_product_name="RiskMetricsReport",
        source_product_version="v1",
        source_id="risk-context-001",
        issuer_coverage_status="partial",
        tracking_error=Decimal("0.034"),
        maximum_drawdown=Decimal("-0.070"),
    )

    assert _risk_source_facts(context) == {
        "source_system": "lotus-risk",
        "source_product_name": "RiskMetricsReport",
        "source_product_version": "v1",
        "source_id": "risk-context-001",
        "issuer_coverage_status": "partial",
    }
    assert _risk_source_metrics(context) == {
        "tracking_error": Decimal("0.034"),
        "maximum_drawdown": Decimal("-0.070"),
    }
    assert _authority_reason_codes(
        context=context,
        degraded_reason="DPM_RISK_AUTHORITY_CONTEXT_DEGRADED",
    ) == ["DPM_RISK_AUTHORITY_CONTEXT_DEGRADED"]


def test_performance_source_analytics_helpers_project_facts_metrics_and_source_ref() -> None:
    context = AuthoritativePerformanceContext(
        supportability_status="READY",
        source_system="lotus-performance",
        source_product_name="PerformanceBenchmarkContext",
        source_product_version="v1",
        source_id="performance-context-001",
        content_hash="sha256:performance-context",
        benchmark_id="MSCI_ACWI",
        active_return=Decimal("0.011"),
        underperformance_flag=True,
        reason_codes=["PERFORMANCE_CONTEXT_READY"],
    )

    assert _performance_source_facts(context) == {
        "source_system": "lotus-performance",
        "source_product_name": "PerformanceBenchmarkContext",
        "source_product_version": "v1",
        "source_id": "performance-context-001",
        "benchmark_id": "MSCI_ACWI",
    }
    assert _performance_source_metrics(context) == {
        "active_return": Decimal("0.011"),
        "underperformance_flag": True,
    }
    assert _authority_reason_codes(
        context=context,
        degraded_reason="DPM_PERFORMANCE_CONTEXT_DEGRADED",
    ) == ["PERFORMANCE_CONTEXT_READY"]

    source_ref = _authority_source_ref(
        family="performance",
        source_system=context.source_system,
        source_type=context.source_product_name or "PerformanceBenchmarkContext",
        source_id=context.source_id,
        supportability_status=context.supportability_status,
        content_hash=context.content_hash,
        fallback_hash="sha256:fallback",
    )

    assert source_ref.source_system == "lotus-performance"
    assert source_ref.source_type == "PerformanceBenchmarkContext"
    assert source_ref.source_id == "performance-context-001"
    assert source_ref.content_hash == "sha256:performance-context"


def test_degraded_context_reason_codes_preserve_source_reasons_before_fallback() -> None:
    assert _degraded_context_reason_codes(
        supportability_status=ConstructionMethodStatus.DEGRADED,
        reason_codes=[],
        degraded_reason="DPM_SOURCE_CONTEXT_DEGRADED",
    ) == ["DPM_SOURCE_CONTEXT_DEGRADED"]
    assert _degraded_context_reason_codes(
        supportability_status=ConstructionMethodStatus.DEGRADED,
        reason_codes=["SOURCE_OWNER_REASON"],
        degraded_reason="DPM_SOURCE_CONTEXT_DEGRADED",
    ) == ["SOURCE_OWNER_REASON"]
    assert (
        _degraded_context_reason_codes(
            supportability_status=ConstructionMethodStatus.READY,
            reason_codes=[],
            degraded_reason="DPM_SOURCE_CONTEXT_DEGRADED",
        )
        == []
    )


def test_transaction_cost_source_helpers_project_facts_and_metrics() -> None:
    context = AuthoritativeTransactionCostContext(
        supportability_status="READY",
        source_system="lotus-core",
        source_product_name="TransactionCostCurve",
        source_product_version="v1",
        source_id="transaction-cost-context-001",
        as_of_date="2026-05-03",
        window_start_date="2026-04-03",
        window_end_date="2026-05-03",
        returned_curve_point_count=2,
        missing_security_ids=["SEC_MISSING"],
        curve_points=[
            AuthoritativeTransactionCostPoint(
                security_id="SEC_A",
                transaction_type="BUY",
                currency="USD",
                total_notional=Decimal("30000"),
                total_cost=Decimal("37.50"),
                average_cost_bps=Decimal("12.5"),
                min_cost_bps=Decimal("10.0"),
                max_cost_bps=Decimal("15.0"),
                observation_count=3,
                first_observed_date="2026-04-03",
                last_observed_date="2026-05-01",
            ),
            AuthoritativeTransactionCostPoint(
                security_id="SEC_B",
                transaction_type="SELL",
                currency="USD",
                total_notional=Decimal("50000"),
                total_cost=Decimal("40.00"),
                average_cost_bps=Decimal("8.0"),
                min_cost_bps=Decimal("7.0"),
                max_cost_bps=Decimal("9.0"),
                observation_count=5,
                first_observed_date="2026-04-05",
                last_observed_date="2026-05-02",
            ),
        ],
    )

    facts = _transaction_cost_source_facts(context)

    assert facts["source_system"] == "lotus-core"
    assert facts["source_product_name"] == "TransactionCostCurve"
    assert facts["source_id"] == "transaction-cost-context-001"
    assert facts["as_of_date"] == "2026-05-03"
    assert facts["missing_security_ids"] == ["SEC_MISSING"]
    assert facts["curve_points"] == [
        {
            "security_id": "SEC_A",
            "transaction_type": "BUY",
            "currency": "USD",
            "total_notional": "30000",
            "total_cost": "37.50",
            "average_cost_bps": "12.5",
            "min_cost_bps": "10.0",
            "max_cost_bps": "15.0",
            "observation_count": 3,
            "first_observed_date": "2026-04-03",
            "last_observed_date": "2026-05-01",
            "sample_transaction_ids": [],
        },
        {
            "security_id": "SEC_B",
            "transaction_type": "SELL",
            "currency": "USD",
            "total_notional": "50000",
            "total_cost": "40.00",
            "average_cost_bps": "8.0",
            "min_cost_bps": "7.0",
            "max_cost_bps": "9.0",
            "observation_count": 5,
            "first_observed_date": "2026-04-05",
            "last_observed_date": "2026-05-02",
            "sample_transaction_ids": [],
        },
    ]
    assert _transaction_cost_source_metrics(context) == {
        "returned_curve_point_count": 2,
        "represented_observation_count": 8,
    }


def test_regime_scenario_pack_missing_governance_evidence_is_pending_review() -> None:
    context = AuthoritativeRegimeStressContext(
        supportability_status="READY",
        source_system="lotus-risk",
        scenario_pack_id="CIO_REGIME_2026_Q4",
        worst_case_loss_pct=Decimal("0.0600"),
        maximum_allowed_loss_pct=Decimal("0.1200"),
        reason_codes=["REGIME_SCENARIO_WITHIN_POLICY"],
    )

    analytics = source_analytics_for_context(
        source_context=context.model_dump(mode="json"),
        family="regime_stress",
    )

    assert analytics is not None
    assert analytics.state == "PENDING_REVIEW"
    assert analytics.facts["approval_evidence_projected"] is False
    assert analytics.facts["effective_period_projected"] is False
    assert analytics.facts["applicability_evidence_projected"] is False
    assert analytics.facts["scenario_evidence_posture"] == {
        "cio_approval": "MISSING",
        "effective_period": "MISSING",
        "applicability": "MISSING",
        "source_reason_posture": "READY",
    }
    assert analytics.reason_codes == [
        "REGIME_SCENARIO_APPLICABILITY_EVIDENCE_MISSING",
        "REGIME_SCENARIO_CIO_APPROVAL_EVIDENCE_MISSING",
        "REGIME_SCENARIO_EFFECTIVE_PERIOD_EVIDENCE_MISSING",
        "REGIME_SCENARIO_WITHIN_POLICY",
    ]


def test_regime_stress_governance_posture_helpers_project_missing_evidence() -> None:
    context = AuthoritativeRegimeStressContext(
        supportability_status="READY",
        source_system="lotus-risk",
        scenario_pack_id="CIO_REGIME_2026_Q4",
        worst_case_loss_pct=Decimal("0.0600"),
        maximum_allowed_loss_pct=Decimal("0.1200"),
    )

    assert _regime_stress_governance_posture_facts(context) == {
        "cio_approval": "MISSING",
        "effective_period": "MISSING",
        "applicability": "MISSING",
        "source_reason_posture": "READY",
    }
    assert _missing_regime_stress_governance_evidence(context) == {
        "cio_approval",
        "effective_period",
        "applicability",
    }


def test_regime_stress_source_helpers_project_facts_and_metrics() -> None:
    context = AuthoritativeRegimeStressContext(
        supportability_status="READY",
        source_system="lotus-risk",
        source_product_version="v1",
        scenario_pack_id="CIO_REGIME_2026_Q4",
        worst_case_loss_pct=Decimal("0.0600"),
        maximum_allowed_loss_pct=Decimal("0.1200"),
        cio_approval_status="APPROVED",
        cio_approval_ref="CIO-APPROVAL-2026-Q4",
        approved_by="cio_001",
        approved_at="2026-09-15T08:30:00Z",
        effective_from=date(2026, 10, 1),
        effective_to=date(2026, 12, 31),
        effective_period_status="ACTIVE",
        applicability_status="APPLICABLE",
        applicability_scope=["MANDATE"],
        portfolio_applicability_ref="portfolio-applicability-001",
        methodology_ref="risk-methodology-regime-v3",
        applicable_portfolio_ids=["pf_001"],
        applicable_mandate_ids=["mandate_001"],
    )

    facts = _regime_stress_source_facts(
        context=context,
        evidence_posture={
            "facts": {
                "cio_approval": "PROJECTED",
                "effective_period": "PROJECTED",
                "applicability": "PROJECTED",
                "source_reason_posture": "READY",
            }
        },
    )

    assert facts["source_system"] == "lotus-risk"
    assert facts["source_product_name"] == "RegimeScenarioPackEvaluation"
    assert facts["scenario_pack_id"] == "CIO_REGIME_2026_Q4"
    assert facts["approved_at"] == "2026-09-15T08:30:00Z"
    assert facts["effective_from"] == "2026-10-01"
    assert facts["effective_to"] == "2026-12-31"
    assert facts["approval_evidence_projected"] is True
    assert facts["effective_period_projected"] is True
    assert facts["applicability_evidence_projected"] is True
    assert facts["scenario_evidence_posture"]["source_reason_posture"] == "READY"
    assert _regime_stress_source_metrics(context) == {
        "worst_case_loss_pct": Decimal("0.0600"),
        "maximum_allowed_loss_pct": Decimal("0.1200"),
    }


@pytest.mark.parametrize(
    ("source_reason_codes", "expected_posture"),
    [
        (["REGIME_SCENARIO_PORTFOLIO_INAPPLICABLE"], "INAPPLICABLE"),
        (["REGIME_SCENARIO_OUTSIDE_EFFECTIVE_PERIOD"], "EFFECTIVE_PERIOD_EXCEPTION"),
        (["REGIME_SCENARIO_CONTRIBUTION_PARTIAL"], "CONTRIBUTION_PARTIAL"),
        (
            [
                "REGIME_SCENARIO_CONTRIBUTION_PARTIAL",
                "REGIME_SCENARIO_PORTFOLIO_INAPPLICABLE",
            ],
            "INAPPLICABLE",
        ),
        (["REGIME_SCENARIO_WITHIN_POLICY"], "READY"),
    ],
)
def test_regime_source_reason_posture_classifies_source_reason_codes(
    source_reason_codes: list[str],
    expected_posture: str,
) -> None:
    assert _regime_source_reason_posture(source_reason_codes) == expected_posture


@pytest.mark.parametrize(
    ("source_reason_code", "expected_state", "expected_posture", "expected_reason_code"),
    [
        (
            "REGIME_SCENARIO_PACK_STALE",
            "DEGRADED",
            "EFFECTIVE_PERIOD_EXCEPTION",
            "REGIME_SCENARIO_EFFECTIVE_PERIOD_EXCEPTION",
        ),
        (
            "REGIME_SCENARIO_PORTFOLIO_INAPPLICABLE",
            "BLOCKED",
            "INAPPLICABLE",
            "REGIME_SCENARIO_APPLICABILITY_NOT_CONFIRMED",
        ),
        (
            "REGIME_SCENARIO_CONTRIBUTION_PARTIAL",
            "PENDING_REVIEW",
            "CONTRIBUTION_PARTIAL",
            "REGIME_SCENARIO_CONTRIBUTION_EVIDENCE_PARTIAL",
        ),
    ],
)
def test_regime_scenario_source_reason_codes_drive_section_posture(
    source_reason_code: str,
    expected_state: str,
    expected_posture: str,
    expected_reason_code: str,
) -> None:
    context = AuthoritativeRegimeStressContext(
        supportability_status="READY",
        source_system="lotus-risk",
        scenario_pack_id="CIO_REGIME_2026_Q4",
        worst_case_loss_pct=Decimal("0.0600"),
        maximum_allowed_loss_pct=Decimal("0.1200"),
        cio_approval_ref="CIO-APPROVAL-2026-Q4",
        effective_from=date(2026, 10, 1),
        applicable_mandate_ids=["mandate_001"],
        reason_codes=[source_reason_code],
    )

    analytics = source_analytics_for_context(
        source_context=context.model_dump(mode="json"),
        family="regime_stress",
    )

    assert analytics is not None
    assert analytics.state == expected_state
    assert analytics.facts["scenario_evidence_posture"]["source_reason_posture"] == (
        expected_posture
    )
    assert expected_reason_code in analytics.reason_codes


@pytest.mark.parametrize(
    "family",
    [
        "risk",
        "performance",
        "transaction_cost",
        "client_restriction",
        "sustainability_preference",
        "regime_stress",
    ],
)
def test_source_analytics_rejects_malformed_authority_contexts(
    family: ProofPackAnalyticsFamily,
) -> None:
    result = _ready_rebalance_result()
    alternative = build_rebalance_result_alternative(result=result).model_copy(
        update={"diagnostics": {"authority_context": {f"{family}_context": {"bad": "shape"}}}}
    )

    assert source_analytics_for_alternative(alternative=alternative, family=family) is None


def test_selected_alternative_builder_rejects_unknown_selection() -> None:
    result = _ready_rebalance_result()
    alternative = build_rebalance_result_alternative(result=result)
    alternative_set = build_alternative_set(
        alternative_set_id="cas_proof_pack_1",
        portfolio_id="pf_proof_pack_1",
        as_of="2026-05-03",
        alternatives=[alternative],
    ).model_copy(update={"generated_at": CREATED_AT})

    with pytest.raises(ProofPackSourceValidationError, match="DPM_SELECTED_ALTERNATIVE_NOT_FOUND"):
        build_proof_pack_from_selected_alternative(
            alternative_set=alternative_set,
            selected_alternative_id="missing",
            run=_run_record(result=result),
            created_by="pm_001",
            reason="Use selected alternative after drift review.",
            created_at=CREATED_AT,
            mandate_id="mandate_001",
        )


def test_selected_alternative_builder_rejects_mismatched_selection_records() -> None:
    result = _ready_rebalance_result()
    alternative = build_rebalance_result_alternative(result=result)
    alternative_set = build_alternative_set(
        alternative_set_id="cas_proof_pack_1",
        portfolio_id="pf_proof_pack_1",
        as_of="2026-05-03",
        alternatives=[alternative],
    ).model_copy(update={"generated_at": CREATED_AT})

    with pytest.raises(
        ProofPackSourceValidationError,
        match="DPM_SELECTED_ALTERNATIVE_SELECTION_MISMATCH",
    ):
        build_proof_pack_from_selected_alternative(
            alternative_set=alternative_set,
            selected_alternative_id=alternative.alternative_id,
            run=_run_record(result=result),
            selection=ConstructionAlternativeSelection(
                selection_id="sel_proof_pack_1",
                alternative_set_id=alternative_set.alternative_set_id,
                alternative_id="different_alternative",
                actor_id="pm_001",
                reason_code="MODEL_DRIFT_REVIEW",
            ),
            created_by="pm_001",
            reason="Use selected alternative after drift review.",
            created_at=CREATED_AT,
            mandate_id="mandate_001",
        )

    with pytest.raises(
        ProofPackSourceValidationError,
        match="DPM_SELECTED_ALTERNATIVE_SET_MISMATCH",
    ):
        build_proof_pack_from_selected_alternative(
            alternative_set=alternative_set,
            selected_alternative_id=alternative.alternative_id,
            run=_run_record(result=result),
            selection=ConstructionAlternativeSelection(
                selection_id="sel_proof_pack_2",
                alternative_set_id="different_set",
                alternative_id=alternative.alternative_id,
                actor_id="pm_001",
                reason_code="MODEL_DRIFT_REVIEW",
            ),
            created_by="pm_001",
            reason="Use selected alternative after drift review.",
            created_at=CREATED_AT,
            mandate_id="mandate_001",
        )
