from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from src.api.routers.wave_campaign_definition_resolution import (
    request_with_campaign_definition,
)
from src.api.routers.wave_campaign_source_resolution import (
    resolve_bulk_review_campaign_portfolios,
)
from src.api.routers.wave_core_source_resolution import (
    resolve_cio_model_change_portfolios,
    resolve_pm_book_portfolios,
)
from src.api.routers.wave_date_validation import parse_wave_as_of_date
from src.api.routers.wave_portfolio_type_validation import (
    normalize_required_portfolio_types,
)
from src.api.routers.wave_request_models import DpmTacticalHouseViewInput
from src.api.routers.wave_request_models import DpmWavePortfolioInput
from src.api.routers.wave_request_models import DpmWavePreviewRequest
from src.api.routers.wave_required_text_validation import normalize_required_text
from src.api.routers.wave_risk_event_validation import (
    RiskEventAffectedCohort,
    RiskEventCandidatePayloads,
    build_risk_event_candidate_payloads,
    build_risk_event_resolved_portfolios,
)
from src.api.routers.wave_source_dependency_http import (
    source_authority_unavailable_http_exception,
    source_dependency_failed_http_exception,
    source_unavailable_http_exception,
)
from src.api.routers.wave_tactical_candidate_selection import (
    TacticalHouseViewAuthorityRequest,
    build_tactical_house_view_authority_request,
    build_tactical_house_view_resolved_portfolios,
    tactical_house_view_cohort_failure,
)
from src.api.services import wave_service
from src.core.waves import DpmBulkReviewCampaignDefinitionRepository
from src.api.services.authority_client_service import (
    AdviseAuthorityClient,
    AdviseAuthorityUnavailableError,
    RiskAuthorityClient,
    RiskAuthorityUnavailableError,
)


@dataclass(frozen=True)
class _PortfolioResolutionContext:
    request: DpmWavePreviewRequest
    correlation_id: str
    advise_authority_client: AdviseAuthorityClient | None
    risk_authority_client: RiskAuthorityClient | None
    campaign_definition_repository: DpmBulkReviewCampaignDefinitionRepository
    core_resolver_factory: Callable[[], object]


@dataclass(frozen=True)
class _RiskEventAuthorityRequest:
    risk_event_id: str
    as_of_date: date
    candidate_payloads: RiskEventCandidatePayloads[DpmWavePortfolioInput]
    minimum_impact_score: Decimal


def resolve_portfolio_inputs_for_request(
    *,
    request: DpmWavePreviewRequest,
    correlation_id: str,
    advise_authority_client: AdviseAuthorityClient | None,
    risk_authority_client: RiskAuthorityClient | None,
    campaign_definition_repository: DpmBulkReviewCampaignDefinitionRepository,
    core_resolver_factory: Callable[[], object],
) -> list[dict[str, object]]:
    context = _PortfolioResolutionContext(
        request=request,
        correlation_id=correlation_id,
        advise_authority_client=advise_authority_client,
        risk_authority_client=risk_authority_client,
        campaign_definition_repository=campaign_definition_repository,
        core_resolver_factory=core_resolver_factory,
    )
    handler = _PORTFOLIO_RESOLUTION_HANDLERS.get(
        request.trigger_type,
        _resolve_explicit_request_portfolios,
    )
    return handler(context)


def _resolve_explicit_request_portfolios(
    context: _PortfolioResolutionContext,
) -> list[dict[str, object]]:
    return [portfolio.model_dump(mode="json") for portfolio in context.request.portfolios]


def _resolve_pm_book_review_request_portfolios(
    context: _PortfolioResolutionContext,
) -> list[dict[str, object]]:
    return resolve_pm_book_portfolios(
        request=context.request,
        correlation_id=context.correlation_id,
        core_resolver_factory=context.core_resolver_factory,
    )


def _resolve_cio_model_change_request_portfolios(
    context: _PortfolioResolutionContext,
) -> list[dict[str, object]]:
    return resolve_cio_model_change_portfolios(
        request=context.request,
        correlation_id=context.correlation_id,
        core_resolver_factory=context.core_resolver_factory,
    )


def _resolve_risk_event_request_portfolios(
    context: _PortfolioResolutionContext,
) -> list[dict[str, object]]:
    return _resolve_risk_event_portfolios(
        request=context.request,
        correlation_id=context.correlation_id,
        risk_authority_client=context.risk_authority_client,
    )


def _resolve_tactical_house_view_request_portfolios(
    context: _PortfolioResolutionContext,
) -> list[dict[str, object]]:
    return _resolve_tactical_house_view_portfolios(
        request=context.request,
        correlation_id=context.correlation_id,
        advise_authority_client=context.advise_authority_client,
    )


def _resolve_bulk_review_campaign_request_portfolios(
    context: _PortfolioResolutionContext,
) -> list[dict[str, object]]:
    resolved_request = request_with_campaign_definition(
        request=context.request,
        repository=context.campaign_definition_repository,
    )
    return resolve_bulk_review_campaign_portfolios(
        request=resolved_request,
        correlation_id=context.correlation_id,
        core_resolver_factory=context.core_resolver_factory,
    )


_PORTFOLIO_RESOLUTION_HANDLERS: dict[
    str,
    Callable[[_PortfolioResolutionContext], list[dict[str, object]]],
] = {
    "EXPLICIT_PORTFOLIO_LIST": _resolve_explicit_request_portfolios,
    "PM_BOOK_REVIEW": _resolve_pm_book_review_request_portfolios,
    "CIO_MODEL_CHANGE": _resolve_cio_model_change_request_portfolios,
    "RISK_EVENT": _resolve_risk_event_request_portfolios,
    "TACTICAL_HOUSE_VIEW": _resolve_tactical_house_view_request_portfolios,
    "BULK_REVIEW_CAMPAIGN": _resolve_bulk_review_campaign_request_portfolios,
}


def _resolve_tactical_house_view_portfolios(
    *,
    request: DpmWavePreviewRequest,
    correlation_id: str,
    advise_authority_client: AdviseAuthorityClient | None,
) -> list[dict[str, object]]:
    if advise_authority_client is None:
        raise source_unavailable_http_exception(
            code="DPM_TACTICAL_HOUSE_VIEW_COHORT_UNAVAILABLE",
            message="DPM_ADVISE_BASE_URL is not configured.",
        )
    authority_request = _tactical_house_view_authority_request_for_wave(request)

    try:
        cohort = advise_authority_client.tactical_house_view_affected_cohort(
            tactical_view=authority_request.tactical_view,
            candidate_portfolios=authority_request.candidate_portfolios,
            eligible_portfolio_types=authority_request.eligible_portfolio_types,
            min_exposure_weight=authority_request.min_exposure_weight,
            correlation_id=correlation_id,
        )
    except AdviseAuthorityUnavailableError as exc:
        raise source_authority_unavailable_http_exception(
            exc,
            default_code="DPM_TACTICAL_HOUSE_VIEW_COHORT_UNAVAILABLE",
            rejected_code="LOTUS_ADVISE_TACTICAL_HOUSE_VIEW_COHORT_REJECTED",
        ) from exc

    failure = tactical_house_view_cohort_failure(cohort)
    if failure is not None:
        raise source_dependency_failed_http_exception(
            code=failure.code,
            message=failure.message,
            reason_codes=list(failure.reason_codes),
        )

    return build_tactical_house_view_resolved_portfolios(cohort)


def _tactical_house_view_authority_request_for_wave(
    request: DpmWavePreviewRequest,
) -> TacticalHouseViewAuthorityRequest:
    tactical_view = _required_tactical_house_view(request)
    _require_tactical_house_view_candidate_portfolios(request)
    _require_tactical_house_view_source_refs(tactical_view)
    return build_tactical_house_view_authority_request(
        tactical_view=tactical_view,
        portfolios=request.portfolios,
        eligible_portfolio_types=_tactical_house_view_portfolio_types(request),
        as_of_date=parse_wave_as_of_date(request.as_of_date),
        min_exposure_weight=request.min_tactical_exposure_weight,
    )


def _required_tactical_house_view(
    request: DpmWavePreviewRequest,
) -> DpmTacticalHouseViewInput:
    tactical_view = request.tactical_house_view
    if tactical_view is None:
        raise wave_service.DpmWaveValidationError(
            "TACTICAL_HOUSE_VIEW_REQUIRED",
            "TACTICAL_HOUSE_VIEW requires tactical_house_view source evidence.",
        )
    return tactical_view


def _require_tactical_house_view_candidate_portfolios(
    request: DpmWavePreviewRequest,
) -> None:
    if request.portfolios:
        return
    raise wave_service.DpmWaveValidationError(
        "TACTICAL_HOUSE_VIEW_CANDIDATE_PORTFOLIOS_REQUIRED",
        "TACTICAL_HOUSE_VIEW requires source-backed candidate portfolios.",
    )


def _require_tactical_house_view_source_refs(
    tactical_view: DpmTacticalHouseViewInput,
) -> None:
    if tactical_view.source_refs:
        return
    raise wave_service.DpmWaveValidationError(
        "TACTICAL_HOUSE_VIEW_SOURCE_REFS_REQUIRED",
        "TACTICAL_HOUSE_VIEW requires tactical house-view source_refs.",
    )


def _tactical_house_view_portfolio_types(
    request: DpmWavePreviewRequest,
) -> list[str]:
    return normalize_required_portfolio_types(
        request.portfolio_types,
        required_code="TACTICAL_HOUSE_VIEW_PORTFOLIO_TYPES_REQUIRED",
        required_message="TACTICAL_HOUSE_VIEW requires at least one eligible portfolio type.",
    )


def _resolve_risk_event_portfolios(
    *,
    request: DpmWavePreviewRequest,
    correlation_id: str,
    risk_authority_client: RiskAuthorityClient | None,
) -> list[dict[str, object]]:
    authority_request = _risk_event_authority_request_for_wave(request)
    risk_authority = _required_risk_event_authority_client(risk_authority_client)
    cohort = _risk_event_affected_cohort(
        risk_authority_client=risk_authority,
        authority_request=authority_request,
        correlation_id=correlation_id,
    )
    _require_risk_event_cohort_ready(cohort)

    return build_risk_event_resolved_portfolios(
        cohort=cohort,
        candidate_by_portfolio_id=authority_request.candidate_payloads.candidate_by_portfolio_id,
        fallback_risk_event_id=authority_request.risk_event_id,
    )


def _risk_event_authority_request_for_wave(
    request: DpmWavePreviewRequest,
) -> _RiskEventAuthorityRequest:
    risk_event_id = normalize_required_text(
        request.risk_event_id,
        required_code="RISK_EVENT_ID_REQUIRED",
        required_message="RISK_EVENT requires risk_event_id.",
    )
    if not request.portfolios:
        raise wave_service.DpmWaveValidationError(
            "RISK_EVENT_CANDIDATE_PORTFOLIOS_REQUIRED",
            "RISK_EVENT requires candidate portfolios with source-supplied exposure weights.",
        )
    candidate_payloads = build_risk_event_candidate_payloads(request.portfolios)
    return _RiskEventAuthorityRequest(
        risk_event_id=risk_event_id,
        as_of_date=parse_wave_as_of_date(request.as_of_date),
        candidate_payloads=candidate_payloads,
        minimum_impact_score=Decimal(str(request.minimum_impact_score)),
    )


def _required_risk_event_authority_client(
    risk_authority_client: RiskAuthorityClient | None,
) -> RiskAuthorityClient:
    if risk_authority_client is not None:
        return risk_authority_client
    raise source_unavailable_http_exception(
        code="DPM_RISK_EVENT_COHORT_UNAVAILABLE",
        message="DPM_RISK_BASE_URL is not configured.",
    )


def _risk_event_affected_cohort(
    *,
    risk_authority_client: RiskAuthorityClient,
    authority_request: _RiskEventAuthorityRequest,
    correlation_id: str,
) -> RiskEventAffectedCohort:
    try:
        return risk_authority_client.risk_event_affected_cohort(
            risk_event_id=authority_request.risk_event_id,
            as_of_date=authority_request.as_of_date,
            portfolios=authority_request.candidate_payloads.risk_portfolios,
            minimum_impact_score=authority_request.minimum_impact_score,
            correlation_id=correlation_id,
        )
    except RiskAuthorityUnavailableError as exc:
        raise source_authority_unavailable_http_exception(
            exc,
            default_code="DPM_RISK_EVENT_COHORT_UNAVAILABLE",
            rejected_code="LOTUS_RISK_EVENT_COHORT_REJECTED",
        ) from exc


def _require_risk_event_cohort_ready(cohort: RiskEventAffectedCohort) -> None:
    if cohort.calculation_supportability != "ready":
        raise source_dependency_failed_http_exception(
            code="DPM_RISK_EVENT_COHORT_INCOMPLETE",
            message="Risk-event affected cohort is not source-ready.",
            reason_codes=list(cohort.reason_codes),
        )
    if not cohort.affected_portfolios:
        raise source_dependency_failed_http_exception(
            code="DPM_RISK_EVENT_COHORT_EMPTY",
            message="Risk-event affected cohort returned no affected portfolios.",
        )
