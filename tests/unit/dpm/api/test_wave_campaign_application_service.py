from __future__ import annotations

from pathlib import Path

import pytest

from src.api.services.wave_campaign_application import (
    DpmCampaignDefinitionCreateCommand,
    DpmCampaignDefinitionRetireCommand,
    DpmWaveCampaignApplicationNotFoundError,
    DpmWaveCampaignApplicationService,
)
from src.core.waves import (
    DpmBulkReviewCampaignDefinitionCandidate,
    DpmWaveSourceRef,
)
from src.infrastructure.waves import InMemoryDpmBulkReviewCampaignDefinitionRepository


def _service() -> DpmWaveCampaignApplicationService:
    return DpmWaveCampaignApplicationService(
        campaign_definition_repository=InMemoryDpmBulkReviewCampaignDefinitionRepository()
    )


def _create_command() -> DpmCampaignDefinitionCreateCommand:
    return DpmCampaignDefinitionCreateCommand(
        tenant_id="tenant-sg",
        campaign_id="campaign-application-boundary",
        campaign_version="2026.05",
        display_name="Application boundary campaign",
        status="ACTIVE",
        as_of_date="2026-05-10",
        rationale="Validate campaign application service orchestration.",
        eligible_portfolio_types=["DISCRETIONARY"],
        candidates=[
            DpmBulkReviewCampaignDefinitionCandidate(
                portfolio_id="PB_SG_GLOBAL_BAL_001",
                mandate_id="MANDATE_PB_SG_GLOBAL_BAL_001",
                portfolio_type="DISCRETIONARY",
                source_refs=[
                    DpmWaveSourceRef(
                        source_system="lotus-manage",
                        source_type="AFFECTED_PORTFOLIO_MANIFEST",
                        source_id="campaign-application-boundary:PB_SG_GLOBAL_BAL_001",
                        source_version="v1",
                        supportability_state="READY",
                        content_hash="sha256:campaign-application-boundary",
                    )
                ],
            )
        ],
        governance=None,
        source_refs=[],
        created_by="ops",
        correlation_id="corr-campaign-application-boundary",
    )


def test_campaign_application_service_creates_lists_reads_and_checks_readiness() -> None:
    service = _service()
    command = _create_command()

    created = service.create_campaign_definition(command=command)
    fetched = service.get_campaign_definition(
        tenant_id=command.tenant_id,
        campaign_id=command.campaign_id,
        campaign_version=command.campaign_version,
    )
    listed = service.list_campaign_definitions(
        tenant_id=command.tenant_id,
        campaign_id=command.campaign_id,
        campaign_status="ACTIVE",
        as_of_date=command.as_of_date,
        limit=50,
        offset=0,
    )
    readiness = service.get_campaign_definition_preview_readiness(
        tenant_id=command.tenant_id,
        campaign_id=command.campaign_id,
        campaign_version=command.campaign_version,
        requested_as_of_date=command.as_of_date,
        actor_id=None,
    )
    read_model_query = service.load_campaign_read_model_query(
        tenant_id=command.tenant_id,
        campaign_id=command.campaign_id,
        campaign_status="ACTIVE",
        as_of_date=command.as_of_date,
        active_on=None,
    )

    assert fetched == created
    assert listed == [created]
    assert read_model_query.definitions == [created]
    assert readiness.candidate_count == 1
    assert readiness.eligible_candidate_count == 1


def test_campaign_application_service_retires_and_raises_not_found() -> None:
    service = _service()
    command = _create_command()
    service.create_campaign_definition(command=command)

    retired = service.retire_campaign_definition(
        command=DpmCampaignDefinitionRetireCommand(
            tenant_id=command.tenant_id,
            campaign_id=command.campaign_id,
            campaign_version=command.campaign_version,
            retired_by="ops",
            retirement_reason="Campaign closed.",
            correlation_id="corr-campaign-application-retire",
        )
    )

    assert retired.status == "RETIRED"
    with pytest.raises(DpmWaveCampaignApplicationNotFoundError):
        service.get_campaign_definition(
            tenant_id=command.tenant_id,
            campaign_id="missing-campaign",
            campaign_version=command.campaign_version,
        )


def test_campaign_definition_routes_depend_on_application_service_boundary() -> None:
    route_paths = [
        Path("src/api/routers/wave_campaign_definition_routes.py"),
        Path("src/api/routers/wave_campaign_definition_lifecycle_routes.py"),
        Path("src/api/routers/wave_campaign_readiness_routes.py"),
        Path("src/api/routers/wave_campaign_discovery_routes.py"),
        Path("src/api/routers/wave_campaign_operating_queue_routes.py"),
        Path("src/api/routers/wave_campaign_approval_inbox_routes.py"),
    ]

    for route_path in route_paths:
        source = route_path.read_text(encoding="utf-8")
        assert "get_wave_campaign_application_service" in source
        assert "get_campaign_definition_repository" not in source
        assert "DpmBulkReviewCampaignDefinitionRepository" not in source
