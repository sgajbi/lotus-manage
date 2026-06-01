from datetime import datetime, timedelta, timezone

from src.api.services.proof_pack_handoff_refs import (
    ensure_handoff_refs,
    find_stored_ref,
    hydrate_handoff_refs,
    require_handoff_ref,
    stored_ref_to_evidence_ref,
)
from src.core.proof_packs import AI_EVIDENCE_REF_TYPE, REPORT_INPUT_REF_TYPE
from src.core.proof_packs.models import DpmProofPackStoredRef
from src.infrastructure.proof_packs import InMemoryDpmProofPackRepository
from tests.unit.dpm.proof_packs.test_proof_pack_repository import _proof_pack


CREATED_AT = datetime(2026, 5, 3, 9, 30, tzinfo=timezone.utc)


def _stored_ref(
    *,
    ref_type: str,
    ref_id: str,
    content_hash: str,
    created_at: datetime = CREATED_AT,
) -> DpmProofPackStoredRef:
    return DpmProofPackStoredRef(
        proof_pack_id=_proof_pack().proof_pack_id,
        ref_type=ref_type,
        ref_id=ref_id,
        source_system="lotus-manage",
        content_hash=content_hash,
        created_at=created_at.isoformat(),
    )


def test_find_stored_ref_returns_latest_matching_append_only_ref() -> None:
    proof_pack = _proof_pack()
    repository = InMemoryDpmProofPackRepository()
    repository.save_proof_pack(
        proof_pack=proof_pack,
        idempotency_key=None,
        retention_expires_at=None,
    )
    repository.append_ref(
        ref=_stored_ref(
            ref_type=REPORT_INPUT_REF_TYPE,
            ref_id="dpri_old",
            content_hash="sha256:old",
        )
    )
    repository.append_ref(
        ref=_stored_ref(
            ref_type=AI_EVIDENCE_REF_TYPE,
            ref_id="dpai_current",
            content_hash="sha256:ai",
        )
    )
    repository.append_ref(
        ref=_stored_ref(
            ref_type=REPORT_INPUT_REF_TYPE,
            ref_id="dpri_new",
            content_hash="sha256:new",
            created_at=CREATED_AT + timedelta(minutes=1),
        )
    )

    stored_ref = find_stored_ref(
        proof_pack_id=proof_pack.proof_pack_id,
        ref_type=REPORT_INPUT_REF_TYPE,
        proof_pack_repository=repository,
    )

    assert stored_ref is not None
    assert stored_ref.ref_id == "dpri_new"
    assert stored_ref.content_hash == "sha256:new"


def test_hydrate_handoff_refs_overlays_stored_refs_without_mutating_pack() -> None:
    proof_pack = _proof_pack()
    repository = InMemoryDpmProofPackRepository()
    repository.save_proof_pack(
        proof_pack=proof_pack,
        idempotency_key=None,
        retention_expires_at=None,
    )
    repository.append_ref(
        ref=_stored_ref(
            ref_type=REPORT_INPUT_REF_TYPE,
            ref_id="dpri_hydrated",
            content_hash="sha256:report",
        )
    )
    repository.append_ref(
        ref=_stored_ref(
            ref_type=AI_EVIDENCE_REF_TYPE,
            ref_id="dpai_hydrated",
            content_hash="sha256:ai",
        )
    )

    hydrated = hydrate_handoff_refs(
        proof_pack=proof_pack,
        proof_pack_repository=repository,
    )

    assert hydrated is not proof_pack
    assert proof_pack.report_input_ref is None
    assert proof_pack.ai_evidence_ref is None
    assert hydrated.report_input_ref is not None
    assert hydrated.report_input_ref.ref_id == "dpri_hydrated"
    assert hydrated.ai_evidence_ref is not None
    assert hydrated.ai_evidence_ref.ref_id == "dpai_hydrated"


def test_ensure_handoff_refs_skips_existing_matching_content_refs() -> None:
    proof_pack = _proof_pack()
    repository = InMemoryDpmProofPackRepository()
    repository.save_proof_pack(
        proof_pack=proof_pack,
        idempotency_key=None,
        retention_expires_at=None,
    )

    first = ensure_handoff_refs(
        proof_pack=proof_pack,
        proof_pack_repository=repository,
        include_report_input=True,
        include_ai_evidence_input=True,
    )
    second = ensure_handoff_refs(
        proof_pack=first,
        proof_pack_repository=repository,
        include_report_input=True,
        include_ai_evidence_input=True,
    )

    assert second.report_input_ref == first.report_input_ref
    assert second.ai_evidence_ref == first.ai_evidence_ref
    assert len(repository.list_refs(proof_pack_id=proof_pack.proof_pack_id)) == 2


def test_stored_ref_to_evidence_ref_preserves_handoff_identity() -> None:
    stored_ref = _stored_ref(
        ref_type=REPORT_INPUT_REF_TYPE,
        ref_id="dpri_identity",
        content_hash="sha256:identity",
    )

    evidence_ref = stored_ref_to_evidence_ref(stored_ref)

    assert evidence_ref.ref_type == stored_ref.ref_type
    assert evidence_ref.ref_id == stored_ref.ref_id
    assert evidence_ref.source_system == stored_ref.source_system
    assert evidence_ref.content_hash == stored_ref.content_hash


def test_require_handoff_ref_prefers_hydrated_ref_without_repository_lookup() -> None:
    proof_pack = _proof_pack()
    hydrated_ref = stored_ref_to_evidence_ref(
        _stored_ref(
            ref_type=REPORT_INPUT_REF_TYPE,
            ref_id="dpri_hydrated",
            content_hash="sha256:hydrated",
        )
    )

    class _FailingRepository:
        def list_refs(self, *, proof_pack_id: str):
            raise AssertionError("repository lookup should not run for hydrated refs")

    ref = require_handoff_ref(
        proof_pack_id=proof_pack.proof_pack_id,
        hydrated_ref=hydrated_ref,
        ref_type=REPORT_INPUT_REF_TYPE,
        proof_pack_repository=_FailingRepository(),  # type: ignore[arg-type]
    )

    assert ref is hydrated_ref


def test_require_handoff_ref_falls_back_to_latest_stored_ref() -> None:
    proof_pack = _proof_pack()
    repository = InMemoryDpmProofPackRepository()
    repository.save_proof_pack(
        proof_pack=proof_pack,
        idempotency_key=None,
        retention_expires_at=None,
    )
    repository.append_ref(
        ref=_stored_ref(
            ref_type=REPORT_INPUT_REF_TYPE,
            ref_id="dpri_required",
            content_hash="sha256:required",
        )
    )

    ref = require_handoff_ref(
        proof_pack_id=proof_pack.proof_pack_id,
        hydrated_ref=None,
        ref_type=REPORT_INPUT_REF_TYPE,
        proof_pack_repository=repository,
    )

    assert ref is not None
    assert ref.ref_id == "dpri_required"
    assert ref.content_hash == "sha256:required"


def test_require_handoff_ref_returns_none_when_no_generated_ref_exists() -> None:
    proof_pack = _proof_pack()
    repository = InMemoryDpmProofPackRepository()
    repository.save_proof_pack(
        proof_pack=proof_pack,
        idempotency_key=None,
        retention_expires_at=None,
    )

    ref = require_handoff_ref(
        proof_pack_id=proof_pack.proof_pack_id,
        hydrated_ref=None,
        ref_type=REPORT_INPUT_REF_TYPE,
        proof_pack_repository=repository,
    )

    assert ref is None
