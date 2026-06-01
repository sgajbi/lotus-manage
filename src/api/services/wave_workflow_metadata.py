from __future__ import annotations

from src.core.waves import DpmWaveHandoffRef


def approval_event_metadata(
    *,
    approved_item_count: int,
    total_item_count: int,
    reason_code: str,
    comment: str | None,
) -> dict[str, object]:
    return _with_optional_comment(
        {
            "approved_item_count": approved_item_count,
            "exception_item_count": total_item_count - approved_item_count,
            "approval_reason_code": reason_code,
        },
        comment=comment,
    )


def stage_event_metadata(
    *,
    staged_item_count: int,
    reason_code: str,
    comment: str | None,
) -> dict[str, object]:
    return _with_optional_comment(
        {
            "staged_item_count": staged_item_count,
            "stage_reason_code": reason_code,
        },
        comment=comment,
    )


def handoff_event_metadata(
    *,
    handoff_ref: DpmWaveHandoffRef,
    handoff_item_count: int,
    reason_code: str,
    comment: str | None,
) -> dict[str, object]:
    return _with_optional_comment(
        {
            "handoff_ref_id": handoff_ref.handoff_ref_id,
            "handoff_item_count": handoff_item_count,
            "external_execution_claimed": False,
            "handoff_reason_code": reason_code,
        },
        comment=comment,
    )


def cancel_event_metadata(
    *,
    cancelled_item_count: int,
    reason_code: str,
    comment: str | None,
) -> dict[str, object]:
    return _with_optional_comment(
        {
            "cancel_reason_code": reason_code,
            "cancelled_item_count": cancelled_item_count,
            "external_execution_claimed": False,
        },
        comment=comment,
    )


def _with_optional_comment(
    metadata: dict[str, object],
    *,
    comment: str | None,
) -> dict[str, object]:
    if comment:
        return {**metadata, "comment": comment}
    return metadata


__all__ = [
    "approval_event_metadata",
    "cancel_event_metadata",
    "handoff_event_metadata",
    "stage_event_metadata",
]
