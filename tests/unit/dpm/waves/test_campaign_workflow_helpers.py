from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.core.waves.campaign_actor_entitlements import (
    validate_campaign_command_actor_entitlement,
)
from src.core.waves.campaign_page_validation import (
    validate_count_map_covers,
    validate_total_count,
)


def test_campaign_actor_entitlement_requires_actor_when_governed() -> None:
    definition = SimpleNamespace(
        governance=SimpleNamespace(entitled_actor_ids=["pm_001"]),
    )

    with pytest.raises(
        ValueError,
        match="BULK_REVIEW_CAMPAIGN_ACTOR_REQUIRED_FOR_ENTITLEMENT",
    ):
        validate_campaign_command_actor_entitlement(
            definition=definition,
            actor_id="  ",
        )


def test_campaign_count_map_covers_rejects_negative_counts() -> None:
    with pytest.raises(ValueError, match="workflow_counts values must be non-negative"):
        validate_count_map_covers(
            counts={"OPEN": -1},
            observed_values=["OPEN"],
            field_name="workflow_counts",
        )


@pytest.mark.parametrize(
    ("total_count", "count", "offset", "message"),
    [
        (-1, 0, 0, "total_count must be non-negative"),
        (2, 3, 0, "total_count must be greater than or equal to count"),
        (5, 2, 4, "total_count must cover the returned page window"),
    ],
)
def test_campaign_total_count_validation_rejects_inconsistent_page_metadata(
    total_count: int,
    count: int,
    offset: int,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        validate_total_count(total_count=total_count, count=count, offset=offset)
