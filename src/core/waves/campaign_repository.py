from __future__ import annotations

from typing import Protocol

from src.core.waves.campaign_definitions import DpmBulkReviewCampaignDefinition


class DpmBulkReviewCampaignDefinitionConflictError(ValueError):
    pass


class DpmBulkReviewCampaignDefinitionRepository(Protocol):
    def save_definition(self, *, definition: DpmBulkReviewCampaignDefinition) -> None:
        raise NotImplementedError

    def get_definition(
        self,
        *,
        campaign_id: str,
        campaign_version: str,
    ) -> DpmBulkReviewCampaignDefinition | None:
        raise NotImplementedError

    def list_definitions(
        self,
        *,
        campaign_id: str | None = None,
        status: str | None = None,
        as_of_date: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[DpmBulkReviewCampaignDefinition]:
        raise NotImplementedError

    def retire_definition(
        self,
        *,
        definition: DpmBulkReviewCampaignDefinition,
    ) -> DpmBulkReviewCampaignDefinition | None:
        raise NotImplementedError
