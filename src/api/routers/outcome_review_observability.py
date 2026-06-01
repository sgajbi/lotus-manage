OUTCOME_CREATE_SURFACE = "rebalance/outcome-reviews/create"
OUTCOME_REFRESH_SURFACE = "rebalance/outcome-reviews/refresh-sources"
OUTCOME_SUPPORTABILITY_SURFACE = "rebalance/outcome-reviews/supportability"


def outcome_review_metric_state(state: str) -> str:
    return state.lower()


def outcome_review_metric_reason(state: str) -> str:
    return {
        "READY": "outcome_review_ready",
        "PENDING_REVIEW": "outcome_review_pending_review",
        "BREACHED": "outcome_review_breached",
        "DEGRADED": "outcome_review_degraded",
        "BLOCKED": "outcome_review_blocked",
        "NOT_SUPPORTED": "outcome_review_not_supported",
    }.get(state, "outcome_review_error")
