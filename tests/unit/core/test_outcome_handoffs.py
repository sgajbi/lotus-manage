import pytest

from src.core.outcomes import (
    OUTCOME_AI_EVIDENCE_REF_TYPE,
    OUTCOME_REPORT_INPUT_REF_TYPE,
    assert_no_ai_forbidden_fields,
    build_ai_evidence_input,
    build_report_input,
)
from src.core.portfolio_memory.handoffs import DpmPortfolioMemoryReportContext
from tests.unit.infrastructure.test_outcome_review_repository import _review


def test_outcome_report_input_is_deterministic_and_hash_linked() -> None:
    review = _review()

    report_input = build_report_input(review)
    replay = build_report_input(review)

    assert report_input == replay
    assert report_input.outcome_review_id == review.outcome_review_id
    assert report_input.outcome_review_content_hash == review.content_hash
    assert report_input.evidence_ref.source_type == OUTCOME_REPORT_INPUT_REF_TYPE
    assert report_input.evidence_ref.content_hash == report_input.content_hash
    assert report_input.content_hash.startswith("sha256:")
    assert report_input.dimensions[0].dimension == "DRIFT_REDUCTION"
    assert report_input.external_execution_boundary.boundary_id == (
        "DPM_OUTCOME_EXTERNAL_EXECUTION_BOUNDARY"
    )
    assert report_input.external_execution_boundary.source_product_present is False
    assert report_input.external_execution_boundary.required_source_product == (
        "ExternalOrderExecutionAcknowledgement:v1"
    )
    assert report_input.redaction_policy == "NO_RAW_PAYLOADS"


def test_outcome_report_input_carries_portfolio_memory_without_changing_hash() -> None:
    review = _review()
    without_context = build_report_input(review)
    memory_context = DpmPortfolioMemoryReportContext.model_validate(
        {
            "portfolio_id": review.portfolio_id,
            "supportability_state": "READY",
            "event_count": 1,
            "source_systems": ["lotus-manage"],
            "reason_codes": ["outcome_review_ready"],
            "content_hash": "sha256:portfolio-memory",
            "governance_policy": {
                "retention_policy": "DPM_PORTFOLIO_MEMORY_SOURCE_LINEAGE_7Y",
                "redaction_policy": "NO_RAW_PAYLOADS",
                "audit_policy": "AUDIT_READ_AND_EXPORT",
                "access_classification": "CLIENT_CONFIDENTIAL_INTERNAL",
            },
            "event_refs": [
                {
                    "event_identity": "lotus-manage:DPM_POST_TRADE_OUTCOME_REVIEW:dor_001:sha256:review",
                    "event_type": "OUTCOME_REVIEW_CREATED",
                    "source_system": "lotus-manage",
                    "source_type": "DPM_POST_TRADE_OUTCOME_REVIEW",
                    "source_id": review.outcome_review_id,
                    "content_hash": review.content_hash,
                    "retention_policy": "DPM_PORTFOLIO_MEMORY_SOURCE_LINEAGE_7Y",
                    "redaction_policy": "NO_RAW_PAYLOADS",
                    "audit_policy": "AUDIT_READ_AND_EXPORT",
                    "access_classification": "CLIENT_CONFIDENTIAL_INTERNAL",
                }
            ],
        }
    )

    with_context = build_report_input(review, portfolio_memory_context=memory_context)

    assert with_context.portfolio_memory_context == memory_context
    assert with_context.content_hash == without_context.content_hash
    assert with_context.evidence_ref.content_hash == without_context.evidence_ref.content_hash


def test_outcome_ai_evidence_input_is_bounded_and_forbids_actions() -> None:
    ai_input = build_ai_evidence_input(_review())

    assert ai_input.evidence_ref.source_type == OUTCOME_AI_EVIDENCE_REF_TYPE
    assert ai_input.evidence_ref.content_hash == ai_input.content_hash
    assert ai_input.content_hash.startswith("sha256:")
    assert "place_orders" in ai_input.forbidden_actions
    assert "approve_rebalance" in ai_input.forbidden_actions
    assert "score_portfolio_manager" in ai_input.forbidden_actions
    assert ai_input.external_execution_boundary.boundary_id == (
        "DPM_OUTCOME_EXTERNAL_EXECUTION_BOUNDARY"
    )
    assert ai_input.external_execution_boundary.supportability_state == "BLOCKED"
    assert "oms_acknowledgement" in ai_input.external_execution_boundary.blocked_capabilities
    assert ai_input.permitted_use.startswith("Draft support-only")
    assert_no_ai_forbidden_fields(ai_input.model_dump(mode="json"))


def test_outcome_ai_guardrail_rejects_forbidden_fields() -> None:
    with pytest.raises(ValueError, match="DPM_OUTCOME_AI_FORBIDDEN_FIELDS"):
        assert_no_ai_forbidden_fields({"raw_payload": {"account_number": "123"}})
