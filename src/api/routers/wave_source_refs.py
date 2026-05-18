from __future__ import annotations

from datetime import date


def source_ref_payload(
    *,
    source_system: str,
    source_type: str,
    source_id: str | None,
    source_version: str | None,
    supportability_state: str,
    content_hash: str | None = None,
    include_content_hash: bool = True,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "source_system": source_system,
        "source_type": source_type,
        "source_id": source_id,
        "source_version": source_version,
        "supportability_state": supportability_state,
    }
    if include_content_hash:
        payload["content_hash"] = content_hash
    return payload


def pm_book_membership_ref(
    *,
    source_id: str | None,
    product_version: str,
    supportability_state: str,
    content_hash: str | None,
) -> dict[str, object]:
    return source_ref_payload(
        source_system="lotus-core",
        source_type="PortfolioManagerBookMembership",
        source_id=source_id,
        source_version=product_version,
        supportability_state=supportability_state,
        content_hash=content_hash,
    )


def pm_book_member_ref(
    *,
    source_record_id: str | None,
    portfolio_id: str,
    as_of_date: date,
) -> dict[str, object]:
    return source_ref_payload(
        source_system="lotus-core",
        source_type="PORTFOLIO_MANAGER_BOOK_MEMBER",
        source_id=source_record_id or portfolio_id,
        source_version=as_of_date.isoformat(),
        supportability_state="READY",
        include_content_hash=False,
    )


def cio_model_change_cohort_ref(
    *,
    source_id: str | None,
    product_version: str,
    supportability_state: str,
    content_hash: str | None,
) -> dict[str, object]:
    return source_ref_payload(
        source_system="lotus-core",
        source_type="CioModelChangeAffectedCohort",
        source_id=source_id,
        source_version=product_version,
        supportability_state=supportability_state,
        content_hash=content_hash,
    )


def cio_model_change_event_ref(
    *,
    model_change_event_id: str,
    model_portfolio_version: str,
    supportability_state: str,
    content_hash: str | None,
) -> dict[str, object]:
    return source_ref_payload(
        source_system="lotus-core",
        source_type="CIO_MODEL_CHANGE_EVENT",
        source_id=model_change_event_id,
        source_version=model_portfolio_version,
        supportability_state=supportability_state,
        content_hash=content_hash,
    )


def cio_model_change_affected_mandate_ref(
    *,
    source_record_id: str | None,
    mandate_id: str,
    binding_version: object,
) -> dict[str, object]:
    return source_ref_payload(
        source_system="lotus-core",
        source_type="CIO_MODEL_CHANGE_AFFECTED_MANDATE",
        source_id=source_record_id or mandate_id,
        source_version=str(binding_version),
        supportability_state="READY",
        include_content_hash=False,
    )


def tactical_house_view_cohort_ref(
    *,
    source_service: str,
    product_name: str,
    cohort_id: str,
    product_version: str,
    supportability_state: str,
    content_hash: str | None,
) -> dict[str, object]:
    return source_ref_payload(
        source_system=source_service,
        source_type=product_name,
        source_id=cohort_id,
        source_version=product_version,
        supportability_state=supportability_state,
        content_hash=content_hash,
    )


def tactical_house_view_ref(
    *,
    source_service: str,
    tactical_view_id: str,
    tactical_view_version: str,
    supportability_state: str,
    content_hash: str | None,
) -> dict[str, object]:
    return source_ref_payload(
        source_system=source_service,
        source_type="TACTICAL_HOUSE_VIEW",
        source_id=tactical_view_id,
        source_version=tactical_view_version,
        supportability_state=supportability_state,
        content_hash=content_hash,
    )


def tactical_house_view_affected_portfolio_ref(
    *,
    source_service: str,
    cohort_id: str,
    portfolio_id: str,
    product_version: str,
    supportability_state: str,
    content_hash: str | None,
) -> dict[str, object]:
    return source_ref_payload(
        source_system=source_service,
        source_type="TACTICAL_HOUSE_VIEW_AFFECTED_PORTFOLIO",
        source_id=f"{cohort_id}:{portfolio_id}",
        source_version=product_version,
        supportability_state=supportability_state,
        content_hash=content_hash,
    )


def risk_event_cohort_ref(
    *,
    source_service: str,
    product_name: str,
    source_id: str,
    product_version: str,
    supportability_state: str,
    content_hash: str | None,
) -> dict[str, object]:
    return source_ref_payload(
        source_system=source_service,
        source_type=product_name,
        source_id=source_id,
        source_version=product_version,
        supportability_state=supportability_state,
        content_hash=content_hash,
    )


def risk_event_ref(
    *,
    source_service: str,
    risk_event_id: str,
    product_version: str,
    supportability_state: str,
    content_hash: str | None,
) -> dict[str, object]:
    return source_ref_payload(
        source_system=source_service,
        source_type="RISK_EVENT",
        source_id=risk_event_id,
        source_version=product_version,
        supportability_state=supportability_state,
        content_hash=content_hash,
    )


def risk_event_affected_portfolio_ref(
    *,
    source_service: str,
    source_ref: str,
    product_version: str,
    supportability_state: str,
    content_hash: str | None,
) -> dict[str, object]:
    return source_ref_payload(
        source_system=source_service,
        source_type="RISK_EVENT_AFFECTED_PORTFOLIO",
        source_id=source_ref,
        source_version=product_version,
        supportability_state=supportability_state,
        content_hash=content_hash,
    )


def bulk_review_campaign_membership_ref(
    *,
    trigger_id: str,
    campaign_as_of_date: date,
    membership_hash: str,
) -> dict[str, object]:
    return source_ref_payload(
        source_system="lotus-manage",
        source_type="BulkReviewCampaignMembership",
        source_id=f"campaign:{trigger_id}:{campaign_as_of_date.isoformat()}",
        source_version="v1",
        supportability_state="READY",
        content_hash=membership_hash,
    )


def bulk_review_campaign_member_ref(
    *,
    trigger_id: str,
    portfolio_id: str,
    campaign_as_of_date: date,
    membership_hash: str,
) -> dict[str, object]:
    return source_ref_payload(
        source_system="lotus-manage",
        source_type="BULK_REVIEW_CAMPAIGN_MEMBER",
        source_id=f"{trigger_id}:{portfolio_id}",
        source_version=campaign_as_of_date.isoformat(),
        supportability_state="READY",
        content_hash=membership_hash,
    )
