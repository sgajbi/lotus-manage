from src.api.services.construction_execution_source_context import (
    external_order_execution_acknowledgement_context,
)
from src.core.construction.vocabulary import ConstructionMethodStatus
from tests.unit.dpm.construction.source_product_context_fixtures import (
    external_order_acknowledgement_response,
)


def test_external_order_acknowledgement_context_is_fail_closed_source_evidence() -> None:
    context = external_order_execution_acknowledgement_context(
        external_order_acknowledgement_response()
    )

    assert context is not None
    assert context.supportability_status == ConstructionMethodStatus.BLOCKED
    assert context.source_system == "lotus-core"
    assert context.source_product_name == "ExternalOrderExecutionAcknowledgement"
    assert context.source_id == "core-ack-fingerprint"
    assert context.acknowledgement_count == 0
    assert context.blocked_capabilities == ["execution", "fill", "settlement"]
    assert context.reason_codes == [
        "EXTERNAL_OMS_SOURCE_NOT_INGESTED",
        "EXTERNAL_ORDER_EXECUTION_ACKNOWLEDGEMENT_FAIL_CLOSED",
    ]


def test_external_order_acknowledgement_context_absent_without_source_response() -> None:
    assert external_order_execution_acknowledgement_context(None) is None
