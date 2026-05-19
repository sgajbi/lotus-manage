from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Protocol

from src.api.routers.wave_portfolio_type_validation import normalize_required_portfolio_type
from src.api.routers.wave_source_refs import source_refs_payload
from src.api.services import wave_service
from src.core.waves import DpmWaveSourceRef


class TacticalHouseViewCandidate(Protocol):
    @property
    def portfolio_id(self) -> str: ...

    @property
    def mandate_id(self) -> str | None: ...

    @property
    def portfolio_type(self) -> str | None: ...

    @property
    def discretionary_mandate(self) -> bool | None: ...

    @property
    def current_exposure_weight(self) -> float | None: ...

    @property
    def alignment_signal(self) -> str: ...

    @property
    def source_refs(self) -> Sequence[DpmWaveSourceRef]: ...


def build_tactical_house_view_candidate_payloads(
    candidates: Iterable[TacticalHouseViewCandidate],
) -> list[dict[str, object]]:
    payloads: list[dict[str, object]] = []
    for candidate in candidates:
        portfolio_type = normalize_required_portfolio_type(
            candidate.portfolio_type,
            required_code="TACTICAL_HOUSE_VIEW_PORTFOLIO_TYPE_REQUIRED",
            required_message=(
                "TACTICAL_HOUSE_VIEW candidate portfolios require source-owned portfolio_type."
            ),
        )
        if candidate.discretionary_mandate is None:
            raise wave_service.DpmWaveValidationError(
                "TACTICAL_HOUSE_VIEW_DISCRETIONARY_MANDATE_REQUIRED",
                "TACTICAL_HOUSE_VIEW candidate portfolios require source-owned discretionary_mandate.",
            )
        if not candidate.source_refs:
            raise wave_service.DpmWaveValidationError(
                "TACTICAL_HOUSE_VIEW_CANDIDATE_SOURCE_REFS_REQUIRED",
                "TACTICAL_HOUSE_VIEW candidate portfolios require source_refs.",
            )
        payloads.append(
            {
                "portfolio_id": candidate.portfolio_id,
                "mandate_id": candidate.mandate_id,
                "portfolio_type": portfolio_type,
                "discretionary_mandate": candidate.discretionary_mandate,
                "current_exposure_weight": (
                    str(candidate.current_exposure_weight)
                    if candidate.current_exposure_weight is not None
                    else None
                ),
                "alignment_signal": candidate.alignment_signal,
                "source_refs": source_refs_payload(candidate.source_refs),
                "reason_codes": ["TACTICAL_HOUSE_VIEW_CANDIDATE_SOURCE_BACKED"],
            }
        )
    return payloads
