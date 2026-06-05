from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

import pytest

from src.api.routers.wave_campaign_definition_resolution import (
    _campaign_definition_source_ref,
    _definition_governance_input,
    _definition_portfolio_inputs,
    request_with_campaign_definition,
)
from src.api.routers.wave_campaign_models import DpmBulkReviewCampaignGovernanceInput
from src.api.routers.wave_request_models import DpmWavePreviewRequest
from src.api.services.wave_errors import DpmWaveValidationError
from src.core.waves import (
    DpmBulkReviewCampaignDefinition,
    DpmBulkReviewCampaignDefinitionCandidate,
    DpmBulkReviewCampaignDefinitionGovernance,
    DpmWaveSourceRef,
)
from src.infrastructure.waves.campaign_definitions import (
    InMemoryDpmBulkReviewCampaignDefinitionRepository,
)


def _source_ref(source_id: str) -> DpmWaveSourceRef:
    return DpmWaveSourceRef(
        source_system="lotus-core",
        source_type="PortfolioCampaignMembership",
        source_id=source_id,
        source_version="v1",
        supportability_state="READY",
    )


def _definition(
    *,
    status: Literal["ACTIVE", "RETIRED", "SUPERSEDED"] = "ACTIVE",
    governance: DpmBulkReviewCampaignDefinitionGovernance | None = None,
) -> DpmBulkReviewCampaignDefinition:
    lifecycle_fields: dict[str, object] = {}
    if status == "RETIRED":
        lifecycle_fields = {
            "retired_at": datetime(2026, 5, 20, tzinfo=timezone.utc),
            "retired_by": "ops",
            "retirement_reason": "Campaign review completed.",
            "retirement_correlation_id": "corr-campaign-definition-retire-001",
        }
    return DpmBulkReviewCampaignDefinition(
        campaign_id="campaign-holdings-apple-tesla-20260510",
        campaign_version="2026.05",
        display_name="Apple and Tesla holdings review",
        status=status,
        as_of_date="2026-05-10",
        rationale="Review source-backed discretionary portfolios affected by the campaign.",
        eligible_portfolio_types=["DISCRETIONARY"],
        candidates=[
            DpmBulkReviewCampaignDefinitionCandidate(
                portfolio_id="PB_SG_GLOBAL_BAL_001",
                mandate_id="MANDATE_PB_SG_GLOBAL_BAL_001",
                portfolio_manager_id="PM_SG_DPM_001",
                portfolio_type="DISCRETIONARY",
                source_refs=[_source_ref("membership-pb-sg-global-bal-001")],
            ),
        ],
        governance=governance,
        source_refs=[
            DpmWaveSourceRef(
                source_system="lotus-manage",
                source_type="CampaignDefinitionSource",
                source_id="campaign-source-20260510",
            )
        ],
        created_by="ops",
        correlation_id="corr-campaign-definition-001",
        **lifecycle_fields,
    )


def _request(
    *,
    campaign_governance: DpmBulkReviewCampaignGovernanceInput | None = None,
) -> DpmWavePreviewRequest:
    return DpmWavePreviewRequest(
        trigger_type="BULK_REVIEW_CAMPAIGN",
        trigger_id="caller-trigger",
        rationale="Caller rationale should be replaced by the persisted definition.",
        as_of_date="2026-05-10",
        actor_id="pm_001",
        portfolios=[],
        campaign_definition_id="campaign-holdings-apple-tesla-20260510",
        campaign_definition_version="2026.05",
        campaign_governance=campaign_governance,
    )


def test_campaign_definition_source_ref_preserves_definition_identity() -> None:
    source_ref = _campaign_definition_source_ref(_definition())

    assert source_ref.source_system == "lotus-manage"
    assert source_ref.source_type == "BulkReviewCampaignDefinition"
    assert source_ref.source_id == (
        "campaign-definition:campaign-holdings-apple-tesla-20260510:2026.05"
    )
    assert source_ref.source_version == "v1"
    assert source_ref.supportability_state == "READY"
    assert source_ref.content_hash is not None
    assert source_ref.content_hash.startswith("sha256:")


def test_definition_portfolio_inputs_prepend_definition_ref_to_candidate_evidence() -> None:
    portfolios = _definition_portfolio_inputs(_definition())

    assert len(portfolios) == 1
    assert portfolios[0].portfolio_id == "PB_SG_GLOBAL_BAL_001"
    assert portfolios[0].mandate_id == "MANDATE_PB_SG_GLOBAL_BAL_001"
    assert portfolios[0].portfolio_manager_id == "PM_SG_DPM_001"
    assert portfolios[0].portfolio_type == "DISCRETIONARY"
    assert [ref.source_type for ref in portfolios[0].source_refs] == [
        "BulkReviewCampaignDefinition",
        "PortfolioCampaignMembership",
    ]


def test_definition_governance_input_uses_definition_governance_before_fallback() -> None:
    fallback = DpmBulkReviewCampaignGovernanceInput(approval_ref="fallback-approval")
    definition_governance = DpmBulkReviewCampaignDefinitionGovernance(
        approval_ref="definition-approval",
        approved_by="cio_ops_committee",
        approved_at="2026-05-14T08:30:00+08:00",
        expires_on="2026-06-30",
        entitled_actor_ids=["pm_001"],
    )

    projected = _definition_governance_input(
        definition=_definition(governance=definition_governance),
        fallback=fallback,
    )
    fallback_projected = _definition_governance_input(
        definition=_definition(governance=None),
        fallback=fallback,
    )

    assert projected is not None
    assert projected.approval_ref == "definition-approval"
    assert projected.approved_by == "cio_ops_committee"
    assert projected.entitled_actor_ids == ["pm_001"]
    assert fallback_projected is fallback


def test_request_with_campaign_definition_projects_persisted_campaign_request() -> None:
    repository = InMemoryDpmBulkReviewCampaignDefinitionRepository()
    repository.save_definition(definition=_definition())

    resolved = request_with_campaign_definition(
        request=_request(),
        repository=repository,
    )

    assert resolved.trigger_id == "campaign-holdings-apple-tesla-20260510"
    assert resolved.rationale == (
        "Review source-backed discretionary portfolios affected by the campaign."
    )
    assert resolved.portfolio_types == ["DISCRETIONARY"]
    assert resolved.portfolios[0].portfolio_id == "PB_SG_GLOBAL_BAL_001"


def test_request_with_campaign_definition_rejects_retired_definition() -> None:
    repository = InMemoryDpmBulkReviewCampaignDefinitionRepository()
    repository.save_definition(definition=_definition(status="RETIRED"))

    with pytest.raises(DpmWaveValidationError) as exc_info:
        request_with_campaign_definition(
            request=_request(),
            repository=repository,
        )

    assert exc_info.value.code == "BULK_REVIEW_CAMPAIGN_DEFINITION_RETIRED"
