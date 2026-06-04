from src.api.services.construction_source_product_status import source_status_to_method_status
from src.api.services.construction_source_identity import source_product_identity
from src.core.construction.models import AuthoritativeExecutionAcknowledgementContext
from src.core.dpm_source_context import DpmCoreExternalOrderExecutionAcknowledgementResponse

_EXTERNAL_ORDER_EXECUTION_ACKNOWLEDGEMENT_FAIL_CLOSED_REASON = (
    "EXTERNAL_ORDER_EXECUTION_ACKNOWLEDGEMENT_FAIL_CLOSED"
)


def external_order_acknowledgement_reason_codes(
    acknowledgement: DpmCoreExternalOrderExecutionAcknowledgementResponse,
) -> list[str]:
    return [
        acknowledgement.supportability.reason,
        _EXTERNAL_ORDER_EXECUTION_ACKNOWLEDGEMENT_FAIL_CLOSED_REASON,
    ]


def external_order_execution_acknowledgement_context(
    acknowledgement: DpmCoreExternalOrderExecutionAcknowledgementResponse | None,
) -> AuthoritativeExecutionAcknowledgementContext | None:
    if acknowledgement is None:
        return None
    identity = source_product_identity(acknowledgement)
    return AuthoritativeExecutionAcknowledgementContext(
        supportability_status=source_status_to_method_status(acknowledgement.supportability.state),
        source_system=identity.source_system,
        source_product_name=identity.source_product_name,
        source_product_version=identity.source_product_version,
        source_id=identity.source_id,
        content_hash=identity.content_hash,
        acknowledgement_count=acknowledgement.supportability.acknowledgement_count,
        missing_data_families=acknowledgement.supportability.missing_data_families,
        blocked_capabilities=acknowledgement.supportability.blocked_capabilities,
        acknowledgements=acknowledgement.acknowledgements,
        reason_codes=external_order_acknowledgement_reason_codes(acknowledgement),
    )


__all__ = [
    "external_order_acknowledgement_reason_codes",
    "external_order_execution_acknowledgement_context",
]
