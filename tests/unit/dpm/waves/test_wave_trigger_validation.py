from src.api.services.wave_trigger_validation import (
    SUPPORTED_CREATE_TRIGGER_TYPES,
    trigger_validation_failure,
)


def test_trigger_validation_accepts_supported_trigger_with_portfolios() -> None:
    assert (
        trigger_validation_failure(
            "EXPLICIT_PORTFOLIO_LIST",
            portfolios=[{"portfolio_id": "PB_SG_TRIGGER"}],
        )
        is None
    )


def test_trigger_validation_rejects_unsupported_trigger() -> None:
    assert trigger_validation_failure("UNSUPPORTED_TRIGGER", portfolios=[{}]) == (
        "NOT_SUPPORTED_TRIGGER",
        "Trigger type UNSUPPORTED_TRIGGER is not supported for RFC-0041 Slice 4.",
    )


def test_trigger_validation_rejects_empty_portfolio_set() -> None:
    assert trigger_validation_failure("PM_BOOK_REVIEW", portfolios=[]) == (
        "AFFECTED_PORTFOLIO_SET_EMPTY",
        "Trigger type PM_BOOK_REVIEW requires at least one source-backed portfolio.",
    )


def test_supported_trigger_set_stays_private_banking_specific() -> None:
    assert SUPPORTED_CREATE_TRIGGER_TYPES == {
        "EXPLICIT_PORTFOLIO_LIST",
        "PM_BOOK_REVIEW",
        "CIO_MODEL_CHANGE",
        "TACTICAL_HOUSE_VIEW",
        "RISK_EVENT",
        "BULK_REVIEW_CAMPAIGN",
    }


def test_wave_trigger_validation_exports_only_trigger_contract() -> None:
    from src.api.services import wave_trigger_validation

    assert wave_trigger_validation.__all__ == [
        "SUPPORTED_CREATE_TRIGGER_TYPES",
        "UNSUPPORTED_SOURCE_OWNER_TRIGGER_TYPES",
        "trigger_validation_failure",
    ]
