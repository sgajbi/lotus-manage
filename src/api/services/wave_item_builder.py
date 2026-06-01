import uuid

from src.api.services.wave_portfolio_sources import (
    diagnostics_from_portfolio,
    optional_str,
    source_refs_from_portfolio,
)
from src.core.mandate_repository import DpmMandateRepository
from src.core.waves import DpmRebalanceWaveItem, DpmWaveSourceRef, WaveItemState


def build_wave_item(
    *,
    index: int,
    portfolio: dict[str, object],
    mandate_repository: DpmMandateRepository,
) -> DpmRebalanceWaveItem:
    portfolio_id = str(portfolio["portfolio_id"]).strip()
    mandate_id = optional_str(portfolio.get("mandate_id"))
    source_refs = source_refs_from_portfolio(portfolio)
    latest_mandate = mandate_repository.get_latest_mandate_by_portfolio(portfolio_id=portfolio_id)
    if latest_mandate is not None:
        mandate_id = latest_mandate.mandate_id
        source_refs.append(
            DpmWaveSourceRef(
                source_system="lotus-manage",
                source_type="MANDATE_DIGITAL_TWIN",
                source_id=latest_mandate.mandate_id,
                source_version=latest_mandate.mandate_version,
                supportability_state="READY",
            )
        )

    if source_refs:
        state: WaveItemState = "CANDIDATE"
        reason_codes = ["AFFECTED_PORTFOLIO_SOURCE_READY"]
        diagnostics = {
            "source_posture": "candidate_evidence_available",
            **diagnostics_from_portfolio(portfolio),
        }
    else:
        state = "SOURCE_BLOCKED"
        reason_codes = ["MISSING_AFFECTED_PORTFOLIO_SOURCE"]
        diagnostics = {
            "source_owner": "caller_or_lotus-core",
            "required_action": "SUPPLY_SOURCE_REF",
        }

    return DpmRebalanceWaveItem(
        wave_item_id=f"dwi_{index:03d}_{uuid.uuid4().hex[:8]}",
        portfolio_id=portfolio_id,
        mandate_id=mandate_id,
        state=state,
        reason_codes=reason_codes,
        source_refs=source_refs,
        diagnostics=diagnostics,
    )


__all__ = ["build_wave_item"]
