from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import HTTPException, status

from src.api.routers.wave_campaign_candidate_selection import (
    select_bulk_review_campaign_candidates,
)
from src.api.routers.wave_campaign_governance_resolution import (
    resolve_bulk_review_campaign_governance,
)
from src.api.routers.wave_campaign_hashing import campaign_membership_hash
from src.api.routers.wave_core_portfolio_universe_resolution import (
    resolve_core_dpm_portfolio_universe_candidates,
)
from src.api.routers.wave_date_validation import parse_wave_as_of_date
from src.api.routers.wave_portfolio_type_validation import (
    normalize_required_portfolio_types,
)
from src.api.routers.wave_request_models import DpmWavePreviewRequest
from src.api.routers.wave_source_refs import (
    bulk_review_campaign_member_ref,
    bulk_review_campaign_membership_ref,
    source_refs_payload,
)
from src.api.services import wave_service


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
