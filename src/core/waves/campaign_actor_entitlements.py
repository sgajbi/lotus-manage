from __future__ import annotations

from src.core.waves.campaign_definitions import DpmBulkReviewCampaignDefinition


def validate_campaign_command_actor_entitlement(
    *,
    definition: DpmBulkReviewCampaignDefinition,
    actor_id: str | None,
) -> None:
    governance = definition.governance
    entitled_actor_ids = governance.entitled_actor_ids if governance is not None else []
    if not entitled_actor_ids:
        return

    normalized_actor_id = actor_id.strip() if actor_id is not None else ""
    if not normalized_actor_id:
        raise ValueError("BULK_REVIEW_CAMPAIGN_ACTOR_REQUIRED_FOR_ENTITLEMENT")
    if normalized_actor_id not in set(entitled_actor_ids):
        raise ValueError("BULK_REVIEW_CAMPAIGN_ACTOR_NOT_ENTITLED")
