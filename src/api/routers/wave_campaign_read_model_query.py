from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from src.api.routers.wave_campaign_definition_errors import (
    parse_optional_campaign_discovery_date,
)
from src.core.waves import (
    DpmBulkReviewCampaignDefinition,
    DpmBulkReviewCampaignDefinitionRepository,
)


@dataclass(frozen=True)
class DpmBulkReviewCampaignReadModelQuery:
    definitions: list[DpmBulkReviewCampaignDefinition]
    active_on: date | None


def load_campaign_read_model_query(
    *,
    repository: DpmBulkReviewCampaignDefinitionRepository,
    campaign_id: str | None,
    campaign_status: str | None,
    as_of_date: str | None,
    active_on: str | None,
    limit: int,
    offset: int,
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
    active_on_date = parse_optional_campaign_discovery_date(
        value=active_on,
        field_name="active_on",
    )
    if use_workflow_projection:
        definitions = repository.list_definitions_by_workflow_projection(
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
        definitions = repository.list_definitions(
            campaign_id=campaign_id,
            status=campaign_status,
            as_of_date=as_of_date,
            limit=None,
            offset=0,
        )
    return DpmBulkReviewCampaignReadModelQuery(
        definitions=definitions,
        active_on=active_on_date,
    )
