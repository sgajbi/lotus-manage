from __future__ import annotations

from datetime import date

from src.api.routers.wave_campaign_governance_validation import (
    campaign_actor_entitlement_state,
    campaign_approval_status,
    campaign_expiry_state,
)
from src.api.routers.wave_campaign_hashing import campaign_governance_hash
from src.api.routers.wave_request_models import DpmWavePreviewRequest
from src.api.routers.wave_source_refs import source_refs_payload


def resolve_bulk_review_campaign_governance(
    *,
    request: DpmWavePreviewRequest,
    campaign_as_of_date: date,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    governance = request.campaign_governance
    if governance is None:
        return (
            {
                "campaign_governance_status": "NOT_SUPPLIED",
                "campaign_access_purpose": None,
                "campaign_expiry_state": "NOT_SUPPLIED",
                "campaign_actor_entitlement_state": "NOT_SUPPLIED",
            },
            [],
        )

    approval_status = campaign_approval_status(
        approval_ref=governance.approval_ref,
        approved_by=governance.approved_by,
        approved_at=governance.approved_at,
    )
    expiry_state = campaign_expiry_state(
        expires_on=governance.expires_on,
        campaign_as_of_date=campaign_as_of_date,
    )
    actor_entitlement_state = campaign_actor_entitlement_state(
        entitled_actor_ids=governance.entitled_actor_ids,
        actor_id=request.actor_id,
    )

    governance_hash = campaign_governance_hash(
        trigger_id=request.trigger_id,
        actor_id=request.actor_id,
        governance=governance.model_dump(mode="json"),
    )
    governance_refs: list[dict[str, object]] = [
        {
            "source_system": "lotus-manage",
            "source_type": "BulkReviewCampaignGovernance",
            "source_id": f"campaign-governance:{request.trigger_id}",
            "source_version": governance.approved_at or campaign_as_of_date.isoformat(),
            "supportability_state": "READY",
            "content_hash": governance_hash,
        },
        *source_refs_payload(governance.source_refs),
    ]
    return (
        {
            "campaign_governance_status": approval_status,
            "campaign_approval_ref": governance.approval_ref,
            "campaign_approved_by": governance.approved_by,
            "campaign_approved_at": governance.approved_at,
            "campaign_access_purpose": governance.access_purpose,
            "campaign_expiry_state": expiry_state,
            "campaign_expires_on": governance.expires_on,
            "campaign_actor_entitlement_state": actor_entitlement_state,
        },
        governance_refs,
    )
