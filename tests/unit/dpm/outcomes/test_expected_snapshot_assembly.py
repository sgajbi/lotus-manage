from datetime import datetime, timezone
from decimal import Decimal

import pytest

from src.core.construction.models import (
    ConstructionAlternative,
    ConstructionAlternativeSelection,
    ConstructionAlternativeSet,
    ConstructionComparisonMetrics,
)
from src.core.construction.vocabulary import ConstructionMethod, ConstructionMethodStatus
from src.core.models import Money
from src.core.outcomes.snapshots import (
    DpmExpectedSnapshotAssemblyError,
    assemble_expected_outcome_snapshot,
)
from src.core.proof_packs.models import (
    DpmPreTradeProofPack,
    DpmProofPackDecisionSummary,
    DpmProofPackDecisionTimeline,
    DpmProofPackSection,
    DpmProofPackSourceRef,
    DpmProofPackSupportability,
)
from src.core.waves.models import (
    DpmRebalanceWave,
    DpmRebalanceWaveItem,
    DpmWaveAggregateMetrics,
    DpmWaveHandoffRef,
    DpmWaveTrigger,
)


def _alternative_set(
    *,
    status: ConstructionMethodStatus = ConstructionMethodStatus.READY,
    method_status: ConstructionMethodStatus = ConstructionMethodStatus.READY,
    source_supportability_state: str | None = None,
    cost: Money | None = Money(amount=Decimal("12.34"), currency="SGD"),
    cash_weight_after: Decimal | None = Decimal("0.0450"),
) -> ConstructionAlternativeSet:
    return ConstructionAlternativeSet(
        alternative_set_id="cas_outcome_001",
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        as_of="2026-05-12",
        status=status,
        request_hash="sha256:cas-request",
        source_supportability_state=source_supportability_state,
        alternatives=[
            ConstructionAlternative(
                alternative_id="alt_selected",
                method=ConstructionMethod.HEURISTIC_EXPLAINABLE,
                method_status=method_status,
                summary="Reduce active-weight drift with explainable trades.",
                rebalance_run_id="rr_outcome_001",
                objective_trace=[],
                constraint_trace=[],
                comparison_metrics=ConstructionComparisonMetrics(
                    drift_before=Decimal("0.1200"),
                    drift_after=Decimal("0.0300"),
                    drift_reduction=Decimal("0.0900"),
                    turnover_weight=Decimal("0.1100"),
                    trade_count=2,
                    estimated_transaction_cost=cost,
                    cash_weight_after=cash_weight_after,
                ),
                intent_ids=["oi_buy_001", "oi_sell_001"],
                diagnostics={"generated_at": "2026-05-12T01:00:00Z"},
            )
        ],
    )


def _selection(
    *,
    alternative_set_id: str = "cas_outcome_001",
    alternative_id: str = "alt_selected",
) -> ConstructionAlternativeSelection:
    return ConstructionAlternativeSelection(
        selection_id="sel_outcome_001",
        alternative_set_id=alternative_set_id,
        alternative_id=alternative_id,
        actor_id="pm_001",
        reason_code="LOWER_DRIFT_WITH_ACCEPTABLE_COST",
        correlation_id="corr-outcome-001",
    )


def _section(
    section_id: str,
    section_type: str,
    *,
    state: str = "READY",
    source_refs: list[DpmProofPackSourceRef] | None = None,
) -> DpmProofPackSection:
    return DpmProofPackSection(
        section_id=section_id,
        section_type=section_type,
        state=state,
        title=section_id.replace("_", " ").title(),
        summary="Operator-safe evidence summary.",
        reason_codes=[],
        source_refs=source_refs or [],
        generated_at="2026-05-12T01:05:00Z",
        content_hash=f"sha256:{section_id}",
    )


def _proof_pack(
    *,
    portfolio_id: str = "PB_SG_GLOBAL_BAL_001",
    mandate_id: str | None = "MANDATE_PB_SG_GLOBAL_BAL_001",
    alternative_set_id: str | None = "cas_outcome_001",
    selected_alternative_id: str | None = "alt_selected",
    rebalance_run_id: str | None = "rr_outcome_001",
    status: str = "READY",
    supportability_reasons: list[str] | None = None,
) -> DpmPreTradeProofPack:
    lineage_ref = DpmProofPackSourceRef(
        source_system="lotus-risk",
        source_type="CONCENTRATION_ANALYSIS",
        source_id="risk_conc_001",
        supportability_state="READY",
        content_hash="sha256:risk-conc-001",
    )
    lineage = _section("lineage", "lineage", source_refs=[lineage_ref])
    approval = _section("approval_requirements", "approval_requirements")
    operations = _section("operations_handoff", "operations_handoff")
    sections = [
        _section("selected_alternative", "selected_alternative", source_refs=[lineage_ref]),
        approval,
        operations,
        lineage,
    ]
    return DpmPreTradeProofPack(
        proof_pack_id="dpp_outcome_001",
        proof_pack_version="1.0.0",
        portfolio_id=portfolio_id,
        mandate_id=mandate_id,
        source_type="SELECTED_ALTERNATIVE",
        rebalance_run_id=rebalance_run_id,
        alternative_set_id=alternative_set_id,
        selected_alternative_id=selected_alternative_id,
        as_of_date="2026-05-12",
        status=status,
        decision_summary=DpmProofPackDecisionSummary(
            decision_type="DPM_REBALANCE",
            recommended_action="PM_REVIEW",
            selected_alternative_type="HEURISTIC_EXPLAINABLE",
            business_rationale="Reduce drift using source-backed construction evidence.",
            expected_benefit="Lower model drift.",
            main_tradeoffs=["Turnover accepted."],
            top_risks=[],
            approval_state="READY",
            operations_state="INTERNAL_HANDOFF_READY",
        ),
        sections=sections,
        approval_requirements=approval,
        operations_handoff=operations,
        decision_timeline=DpmProofPackDecisionTimeline(events=[]),
        lineage=lineage,
        supportability=DpmProofPackSupportability(
            status=status,
            section_state_counts={status: len(sections)},
            ready_section_count=len(sections) if status == "READY" else 0,
            degraded_section_count=1 if status == "DEGRADED" else 0,
            blocked_section_count=1 if status == "BLOCKED" else 0,
            pending_review_section_count=1 if status == "PENDING_REVIEW" else 0,
            reason_codes=supportability_reasons or [],
            section_hashes={"selected_alternative": "sha256:section-override"},
        ),
        content_hash="sha256:proof-pack",
        source_hashes={
            "selected_alternative": "sha256:selected-alternative",
            "risk_conc_001": "sha256:risk-conc-001",
        },
        created_at=datetime(2026, 5, 12, 1, 5, tzinfo=timezone.utc),
        created_by="lotus-manage",
        correlation_id="corr-outcome-001",
    )


def _wave(
    *,
    item_state: str = "HANDOFF_READY",
    handoff_external_execution_claimed: bool = False,
) -> DpmRebalanceWave:
    item = DpmRebalanceWaveItem(
        wave_item_id="dwi_outcome_001",
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        mandate_id="MANDATE_PB_SG_GLOBAL_BAL_001",
        state=item_state,
        reason_codes=["WAVE_ITEM_READY_FOR_HANDOFF"],
        alternative_set_id="cas_outcome_001",
        selected_alternative_id="alt_selected",
        proof_pack_id="dpp_outcome_001",
    )
    handoff = DpmWaveHandoffRef(
        handoff_ref_id="dwh_outcome_001",
        wave_id="dwv_outcome_001",
        item_ids=["dwi_outcome_001"],
        actor_id="ops_001",
        reason_code="READY_FOR_OPERATIONS_REVIEW",
        correlation_id="corr-outcome-001",
        external_execution_claimed=handoff_external_execution_claimed,
        content_hash="sha256:handoff",
    )
    return DpmRebalanceWave(
        wave_id="dwv_outcome_001",
        state="HANDOFF_READY",
        trigger=DpmWaveTrigger(
            trigger_type="EXPLICIT_PORTFOLIO_LIST",
            trigger_id="manual-review-001",
            rationale="PM-selected rebalance review.",
        ),
        as_of_date="2026-05-12",
        created_by="pm_001",
        correlation_id="corr-outcome-001",
        items=[item],
        aggregate_metrics=DpmWaveAggregateMetrics(
            item_count=1,
            state_counts={item_state: 1},
            ready_item_count=1,
            blocked_item_count=0,
            review_required_item_count=0,
            source_degraded_item_count=0,
        ),
        handoff_refs=[handoff],
    )


def test_expected_snapshot_preserves_construction_proof_pack_wave_and_handoff_lineage() -> None:
    snapshot = assemble_expected_outcome_snapshot(
        alternative_set=_alternative_set(),
        selection=_selection(),
        proof_pack=_proof_pack(supportability_reasons=["PROOF_PACK_SOURCE_READY"]),
        wave=_wave(),
        wave_item_id="dwi_outcome_001",
        handoff_ref_id="dwh_outcome_001",
    )

    assert snapshot.portfolio_id == "PB_SG_GLOBAL_BAL_001"
    assert snapshot.wave_id == "dwv_outcome_001"
    assert snapshot.wave_item_id == "dwi_outcome_001"
    assert snapshot.operations_handoff_ref_id == "dwh_outcome_001"
    assert set(snapshot.expected_values) == {"DRIFT_REDUCTION", "COST", "CASH_RESIDUAL"}
    assert snapshot.expected_values["COST"].value == Decimal("12.34")
    assert snapshot.supportability.state == "READY"
    assert snapshot.supportability.reason_codes == [
        "CONSTRUCTION_READY",
        "ALTERNATIVE_SET_READY",
        "PROOF_PACK_READY",
        "PROOF_PACK_SOURCE_READY",
        "WAVE_ITEM_HANDOFF_READY",
        "READY_FOR_OPERATIONS_REVIEW",
    ]
    assert snapshot.section_hashes["selected_alternative"] == "sha256:section-override"
    assert snapshot.section_hashes["lineage"] == "sha256:lineage"
    assert snapshot.calculation_trace["selected_method"] == str(
        ConstructionMethod.HEURISTIC_EXPLAINABLE
    )
    source_keys = {
        (ref.source_system, ref.source_type, ref.source_id) for ref in snapshot.source_lineage
    }
    assert ("lotus-manage", "REBALANCE_WAVE", "dwv_outcome_001") in source_keys
    assert ("lotus-manage", "INTERNAL_OPERATIONS_HANDOFF", "dwh_outcome_001") in source_keys
    assert ("lotus-risk", "CONCENTRATION_ANALYSIS", "risk_conc_001") in source_keys


@pytest.mark.parametrize(
    ("alternative_set", "proof_pack", "expected_state"),
    [
        (
            _alternative_set(source_supportability_state="DEGRADED"),
            _proof_pack(),
            "DEGRADED",
        ),
        (
            _alternative_set(method_status=ConstructionMethodStatus.PENDING_REVIEW),
            _proof_pack(),
            "PENDING_REVIEW",
        ),
        (
            _alternative_set(status=ConstructionMethodStatus.BLOCKED),
            _proof_pack(status="READY"),
            "BLOCKED",
        ),
        (
            _alternative_set(),
            _proof_pack().model_copy(update={"status": "ARCHIVED"}),
            "BLOCKED",
        ),
    ],
)
def test_expected_snapshot_rolls_up_supportability_state(
    alternative_set: ConstructionAlternativeSet,
    proof_pack: DpmPreTradeProofPack,
    expected_state: str,
) -> None:
    snapshot = assemble_expected_outcome_snapshot(
        alternative_set=alternative_set,
        selection=_selection(),
        proof_pack=proof_pack,
    )

    assert snapshot.supportability.state == expected_state


def test_expected_snapshot_omits_optional_cost_and_cash_values_when_not_source_backed() -> None:
    snapshot = assemble_expected_outcome_snapshot(
        alternative_set=_alternative_set(cost=None, cash_weight_after=None),
        selection=_selection(),
        proof_pack=_proof_pack(),
    )

    assert set(snapshot.expected_values) == {"DRIFT_REDUCTION"}


@pytest.mark.parametrize(
    ("selection", "proof_pack", "message"),
    [
        (
            _selection(alternative_set_id="cas_other"),
            _proof_pack(),
            "selection alternative_set_id does not match alternative set",
        ),
        (
            _selection(alternative_id="alt_missing"),
            _proof_pack(),
            "selection alternative_id does not exist in alternative set",
        ),
        (
            _selection(),
            _proof_pack(portfolio_id="PB_SG_OTHER_001"),
            "proof_pack.portfolio_id mismatch",
        ),
        (
            _selection(),
            _proof_pack(rebalance_run_id="rr_other"),
            "proof_pack.rebalance_run_id mismatch",
        ),
    ],
)
def test_expected_snapshot_rejects_inconsistent_selection_and_proof_pack_linkage(
    selection: ConstructionAlternativeSelection,
    proof_pack: DpmPreTradeProofPack,
    message: str,
) -> None:
    with pytest.raises(DpmExpectedSnapshotAssemblyError, match=message):
        assemble_expected_outcome_snapshot(
            alternative_set=_alternative_set(),
            selection=selection,
            proof_pack=proof_pack,
        )


def test_expected_snapshot_requires_complete_wave_item_context() -> None:
    with pytest.raises(
        DpmExpectedSnapshotAssemblyError,
        match="wave_item_id cannot be supplied without wave",
    ):
        assemble_expected_outcome_snapshot(
            alternative_set=_alternative_set(),
            selection=_selection(),
            proof_pack=_proof_pack(),
            wave_item_id="dwi_outcome_001",
        )

    with pytest.raises(
        DpmExpectedSnapshotAssemblyError,
        match="wave_item_id is required when wave evidence is supplied",
    ):
        assemble_expected_outcome_snapshot(
            alternative_set=_alternative_set(),
            selection=_selection(),
            proof_pack=_proof_pack(),
            wave=_wave(),
        )


@pytest.mark.parametrize(
    ("wave", "wave_item_id", "message"),
    [
        (_wave(), "dwi_missing", "wave_item_id does not exist in wave"),
        (
            _wave().model_copy(
                update={
                    "items": [_wave().items[0].model_copy(update={"mandate_id": "MANDATE_OTHER"})]
                }
            ),
            "dwi_outcome_001",
            "wave_item.mandate_id mismatch",
        ),
    ],
)
def test_expected_snapshot_rejects_invalid_wave_item_linkage(
    wave: DpmRebalanceWave,
    wave_item_id: str,
    message: str,
) -> None:
    with pytest.raises(DpmExpectedSnapshotAssemblyError, match=message):
        assemble_expected_outcome_snapshot(
            alternative_set=_alternative_set(),
            selection=_selection(),
            proof_pack=_proof_pack(),
            wave=wave,
            wave_item_id=wave_item_id,
        )


def test_expected_snapshot_rejects_invalid_handoff_linkage_and_external_execution_claims() -> None:
    with pytest.raises(
        DpmExpectedSnapshotAssemblyError,
        match="handoff_ref_id requires wave and wave_item evidence",
    ):
        assemble_expected_outcome_snapshot(
            alternative_set=_alternative_set(),
            selection=_selection(),
            proof_pack=_proof_pack(),
            handoff_ref_id="dwh_outcome_001",
        )

    with pytest.raises(
        DpmExpectedSnapshotAssemblyError,
        match="handoff_ref_id does not include the selected wave item",
    ):
        assemble_expected_outcome_snapshot(
            alternative_set=_alternative_set(),
            selection=_selection(),
            proof_pack=_proof_pack(),
            wave=_wave().model_copy(
                update={
                    "handoff_refs": [
                        _wave().handoff_refs[0].model_copy(update={"item_ids": ["dwi_other"]})
                    ]
                }
            ),
            wave_item_id="dwi_outcome_001",
            handoff_ref_id="dwh_outcome_001",
        )

    with pytest.raises(
        DpmExpectedSnapshotAssemblyError,
        match="manage handoff evidence cannot claim external execution",
    ):
        assemble_expected_outcome_snapshot(
            alternative_set=_alternative_set(),
            selection=_selection(),
            proof_pack=_proof_pack(),
            wave=_wave(handoff_external_execution_claimed=True),
            wave_item_id="dwi_outcome_001",
            handoff_ref_id="dwh_outcome_001",
        )
