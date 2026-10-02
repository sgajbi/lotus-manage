"""Reject incomplete or internally contradictory publication evidence."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from src.core.composite_publication import (
    DpmCompositeMembershipPublication,
    DpmCompositePublicationReceipt,
)


def _publication() -> DpmCompositeMembershipPublication:
    return DpmCompositeMembershipPublication(
        sequence=1,
        tenant_id="tenant-sg",
        composite_id="GLOBAL_BALANCED",
        definition_version="2026.10",
        membership_revision="2026.10.1",
        membership_content_hash="sha256:revision-001",
        policy_version="eligibility.v1",
        source_cut_id="core-cut-001",
        decision_count=3,
        decided_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
        published_at=datetime(2026, 10, 2, tzinfo=timezone.utc),
    )


def _receipt() -> DpmCompositePublicationReceipt:
    return DpmCompositePublicationReceipt(
        tenant_id="tenant-sg",
        publication_sequence=1,
        membership_content_hash="sha256:revision-001",
        consumer_id="lotus-performance",
        receipt_evidence_hash="sha256:retrieval-001",
        disposition="RECEIVED",
        received_at=datetime(2026, 10, 2, tzinfo=timezone.utc),
        correlation_id="corr-retrieval-001",
    )


def test_publication_requires_nonblank_source_and_timezone() -> None:
    valid = _publication()
    assert valid.completeness == "UNVERIFIED"
    with pytest.raises(ValidationError, match="COMPOSITE_PUBLICATION_REQUIRED_TEXT"):
        DpmCompositeMembershipPublication.model_validate(
            valid.model_dump() | {"source_cut_id": " "}
        )
    with pytest.raises(ValidationError, match="COMPOSITE_PUBLICATION_TIMEZONE_REQUIRED"):
        DpmCompositeMembershipPublication.model_validate(
            valid.model_dump() | {"decided_at": datetime(2026, 10, 1)}
        )


def test_receipt_requires_valid_evidence_and_disposition_reason() -> None:
    valid = _receipt()
    assert valid.disposition == "RECEIVED"
    cases = (
        ({"receipt_evidence_hash": " "}, "COMPOSITE_PUBLICATION_RECEIPT_REQUIRED_TEXT"),
        ({"received_at": datetime(2026, 10, 2)}, "COMPOSITE_RECEIPT_TIMEZONE_REQUIRED"),
        ({"disposition": "REJECTED"}, "COMPOSITE_RECEIPT_REJECTION_REASON_REQUIRED"),
        ({"reason_code": "SOURCE_GAP"}, "COMPOSITE_RECEIPT_SUCCESS_REASON_FORBIDDEN"),
    )
    for change, error_code in cases:
        with pytest.raises(ValidationError, match=error_code):
            DpmCompositePublicationReceipt.model_validate(valid.model_dump() | change)
