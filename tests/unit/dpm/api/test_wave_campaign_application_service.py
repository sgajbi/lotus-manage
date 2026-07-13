from __future__ import annotations

from datetime import date

import pytest

from src.api.services.wave_campaign_application import (
    DpmCampaignDefinitionApprovalDecisionCommand,
    DpmCampaignDefinitionAssignmentActionCommand,
    DpmCampaignDefinitionAssignmentTaskOpenCommand,
    DpmCampaignDefinitionAssignmentTaskTransitionCommand,
    DpmCampaignDefinitionCreateCommand,
    DpmCampaignDefinitionMakerCheckerControlCommand,
    DpmCampaignDefinitionRetireCommand,
    DpmWaveCampaignApplicationNotFoundError,
    DpmWaveCampaignApplicationService,
)
from src.core.waves import (
    DpmBulkReviewCampaignDefinitionCandidate,
    DpmWaveSourceRef,
)
from src.infrastructure.waves import InMemoryDpmBulkReviewCampaignDefinitionRepository


class _ReadModelRepositorySpy:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []

    def list_definitions(self, **kwargs: object) -> list[object]:
        self.calls.append(("base", kwargs))
        return []

    def list_definitions_by_workflow_projection(self, **kwargs: object) -> list[object]:
        self.calls.append(("projection", kwargs))
        return []


def _service() -> DpmWaveCampaignApplicationService:
    return DpmWaveCampaignApplicationService(
        campaign_definition_repository=InMemoryDpmBulkReviewCampaignDefinitionRepository()
    )


def _create_command(
    *,
    campaign_id: str = "campaign-application-boundary",
    as_of_date: str = "2026-05-10",
) -> DpmCampaignDefinitionCreateCommand:
    return DpmCampaignDefinitionCreateCommand(
        tenant_id="tenant-sg",
        campaign_id=campaign_id,
        campaign_version="2026.05",
        display_name="Application boundary campaign",
        status="ACTIVE",
        as_of_date=as_of_date,
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
    launch_package = service.get_campaign_definition_launch_package(
        tenant_id=command.tenant_id,
        campaign_id=command.campaign_id,
        campaign_version=command.campaign_version,
        requested_as_of_date=command.as_of_date,
        actor_id="ops",
        correlation_id="corr-campaign-launch-package",
    )
    workflow_overview = service.get_campaign_definition_workflow_overview(
        tenant_id=command.tenant_id,
        campaign_id=command.campaign_id,
        campaign_version=command.campaign_version,
        requested_as_of_date=command.as_of_date,
        actor_id="ops",
        active_on=None,
        include_launch_package=True,
        correlation_id="corr-campaign-workflow-overview",
        launch_history_limit=20,
        launch_history_offset=0,
    )
    lifecycle_events = service.list_campaign_definition_lifecycle_events(
        tenant_id=command.tenant_id,
        campaign_id=command.campaign_id,
        campaign_version=command.campaign_version,
    )
    launch_history = service.list_campaign_definition_launch_history(
        tenant_id=command.tenant_id,
        campaign_id=command.campaign_id,
        campaign_version=command.campaign_version,
        limit=50,
        offset=0,
    )

    assert fetched == created
    assert listed == [created]
    assert read_model_query.definitions == [created]
    assert readiness.candidate_count == 1
    assert readiness.eligible_candidate_count == 1
    assert launch_package.campaign_id == command.campaign_id
    assert workflow_overview.campaign_id == command.campaign_id
    assert lifecycle_events.count == 1
    assert launch_history.count == 0


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


def test_campaign_application_service_records_and_lists_workflow_evidence() -> None:
    service = _service()
    command = _create_command()
    service.create_campaign_definition(command=command)

    approval_result = service.record_campaign_definition_approval_decision(
        command=DpmCampaignDefinitionApprovalDecisionCommand(
            tenant_id=command.tenant_id,
            campaign_id=command.campaign_id,
            campaign_version=command.campaign_version,
            decision_type="APPROVED",
            decision_ref="approval-001",
            decided_by="ops",
            decision_reason="Campaign approved for bounded review launch.",
            correlation_id="corr-approval-001",
            source_refs=[],
        )
    )
    assignment_result = service.record_campaign_definition_assignment_action(
        command=DpmCampaignDefinitionAssignmentActionCommand(
            tenant_id=command.tenant_id,
            campaign_id=command.campaign_id,
            campaign_version=command.campaign_version,
            action_type="ASSIGNED",
            action_ref="assignment-001",
            recorded_by="ops",
            action_reason="Assign campaign review to PM.",
            assigned_actor_ids=["pm_001"],
            escalation_tier="PM",
            sla_posture="ON_TRACK",
            correlation_id="corr-assignment-001",
            source_refs=[],
        )
    )
    task_result = service.open_campaign_definition_assignment_task(
        command=DpmCampaignDefinitionAssignmentTaskOpenCommand(
            tenant_id=command.tenant_id,
            campaign_id=command.campaign_id,
            campaign_version=command.campaign_version,
            task_ref="task-001",
            task_type="ASSIGNMENT",
            opened_by="ops",
            task_reason="PM acknowledgement required.",
            assigned_actor_ids=["pm_001"],
            escalation_tier="PM",
            sla_posture="ON_TRACK",
            due_at=None,
            correlation_id="corr-task-001",
            source_refs=[],
        )
    )
    transition_result = service.transition_campaign_definition_assignment_task(
        command=DpmCampaignDefinitionAssignmentTaskTransitionCommand(
            tenant_id=command.tenant_id,
            campaign_id=command.campaign_id,
            campaign_version=command.campaign_version,
            task_ref="task-001",
            transition_type="ACKNOWLEDGED",
            transition_ref="task-001:ack",
            transitioned_by="pm_001",
            transition_reason="Assigned PM acknowledged the campaign task.",
            assigned_actor_ids=None,
            escalation_tier=None,
            sla_posture=None,
            due_at=None,
            correlation_id="corr-task-ack-001",
            source_refs=[],
        )
    )
    maker_checker_result = service.record_campaign_definition_maker_checker_control(
        command=DpmCampaignDefinitionMakerCheckerControlCommand(
            tenant_id=command.tenant_id,
            campaign_id=command.campaign_id,
            campaign_version=command.campaign_version,
            control_action="SUBMITTED_FOR_REVIEW",
            control_ref="maker-checker-001",
            recorded_by="ops",
            submitter_actor_id="pm_001",
            reviewer_actor_id=None,
            required_reviewer_role=None,
            control_outcome="PENDING",
            control_reason="Campaign submitted for independent review.",
            correlation_id="corr-maker-checker-001",
            source_refs=[],
        )
    )

    approvals = service.list_campaign_definition_approval_decisions(
        tenant_id=command.tenant_id,
        campaign_id=command.campaign_id,
        campaign_version=command.campaign_version,
        limit=50,
        offset=0,
    )
    assignments = service.list_campaign_definition_assignment_actions(
        tenant_id=command.tenant_id,
        campaign_id=command.campaign_id,
        campaign_version=command.campaign_version,
        limit=50,
        offset=0,
    )
    tasks = service.list_campaign_definition_assignment_tasks(
        tenant_id=command.tenant_id,
        campaign_id=command.campaign_id,
        campaign_version=command.campaign_version,
        status=None,
        limit=50,
        offset=0,
    )
    maker_checker_controls = service.list_campaign_definition_maker_checker_controls(
        tenant_id=command.tenant_id,
        campaign_id=command.campaign_id,
        campaign_version=command.campaign_version,
        limit=50,
        offset=0,
    )

    assert approval_result.definition.approval_decisions
    assert assignment_result.definition.assignment_actions
    assert task_result.definition.assignment_tasks[0].status == "OPEN"
    assert transition_result.definition.assignment_tasks[0].status == "ACKNOWLEDGED"
    assert maker_checker_result.definition.maker_checker_controls
    assert not approval_result.replay
    assert approvals.count == 1
    assert assignments.count == 1
    assert tasks.count == 1
    assert maker_checker_controls.count == 1


def test_campaign_application_service_centralizes_read_model_filters_and_active_date() -> None:
    service = _service()
    service.create_campaign_definition(
        command=_create_command(
            campaign_id="campaign-active",
            as_of_date="2026-05-10",
        )
    )
    service.create_campaign_definition(
        command=_create_command(
            campaign_id="campaign-other-date",
            as_of_date="2026-05-11",
        )
    )

    query = service.load_campaign_read_model_query(
        tenant_id="tenant-sg",
        campaign_id=None,
        campaign_status="ACTIVE",
        as_of_date="2026-05-10",
        active_on=date(2026, 5, 12),
    )

    assert query.active_on == date(2026, 5, 12)
    assert [definition.campaign_id for definition in query.definitions] == ["campaign-active"]


def test_campaign_application_service_bounds_base_read_model_repository_prefix() -> None:
    repository = _ReadModelRepositorySpy()
    service = DpmWaveCampaignApplicationService(
        campaign_definition_repository=repository,  # type: ignore[arg-type]
    )

    query = service.load_campaign_read_model_query(
        tenant_id="tenant-sg",
        campaign_id=None,
        campaign_status="ACTIVE",
        as_of_date=None,
        active_on=None,
        page_limit=5,
        page_offset=2,
    )

    assert query.definitions == []
    assert repository.calls == [
        (
            "base",
            {
                "tenant_id": "tenant-sg",
                "campaign_id": None,
                "status": "ACTIVE",
                "as_of_date": None,
                "limit": 7,
                "offset": 0,
            },
        )
    ]


def test_campaign_application_service_bounds_workflow_projection_prefix() -> None:
    repository = _ReadModelRepositorySpy()
    service = DpmWaveCampaignApplicationService(
        campaign_definition_repository=repository,  # type: ignore[arg-type]
    )

    query = service.load_campaign_read_model_query(
        tenant_id="tenant-sg",
        campaign_id=None,
        campaign_status="ACTIVE",
        as_of_date=None,
        active_on=None,
        use_workflow_projection=True,
        include_closed=False,
        next_action="RECORD_APPROVAL_DECISION",
        page_limit=1,
        page_offset=1,
    )

    assert query.definitions == []
    assert repository.calls == [
        (
            "projection",
            {
                "tenant_id": "tenant-sg",
                "campaign_id": None,
                "status": "ACTIVE",
                "as_of_date": None,
                "include_closed": False,
                "board_status": None,
                "next_action": "RECORD_APPROVAL_DECISION",
                "assignment_escalation_tier": None,
                "assignment_task_status": None,
                "assigned_actor_id": None,
                "assignment_sla_posture": None,
                "maker_checker_outcome": None,
                "limit": 2,
                "offset": 0,
            },
        )
    ]
