from __future__ import annotations

from typing import Iterable


def validate_page_count(*, count: int, item_count: int, field_name: str = "count") -> None:
    """Validate that a page count reflects the returned rows."""

    if count != item_count:
        raise ValueError(f"{field_name} must equal the returned item count")


def validate_count_map(
    *,
    counts: dict[str, int],
    observed_values: Iterable[str],
    field_name: str,
) -> None:
    """Validate that a page count map exactly summarizes the returned rows."""

    expected: dict[str, int] = {}
    for value in observed_values:
        expected[value] = expected.get(value, 0) + 1
    if any(count < 0 for count in counts.values()):
        raise ValueError(f"{field_name} values must be non-negative")
    if counts != expected:
        raise ValueError(f"{field_name} must match the returned page items")
