"""External execution boundary evidence for RFC-0042 outcome reviews."""

from __future__ import annotations

from src.core.common.canonical import hash_canonical_payload
from src.core.outcomes.models import (
    DpmOutcomeExternalExecutionBoundaryEvidence,
    DpmPostTradeOutcomeReview,
)


def build_outcome_external_execution_boundary(
    review: DpmPostTradeOutcomeReview,
) -> DpmOutcomeExternalExecutionBoundaryEvidence:
    """Build fail-closed external execution evidence from persisted review truth."""

    execution_quality = next(
        (result for result in review.dimension_results if result.dimension == "EXECUTION_QUALITY"),
        None,
    )
    realized_execution_value = review.realized_snapshot.realized_values.get("EXECUTION_QUALITY")
    reason_codes = sorted(
        {
            reason
            for result in review.dimension_results
            for reason in [
                result.reason_code,
                *result.supportability.reason_codes,
                *(ref.source_type for ref in result.source_refs),
            ]
        }
        | set(review.supportability.reason_codes)
        | (
            set(realized_execution_value.supportability.reason_codes)
            if realized_execution_value is not None
            else set()
        )
    )
    source_product_present = any(
        ref.source_type == "EXTERNAL_ORDER_EXECUTION_ACKNOWLEDGEMENT"
        for ref in [
            *review.source_lineage,
            *(ref for result in review.dimension_results for ref in result.source_refs),
            *(realized_execution_value.source_refs if realized_execution_value is not None else []),
        ]
    )
    payload = {
        "boundary_id": "DPM_OUTCOME_EXTERNAL_EXECUTION_BOUNDARY",
        "supportability_state": "BLOCKED",
        "source_system": "lotus-manage",
        "source_product_name": "DpmPostTradeOutcomeReview",
        "source_product_version": "v1",
        "source_product_present": source_product_present,
        "execution_quality_dimension_state": execution_quality.state if execution_quality else None,
        "execution_acknowledgement_count_projected": _execution_acknowledgement_count(reason_codes),
        "reason_code": (
            "OUTCOME_EXTERNAL_EXECUTION_EVIDENCE_NOT_CERTIFIED"
            if source_product_present
            else "OUTCOME_EXTERNAL_EXECUTION_SOURCE_PRODUCT_NOT_PRESENT"
        ),
        "blocked_capabilities": _blocked_execution_capabilities(reason_codes),
        "required_owner": "future execution/OMS owner",
        "required_source_product": "ExternalOrderExecutionAcknowledgement:v1",
        "summary": (
            "Outcome review may preserve fail-closed Core acknowledgement posture, but Manage does "
            "not certify best execution, route orders, project fills or settlement, reconcile OMS "
            "status, or promote execution evidence until a bank-owned execution/OMS owner publishes "
            "certified acknowledgement source events."
        ),
    }
    payload["content_hash"] = hash_canonical_payload(payload)
    return DpmOutcomeExternalExecutionBoundaryEvidence.model_validate(payload)


def _blocked_execution_capabilities(reason_codes: list[str]) -> list[str]:
    capabilities = {
        reason.removeprefix("EXECUTION_ACKNOWLEDGEMENT_BLOCKED_CAPABILITY_").lower()
        for reason in reason_codes
        if reason.startswith("EXECUTION_ACKNOWLEDGEMENT_BLOCKED_CAPABILITY_")
    }
    if not capabilities:
        capabilities = {
            "best_execution",
            "oms_acknowledgement",
            "fills",
            "settlement",
            "execution_status_projection",
        }
    return sorted(capabilities)


def _execution_acknowledgement_count(reason_codes: list[str]) -> int | None:
    for reason in reason_codes:
        if reason.startswith("EXECUTION_ACKNOWLEDGEMENT_COUNT_"):
            value = reason.removeprefix("EXECUTION_ACKNOWLEDGEMENT_COUNT_")
            if value.isdigit():
                return int(value)
    return None
