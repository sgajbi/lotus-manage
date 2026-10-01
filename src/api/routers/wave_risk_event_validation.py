from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from typing import Generic, Protocol, TypeVar

from src.api.routers.wave_source_refs import (
    risk_event_affected_portfolio_ref,
    risk_event_cohort_ref,
    risk_event_ref,
    source_refs_payload,
)
from src.api.services import wave_service
from src.core.waves import DpmWaveSourceRef


class RiskEventCandidate(Protocol):
    @property
    def portfolio_id(self) -> str: ...

    @property
    def mandate_id(self) -> str | None: ...

    @property
    def portfolio_manager_id(self) -> str | None: ...

    @property
    def exposure_weights(self) -> Mapping[str, float]: ...

    @property
    def source_refs(self) -> list[DpmWaveSourceRef]: ...


class RiskEventAffectedPortfolio(Protocol):
    @property
    def portfolio_id(self) -> str: ...

    @property
    def mandate_id(self) -> str | None: ...

    @property
    def source_ref(self) -> str: ...


class RiskEventExcludedPortfolio(Protocol):
    @property
    def portfolio_id(self) -> str: ...

    @property
    def mandate_id(self) -> str | None: ...


class RiskEventAffectedCohort(Protocol):
    @property
    def cohort_id(self) -> str | None: ...

    @property
    def risk_event_id(self) -> str: ...

    @property
    def as_of_date(self) -> date: ...

    @property
    def product_name(self) -> str: ...

    @property
    def product_version(self) -> str: ...

    @property
    def source_service(self) -> str: ...

    @property
    def request_fingerprint(self) -> str | None: ...

    @property
    def calculation_supportability(self) -> str: ...

    @property
    def reason_codes(self) -> tuple[str, ...]: ...

    @property
    def affected_portfolios(self) -> tuple[RiskEventAffectedPortfolio, ...]: ...

    @property
    def excluded_portfolios(self) -> tuple[RiskEventExcludedPortfolio, ...]: ...


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
    portfolio_ids = [candidate.portfolio_id for candidate in candidates]
    if len(portfolio_ids) != len(set(portfolio_ids)):
        raise wave_service.DpmWaveValidationError(
            "RISK_EVENT_CANDIDATE_PORTFOLIO_DUPLICATE",
            "RISK_EVENT candidate portfolio identities must be unique.",
        )
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


def risk_event_cohort_membership_failure(
    *,
    cohort: RiskEventAffectedCohort,
    candidate_by_portfolio_id: Mapping[str, RiskEventCandidate],
    risk_event_id: str,
    as_of_date: date,
) -> str | None:
    if cohort.risk_event_id != risk_event_id:
        return "DPM_RISK_EVENT_COHORT_EVENT_MISMATCH"
    if cohort.as_of_date != as_of_date:
        return "DPM_RISK_EVENT_COHORT_DATE_MISMATCH"
    seen: set[str] = set()
    for member in (*cohort.affected_portfolios, *cohort.excluded_portfolios):
        if member.portfolio_id in seen:
            return "DPM_RISK_EVENT_COHORT_DUPLICATE_MEMBER"
        seen.add(member.portfolio_id)
        candidate = candidate_by_portfolio_id.get(member.portfolio_id)
        if candidate is None:
            return "DPM_RISK_EVENT_COHORT_UNKNOWN_MEMBER"
        if member.mandate_id != candidate.mandate_id:
            return "DPM_RISK_EVENT_COHORT_MANDATE_MISMATCH"
    return None


def build_risk_event_resolved_portfolios(
    *,
    cohort: RiskEventAffectedCohort,
    candidate_by_portfolio_id: Mapping[str, RiskEventCandidate],
    fallback_risk_event_id: str,
) -> list[dict[str, object]]:
    source_id = cohort.cohort_id or cohort.request_fingerprint or fallback_risk_event_id
    supportability_state = cohort.calculation_supportability.upper()
    cohort_ref = risk_event_cohort_ref(
        source_service=cohort.source_service,
        product_name=cohort.product_name,
        source_id=source_id,
        product_version=cohort.product_version,
        supportability_state=supportability_state,
        content_hash=cohort.request_fingerprint,
    )
    event_ref = risk_event_ref(
        source_service=cohort.source_service,
        risk_event_id=cohort.risk_event_id,
        product_version=cohort.product_version,
        supportability_state=supportability_state,
        content_hash=cohort.request_fingerprint,
    )
    portfolios: list[dict[str, object]] = []
    for affected in cohort.affected_portfolios:
        candidate_refs = candidate_by_portfolio_id[affected.portfolio_id].source_refs
        portfolios.append(
            {
                "portfolio_id": affected.portfolio_id,
                "mandate_id": affected.mandate_id,
                "source_refs": [
                    cohort_ref,
                    event_ref,
                    risk_event_affected_portfolio_ref(
                        source_service=cohort.source_service,
                        source_ref=affected.source_ref,
                        product_version=cohort.product_version,
                        supportability_state=supportability_state,
                        content_hash=cohort.request_fingerprint,
                    ),
                    *source_refs_payload(candidate_refs),
                ],
            }
        )
    return portfolios
