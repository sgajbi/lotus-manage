from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol

from src.api.routers.wave_portfolio_type_validation import normalize_required_portfolio_type
from src.api.routers.wave_source_refs import (
    source_refs_payload,
    tactical_house_view_affected_portfolio_ref,
    tactical_house_view_cohort_ref,
    tactical_house_view_ref,
)
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


class TacticalHouseViewAffectedPortfolio(Protocol):
    @property
    def portfolio_id(self) -> str: ...

    @property
    def mandate_id(self) -> str | None: ...

    @property
    def inclusion_reason_codes(self) -> tuple[str, ...]: ...

    @property
    def source_refs(self) -> Sequence[dict[str, object]]: ...


class TacticalHouseViewAffectedCohort(Protocol):
    @property
    def cohort_id(self) -> str: ...

    @property
    def tactical_view_id(self) -> str: ...

    @property
    def tactical_view_version(self) -> str: ...

    @property
    def theme_id(self) -> str: ...

    @property
    def target_action(self) -> str: ...

    @property
    def product_name(self) -> str: ...

    @property
    def product_version(self) -> str: ...

    @property
    def source_service(self) -> str: ...

    @property
    def content_hash(self) -> str | None: ...

    @property
    def supportability_state(self) -> str: ...

    @property
    def supportability_reason_codes(self) -> tuple[str, ...]: ...

    @property
    def affected_portfolios(self) -> tuple[TacticalHouseViewAffectedPortfolio, ...]: ...


class TacticalHouseViewSource(Protocol):
    @property
    def tactical_view_id(self) -> str: ...

    @property
    def tactical_view_version(self) -> str: ...

    @property
    def theme_id(self) -> str: ...

    @property
    def target_action(self) -> str: ...

    @property
    def rationale(self) -> str: ...

    @property
    def source_refs(self) -> Sequence[DpmWaveSourceRef]: ...


@dataclass(frozen=True)
class TacticalHouseViewAuthorityRequest:
    tactical_view: dict[str, object]
    candidate_portfolios: list[dict[str, object]]
    eligible_portfolio_types: list[str]
    min_exposure_weight: Decimal | None


@dataclass(frozen=True)
class TacticalHouseViewCohortFailure:
    code: str
    message: str
    reason_codes: tuple[str, ...] = ()


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


def build_tactical_house_view_authority_request(
    *,
    tactical_view: TacticalHouseViewSource,
    portfolios: Iterable[TacticalHouseViewCandidate],
    eligible_portfolio_types: list[str],
    as_of_date: date,
    min_exposure_weight: float | None,
) -> TacticalHouseViewAuthorityRequest:
    return TacticalHouseViewAuthorityRequest(
        tactical_view={
            "tactical_view_id": tactical_view.tactical_view_id,
            "tactical_view_version": tactical_view.tactical_view_version,
            "theme_id": tactical_view.theme_id,
            "as_of_date": as_of_date.isoformat(),
            "target_action": tactical_view.target_action,
            "rationale": tactical_view.rationale,
            "source_refs": source_refs_payload(tactical_view.source_refs),
            "reason_codes": ["TACTICAL_HOUSE_VIEW_BANK_AUTHORED"],
        },
        candidate_portfolios=build_tactical_house_view_candidate_payloads(portfolios),
        eligible_portfolio_types=eligible_portfolio_types,
        min_exposure_weight=(
            Decimal(str(min_exposure_weight)) if min_exposure_weight is not None else None
        ),
    )


def tactical_house_view_cohort_failure(
    cohort: TacticalHouseViewAffectedCohort,
) -> TacticalHouseViewCohortFailure | None:
    if cohort.supportability_state != "READY":
        return TacticalHouseViewCohortFailure(
            code=(
                "DPM_TACTICAL_HOUSE_VIEW_COHORT_EMPTY"
                if cohort.supportability_state == "EMPTY"
                else "DPM_TACTICAL_HOUSE_VIEW_COHORT_INCOMPLETE"
            ),
            message="Tactical house-view affected cohort is not source-ready.",
            reason_codes=tuple(cohort.supportability_reason_codes),
        )
    if not cohort.affected_portfolios:
        return TacticalHouseViewCohortFailure(
            code="DPM_TACTICAL_HOUSE_VIEW_COHORT_EMPTY",
            message="Tactical house-view cohort returned no affected portfolios.",
        )
    return None


def build_tactical_house_view_resolved_portfolios(
    cohort: TacticalHouseViewAffectedCohort,
) -> list[dict[str, object]]:
    cohort_ref = tactical_house_view_cohort_ref(
        source_service=cohort.source_service,
        product_name=cohort.product_name,
        cohort_id=cohort.cohort_id,
        product_version=cohort.product_version,
        supportability_state=cohort.supportability_state,
        content_hash=cohort.content_hash,
    )
    house_view_ref = tactical_house_view_ref(
        source_service=cohort.source_service,
        tactical_view_id=cohort.tactical_view_id,
        tactical_view_version=cohort.tactical_view_version,
        supportability_state=cohort.supportability_state,
        content_hash=cohort.content_hash,
    )
    return [
        {
            "portfolio_id": affected.portfolio_id,
            "mandate_id": affected.mandate_id,
            "source_refs": [
                cohort_ref,
                house_view_ref,
                tactical_house_view_affected_portfolio_ref(
                    source_service=cohort.source_service,
                    cohort_id=cohort.cohort_id,
                    portfolio_id=affected.portfolio_id,
                    product_version=cohort.product_version,
                    supportability_state=cohort.supportability_state,
                    content_hash=cohort.content_hash,
                ),
                *affected.source_refs,
            ],
            "diagnostics": {
                "source_owner": cohort.source_service,
                "source_product": f"{cohort.product_name}:{cohort.product_version}",
                "tactical_view_id": cohort.tactical_view_id,
                "tactical_view_version": cohort.tactical_view_version,
                "theme_id": cohort.theme_id,
                "target_action": cohort.target_action,
                "cohort_supportability_state": cohort.supportability_state,
                "cohort_reason_codes": list(cohort.supportability_reason_codes),
                "inclusion_reason_codes": list(affected.inclusion_reason_codes),
            },
        }
        for affected in cohort.affected_portfolios
    ]
