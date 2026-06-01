from src.api.services import wave_workflow_metadata
from src.api.services.wave_workflow_metadata import (
    approval_event_metadata,
    cancel_event_metadata,
    handoff_event_metadata,
    selection_event_metadata,
    stage_event_metadata,
)
from src.core.waves import DpmWaveHandoffRef


def _handoff_ref() -> DpmWaveHandoffRef:
    return DpmWaveHandoffRef.model_construct(
        handoff_ref_id="dwh_test",
        wave_id="dwv_test",
        item_ids=["dwi_1"],
        actor_id="pm_001",
        reason_code="READY_FOR_OPERATIONS",
        correlation_id="corr_handoff",
        external_execution_claimed=False,
        content_hash="sha256:test",
        metadata={},
    )


def test_approval_event_metadata_counts_exceptions_and_preserves_comment() -> None:
    assert approval_event_metadata(
        approved_item_count=2,
        total_item_count=3,
        reason_code="PM_APPROVED",
        comment="approved with exception",
    ) == {
        "approved_item_count": 2,
        "exception_item_count": 1,
        "approval_reason_code": "PM_APPROVED",
        "comment": "approved with exception",
    }


def test_selection_event_metadata_preserves_selected_alternative_and_proof_pack() -> None:
    assert selection_event_metadata(
        wave_item_id="dwi_select",
        alternative_set_id="alt_set_001",
        selected_alternative_id="alt_balanced",
        proof_pack_id="proof_pack_001",
        proof_pack_state="READY_FOR_REVIEW",
    ) == {
        "wave_item_id": "dwi_select",
        "alternative_set_id": "alt_set_001",
        "selected_alternative_id": "alt_balanced",
        "proof_pack_id": "proof_pack_001",
        "proof_pack_state": "READY_FOR_REVIEW",
    }


def test_stage_event_metadata_omits_empty_comment() -> None:
    assert stage_event_metadata(
        staged_item_count=2,
        reason_code="READY_TO_STAGE",
        comment=None,
    ) == {
        "staged_item_count": 2,
        "stage_reason_code": "READY_TO_STAGE",
    }


def test_handoff_event_metadata_preserves_internal_execution_boundary() -> None:
    assert handoff_event_metadata(
        handoff_ref=_handoff_ref(),
        handoff_item_count=1,
        reason_code="READY_FOR_OPERATIONS",
        comment="handoff reviewed",
    ) == {
        "handoff_ref_id": "dwh_test",
        "handoff_item_count": 1,
        "external_execution_claimed": False,
        "handoff_reason_code": "READY_FOR_OPERATIONS",
        "comment": "handoff reviewed",
    }


def test_cancel_event_metadata_preserves_no_external_execution_claim() -> None:
    assert cancel_event_metadata(
        cancelled_item_count=3,
        reason_code="CLIENT_CANCELLED",
        comment=None,
    ) == {
        "cancel_reason_code": "CLIENT_CANCELLED",
        "cancelled_item_count": 3,
        "external_execution_claimed": False,
    }


def test_wave_workflow_metadata_exports_public_surface() -> None:
    assert wave_workflow_metadata.__all__ == [
        "approval_event_metadata",
        "cancel_event_metadata",
        "handoff_event_metadata",
        "selection_event_metadata",
        "stage_event_metadata",
    ]
