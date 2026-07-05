from __future__ import annotations

import pytest

from src.core.portfolio_memory.handoffs import (
    DpmPortfolioMemoryReportEventRef,
    _validate_event_ref_counts,
    _validate_event_ref_governance,
    _validate_event_ref_ranks,
    _validate_governance_policy,
)


def _governance_policy() -> dict[str, str]:
    return {
        "event_identity_scheme": (
            "source_system:source_type:source_id:content_hash_or_content_hash_unavailable"
        ),
        "retention_policy": "DPM_PORTFOLIO_MEMORY_SOURCE_LINEAGE_7Y",
        "redaction_policy": "NO_RAW_PAYLOADS",
        "audit_policy": "AUDIT_READ_AND_EXPORT",
        "access_classification": "CLIENT_CONFIDENTIAL_INTERNAL",
        "source_authority_policy": (
            "portfolio memory projects source-owned facts; consumers must not reconstruct truth"
        ),
    }


def _event_ref(*, rank: int = 1) -> DpmPortfolioMemoryReportEventRef:
    return DpmPortfolioMemoryReportEventRef(
        event_id="memory:proof_pack:dpp_001:created",
        event_identity="lotus-manage:PROOF_PACK:dpp_001:sha256:proof-pack",
        event_type="PROOF_PACK_CREATED",
        event_time="2026-05-07T10:00:00Z",
        event_ref_selection_rank=rank,
        source_system="lotus-manage",
        source_type="PROOF_PACK",
        source_id="dpp_001",
        content_hash="sha256:proof-pack",
        retention_policy="DPM_PORTFOLIO_MEMORY_SOURCE_LINEAGE_7Y",
        redaction_policy="NO_RAW_PAYLOADS",
        audit_policy="AUDIT_READ_AND_EXPORT",
        access_classification="CLIENT_CONFIDENTIAL_INTERNAL",
    )


def test_event_ref_counts_accept_consistent_bounded_projection() -> None:
    _validate_event_ref_counts(
        event_count=3,
        event_refs_returned=1,
        event_refs_omitted=2,
        event_refs_truncated=True,
        event_ref_count=1,
    )


def test_event_ref_counts_reject_inconsistent_returned_count() -> None:
    with pytest.raises(ValueError, match="event_refs_returned must equal"):
        _validate_event_ref_counts(
            event_count=3,
            event_refs_returned=2,
            event_refs_omitted=1,
            event_refs_truncated=True,
            event_ref_count=1,
        )


def test_event_ref_ranks_require_contiguous_one_based_values() -> None:
    _validate_event_ref_ranks([_event_ref(rank=1)])

    with pytest.raises(ValueError, match="contiguous one-based ranks"):
        _validate_event_ref_ranks([_event_ref(rank=2)])


def test_governance_policy_requires_complete_non_blank_values() -> None:
    _validate_governance_policy(_governance_policy())

    missing = _governance_policy()
    missing.pop("source_authority_policy")
    with pytest.raises(ValueError, match="missing required keys: source_authority_policy"):
        _validate_governance_policy(missing)

    blank = _governance_policy()
    blank["audit_policy"] = " "
    with pytest.raises(ValueError, match="non-blank for keys: audit_policy"):
        _validate_governance_policy(blank)


def test_event_ref_governance_requires_refs_to_match_policy() -> None:
    _validate_event_ref_governance(
        governance_policy=_governance_policy(),
        event_refs=[_event_ref()],
    )

    mismatched = _event_ref().model_copy(update={"audit_policy": "READ_ONLY"})
    with pytest.raises(ValueError, match="event_refs must match governance_policy.audit_policy"):
        _validate_event_ref_governance(
            governance_policy=_governance_policy(),
            event_refs=[mismatched],
        )
