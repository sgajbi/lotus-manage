from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from src.core.waves import (
    DpmBulkReviewCampaignDefinition,
    DpmBulkReviewCampaignDefinitionCandidate,
    DpmBulkReviewCampaignDefinitionGovernance,
    DpmBulkReviewCampaignDefinitionLaunchHistoryPage,
    DpmBulkReviewCampaignDefinitionLaunchPackage,
    DpmBulkReviewCampaignDefinitionPreviewReadiness,
    DpmBulkReviewCampaignDefinitionRepository,
    DpmBulkReviewCampaignDefinitionWorkflowOverview,
    DpmWaveSourceRef,
    build_bulk_review_campaign_definition_launch_history_page,
    build_bulk_review_campaign_definition_launch_package,
    build_bulk_review_campaign_definition_preview_readiness,
    build_bulk_review_campaign_definition_workflow_overview,
)
from src.core.waves.campaign_definition_events import (
    DpmBulkReviewCampaignDefinitionLifecycleEventPage,
    build_bulk_review_campaign_definition_lifecycle_events,
)
from src.core.waves.campaign_definition_lifecycle import (
    retire_bulk_review_campaign_definition,
    supersede_bulk_review_campaign_definition,
)


class DpmWaveCampaignApplicationNotFoundError(ValueError):
    pass


@dataclass(frozen=True)
class DpmCampaignDefinitionCreateCommand:
    tenant_id: str
    campaign_id: str
    campaign_version: str
    display_name: str
    status: str
    as_of_date: str
    rationale: str
    eligible_portfolio_types: list[str]
    candidates: list[DpmBulkReviewCampaignDefinitionCandidate]
    governance: DpmBulkReviewCampaignDefinitionGovernance | None
    source_refs: list[DpmWaveSourceRef]
    created_by: str
    correlation_id: str


@dataclass(frozen=True)
class DpmCampaignDefinitionRetireCommand:
    tenant_id: str
    campaign_id: str
    campaign_version: str
    retired_by: str
    retirement_reason: str
    correlation_id: str


@dataclass(frozen=True)
class DpmCampaignDefinitionSupersedeCommand:
    tenant_id: str
    campaign_id: str
    campaign_version: str
    replacement_version: str
    superseded_by: str
    supersession_reason: str
    correlation_id: str


@dataclass(frozen=True)
class DpmBulkReviewCampaignReadModelQuery:
    definitions: list[DpmBulkReviewCampaignDefinition]
    active_on: date | None


@dataclass(frozen=True)
class DpmWaveCampaignApplicationService:
    """Campaign workflow use cases over repository ports."""

    campaign_definition_repository: DpmBulkReviewCampaignDefinitionRepository

    def create_campaign_definition(
        self,
        *,
        command: DpmCampaignDefinitionCreateCommand,
    ) -> DpmBulkReviewCampaignDefinition:
        definition = DpmBulkReviewCampaignDefinition(
            tenant_id=command.tenant_id,
            campaign_id=command.campaign_id,
            campaign_version=command.campaign_version,
            display_name=command.display_name,
            status=command.status,
            as_of_date=command.as_of_date,
            rationale=command.rationale,
            eligible_portfolio_types=command.eligible_portfolio_types,
            candidates=command.candidates,
            governance=command.governance,
            source_refs=command.source_refs,
            created_by=command.created_by,
            correlation_id=command.correlation_id,
        )
        self.campaign_definition_repository.save_definition(definition=definition)
        return definition

    def get_campaign_definition(
        self,
        *,
        tenant_id: str,
        campaign_id: str,
        campaign_version: str,
    ) -> DpmBulkReviewCampaignDefinition:
        definition = self.campaign_definition_repository.get_definition(
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            campaign_version=campaign_version,
        )
        if definition is None:
            raise DpmWaveCampaignApplicationNotFoundError(
                "BULK_REVIEW_CAMPAIGN_DEFINITION_NOT_FOUND"
            )
        return definition

    def list_campaign_definitions(
        self,
        *,
        tenant_id: str,
        campaign_id: str | None,
        campaign_status: str | None,
        as_of_date: str | None,
        limit: int,
        offset: int,
    ) -> list[DpmBulkReviewCampaignDefinition]:
        return self.campaign_definition_repository.list_definitions(
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            status=campaign_status,
            as_of_date=as_of_date,
            limit=limit,
            offset=offset,
        )

    def load_campaign_read_model_query(
        self,
        *,
        tenant_id: str,
        campaign_id: str | None,
        campaign_status: str | None,
        as_of_date: str | None,
        active_on: date | None,
        use_workflow_projection: bool = False,
        include_closed: bool = False,
        board_status: str | None = None,
        next_action: str | None = None,
        assignment_escalation_tier: str | None = None,
        assignment_task_status: str | None = None,
        assigned_actor_id: str | None = None,
        assignment_sla_posture: str | None = None,
        maker_checker_outcome: str | None = None,
    ) -> DpmBulkReviewCampaignReadModelQuery:
        if use_workflow_projection:
            definitions = self.campaign_definition_repository.list_definitions_by_workflow_projection(
                tenant_id=tenant_id,
                campaign_id=campaign_id,
                status=campaign_status,
                as_of_date=as_of_date,
                include_closed=include_closed,
                board_status=board_status,
                next_action=next_action,
                assignment_escalation_tier=assignment_escalation_tier,
                assignment_task_status=assignment_task_status,
                assigned_actor_id=assigned_actor_id,
                assignment_sla_posture=assignment_sla_posture,
                maker_checker_outcome=maker_checker_outcome,
                limit=None,
                offset=0,
            )
        else:
            definitions = self.campaign_definition_repository.list_definitions(
                tenant_id=tenant_id,
                campaign_id=campaign_id,
                status=campaign_status,
                as_of_date=as_of_date,
                limit=None,
                offset=0,
            )
        return DpmBulkReviewCampaignReadModelQuery(
            definitions=definitions,
            active_on=active_on,
        )

    def retire_campaign_definition(
        self,
        *,
        command: DpmCampaignDefinitionRetireCommand,
    ) -> DpmBulkReviewCampaignDefinition:
        retired = retire_bulk_review_campaign_definition(
            repository=self.campaign_definition_repository,
            tenant_id=command.tenant_id,
            campaign_id=command.campaign_id,
            campaign_version=command.campaign_version,
            retired_by=command.retired_by,
            retirement_reason=command.retirement_reason,
            correlation_id=command.correlation_id,
        )
        if retired is None:
            raise DpmWaveCampaignApplicationNotFoundError(
                "BULK_REVIEW_CAMPAIGN_DEFINITION_NOT_FOUND"
            )
        return retired

    def supersede_campaign_definition(
        self,
        *,
        command: DpmCampaignDefinitionSupersedeCommand,
    ) -> DpmBulkReviewCampaignDefinition:
        superseded = supersede_bulk_review_campaign_definition(
            repository=self.campaign_definition_repository,
            tenant_id=command.tenant_id,
            campaign_id=command.campaign_id,
            campaign_version=command.campaign_version,
            replacement_version=command.replacement_version,
            superseded_by=command.superseded_by,
            supersession_reason=command.supersession_reason,
            correlation_id=command.correlation_id,
        )
        if superseded is None:
            raise DpmWaveCampaignApplicationNotFoundError(
                "BULK_REVIEW_CAMPAIGN_DEFINITION_NOT_FOUND"
            )
        return superseded

    def get_campaign_definition_preview_readiness(
        self,
        *,
        tenant_id: str,
        campaign_id: str,
        campaign_version: str,
        requested_as_of_date: str,
        actor_id: str | None,
    ) -> DpmBulkReviewCampaignDefinitionPreviewReadiness:
        return build_bulk_review_campaign_definition_preview_readiness(
            definition=self.get_campaign_definition(
                tenant_id=tenant_id,
                campaign_id=campaign_id,
                campaign_version=campaign_version,
            ),
            requested_as_of_date=requested_as_of_date,
            actor_id=actor_id,
        )

    def get_campaign_definition_launch_package(
        self,
        *,
        tenant_id: str,
        campaign_id: str,
        campaign_version: str,
        requested_as_of_date: str,
        actor_id: str,
        correlation_id: str | None,
    ) -> DpmBulkReviewCampaignDefinitionLaunchPackage:
        return build_bulk_review_campaign_definition_launch_package(
            definition=self.get_campaign_definition(
                tenant_id=tenant_id,
                campaign_id=campaign_id,
                campaign_version=campaign_version,
            ),
            requested_as_of_date=requested_as_of_date,
            actor_id=actor_id,
            correlation_id=correlation_id,
        )

    def get_campaign_definition_workflow_overview(
        self,
        *,
        tenant_id: str,
        campaign_id: str,
        campaign_version: str,
        requested_as_of_date: str,
        actor_id: str | None,
        active_on: date | None,
        include_launch_package: bool,
        correlation_id: str | None,
        launch_history_limit: int,
        launch_history_offset: int,
    ) -> DpmBulkReviewCampaignDefinitionWorkflowOverview:
        return build_bulk_review_campaign_definition_workflow_overview(
            definition=self.get_campaign_definition(
                tenant_id=tenant_id,
                campaign_id=campaign_id,
                campaign_version=campaign_version,
            ),
            requested_as_of_date=requested_as_of_date,
            actor_id=actor_id,
            active_on=active_on,
            launch_history_limit=launch_history_limit,
            launch_history_offset=launch_history_offset,
            include_launch_package=include_launch_package,
            correlation_id=correlation_id,
        )

    def list_campaign_definition_lifecycle_events(
        self,
        *,
        tenant_id: str,
        campaign_id: str,
        campaign_version: str,
    ) -> DpmBulkReviewCampaignDefinitionLifecycleEventPage:
        return build_bulk_review_campaign_definition_lifecycle_events(
            definition=self.get_campaign_definition(
                tenant_id=tenant_id,
                campaign_id=campaign_id,
                campaign_version=campaign_version,
            )
        )

    def list_campaign_definition_launch_history(
        self,
        *,
        tenant_id: str,
        campaign_id: str,
        campaign_version: str,
        limit: int,
        offset: int,
    ) -> DpmBulkReviewCampaignDefinitionLaunchHistoryPage:
        return build_bulk_review_campaign_definition_launch_history_page(
            definition=self.get_campaign_definition(
                tenant_id=tenant_id,
                campaign_id=campaign_id,
                campaign_version=campaign_version,
            ),
            limit=limit,
            offset=offset,
        )
