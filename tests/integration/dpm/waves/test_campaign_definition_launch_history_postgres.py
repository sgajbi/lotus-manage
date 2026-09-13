"""Campaign launch-history persistence against a real PostgreSQL engine (#679).

The source-definition hash is intentionally stable across an append-only launch
audit. This test proves PostgreSQL accepts that same-hash JSONB mutation while
rejecting an independently built stale append; an in-memory store cannot prove
the SQL comparison at the durable boundary.
"""

from __future__ import annotations

from datetime import datetime, timezone
import uuid

import pytest

from src.core.waves import (
    DpmBulkReviewCampaignDefinition,
    DpmBulkReviewCampaignDefinitionCandidate,
    DpmBulkReviewCampaignDefinitionConflictError,
    DpmWaveSourceRef,
)
from src.core.waves.campaign_definition_launch_history import (
    record_bulk_review_campaign_definition_launch,
)
from src.infrastructure.waves.campaign_definitions import (
    PostgresDpmBulkReviewCampaignDefinitionRepository,
)
from tests.integration.dpm.postgres_prerequisite import postgres_dsn_or_skip

_PROOF = "campaign launch-history durable write proof"


def _definition(*, campaign_id: str) -> DpmBulkReviewCampaignDefinition:
    return DpmBulkReviewCampaignDefinition(
        tenant_id=f"tenant-campaign-{uuid.uuid4().hex[:12]}",
        campaign_id=campaign_id,
        campaign_version="2026.09",
        display_name="Stable campaign launch evidence",
        as_of_date="2026-09-13",
        rationale="Prove launch audit persistence without changing campaign identity.",
        eligible_portfolio_types=["DISCRETIONARY"],
        candidates=[
            DpmBulkReviewCampaignDefinitionCandidate(
                portfolio_id="PB_SG_GLOBAL_BAL_001",
                mandate_id="MANDATE_PB_SG_GLOBAL_BAL_001",
                portfolio_type="DISCRETIONARY",
                source_refs=[
                    DpmWaveSourceRef(
                        source_system="lotus-core",
                        source_type="DpmPortfolioUniverseCandidate",
                        source_id="postgres-campaign-candidate",
                        source_version="2026-09-13",
                        supportability_state="READY",
                        content_hash="sha256:postgres-campaign-candidate",
                    )
                ],
            )
        ],
        source_refs=[],
        created_by="ops",
        correlation_id="corr-postgres-campaign-launch",
    )


def _launch(
    definition: DpmBulkReviewCampaignDefinition,
    *,
    suffix: str,
) -> DpmBulkReviewCampaignDefinition:
    return record_bulk_review_campaign_definition_launch(
        definition=definition,
        wave_id=f"dwv_campaign_{suffix}",
        launched_by="pm_001",
        requested_as_of_date="2026-09-13",
        correlation_id=f"corr-postgres-campaign-launch-{suffix}",
        idempotency_key=f"campaign-launch:postgres:{suffix}",
        launched_at=datetime(2026, 9, 13, tzinfo=timezone.utc),
    )


def test_postgres_records_launch_audit_without_moving_definition_identity() -> None:
    definition = _definition(campaign_id=f"campaign-postgres-{uuid.uuid4().hex[:12]}")
    repository = PostgresDpmBulkReviewCampaignDefinitionRepository(dsn=postgres_dsn_or_skip(_PROOF))
    repository.save_definition(definition=definition)
    appended = _launch(definition, suffix="first")

    assert appended.content_hash == definition.content_hash
    assert (
        repository.record_definition_launch(
            definition=appended,
            expected_content_hash=definition.content_hash,
        )
        == appended
    )
    stored = repository.get_definition(
        tenant_id=definition.tenant_id,
        campaign_id=definition.campaign_id,
        campaign_version=definition.campaign_version,
    )
    assert stored == appended
    assert stored is not None
    assert stored.content_hash == definition.content_hash
    assert len(stored.launch_history) == 1

    stale_append = _launch(definition, suffix="stale")
    with pytest.raises(
        DpmBulkReviewCampaignDefinitionConflictError,
        match="BULK_REVIEW_CAMPAIGN_DEFINITION_STALE_WRITE",
    ):
        repository.record_definition_launch(
            definition=stale_append,
            expected_content_hash=definition.content_hash,
        )

    survivor = repository.get_definition(
        tenant_id=definition.tenant_id,
        campaign_id=definition.campaign_id,
        campaign_version=definition.campaign_version,
    )
    assert survivor == appended


def test_postgres_migrates_legacy_definition_hash_on_next_fenced_launch_append() -> None:
    definition = _definition(campaign_id=f"campaign-legacy-{uuid.uuid4().hex[:12]}")
    repository = PostgresDpmBulkReviewCampaignDefinitionRepository(dsn=postgres_dsn_or_skip(_PROOF))
    repository.save_definition(definition=definition)
    legacy_hash = "sha256:legacy-campaign-definition-hash"
    with repository._connect() as connection:  # noqa: SLF001
        connection.execute(
            """
            UPDATE dpm_bulk_review_campaign_definitions
            SET content_hash = %s,
                payload_json = jsonb_set(
                    payload_json,
                    '{content_hash}',
                    to_jsonb(%s::text)
                )
            WHERE tenant_id = %s AND campaign_id = %s AND campaign_version = %s
            """,
            (
                legacy_hash,
                legacy_hash,
                definition.tenant_id,
                definition.campaign_id,
                definition.campaign_version,
            ),
        )
        connection.commit()

    loaded = repository.get_definition(
        tenant_id=definition.tenant_id,
        campaign_id=definition.campaign_id,
        campaign_version=definition.campaign_version,
    )
    assert loaded is not None
    assert loaded.content_hash == definition.content_hash
    appended = _launch(loaded, suffix="legacy")
    assert (
        repository.record_definition_launch(
            definition=appended,
            expected_content_hash=loaded.content_hash,
        )
        == appended
    )

    with repository._connect() as connection:  # noqa: SLF001
        persisted = connection.execute(
            """
            SELECT content_hash, payload_json->>'content_hash' AS payload_hash
            FROM dpm_bulk_review_campaign_definitions
            WHERE tenant_id = %s AND campaign_id = %s AND campaign_version = %s
            """,
            (definition.tenant_id, definition.campaign_id, definition.campaign_version),
        ).fetchone()

    assert persisted["content_hash"] == definition.content_hash
    assert persisted["payload_hash"] == definition.content_hash
