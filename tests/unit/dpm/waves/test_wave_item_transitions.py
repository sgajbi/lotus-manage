from src.api.services.wave_item_transitions import (
    approve_item,
    cancel_item,
    handoff_item,
    stage_item,
)
from src.core.waves import DpmRebalanceWaveItem


def _item(*, state: str, reason_codes: list[str] | None = None) -> DpmRebalanceWaveItem:
    return DpmRebalanceWaveItem(
        wave_item_id="dwi_transition",
        portfolio_id="PB_SG_TRANSITION",
        state=state,
        reason_codes=reason_codes or ["INITIAL_REASON"],
        diagnostics={"existing": "value"},
    )


def test_approve_item_adds_approval_diagnostics() -> None:
    updated = approve_item(
        _item(state="PROOF_PACK_READY"),
        "pm_001",
        "APPROVED_BY_PM",
        "Approved for staging.",
    )

    assert updated.state == "APPROVED"
    assert updated.reason_codes == ["INITIAL_REASON", "WAVE_ITEM_APPROVED"]
    assert updated.diagnostics == {
        "existing": "value",
        "approval_actor_id": "pm_001",
        "approval_reason_code": "APPROVED_BY_PM",
        "approval_comment": "Approved for staging.",
    }


def test_stage_item_marks_no_external_execution_claim() -> None:
    updated = stage_item(
        _item(state="APPROVED"),
        "ops_001",
        "READY_FOR_HANDOFF",
        None,
    )

    assert updated.state == "STAGED"
    assert updated.reason_codes == ["INITIAL_REASON", "WAVE_ITEM_STAGED"]
    assert updated.diagnostics == {
        "existing": "value",
        "stage_actor_id": "ops_001",
        "stage_reason_code": "READY_FOR_HANDOFF",
        "external_execution_claimed": False,
    }


def test_handoff_item_marks_internal_handoff_ready() -> None:
    updated = handoff_item(
        _item(state="STAGED"),
        "ops_001",
        "READY_FOR_OPERATIONS_REVIEW",
        "Operations package ready.",
    )

    assert updated.state == "HANDOFF_READY"
    assert updated.reason_codes == ["INITIAL_REASON", "WAVE_ITEM_HANDOFF_READY"]
    assert updated.diagnostics == {
        "existing": "value",
        "handoff_actor_id": "ops_001",
        "handoff_reason_code": "READY_FOR_OPERATIONS_REVIEW",
        "external_execution_claimed": False,
        "handoff_comment": "Operations package ready.",
    }


def test_cancel_item_preserves_handoff_ready_item() -> None:
    item = _item(state="HANDOFF_READY")

    assert cancel_item(item, "pm_001", "CANCEL_REQUESTED", None) is item


def test_cancel_item_excludes_non_handoff_ready_item() -> None:
    updated = cancel_item(
        _item(state="STAGED"),
        "pm_001",
        "CANCEL_REQUESTED",
        "Cancel before external execution.",
    )

    assert updated.state == "EXCLUDED"
    assert updated.reason_codes == ["INITIAL_REASON", "WAVE_ITEM_CANCELLED"]
    assert updated.diagnostics == {
        "existing": "value",
        "cancel_actor_id": "pm_001",
        "cancel_reason_code": "CANCEL_REQUESTED",
        "external_execution_claimed": False,
        "cancel_comment": "Cancel before external execution.",
    }


def test_non_matching_transition_returns_original_item() -> None:
    item = _item(state="SOURCE_READY")

    assert approve_item(item, "pm_001", "APPROVED_BY_PM", None) is item
    assert stage_item(item, "pm_001", "READY_FOR_HANDOFF", None) is item
    assert handoff_item(item, "pm_001", "READY_FOR_OPERATIONS_REVIEW", None) is item


def test_wave_item_transitions_exports_only_transition_builders() -> None:
    from src.api.services import wave_item_transitions

    assert wave_item_transitions.__all__ == [
        "approve_item",
        "cancel_item",
        "handoff_item",
        "stage_item",
    ]
