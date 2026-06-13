from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi import HTTPException

from src.api.routers.pm_operating_quality_models import (
    DpmPmOperatingQualityScorePreviewRequest,
)
from src.api.routers.pm_operating_quality_score_run_builder import (
    _outcome_reviews_for_request,
    _score_run_evidence_inputs,
)
from src.core.pm_quality import (
    DpmPmOperatingQualityPolicy,
    DpmPmQualityEvidenceItem,
)


class _MissingOutcomeRepository:
    def get_outcome_review(self, *, outcome_review_id: str) -> None:
        return None


def _score_request(
    *,
    outcome_review_ids: list[str] | None = None,
) -> DpmPmOperatingQualityScorePreviewRequest:
    return DpmPmOperatingQualityScorePreviewRequest(
        pm_id="pm_001",
        book_id="sg_dpm_balanced_book",
        as_of_date="2026-05-12",
        policy=DpmPmOperatingQualityPolicy(
            policy_id="pmq_sg_dpm",
            policy_version="2026.05",
            enabled=False,
            as_of_date="2026-05-12",
            access_purpose="SUPERVISORY_CONTROL_REVIEW",
        ),
        evidence_items=[
            DpmPmQualityEvidenceItem(
                indicator="SOURCE_QUALITY",
                evidence_state="READY",
                score=Decimal("95"),
                source_system="lotus-risk",
                source_type="RiskAttributionEvidence",
                source_id="risk-pm-001",
                reason_codes=["SOURCE_READY"],
            )
        ],
        outcome_review_ids=outcome_review_ids or [],
        actor_id="ops",
    )


def test_score_run_evidence_inputs_copy_inline_evidence_without_book_scope() -> None:
    request = _score_request()

    evidence_inputs = _score_run_evidence_inputs(
        request=request,
        correlation_id="corr-pmq-builder",
        core_resolver_factory=object,
    )

    assert evidence_inputs.book_scope_evidence is None
    assert evidence_inputs.evidence_items == request.evidence_items
    assert evidence_inputs.evidence_items is not request.evidence_items


def test_outcome_reviews_for_request_maps_missing_review_to_404() -> None:
    request = _score_request(outcome_review_ids=["dor_missing"])

    with pytest.raises(HTTPException) as exc_info:
        _outcome_reviews_for_request(
            request=request,
            repository=_MissingOutcomeRepository(),
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "OUTCOME_REVIEW_NOT_FOUND:dor_missing"
