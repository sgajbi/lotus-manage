from __future__ import annotations

from dataclasses import dataclass

from src.core.mandate_repository import DpmMandateRepository
from src.core.mandates import DpmMandateDigitalTwin, DpmMandateHealthSnapshot


@dataclass(frozen=True)
class ProofPackMandateEvidence:
    twin: DpmMandateDigitalTwin | None
    health: DpmMandateHealthSnapshot | None
    gap_codes: list[str]


def resolve_mandate_evidence(
    *,
    mandate_id: str | None,
    portfolio_id: str,
    mandate_repository: DpmMandateRepository | None,
) -> ProofPackMandateEvidence:
    if mandate_id is None or mandate_repository is None:
        return ProofPackMandateEvidence(twin=None, health=None, gap_codes=[])
    twin = mandate_repository.get_latest_mandate(mandate_id=mandate_id)
    if twin is None:
        return ProofPackMandateEvidence(twin=None, health=None, gap_codes=[])
    if twin.portfolio_id != portfolio_id:
        return ProofPackMandateEvidence(
            twin=None,
            health=None,
            gap_codes=["DPM_MANDATE_TWIN_PORTFOLIO_MISMATCH"],
        )
    return ProofPackMandateEvidence(
        twin=twin,
        health=mandate_repository.get_latest_health_snapshot(mandate_id=mandate_id),
        gap_codes=[],
    )
