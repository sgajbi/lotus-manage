from __future__ import annotations

from typing import Literal, cast

from fastapi import HTTPException

from src.api.routers.wave_campaign_read_model_query import load_campaign_read_model_query
from src.core.waves import (
    DpmBulkReviewCampaignDefinition,
    DpmBulkReviewCampaignDefinitionCandidate,
    DpmWaveSourceRef,
)
from src.infrastructure.waves import InMemoryDpmBulkReviewCampaignDefinitionRepository


def _campaign_definition(
    *,
    campaign_id: str,
    as_of_date: str,
    status: Literal["ACTIVE", "RETIRED", "SUPERSEDED"] = "ACTIVE",
) -> DpmBulkReviewCampaignDefinition:
    return DpmBulkReviewCampaignDefinition(
        campaign_id=campaign_id,
        campaign_version="2026.05",
        display_name=f"{campaign_id} review",
        status=status,
        as_of_date=as_of_date,
        rationale="Review source-backed discretionary mandate candidates.",
        candidates=[
            DpmBulkReviewCampaignDefinitionCandidate(
                portfolio_id="PB_SG_GLOBAL_BAL_001",
                portfolio_type="DISCRETIONARY",
                source_refs=[
                    DpmWaveSourceRef(
                        source_system="lotus-core",
                        source_type="HoldingsAsOf",
                        source_id=f"holdings-{campaign_id}",
                    )
                ],
            )
        ],
        created_by="ops",
        correlation_id=f"corr-{campaign_id}",
    )


def test_campaign_read_model_query_centralizes_repository_filters_and_active_date() -> None:
    repository = InMemoryDpmBulkReviewCampaignDefinitionRepository()
    repository.save_definition(
        definition=_campaign_definition(
            campaign_id="campaign-active",
            as_of_date="2026-05-10",
        )
    )
    repository.save_definition(
        definition=_campaign_definition(
            campaign_id="campaign-other-date",
            as_of_date="2026-05-11",
        )
    )

    query = load_campaign_read_model_query(
        repository=repository,
        campaign_id=None,
        campaign_status="ACTIVE",
        as_of_date="2026-05-10",
        active_on="2026-05-12",
        limit=50,
        offset=0,
    )

    assert query.active_on is not None
    assert query.active_on.isoformat() == "2026-05-12"
    assert [definition.campaign_id for definition in query.definitions] == ["campaign-active"]


def test_campaign_read_model_query_reuses_invalid_active_date_error_contract() -> None:
    repository = InMemoryDpmBulkReviewCampaignDefinitionRepository()

    try:
        load_campaign_read_model_query(
            repository=repository,
            campaign_id=None,
            campaign_status=None,
            as_of_date=None,
            active_on="bad-date",
            limit=50,
            offset=0,
        )
    except HTTPException as exc:
        assert exc.status_code == 422
        detail = cast(dict[str, str], exc.detail)
        assert detail == {
            "code": "BULK_REVIEW_CAMPAIGN_DISCOVERY_DATE_INVALID",
            "message": "active_on must be an ISO date.",
        }
    else:  # pragma: no cover - defensive assertion for the error contract
        raise AssertionError("Expected invalid active_on date to raise HTTPException")
