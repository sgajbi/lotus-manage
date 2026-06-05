from __future__ import annotations

from datetime import datetime, timezone

from src.core.waves import DpmWaveSourceRef
from src.core.waves.campaign_definition_events import (
    build_bulk_review_campaign_definition_created_event,
    build_bulk_review_campaign_definition_launch_event,
    build_bulk_review_campaign_definition_lifecycle_events,
    build_bulk_review_campaign_definition_retired_event,
    build_bulk_review_campaign_definition_superseded_event,
)
from src.core.waves.campaign_definitions import (
    DpmBulkReviewCampaignDefinition,
    DpmBulkReviewCampaignDefinitionCandidate,
    DpmBulkReviewCampaignDefinitionLaunchRecord,
)


def _definition() -> DpmBulkReviewCampaignDefinition:
    return DpmBulkReviewCampaignDefinition(
        campaign_id="campaign-holdings-apple-tesla-20260510",
        campaign_version="2026.05",
        display_name="Apple and Tesla holdings review",
        as_of_date="2026-05-10",
        rationale="Review discretionary portfolios affected by the Apple and Tesla campaign.",
        candidates=[
            DpmBulkReviewCampaignDefinitionCandidate(
                portfolio_id="PB_SG_GLOBAL_BAL_001",
                mandate_id="MANDATE_PB_SG_GLOBAL_BAL_001",
                portfolio_type="DISCRETIONARY",
                source_refs=[
                    DpmWaveSourceRef(
                        source_system="lotus-core",
                        source_type="HoldingsAsOf",
                        source_id="holdings-asof-pb-sg-global-bal-001",
                    )
                ],
            )
        ],
        created_at=datetime(2026, 5, 10, 8, 30, tzinfo=timezone.utc),
        created_by="ops",
        correlation_id="corr-campaign-definition-001",
    )


def _launch() -> DpmBulkReviewCampaignDefinitionLaunchRecord:
    return DpmBulkReviewCampaignDefinitionLaunchRecord(
        wave_id="dwv_campaign_launch_001",
        launched_at=datetime(2026, 5, 11, 9, 15, tzinfo=timezone.utc),
        launched_by="pm_001",
        requested_as_of_date="2026-05-10",
        correlation_id="corr-campaign-launch-001",
        idempotency_key="campaign-launch:2026.05:001",
    )


def _retired_definition() -> DpmBulkReviewCampaignDefinition:
    payload = {
        **_definition().model_dump(mode="python"),
        "status": "RETIRED",
        "retired_at": datetime(2026, 5, 12, 10, 0, tzinfo=timezone.utc),
        "retired_by": "ops",
        "retirement_reason": "Campaign completed.",
        "retirement_correlation_id": "corr-campaign-retire-001",
        "content_hash": "",
    }
    return DpmBulkReviewCampaignDefinition.model_validate(payload)


def _superseded_definition() -> DpmBulkReviewCampaignDefinition:
    payload = {
        **_definition().model_dump(mode="python"),
        "status": "SUPERSEDED",
        "superseded_at": datetime(2026, 5, 13, 11, 0, tzinfo=timezone.utc),
        "superseded_by": "ops",
        "supersession_reason": "Campaign candidate set refreshed.",
        "supersession_correlation_id": "corr-campaign-supersede-001",
        "superseded_by_campaign_id": "campaign-holdings-apple-tesla-20260510",
        "superseded_by_campaign_version": "2026.06",
        "superseded_by_content_hash": "sha256:replacement",
        "content_hash": "",
    }
    return DpmBulkReviewCampaignDefinition.model_validate(payload)


def test_campaign_definition_created_event_projects_definition_identity() -> None:
    definition = _definition()

    event = build_bulk_review_campaign_definition_created_event(definition=definition)

    assert event.event_type == "CREATED"
    assert event.campaign_id == "campaign-holdings-apple-tesla-20260510"
    assert event.campaign_version == "2026.05"
    assert event.occurred_at == "2026-05-10T08:30:00+00:00"
    assert event.actor_id == "ops"
    assert event.reason == definition.rationale
    assert event.correlation_id == "corr-campaign-definition-001"
    assert event.status_after == "ACTIVE"
    assert event.content_hash == definition.content_hash


def test_campaign_definition_launch_event_projects_launch_lineage() -> None:
    definition = _definition()

    event = build_bulk_review_campaign_definition_launch_event(
        definition=definition,
        launch=_launch(),
    )

    assert event.event_type == "LAUNCHED"
    assert event.occurred_at == "2026-05-11T09:15:00+00:00"
    assert event.actor_id == "pm_001"
    assert event.reason == "Durable bulk-review campaign wave launched."
    assert event.correlation_id == "corr-campaign-launch-001"
    assert event.status_after == "ACTIVE"
    assert event.wave_id == "dwv_campaign_launch_001"
    assert event.requested_as_of_date == "2026-05-10"
    assert event.idempotency_key == "campaign-launch:2026.05:001"


def test_campaign_definition_retired_event_projects_retirement_audit_fields() -> None:
    definition = _retired_definition()

    event = build_bulk_review_campaign_definition_retired_event(definition=definition)

    assert event is not None
    assert event.event_type == "RETIRED"
    assert event.occurred_at == "2026-05-12T10:00:00+00:00"
    assert event.actor_id == "ops"
    assert event.reason == "Campaign completed."
    assert event.correlation_id == "corr-campaign-retire-001"
    assert event.status_after == "RETIRED"


def test_campaign_definition_retired_event_ignores_active_definitions() -> None:
    assert build_bulk_review_campaign_definition_retired_event(definition=_definition()) is None


def test_campaign_definition_superseded_event_projects_replacement_lineage() -> None:
    definition = _superseded_definition()

    event = build_bulk_review_campaign_definition_superseded_event(definition=definition)

    assert event is not None
    assert event.event_type == "SUPERSEDED"
    assert event.occurred_at == "2026-05-13T11:00:00+00:00"
    assert event.actor_id == "ops"
    assert event.reason == "Campaign candidate set refreshed."
    assert event.correlation_id == "corr-campaign-supersede-001"
    assert event.status_after == "SUPERSEDED"
    assert event.replacement_campaign_id == "campaign-holdings-apple-tesla-20260510"
    assert event.replacement_campaign_version == "2026.06"
    assert event.replacement_content_hash == "sha256:replacement"


def test_campaign_definition_superseded_event_ignores_active_definitions() -> None:
    assert build_bulk_review_campaign_definition_superseded_event(definition=_definition()) is None


def test_campaign_definition_lifecycle_event_page_preserves_event_order() -> None:
    definition = _retired_definition().model_copy(update={"launch_history": [_launch()]})

    page = build_bulk_review_campaign_definition_lifecycle_events(definition=definition)

    assert page.count == 3
    assert [event.event_type for event in page.items] == ["CREATED", "LAUNCHED", "RETIRED"]
