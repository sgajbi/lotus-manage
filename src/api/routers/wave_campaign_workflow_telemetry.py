from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from src.api.observability import record_campaign_workflow


def record_campaign_workflow_success(*, surface: str, replay: bool = False) -> None:
    record_campaign_workflow(
        surface=surface,
        outcome="replay" if replay else "success",
        reason="replay" if replay else "success",
    )


def record_campaign_workflow_readiness(
    *,
    surface: str,
    blocked: bool,
) -> None:
    record_campaign_workflow(
        surface=surface,
        outcome="blocked" if blocked else "success",
        reason="launch_blocked" if blocked else "success",
    )


def record_campaign_workflow_unexpected_error(*, surface: str) -> None:
    record_campaign_workflow(
        surface=surface,
        outcome="error",
        reason="unexpected_error",
    )


def record_campaign_workflow_validation_failure(*, surface: str, reason: str) -> None:
    record_campaign_workflow(
        surface=surface,
        outcome="validation_failed",
        reason=reason,
    )


def campaign_workflow_http_exception(*, surface: str, exc: HTTPException) -> HTTPException:
    outcome, reason = _campaign_workflow_labels_for_http_exception(exc)
    record_campaign_workflow(surface=surface, outcome=outcome, reason=reason)
    return exc


def _campaign_workflow_labels_for_http_exception(exc: HTTPException) -> tuple[str, str]:
    code = _http_exception_code(exc)
    if code == "BULK_REVIEW_CAMPAIGN_DEFINITION_NOT_FOUND":
        return "not_found", "definition_not_found"
    if code == "BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_NOT_FOUND":
        return "not_found", "task_not_found"
    if code == "BULK_REVIEW_CAMPAIGN_ACTOR_REQUIRED_FOR_ENTITLEMENT":
        return "entitlement_failed", "entitlement_required"
    if code == "BULK_REVIEW_CAMPAIGN_ACTOR_NOT_ENTITLED":
        return "entitlement_failed", "entitlement_denied"
    if code == "BULK_REVIEW_CAMPAIGN_DEFINITION_LAUNCH_BLOCKED":
        return "blocked", "launch_blocked"
    if code and code.endswith("_REF_CONFLICT"):
        return "conflict", "reference_conflict"
    if exc.status_code == 404:
        return "not_found", "definition_not_found"
    if exc.status_code == 409:
        return "conflict", "definition_conflict"
    if exc.status_code == 422:
        return "validation_failed", "validation_error"
    return "error", "unexpected_error"


def _http_exception_code(exc: HTTPException) -> str | None:
    detail = exc.detail
    if isinstance(detail, dict):
        code = detail.get("code")
        return code if isinstance(code, str) else None
    if isinstance(detail, list):
        for item in detail:
            code = _code_from_detail_item(item)
            if code:
                return code
    return None


def _code_from_detail_item(item: Any) -> str | None:
    if not isinstance(item, dict):
        return None
    code = item.get("code")
    return code if isinstance(code, str) else None
