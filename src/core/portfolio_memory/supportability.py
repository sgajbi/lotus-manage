"""Supportability-state mapping for portfolio memory event projection."""

from src.core.mandates import DpmMonitoringException
from src.core.pm_quality.models import (
    DpmPmQualityReviewAction,
    DpmPmQualitySummaryInvocation,
)
from src.core.portfolio_memory.models import (
    DpmPortfolioMemoryEvent,
    PortfolioMemorySupportabilityState,
)


def portfolio_memory_state(
    events: list[DpmPortfolioMemoryEvent],
) -> PortfolioMemorySupportabilityState:
    if not events:
        return "EMPTY"
    states = {event.supportability_state for event in events}
    for state in ("BLOCKED", "DEGRADED", "PENDING_REVIEW"):
        if state in states:
            return state
    return "READY"


def source_supportability_state(source_state: str | None) -> PortfolioMemorySupportabilityState:
    normalized = (source_state or "").upper()
    if _source_state_is_blocked(normalized):
        return "BLOCKED"
    if _source_state_is_degraded(normalized):
        return "DEGRADED"
    if _source_state_requires_review(normalized):
        return "PENDING_REVIEW"
    return "READY"


def _source_state_is_blocked(normalized_source_state: str) -> bool:
    return "BLOCK" in normalized_source_state or normalized_source_state in {
        "FAILED",
        "REJECTED",
        "CANCELLED",
    }


def _source_state_is_degraded(normalized_source_state: str) -> bool:
    return (
        "DEGRADED" in normalized_source_state
        or "BREACHED" in normalized_source_state
        or "PARTIAL" in normalized_source_state
    )


def _source_state_requires_review(normalized_source_state: str) -> bool:
    return "REVIEW" in normalized_source_state or normalized_source_state in {
        "CREATED",
        "DRAFT",
        "PREVIEWED",
        "CANDIDATE",
    }


def monitoring_exception_state(
    exception: DpmMonitoringException,
) -> PortfolioMemorySupportabilityState:
    if exception.state == "RESOLVED":
        return "READY"
    if exception.severity.value == "CRITICAL":
        return "BLOCKED"
    if exception.severity.value == "WARNING":
        return "DEGRADED"
    return "PENDING_REVIEW"


def pm_quality_review_action_state(
    action: DpmPmQualityReviewAction,
) -> PortfolioMemorySupportabilityState:
    if action.action_state == "ESCALATED":
        return "DEGRADED"
    if action.action_state == "REVIEW_REQUIRED":
        return "PENDING_REVIEW"
    return "READY"


def pm_quality_summary_invocation_state(
    invocation: DpmPmQualitySummaryInvocation,
) -> PortfolioMemorySupportabilityState:
    if invocation.invocation_state == "COMPLETED":
        return "READY"
    if invocation.invocation_state == "FAILED":
        return "DEGRADED"
    return "PENDING_REVIEW"


def assignment_sla_state(sla_posture: str) -> PortfolioMemorySupportabilityState:
    if sla_posture == "BREACHED_OR_BLOCKED":
        return "DEGRADED"
    return "READY"


def assignment_task_state(
    status: str,
    sla_posture: str,
) -> PortfolioMemorySupportabilityState:
    if status == "CANCELLED":
        return "BLOCKED"
    if status == "BLOCKED" or sla_posture == "BREACHED_OR_BLOCKED":
        return "DEGRADED"
    if status in {"OPEN", "ACKNOWLEDGED", "IN_PROGRESS"}:
        return "PENDING_REVIEW"
    return "READY"


def maker_checker_state(control_outcome: str) -> PortfolioMemorySupportabilityState:
    if control_outcome == "FAILED":
        return "BLOCKED"
    if control_outcome == "EXCEPTION_OPEN":
        return "DEGRADED"
    if control_outcome == "PENDING":
        return "PENDING_REVIEW"
    return "READY"
