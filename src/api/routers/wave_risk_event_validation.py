from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Generic, Protocol, TypeVar

from src.api.services import wave_service


class RiskEventCandidate(Protocol):
    @property
    def portfolio_id(self) -> str: ...

    @property
    def mandate_id(self) -> str | None: ...

    @property
    def portfolio_manager_id(self) -> str | None: ...

    @property
    def exposure_weights(self) -> Mapping[str, float]: ...


T = TypeVar("T", bound=RiskEventCandidate)


@dataclass(frozen=True)
class RiskEventCandidatePayloads(Generic[T]):
    candidate_by_portfolio_id: dict[str, T]
    risk_portfolios: list[dict[str, object]]


def normalize_risk_event_exposure_weights(values: Mapping[str, float]) -> dict[str, float]:
    exposure_weights = {
        bucket.strip().upper(): weight for bucket, weight in values.items() if bucket.strip()
    }
    if not exposure_weights:
        raise wave_service.DpmWaveValidationError(
            "RISK_EVENT_EXPOSURE_WEIGHTS_REQUIRED",
            "RISK_EVENT candidate portfolios require source-supplied exposure_weights.",
        )
    if any(weight < 0 for weight in exposure_weights.values()):
        raise wave_service.DpmWaveValidationError(
            "RISK_EVENT_EXPOSURE_WEIGHTS_INVALID",
            "RISK_EVENT exposure_weights must be non-negative.",
        )
    return exposure_weights


def build_risk_event_candidate_payloads(
    candidates: list[T],
) -> RiskEventCandidatePayloads[T]:
    candidate_by_portfolio_id: dict[str, T] = {}
    risk_portfolios: list[dict[str, object]] = []
    for candidate in candidates:
        exposure_weights = normalize_risk_event_exposure_weights(candidate.exposure_weights)
        candidate_by_portfolio_id[candidate.portfolio_id] = candidate
        risk_portfolios.append(
            {
                "portfolio_id": candidate.portfolio_id,
                "mandate_id": candidate.mandate_id,
                "portfolio_manager_id": candidate.portfolio_manager_id,
                "exposure_weights": exposure_weights,
            }
        )

    return RiskEventCandidatePayloads(
        candidate_by_portfolio_id=candidate_by_portfolio_id,
        risk_portfolios=risk_portfolios,
    )
