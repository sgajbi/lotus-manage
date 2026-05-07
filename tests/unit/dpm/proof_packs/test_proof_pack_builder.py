from datetime import datetime, timezone
from decimal import Decimal

import pytest

from src.core.construction import (
    AuthoritativePerformanceContext,
    AuthoritativeRiskContext,
    ConstructionAuthorityContext,
    ConstructionAlternativeSelection,
    build_alternative_set,
    build_rebalance_result_alternative,
)
from src.core.models import EngineOptions, Money, RebalanceResult, TaxImpact
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
