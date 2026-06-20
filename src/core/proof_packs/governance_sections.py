"""Governance section payload builders for RFC-0040 proof packs."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from src.core.models import GateDecision, RebalanceResult
from src.core.proof_packs.models import ProofPackSectionState, ProofPackSectionType
from src.core.rebalance_runs.models import DpmRunRecord, DpmRunWorkflowDecisionRecord
from src.core.construction.models import ConstructionAlternativeSelection

SectionPayload = tuple[ProofPackSectionState, str, dict[str, Any], dict[str, Any], list[str]]

GovernanceSectionPayloadBuilder = Callable[["_GovernanceSectionPayloadInput"], SectionPayload]


@dataclass(frozen=True)
class _GovernanceSectionPayloadInput:
    result: RebalanceResult
    run: DpmRunRecord | None
    selection: ConstructionAlternativeSelection | None
    source_ref_count: int
    workflow_decisions: list[DpmRunWorkflowDecisionRecord]


def proof_pack_governance_section_payload(
    *,
    section_type: ProofPackSectionType,
    result: RebalanceResult,
    run: DpmRunRecord | None,
    selection: ConstructionAlternativeSelection | None,
    source_ref_count: int,
    workflow_decisions: list[DpmRunWorkflowDecisionRecord],
) -> SectionPayload | None:
    builder = governance_section_payload_builder(section_type)
    if builder is None:
        return None
    return builder(
        _GovernanceSectionPayloadInput(
            result=result,
            run=run,
            selection=selection,
            source_ref_count=source_ref_count,
            workflow_decisions=workflow_decisions,
        )
    )


def governance_section_payload_builder(
    section_type: ProofPackSectionType,
) -> GovernanceSectionPayloadBuilder | None:
    return _GOVERNANCE_SECTION_PAYLOAD_BUILDERS.get(section_type)


def approval_requirements_governance_payload(
    context: _GovernanceSectionPayloadInput,
) -> SectionPayload:
    return approval_requirements_section_payload(
        result=context.result,
        workflow_decisions=context.workflow_decisions,
    )


def operations_handoff_governance_payload(
    context: _GovernanceSectionPayloadInput,
) -> SectionPayload:
    return operations_handoff_section_payload(result=context.result)


def decision_timeline_governance_payload(
    context: _GovernanceSectionPayloadInput,
) -> SectionPayload:
    return decision_timeline_section_payload(run=context.run, selection=context.selection)


def lineage_governance_payload(context: _GovernanceSectionPayloadInput) -> SectionPayload:
    return lineage_section_payload(
        result=context.result,
        run=context.run,
        source_ref_count=context.source_ref_count,
    )


def supportability_governance_payload(
    context: _GovernanceSectionPayloadInput,
) -> SectionPayload:
    return supportability_section_payload()


_GOVERNANCE_SECTION_PAYLOAD_BUILDERS: dict[
    ProofPackSectionType,
    GovernanceSectionPayloadBuilder,
] = {
    "approval_requirements": approval_requirements_governance_payload,
    "operations_handoff": operations_handoff_governance_payload,
    "decision_timeline": decision_timeline_governance_payload,
    "lineage": lineage_governance_payload,
    "supportability": supportability_governance_payload,
}


def operations_handoff_section_payload(*, result: RebalanceResult) -> SectionPayload:
    return (
        "READY" if result.status == "READY" else "PENDING_REVIEW",
        "Operations handoff reflects current pre-trade readiness.",
        {"run_status": result.status},
        {},
        [] if result.status == "READY" else ["DPM_OPERATIONS_REVIEW_REQUIRED"],
    )


def decision_timeline_section_payload(
    *,
    run: DpmRunRecord | None,
    selection: ConstructionAlternativeSelection | None,
) -> SectionPayload:
    return (
        "READY",
        "Timeline generated from source run, selection, and proof-pack generation events.",
        {
            "run_created_at": run.created_at.isoformat() if run else None,
            "selection_id": selection.selection_id if selection else None,
        },
        {},
        [],
    )


def lineage_section_payload(
    *,
    result: RebalanceResult,
    run: DpmRunRecord | None,
    source_ref_count: int,
) -> SectionPayload:
    return (
        "READY" if run is not None else "BLOCKED",
        "Lineage identifiers captured from source run and source artifacts.",
        result.lineage.model_dump(mode="json") if result else {},
        {"source_ref_count": source_ref_count},
        [] if run is not None else ["DPM_LINEAGE_RUN_MISSING"],
    )


def supportability_section_payload() -> SectionPayload:
    return ("READY", "Supportability summary is generated for every proof pack.", {}, {}, [])


def approval_requirements_section_payload(
    *,
    result: RebalanceResult,
    workflow_decisions: list[DpmRunWorkflowDecisionRecord],
) -> SectionPayload:
    gate = result.gate_decision
    workflow_facts = approval_workflow_decision_facts(workflow_decisions)
    return (
        approval_section_state(result=result, gate=gate),
        "Approval posture captured from run status and gate decision.",
        {
            "gate_decision": approval_gate_fact(gate),
            "workflow_decisions": workflow_facts,
        },
        {"workflow_decision_count": len(workflow_facts)},
        approval_reason_codes(gate),
    )


def approval_workflow_decision_facts(
    workflow_decisions: list[DpmRunWorkflowDecisionRecord],
) -> list[dict[str, Any]]:
    return [
        decision.model_dump(mode="json")
        for decision in sorted(workflow_decisions, key=lambda item: item.decided_at)
    ]


def approval_section_state(
    *, result: RebalanceResult, gate: GateDecision | None
) -> ProofPackSectionState:
    if run_blocks_approval(result) or gate_blocks_approval(gate):
        return "BLOCKED"
    if run_requires_approval_review(result) or gate_requires_approval_review(gate):
        return "PENDING_REVIEW"
    return "READY"


def run_blocks_approval(result: RebalanceResult) -> bool:
    return result.status == "BLOCKED"


def gate_blocks_approval(gate: GateDecision | None) -> bool:
    return gate is not None and gate.gate == "BLOCKED"


def run_requires_approval_review(result: RebalanceResult) -> bool:
    return result.status == "PENDING_REVIEW"


def gate_requires_approval_review(gate: GateDecision | None) -> bool:
    return gate is not None and gate.gate.endswith("REQUIRED")


def approval_gate_fact(gate: GateDecision | None) -> dict[str, Any] | None:
    return gate.model_dump(mode="json") if gate is not None else None


def approval_reason_codes(gate: GateDecision | None) -> list[str]:
    if gate is None:
        return []
    return [reason.reason_code for reason in gate.reasons]
