import pytest

from src.core.construction.status import construction_status_rank, lowest_construction_status
from src.core.construction.vocabulary import ConstructionMethodStatus


def test_lowest_construction_status_uses_conservative_ordering() -> None:
    assert (
        lowest_construction_status(
            [
                ConstructionMethodStatus.READY,
                ConstructionMethodStatus.PENDING_REVIEW,
                ConstructionMethodStatus.DEGRADED,
            ]
        )
        == ConstructionMethodStatus.DEGRADED
    )
    assert construction_status_rank(ConstructionMethodStatus.BLOCKED) < construction_status_rank(
        ConstructionMethodStatus.DEGRADED
    )


def test_lowest_construction_status_honors_default_for_empty_inputs() -> None:
    assert (
        lowest_construction_status([], default=ConstructionMethodStatus.BLOCKED)
        == ConstructionMethodStatus.BLOCKED
    )

    with pytest.raises(ValueError, match="empty sequence"):
        lowest_construction_status([])
