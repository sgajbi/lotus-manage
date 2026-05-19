from __future__ import annotations

import pytest

from src.api.routers.wave_portfolio_type_validation import (
    normalize_required_portfolio_type,
    normalize_required_portfolio_types,
)
from src.api.services import wave_service


def test_normalize_required_portfolio_type_strips_and_uppercases_value() -> None:
    assert (
        normalize_required_portfolio_type(
            " discretionary ",
            required_code="PORTFOLIO_TYPE_REQUIRED",
            required_message="Portfolio type is required.",
        )
        == "DISCRETIONARY"
    )


def test_normalize_required_portfolio_type_raises_domain_validation_error() -> None:
    with pytest.raises(wave_service.DpmWaveValidationError) as exc_info:
        normalize_required_portfolio_type(
            "   ",
            required_code="PORTFOLIO_TYPE_REQUIRED",
            required_message="Portfolio type is required.",
        )

    assert exc_info.value.code == "PORTFOLIO_TYPE_REQUIRED"
    assert exc_info.value.message == "Portfolio type is required."


def test_normalize_required_portfolio_types_strips_and_uppercases_values() -> None:
    assert normalize_required_portfolio_types(
        [" discretionary ", "", "advisory"],
        required_code="PORTFOLIO_TYPES_REQUIRED",
        required_message="Portfolio types are required.",
    ) == ["DISCRETIONARY", "ADVISORY"]


def test_normalize_required_portfolio_types_raises_domain_validation_error() -> None:
    with pytest.raises(wave_service.DpmWaveValidationError) as exc_info:
        normalize_required_portfolio_types(
            ["", "   "],
            required_code="PORTFOLIO_TYPES_REQUIRED",
            required_message="Portfolio types are required.",
        )

    assert exc_info.value.code == "PORTFOLIO_TYPES_REQUIRED"
    assert exc_info.value.message == "Portfolio types are required."
