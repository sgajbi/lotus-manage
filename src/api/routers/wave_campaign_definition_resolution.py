from __future__ import annotations

from src.api.routers.wave_campaign_models import DpmBulkReviewCampaignGovernanceInput
from src.api.routers.wave_request_models import DpmWavePortfolioInput, DpmWavePreviewRequest
from src.api.services import wave_service
from src.core.waves import (
    DpmBulkReviewCampaignDefinitionRepository,
    DpmWaveSourceRef,
)


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
