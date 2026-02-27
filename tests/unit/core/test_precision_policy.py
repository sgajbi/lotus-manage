from decimal import Decimal

import pytest

from src.core import precision_policy as policy


def test_to_decimal_handles_none_decimal_and_invalid_values() -> None:
    assert policy.to_decimal(None) == Decimal("0")
    assert policy.to_decimal(Decimal("1.25")) == Decimal("1.25")
    assert policy.to_decimal("2.5") == Decimal("2.5")

    with pytest.raises(ValueError, match="Invalid numeric value"):
        policy.to_decimal(object())


def test_normalize_input_validates_supported_semantics_and_scale() -> None:
    assert policy.normalize_input("1.23456789", "money") == Decimal("1.23456789")

    with pytest.raises(ValueError, match="Unsupported semantic type"):
        policy.normalize_input("1.0", "unknown")

    with pytest.raises(ValueError, match="exceeds max"):
        policy.normalize_input("1.234567891", "money")


@pytest.mark.parametrize(
    ("fn", "value", "expected"),
    [
        (policy.quantize_money, "1.235", Decimal("1.24")),
        (policy.quantize_money, "1.225", Decimal("1.22")),
        (policy.quantize_quantity, "1.23456789", Decimal("1.234568")),
        (policy.quantize_price, "123.4567896", Decimal("123.456790")),
        (policy.quantize_fx_rate, "1.123456789", Decimal("1.12345679")),
        (policy.quantize_performance, "0.1234567", Decimal("0.123457")),
        (policy.quantize_risk, "0.9876544", Decimal("0.987654")),
    ],
)
def test_quantize_functions_apply_platform_rounding_policy(
    fn, value: str, expected: Decimal
) -> None:
    assert fn(value) == expected
