from __future__ import annotations

from dataclasses import dataclass

from src.core.construction.models import (
    ConstructionAlternativeSelection,
    ConstructionAlternativeSet,
)
from src.core.construction.repository import ConstructionRepository
from src.core.proof_packs import ProofPackSourceValidationError
from src.core.rebalance_runs.models import DpmRunRecord, DpmRunWorkflowDecisionRecord
from src.core.rebalance_runs.service import DpmRunNotFoundError, DpmRunSupportService


@dataclass(frozen=True)
class ProofPackSelectedAlternativeSource:
    alternative_set: ConstructionAlternativeSet
    selection: ConstructionAlternativeSelection | None
    run: DpmRunRecord | None
    workflow_decisions: list[DpmRunWorkflowDecisionRecord]


def resolve_selected_alternative_source(
    *,
    alternative_set_id: str,
    selected_alternative_id: str,
    construction_repository: ConstructionRepository,
    run_service: DpmRunSupportService,
) -> ProofPackSelectedAlternativeSource:
    alternative_set = construction_repository.get_alternative_set(
        alternative_set_id=alternative_set_id
    )
    if alternative_set is None:
        raise ProofPackSourceValidationError("DPM_ALTERNATIVE_SET_NOT_FOUND")
    selected = next(
        (
            alternative
            for alternative in alternative_set.alternatives
            if alternative.alternative_id == selected_alternative_id
        ),
        None,
    )
    if selected is None:
        raise ProofPackSourceValidationError("DPM_SELECTED_ALTERNATIVE_NOT_FOUND")
    run = None
    workflow_decisions: list[DpmRunWorkflowDecisionRecord] = []
    if selected.rebalance_run_id is not None:
        try:
            run = run_service.get_run_record(rebalance_run_id=selected.rebalance_run_id)
            workflow_decisions = run_service.list_workflow_decision_records(
                rebalance_run_id=selected.rebalance_run_id
            )
        except DpmRunNotFoundError:
            run = None
            workflow_decisions = []
    return ProofPackSelectedAlternativeSource(
        alternative_set=alternative_set,
        selection=construction_repository.get_selection(alternative_set_id=alternative_set_id),
        run=run,
        workflow_decisions=workflow_decisions,
    )
