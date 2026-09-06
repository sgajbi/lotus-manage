from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from src.api.services import wave_service
from src.api.services.wave_campaign_launch_membership import (
    build_campaign_definition_launch_portfolios,
)
from src.core.mandate_repository import DpmMandateRepository
from src.core.waves import (
    CampaignApprovalDecisionType,
    CampaignAssignmentActionType,
    CampaignAssignmentEscalationTier,
    CampaignAssignmentSlaPosture,
    CampaignAssignmentTaskStatus,
    CampaignAssignmentTaskTransitionType,
    CampaignAssignmentTaskType,
    CampaignDefinitionStatus,
    CampaignMakerCheckerControlAction,
    CampaignMakerCheckerControlOutcome,
    DpmBulkReviewCampaignDefinition,
    DpmBulkReviewCampaignDefinitionApprovalDecisionPage,
    DpmBulkReviewCampaignDefinitionAssignmentActionPage,
    DpmBulkReviewCampaignDefinitionAssignmentTaskPage,
    DpmBulkReviewCampaignDefinitionCandidate,
    DpmBulkReviewCampaignDefinitionGovernance,
    DpmBulkReviewCampaignDefinitionLaunchHistoryPage,
    DpmBulkReviewCampaignDefinitionLaunchPackage,
    DpmBulkReviewCampaignDefinitionMakerCheckerControlPage,
    DpmBulkReviewCampaignDefinitionPreviewReadiness,
    DpmBulkReviewCampaignDefinitionRepository,
    DpmBulkReviewCampaignDefinitionWorkflowOverview,
    DpmRebalanceWave,
    DpmWaveRepository,
    DpmWaveSourceRef,
    build_bulk_review_campaign_definition_approval_decision_page,
    build_bulk_review_campaign_definition_assignment_action_page,
    build_bulk_review_campaign_definition_assignment_task_page,
    build_bulk_review_campaign_definition_launch_command,
    build_bulk_review_campaign_definition_launch_history_page,
    build_bulk_review_campaign_definition_launch_package,
    build_bulk_review_campaign_definition_maker_checker_control_page,
    build_bulk_review_campaign_definition_preview_readiness,
    build_bulk_review_campaign_definition_workflow_overview,
    open_bulk_review_campaign_definition_assignment_task,
    record_bulk_review_campaign_definition_approval_decision,
    record_bulk_review_campaign_definition_assignment_action,
    record_bulk_review_campaign_definition_launch,
    record_bulk_review_campaign_definition_maker_checker_control,
    transition_bulk_review_campaign_definition_assignment_task,
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
    status: CampaignDefinitionStatus
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


def _read_model_repository_limit(*, page_limit: int | None, page_offset: int) -> int | None:
    if page_limit is None:
        return None
    return page_limit + page_offset


@dataclass(frozen=True)
class DpmCampaignDefinitionApprovalDecisionCommand:
    tenant_id: str
    campaign_id: str
    campaign_version: str
    decision_type: CampaignApprovalDecisionType
    decision_ref: str
    decided_by: str
    decision_reason: str
    correlation_id: str
    source_refs: list[DpmWaveSourceRef]


@dataclass(frozen=True)
class DpmCampaignDefinitionAssignmentActionCommand:
    tenant_id: str
    campaign_id: str
    campaign_version: str
    action_type: CampaignAssignmentActionType
    action_ref: str
    recorded_by: str
    action_reason: str
    assigned_actor_ids: list[str]
    escalation_tier: CampaignAssignmentEscalationTier
    sla_posture: CampaignAssignmentSlaPosture
    correlation_id: str
    source_refs: list[DpmWaveSourceRef]


@dataclass(frozen=True)
class DpmCampaignDefinitionAssignmentTaskOpenCommand:
    tenant_id: str
    campaign_id: str
    campaign_version: str
    task_ref: str
    task_type: CampaignAssignmentTaskType
    opened_by: str
    task_reason: str
    assigned_actor_ids: list[str]
    escalation_tier: CampaignAssignmentEscalationTier
    sla_posture: CampaignAssignmentSlaPosture
    due_at: datetime | None
    correlation_id: str
    source_refs: list[DpmWaveSourceRef]


@dataclass(frozen=True)
class DpmCampaignDefinitionAssignmentTaskTransitionCommand:
    tenant_id: str
    campaign_id: str
    campaign_version: str
    task_ref: str
    transition_type: CampaignAssignmentTaskTransitionType
    transition_ref: str
    transitioned_by: str
    transition_reason: str
    assigned_actor_ids: list[str] | None
    escalation_tier: CampaignAssignmentEscalationTier | None
    sla_posture: CampaignAssignmentSlaPosture | None
    due_at: datetime | None
    correlation_id: str
    source_refs: list[DpmWaveSourceRef]


@dataclass(frozen=True)
class DpmCampaignDefinitionMakerCheckerControlCommand:
    tenant_id: str
    campaign_id: str
    campaign_version: str
    control_action: CampaignMakerCheckerControlAction
    control_ref: str
    recorded_by: str
    submitter_actor_id: str | None
    reviewer_actor_id: str | None
    required_reviewer_role: str | None
    control_outcome: CampaignMakerCheckerControlOutcome
    control_reason: str
    correlation_id: str
    source_refs: list[DpmWaveSourceRef]


@dataclass(frozen=True)
class DpmCampaignDefinitionLaunchCommand:
    tenant_id: str
    campaign_id: str
    campaign_version: str
    requested_as_of_date: str
    actor_id: str
    correlation_id: str | None


@dataclass(frozen=True)
class DpmCampaignDefinitionWriteResult:
    definition: DpmBulkReviewCampaignDefinition
    replay: bool


@dataclass(frozen=True)
class DpmCampaignDefinitionLaunchResult:
    wave: DpmRebalanceWave
    replay: bool


@dataclass(frozen=True)
class DpmWaveCampaignApplicationService:
    """Campaign workflow use cases over repository ports."""

    campaign_definition_repository: DpmBulkReviewCampaignDefinitionRepository

    def _persisted_campaign_definition(
        self,
        persisted: DpmBulkReviewCampaignDefinition | None,
    ) -> DpmBulkReviewCampaignDefinition:
        if persisted is None:
            raise DpmWaveCampaignApplicationNotFoundError(
                "BULK_REVIEW_CAMPAIGN_DEFINITION_NOT_FOUND"
            )
        return persisted

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
        page_limit: int | None = None,
        page_offset: int = 0,
    ) -> DpmBulkReviewCampaignReadModelQuery:
        repository_limit = _read_model_repository_limit(
            page_limit=page_limit,
            page_offset=page_offset,
        )
        if use_workflow_projection:
            definitions = (
                self.campaign_definition_repository.list_definitions_by_workflow_projection(
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
                    limit=repository_limit,
                    offset=0,
                )
            )
        else:
            definitions = self.campaign_definition_repository.list_definitions(
                tenant_id=tenant_id,
                campaign_id=campaign_id,
                status=campaign_status,
                as_of_date=as_of_date,
                limit=repository_limit,
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

    def record_campaign_definition_approval_decision(
        self,
        *,
        command: DpmCampaignDefinitionApprovalDecisionCommand,
    ) -> DpmCampaignDefinitionWriteResult:
        definition = self.get_campaign_definition(
            tenant_id=command.tenant_id,
            campaign_id=command.campaign_id,
            campaign_version=command.campaign_version,
        )
        updated = record_bulk_review_campaign_definition_approval_decision(
            definition=definition,
            decision_type=command.decision_type,
            decision_ref=command.decision_ref,
            decided_by=command.decided_by,
            decision_reason=command.decision_reason,
            correlation_id=command.correlation_id,
            source_refs=command.source_refs,
        )
        persisted = self.campaign_definition_repository.record_definition_approval_decision(
            definition=updated,
            expected_content_hash=definition.content_hash,
        )
        return DpmCampaignDefinitionWriteResult(
            definition=self._persisted_campaign_definition(persisted),
            replay=updated is definition,
        )

    def list_campaign_definition_approval_decisions(
        self,
        *,
        tenant_id: str,
        campaign_id: str,
        campaign_version: str,
        limit: int,
        offset: int,
    ) -> DpmBulkReviewCampaignDefinitionApprovalDecisionPage:
        return build_bulk_review_campaign_definition_approval_decision_page(
            definition=self.get_campaign_definition(
                tenant_id=tenant_id,
                campaign_id=campaign_id,
                campaign_version=campaign_version,
            ),
            limit=limit,
            offset=offset,
        )

    def record_campaign_definition_assignment_action(
        self,
        *,
        command: DpmCampaignDefinitionAssignmentActionCommand,
    ) -> DpmCampaignDefinitionWriteResult:
        definition = self.get_campaign_definition(
            tenant_id=command.tenant_id,
            campaign_id=command.campaign_id,
            campaign_version=command.campaign_version,
        )
        updated = record_bulk_review_campaign_definition_assignment_action(
            definition=definition,
            action_type=command.action_type,
            action_ref=command.action_ref,
            recorded_by=command.recorded_by,
            action_reason=command.action_reason,
            assigned_actor_ids=command.assigned_actor_ids,
            escalation_tier=command.escalation_tier,
            sla_posture=command.sla_posture,
            correlation_id=command.correlation_id,
            source_refs=command.source_refs,
        )
        persisted = self.campaign_definition_repository.record_definition_assignment_action(
            definition=updated,
            expected_content_hash=definition.content_hash,
        )
        return DpmCampaignDefinitionWriteResult(
            definition=self._persisted_campaign_definition(persisted),
            replay=updated is definition,
        )

    def list_campaign_definition_assignment_actions(
        self,
        *,
        tenant_id: str,
        campaign_id: str,
        campaign_version: str,
        limit: int,
        offset: int,
    ) -> DpmBulkReviewCampaignDefinitionAssignmentActionPage:
        return build_bulk_review_campaign_definition_assignment_action_page(
            definition=self.get_campaign_definition(
                tenant_id=tenant_id,
                campaign_id=campaign_id,
                campaign_version=campaign_version,
            ),
            limit=limit,
            offset=offset,
        )

    def open_campaign_definition_assignment_task(
        self,
        *,
        command: DpmCampaignDefinitionAssignmentTaskOpenCommand,
    ) -> DpmCampaignDefinitionWriteResult:
        definition = self.get_campaign_definition(
            tenant_id=command.tenant_id,
            campaign_id=command.campaign_id,
            campaign_version=command.campaign_version,
        )
        updated = open_bulk_review_campaign_definition_assignment_task(
            definition=definition,
            task_ref=command.task_ref,
            task_type=command.task_type,
            opened_by=command.opened_by,
            task_reason=command.task_reason,
            assigned_actor_ids=command.assigned_actor_ids,
            escalation_tier=command.escalation_tier,
            sla_posture=command.sla_posture,
            due_at=command.due_at,
            correlation_id=command.correlation_id,
            source_refs=command.source_refs,
        )
        persisted = self.campaign_definition_repository.record_definition_assignment_task(
            definition=updated,
            expected_content_hash=definition.content_hash,
        )
        return DpmCampaignDefinitionWriteResult(
            definition=self._persisted_campaign_definition(persisted),
            replay=updated is definition,
        )

    def transition_campaign_definition_assignment_task(
        self,
        *,
        command: DpmCampaignDefinitionAssignmentTaskTransitionCommand,
    ) -> DpmCampaignDefinitionWriteResult:
        definition = self.get_campaign_definition(
            tenant_id=command.tenant_id,
            campaign_id=command.campaign_id,
            campaign_version=command.campaign_version,
        )
        updated = transition_bulk_review_campaign_definition_assignment_task(
            definition=definition,
            task_ref=command.task_ref,
            transition_type=command.transition_type,
            transition_ref=command.transition_ref,
            transitioned_by=command.transitioned_by,
            transition_reason=command.transition_reason,
            assigned_actor_ids=command.assigned_actor_ids,
            escalation_tier=command.escalation_tier,
            sla_posture=command.sla_posture,
            due_at=command.due_at,
            correlation_id=command.correlation_id,
            source_refs=command.source_refs,
        )
        persisted = self.campaign_definition_repository.record_definition_assignment_task(
            definition=updated,
            expected_content_hash=definition.content_hash,
        )
        return DpmCampaignDefinitionWriteResult(
            definition=self._persisted_campaign_definition(persisted),
            replay=updated is definition,
        )

    def list_campaign_definition_assignment_tasks(
        self,
        *,
        tenant_id: str,
        campaign_id: str,
        campaign_version: str,
        status: CampaignAssignmentTaskStatus | None,
        limit: int,
        offset: int,
    ) -> DpmBulkReviewCampaignDefinitionAssignmentTaskPage:
        return build_bulk_review_campaign_definition_assignment_task_page(
            definition=self.get_campaign_definition(
                tenant_id=tenant_id,
                campaign_id=campaign_id,
                campaign_version=campaign_version,
            ),
            status_filter=status,
            limit=limit,
            offset=offset,
        )

    def record_campaign_definition_maker_checker_control(
        self,
        *,
        command: DpmCampaignDefinitionMakerCheckerControlCommand,
    ) -> DpmCampaignDefinitionWriteResult:
        definition = self.get_campaign_definition(
            tenant_id=command.tenant_id,
            campaign_id=command.campaign_id,
            campaign_version=command.campaign_version,
        )
        updated = record_bulk_review_campaign_definition_maker_checker_control(
            definition=definition,
            control_action=command.control_action,
            control_ref=command.control_ref,
            recorded_by=command.recorded_by,
            submitter_actor_id=command.submitter_actor_id,
            reviewer_actor_id=command.reviewer_actor_id,
            required_reviewer_role=command.required_reviewer_role,
            control_outcome=command.control_outcome,
            control_reason=command.control_reason,
            correlation_id=command.correlation_id,
            source_refs=command.source_refs,
        )
        persisted = self.campaign_definition_repository.record_definition_maker_checker_control(
            definition=updated,
            expected_content_hash=definition.content_hash,
        )
        return DpmCampaignDefinitionWriteResult(
            definition=self._persisted_campaign_definition(persisted),
            replay=updated is definition,
        )

    def list_campaign_definition_maker_checker_controls(
        self,
        *,
        tenant_id: str,
        campaign_id: str,
        campaign_version: str,
        limit: int,
        offset: int,
    ) -> DpmBulkReviewCampaignDefinitionMakerCheckerControlPage:
        return build_bulk_review_campaign_definition_maker_checker_control_page(
            definition=self.get_campaign_definition(
                tenant_id=tenant_id,
                campaign_id=campaign_id,
                campaign_version=campaign_version,
            ),
            limit=limit,
            offset=offset,
        )

    def launch_campaign_definition(
        self,
        *,
        command: DpmCampaignDefinitionLaunchCommand,
        mandate_repository: DpmMandateRepository,
        wave_repository: DpmWaveRepository,
    ) -> DpmCampaignDefinitionLaunchResult:
        definition = self.get_campaign_definition(
            tenant_id=command.tenant_id,
            campaign_id=command.campaign_id,
            campaign_version=command.campaign_version,
        )
        launch_command = build_bulk_review_campaign_definition_launch_command(
            definition=definition,
            requested_as_of_date=command.requested_as_of_date,
            actor_id=command.actor_id,
            correlation_id=command.correlation_id,
        )
        wave_request = launch_command.create_request
        portfolios = build_campaign_definition_launch_portfolios(
            definition=definition,
            actor_id=wave_request.actor_id,
            requested_as_of_date=wave_request.as_of_date,
        )
        wave, replay = wave_service.create_wave(
            tenant_id=command.tenant_id,
            trigger_type=wave_request.trigger_type,
            trigger_id=wave_request.trigger_id,
            rationale=wave_request.rationale,
            as_of_date=wave_request.as_of_date,
            actor_id=wave_request.actor_id,
            correlation_id=launch_command.correlation_id,
            portfolios=portfolios,
            idempotency_key=launch_command.idempotency_key,
            mandate_repository=mandate_repository,
            wave_repository=wave_repository,
        )
        launched_definition = record_bulk_review_campaign_definition_launch(
            definition=definition,
            wave_id=wave.wave_id,
            launched_by=wave_request.actor_id,
            requested_as_of_date=wave_request.as_of_date,
            correlation_id=launch_command.correlation_id,
            idempotency_key=launch_command.idempotency_key,
        )
        if launched_definition.content_hash != definition.content_hash:
            self.campaign_definition_repository.record_definition_launch(
                definition=launched_definition,
                expected_content_hash=definition.content_hash,
            )
        return DpmCampaignDefinitionLaunchResult(wave=wave, replay=replay)
