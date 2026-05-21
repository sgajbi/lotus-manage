from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal

from src.api.routers.wave_campaign_source_resolution import (
    request_with_campaign_definition,
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
from src.api.routers.wave_request_models import DpmWavePreviewRequest
from src.api.routers.wave_required_text_validation import normalize_required_text
from src.api.routers.wave_risk_event_validation import (
    build_risk_event_candidate_payloads,
    build_risk_event_resolved_portfolios,
)
from src.api.routers.wave_source_dependency_http import (
    source_authority_unavailable_http_exception,
    source_dependency_failed_http_exception,
    source_unavailable_http_exception,
)
from src.api.routers.wave_source_refs import source_refs_payload
from src.api.routers.wave_tactical_candidate_selection import (
    build_tactical_house_view_candidate_payloads,
    build_tactical_house_view_resolved_portfolios,
)
from src.api.services import wave_service
from src.core.waves import DpmBulkReviewCampaignDefinitionRepository
from src.infrastructure.advise_authority import (
    LotusAdviseAuthorityClient,
    LotusAdviseAuthorityUnavailableError,
)
from src.infrastructure.risk_authority import (
    LotusRiskAuthorityClient,
    LotusRiskAuthorityUnavailableError,
)


def resolve_portfolio_inputs_for_request(
    *,
    request: DpmWavePreviewRequest,
    correlation_id: str,
    advise_authority_client: LotusAdviseAuthorityClient | None,
    risk_authority_client: LotusRiskAuthorityClient | None,
    campaign_definition_repository: DpmBulkReviewCampaignDefinitionRepository,
    core_resolver_factory: Callable[[], object],
) -> list[dict[str, object]]:
    if request.trigger_type == "EXPLICIT_PORTFOLIO_LIST":
        return [portfolio.model_dump(mode="json") for portfolio in request.portfolios]
    if request.trigger_type == "PM_BOOK_REVIEW":
        return resolve_pm_book_portfolios(
            request=request,
            correlation_id=correlation_id,
            core_resolver_factory=core_resolver_factory,
        )
    if request.trigger_type == "CIO_MODEL_CHANGE":
        return resolve_cio_model_change_portfolios(
            request=request,
            correlation_id=correlation_id,
            core_resolver_factory=core_resolver_factory,
        )
    if request.trigger_type == "RISK_EVENT":
        return _resolve_risk_event_portfolios(
            request=request,
            correlation_id=correlation_id,
            risk_authority_client=risk_authority_client,
        )
    if request.trigger_type == "TACTICAL_HOUSE_VIEW":
        return _resolve_tactical_house_view_portfolios(
            request=request,
            correlation_id=correlation_id,
            advise_authority_client=advise_authority_client,
        )
    if request.trigger_type == "BULK_REVIEW_CAMPAIGN":
        resolved_request = request_with_campaign_definition(
            request=request,
            repository=campaign_definition_repository,
        )
        return resolve_bulk_review_campaign_portfolios(request=resolved_request)
    return [portfolio.model_dump(mode="json") for portfolio in request.portfolios]


def _resolve_tactical_house_view_portfolios(
    *,
    request: DpmWavePreviewRequest,
    correlation_id: str,
    advise_authority_client: LotusAdviseAuthorityClient | None,
) -> list[dict[str, object]]:
    tactical_view = request.tactical_house_view
    if tactical_view is None:
        raise wave_service.DpmWaveValidationError(
            "TACTICAL_HOUSE_VIEW_REQUIRED",
            "TACTICAL_HOUSE_VIEW requires tactical_house_view source evidence.",
        )
    if not request.portfolios:
        raise wave_service.DpmWaveValidationError(
            "TACTICAL_HOUSE_VIEW_CANDIDATE_PORTFOLIOS_REQUIRED",
            "TACTICAL_HOUSE_VIEW requires source-backed candidate portfolios.",
        )
    if not tactical_view.source_refs:
        raise wave_service.DpmWaveValidationError(
            "TACTICAL_HOUSE_VIEW_SOURCE_REFS_REQUIRED",
            "TACTICAL_HOUSE_VIEW requires tactical house-view source_refs.",
        )
    if advise_authority_client is None:
        raise source_unavailable_http_exception(
            code="DPM_TACTICAL_HOUSE_VIEW_COHORT_UNAVAILABLE",
            message="DPM_ADVISE_BASE_URL is not configured.",
        )
    as_of_date = parse_wave_as_of_date(request.as_of_date)
    eligible_portfolio_types = normalize_required_portfolio_types(
        request.portfolio_types,
        required_code="TACTICAL_HOUSE_VIEW_PORTFOLIO_TYPES_REQUIRED",
        required_message="TACTICAL_HOUSE_VIEW requires at least one eligible portfolio type.",
    )

    candidate_payloads = build_tactical_house_view_candidate_payloads(request.portfolios)

    try:
        cohort = advise_authority_client.tactical_house_view_affected_cohort(
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
            candidate_portfolios=candidate_payloads,
            eligible_portfolio_types=eligible_portfolio_types,
            min_exposure_weight=(
                Decimal(str(request.min_tactical_exposure_weight))
                if request.min_tactical_exposure_weight is not None
                else None
            ),
            correlation_id=correlation_id,
        )
    except LotusAdviseAuthorityUnavailableError as exc:
        raise source_authority_unavailable_http_exception(
            exc,
            default_code="DPM_TACTICAL_HOUSE_VIEW_COHORT_UNAVAILABLE",
            rejected_code="LOTUS_ADVISE_TACTICAL_HOUSE_VIEW_COHORT_REJECTED",
        ) from exc

    if cohort.supportability_state != "READY":
        raise source_dependency_failed_http_exception(
            code="DPM_TACTICAL_HOUSE_VIEW_COHORT_EMPTY"
            if cohort.supportability_state == "EMPTY"
            else "DPM_TACTICAL_HOUSE_VIEW_COHORT_INCOMPLETE",
            message="Tactical house-view affected cohort is not source-ready.",
            reason_codes=list(cohort.supportability_reason_codes),
        )
    if not cohort.affected_portfolios:
        raise source_dependency_failed_http_exception(
            code="DPM_TACTICAL_HOUSE_VIEW_COHORT_EMPTY",
            message="Tactical house-view cohort returned no affected portfolios.",
        )

    return build_tactical_house_view_resolved_portfolios(cohort)


def _resolve_risk_event_portfolios(
    *,
    request: DpmWavePreviewRequest,
    correlation_id: str,
    risk_authority_client: LotusRiskAuthorityClient | None,
) -> list[dict[str, object]]:
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
    as_of_date = parse_wave_as_of_date(request.as_of_date)
    if risk_authority_client is None:
        raise source_unavailable_http_exception(
            code="DPM_RISK_EVENT_COHORT_UNAVAILABLE",
            message="DPM_RISK_BASE_URL is not configured.",
        )

    candidate_payloads = build_risk_event_candidate_payloads(request.portfolios)

    try:
        cohort = risk_authority_client.risk_event_affected_cohort(
            risk_event_id=risk_event_id,
            as_of_date=as_of_date,
            portfolios=candidate_payloads.risk_portfolios,
            minimum_impact_score=Decimal(str(request.minimum_impact_score)),
            correlation_id=correlation_id,
        )
    except LotusRiskAuthorityUnavailableError as exc:
        raise source_authority_unavailable_http_exception(
            exc,
            default_code="DPM_RISK_EVENT_COHORT_UNAVAILABLE",
            rejected_code="LOTUS_RISK_EVENT_COHORT_REJECTED",
        ) from exc

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

    return build_risk_event_resolved_portfolios(
        cohort=cohort,
        candidate_by_portfolio_id=candidate_payloads.candidate_by_portfolio_id,
        fallback_risk_event_id=risk_event_id,
    )
