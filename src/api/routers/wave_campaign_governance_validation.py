from __future__ import annotations

from collections.abc import Iterable
from datetime import date

from src.api.services import wave_service


def campaign_approval_status(
    *,
    approval_ref: str | None,
    approved_by: str | None,
    approved_at: str | None,
) -> str:
    approval_fields = [approval_ref, approved_by, approved_at]
    supplied_approval_fields = [value for value in approval_fields if value]
    if supplied_approval_fields and len(supplied_approval_fields) != len(approval_fields):
        raise wave_service.DpmWaveValidationError(
            "BULK_REVIEW_CAMPAIGN_APPROVAL_EVIDENCE_INCOMPLETE",
            "Bulk-review campaign approval evidence requires approval_ref, approved_by, and approved_at.",
        )
    return "APPROVED" if len(supplied_approval_fields) == len(approval_fields) else "NOT_SUPPLIED"


def campaign_expiry_state(
    *,
    expires_on: str | None,
    campaign_as_of_date: date,
) -> str:
    if not expires_on:
        return "NOT_SUPPLIED"
    try:
        expiry_date = date.fromisoformat(expires_on)
    except ValueError as exc:
        raise wave_service.DpmWaveValidationError(
            "BULK_REVIEW_CAMPAIGN_EXPIRY_DATE_INVALID",
            "campaign_governance.expires_on must be an ISO date.",
        ) from exc
    if expiry_date < campaign_as_of_date:
        raise wave_service.DpmWaveValidationError(
            "BULK_REVIEW_CAMPAIGN_EXPIRED",
            "Bulk-review campaign governance is expired for the requested as_of_date.",
        )
    return "ACTIVE"


def campaign_actor_entitlement_state(
    *,
    entitled_actor_ids: Iterable[str],
    actor_id: str,
) -> str:
    entitled_actors = {actor.strip() for actor in entitled_actor_ids if actor.strip()}
    if not entitled_actors:
        return "NOT_SUPPLIED"
    if actor_id not in entitled_actors:
        raise wave_service.DpmWaveValidationError(
            "BULK_REVIEW_CAMPAIGN_ACTOR_NOT_ENTITLED",
            "actor_id is not entitled for this bulk-review campaign.",
        )
    return "AUTHORIZED"
