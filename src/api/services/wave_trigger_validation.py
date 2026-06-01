SUPPORTED_CREATE_TRIGGER_TYPES = {
    "EXPLICIT_PORTFOLIO_LIST",
    "PM_BOOK_REVIEW",
    "CIO_MODEL_CHANGE",
    "TACTICAL_HOUSE_VIEW",
    "RISK_EVENT",
    "BULK_REVIEW_CAMPAIGN",
}

UNSUPPORTED_SOURCE_OWNER_TRIGGER_TYPES: dict[str, str] = {}


def trigger_validation_failure(
    trigger_type: str,
    *,
    portfolios: list[dict[str, object]],
) -> tuple[str, str] | None:
    if trigger_type not in SUPPORTED_CREATE_TRIGGER_TYPES:
        source_owner_reason = UNSUPPORTED_SOURCE_OWNER_TRIGGER_TYPES.get(trigger_type)
        if source_owner_reason is not None:
            return (
                "NOT_SUPPORTED_TRIGGER",
                f"Trigger type {trigger_type} is not supported. {source_owner_reason}",
            )
        return (
            "NOT_SUPPORTED_TRIGGER",
            f"Trigger type {trigger_type} is not supported for RFC-0041 Slice 4.",
        )
    if not portfolios:
        return (
            "AFFECTED_PORTFOLIO_SET_EMPTY",
            f"Trigger type {trigger_type} requires at least one source-backed portfolio.",
        )
    return None


__all__ = [
    "SUPPORTED_CREATE_TRIGGER_TYPES",
    "UNSUPPORTED_SOURCE_OWNER_TRIGGER_TYPES",
    "trigger_validation_failure",
]
