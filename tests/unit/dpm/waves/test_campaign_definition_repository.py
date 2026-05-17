from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.core.waves import DpmWaveSourceRef
from src.core.waves.campaign_definition_lifecycle import (
    DpmBulkReviewCampaignDefinitionLifecycleError,
    retire_bulk_review_campaign_definition,
    supersede_bulk_review_campaign_definition,
)
from src.core.waves.campaign_definition_launch_history import (
    build_bulk_review_campaign_definition_launch_history_page,
    record_bulk_review_campaign_definition_launch,
)
from src.core.waves.campaign_definition_launch_execution import (
    DpmBulkReviewCampaignDefinitionLaunchBlocked,
    build_bulk_review_campaign_definition_launch_command,
)
from src.core.waves.campaign_definitions import (
    DpmBulkReviewCampaignDefinition,
    DpmBulkReviewCampaignDefinitionCandidate,
    DpmBulkReviewCampaignDefinitionGovernance,
)
from src.core.waves.campaign_repository import DpmBulkReviewCampaignDefinitionConflictError
from src.infrastructure.waves.campaign_definitions import (
    InMemoryDpmBulkReviewCampaignDefinitionRepository,
    PostgresDpmBulkReviewCampaignDefinitionRepository,
    _import_psycopg,
    _payload,
)
import src.infrastructure.waves.campaign_definitions as campaign_definition_infra


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
    with pytest.raises(ValueError, match="BULK_REVIEW_CAMPAIGN_PORTFOLIO_TYPE_REQUIRED"):
        DpmBulkReviewCampaignDefinitionCandidate(
            portfolio_id="PB_SG_GLOBAL_BAL_001",
            portfolio_type=" ",
            source_refs=[
                DpmWaveSourceRef(
                    source_system="lotus-core",
                    source_type="HoldingsAsOf",
                    source_id="holdings-asof-pb-sg-global-bal-001",
                )
            ],
        )

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

    with pytest.raises(ValueError, match="BULK_REVIEW_CAMPAIGN_CANDIDATE_PORTFOLIOS_REQUIRED"):
        DpmBulkReviewCampaignDefinition(
            campaign_id="campaign-empty-candidates",
            campaign_version="2026.05",
            display_name="Empty candidate campaign",
            as_of_date="2026-05-10",
            rationale="Invalid campaign.",
            candidates=[],
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


def test_campaign_definition_retired_and_superseded_validation_edges() -> None:
    definition = _definition()
    retired_base = {
        **definition.model_dump(mode="python"),
        "status": "RETIRED",
        "retired_at": "2026-05-11T08:00:00Z",
        "retired_by": "ops",
        "retirement_reason": "Campaign completed.",
        "retirement_correlation_id": "corr-campaign-definition-retire-001",
        "content_hash": "",
    }
    for field_name, reason_code in [
        ("retired_at", "BULK_REVIEW_CAMPAIGN_RETIREMENT_TIMESTAMP_REQUIRED"),
        ("retired_by", "BULK_REVIEW_CAMPAIGN_RETIREMENT_ACTOR_REQUIRED"),
        ("retirement_reason", "BULK_REVIEW_CAMPAIGN_RETIREMENT_REASON_REQUIRED"),
        ("retirement_correlation_id", "BULK_REVIEW_CAMPAIGN_RETIREMENT_CORRELATION_REQUIRED"),
    ]:
        payload = {**retired_base, field_name: None}
        with pytest.raises(ValueError, match=reason_code):
            DpmBulkReviewCampaignDefinition.model_validate(payload)

    with pytest.raises(
        ValueError,
        match="BULK_REVIEW_CAMPAIGN_RETIRED_SUPERSESSION_FIELDS_FORBIDDEN",
    ):
        DpmBulkReviewCampaignDefinition.model_validate(
            {**retired_base, "superseded_by": "ops", "content_hash": ""}
        )

    superseded_base = {
        **definition.model_dump(mode="python"),
        "status": "SUPERSEDED",
        "superseded_at": "2026-05-12T08:00:00Z",
        "superseded_by": "ops",
        "supersession_reason": "Campaign candidate set refreshed.",
        "supersession_correlation_id": "corr-campaign-definition-supersede-001",
        "superseded_by_campaign_id": definition.campaign_id,
        "superseded_by_campaign_version": "2026.06",
        "superseded_by_content_hash": "sha256:replacement",
        "content_hash": "",
    }
    for field_name, reason_code in [
        ("superseded_at", "BULK_REVIEW_CAMPAIGN_SUPERSESSION_TIMESTAMP_REQUIRED"),
        ("superseded_by", "BULK_REVIEW_CAMPAIGN_SUPERSESSION_ACTOR_REQUIRED"),
        ("supersession_reason", "BULK_REVIEW_CAMPAIGN_SUPERSESSION_REASON_REQUIRED"),
        ("supersession_correlation_id", "BULK_REVIEW_CAMPAIGN_SUPERSESSION_CORRELATION_REQUIRED"),
        ("superseded_by_campaign_id", "BULK_REVIEW_CAMPAIGN_SUPERSESSION_CAMPAIGN_ID_REQUIRED"),
        (
            "superseded_by_campaign_version",
            "BULK_REVIEW_CAMPAIGN_SUPERSESSION_CAMPAIGN_VERSION_REQUIRED",
        ),
        ("superseded_by_content_hash", "BULK_REVIEW_CAMPAIGN_SUPERSESSION_CONTENT_HASH_REQUIRED"),
    ]:
        payload = {**superseded_base, field_name: None}
        with pytest.raises(ValueError, match=reason_code):
            DpmBulkReviewCampaignDefinition.model_validate(payload)

    with pytest.raises(
        ValueError,
        match="BULK_REVIEW_CAMPAIGN_SUPERSEDED_RETIREMENT_FIELDS_FORBIDDEN",
    ):
        DpmBulkReviewCampaignDefinition.model_validate(
            {**superseded_base, "retired_by": "ops", "content_hash": ""}
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


def test_campaign_definition_launch_history_is_append_only_and_idempotent() -> None:
    repository = InMemoryDpmBulkReviewCampaignDefinitionRepository()
    definition = _definition()
    repository.save_definition(definition=definition)

    launched = record_bulk_review_campaign_definition_launch(
        definition=definition,
        wave_id="dwv_campaign_launch_001",
        launched_by="pm_001",
        requested_as_of_date="2026-05-10",
        correlation_id="corr-campaign-definition-launch-001",
        idempotency_key="campaign-launch:campaign-holdings-apple-tesla-20260510:2026.05:ready",
        launched_at=datetime(2026, 5, 10, tzinfo=timezone.utc),
    )
    replayed = record_bulk_review_campaign_definition_launch(
        definition=launched,
        wave_id="dwv_campaign_launch_001",
        launched_by="pm_001",
        requested_as_of_date="2026-05-10",
        correlation_id="corr-campaign-definition-launch-001",
        idempotency_key="campaign-launch:campaign-holdings-apple-tesla-20260510:2026.05:ready",
    )

    returned = repository.record_definition_launch(definition=launched)

    assert returned == launched
    assert replayed == launched
    assert launched.content_hash != definition.content_hash
    assert len(launched.launch_history) == 1
    assert launched.launch_history[0].wave_id == "dwv_campaign_launch_001"
    assert (
        repository.get_definition(
            campaign_id=definition.campaign_id,
            campaign_version=definition.campaign_version,
        )
        == launched
    )
    assert repository.record_definition_launch(definition=launched) == launched
    assert (
        repository.record_definition_launch(
            definition=DpmBulkReviewCampaignDefinition.model_validate(
                {
                    **launched.model_dump(mode="python"),
                    "campaign_id": "missing-campaign",
                    "content_hash": "",
                }
            )
        )
        is None
    )


def test_campaign_definition_launch_history_page_is_bounded_audit_evidence() -> None:
    definition = record_bulk_review_campaign_definition_launch(
        definition=_definition(),
        wave_id="dwv_campaign_launch_001",
        launched_by="pm_001",
        requested_as_of_date="2026-05-10",
        correlation_id="corr-campaign-definition-launch-001",
        idempotency_key="campaign-launch:campaign-holdings-apple-tesla-20260510:2026.05:ready",
        launched_at=datetime(2026, 5, 10, tzinfo=timezone.utc),
    )

    page = build_bulk_review_campaign_definition_launch_history_page(
        definition=definition,
        limit=1,
        offset=0,
    )
    empty_page = build_bulk_review_campaign_definition_launch_history_page(
        definition=definition,
        limit=1,
        offset=1,
    )

    assert page.product_name == "BulkReviewCampaignDefinitionLaunchHistory"
    assert page.campaign_id == definition.campaign_id
    assert page.count == 1
    assert page.total_count == 1
    assert page.items[0].wave_id == "dwv_campaign_launch_001"
    assert "NO_ORDER_GENERATION" in page.operating_boundaries
    assert "NO_OMS_EXECUTION_CLAIM" in page.operating_boundaries
    assert empty_page.count == 0
    assert empty_page.total_count == 1


def test_campaign_definition_launch_command_is_ready_only() -> None:
    definition = _definition()

    command = build_bulk_review_campaign_definition_launch_command(
        definition=definition,
        requested_as_of_date="2026-05-10",
        actor_id="ops",
        correlation_id="corr-campaign-definition-launch-001",
    )

    assert command.create_request.trigger_type == "BULK_REVIEW_CAMPAIGN"
    assert command.create_request.campaign_definition_id == definition.campaign_id
    assert command.correlation_id == "corr-campaign-definition-launch-001"
    assert command.idempotency_key.startswith(
        "campaign-launch:campaign-holdings-apple-tesla-20260510:2026.05:"
    )
    assert command.launch_package.launch_state == "READY"

    expired = DpmBulkReviewCampaignDefinition.model_validate(
        {
            **definition.model_dump(mode="python"),
            "governance": {
                **definition.governance.model_dump(mode="python"),
                "expires_on": "2026-05-09",
            },
            "content_hash": "",
        }
    )
    with pytest.raises(DpmBulkReviewCampaignDefinitionLaunchBlocked) as blocked:
        build_bulk_review_campaign_definition_launch_command(
            definition=expired,
            requested_as_of_date="2026-05-10",
            actor_id="ops",
            correlation_id=None,
        )

    assert "BULK_REVIEW_CAMPAIGN_EXPIRED" in blocked.value.reason_codes
    assert blocked.value.readiness.preview_create_allowed is False


def test_campaign_definition_retirement_validation_and_in_memory_lifecycle() -> None:
    repository = InMemoryDpmBulkReviewCampaignDefinitionRepository()
    definition = _definition()
    repository.save_definition(definition=definition)

    with pytest.raises(
        ValueError,
        match="BULK_REVIEW_CAMPAIGN_ACTIVE_LIFECYCLE_FIELDS_FORBIDDEN",
    ):
        DpmBulkReviewCampaignDefinition.model_validate(
            {
                **definition.model_dump(mode="python"),
                "retired_by": "ops",
                "content_hash": "",
            }
        )

    retired = DpmBulkReviewCampaignDefinition.model_validate(
        {
            **definition.model_dump(mode="python"),
            "status": "RETIRED",
            "retired_at": "2026-05-11T08:00:00Z",
            "retired_by": "ops",
            "retirement_reason": "Campaign completed.",
            "retirement_correlation_id": "corr-campaign-definition-retire-001",
            "content_hash": "",
        }
    )

    returned = repository.retire_definition(definition=retired)

    assert returned is not None
    assert returned == retired
    assert returned.content_hash != definition.content_hash
    assert (
        repository.get_definition(
            campaign_id=definition.campaign_id,
            campaign_version=definition.campaign_version,
        )
        == retired
    )
    assert repository.list_definitions(status="ACTIVE") == []
    assert repository.list_definitions(status="RETIRED") == [retired]
    assert repository.retire_definition(definition=retired) == retired
    assert (
        repository.retire_definition(
            definition=DpmBulkReviewCampaignDefinition.model_validate(
                {
                    **retired.model_dump(mode="python"),
                    "campaign_id": "missing-campaign",
                    "content_hash": "",
                }
            )
        )
        is None
    )


def test_campaign_definition_supersession_validation_and_in_memory_lifecycle() -> None:
    repository = InMemoryDpmBulkReviewCampaignDefinitionRepository()
    original = _definition()
    replacement = _definition(display_name="Refreshed Apple and Tesla holdings review")
    replacement = DpmBulkReviewCampaignDefinition.model_validate(
        {
            **replacement.model_dump(mode="python"),
            "campaign_version": "2026.06",
            "content_hash": "",
        }
    )
    repository.save_definition(definition=original)
    repository.save_definition(definition=replacement)

    with pytest.raises(
        ValueError,
        match="BULK_REVIEW_CAMPAIGN_SUPERSESSION_CONTENT_HASH_REQUIRED",
    ):
        DpmBulkReviewCampaignDefinition.model_validate(
            {
                **original.model_dump(mode="python"),
                "status": "SUPERSEDED",
                "superseded_at": "2026-05-12T08:00:00Z",
                "superseded_by": "ops",
                "supersession_reason": "Campaign candidate set refreshed.",
                "supersession_correlation_id": "corr-campaign-definition-supersede-001",
                "superseded_by_campaign_id": replacement.campaign_id,
                "superseded_by_campaign_version": replacement.campaign_version,
                "content_hash": "",
            }
        )

    superseded = DpmBulkReviewCampaignDefinition.model_validate(
        {
            **original.model_dump(mode="python"),
            "status": "SUPERSEDED",
            "superseded_at": "2026-05-12T08:00:00Z",
            "superseded_by": "ops",
            "supersession_reason": "Campaign candidate set refreshed.",
            "supersession_correlation_id": "corr-campaign-definition-supersede-001",
            "superseded_by_campaign_id": replacement.campaign_id,
            "superseded_by_campaign_version": replacement.campaign_version,
            "superseded_by_content_hash": replacement.content_hash,
            "content_hash": "",
        }
    )

    returned = repository.supersede_definition(definition=superseded)

    assert returned is not None
    assert returned == superseded
    assert repository.list_definitions(status="ACTIVE") == [replacement]
    assert repository.list_definitions(status="SUPERSEDED") == [superseded]
    assert repository.supersede_definition(definition=superseded) == superseded
    assert (
        repository.supersede_definition(
            definition=DpmBulkReviewCampaignDefinition.model_validate(
                {
                    **superseded.model_dump(mode="python"),
                    "campaign_id": "missing-campaign",
                    "content_hash": "",
                }
            )
        )
        is None
    )


def test_campaign_definition_lifecycle_helpers_are_idempotent_and_fail_closed() -> None:
    repository = InMemoryDpmBulkReviewCampaignDefinitionRepository()
    original = _definition()
    replacement = DpmBulkReviewCampaignDefinition.model_validate(
        {
            **_definition(display_name="Refreshed Apple and Tesla holdings review").model_dump(
                mode="python"
            ),
            "campaign_version": "2026.06",
            "content_hash": "",
        }
    )
    repository.save_definition(definition=original)
    repository.save_definition(definition=replacement)

    assert (
        retire_bulk_review_campaign_definition(
            repository=repository,
            campaign_id="missing",
            campaign_version="2026.05",
            retired_by="ops",
            retirement_reason="Not found.",
            correlation_id="corr-retire-missing",
        )
        is None
    )
    superseded = supersede_bulk_review_campaign_definition(
        repository=repository,
        campaign_id=original.campaign_id,
        campaign_version=original.campaign_version,
        replacement_version=replacement.campaign_version,
        superseded_by="ops",
        supersession_reason="Campaign candidate set refreshed.",
        correlation_id="corr-supersede-original",
        superseded_at=datetime(2026, 5, 12, tzinfo=timezone.utc),
    )

    assert superseded is not None
    assert superseded.status == "SUPERSEDED"
    assert (
        supersede_bulk_review_campaign_definition(
            repository=repository,
            campaign_id=original.campaign_id,
            campaign_version=original.campaign_version,
            replacement_version=replacement.campaign_version,
            superseded_by="ops",
            supersession_reason="Already superseded.",
            correlation_id="corr-supersede-idempotent",
        )
        == superseded
    )
    with pytest.raises(
        DpmBulkReviewCampaignDefinitionLifecycleError,
        match="BULK_REVIEW_CAMPAIGN_DEFINITION_LIFECYCLE_CONFLICT",
    ):
        retire_bulk_review_campaign_definition(
            repository=repository,
            campaign_id=original.campaign_id,
            campaign_version=original.campaign_version,
            retired_by="ops",
            retirement_reason="Cannot retire superseded.",
            correlation_id="corr-retire-superseded",
        )
    with pytest.raises(
        DpmBulkReviewCampaignDefinitionLifecycleError,
        match="BULK_REVIEW_CAMPAIGN_SUPERSESSION_REPLACEMENT_VERSION_INVALID",
    ):
        supersede_bulk_review_campaign_definition(
            repository=repository,
            campaign_id=replacement.campaign_id,
            campaign_version=replacement.campaign_version,
            replacement_version=replacement.campaign_version,
            superseded_by="ops",
            supersession_reason="Invalid replacement.",
            correlation_id="corr-supersede-invalid-version",
        )
    with pytest.raises(
        DpmBulkReviewCampaignDefinitionLifecycleError,
        match="BULK_REVIEW_CAMPAIGN_SUPERSESSION_REPLACEMENT_NOT_FOUND",
    ):
        supersede_bulk_review_campaign_definition(
            repository=repository,
            campaign_id=replacement.campaign_id,
            campaign_version=replacement.campaign_version,
            replacement_version="2026.07",
            superseded_by="ops",
            supersession_reason="Missing replacement.",
            correlation_id="corr-supersede-missing-replacement",
        )

    assert (
        supersede_bulk_review_campaign_definition(
            repository=repository,
            campaign_id="missing",
            campaign_version="2026.05",
            replacement_version=replacement.campaign_version,
            superseded_by="ops",
            supersession_reason="Missing definition.",
            correlation_id="corr-supersede-missing-definition",
        )
        is None
    )

    retired_replacement = retire_bulk_review_campaign_definition(
        repository=repository,
        campaign_id=replacement.campaign_id,
        campaign_version=replacement.campaign_version,
        retired_by="ops",
        retirement_reason="Replacement completed.",
        correlation_id="corr-retire-replacement",
        retired_at=datetime(2026, 5, 13, tzinfo=timezone.utc),
    )
    assert retired_replacement is not None
    assert retired_replacement.status == "RETIRED"
    assert (
        retire_bulk_review_campaign_definition(
            repository=repository,
            campaign_id=replacement.campaign_id,
            campaign_version=replacement.campaign_version,
            retired_by="ops",
            retirement_reason="Already retired.",
            correlation_id="corr-retire-idempotent",
        )
        == retired_replacement
    )
    with pytest.raises(
        DpmBulkReviewCampaignDefinitionLifecycleError,
        match="BULK_REVIEW_CAMPAIGN_DEFINITION_LIFECYCLE_CONFLICT",
    ):
        supersede_bulk_review_campaign_definition(
            repository=repository,
            campaign_id=replacement.campaign_id,
            campaign_version=replacement.campaign_version,
            replacement_version="2026.08",
            superseded_by="ops",
            supersession_reason="Cannot supersede retired.",
            correlation_id="corr-supersede-retired",
        )

    not_active_repository = InMemoryDpmBulkReviewCampaignDefinitionRepository()
    not_active_original = _definition(campaign_id="campaign-not-active-replacement")
    not_active_replacement = DpmBulkReviewCampaignDefinition.model_validate(
        {
            **_definition(
                campaign_id="campaign-not-active-replacement",
                display_name="Retired replacement",
            ).model_dump(mode="python"),
            "campaign_version": "2026.06",
            "status": "RETIRED",
            "retired_at": "2026-05-13T08:00:00Z",
            "retired_by": "ops",
            "retirement_reason": "Replacement retired.",
            "retirement_correlation_id": "corr-retired-replacement",
            "content_hash": "",
        }
    )
    not_active_repository.save_definition(definition=not_active_original)
    not_active_repository.save_definition(definition=not_active_replacement)
    with pytest.raises(
        DpmBulkReviewCampaignDefinitionLifecycleError,
        match="BULK_REVIEW_CAMPAIGN_SUPERSESSION_REPLACEMENT_NOT_ACTIVE",
    ):
        supersede_bulk_review_campaign_definition(
            repository=not_active_repository,
            campaign_id=not_active_original.campaign_id,
            campaign_version=not_active_original.campaign_version,
            replacement_version=not_active_replacement.campaign_version,
            superseded_by="ops",
            supersession_reason="Replacement not active.",
            correlation_id="corr-supersede-not-active-replacement",
        )


def test_in_memory_campaign_definition_repository_rejects_direct_invalid_lifecycle_state() -> None:
    repository = InMemoryDpmBulkReviewCampaignDefinitionRepository()
    active = _definition()
    retired = DpmBulkReviewCampaignDefinition.model_validate(
        {
            **active.model_dump(mode="python"),
            "status": "RETIRED",
            "retired_at": "2026-05-11T08:00:00Z",
            "retired_by": "ops",
            "retirement_reason": "Campaign completed.",
            "retirement_correlation_id": "corr-campaign-definition-retire-001",
            "content_hash": "",
        }
    )
    superseded = DpmBulkReviewCampaignDefinition.model_validate(
        {
            **active.model_dump(mode="python"),
            "status": "SUPERSEDED",
            "superseded_at": "2026-05-12T08:00:00Z",
            "superseded_by": "ops",
            "supersession_reason": "Campaign candidate set refreshed.",
            "supersession_correlation_id": "corr-campaign-definition-supersede-001",
            "superseded_by_campaign_id": active.campaign_id,
            "superseded_by_campaign_version": "2026.06",
            "superseded_by_content_hash": "sha256:replacement",
            "content_hash": "",
        }
    )
    repository.save_definition(definition=retired)
    with pytest.raises(
        DpmBulkReviewCampaignDefinitionConflictError,
        match="BULK_REVIEW_CAMPAIGN_DEFINITION_LIFECYCLE_CONFLICT",
    ):
        repository.supersede_definition(definition=superseded)

    repository = InMemoryDpmBulkReviewCampaignDefinitionRepository()
    repository.save_definition(definition=superseded)
    with pytest.raises(
        DpmBulkReviewCampaignDefinitionConflictError,
        match="BULK_REVIEW_CAMPAIGN_DEFINITION_LIFECYCLE_CONFLICT",
    ):
        repository.retire_definition(definition=retired)


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


def test_postgres_campaign_definition_repository_retires_active_definition() -> None:
    definition = _definition()
    retired = DpmBulkReviewCampaignDefinition.model_validate(
        {
            **definition.model_dump(mode="python"),
            "status": "RETIRED",
            "retired_at": "2026-05-11T08:00:00Z",
            "retired_by": "ops",
            "retirement_reason": "Campaign completed.",
            "retirement_correlation_id": "corr-campaign-definition-retire-001",
            "content_hash": "",
        }
    )
    repository = object.__new__(PostgresDpmBulkReviewCampaignDefinitionRepository)
    connection = _Connection(
        [
            _Cursor(
                row={
                    "status": "ACTIVE",
                    "payload_json": definition.model_dump(mode="json"),
                }
            ),
            _Cursor(),
        ]
    )
    repository._connect = lambda: connection  # type: ignore[attr-defined, method-assign]

    assert repository.retire_definition(definition=retired) == retired
    assert connection.committed is True


def test_postgres_campaign_definition_repository_supersedes_active_definition() -> None:
    definition = _definition()
    replacement = DpmBulkReviewCampaignDefinition.model_validate(
        {
            **_definition(display_name="Refreshed Apple and Tesla holdings review").model_dump(
                mode="python"
            ),
            "campaign_version": "2026.06",
            "content_hash": "",
        }
    )
    superseded = DpmBulkReviewCampaignDefinition.model_validate(
        {
            **definition.model_dump(mode="python"),
            "status": "SUPERSEDED",
            "superseded_at": "2026-05-12T08:00:00Z",
            "superseded_by": "ops",
            "supersession_reason": "Campaign candidate set refreshed.",
            "supersession_correlation_id": "corr-campaign-definition-supersede-001",
            "superseded_by_campaign_id": replacement.campaign_id,
            "superseded_by_campaign_version": replacement.campaign_version,
            "superseded_by_content_hash": replacement.content_hash,
            "content_hash": "",
        }
    )
    repository = object.__new__(PostgresDpmBulkReviewCampaignDefinitionRepository)
    connection = _Connection(
        [
            _Cursor(
                row={
                    "status": "ACTIVE",
                    "payload_json": definition.model_dump(mode="json"),
                }
            ),
            _Cursor(),
        ]
    )
    repository._connect = lambda: connection  # type: ignore[attr-defined, method-assign]

    assert repository.supersede_definition(definition=superseded) == superseded
    assert connection.committed is True


def test_postgres_campaign_definition_repository_records_launch_history() -> None:
    definition = _definition()
    launched = record_bulk_review_campaign_definition_launch(
        definition=definition,
        wave_id="dwv_campaign_launch_001",
        launched_by="pm_001",
        requested_as_of_date="2026-05-10",
        correlation_id="corr-campaign-definition-launch-001",
        idempotency_key="campaign-launch:campaign-holdings-apple-tesla-20260510:2026.05:ready",
        launched_at=datetime(2026, 5, 10, tzinfo=timezone.utc),
    )
    repository = object.__new__(PostgresDpmBulkReviewCampaignDefinitionRepository)
    connection = _Connection(
        [
            _Cursor(
                row={
                    "status": "ACTIVE",
                    "content_hash": definition.content_hash,
                    "payload_json": definition.model_dump(mode="json"),
                }
            ),
            _Cursor(),
        ]
    )
    repository._connect = lambda: connection  # type: ignore[attr-defined, method-assign]

    assert repository.record_definition_launch(definition=launched) == launched
    assert connection.committed is True


def test_postgres_campaign_definition_repository_retirement_edges() -> None:
    definition = _definition()
    repository = object.__new__(PostgresDpmBulkReviewCampaignDefinitionRepository)
    missing_connection = _Connection([_Cursor(row=None)])
    repository._connect = lambda: missing_connection  # type: ignore[attr-defined, method-assign]

    assert repository.retire_definition(definition=definition) is None
    assert missing_connection.rolled_back is True

    retired = DpmBulkReviewCampaignDefinition.model_validate(
        {
            **definition.model_dump(mode="python"),
            "status": "RETIRED",
            "retired_at": "2026-05-11T08:00:00Z",
            "retired_by": "ops",
            "retirement_reason": "Campaign completed.",
            "retirement_correlation_id": "corr-campaign-definition-retire-001",
            "content_hash": "",
        }
    )
    retired_connection = _Connection(
        [
            _Cursor(
                row={
                    "status": "RETIRED",
                    "payload_json": retired.model_dump(mode="json"),
                }
            )
        ]
    )
    repository._connect = lambda: retired_connection  # type: ignore[attr-defined, method-assign]

    assert repository.retire_definition(definition=retired) == retired
    assert retired_connection.rolled_back is True


def test_postgres_campaign_definition_repository_lifecycle_conflict_edges() -> None:
    definition = _definition()
    retired = DpmBulkReviewCampaignDefinition.model_validate(
        {
            **definition.model_dump(mode="python"),
            "status": "RETIRED",
            "retired_at": "2026-05-11T08:00:00Z",
            "retired_by": "ops",
            "retirement_reason": "Campaign completed.",
            "retirement_correlation_id": "corr-campaign-definition-retire-001",
            "content_hash": "",
        }
    )
    superseded = DpmBulkReviewCampaignDefinition.model_validate(
        {
            **definition.model_dump(mode="python"),
            "status": "SUPERSEDED",
            "superseded_at": "2026-05-12T08:00:00Z",
            "superseded_by": "ops",
            "supersession_reason": "Campaign candidate set refreshed.",
            "supersession_correlation_id": "corr-campaign-definition-supersede-001",
            "superseded_by_campaign_id": definition.campaign_id,
            "superseded_by_campaign_version": "2026.06",
            "superseded_by_content_hash": "sha256:replacement",
            "content_hash": "",
        }
    )
    failed_update = _Cursor()
    failed_update.rowcount = 0
    repository = object.__new__(PostgresDpmBulkReviewCampaignDefinitionRepository)
    retire_connection = _Connection(
        [
            _Cursor(row={"status": "ACTIVE", "payload_json": definition.model_dump(mode="json")}),
            failed_update,
        ]
    )
    repository._connect = lambda: retire_connection  # type: ignore[attr-defined, method-assign]

    with pytest.raises(
        DpmBulkReviewCampaignDefinitionConflictError,
        match="BULK_REVIEW_CAMPAIGN_DEFINITION_LIFECYCLE_CONFLICT",
    ):
        repository.retire_definition(definition=retired)
    assert retire_connection.rolled_back is True

    failed_supersede = _Cursor()
    failed_supersede.rowcount = 0
    supersede_connection = _Connection(
        [
            _Cursor(row={"status": "ACTIVE", "payload_json": definition.model_dump(mode="json")}),
            failed_supersede,
        ]
    )
    repository._connect = lambda: supersede_connection  # type: ignore[attr-defined, method-assign]

    with pytest.raises(
        DpmBulkReviewCampaignDefinitionConflictError,
        match="BULK_REVIEW_CAMPAIGN_DEFINITION_LIFECYCLE_CONFLICT",
    ):
        repository.supersede_definition(definition=superseded)
    assert supersede_connection.rolled_back is True

    superseded_connection = _Connection(
        [
            _Cursor(
                row={
                    "status": "SUPERSEDED",
                    "payload_json": superseded.model_dump(mode="json"),
                }
            )
        ]
    )
    repository._connect = lambda: superseded_connection  # type: ignore[attr-defined, method-assign]

    assert repository.supersede_definition(definition=superseded) == superseded
    assert superseded_connection.rolled_back is True

    missing_supersede_connection = _Connection([_Cursor(row=None)])
    repository._connect = lambda: missing_supersede_connection  # type: ignore[attr-defined, method-assign]

    assert repository.supersede_definition(definition=superseded) is None
    assert missing_supersede_connection.rolled_back is True


def test_postgres_campaign_definition_repository_init_guards(monkeypatch) -> None:
    with pytest.raises(RuntimeError, match="DPM_CAMPAIGN_DEFINITION_POSTGRES_DSN_REQUIRED"):
        PostgresDpmBulkReviewCampaignDefinitionRepository(dsn="")

    monkeypatch.setattr(campaign_definition_infra, "has_psycopg", lambda: False)
    with pytest.raises(RuntimeError, match="DPM_CAMPAIGN_DEFINITION_POSTGRES_DRIVER_MISSING"):
        PostgresDpmBulkReviewCampaignDefinitionRepository(dsn="postgresql://campaigns")


def test_postgres_campaign_definition_repository_connects_and_initializes(monkeypatch) -> None:
    first_expected_connection = _Connection([_Cursor()])
    init_expected_connection = _Connection([_Cursor()])
    connections = [first_expected_connection, init_expected_connection]
    connect_calls: list[tuple[str, object]] = []
    migrations: list[tuple[_Connection, str]] = []
    dict_row = object()

    class FakePsycopg:
        @staticmethod
        def connect(dsn: str, *, row_factory: object) -> _Connection:
            connect_calls.append((dsn, row_factory))
            return connections.pop(0)

    monkeypatch.setattr(
        campaign_definition_infra,
        "_import_psycopg",
        lambda: (FakePsycopg, dict_row),
    )
    monkeypatch.setattr(
        campaign_definition_infra,
        "apply_postgres_migrations",
        lambda *, connection, namespace: migrations.append((connection, namespace)),
    )
    repository = object.__new__(PostgresDpmBulkReviewCampaignDefinitionRepository)
    repository._dsn = "postgresql://campaigns"

    first_connection = repository._connect()
    repository._init_db()

    assert first_connection is first_expected_connection
    assert connect_calls == [
        ("postgresql://campaigns", dict_row),
        ("postgresql://campaigns", dict_row),
    ]
    assert migrations == [(init_expected_connection, "dpm")]


def test_postgres_campaign_definition_repository_init_stores_dsn(monkeypatch) -> None:
    init_calls: list[str] = []

    monkeypatch.setattr(campaign_definition_infra, "has_psycopg", lambda: True)
    monkeypatch.setattr(
        PostgresDpmBulkReviewCampaignDefinitionRepository,
        "_init_db",
        lambda self: init_calls.append(self._dsn),
    )

    repository = PostgresDpmBulkReviewCampaignDefinitionRepository(dsn="postgresql://campaigns")

    assert repository._dsn == "postgresql://campaigns"
    assert init_calls == ["postgresql://campaigns"]


def test_postgres_campaign_definition_payload_and_driver_import_edges() -> None:
    assert _payload({"payload_json": "raw-json"}) == "raw-json"
    psycopg, dict_row = _import_psycopg()

    assert psycopg is not None
    assert dict_row is not None


def test_postgres_campaign_definition_repository_returns_none_for_missing_definition() -> None:
    repository = object.__new__(PostgresDpmBulkReviewCampaignDefinitionRepository)
    connection = _Connection([_Cursor(row=None)])
    repository._connect = lambda: connection  # type: ignore[attr-defined, method-assign]

    assert (
        repository.get_definition(
            campaign_id="missing",
            campaign_version="2026.05",
        )
        is None
    )


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
