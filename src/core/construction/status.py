from collections.abc import Iterable

from src.core.construction.vocabulary import ConstructionMethodStatus

CONSTRUCTION_STATUS_ORDER: dict[ConstructionMethodStatus, int] = {
    ConstructionMethodStatus.BLOCKED: 0,
    ConstructionMethodStatus.DEGRADED: 1,
    ConstructionMethodStatus.PENDING_REVIEW: 2,
    ConstructionMethodStatus.READY: 3,
}


def construction_status_rank(status: ConstructionMethodStatus) -> int:
    return CONSTRUCTION_STATUS_ORDER[status]


def lowest_construction_status(
    statuses: Iterable[ConstructionMethodStatus],
    *,
    default: ConstructionMethodStatus | None = None,
) -> ConstructionMethodStatus:
    status_list = list(statuses)
    if not status_list:
        if default is None:
            raise ValueError("lowest_construction_status() arg is an empty sequence")
        return default
    return min(status_list, key=construction_status_rank)


__all__ = [
    "CONSTRUCTION_STATUS_ORDER",
    "construction_status_rank",
    "lowest_construction_status",
]
