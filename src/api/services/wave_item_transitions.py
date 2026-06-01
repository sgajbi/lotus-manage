from src.core.waves import DpmRebalanceWaveItem


def approve_item(
    item: DpmRebalanceWaveItem,
    actor_id: str,
    reason_code: str,
    comment: str | None,
) -> DpmRebalanceWaveItem:
    if item.state not in {"SELECTED", "PROOF_PACK_READY"}:
        return item
    diagnostics = {
        **item.diagnostics,
        "approval_actor_id": actor_id,
        "approval_reason_code": reason_code,
    }
    if comment:
        diagnostics["approval_comment"] = comment
    return item.model_copy(
        update={
            "state": "APPROVED",
            "reason_codes": [*item.reason_codes, "WAVE_ITEM_APPROVED"],
            "diagnostics": diagnostics,
        },
        deep=True,
    )


def stage_item(
    item: DpmRebalanceWaveItem,
    actor_id: str,
    reason_code: str,
    comment: str | None,
) -> DpmRebalanceWaveItem:
    if item.state != "APPROVED":
        return item
    diagnostics = {
        **item.diagnostics,
        "stage_actor_id": actor_id,
        "stage_reason_code": reason_code,
        "external_execution_claimed": False,
    }
    if comment:
        diagnostics["stage_comment"] = comment
    return item.model_copy(
        update={
            "state": "STAGED",
            "reason_codes": [*item.reason_codes, "WAVE_ITEM_STAGED"],
            "diagnostics": diagnostics,
        },
        deep=True,
    )


def handoff_item(
    item: DpmRebalanceWaveItem,
    actor_id: str,
    reason_code: str,
    comment: str | None,
) -> DpmRebalanceWaveItem:
    if item.state != "STAGED":
        return item
    diagnostics = {
        **item.diagnostics,
        "handoff_actor_id": actor_id,
        "handoff_reason_code": reason_code,
        "external_execution_claimed": False,
    }
    if comment:
        diagnostics["handoff_comment"] = comment
    return item.model_copy(
        update={
            "state": "HANDOFF_READY",
            "reason_codes": [*item.reason_codes, "WAVE_ITEM_HANDOFF_READY"],
            "diagnostics": diagnostics,
        },
        deep=True,
    )


def cancel_item(
    item: DpmRebalanceWaveItem,
    actor_id: str,
    reason_code: str,
    comment: str | None,
) -> DpmRebalanceWaveItem:
    if item.state == "HANDOFF_READY":
        return item
    diagnostics = {
        **item.diagnostics,
        "cancel_actor_id": actor_id,
        "cancel_reason_code": reason_code,
        "external_execution_claimed": False,
    }
    if comment:
        diagnostics["cancel_comment"] = comment
    return item.model_copy(
        update={
            "state": "EXCLUDED",
            "reason_codes": [*item.reason_codes, "WAVE_ITEM_CANCELLED"],
            "diagnostics": diagnostics,
        },
        deep=True,
    )


__all__ = ["approve_item", "cancel_item", "handoff_item", "stage_item"]
