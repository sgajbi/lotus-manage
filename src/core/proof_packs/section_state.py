"""Shared proof-pack section state ordering helpers."""

from src.core.proof_packs.models import ProofPackSectionState

_SECTION_STATE_SEVERITY: dict[ProofPackSectionState, int] = {
    "READY": 0,
    "NOT_APPLICABLE": 0,
    "PENDING_REVIEW": 1,
    "DEGRADED": 2,
    "BLOCKED": 3,
}


def lowest_section_state(states: list[ProofPackSectionState]) -> ProofPackSectionState:
    return max(states, key=lambda state: _SECTION_STATE_SEVERITY[state])
