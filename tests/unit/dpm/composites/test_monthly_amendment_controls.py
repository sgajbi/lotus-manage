"""Source correction intent cannot borrow policy authority or ambiguous lineage."""

from copy import deepcopy

from pydantic import ValidationError
import pytest

from src.core.composite_authority_models import EvidenceBinding
from src.core.composite_eligibility.monthly_amendment import MonthlySourceAmendment


@pytest.fixture
def claims():
    approval = {
        "product_name": "CompositeMonthlyEvaluationApproval",
        "product_version": "v1",
        "revision": "original.september.r1",
        "digest": "sha256:" + "a" * 64,
    }
    return {
        "correction_kind": "SOURCE_CORRECTION",
        "predecessor_approval_binding": approval,
        "predecessor_receipt_binding": {
            "product_name": "CompositeMonthlyEligibilityPublicationReceipt",
            "product_version": "v1",
            "revision": approval["revision"],
            "digest": "sha256:" + "b" * 64,
        },
        "original_approval_binding": deepcopy(approval),
        "expected_authority_binding": deepcopy(approval),
        "projection_parent_membership_binding": {
            "product_name": "CompositeMembership",
            "product_version": "v1",
            "revision": "published.september.r1",
            "digest": "sha256:" + "c" * 64,
        },
        "expected_current_publication_sequence": 7,
        "affected_from": "2026-09-01",
        "affected_to": "2026-09-30",
        "reason_code": "LATE_SOURCE_CORRECTION",
        "reason": "The source owner retained a corrected September funding observation.",
        "evidence_bindings": [
            {
                "product_name": "SyntheticSourceCorrectionEvidence",
                "product_version": "v1",
                "revision": "funding.september.r2",
                "digest": "sha256:" + "d" * 64,
            }
        ],
    }


def test_explicit_source_amendment_round_trips_without_normalizing_evidence(claims):
    parsed = MonthlySourceAmendment.model_validate(claims)
    assert parsed.model_dump(mode="json") == claims
    assert MonthlySourceAmendment.model_validate(parsed.model_dump(mode="json")) == parsed


@pytest.mark.parametrize(
    "field,value",
    [
        ("correction_kind", "POLICY_CHANGE"),
        ("reason", "   "),
        ("reason", "x" * 2049),
        ("expected_current_publication_sequence", 0),
        ("expected_current_publication_sequence", True),
        ("evidence_bindings", []),
    ],
)
def test_missing_or_unsupported_amendment_authority_refuses(claims, field, value):
    claims[field] = value
    with pytest.raises(ValidationError):
        MonthlySourceAmendment.model_validate(claims)


@pytest.mark.parametrize(
    "field,property,value",
    [
        ("expected_authority_binding", "digest", "sha256:" + "e" * 64),
        ("predecessor_receipt_binding", "revision", "another.month.r1"),
        ("predecessor_receipt_binding", "product_version", "v2"),
        ("predecessor_approval_binding", "product_version", "v3"),
        ("projection_parent_membership_binding", "product_name", "CompositeUniverseAttestation"),
    ],
)
def test_mismatched_lineage_and_projection_references_refuse(claims, field, property, value):
    claims[field][property] = value
    with pytest.raises(ValidationError):
        MonthlySourceAmendment.model_validate(claims)


def test_duplicate_evidence_identity_with_conflicting_digest_refuses(claims):
    conflicting = deepcopy(claims["evidence_bindings"][0])
    conflicting["digest"] = "sha256:" + "e" * 64
    claims["evidence_bindings"].append(conflicting)
    with pytest.raises(ValidationError, match="EVIDENCE_AMBIGUOUS"):
        MonthlySourceAmendment.model_validate(claims)


def test_versioned_amendment_reference_does_not_widen_frozen_authority_binding(claims):
    claims["predecessor_approval_binding"]["product_version"] = "v2"
    claims["expected_authority_binding"]["product_version"] = "v2"
    claims["predecessor_receipt_binding"]["product_version"] = "v2"
    assert (
        MonthlySourceAmendment.model_validate(claims).predecessor_approval_binding.product_version
        == "v2"
    )
    with pytest.raises(ValidationError):
        EvidenceBinding.model_validate(claims["predecessor_approval_binding"])
