import hashlib
import json

from src.core.common.boundary_promotion import (
    CLIENT_COMMUNICATION_PROMOTION_REQUIREMENTS,
    EXTERNAL_EXECUTION_PROMOTION_REQUIREMENTS,
)
from src.core.waves import (
    DpmWaveClientCommunicationBoundaryEvidence,
    DpmWaveExternalExecutionBoundaryEvidence,
)


def external_execution_boundary(
    *, external_execution_claimed: bool
) -> DpmWaveExternalExecutionBoundaryEvidence:
    payload: dict[str, object] = {
        "boundary_id": "DPM_WAVE_EXTERNAL_EXECUTION_BOUNDARY",
        "supportability_state": "BLOCKED",
        "source_system": "lotus-manage",
        "source_product_name": "DpmWaveInternalOperationsHandoff",
        "source_product_version": "v1",
        "external_execution_claimed": external_execution_claimed,
        "reason_code": "UNSAFE_EXTERNAL_EXECUTION_CLAIM"
        if external_execution_claimed
        else "NO_EXTERNAL_EXECUTION_OWNER",
        "blocked_capabilities": [
            "order_generation",
            "venue_routing",
            "best_execution",
            "oms_acknowledgement",
            "fills",
            "settlement",
            "execution_status_certification",
        ],
        "required_owner": "future execution/OMS owner",
        "required_source_product": "ExternalOrderExecutionAcknowledgement:v1",
        "promotion_requirements": list(EXTERNAL_EXECUTION_PROMOTION_REQUIREMENTS),
        "summary": (
            "Persisted handoff evidence contains an unsafe external execution claim; downstream "
            "report input must remain blocked."
            if external_execution_claimed
            else "Manage wave evidence stops at internal operations handoff until a governed "
            "execution/OMS owner and certified acknowledgement source product exist."
        ),
    }
    payload["content_hash"] = boundary_content_hash(payload)
    return DpmWaveExternalExecutionBoundaryEvidence.model_validate(payload)


def client_communication_boundary() -> DpmWaveClientCommunicationBoundaryEvidence:
    payload: dict[str, object] = {
        "boundary_id": "DPM_WAVE_CLIENT_COMMUNICATION_BOUNDARY",
        "supportability_state": "BLOCKED",
        "source_system": "lotus-manage",
        "source_product_name": "DpmWaveInternalOperationsHandoff",
        "source_product_version": "v1",
        "client_communication_projected": False,
        "client_approval_projected": False,
        "reason_code": "WAVE_CLIENT_COMMUNICATION_NOT_SUPPORTED",
        "blocked_capabilities": [
            "client_contact",
            "client_message_generation",
            "client_approval",
            "delivery_confirmation",
            "communication_audit",
        ],
        "required_owner": "future client-communication owner",
        "required_source_product": "ClientCommunicationRecord:v1",
        "promotion_requirements": list(CLIENT_COMMUNICATION_PROMOTION_REQUIREMENTS),
        "summary": (
            "Manage wave evidence stops at internal operations handoff; it does not project "
            "client communication, client approval, delivery confirmation, or communication "
            "audit truth until a governed client-communication owner and certified source "
            "product exist."
        ),
    }
    payload["content_hash"] = boundary_content_hash(payload)
    return DpmWaveClientCommunicationBoundaryEvidence.model_validate(payload)


def boundary_content_hash(payload: dict[str, object]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return f"sha256:{hashlib.sha256(canonical.encode()).hexdigest()}"


__all__ = [
    "boundary_content_hash",
    "client_communication_boundary",
    "external_execution_boundary",
]
