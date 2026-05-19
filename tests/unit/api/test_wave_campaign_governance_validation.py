from __future__ import annotations

from datetime import date

import pytest

from src.api.routers.wave_campaign_governance_validation import (
    campaign_actor_entitlement_state,
    campaign_approval_status,
    campaign_expiry_state,
)
from src.api.services import wave_service


def test_campaign_approval_status_returns_approved_when_all_evidence_supplied() -> None:
    assert (
        campaign_approval_status(
            approval_ref="APPROVAL-001",
            approved_by="CIO_SG",
            approved_at="2026-05-19T00:00:00Z",
        )
        == "APPROVED"
    )


def test_campaign_approval_status_returns_not_supplied_when_empty() -> None:
    assert (
        campaign_approval_status(approval_ref=None, approved_by=None, approved_at=None)
        == "NOT_SUPPLIED"
    )


def test_campaign_approval_status_raises_for_partial_evidence() -> None:
    with pytest.raises(wave_service.DpmWaveValidationError) as exc_info:
        campaign_approval_status(
            approval_ref="APPROVAL-001",
            approved_by=None,
            approved_at="2026-05-19T00:00:00Z",
        )

    assert exc_info.value.code == "BULK_REVIEW_CAMPAIGN_APPROVAL_EVIDENCE_INCOMPLETE"
    assert (
        exc_info.value.message
        == "Bulk-review campaign approval evidence requires approval_ref, approved_by, and approved_at."
    )


def test_campaign_expiry_state_returns_not_supplied_without_expiry() -> None:
    assert (
        campaign_expiry_state(expires_on=None, campaign_as_of_date=date(2026, 5, 19))
        == "NOT_SUPPLIED"
    )


def test_campaign_expiry_state_returns_active_for_current_expiry() -> None:
    assert (
        campaign_expiry_state(expires_on="2026-05-19", campaign_as_of_date=date(2026, 5, 19))
        == "ACTIVE"
    )


def test_campaign_expiry_state_raises_for_invalid_date() -> None:
    with pytest.raises(wave_service.DpmWaveValidationError) as exc_info:
        campaign_expiry_state(expires_on="19-05-2026", campaign_as_of_date=date(2026, 5, 19))

    assert exc_info.value.code == "BULK_REVIEW_CAMPAIGN_EXPIRY_DATE_INVALID"
    assert exc_info.value.message == "campaign_governance.expires_on must be an ISO date."


def test_campaign_expiry_state_raises_for_expired_governance() -> None:
    with pytest.raises(wave_service.DpmWaveValidationError) as exc_info:
        campaign_expiry_state(expires_on="2026-05-18", campaign_as_of_date=date(2026, 5, 19))

    assert exc_info.value.code == "BULK_REVIEW_CAMPAIGN_EXPIRED"
    assert (
        exc_info.value.message
        == "Bulk-review campaign governance is expired for the requested as_of_date."
    )


def test_campaign_actor_entitlement_state_returns_not_supplied_without_entitlements() -> None:
    assert (
        campaign_actor_entitlement_state(entitled_actor_ids=["", "   "], actor_id="PM_SG_DPM_001")
        == "NOT_SUPPLIED"
    )


def test_campaign_actor_entitlement_state_returns_authorized_for_matching_actor() -> None:
    assert (
        campaign_actor_entitlement_state(
            entitled_actor_ids=[" PM_SG_DPM_001 "],
            actor_id="PM_SG_DPM_001",
        )
        == "AUTHORIZED"
    )


def test_campaign_actor_entitlement_state_raises_for_unentitled_actor() -> None:
    with pytest.raises(wave_service.DpmWaveValidationError) as exc_info:
        campaign_actor_entitlement_state(
            entitled_actor_ids=["PM_SG_DPM_002"],
            actor_id="PM_SG_DPM_001",
        )

    assert exc_info.value.code == "BULK_REVIEW_CAMPAIGN_ACTOR_NOT_ENTITLED"
    assert exc_info.value.message == "actor_id is not entitled for this bulk-review campaign."
