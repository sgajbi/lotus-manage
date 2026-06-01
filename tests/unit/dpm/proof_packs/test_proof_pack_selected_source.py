from datetime import datetime, timezone

import pytest

from src.api.services.proof_pack_selected_source import resolve_selected_alternative_source
from src.core.construction import (
    ConstructionAlternativeSelection,
    build_alternative_set,
    build_rebalance_result_alternative,
)
from src.core.proof_packs import ProofPackSourceValidationError
from src.core.rebalance_runs.models import DpmRunWorkflowDecisionRecord
from src.core.rebalance_runs.service import DpmRunNotFoundError
from src.infrastructure.construction import InMemoryConstructionRepository
from tests.unit.dpm.proof_packs.test_proof_pack_builder import (
    _ready_rebalance_result,
    _run_record,
)


CREATED_AT = datetime(2026, 5, 3, 9, 30, tzinfo=timezone.utc)


class _RunService:
    def __init__(self, *, missing: bool = False) -> None:
        self.missing = missing
        self.run = _run_record()
        self.decisions = [
            DpmRunWorkflowDecisionRecord(
                decision_id="dwd_selected_source_001",
                run_id=self.run.rebalance_run_id,
                action="APPROVE",
                reason_code="REVIEW_APPROVED",
                comment="Approved for proof pack.",
                actor_id="pm_selected_source",
                decided_at=CREATED_AT,
                correlation_id="corr-selected-source",
            )
        ]

    def get_run_record(self, *, rebalance_run_id: str):
        if self.missing:
            raise DpmRunNotFoundError("DPM_RUN_NOT_FOUND")
        return self.run

    def list_workflow_decision_records(self, *, rebalance_run_id: str):
        if self.missing:
            raise DpmRunNotFoundError("DPM_RUN_NOT_FOUND")
        return self.decisions


def _construction_repository() -> tuple[InMemoryConstructionRepository, str, str]:
    result = _ready_rebalance_result()
    alternative = build_rebalance_result_alternative(result=result)
    alternative_set = build_alternative_set(
        alternative_set_id="cas_selected_source_001",
        portfolio_id="pf_selected_source_1",
        as_of="2026-05-03",
        alternatives=[alternative],
    ).model_copy(update={"generated_at": CREATED_AT})
    selection = ConstructionAlternativeSelection(
        selection_id="casel_selected_source_001",
        alternative_set_id=alternative_set.alternative_set_id,
        alternative_id=alternative.alternative_id,
        actor_id="pm_selected_source",
        reason_code="MODEL_DRIFT_REVIEW",
        comment="Use selected alternative.",
        correlation_id="corr-selected-source",
    )
    repository = InMemoryConstructionRepository()
    repository.save_alternative_set(alternative_set=alternative_set, idempotency_key=None)
    repository.save_selection(selection=selection)
    return repository, alternative_set.alternative_set_id, alternative.alternative_id


def test_resolve_selected_alternative_source_returns_selection_run_and_decisions() -> None:
    repository, alternative_set_id, selected_alternative_id = _construction_repository()
    run_service = _RunService()

    source = resolve_selected_alternative_source(
        alternative_set_id=alternative_set_id,
        selected_alternative_id=selected_alternative_id,
        construction_repository=repository,
        run_service=run_service,
    )

    assert source.alternative_set.alternative_set_id == alternative_set_id
    assert source.selection is not None
    assert source.selection.alternative_id == selected_alternative_id
    assert source.run == run_service.run
    assert source.workflow_decisions == run_service.decisions


def test_resolve_selected_alternative_source_degrades_when_linked_run_is_missing() -> None:
    repository, alternative_set_id, selected_alternative_id = _construction_repository()

    source = resolve_selected_alternative_source(
        alternative_set_id=alternative_set_id,
        selected_alternative_id=selected_alternative_id,
        construction_repository=repository,
        run_service=_RunService(missing=True),
    )

    assert source.run is None
    assert source.workflow_decisions == []


def test_resolve_selected_alternative_source_rejects_missing_alternative_set() -> None:
    repository, _, selected_alternative_id = _construction_repository()

    with pytest.raises(ProofPackSourceValidationError, match="DPM_ALTERNATIVE_SET_NOT_FOUND"):
        resolve_selected_alternative_source(
            alternative_set_id="missing",
            selected_alternative_id=selected_alternative_id,
            construction_repository=repository,
            run_service=_RunService(),
        )


def test_resolve_selected_alternative_source_rejects_missing_selected_alternative() -> None:
    repository, alternative_set_id, _ = _construction_repository()

    with pytest.raises(ProofPackSourceValidationError, match="DPM_SELECTED_ALTERNATIVE_NOT_FOUND"):
        resolve_selected_alternative_source(
            alternative_set_id=alternative_set_id,
            selected_alternative_id="missing",
            construction_repository=repository,
            run_service=_RunService(),
        )
