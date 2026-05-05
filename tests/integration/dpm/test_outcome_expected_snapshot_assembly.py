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
from src.core.outcomes import (
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


def _alternative_set() -> ConstructionAlternativeSet:
    return ConstructionAlternativeSet(
        alternative_set_id="cas_001",
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        as_of="2026-05-05",
        status=ConstructionMethodStatus.READY,
        alternatives=[
            ConstructionAlternative(
                alternative_id="alt_min_turnover",
                method=ConstructionMethod.MIN_TURNOVER,
                method_status=ConstructionMethodStatus.READY,
                summary="Reduce drift with bounded turnover.",
                rebalance_run_id="rr_001",
                objective_trace=[],
                constraint_trace=[],
                comparison_metrics=ConstructionComparisonMetrics(
                    drift_before=Decimal("0.1200"),
                    drift_after=Decimal("0.0350"),
                    drift_reduction=Decimal("0.0850"),
                    turnover_weight=Decimal("0.0700"),
                    trade_count=4,
                    estimated_transaction_cost=Money(amount=Decimal("125.00"), currency="SGD"),
                    cash_weight_after=Decimal("0.0400"),
                ),
                intent_ids=["intent_001", "intent_002"],
                diagnostics={"generated_at": "2026-05-05T01:00:00Z"},
            )
        ],
        request_hash="sha256:alternative-set",
        input_mode="stateful",
        source_supportability_state="READY",
    )


def _selection(alternative_id: str = "alt_min_turnover") -> ConstructionAlternativeSelection:
    return ConstructionAlternativeSelection(
        selection_id="sel_001",
        alternative_set_id="cas_001",
        alternative_id=alternative_id,
        actor_id="pm_001",
        reason_code="BEST_IMPLEMENTATION_TRADE_OFF",
        comment="Best implementation trade-off.",
        selected_at=datetime(2026, 5, 5, 1, 5, tzinfo=timezone.utc),
        correlation_id="corr_001",
    )


def _proof_section(section_id: str = "selected_alternative") -> DpmProofPackSection:
    return DpmProofPackSection(
        section_id=section_id,
        section_type="selected_alternative",
        state="READY",
        title="Selected alternative",
        summary="Selected min-turnover construction alternative.",
        facts={"alternative_id": "alt_min_turnover"},
        metrics={"drift_after": "0.0350"},
        reason_codes=["SELECTED_ALTERNATIVE_READY"],
        evidence_refs=[],
        source_refs=[
            DpmProofPackSourceRef(
                source_system="lotus-manage",
                source_type="CONSTRUCTION_SELECTED_ALTERNATIVE",
                source_id="cas_001:alt_min_turnover",
                supportability_state="READY",
                content_hash="sha256:selected-alternative",
            )
        ],
        source_supportability={"state": "READY"},
        generated_at="2026-05-05T01:06:00Z",
        content_hash="sha256:selected-section",
    )


def _proof_pack(
    *,
    portfolio_id: str = "PB_SG_GLOBAL_BAL_001",
    alternative_set_id: str | None = "cas_001",
    selected_alternative_id: str | None = "alt_min_turnover",
) -> DpmPreTradeProofPack:
    section = _proof_section()
    return DpmPreTradeProofPack(
        proof_pack_id="dpp_001",
        proof_pack_version="1.0.0",
        portfolio_id=portfolio_id,
        mandate_id="MANDATE_PB_SG_GLOBAL_BAL_001",
        source_type="SELECTED_ALTERNATIVE",
        rebalance_run_id="rr_001",
        alternative_set_id=alternative_set_id,
        selected_alternative_id=selected_alternative_id,
        as_of_date="2026-05-05",
        status="READY",
        decision_summary=DpmProofPackDecisionSummary(
            decision_type="REBALANCE",
            recommended_action="Proceed with min-turnover alternative.",
            selected_alternative_type="MIN_TURNOVER",
            business_rationale="Reduce drift within implementation constraints.",
            expected_benefit="Drift reduction after trade.",
            main_tradeoffs=["Accept modest turnover."],
            top_risks=["Execution evidence arrives post-trade."],
            approval_state="APPROVED",
            operations_state="HANDOFF_READY",
        ),
        sections=[section],
        approval_requirements=section,
        operations_handoff=section,
        decision_timeline=DpmProofPackDecisionTimeline(events=[]),
        lineage=section,
        supportability=DpmProofPackSupportability(
            status="READY",
            section_state_counts={"READY": 1},
            ready_section_count=1,
            degraded_section_count=0,
            blocked_section_count=0,
            pending_review_section_count=0,
            reason_codes=["PROOF_PACK_READY"],
            section_hashes={"selected_alternative": "sha256:selected-section"},
        ),
        content_hash="sha256:proof-pack",
        source_hashes={"selected_alternative": "sha256:selected-alternative"},
        created_at=datetime(2026, 5, 5, 1, 7, tzinfo=timezone.utc),
        created_by="pm_001",
        correlation_id="corr_001",
    )


def _wave(*, external_execution_claimed: bool = False) -> DpmRebalanceWave:
    item = DpmRebalanceWaveItem(
        wave_item_id="dwi_001",
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        mandate_id="MANDATE_PB_SG_GLOBAL_BAL_001",
        model_portfolio_id="MODEL_SG_BALANCED",
        state="HANDOFF_READY",
        reason_codes=["WAVE_ITEM_HANDOFF_READY"],
        source_refs=[],
        alternative_set_id="cas_001",
        selected_alternative_id="alt_min_turnover",
        proof_pack_id="dpp_001",
        diagnostics={"proof_pack_state": "READY"},
    )
    return DpmRebalanceWave(
        wave_id="dwv_001",
        wave_version="1.0.0",
        state="HANDOFF_READY",
        trigger=DpmWaveTrigger(
            trigger_type="EXPLICIT_PORTFOLIO_LIST",
            trigger_id="manual-wave-001",
            rationale="Review canonical portfolio.",
            source_refs=[],
        ),
        as_of_date="2026-05-05",
        created_at=datetime(2026, 5, 5, 1, 10, tzinfo=timezone.utc),
        created_by="pm_001",
        correlation_id="corr_wave_001",
        items=[item],
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
                handoff_ref_id="dwh_001",
                wave_id="dwv_001",
                item_ids=["dwi_001"],
                actor_id="pm_001",
                reason_code="READY_FOR_OPERATIONS_REVIEW",
                correlation_id="corr_handoff_001",
                external_execution_claimed=external_execution_claimed,
                content_hash="sha256:handoff",
                created_at=datetime(2026, 5, 5, 1, 12, tzinfo=timezone.utc),
            )
        ],
    )


def test_expected_snapshot_assembles_selected_alternative_proof_pack_wave_and_handoff() -> None:
    snapshot = assemble_expected_outcome_snapshot(
        alternative_set=_alternative_set(),
        selection=_selection(),
        proof_pack=_proof_pack(),
        wave=_wave(),
        wave_item_id="dwi_001",
        handoff_ref_id="dwh_001",
    )

    assert snapshot.portfolio_id == "PB_SG_GLOBAL_BAL_001"
    assert snapshot.mandate_id == "MANDATE_PB_SG_GLOBAL_BAL_001"
    assert snapshot.rebalance_run_id == "rr_001"
    assert snapshot.proof_pack_id == "dpp_001"
    assert snapshot.wave_id == "dwv_001"
    assert snapshot.wave_item_id == "dwi_001"
    assert snapshot.operations_handoff_ref_id == "dwh_001"
    assert snapshot.supportability.state == "READY"
    assert snapshot.expected_values["DRIFT_REDUCTION"].value == Decimal("0.0350")
    assert snapshot.expected_values["COST"].value == Decimal("125.00")
    assert snapshot.expected_values["CASH_RESIDUAL"].value == Decimal("0.0400")
    assert snapshot.section_hashes["selected_alternative"] == "sha256:selected-section"
    assert snapshot.source_hashes["selected_alternative"] == "sha256:selected-alternative"
    assert snapshot.calculation_trace["defaulted_expected_values"] == []
    assert {
        (source.source_system, source.source_type, source.source_id)
        for source in snapshot.source_lineage
    } >= {
        ("lotus-manage", "CONSTRUCTION_ALTERNATIVE_SET", "cas_001"),
        ("lotus-manage", "PRE_TRADE_PROOF_PACK", "dpp_001"),
        ("lotus-manage", "REBALANCE_WAVE", "dwv_001"),
        ("lotus-manage", "INTERNAL_OPERATIONS_HANDOFF", "dwh_001"),
    }


def test_expected_snapshot_rejects_proof_pack_selected_alternative_mismatch() -> None:
    with pytest.raises(DpmExpectedSnapshotAssemblyError, match="selected_alternative_id mismatch"):
        assemble_expected_outcome_snapshot(
            alternative_set=_alternative_set(),
            selection=_selection(),
            proof_pack=_proof_pack(selected_alternative_id="alt_other"),
        )


def test_expected_snapshot_rejects_missing_selected_alternative() -> None:
    with pytest.raises(DpmExpectedSnapshotAssemblyError, match="selection alternative_id"):
        assemble_expected_outcome_snapshot(
            alternative_set=_alternative_set(),
            selection=_selection(alternative_id="alt_missing"),
            proof_pack=_proof_pack(selected_alternative_id="alt_missing"),
        )


def test_expected_snapshot_rejects_wave_item_linkage_mismatch() -> None:
    wave = _wave()
    wave.items[0].proof_pack_id = "dpp_other"

    with pytest.raises(DpmExpectedSnapshotAssemblyError, match="wave_item.proof_pack_id mismatch"):
        assemble_expected_outcome_snapshot(
            alternative_set=_alternative_set(),
            selection=_selection(),
            proof_pack=_proof_pack(),
            wave=wave,
            wave_item_id="dwi_001",
        )


def test_expected_snapshot_rejects_handoff_external_execution_claim() -> None:
    with pytest.raises(DpmExpectedSnapshotAssemblyError, match="external execution"):
        assemble_expected_outcome_snapshot(
            alternative_set=_alternative_set(),
            selection=_selection(),
            proof_pack=_proof_pack(),
            wave=_wave(external_execution_claimed=True),
            wave_item_id="dwi_001",
            handoff_ref_id="dwh_001",
        )


def test_expected_snapshot_rejects_selection_set_wave_and_handoff_shape_errors() -> None:
    with pytest.raises(DpmExpectedSnapshotAssemblyError, match="alternative_set_id"):
        assemble_expected_outcome_snapshot(
            alternative_set=_alternative_set(),
            selection=ConstructionAlternativeSelection(
                **{
                    **_selection().model_dump(),
                    "alternative_set_id": "cas_other",
                }
            ),
            proof_pack=_proof_pack(),
        )

    with pytest.raises(DpmExpectedSnapshotAssemblyError, match="without wave"):
        assemble_expected_outcome_snapshot(
            alternative_set=_alternative_set(),
            selection=_selection(),
            proof_pack=_proof_pack(),
            wave_item_id="dwi_001",
        )

    with pytest.raises(DpmExpectedSnapshotAssemblyError, match="required when wave"):
        assemble_expected_outcome_snapshot(
            alternative_set=_alternative_set(),
            selection=_selection(),
            proof_pack=_proof_pack(),
            wave=_wave(),
        )

    with pytest.raises(DpmExpectedSnapshotAssemblyError, match="does not exist in wave"):
        assemble_expected_outcome_snapshot(
            alternative_set=_alternative_set(),
            selection=_selection(),
            proof_pack=_proof_pack(),
            wave=_wave(),
            wave_item_id="missing",
        )

    with pytest.raises(DpmExpectedSnapshotAssemblyError, match="requires wave and wave_item"):
        assemble_expected_outcome_snapshot(
            alternative_set=_alternative_set(),
            selection=_selection(),
            proof_pack=_proof_pack(),
            handoff_ref_id="dwh_001",
        )

    with pytest.raises(DpmExpectedSnapshotAssemblyError, match="handoff_ref_id does not exist"):
        assemble_expected_outcome_snapshot(
            alternative_set=_alternative_set(),
            selection=_selection(),
            proof_pack=_proof_pack(),
            wave=_wave(),
            wave_item_id="dwi_001",
            handoff_ref_id="missing",
        )

    wave = _wave()
    wave.handoff_refs[0].item_ids = ["dwi_other"]
    with pytest.raises(DpmExpectedSnapshotAssemblyError, match="does not include"):
        assemble_expected_outcome_snapshot(
            alternative_set=_alternative_set(),
            selection=_selection(),
            proof_pack=_proof_pack(),
            wave=wave,
            wave_item_id="dwi_001",
            handoff_ref_id="dwh_001",
        )


def test_expected_snapshot_rejects_selected_alternative_without_expected_values() -> None:
    alternative_set = _alternative_set()
    metrics = alternative_set.alternatives[0].comparison_metrics
    metrics.drift_after = None
    metrics.estimated_transaction_cost = None
    metrics.cash_weight_after = None

    with pytest.raises(DpmExpectedSnapshotAssemblyError, match="does not expose"):
        assemble_expected_outcome_snapshot(
            alternative_set=alternative_set,
            selection=_selection(),
            proof_pack=_proof_pack(),
        )


def test_expected_snapshot_dedupes_lineage_refs_from_proof_sections() -> None:
    proof_pack = _proof_pack()
    proof_pack.sections[0].source_refs.append(
        DpmProofPackSourceRef(
            source_system="lotus-manage",
            source_type="PRE_TRADE_PROOF_PACK",
            source_id="dpp_001",
            supportability_state="READY",
            content_hash="sha256:proof-pack",
        )
    )

    snapshot = assemble_expected_outcome_snapshot(
        alternative_set=_alternative_set(),
        selection=_selection(),
        proof_pack=proof_pack,
    )

    assert [
        (ref.source_system, ref.source_type, ref.source_id) for ref in snapshot.source_lineage
    ].count(("lotus-manage", "PRE_TRADE_PROOF_PACK", "dpp_001")) == 1


@pytest.mark.parametrize(
    ("set_status", "method_status", "source_state", "proof_status", "wave_item_state", "expected"),
    [
        (
            ConstructionMethodStatus.BLOCKED,
            ConstructionMethodStatus.READY,
            "READY",
            "READY",
            "HANDOFF_READY",
            "BLOCKED",
        ),
        (
            ConstructionMethodStatus.READY,
            ConstructionMethodStatus.PENDING_REVIEW,
            "READY",
            "READY",
            "HANDOFF_READY",
            "PENDING_REVIEW",
        ),
        (
            ConstructionMethodStatus.READY,
            ConstructionMethodStatus.READY,
            "DEGRADED",
            "READY",
            "HANDOFF_READY",
            "DEGRADED",
        ),
        (
            ConstructionMethodStatus.READY,
            ConstructionMethodStatus.DEGRADED,
            "READY",
            "READY",
            "HANDOFF_READY",
            "DEGRADED",
        ),
        (
            ConstructionMethodStatus.READY,
            ConstructionMethodStatus.READY,
            "READY",
            "UNRECOGNIZED",
            "HANDOFF_READY",
            "BLOCKED",
        ),
        (
            ConstructionMethodStatus.READY,
            ConstructionMethodStatus.READY,
            "READY",
            "READY",
            "SOURCE_DEGRADED",
            "DEGRADED",
        ),
        (
            ConstructionMethodStatus.READY,
            ConstructionMethodStatus.READY,
            "READY",
            "READY",
            "SOURCE_BLOCKED",
            "BLOCKED",
        ),
    ],
)
def test_expected_snapshot_rolls_up_pre_trade_supportability_states(
    set_status: ConstructionMethodStatus,
    method_status: ConstructionMethodStatus,
    source_state: str,
    proof_status: str,
    wave_item_state: str,
    expected: str,
) -> None:
    alternative_set = _alternative_set()
    alternative_set.status = set_status
    alternative_set.source_supportability_state = source_state
    alternative_set.alternatives[0].method_status = method_status
    proof_pack = _proof_pack()
    proof_pack.status = proof_status
    wave = _wave()
    wave.items[0].state = wave_item_state

    snapshot = assemble_expected_outcome_snapshot(
        alternative_set=alternative_set,
        selection=_selection(),
        proof_pack=proof_pack,
        wave=wave,
        wave_item_id="dwi_001",
    )

    assert snapshot.supportability.state == expected
