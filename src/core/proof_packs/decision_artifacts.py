"""Decision summary and timeline builders for proof packs."""

from src.core.construction.models import (
    ConstructionAlternative,
    ConstructionAlternativeSelection,
    ConstructionAlternativeSet,
)
from src.core.models import RebalanceResult
from src.core.proof_packs.models import (
    DpmProofPackDecisionSummary,
    DpmProofPackDecisionTimeline,
    DpmProofPackDecisionTimelineEvent,
    DpmProofPackSupportability,
    ProofPackSourceType,
)
from src.core.rebalance_runs.models import DpmRunRecord, DpmRunWorkflowDecisionRecord


def decision_summary(
    *,
    source_type: ProofPackSourceType,
    result: RebalanceResult | None,
    selected_alternative: ConstructionAlternative | None,
    reason: str | None,
    supportability: DpmProofPackSupportability,
) -> DpmProofPackDecisionSummary:
    return DpmProofPackDecisionSummary(
        decision_type="PRE_TRADE_REBALANCE",
        recommended_action=recommended_action(supportability=supportability),
        selected_alternative_type=selected_alternative_type(
            selected_alternative=selected_alternative
        ),
        business_rationale=reason or "No actor rationale supplied.",
        expected_benefit=expected_benefit(selected_alternative=selected_alternative),
        main_tradeoffs=main_tradeoffs(selected_alternative=selected_alternative),
        top_risks=supportability.reason_codes[:5],
        approval_state=approval_state(result=result),
        operations_state=supportability.status,
    )


def recommended_action(*, supportability: DpmProofPackSupportability) -> str:
    if supportability.status == "READY":
        return "APPROVE_REBALANCE"
    return "REVIEW_REBALANCE"


def selected_alternative_type(
    *, selected_alternative: ConstructionAlternative | None
) -> str | None:
    if selected_alternative is None:
        return None
    return str(selected_alternative.method)


def expected_benefit(*, selected_alternative: ConstructionAlternative | None) -> str:
    if selected_alternative is None:
        return "Direct source run proof pack."
    return selected_alternative.summary


def approval_state(*, result: RebalanceResult | None) -> str:
    if result is None:
        return "BLOCKED"
    return result.status


def main_tradeoffs(*, selected_alternative: ConstructionAlternative | None) -> list[str]:
    if selected_alternative is None:
        return ["No construction alternative comparison was selected."]
    metrics = selected_alternative.comparison_metrics
    return [
        f"turnover_weight={metrics.turnover_weight}",
        f"drift_reduction={metrics.drift_reduction}",
        f"trade_count={metrics.trade_count}",
    ]


def decision_timeline(
    *,
    proof_pack_id: str,
    generated_at: str,
    source_type: ProofPackSourceType,
    run: DpmRunRecord | None,
    alternative_set: ConstructionAlternativeSet | None,
    selected_alternative: ConstructionAlternative | None,
    selection: ConstructionAlternativeSelection | None,
    workflow_decisions: list[DpmRunWorkflowDecisionRecord],
    created_by: str,
) -> DpmProofPackDecisionTimeline:
    events = source_decision_timeline_events(
        run=run,
        alternative_set=alternative_set,
        selected_alternative=selected_alternative,
        selection=selection,
        generated_at=generated_at,
        created_by=created_by,
    )
    events.extend(workflow_decision_timeline_events(workflow_decisions))
    events.append(
        proof_pack_generated_timeline_event(
            proof_pack_id=proof_pack_id,
            generated_at=generated_at,
            source_type=source_type,
            created_by=created_by,
        )
    )
    return DpmProofPackDecisionTimeline(events=sorted(events, key=decision_timeline_event_sort_key))


def source_decision_timeline_events(
    *,
    run: DpmRunRecord | None,
    alternative_set: ConstructionAlternativeSet | None,
    selected_alternative: ConstructionAlternative | None,
    selection: ConstructionAlternativeSelection | None,
    generated_at: str,
    created_by: str,
) -> list[DpmProofPackDecisionTimelineEvent]:
    events: list[DpmProofPackDecisionTimelineEvent] = []
    if run is not None:
        events.append(run_created_timeline_event(run))
    if alternative_set is not None:
        events.append(alternative_set_generated_timeline_event(alternative_set))
    if selected_alternative is not None:
        events.append(
            selected_alternative_timeline_event(
                selected_alternative=selected_alternative,
                selection=selection,
                generated_at=generated_at,
                created_by=created_by,
            )
        )
    return events


def run_created_timeline_event(
    run: DpmRunRecord,
) -> DpmProofPackDecisionTimelineEvent:
    return DpmProofPackDecisionTimelineEvent(
        event_id=f"{run.rebalance_run_id}:run_created",
        event_type="REBALANCE_RUN_CREATED",
        event_time=run.created_at.isoformat(),
        actor="lotus-manage",
        source_system="lotus-manage",
        status=str(run.result_json.get("status", "UNKNOWN")),
        reason_codes=[],
    )


def alternative_set_generated_timeline_event(
    alternative_set: ConstructionAlternativeSet,
) -> DpmProofPackDecisionTimelineEvent:
    return DpmProofPackDecisionTimelineEvent(
        event_id=f"{alternative_set.alternative_set_id}:generated",
        event_type="ALTERNATIVE_SET_GENERATED",
        event_time=alternative_set.generated_at.isoformat(),
        actor="lotus-manage",
        source_system="lotus-manage",
        status=str(alternative_set.status),
        reason_codes=[],
    )


def selected_alternative_timeline_event(
    *,
    selected_alternative: ConstructionAlternative,
    selection: ConstructionAlternativeSelection | None,
    generated_at: str,
    created_by: str,
) -> DpmProofPackDecisionTimelineEvent:
    return DpmProofPackDecisionTimelineEvent(
        event_id=f"{selected_alternative.alternative_id}:selected",
        event_type="SELECTED_ALTERNATIVE",
        event_time=selection.selected_at.isoformat() if selection else generated_at,
        actor=selection.actor_id if selection else created_by,
        source_system="lotus-manage",
        status=str(selected_alternative.method_status),
        reason_codes=[selection.reason_code] if selection else [],
    )


def workflow_decision_timeline_events(
    workflow_decisions: list[DpmRunWorkflowDecisionRecord],
) -> list[DpmProofPackDecisionTimelineEvent]:
    return [
        DpmProofPackDecisionTimelineEvent(
            event_id=f"{decision.decision_id}:workflow_decision",
            event_type="WORKFLOW_DECISION",
            event_time=decision.decided_at.isoformat(),
            actor=decision.actor_id,
            source_system="lotus-manage",
            status=str(decision.action),
            reason_codes=[decision.reason_code],
        )
        for decision in workflow_decisions
    ]


def proof_pack_generated_timeline_event(
    *,
    proof_pack_id: str,
    generated_at: str,
    source_type: ProofPackSourceType,
    created_by: str,
) -> DpmProofPackDecisionTimelineEvent:
    return DpmProofPackDecisionTimelineEvent(
        event_id=f"{proof_pack_id}:generated",
        event_type="PROOF_PACK_GENERATED",
        event_time=generated_at,
        actor=created_by,
        source_system="lotus-manage",
        status=source_type,
        reason_codes=[],
    )


_DECISION_TIMELINE_EVENT_RANK = {
    "REBALANCE_RUN_CREATED": 0,
    "ALTERNATIVE_SET_GENERATED": 1,
    "SELECTED_ALTERNATIVE": 2,
    "WORKFLOW_DECISION": 3,
    "PROOF_PACK_GENERATED": 4,
}


def decision_timeline_event_sort_key(
    event: DpmProofPackDecisionTimelineEvent,
) -> tuple[str, int, str]:
    return (
        event.event_time,
        _DECISION_TIMELINE_EVENT_RANK.get(event.event_type, 99),
        event.event_id,
    )
