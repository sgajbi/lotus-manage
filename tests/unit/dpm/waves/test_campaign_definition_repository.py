from __future__ import annotations

import pytest

from src.core.waves import DpmWaveSourceRef
from src.core.waves.campaign_definitions import (
    DpmBulkReviewCampaignDefinition,
    DpmBulkReviewCampaignDefinitionCandidate,
    DpmBulkReviewCampaignDefinitionGovernance,
)
from src.core.waves.campaign_repository import DpmBulkReviewCampaignDefinitionConflictError
from src.infrastructure.waves.campaign_definitions import (
    InMemoryDpmBulkReviewCampaignDefinitionRepository,
    PostgresDpmBulkReviewCampaignDefinitionRepository,
    _payload,
)


def _definition(
    *,
    campaign_id: str = "campaign-holdings-apple-tesla-20260510",
    display_name: str = "Apple and Tesla holdings review",
) -> DpmBulkReviewCampaignDefinition:
    return DpmBulkReviewCampaignDefinition(
        campaign_id=campaign_id,
        campaign_version="2026.05",
        display_name=display_name,
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
        governance=DpmBulkReviewCampaignDefinitionGovernance(
            approval_ref="BRC-APPROVAL-2026-05",
            approved_by="cio_ops_committee",
            approved_at="2026-05-09T09:30:00+08:00",
        ),
        created_by="ops",
        correlation_id="corr-campaign-definition-001",
    )


def test_campaign_definition_validation_rejects_bad_candidates_and_hash() -> None:
    with pytest.raises(ValueError, match="BULK_REVIEW_CAMPAIGN_SOURCE_REFS_REQUIRED"):
        DpmBulkReviewCampaignDefinitionCandidate(
            portfolio_id="PB_SG_GLOBAL_BAL_001",
            portfolio_type="DISCRETIONARY",
            source_refs=[],
        )

    with pytest.raises(ValueError, match="BULK_REVIEW_CAMPAIGN_PORTFOLIO_TYPES_REQUIRED"):
        DpmBulkReviewCampaignDefinition(
            campaign_id="campaign-empty-types",
            campaign_version="2026.05",
            display_name="Empty type campaign",
            as_of_date="2026-05-10",
            rationale="Invalid campaign.",
            eligible_portfolio_types=[],
            candidates=[_definition().candidates[0]],
            created_by="ops",
            correlation_id="corr-campaign-definition-001",
        )

    with pytest.raises(ValueError, match="BULK_REVIEW_CAMPAIGN_DEFINITION_HASH_MISMATCH"):
        DpmBulkReviewCampaignDefinition(
            campaign_id="campaign-bad-hash",
            campaign_version="2026.05",
            display_name="Bad hash campaign",
            as_of_date="2026-05-10",
            rationale="Invalid campaign.",
            candidates=[_definition().candidates[0]],
            created_by="ops",
            correlation_id="corr-campaign-definition-001",
            content_hash="sha256:bad",
        )


def test_in_memory_campaign_definition_repository_filters_and_conflicts() -> None:
    repository = InMemoryDpmBulkReviewCampaignDefinitionRepository()
    definition = _definition()
    repository.save_definition(definition=definition)
    repository.save_definition(definition=definition)

    assert (
        repository.get_definition(
            campaign_id=definition.campaign_id,
            campaign_version=definition.campaign_version,
        )
        == definition
    )
    assert repository.get_definition(campaign_id="missing", campaign_version="2026.05") is None
    assert repository.list_definitions(campaign_id=definition.campaign_id) == [definition]
    assert repository.list_definitions(status="ACTIVE", as_of_date="2026-05-10") == [definition]
    assert repository.list_definitions(offset=1) == []

    with pytest.raises(
        DpmBulkReviewCampaignDefinitionConflictError,
        match="BULK_REVIEW_CAMPAIGN_DEFINITION_IMMUTABLE_CONFLICT",
    ):
        repository.save_definition(definition=_definition(display_name="Changed name"))


class _Cursor:
    def __init__(
        self, row: dict[str, object] | None = None, rows: list[dict[str, object]] | None = None
    ):
        self._row = row
        self._rows = rows or []

    def fetchone(self) -> dict[str, object] | None:
        return self._row

    def fetchall(self) -> list[dict[str, object]]:
        return self._rows


class _Connection:
    def __init__(self, cursors: list[_Cursor]) -> None:
        self._cursors = cursors
        self.committed = False
        self.rolled_back = False

    def execute(self, _sql: str, _args: object = None) -> _Cursor:
        return self._cursors.pop(0)

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True

    def close(self) -> None:
        pass


def test_postgres_campaign_definition_repository_uses_payload_rows() -> None:
    definition = _definition()
    row = {"payload_json": definition.model_dump(mode="json")}
    repository = object.__new__(PostgresDpmBulkReviewCampaignDefinitionRepository)
    connection = _Connection(
        [
            _Cursor(),
            _Cursor(row={"content_hash": definition.content_hash}),
            _Cursor(row=row),
            _Cursor(rows=[row]),
        ]
    )
    repository._connect = lambda: connection  # type: ignore[attr-defined, method-assign]

    repository.save_definition(definition=definition)
    fetched = repository.get_definition(
        campaign_id=definition.campaign_id,
        campaign_version=definition.campaign_version,
    )
    listed = repository.list_definitions(
        campaign_id=definition.campaign_id,
        status="ACTIVE",
        as_of_date="2026-05-10",
    )

    assert connection.committed is True
    assert fetched == definition
    assert listed == [definition]
    assert _payload({"payload_json": {"campaign_id": "dict"}}) == {"campaign_id": "dict"}
    assert _payload({"payload_json": 1}) == "1"


def test_postgres_campaign_definition_repository_detects_conflict() -> None:
    definition = _definition()
    repository = object.__new__(PostgresDpmBulkReviewCampaignDefinitionRepository)
    connection = _Connection([_Cursor(), _Cursor(row={"content_hash": "sha256:different"})])
    repository._connect = lambda: connection  # type: ignore[attr-defined, method-assign]

    with pytest.raises(
        DpmBulkReviewCampaignDefinitionConflictError,
        match="BULK_REVIEW_CAMPAIGN_DEFINITION_IMMUTABLE_CONFLICT",
    ):
        repository.save_definition(definition=definition)

    assert connection.rolled_back is True
