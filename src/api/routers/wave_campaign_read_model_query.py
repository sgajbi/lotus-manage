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
) -> DpmBulkReviewCampaignReadModelQuery:
    active_on_date = parse_optional_campaign_discovery_date(
        value=active_on,
        field_name="active_on",
    )
    definitions = repository.list_definitions(
        campaign_id=campaign_id,
        status=campaign_status,
        as_of_date=as_of_date,
        limit=limit,
        offset=offset,
    )
    return DpmBulkReviewCampaignReadModelQuery(
        definitions=definitions,
        active_on=active_on_date,
    )
