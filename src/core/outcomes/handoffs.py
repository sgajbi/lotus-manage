"""Report and AI handoff adapters for RFC-0042 outcome reviews."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from src.core.common.canonical import hash_canonical_payload, strip_keys
from src.core.portfolio_memory.handoffs import DpmPortfolioMemoryReportContext
from src.core.outcomes.execution_boundary import (
    build_outcome_client_communication_boundary,
    build_outcome_external_execution_boundary,
)
from src.core.outcomes.models import (
    DpmOutcomeClientCommunicationBoundaryEvidence,
    DpmOutcomeDimensionResult,
    DpmOutcomeExternalExecutionBoundaryEvidence,
    DpmOutcomeSourceRef,
    DpmOutcomeSupportability,
    DpmPostTradeOutcomeReview,
    OutcomeDimension,
    OutcomeDimensionState,
    OutcomeReviewState,
)

HANDOFF_CONTRACT_VERSION = "1.0"
OUTCOME_REPORT_INPUT_REF_TYPE = "DPM_OUTCOME_REPORT_INPUT"
OUTCOME_AI_EVIDENCE_REF_TYPE = "DPM_OUTCOME_AI_EVIDENCE_INPUT"
AI_FORBIDDEN_FIELD_NAMES = frozenset(
    {
        "account_number",
        "client_name",
        "client_id",
        "email",
        "phone",
        "raw_payload",
        "raw_request",
        "raw_response",
        "secret",
        "ssn",
        "token",
    }
)


class DpmOutcomeReportDimension(BaseModel):
    dimension: OutcomeDimension = Field(description="Outcome dimension.")
    state: OutcomeDimensionState = Field(description="Dimension supportability or outcome state.")
    reason_code: str = Field(description="Primary bounded reason code.")
    expected: str | None = Field(description="Expected value serialized for report consumers.")
    realized: str | None = Field(description="Realized value serialized for report consumers.")
    variance: str | None = Field(description="Realized minus expected variance when comparable.")
    explanation: str = Field(description="Operator-safe deterministic explanation.")
    source_refs: list[DpmOutcomeSourceRef] = Field(
        description="Source refs supporting the dimension."
    )
    supportability: DpmOutcomeSupportability = Field(
        description="Dimension supportability posture."
    )


class DpmOutcomeReportInput(BaseModel):
    contract_version: str = Field(description="Report-input contract version.")
    outcome_review_id: str = Field(description="Source outcome-review identifier.")
    outcome_review_content_hash: str = Field(description="Canonical source outcome-review hash.")
    portfolio_id: str = Field(description="Portfolio identifier.")
    mandate_id: str | None = Field(description="Mandate identifier when available.")
    rebalance_run_id: str | None = Field(description="Rebalance run identifier when available.")
    proof_pack_id: str = Field(description="Linked proof-pack identifier.")
    wave_id: str | None = Field(description="Linked rebalance-wave identifier when available.")
    review_window: dict[str, Any] = Field(description="Post-trade review window.")
    generated_at: str = Field(description="Deterministic handoff generation timestamp.")
    report_title: str = Field(description="Suggested report title.")
    report_audience: list[str] = Field(description="Intended report audiences.")
    state: OutcomeReviewState = Field(description="Overall outcome-review state.")
    overall_outcome: str = Field(description="Deterministic overall outcome summary.")
    variance_summary: dict[str, str | None] = Field(description="Variance by outcome dimension.")
    supportability: DpmOutcomeSupportability = Field(
        description="Outcome-review supportability posture."
    )
    dimensions: list[DpmOutcomeReportDimension] = Field(description="Report-safe dimension facts.")
    source_lineage: list[DpmOutcomeSourceRef] = Field(description="Source lineage for audit trace.")
    source_hashes: dict[str, str] = Field(description="Source hashes carried by the review.")
    section_hashes: dict[str, str] = Field(
        description="Proof-pack section hashes carried by the review."
    )
    external_execution_boundary: DpmOutcomeExternalExecutionBoundaryEvidence = Field(
        description=(
            "Fail-closed external execution/OMS boundary evidence carried for downstream report "
            "consumers without promoting acknowledgement, fill, settlement, or best-execution truth."
        )
    )
    client_communication_boundary: DpmOutcomeClientCommunicationBoundaryEvidence = Field(
        description=(
            "Fail-closed client communication boundary evidence carried for downstream report "
            "consumers without promoting client contact, message, approval, delivery, or audit truth."
        )
    )
    portfolio_memory_context: DpmPortfolioMemoryReportContext | None = Field(
        default=None,
        description=(
            "Optional Manage-owned portfolio-memory lineage context for downstream reports. "
            "This context carries its own content hash and is excluded from the outcome "
            "report-input evidence hash to avoid recursive report-input lineage."
        ),
    )
    redaction_policy: str = Field(description="Redaction policy applied to report input.")
    evidence_ref: DpmOutcomeSourceRef = Field(description="Evidence reference for this input.")
    content_hash: str = Field(description="Canonical report-input hash.")


class DpmOutcomeAiDimensionEvidence(BaseModel):
    dimension: OutcomeDimension = Field(description="Outcome dimension.")
    state: OutcomeDimensionState = Field(description="Dimension state.")
    reason_code: str = Field(description="Bounded reason code.")
    expected: str | None = Field(description="Expected value serialized for AI evidence.")
    realized: str | None = Field(description="Realized value serialized for AI evidence.")
    variance: str | None = Field(description="Variance serialized for AI evidence.")
    explanation: str = Field(description="Operator-safe deterministic explanation.")


class DpmOutcomeAiEvidenceInput(BaseModel):
    contract_version: str = Field(description="AI-evidence input contract version.")
    outcome_review_id: str = Field(description="Source outcome-review identifier.")
    outcome_review_content_hash: str = Field(description="Canonical source outcome-review hash.")
    portfolio_id: str = Field(description="Portfolio identifier.")
    mandate_id: str | None = Field(description="Mandate identifier when available.")
    rebalance_run_id: str | None = Field(description="Rebalance run identifier when available.")
    proof_pack_id: str = Field(description="Linked proof-pack identifier.")
    wave_id: str | None = Field(description="Linked rebalance-wave identifier when available.")
    review_window: dict[str, Any] = Field(description="Post-trade review window.")
    generated_at: str = Field(description="Deterministic handoff generation timestamp.")
    permitted_use: str = Field(description="Permitted AI use for this evidence.")
    forbidden_actions: list[str] = Field(description="Actions the AI layer must not perform.")
    forbidden_fields_removed: list[str] = Field(description="Forbidden field names removed.")
    state: OutcomeReviewState = Field(description="Overall outcome-review state.")
    overall_outcome: str = Field(description="Deterministic overall outcome summary.")
    reason_codes: list[str] = Field(description="Aggregate outcome-review reason codes.")
    dimensions: list[DpmOutcomeAiDimensionEvidence] = Field(
        description="AI-safe dimension evidence."
    )
    source_refs: list[DpmOutcomeSourceRef] = Field(description="AI-safe source references.")
    external_execution_boundary: DpmOutcomeExternalExecutionBoundaryEvidence = Field(
        description=(
            "Fail-closed external execution/OMS boundary evidence carried for downstream AI "
            "consumers without permitting order, fill, settlement, or best-execution claims."
        )
    )
    client_communication_boundary: DpmOutcomeClientCommunicationBoundaryEvidence = Field(
        description=(
            "Fail-closed client communication boundary evidence carried for downstream AI "
            "consumers without permitting client contact, message generation, approval, delivery, "
            "or communication-audit claims."
        )
    )
    evidence_ref: DpmOutcomeSourceRef = Field(description="Evidence reference for this input.")
    content_hash: str = Field(description="Canonical AI-evidence input hash.")


def build_report_input(
    review: DpmPostTradeOutcomeReview,
    *,
    portfolio_memory_context: DpmPortfolioMemoryReportContext | None = None,
) -> DpmOutcomeReportInput:
    payload = DpmOutcomeReportInput(
        contract_version=HANDOFF_CONTRACT_VERSION,
        outcome_review_id=review.outcome_review_id,
        outcome_review_content_hash=review.content_hash,
        portfolio_id=review.portfolio_id,
        mandate_id=review.mandate_id,
        rebalance_run_id=review.rebalance_run_id,
        proof_pack_id=review.proof_pack_id,
        wave_id=review.wave_id,
        review_window=review.review_window.model_dump(mode="json"),
        generated_at=review.created_at.isoformat(),
        report_title=f"Post-Trade Outcome Review - {review.portfolio_id}",
        report_audience=[
            "portfolio_manager",
            "cio_office",
            "investment_control",
            "operations",
            "audit",
        ],
        state=review.state,
        overall_outcome=review.overall_outcome,
        variance_summary=_stringify_variance_summary(review),
        supportability=review.supportability,
        dimensions=[_report_dimension(result) for result in review.dimension_results],
        source_lineage=review.source_lineage,
        source_hashes=review.source_hashes,
        section_hashes=review.section_hashes,
        external_execution_boundary=build_outcome_external_execution_boundary(review),
        client_communication_boundary=build_outcome_client_communication_boundary(review),
        portfolio_memory_context=portfolio_memory_context,
        redaction_policy="NO_RAW_PAYLOADS",
        evidence_ref=_handoff_ref(
            ref_type=OUTCOME_REPORT_INPUT_REF_TYPE,
            outcome_review_id=review.outcome_review_id,
        ),
        content_hash="",
    ).model_dump(mode="json")
    payload["content_hash"] = hash_canonical_payload(
        strip_keys(payload, exclude={"content_hash", "portfolio_memory_context"})
    )
    payload["evidence_ref"]["content_hash"] = payload["content_hash"]
    return DpmOutcomeReportInput.model_validate(payload)


def build_ai_evidence_input(review: DpmPostTradeOutcomeReview) -> DpmOutcomeAiEvidenceInput:
    removed: set[str] = set()
    review_window = _sanitize_for_ai(review.review_window.model_dump(mode="json"), removed)
    dimensions = [
        _ai_dimension(_sanitize_for_ai(result.model_dump(mode="json"), removed))
        for result in review.dimension_results
    ]
    payload = DpmOutcomeAiEvidenceInput(
        contract_version=HANDOFF_CONTRACT_VERSION,
        outcome_review_id=review.outcome_review_id,
        outcome_review_content_hash=review.content_hash,
        portfolio_id=review.portfolio_id,
        mandate_id=review.mandate_id,
        rebalance_run_id=review.rebalance_run_id,
        proof_pack_id=review.proof_pack_id,
        wave_id=review.wave_id,
        review_window=review_window,
        generated_at=review.created_at.isoformat(),
        permitted_use="Draft support-only PM, CIO, compliance, and operations narratives from evidence.",
        forbidden_actions=[
            "place_orders",
            "approve_rebalance",
            "override_controls",
            "invent_missing_evidence",
            "score_portfolio_manager",
            "contact_client",
        ],
        forbidden_fields_removed=sorted(removed),
        state=review.state,
        overall_outcome=review.overall_outcome,
        reason_codes=review.supportability.reason_codes,
        dimensions=dimensions,
        source_refs=_dedupe_source_refs(review),
        external_execution_boundary=build_outcome_external_execution_boundary(review),
        client_communication_boundary=build_outcome_client_communication_boundary(review),
        evidence_ref=_handoff_ref(
            ref_type=OUTCOME_AI_EVIDENCE_REF_TYPE,
            outcome_review_id=review.outcome_review_id,
        ),
        content_hash="",
    ).model_dump(mode="json")
    assert_no_ai_forbidden_fields(payload)
    payload["content_hash"] = hash_canonical_payload(strip_keys(payload, exclude={"content_hash"}))
    payload["evidence_ref"]["content_hash"] = payload["content_hash"]
    return DpmOutcomeAiEvidenceInput.model_validate(payload)


def assert_no_ai_forbidden_fields(payload: Any) -> None:
    found = sorted(_find_forbidden_field_names(payload))
    if found:
        raise ValueError(f"DPM_OUTCOME_AI_FORBIDDEN_FIELDS:{','.join(found)}")


def _report_dimension(result: DpmOutcomeDimensionResult) -> DpmOutcomeReportDimension:
    return DpmOutcomeReportDimension(
        dimension=result.dimension,
        state=result.state,
        reason_code=result.reason_code,
        expected=_decimal_to_str(result.expected),
        realized=_decimal_to_str(result.realized),
        variance=_decimal_to_str(result.variance),
        explanation=result.explanation,
        source_refs=result.source_refs,
        supportability=result.supportability,
    )


def _ai_dimension(result: dict[str, Any]) -> DpmOutcomeAiDimensionEvidence:
    return DpmOutcomeAiDimensionEvidence(
        dimension=result["dimension"],
        state=result["state"],
        reason_code=result["reason_code"],
        expected=_value_to_str(result.get("expected")),
        realized=_value_to_str(result.get("realized")),
        variance=_value_to_str(result.get("variance")),
        explanation=result["explanation"],
    )


def _sanitize_for_ai(value: Any, removed: set[str]) -> Any:
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            if key.lower() in AI_FORBIDDEN_FIELD_NAMES:
                removed.add(key.lower())
                continue
            sanitized[key] = _sanitize_for_ai(item, removed)
        return sanitized
    if isinstance(value, list):
        return [_sanitize_for_ai(item, removed) for item in value]
    return value


def _find_forbidden_field_names(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            if key.lower() in AI_FORBIDDEN_FIELD_NAMES:
                found.add(key.lower())
            found.update(_find_forbidden_field_names(item))
    elif isinstance(value, list):
        for item in value:
            found.update(_find_forbidden_field_names(item))
    return found


def _dedupe_source_refs(review: DpmPostTradeOutcomeReview) -> list[DpmOutcomeSourceRef]:
    refs_by_key: dict[tuple[str, str, str], DpmOutcomeSourceRef] = {}
    for ref in review.source_lineage:
        refs_by_key[(ref.source_system, ref.source_type, ref.source_id)] = ref
    return list(refs_by_key.values())


def _handoff_ref(*, ref_type: str, outcome_review_id: str) -> DpmOutcomeSourceRef:
    return DpmOutcomeSourceRef(
        source_system="lotus-manage",
        source_type=ref_type,
        source_id=f"{outcome_review_id}:{ref_type.lower()}",
        content_hash=None,
    )


def _stringify_variance_summary(review: DpmPostTradeOutcomeReview) -> dict[str, str | None]:
    return {dimension: _value_to_str(value) for dimension, value in review.variance_summary.items()}


def _decimal_to_str(value: Any) -> str | None:
    return _value_to_str(value)


def _value_to_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)
