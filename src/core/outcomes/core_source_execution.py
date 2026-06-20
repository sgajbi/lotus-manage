"""lotus-core external execution acknowledgement outcome adapter."""

from decimal import Decimal
from typing import Any, Literal, TypedDict

from src.core.outcomes.core_source_common import (
    _CoreSourceMetadata,
    _core_metadata,
    _prefixed_reason_codes,
    _read_int,
    _read_mapping,
    _read_required_text,
    _read_text,
    _read_text_list,
    _source_id,
)
from src.core.outcomes.models import DpmRealizedSourceSnapshot


class _ExecutionAcknowledgementPosture(TypedDict):
    acknowledgement_count: int
    supportability_state: str
    supportability_reason: str
    execution_intent_id: str
    order_reference_ids: list[str]
    missing_data_families: list[str]
    blocked_capabilities: list[str]


def realized_execution_acknowledgement_source_from_response(
    response: dict[str, Any],
) -> DpmRealizedSourceSnapshot:
    """Adapt lotus-core OMS acknowledgement posture without claiming execution support."""

    metadata = _core_metadata(response)
    portfolio_id = _read_required_text(response.get("portfolio_id"), "portfolio_id")
    posture = _execution_acknowledgement_posture(response, metadata=metadata)
    source_state, quality = _execution_acknowledgement_state_quality(
        posture["supportability_state"]
    )
    return DpmRealizedSourceSnapshot(
        dimension="EXECUTION_QUALITY",
        source_system="lotus-core",
        source_type="EXTERNAL_ORDER_EXECUTION_ACKNOWLEDGEMENT",
        source_id=_execution_acknowledgement_source_id(
            metadata=metadata,
            portfolio_id=portfolio_id,
            posture=posture,
        ),
        value=Decimal(posture["acknowledgement_count"]),
        unit="acknowledgements",
        source_state=source_state,
        quality=quality,
        observed_at=metadata["observed_at"],
        as_of_date=metadata["as_of_date"],
        content_hash=metadata["content_hash"],
        reason_codes=_execution_acknowledgement_reason_codes(
            metadata=metadata,
            posture=posture,
        ),
    )


def _execution_acknowledgement_posture(
    response: dict[str, Any],
    *,
    metadata: _CoreSourceMetadata,
) -> _ExecutionAcknowledgementPosture:
    supportability = _read_mapping(response.get("supportability"))
    return {
        "acknowledgement_count": _read_int(
            supportability.get("acknowledgement_count"),
            "supportability.acknowledgement_count",
        ),
        "supportability_state": (
            _read_text(supportability.get("state")) or metadata["data_quality_status"]
        ).upper(),
        "supportability_reason": (
            _read_text(supportability.get("reason")) or "EXTERNAL_OMS_ACKNOWLEDGEMENT_UNAVAILABLE"
        ),
        "execution_intent_id": _read_text(response.get("execution_intent_id")) or "none",
        "order_reference_ids": _read_text_list(response.get("order_reference_ids")),
        "missing_data_families": _read_text_list(supportability.get("missing_data_families")),
        "blocked_capabilities": _read_text_list(supportability.get("blocked_capabilities")),
    }


def _execution_acknowledgement_source_id(
    *,
    metadata: _CoreSourceMetadata,
    portfolio_id: str,
    posture: _ExecutionAcknowledgementPosture,
) -> str:
    order_basis = (
        ",".join(posture["order_reference_ids"]) if posture["order_reference_ids"] else "none"
    )
    return _source_id(
        product_name=metadata["product_name"],
        product_version=metadata["product_version"],
        portfolio_id=portfolio_id,
        as_of_date=metadata["as_of_date"],
        basis=(
            "external_order_execution_acknowledgement:"
            f"execution_intent={posture['execution_intent_id']}:orders={order_basis}"
        ),
        fingerprint=metadata["content_hash"],
    )


def _execution_acknowledgement_state_quality(
    supportability_state: str,
) -> tuple[Literal["BLOCKED", "DEGRADED"], Literal["MISSING", "UNAVAILABLE"]]:
    if supportability_state == "UNAVAILABLE":
        return "BLOCKED", "MISSING"
    return "DEGRADED", "UNAVAILABLE"


def _execution_acknowledgement_reason_codes(
    *,
    metadata: _CoreSourceMetadata,
    posture: _ExecutionAcknowledgementPosture,
) -> list[str]:
    return [
        "CORE_EXECUTION_ACKNOWLEDGEMENT_FAIL_CLOSED",
        f"CORE_PRODUCT_{metadata['product_name'].upper()}",
        f"CORE_PRODUCT_VERSION_{metadata['product_version'].upper()}",
        f"EXECUTION_ACKNOWLEDGEMENT_SUPPORTABILITY_{posture['supportability_state']}",
        posture["supportability_reason"],
        f"EXECUTION_ACKNOWLEDGEMENT_COUNT_{posture['acknowledgement_count']}",
        *_prefixed_reason_codes(
            "EXECUTION_ACKNOWLEDGEMENT_MISSING_DATA",
            posture["missing_data_families"],
        ),
        *_prefixed_reason_codes(
            "EXECUTION_ACKNOWLEDGEMENT_BLOCKED_CAPABILITY",
            posture["blocked_capabilities"],
        ),
        f"CORE_DATA_QUALITY_{metadata['data_quality_status'].upper()}",
    ]
