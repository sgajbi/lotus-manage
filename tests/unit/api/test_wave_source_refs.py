from __future__ import annotations

from datetime import date

from src.api.routers.wave_source_refs import (
    bulk_review_campaign_member_ref,
    bulk_review_campaign_membership_ref,
    cio_model_change_affected_mandate_ref,
    pm_book_member_ref,
    pm_book_membership_ref,
    risk_event_affected_portfolio_ref,
    source_refs_payload,
    tactical_house_view_affected_portfolio_ref,
)
from src.core.waves import DpmWaveSourceRef


def test_source_refs_payload_serializes_refs_with_json_mode() -> None:
    refs = [
        DpmWaveSourceRef(
            source_system="lotus-core",
            source_type="PortfolioManagerBookMembership",
            source_id="pm-book-snapshot-001",
            source_version="v1",
            supportability_state="READY",
            content_hash="sha256:pm-book",
        )
    ]

    assert source_refs_payload(refs) == [
        {
            "source_system": "lotus-core",
            "source_type": "PortfolioManagerBookMembership",
            "source_id": "pm-book-snapshot-001",
            "source_version": "v1",
            "supportability_state": "READY",
            "content_hash": "sha256:pm-book",
        }
    ]


def test_pm_book_membership_ref_preserves_source_batch_lineage() -> None:
    assert pm_book_membership_ref(
        source_id="pm-book-snapshot-001",
        product_version="v1",
        supportability_state="READY",
        content_hash="sha256:pm-book",
    ) == {
        "source_system": "lotus-core",
        "source_type": "PortfolioManagerBookMembership",
        "source_id": "pm-book-snapshot-001",
        "source_version": "v1",
        "supportability_state": "READY",
        "content_hash": "sha256:pm-book",
    }


def test_pm_book_member_ref_falls_back_to_portfolio_id() -> None:
    assert pm_book_member_ref(
        source_record_id=None,
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        as_of_date=date(2026, 5, 18),
    ) == {
        "source_system": "lotus-core",
        "source_type": "PORTFOLIO_MANAGER_BOOK_MEMBER",
        "source_id": "PB_SG_GLOBAL_BAL_001",
        "source_version": "2026-05-18",
        "supportability_state": "READY",
    }


def test_cio_model_change_affected_mandate_ref_stringifies_binding_version() -> None:
    assert cio_model_change_affected_mandate_ref(
        source_record_id=None,
        mandate_id="MANDATE_PB_SG_GLOBAL_BAL_001",
        binding_version=7,
    ) == {
        "source_system": "lotus-core",
        "source_type": "CIO_MODEL_CHANGE_AFFECTED_MANDATE",
        "source_id": "MANDATE_PB_SG_GLOBAL_BAL_001",
        "source_version": "7",
        "supportability_state": "READY",
    }


def test_tactical_house_view_affected_portfolio_ref_uses_cohort_portfolio_identity() -> None:
    assert tactical_house_view_affected_portfolio_ref(
        source_service="lotus-advise",
        cohort_id="thv-cohort-001",
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        product_version="v1",
        supportability_state="READY",
        content_hash="sha256:thv",
    ) == {
        "source_system": "lotus-advise",
        "source_type": "TACTICAL_HOUSE_VIEW_AFFECTED_PORTFOLIO",
        "source_id": "thv-cohort-001:PB_SG_GLOBAL_BAL_001",
        "source_version": "v1",
        "supportability_state": "READY",
        "content_hash": "sha256:thv",
    }


def test_risk_event_affected_portfolio_ref_preserves_source_ref() -> None:
    assert risk_event_affected_portfolio_ref(
        source_service="lotus-risk",
        source_ref="risk-event-source-row-001",
        product_version="v1",
        supportability_state="READY",
        content_hash="sha256:risk-event",
    ) == {
        "source_system": "lotus-risk",
        "source_type": "RISK_EVENT_AFFECTED_PORTFOLIO",
        "source_id": "risk-event-source-row-001",
        "source_version": "v1",
        "supportability_state": "READY",
        "content_hash": "sha256:risk-event",
    }


def test_bulk_review_campaign_refs_preserve_membership_and_member_lineage() -> None:
    campaign_as_of_date = date(2026, 5, 18)

    assert bulk_review_campaign_membership_ref(
        trigger_id="campaign-q2-review",
        campaign_as_of_date=campaign_as_of_date,
        membership_hash="sha256:membership",
    ) == {
        "source_system": "lotus-manage",
        "source_type": "BulkReviewCampaignMembership",
        "source_id": "campaign:campaign-q2-review:2026-05-18",
        "source_version": "v1",
        "supportability_state": "READY",
        "content_hash": "sha256:membership",
    }
    assert bulk_review_campaign_member_ref(
        trigger_id="campaign-q2-review",
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        campaign_as_of_date=campaign_as_of_date,
        membership_hash="sha256:membership",
    ) == {
        "source_system": "lotus-manage",
        "source_type": "BULK_REVIEW_CAMPAIGN_MEMBER",
        "source_id": "campaign-q2-review:PB_SG_GLOBAL_BAL_001",
        "source_version": "2026-05-18",
        "supportability_state": "READY",
        "content_hash": "sha256:membership",
    }
