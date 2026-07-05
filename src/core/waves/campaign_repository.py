from __future__ import annotations

from typing import Protocol

from src.core.waves.campaign_definitions import DpmBulkReviewCampaignDefinition


class DpmBulkReviewCampaignDefinitionConflictError(ValueError):
    pass


class DpmBulkReviewCampaignDefinitionRepository(Protocol):
    def save_definition(self, *, definition: DpmBulkReviewCampaignDefinition) -> None:
        """Persist a campaign definition."""

    def get_definition(
        self,
        *,
        campaign_id: str,
        campaign_version: str,
    ) -> DpmBulkReviewCampaignDefinition | None:
        """Return a campaign definition by identifier and version."""

    def list_definitions(
        self,
        *,
        campaign_id: str | None = None,
        status: str | None = None,
        as_of_date: str | None = None,
        limit: int | None = 50,
        offset: int = 0,
    ) -> list[DpmBulkReviewCampaignDefinition]:
        """Return campaign definitions, optionally bounded by repository-level filters."""

    def retire_definition(
        self,
        *,
        definition: DpmBulkReviewCampaignDefinition,
    ) -> DpmBulkReviewCampaignDefinition | None:
        """Persist a retired campaign definition version."""

    def supersede_definition(
        self,
        *,
        definition: DpmBulkReviewCampaignDefinition,
    ) -> DpmBulkReviewCampaignDefinition | None:
        """Persist a superseded campaign definition version."""

    def record_definition_launch(
        self,
        *,
        definition: DpmBulkReviewCampaignDefinition,
        expected_content_hash: str,
    ) -> DpmBulkReviewCampaignDefinition | None:
        """Persist launch evidence when the stored definition still matches the expected hash."""

    def record_definition_approval_decision(
        self,
        *,
        definition: DpmBulkReviewCampaignDefinition,
        expected_content_hash: str,
    ) -> DpmBulkReviewCampaignDefinition | None:
        """Persist approval-decision evidence with optimistic stale-write protection."""

    def record_definition_assignment_action(
        self,
        *,
        definition: DpmBulkReviewCampaignDefinition,
        expected_content_hash: str,
    ) -> DpmBulkReviewCampaignDefinition | None:
        """Persist assignment-action evidence with optimistic stale-write protection."""

    def record_definition_assignment_task(
        self,
        *,
        definition: DpmBulkReviewCampaignDefinition,
        expected_content_hash: str,
    ) -> DpmBulkReviewCampaignDefinition | None:
        """Persist assignment-task evidence with optimistic stale-write protection."""

    def record_definition_maker_checker_control(
        self,
        *,
        definition: DpmBulkReviewCampaignDefinition,
        expected_content_hash: str,
    ) -> DpmBulkReviewCampaignDefinition | None:
        """Persist maker-checker control evidence with optimistic stale-write protection."""
