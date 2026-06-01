from src.api.services.construction_source_product_status import source_status_to_method_status
from src.core.construction.vocabulary import ConstructionMethodStatus


def test_source_status_to_method_status_maps_non_ready_fail_closed() -> None:
    assert source_status_to_method_status("READY") == ConstructionMethodStatus.READY
    assert source_status_to_method_status("DEGRADED") == ConstructionMethodStatus.DEGRADED
    assert source_status_to_method_status("UNAVAILABLE") == ConstructionMethodStatus.BLOCKED
    assert source_status_to_method_status("INCOMPLETE") == ConstructionMethodStatus.BLOCKED
