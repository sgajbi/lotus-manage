from src.core.common.canonical import hash_canonical_payload
from src.core.construction.models import AuthoritativeExecutionAcknowledgementContext
from src.core.construction.vocabulary import ConstructionMethodStatus
from src.core.dpm_source_context import DpmCoreExternalOrderExecutionAcknowledgementResponse


def external_order_execution_acknowledgement_context(
    acknowledgement: DpmCoreExternalOrderExecutionAcknowledgementResponse | None,
) -> AuthoritativeExecutionAcknowledgementContext | None:
    if acknowledgement is None:
        return None
    payload = acknowledgement.model_dump(mode="json", exclude_none=True)
    source_hash = hash_canonical_payload(payload)
    return AuthoritativeExecutionAcknowledgementContext(
        supportability_status=source_status_to_method_status(acknowledgement.supportability.state),
        source_system="lotus-core",
        source_product_name=acknowledgement.product_name,
        source_product_version=acknowledgement.product_version,
        source_id=(
            acknowledgement.source_batch_fingerprint
            or acknowledgement.lineage.get("source_batch_fingerprint")
            or source_hash
        ),
        content_hash=source_hash,
        acknowledgement_count=acknowledgement.supportability.acknowledgement_count,
        missing_data_families=acknowledgement.supportability.missing_data_families,
        blocked_capabilities=acknowledgement.supportability.blocked_capabilities,
        acknowledgements=acknowledgement.acknowledgements,
        reason_codes=[
            acknowledgement.supportability.reason,
            "EXTERNAL_ORDER_EXECUTION_ACKNOWLEDGEMENT_FAIL_CLOSED",
        ],
    )


def source_status_to_method_status(status: str) -> ConstructionMethodStatus:
    if status == "READY":
        return ConstructionMethodStatus.READY
    if status == "DEGRADED":
        return ConstructionMethodStatus.DEGRADED
    return ConstructionMethodStatus.BLOCKED


__all__ = [
    "external_order_execution_acknowledgement_context",
    "source_status_to_method_status",
]
