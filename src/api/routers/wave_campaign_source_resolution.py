from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import Any

from fastapi import HTTPException, status

from src.api.routers.wave_campaign_candidate_selection import (
    select_bulk_review_campaign_candidates,
)
from src.api.routers.wave_campaign_governance_validation import (
    campaign_actor_entitlement_state,
    campaign_approval_status,
    campaign_expiry_state,
)
from src.api.routers.wave_campaign_hashing import (
    campaign_governance_hash,
    campaign_membership_hash,
)
from src.api.routers.wave_campaign_models import DpmBulkReviewCampaignGovernanceInput
from src.api.routers.wave_date_validation import parse_wave_as_of_date
from src.api.routers.wave_portfolio_type_validation import (
    normalize_required_portfolio_types,
)
from src.api.routers.wave_request_models import DpmWavePortfolioInput, DpmWavePreviewRequest
from src.api.routers.wave_source_refs import (
    bulk_review_campaign_member_ref,
    bulk_review_campaign_membership_ref,
    dpm_portfolio_universe_candidate_ref,
    dpm_portfolio_universe_ref,
    source_refs_payload,
)
from src.api.routers.wave_source_dependency_http import (
    source_dependency_failed_http_exception,
    upstream_dependency_failed_http_exception,
    upstream_unavailable_http_exception,
)
from src.api.services import wave_service
from src.core.waves import (
    DpmBulkReviewCampaignDefinitionRepository,
    DpmWaveSourceRef,
)
from src.infrastructure.core_sourcing import DpmCoreResolverError, DpmCoreResolverUnavailableError

MAX_CORE_DPM_PORTFOLIO_UNIVERSE_PAGES = 10


def request_with_campaign_definition(
    *,
    request: DpmWavePreviewRequest,
    repository: DpmBulkReviewCampaignDefinitionRepository,
) -> DpmWavePreviewRequest:
    if request.campaign_definition_id is None and request.campaign_definition_version is None:
        return request
    if request.campaign_candidate_source != "INLINE_SOURCE_BACKED":
        raise wave_service.DpmWaveValidationError(
            "BULK_REVIEW_CAMPAIGN_DEFINITION_REJECTS_SOURCE_DISCOVERY",
            "Persisted campaign definitions already supply the candidate portfolio set.",
        )
    if not request.campaign_definition_id or not request.campaign_definition_version:
        raise wave_service.DpmWaveValidationError(
            "BULK_REVIEW_CAMPAIGN_DEFINITION_REF_INCOMPLETE",
            "campaign_definition_id and campaign_definition_version must be supplied together.",
        )
    if request.portfolios:
        raise wave_service.DpmWaveValidationError(
            "BULK_REVIEW_CAMPAIGN_DEFINITION_REJECTS_CALLER_PORTFOLIOS",
            "Persisted campaign definitions supply the candidate portfolio set.",
        )
    definition = repository.get_definition(
        campaign_id=request.campaign_definition_id,
        campaign_version=request.campaign_definition_version,
    )
    if definition is None:
        raise wave_service.DpmWaveValidationError(
            "BULK_REVIEW_CAMPAIGN_DEFINITION_NOT_FOUND",
            "Persisted bulk-review campaign definition was not found.",
        )
    if definition.status == "RETIRED":
        raise wave_service.DpmWaveValidationError(
            "BULK_REVIEW_CAMPAIGN_DEFINITION_RETIRED",
            "Retired bulk-review campaign definitions cannot be used for new wave preview/create.",
        )
    if definition.status == "SUPERSEDED":
        raise wave_service.DpmWaveValidationError(
            "BULK_REVIEW_CAMPAIGN_DEFINITION_SUPERSEDED",
            "Superseded bulk-review campaign definitions cannot be used for new wave preview/create.",
        )
    if definition.as_of_date != request.as_of_date:
        raise wave_service.DpmWaveValidationError(
            "BULK_REVIEW_CAMPAIGN_DEFINITION_AS_OF_DATE_MISMATCH",
            "campaign definition as_of_date must match the wave request as_of_date.",
        )
    definition_ref = DpmWaveSourceRef(
        source_system="lotus-manage",
        source_type="BulkReviewCampaignDefinition",
        source_id=f"campaign-definition:{definition.campaign_id}:{definition.campaign_version}",
        source_version=definition.product_version,
        supportability_state="READY",
        content_hash=definition.content_hash,
    )
    portfolios = [
        DpmWavePortfolioInput(
            portfolio_id=candidate.portfolio_id,
            mandate_id=candidate.mandate_id,
            portfolio_manager_id=candidate.portfolio_manager_id,
            portfolio_type=candidate.portfolio_type,
            source_refs=[definition_ref, *candidate.source_refs],
        )
        for candidate in definition.candidates
    ]
    governance = (
        DpmBulkReviewCampaignGovernanceInput.model_validate(
            definition.governance.model_dump(mode="json")
        )
        if definition.governance is not None
        else request.campaign_governance
    )
    return request.model_copy(
        update={
            "trigger_id": definition.campaign_id,
            "rationale": definition.rationale,
            "portfolios": portfolios,
            "portfolio_types": definition.eligible_portfolio_types,
            "campaign_governance": governance,
        },
        deep=True,
    )


def resolve_bulk_review_campaign_portfolios(
    *,
    request: DpmWavePreviewRequest,
    correlation_id: str,
    core_resolver_factory: Callable[[], Any],
) -> list[dict[str, object]]:
    if request.campaign_candidate_source == "CORE_DPM_PORTFOLIO_UNIVERSE":
        request = request.model_copy(
            update={
                "portfolios": resolve_core_dpm_portfolio_universe_candidates(
                    request=request,
                    correlation_id=correlation_id,
                    core_resolver_factory=core_resolver_factory,
                )
            },
            deep=True,
        )
    elif not request.portfolios:
        raise wave_service.DpmWaveValidationError(
            "BULK_REVIEW_CAMPAIGN_CANDIDATE_PORTFOLIOS_REQUIRED",
            "BULK_REVIEW_CAMPAIGN requires source-backed candidate portfolios.",
        )
    elif request.campaign_candidate_source != "INLINE_SOURCE_BACKED":
        raise wave_service.DpmWaveValidationError(
            "BULK_REVIEW_CAMPAIGN_CANDIDATE_SOURCE_UNSUPPORTED",
            "BULK_REVIEW_CAMPAIGN candidate source is not supported.",
        )
    campaign_as_of_date = parse_wave_as_of_date(request.as_of_date)
    governance_diagnostics, governance_refs = resolve_bulk_review_campaign_governance(
        request=request,
        campaign_as_of_date=campaign_as_of_date,
    )
    eligible_portfolio_types = set(
        normalize_required_portfolio_types(
            request.portfolio_types,
            required_code="BULK_REVIEW_CAMPAIGN_PORTFOLIO_TYPES_REQUIRED",
            required_message=(
                "BULK_REVIEW_CAMPAIGN requires at least one eligible portfolio type."
            ),
        )
    )

    selection = select_bulk_review_campaign_candidates(
        candidates=request.portfolios,
        eligible_portfolio_types=eligible_portfolio_types,
    )
    included_candidates = selection.included_candidates

    if not included_candidates:
        raise HTTPException(
            status_code=status.HTTP_424_FAILED_DEPENDENCY,
            detail={
                "code": "BULK_REVIEW_CAMPAIGN_MEMBERSHIP_EMPTY",
                "message": "Bulk-review campaign membership returned no eligible DPM portfolios.",
            },
        )

    membership_hash = campaign_membership_hash(
        trigger_id=request.trigger_id,
        as_of_date=campaign_as_of_date,
        portfolio_types=sorted(eligible_portfolio_types),
        portfolios=[candidate.model_dump(mode="json") for candidate in included_candidates],
    )
    membership_ref = bulk_review_campaign_membership_ref(
        trigger_id=request.trigger_id,
        campaign_as_of_date=campaign_as_of_date,
        membership_hash=membership_hash,
    )
    return [
        {
            "portfolio_id": candidate.portfolio_id,
            "mandate_id": candidate.mandate_id,
            "source_refs": [
                membership_ref,
                *governance_refs,
                bulk_review_campaign_member_ref(
                    trigger_id=request.trigger_id,
                    portfolio_id=candidate.portfolio_id,
                    campaign_as_of_date=campaign_as_of_date,
                    membership_hash=membership_hash,
                ),
                *source_refs_payload(candidate.source_refs),
            ],
            "diagnostics": {
                "source_owner": "lotus-manage",
                "source_product": "BulkReviewCampaignMembership:v1",
                "campaign_id": request.trigger_id,
                "campaign_as_of_date": campaign_as_of_date.isoformat(),
                "portfolio_type": candidate.portfolio_type.strip().upper()
                if candidate.portfolio_type
                else None,
                "eligible_portfolio_types": sorted(eligible_portfolio_types),
                "excluded_candidate_count": selection.excluded_count,
                "membership_supportability_state": "READY",
                **governance_diagnostics,
            },
        }
        for candidate in included_candidates
    ]


def resolve_core_dpm_portfolio_universe_candidates(
    *,
    request: DpmWavePreviewRequest,
    correlation_id: str,
    core_resolver_factory: Callable[[], Any],
) -> list[DpmWavePortfolioInput]:
    if request.portfolios:
        raise wave_service.DpmWaveValidationError(
            "BULK_REVIEW_CAMPAIGN_CORE_UNIVERSE_REJECTS_CALLER_PORTFOLIOS",
            "Core DPM portfolio-universe discovery supplies the candidate portfolio set.",
        )
    as_of_date = parse_wave_as_of_date(request.as_of_date)
    resolver = core_resolver_factory()
    candidate_pages: list[Any] = []
    next_page_token: str | None = None
    seen_page_tokens: set[str] = set()
    try:
        for _ in range(MAX_CORE_DPM_PORTFOLIO_UNIVERSE_PAGES):
            candidate_page = resolver.resolve_dpm_portfolio_universe_candidates(
                as_of_date=as_of_date,
                tenant_id=request.tenant_id,
                booking_center_code=request.booking_center_code,
                model_portfolio_ids=request.model_portfolio_ids,
                include_inactive_mandates=request.include_inactive_mandates,
                page_size=request.campaign_candidate_page_size,
                page_token=next_page_token,
                correlation_id=correlation_id,
            )
            candidate_pages.append(candidate_page)
            if candidate_page.supportability.state != "READY":
                break
            next_page_token = candidate_page.page.next_page_token
            if not next_page_token:
                break
            if next_page_token in seen_page_tokens:
                raise DpmCoreResolverError("DPM_CORE_PORTFOLIO_UNIVERSE_NON_TERMINATING")
            seen_page_tokens.add(next_page_token)
        else:
            raise DpmCoreResolverError("DPM_CORE_PORTFOLIO_UNIVERSE_NON_TERMINATING")
    except DpmCoreResolverUnavailableError as exc:
        raise upstream_unavailable_http_exception(
            exc,
            default_code="DPM_CORE_PORTFOLIO_UNIVERSE_UNAVAILABLE",
        ) from exc
    except DpmCoreResolverError as exc:
        raise upstream_dependency_failed_http_exception(
            exc,
            default_code="DPM_CORE_PORTFOLIO_UNIVERSE_INCOMPLETE",
        ) from exc

    candidate_page = candidate_pages[-1]
    if candidate_page.supportability.state != "READY":
        raise source_dependency_failed_http_exception(
            code=candidate_page.supportability.reason,
            message="Core DPM portfolio-universe candidates are not source-ready.",
        )
    if next_page_token or candidate_page.supportability.page_truncated:
        raise source_dependency_failed_http_exception(
            code="DPM_CORE_PORTFOLIO_UNIVERSE_PAGE_PARTIAL",
            message=(
                "Core DPM portfolio-universe candidates could not be exhausted within the "
                "bounded Manage consumer guard; refine filters before creating a campaign wave."
            ),
        )
    candidates = [candidate for page in candidate_pages for candidate in page.candidates]
    if not candidates:
        raise source_dependency_failed_http_exception(
            code="DPM_CORE_PORTFOLIO_UNIVERSE_EMPTY",
            message="Core DPM portfolio-universe discovery returned no candidate portfolios.",
        )
    candidate_keys: set[tuple[str, str | None, str | None]] = set()
    for candidate in candidates:
        candidate_key = (
            candidate.portfolio_id,
            candidate.mandate_id,
            candidate.source_record_id,
        )
        if candidate_key in candidate_keys:
            raise source_dependency_failed_http_exception(
                code="DPM_CORE_PORTFOLIO_UNIVERSE_DUPLICATE_CANDIDATE",
                message=(
                    "Core DPM portfolio-universe discovery returned duplicate candidate rows."
                ),
            )
        candidate_keys.add(candidate_key)

    first_page = candidate_pages[0]
    selection_basis = (
        first_page.selection_basis.model_dump(mode="json")
        if first_page.selection_basis is not None
        else None
    )
    universe_ref = dpm_portfolio_universe_ref(
        source_id=first_page.snapshot_id or first_page.page.request_scope_fingerprint,
        product_version=first_page.product_version,
        supportability_state=first_page.supportability.state,
        content_hash=first_page.source_batch_fingerprint,
    )
    return [
        DpmWavePortfolioInput(
            portfolio_id=candidate.portfolio_id,
            mandate_id=candidate.mandate_id,
            portfolio_type="DISCRETIONARY",
            source_refs=[
                DpmWaveSourceRef.model_validate(universe_ref),
                DpmWaveSourceRef.model_validate(
                    dpm_portfolio_universe_candidate_ref(
                        source_record_id=candidate.source_record_id,
                        portfolio_id=candidate.portfolio_id,
                        mandate_id=candidate.mandate_id,
                        binding_version=candidate.binding_version,
                        selection_basis=selection_basis,
                    )
                ),
            ],
        )
        for candidate in candidates
    ]


def resolve_bulk_review_campaign_governance(
    *,
    request: DpmWavePreviewRequest,
    campaign_as_of_date: date,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    governance = request.campaign_governance
    if governance is None:
        return (
            {
                "campaign_governance_status": "NOT_SUPPLIED",
                "campaign_access_purpose": None,
                "campaign_expiry_state": "NOT_SUPPLIED",
                "campaign_actor_entitlement_state": "NOT_SUPPLIED",
            },
            [],
        )

    approval_status = campaign_approval_status(
        approval_ref=governance.approval_ref,
        approved_by=governance.approved_by,
        approved_at=governance.approved_at,
    )
    expiry_state = campaign_expiry_state(
        expires_on=governance.expires_on,
        campaign_as_of_date=campaign_as_of_date,
    )
    actor_entitlement_state = campaign_actor_entitlement_state(
        entitled_actor_ids=governance.entitled_actor_ids,
        actor_id=request.actor_id,
    )

    governance_hash = campaign_governance_hash(
        trigger_id=request.trigger_id,
        actor_id=request.actor_id,
        governance=governance.model_dump(mode="json"),
    )
    governance_refs: list[dict[str, object]] = [
        {
            "source_system": "lotus-manage",
            "source_type": "BulkReviewCampaignGovernance",
            "source_id": f"campaign-governance:{request.trigger_id}",
            "source_version": governance.approved_at or campaign_as_of_date.isoformat(),
            "supportability_state": "READY",
            "content_hash": governance_hash,
        },
        *source_refs_payload(governance.source_refs),
    ]
    return (
        {
            "campaign_governance_status": approval_status,
            "campaign_approval_ref": governance.approval_ref,
            "campaign_approved_by": governance.approved_by,
            "campaign_approved_at": governance.approved_at,
            "campaign_access_purpose": governance.access_purpose,
            "campaign_expiry_state": expiry_state,
            "campaign_expires_on": governance.expires_on,
            "campaign_actor_entitlement_state": actor_entitlement_state,
        },
        governance_refs,
    )
