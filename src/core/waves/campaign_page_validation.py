from __future__ import annotations

from typing import Iterable


def page_items[T](items: list[T], *, limit: int, offset: int) -> list[T]:
    """Return a stable page window after read-model filtering and classification."""

    return items[offset : offset + limit]


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


def validate_count_map_covers(
    *,
    counts: dict[str, int],
    observed_values: Iterable[str],
    field_name: str,
) -> None:
    """Validate that an aggregate count map covers every returned row."""

    observed: dict[str, int] = {}
    for value in observed_values:
        observed[value] = observed.get(value, 0) + 1
    if any(count < 0 for count in counts.values()):
        raise ValueError(f"{field_name} values must be non-negative")
    for key, observed_count in observed.items():
        if counts.get(key, 0) < observed_count:
            raise ValueError(f"{field_name} must cover the returned page items")


def validate_total_count(
    *,
    total_count: int,
    count: int,
    offset: int,
    field_name: str = "total_count",
) -> None:
    """Validate that total count can support the returned page metadata."""

    if total_count < 0:
        raise ValueError(f"{field_name} must be non-negative")
    if count > total_count:
        raise ValueError(f"{field_name} must be greater than or equal to count")
    if count > 0 and offset + count > total_count:
        raise ValueError(f"{field_name} must cover the returned page window")
