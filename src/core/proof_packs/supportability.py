"""Proof-pack supportability aggregation helpers."""

from src.core.proof_packs.models import (
    DpmProofPackSection,
    DpmProofPackSupportability,
    ProofPackStatus,
)


def supportability(sections: list[DpmProofPackSection]) -> DpmProofPackSupportability:
    counts: dict[str, int] = {}
    reason_codes: list[str] = []
    section_hashes: dict[str, str] = {}
    for section in sections:
        counts[section.state] = counts.get(section.state, 0) + 1
        reason_codes.extend(section.reason_codes)
        section_hashes[section.section_id] = section.content_hash
    status = aggregate_status(counts)
    return DpmProofPackSupportability(
        status=status,
        section_state_counts=counts,
        ready_section_count=counts.get("READY", 0),
        degraded_section_count=counts.get("DEGRADED", 0),
        blocked_section_count=counts.get("BLOCKED", 0),
        pending_review_section_count=counts.get("PENDING_REVIEW", 0),
        reason_codes=sorted(set(reason_codes)),
        section_hashes=section_hashes,
    )


def aggregate_status(counts: dict[str, int]) -> ProofPackStatus:
    if counts.get("BLOCKED", 0) > 0:
        return "BLOCKED"
    if counts.get("PENDING_REVIEW", 0) > 0:
        return "PENDING_REVIEW"
    if counts.get("DEGRADED", 0) > 0:
        return "DEGRADED"
    return "READY"
