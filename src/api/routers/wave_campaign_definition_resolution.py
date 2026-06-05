from __future__ import annotations

from src.api.routers.wave_campaign_models import DpmBulkReviewCampaignGovernanceInput
from src.api.routers.wave_request_models import DpmWavePortfolioInput, DpmWavePreviewRequest
from src.api.services import wave_service
from src.core.waves import (
    DpmBulkReviewCampaignDefinition,
    DpmBulkReviewCampaignDefinitionCandidate,
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
    campaign_id, campaign_version = _validate_campaign_definition_reference_request(request)
    definition = repository.get_definition(
        campaign_id=campaign_id,
        campaign_version=campaign_version,
    )
    if definition is None:
        raise wave_service.DpmWaveValidationError(
            "BULK_REVIEW_CAMPAIGN_DEFINITION_NOT_FOUND",
            "Persisted bulk-review campaign definition was not found.",
        )
    _validate_campaign_definition_available(definition=definition, request=request)
    return request.model_copy(
        update={
            "trigger_id": definition.campaign_id,
            "rationale": definition.rationale,
            "portfolios": _definition_portfolio_inputs(definition),
            "portfolio_types": definition.eligible_portfolio_types,
            "campaign_governance": _definition_governance_input(
                definition=definition,
                fallback=request.campaign_governance,
            ),
        },
        deep=True,
    )


def _validate_campaign_definition_reference_request(
    request: DpmWavePreviewRequest,
) -> tuple[str, str]:
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
    return request.campaign_definition_id, request.campaign_definition_version


def _validate_campaign_definition_available(
    *,
    definition: DpmBulkReviewCampaignDefinition,
    request: DpmWavePreviewRequest,
) -> None:
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


def _campaign_definition_source_ref(
    definition: DpmBulkReviewCampaignDefinition,
) -> DpmWaveSourceRef:
    return DpmWaveSourceRef(
        source_system="lotus-manage",
        source_type="BulkReviewCampaignDefinition",
        source_id=f"campaign-definition:{definition.campaign_id}:{definition.campaign_version}",
        source_version=definition.product_version,
        supportability_state="READY",
        content_hash=definition.content_hash,
    )


def _definition_portfolio_input(
    *,
    candidate: DpmBulkReviewCampaignDefinitionCandidate,
    definition_ref: DpmWaveSourceRef,
) -> DpmWavePortfolioInput:
    return DpmWavePortfolioInput(
        portfolio_id=candidate.portfolio_id,
        mandate_id=candidate.mandate_id,
        portfolio_manager_id=candidate.portfolio_manager_id,
        portfolio_type=candidate.portfolio_type,
        source_refs=[definition_ref, *candidate.source_refs],
    )


def _definition_portfolio_inputs(
    definition: DpmBulkReviewCampaignDefinition,
) -> list[DpmWavePortfolioInput]:
    definition_ref = _campaign_definition_source_ref(definition)
    return [
        _definition_portfolio_input(candidate=candidate, definition_ref=definition_ref)
        for candidate in definition.candidates
    ]


def _definition_governance_input(
    *,
    definition: DpmBulkReviewCampaignDefinition,
    fallback: DpmBulkReviewCampaignGovernanceInput | None,
) -> DpmBulkReviewCampaignGovernanceInput | None:
    if definition.governance is None:
        return fallback
    return DpmBulkReviewCampaignGovernanceInput.model_validate(
        definition.governance.model_dump(mode="json")
    )
