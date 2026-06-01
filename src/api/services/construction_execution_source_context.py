from src.api.services.construction_source_product_status import source_status_to_method_status
from src.api.services.construction_source_identity import (
    response_source_id,
    source_hash,
    source_payload,
)
from src.core.construction.models import AuthoritativeExecutionAcknowledgementContext
from src.core.dpm_source_context import DpmCoreExternalOrderExecutionAcknowledgementResponse


def external_order_execution_acknowledgement_context(
    acknowledgement: DpmCoreExternalOrderExecutionAcknowledgementResponse | None,
) -> AuthoritativeExecutionAcknowledgementContext | None:
    if acknowledgement is None:
        return None
    payload = source_payload(acknowledgement)
    source_hash_value = source_hash(payload)
    return AuthoritativeExecutionAcknowledgementContext(
        supportability_status=source_status_to_method_status(acknowledgement.supportability.state),
        source_system="lotus-core",
        source_product_name=acknowledgement.product_name,
        source_product_version=acknowledgement.product_version,
        source_id=response_source_id(acknowledgement, source_hash_value),
        content_hash=source_hash_value,
        acknowledgement_count=acknowledgement.supportability.acknowledgement_count,
        missing_data_families=acknowledgement.supportability.missing_data_families,
        blocked_capabilities=acknowledgement.supportability.blocked_capabilities,
        acknowledgements=acknowledgement.acknowledgements,
        reason_codes=[
            acknowledgement.supportability.reason,
            "EXTERNAL_ORDER_EXECUTION_ACKNOWLEDGEMENT_FAIL_CLOSED",
        ],
    )


__all__ = ["external_order_execution_acknowledgement_context"]
