from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status

from src.api.dependencies import get_wave_campaign_application_service
from src.api.routers.wave_campaign_definition_errors import (
    parse_optional_campaign_discovery_date,
)
from src.api.routers.wave_campaign_trusted_context import (
    CampaignTrustedContext,
    campaign_trusted_context_required,
)
from src.api.services.wave_campaign_application import DpmWaveCampaignApplicationService
from src.api.routers.wave_route_parameters import (
    CampaignActiveOnQuery,
    CampaignActorIdQuery,
    CampaignDefinitionAsOfDateQuery,
    CampaignDefinitionFilterIdQuery,
    CampaignDefinitionStatusQuery,
    CampaignIncludeClosedQuery,
    CampaignReadModelLimitQuery,
    CampaignReadModelOffsetQuery,
    CampaignRequestedAsOfDateQuery,
)
from src.core.waves import (
    CampaignWorkflowAutomationAction,
    CampaignWorkflowAutomationStatus,
    DpmBulkReviewCampaignWorkflowAutomationPage,
    build_bulk_review_campaign_workflow_automation_page,
)

router = APIRouter()

WORKFLOW_AUTOMATION_RESPONSE_EXAMPLE = {
    "product_name": "BulkReviewCampaignWorkflowAutomation",
    "product_version": "v1",
    "items": [],
    "limit": 50,
    "offset": 0,
    "count": 0,
    "automation_status_counts": {},
    "automation_action_counts": {},
    "capability_posture": {
        "product_name": "BulkReviewCampaignWorkflowCapabilityPosture",
        "product_version": "v1",
        "manage_assignment_task_readiness": "SUPPORTED",
        "manage_assignment_task_mutation": "CONTROLLED_ENDPOINT_ONLY",
        "external_workflow_orchestration": "UNSUPPORTED",
        "external_workflow_events_projected": False,
        "external_workflow_owner_posture": "DEFERRED_SOURCE_OWNER",
        "required_source_product": "ExternalWorkflowOrchestrationRecord:v1",
        "blocked_capabilities": [
            "external_workflow_task_creation",
            "external_workflow_task_assignment",
            "external_workflow_task_synchronization",
            "external_workflow_task_escalation",
            "external_workflow_task_completion",
        ],
        "promotion_requirements": [
            "certified_external_workflow_source_owner",
            "ExternalWorkflowOrchestrationRecord:v1",
            "gateway_workbench_external_workflow_contracts",
            "source_safe_lineage_and_audit_evidence",
        ],
        "controlled_assignment_task_endpoint": (
            "/api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/"
            "{campaign_version}/assignment-tasks"
        ),
        "operating_boundaries": [
            "no_external_workflow_orchestration",
            "no_external_workflow_task_projection",
            "no_order_generation",
            "no_client_contact",
            "no_oms_execution_claim",
        ],
        "content_hash": "sha256:workflow-capability-posture-example",
    },
    "content_hash": "sha256:workflow-automation-page-example",
}


@router.get(
    "/campaign-workflow-automation",
    response_model=DpmBulkReviewCampaignWorkflowAutomationPage,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": (
                "Read-only campaign workflow automation page with explicit Manage task "
                "readiness and unsupported external-workflow posture."
            ),
            "content": {
                "application/json": {
                    "example": WORKFLOW_AUTOMATION_RESPONSE_EXAMPLE,
                }
            },
        },
    },
    summary="List bulk-review campaign workflow automation readiness",
    description=(
        "Returns read-only Manage-side workflow automation readiness over persisted "
        "`BulkReviewCampaignDefinition:v1` records. The projection composes the assignment plan "
        "with existing controlled assignment-task state to identify where Manage may safely "
        "propose opening, monitoring, or escalating its own assignment tasks. It does not mutate "
        "tasks, orchestrate external workflow, discover the global portfolio universe, "
        "recalculate source facts, mutate approval state, mutate maker-checker control state, "
        "contact clients, approve trades, generate orders, or claim OMS execution. The response "
        "includes `capability_posture` so consumers can distinguish supported Manage assignment "
        "readiness from unsupported external workflow orchestration even when the page is empty; "
        "that posture names blocked external workflow capabilities, the required future "
        "`ExternalWorkflowOrchestrationRecord:v1` source product, promotion requirements for "
        "future source-owner/downstream realization, and a deterministic content hash."
    ),
)
def list_bulk_review_campaign_workflow_automation(
    campaign_id: CampaignDefinitionFilterIdQuery = None,
    campaign_status: CampaignDefinitionStatusQuery = None,
    as_of_date: CampaignDefinitionAsOfDateQuery = None,
    requested_as_of_date: CampaignRequestedAsOfDateQuery = None,
    actor_id: CampaignActorIdQuery = None,
    active_on: CampaignActiveOnQuery = None,
    automation_status: CampaignWorkflowAutomationStatus | None = Query(
        default=None,
        description="Optional filter for one Manage-side automation posture.",
    ),
    automation_action: CampaignWorkflowAutomationAction | None = Query(
        default=None,
        description="Optional filter for one proposed Manage-side automation action.",
    ),
    include_closed: CampaignIncludeClosedQuery = False,
    limit: CampaignReadModelLimitQuery = 50,
    offset: CampaignReadModelOffsetQuery = 0,
    trusted_context: CampaignTrustedContext = Depends(campaign_trusted_context_required),
    application_service: DpmWaveCampaignApplicationService = Depends(
        get_wave_campaign_application_service
    ),
) -> DpmBulkReviewCampaignWorkflowAutomationPage:
    campaign_query = application_service.load_campaign_read_model_query(
        tenant_id=trusted_context.tenant_id,
        campaign_id=campaign_id,
        campaign_status=campaign_status,
        as_of_date=as_of_date,
        active_on=parse_optional_campaign_discovery_date(
            value=active_on,
            field_name="active_on",
        ),
    )
    return build_bulk_review_campaign_workflow_automation_page(
        definitions=campaign_query.definitions,
        requested_as_of_date=requested_as_of_date,
        actor_id=actor_id,
        active_on=campaign_query.active_on,
        include_closed=include_closed,
        automation_status=automation_status,
        automation_action=automation_action,
        limit=limit,
        offset=offset,
    )
