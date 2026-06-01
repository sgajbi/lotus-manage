import re

from src.api.services.wave_handoff_evidence import build_handoff_ref, handoff_content_hash


def test_build_handoff_ref_marks_internal_operations_boundary() -> None:
    handoff_ref = build_handoff_ref(
        wave_id="dwv_handoff",
        item_ids=["dwi_001", "dwi_002"],
        actor_id="pm_001",
        reason_code="READY_FOR_OPERATIONS_REVIEW",
        correlation_id="corr-handoff",
        comment="Reviewed by PM desk.",
    )

    assert re.fullmatch(r"dwh_[0-9a-f]{12}", handoff_ref.handoff_ref_id)
    assert handoff_ref.wave_id == "dwv_handoff"
    assert handoff_ref.item_ids == ["dwi_001", "dwi_002"]
    assert handoff_ref.actor_id == "pm_001"
    assert handoff_ref.reason_code == "READY_FOR_OPERATIONS_REVIEW"
    assert handoff_ref.correlation_id == "corr-handoff"
    assert handoff_ref.external_execution_claimed is False
    assert handoff_ref.content_hash.startswith("sha256:")
    assert handoff_ref.metadata == {
        "handoff_contract": "RFC-0041_INTERNAL_OPERATIONS_HANDOFF_V1",
        "handoff_boundary": "NO_EXTERNAL_EXECUTION",
        "item_count": 2,
        "comment": "Reviewed by PM desk.",
    }


def test_build_handoff_ref_omits_empty_comment_from_metadata() -> None:
    handoff_ref = build_handoff_ref(
        wave_id="dwv_handoff",
        item_ids=["dwi_001"],
        actor_id="pm_001",
        reason_code="READY_FOR_OPERATIONS_REVIEW",
        correlation_id="corr-handoff",
        comment=None,
    )

    assert handoff_ref.metadata == {
        "handoff_contract": "RFC-0041_INTERNAL_OPERATIONS_HANDOFF_V1",
        "handoff_boundary": "NO_EXTERNAL_EXECUTION",
        "item_count": 1,
    }


def test_handoff_content_hash_is_stable_for_key_order() -> None:
    assert handoff_content_hash({"b": 2, "a": 1}) == handoff_content_hash({"a": 1, "b": 2})


def test_wave_handoff_evidence_exports_only_handoff_builders() -> None:
    from src.api.services import wave_handoff_evidence

    assert wave_handoff_evidence.__all__ == ["build_handoff_ref", "handoff_content_hash"]
