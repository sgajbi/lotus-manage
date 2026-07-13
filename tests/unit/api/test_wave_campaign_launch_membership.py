from __future__ import annotations

import pytest

from src.api.services import wave_service
from src.api.services.wave_campaign_launch_membership import (
    _source_refs_payload,
    build_campaign_definition_launch_portfolios,
)
from src.core.waves import (
    DpmBulkReviewCampaignDefinition,
    DpmBulkReviewCampaignDefinitionCandidate,
    DpmBulkReviewCampaignDefinitionGovernance,
    DpmWaveSourceRef,
)


def _source_ref(
    *,
    source_system: str = "lotus-core",
    source_type: str = "DpmPortfolioUniverseCandidate",
    content_hash: str = "sha256:candidate",
) -> DpmWaveSourceRef:
    return DpmWaveSourceRef(
        source_system=source_system,
        source_type=source_type,
        source_id="candidate-source-pb-sg-global-bal-001",
        source_version="2026-05-10",
        supportability_state="READY",
        content_hash=content_hash,
    )


def _definition() -> DpmBulkReviewCampaignDefinition:
    return DpmBulkReviewCampaignDefinition(
        tenant_id="tenant-sg",
        campaign_id="campaign-launch-membership",
        campaign_version="2026.05",
        display_name="Launch membership campaign",
        as_of_date="2026-05-10",
        rationale="Validate launch membership publication over source-backed candidates.",
        eligible_portfolio_types=["DISCRETIONARY"],
        candidates=[
            DpmBulkReviewCampaignDefinitionCandidate(
                portfolio_id="PB_SG_GLOBAL_BAL_001",
                mandate_id="MANDATE_PB_SG_GLOBAL_BAL_001",
                portfolio_type="DISCRETIONARY",
                source_refs=[_source_ref()],
            )
        ],
        governance=DpmBulkReviewCampaignDefinitionGovernance(
            approval_ref="BRC-APPROVAL-2026-05",
            approved_by="cio_ops_committee",
            approved_at="2026-05-09T09:00:00Z",
            expires_on="2026-06-30",
            access_purpose="DPM_BULK_REVIEW_CAMPAIGN",
            entitled_actor_ids=["pm_001"],
            source_refs=[
                DpmWaveSourceRef(
                    source_system="lotus-manage",
                    source_type="AFFECTED_PORTFOLIO_MANIFEST",
                    source_id="governance-source",
                    source_version="2026-05-10",
                    supportability_state="READY",
                    content_hash="sha256:governance",
                )
            ],
        ),
        source_refs=[],
        created_by="ops",
        correlation_id="corr-campaign-launch-membership",
    )


def test_campaign_launch_membership_projects_absent_governance_diagnostics() -> None:
    definition = _definition().model_copy(update={"governance": None})

    portfolios = build_campaign_definition_launch_portfolios(
        definition=definition,
        actor_id="pm_001",
        requested_as_of_date="2026-05-10",
    )

    assert len(portfolios) == 1
    diagnostics = portfolios[0]["diagnostics"]
    assert diagnostics["campaign_governance_status"] == "NOT_SUPPLIED"
    assert diagnostics["campaign_actor_entitlement_state"] == "NOT_SUPPLIED"
    assert diagnostics["excluded_candidate_count"] == 0


@pytest.mark.parametrize(
    ("definition_update", "expected_code"),
    [
        (
            {"eligible_portfolio_types": []},
            "BULK_REVIEW_CAMPAIGN_PORTFOLIO_TYPES_REQUIRED",
        ),
        (
            {"eligible_portfolio_types": ["ADVISORY"]},
            "BULK_REVIEW_CAMPAIGN_MEMBERSHIP_EMPTY",
        ),
        (
            {"eligible_portfolio_types": [" "]},
            "BULK_REVIEW_CAMPAIGN_PORTFOLIO_TYPE_REQUIRED",
        ),
    ],
)
def test_campaign_launch_membership_rejects_invalid_portfolio_type_scope(
    definition_update: dict[str, object],
    expected_code: str,
) -> None:
    definition = _definition().model_copy(update=definition_update)

    with pytest.raises(wave_service.DpmWaveValidationError) as exc_info:
        build_campaign_definition_launch_portfolios(
            definition=definition,
            actor_id="pm_001",
            requested_as_of_date="2026-05-10",
        )

    assert exc_info.value.code == expected_code


def test_campaign_launch_membership_rejects_invalid_requested_as_of_date() -> None:
    with pytest.raises(wave_service.DpmWaveValidationError) as exc_info:
        build_campaign_definition_launch_portfolios(
            definition=_definition(),
            actor_id="pm_001",
            requested_as_of_date="2026-02-30",
        )

    assert exc_info.value.code == "WAVE_AS_OF_DATE_INVALID"


def test_campaign_launch_membership_rejects_unsupported_candidate_source_contract() -> None:
    candidate = (
        _definition()
        .candidates[0]
        .model_copy(update={"source_refs": [_source_ref(source_type="UnsupportedCandidateSource")]})
    )
    definition = _definition().model_copy(update={"candidates": [candidate]})

    with pytest.raises(wave_service.DpmWaveValidationError) as exc_info:
        build_campaign_definition_launch_portfolios(
            definition=definition,
            actor_id="pm_001",
            requested_as_of_date="2026-05-10",
        )

    assert exc_info.value.code == "BULK_REVIEW_CAMPAIGN_SOURCE_CONTRACT_UNSUPPORTED"


def test_campaign_launch_membership_source_ref_payload_requires_list_shape() -> None:
    with pytest.raises(TypeError, match="DpmWaveSourceRef payload must be a list"):
        _source_refs_payload({"source_system": "lotus-core"})
