import pytest

from src.api.services.construction_source_product_status import source_status_to_method_status
from src.core.construction.vocabulary import ConstructionMethodStatus


@pytest.mark.parametrize(
    ("source_status", "expected_status"),
    [
        ("READY", ConstructionMethodStatus.READY),
        ("DEGRADED", ConstructionMethodStatus.DEGRADED),
        ("UNAVAILABLE", ConstructionMethodStatus.BLOCKED),
        ("INCOMPLETE", ConstructionMethodStatus.BLOCKED),
        ("UNKNOWN_UPSTREAM_STATE", ConstructionMethodStatus.BLOCKED),
    ],
)
def test_source_status_to_method_status_maps_non_ready_fail_closed(
    source_status: str,
    expected_status: ConstructionMethodStatus,
) -> None:
    assert source_status_to_method_status(source_status) == expected_status
