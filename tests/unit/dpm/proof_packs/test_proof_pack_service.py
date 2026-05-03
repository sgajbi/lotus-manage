from datetime import datetime, timedelta, timezone

import pytest

from src.api.services import proof_pack_service
from src.core.construction import (
    ConstructionAlternativeSelection,
    build_alternative_set,
    build_rebalance_result_alternative,
)
from src.core.proof_packs.models import DpmProofPackStoredRef
from src.core.proof_packs.repository import DpmProofPackConflictError
from src.core.rebalance_runs.service import DpmRunNotFoundError
from src.infrastructure.construction import InMemoryConstructionRepository
from src.infrastructure.proof_packs import InMemoryDpmProofPackRepository
from tests.unit.dpm.proof_packs.test_proof_pack_builder import _ready_rebalance_result, _run_record
from tests.unit.dpm.proof_packs.test_proof_pack_repository import _proof_pack


CREATED_AT = datetime(2026, 5, 3, 9, 30, tzinfo=timezone.utc)


class _RunService:
    def __init__(self, *, missing: bool = False) -> None:
        self.missing = missing
        self.run = _run_record()

    def get_run_record(self, *, rebalance_run_id: str):
        if self.missing:
            raise DpmRunNotFoundError("DPM_RUN_NOT_FOUND")
        return self.run

    def list_workflow_decision_records(self, *, rebalance_run_id: str):
        if self.missing:
            raise DpmRunNotFoundError("DPM_RUN_NOT_FOUND")
        return []


def _construction_repository() -> tuple[InMemoryConstructionRepository, str, str]:
    result = _ready_rebalance_result()
    alternative = build_rebalance_result_alternative(result=result)
    alternative_set = build_alternative_set(
        alternative_set_id="cas_service_001",
        portfolio_id="pf_service_1",
        as_of="2026-05-03",
        alternatives=[alternative],
    ).model_copy(update={"generated_at": CREATED_AT})
    selection = ConstructionAlternativeSelection(
        selection_id="casel_service_001",
        alternative_set_id=alternative_set.alternative_set_id,
        alternative_id=alternative.alternative_id,
        actor_id="pm_service",
        reason_code="MODEL_DRIFT_REVIEW",
        comment="Use selected alternative.",
        correlation_id="corr-service-selection",
    )
    repository = InMemoryConstructionRepository()
    repository.save_alternative_set(alternative_set=alternative_set, idempotency_key=None)
    repository.save_selection(selection=selection)
    return repository, alternative_set.alternative_set_id, alternative.alternative_id


def test_selected_alternative_service_replays_idempotent_existing_pack() -> None:
    repository, alternative_set_id, selected_alternative_id = _construction_repository()
    proof_repository = InMemoryDpmProofPackRepository()

    first = proof_pack_service.generate_proof_pack_from_selected_alternative(
        alternative_set_id=alternative_set_id,
        selected_alternative_id=selected_alternative_id,
        actor_id="pm_service",
        reason="Initial proof.",
        correlation_id="corr-service-proof",
        mandate_id="mandate_service",
        idempotency_key="idem-service-proof",
        construction_repository=repository,
        run_service=_RunService(),
        proof_pack_repository=proof_repository,
    )
    replay = proof_pack_service.generate_proof_pack_from_selected_alternative(
        alternative_set_id=alternative_set_id,
        selected_alternative_id=selected_alternative_id,
        actor_id="pm_service",
        reason="Changed proof reason should replay.",
        correlation_id="corr-service-proof-replay",
        mandate_id="mandate_service",
        idempotency_key="idem-service-proof",
        construction_repository=repository,
        run_service=_RunService(missing=True),
        proof_pack_repository=proof_repository,
    )

    assert replay == first


def test_selected_alternative_service_validates_sources_and_missing_run_degrades() -> None:
    repository, alternative_set_id, selected_alternative_id = _construction_repository()
    proof_repository = InMemoryDpmProofPackRepository()

    with pytest.raises(proof_pack_service.ProofPackSourceValidationError, match="NOT_FOUND"):
        proof_pack_service.generate_proof_pack_from_selected_alternative(
            alternative_set_id="missing",
            selected_alternative_id=selected_alternative_id,
            actor_id="pm_service",
            reason=None,
            correlation_id=None,
            mandate_id=None,
            idempotency_key=None,
            construction_repository=repository,
            run_service=_RunService(),
            proof_pack_repository=proof_repository,
        )
    with pytest.raises(
        proof_pack_service.ProofPackSourceValidationError,
        match="DPM_SELECTED_ALTERNATIVE_NOT_FOUND",
    ):
        proof_pack_service.generate_proof_pack_from_selected_alternative(
            alternative_set_id=alternative_set_id,
            selected_alternative_id="missing",
            actor_id="pm_service",
            reason=None,
            correlation_id=None,
            mandate_id=None,
            idempotency_key=None,
            construction_repository=repository,
            run_service=_RunService(),
            proof_pack_repository=proof_repository,
        )

    proof_pack = proof_pack_service.generate_proof_pack_from_selected_alternative(
        alternative_set_id=alternative_set_id,
        selected_alternative_id=selected_alternative_id,
        actor_id="pm_service",
        reason=None,
        correlation_id=None,
        mandate_id="mandate_service",
        idempotency_key=None,
        construction_repository=repository,
        run_service=_RunService(missing=True),
        proof_pack_repository=proof_repository,
    )

    assert proof_pack.rebalance_run_id is None
    assert proof_pack.alternative_set_id == alternative_set_id


def test_handoff_ref_lookup_uses_append_only_refs_and_reports_missing_refs() -> None:
    repository = InMemoryDpmProofPackRepository()
    proof_pack = _proof_pack()
    repository.save_proof_pack(
        proof_pack=proof_pack,
        idempotency_key=None,
        retention_expires_at=None,
    )

    with pytest.raises(
        proof_pack_service.DpmProofPackReportInputNotGeneratedError,
        match="DPM_PROOF_PACK_REPORT_INPUT_NOT_GENERATED",
    ):
        proof_pack_service.get_report_input_ref(
            proof_pack_id=proof_pack.proof_pack_id,
            proof_pack_repository=repository,
        )
    with pytest.raises(
        proof_pack_service.DpmProofPackAiEvidenceInputNotGeneratedError,
        match="DPM_PROOF_PACK_AI_EVIDENCE_INPUT_NOT_GENERATED",
    ):
        proof_pack_service.get_ai_evidence_ref(
            proof_pack_id=proof_pack.proof_pack_id,
            proof_pack_repository=repository,
        )

    report_ref = DpmProofPackStoredRef(
        proof_pack_id=proof_pack.proof_pack_id,
        ref_type=proof_pack_service.REPORT_INPUT_REF_TYPE,
        ref_id="dpri_service_001",
        source_system="lotus-manage",
        content_hash="sha256:report",
        created_at=CREATED_AT.isoformat(),
    )
    ai_ref = DpmProofPackStoredRef(
        proof_pack_id=proof_pack.proof_pack_id,
        ref_type=proof_pack_service.AI_EVIDENCE_REF_TYPE,
        ref_id="dpai_service_001",
        source_system="lotus-manage",
        content_hash="sha256:ai",
        created_at=CREATED_AT.isoformat(),
    )
    repository.append_ref(ref=report_ref)
    repository.append_ref(ref=ai_ref)

    assert (
        proof_pack_service.get_report_input_ref(
            proof_pack_id=proof_pack.proof_pack_id,
            proof_pack_repository=repository,
        ).content_hash
        == "sha256:report"
    )
    assert (
        proof_pack_service.get_ai_evidence_ref(
            proof_pack_id=proof_pack.proof_pack_id,
            proof_pack_repository=repository,
        ).content_hash
        == "sha256:ai"
    )


def test_ensure_handoff_refs_is_idempotent_for_existing_matching_refs() -> None:
    repository = InMemoryDpmProofPackRepository()
    proof_pack = _proof_pack()
    repository.save_proof_pack(
        proof_pack=proof_pack,
        idempotency_key=None,
        retention_expires_at=None,
    )

    first = proof_pack_service.ensure_handoff_refs(
        proof_pack=proof_pack,
        proof_pack_repository=repository,
        include_report_input=True,
        include_ai_evidence_input=True,
    )
    second = proof_pack_service.ensure_handoff_refs(
        proof_pack=first,
        proof_pack_repository=repository,
        include_report_input=True,
        include_ai_evidence_input=True,
    )

    assert second.report_input_ref == first.report_input_ref
    assert second.ai_evidence_ref == first.ai_evidence_ref
    assert len(repository.list_refs(proof_pack_id=proof_pack.proof_pack_id)) == 2


def test_handoff_ref_lookup_prefers_latest_append_only_ref() -> None:
    repository = InMemoryDpmProofPackRepository()
    proof_pack = _proof_pack()
    repository.save_proof_pack(
        proof_pack=proof_pack,
        idempotency_key=None,
        retention_expires_at=None,
    )
    repository.append_ref(
        ref=DpmProofPackStoredRef(
            proof_pack_id=proof_pack.proof_pack_id,
            ref_type=proof_pack_service.REPORT_INPUT_REF_TYPE,
            ref_id="dpri_old",
            source_system="lotus-manage",
            content_hash="sha256:old",
            created_at=CREATED_AT.isoformat(),
        )
    )
    repository.append_ref(
        ref=DpmProofPackStoredRef(
            proof_pack_id=proof_pack.proof_pack_id,
            ref_type=proof_pack_service.REPORT_INPUT_REF_TYPE,
            ref_id="dpri_new",
            source_system="lotus-manage",
            content_hash="sha256:new",
            created_at=(CREATED_AT + timedelta(minutes=1)).isoformat(),
        )
    )

    report_ref = proof_pack_service.get_report_input_ref(
        proof_pack_id=proof_pack.proof_pack_id,
        proof_pack_repository=repository,
    )

    assert report_ref.ref_id == "dpri_new"
    assert report_ref.content_hash == "sha256:new"


def test_proof_pack_service_exception_mapping() -> None:
    mappings = [
        (DpmProofPackConflictError("conflict"), 409, "conflict"),
        (DpmRunNotFoundError("missing"), 404, "missing"),
        (proof_pack_service.ProofPackSourceValidationError("bad-source"), 404, "bad-source"),
        (
            proof_pack_service.DpmProofPackReportInputNotGeneratedError("no-report"),
            424,
            "no-report",
        ),
        (RuntimeError("boom"), 500, "RuntimeError"),
    ]

    for exc, status_code, detail in mappings:
        http_exc = proof_pack_service.to_api_http_exception(exc)

        assert http_exc.status_code == status_code
        assert http_exc.detail == detail
