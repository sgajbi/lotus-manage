from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import patch

import pytest

from src.core.composite_membership import (
    DpmCompositeDefinition,
    DpmCompositeMembershipDecision,
    DpmCompositeMembershipRevision,
    DpmCompositeSourceAuthority,
    composite_definition_hash,
    composite_membership_revision_hash,
)
from src.core.composite_repository import DpmCompositeConflictError
from src.core.composite_publication import DpmCompositePublicationReceipt
from src.infrastructure.composites.in_memory import InMemoryDpmCompositeRepository
from src.infrastructure.composites.postgres import PostgresDpmCompositeRepository, _payload


def _authority() -> DpmCompositeSourceAuthority:
    return DpmCompositeSourceAuthority(policy_version="composite-source-authority.v1")


def _definition(**updates: Any) -> DpmCompositeDefinition:
    values: dict[str, Any] = {
        "tenant_id": "tenant-sg",
        "composite_id": "PB_GLOBAL_BALANCED_USD",
        "definition_version": "2026.10",
        "display_name": "Private Banking Global Balanced USD Composite",
        "strategy_code": "GLOBAL_BALANCED",
        "reporting_currency": "usd",
        "inception_date": "2024-01-01",
        "eligibility_policy_version": "composite-eligibility.v1",
        "source_authority": _authority(),
        "created_at": datetime(2026, 10, 1, tzinfo=timezone.utc),
        "created_by": "pm-ops",
        "correlation_id": "corr-composite-definition",
    }
    values.update(updates)
    return DpmCompositeDefinition(**values)


def _decision(**updates: Any) -> DpmCompositeMembershipDecision:
    values: dict[str, Any] = {
        "portfolio_id": "PB_SG_GLOBAL_BAL_001",
        "effective_from": "2026-01-01",
        "status": "INCLUDED",
        "source_snapshot_id": "manage-membership-source-2026-01-01",
    }
    values.update(updates)
    return DpmCompositeMembershipDecision(**values)


def _revision(**updates: Any) -> DpmCompositeMembershipRevision:
    values: dict[str, Any] = {
        "tenant_id": "tenant-sg",
        "composite_id": "PB_GLOBAL_BALANCED_USD",
        "definition_version": "2026.10",
        "membership_revision": "2026.10.1",
        "policy_version": "composite-eligibility.v1",
        "source_cut_id": "core-cut-2026-10-01",
        "decisions": [_decision()],
        "decided_at": datetime(2026, 10, 1, tzinfo=timezone.utc),
        "decided_by": "composite-committee",
        "correlation_id": "corr-composite-membership",
    }
    values.update(updates)
    return DpmCompositeMembershipRevision(**values)


def test_definition_normalizes_currency_and_hashes_immutable_payload() -> None:
    definition = _definition()

    assert definition.reporting_currency == "USD"
    assert definition.content_hash == composite_definition_hash(definition)
    assert _definition(content_hash=definition.content_hash) == definition
    with pytest.raises(ValueError, match="COMPOSITE_DEFINITION_HASH_MISMATCH"):
        _definition(content_hash="sha256:not-this-definition")


@pytest.mark.parametrize(
    ("updates", "reason_code"),
    [
        ({"reporting_currency": " usd"}, "COMPOSITE_DEFINITION_REPORTING_CURRENCY_INVALID"),
        ({"inception_date": "not-a-date"}, "COMPOSITE_DEFINITION_INCEPTION_DATE_INVALID"),
        (
            {"termination_date": "2023-12-31"},
            "COMPOSITE_DEFINITION_TERMINATION_BEFORE_INCEPTION",
        ),
        ({"created_by": " "}, "COMPOSITE_DEFINITION_REQUIRED_TEXT"),
    ],
)
def test_definition_rejects_invalid_authority_or_temporal_identity(
    updates: dict[str, object], reason_code: str
) -> None:
    with pytest.raises(ValueError, match=reason_code):
        _definition(**updates)
    with pytest.raises(ValueError, match="COMPOSITE_SOURCE_AUTHORITY_POLICY_VERSION_REQUIRED"):
        DpmCompositeSourceAuthority(policy_version=" ")


def test_membership_decision_preserves_inclusion_and_refusal_semantics() -> None:
    included = _decision()
    excluded = _decision(
        portfolio_id="PB_SG_GLOBAL_BAL_002",
        status="EXCLUDED",
        reason_code="MINIMUM_ASSET_NOT_MET",
        effective_to="2026-06-30",
        discretionary=False,
    )
    assert included.reason_code is None
    assert excluded.status == "EXCLUDED"

    with pytest.raises(ValueError, match="COMPOSITE_MEMBERSHIP_REASON_REQUIRED"):
        _decision(status="PENDING_REVIEW")
    with pytest.raises(ValueError, match="COMPOSITE_MEMBERSHIP_INCLUDED_REASON_FORBIDDEN"):
        _decision(reason_code="NOT_ALLOWED")
    with pytest.raises(ValueError, match="COMPOSITE_MEMBERSHIP_EFFECTIVE_WINDOW_INVALID"):
        _decision(effective_to="2025-12-31")


def test_membership_revision_requires_non_overlapping_windows_and_correction_lineage() -> None:
    revision = _revision()
    assert revision.content_hash == composite_membership_revision_hash(revision)
    assert _revision(content_hash=revision.content_hash) == revision

    non_overlapping = _revision(
        decisions=[
            _decision(effective_to="2026-03-31"),
            _decision(
                effective_from="2026-04-01",
                status="EXCLUDED",
                reason_code="PORTFOLIO_TERMINATED",
            ),
        ]
    )
    assert len(non_overlapping.decisions) == 2
    with pytest.raises(ValueError, match="COMPOSITE_MEMBERSHIP_DECISION_WINDOW_OVERLAP"):
        _revision(
            decisions=[
                _decision(effective_to="2026-03-31"),
                _decision(
                    effective_from="2026-03-31",
                    status="EXCLUDED",
                    reason_code="PORTFOLIO_TERMINATED",
                ),
            ]
        )
    with pytest.raises(ValueError, match="COMPOSITE_MEMBERSHIP_CORRECTION_WINDOW_INCOMPLETE"):
        _revision(affected_from="2026-02-01")
    with pytest.raises(ValueError, match="COMPOSITE_MEMBERSHIP_CORRECTION_SUPERSEDES_REQUIRED"):
        _revision(affected_from="2026-02-01", affected_to="2026-02-28")
    with pytest.raises(ValueError, match="COMPOSITE_MEMBERSHIP_CORRECTION_WINDOW_REQUIRED"):
        _revision(supersedes_membership_revision="2026.10.1")
    with pytest.raises(ValueError, match="COMPOSITE_MEMBERSHIP_CORRECTION_WINDOW_INVALID"):
        _revision(
            supersedes_membership_revision="2026.10.1",
            affected_from="2026-03-01",
            affected_to="2026-02-28",
        )
    corrected = _revision(
        membership_revision="2026.10.2",
        supersedes_membership_revision="2026.10.1",
        affected_from="2026-02-01",
        affected_to="2026-02-28",
    )
    assert corrected.supersedes_membership_revision == "2026.10.1"
    with pytest.raises(ValueError, match="COMPOSITE_MEMBERSHIP_REVISION_HASH_MISMATCH"):
        _revision(content_hash="sha256:not-this-revision")


def test_repository_fences_tenants_replays_and_membership_revision_lineage() -> None:
    repository = InMemoryDpmCompositeRepository()
    definition = _definition()
    repository.save_definition(definition=definition)
    repository.save_definition(definition=definition)
    assert (
        repository.get_definition(
            tenant_id="tenant-other",
            composite_id=definition.composite_id,
            definition_version=definition.definition_version,
        )
        is None
    )
    definition_page = repository.list_definitions(tenant_id="tenant-sg", limit=1, offset=0)
    assert definition_page.items == [definition]
    assert definition_page.count == 1
    with pytest.raises(DpmCompositeConflictError, match="COMPOSITE_DEFINITION_IMMUTABLE_CONFLICT"):
        repository.save_definition(definition=_definition(display_name="Changed composite"))

    revision = _revision()
    repository.save_membership_revision(revision=revision)
    repository.save_membership_revision(revision=revision)
    assert (
        repository.get_membership_revision(
            tenant_id="tenant-other",
            composite_id=revision.composite_id,
            definition_version=revision.definition_version,
            membership_revision=revision.membership_revision,
        )
        is None
    )
    first_page = repository.list_membership_revisions(
        tenant_id="tenant-sg",
        composite_id=revision.composite_id,
        definition_version=revision.definition_version,
        limit=1,
        offset=0,
    )
    assert first_page.items == [revision]
    assert first_page.count == 1
    with pytest.raises(
        DpmCompositeConflictError, match="COMPOSITE_MEMBERSHIP_REVISION_IMMUTABLE_CONFLICT"
    ):
        repository.save_membership_revision(
            revision=_revision(policy_version="composite-eligibility.v2")
        )

    corrected = _revision(
        membership_revision="2026.10.2",
        supersedes_membership_revision=revision.membership_revision,
        affected_from="2026-02-01",
        affected_to="2026-02-28",
    )
    repository.save_membership_revision(revision=corrected)
    history_page = repository.list_membership_revisions(
        tenant_id="tenant-sg",
        composite_id=revision.composite_id,
        definition_version=revision.definition_version,
        limit=10,
        offset=0,
    )
    assert history_page.items == [corrected, revision]
    assert history_page.count == 2
    assert (
        repository.list_membership_revisions(
            tenant_id="tenant-sg",
            composite_id=revision.composite_id,
            definition_version=revision.definition_version,
            limit=1,
            offset=2,
        ).count
        == 2
    )


def test_repository_rejects_membership_without_definition_or_known_superseded_revision() -> None:
    repository = InMemoryDpmCompositeRepository()
    with pytest.raises(
        DpmCompositeConflictError, match="COMPOSITE_MEMBERSHIP_DEFINITION_NOT_FOUND"
    ):
        repository.save_membership_revision(revision=_revision())

    repository.save_definition(definition=_definition())
    missing_parent = _revision(
        membership_revision="2026.10.2",
        supersedes_membership_revision="2026.10.1",
        affected_from="2026-02-01",
        affected_to="2026-02-28",
    )
    with pytest.raises(
        DpmCompositeConflictError, match="COMPOSITE_MEMBERSHIP_SUPERSEDED_REVISION_NOT_FOUND"
    ):
        repository.save_membership_revision(revision=missing_parent)


def test_repository_refuses_receipt_without_tenant_owned_publication() -> None:
    repository = InMemoryDpmCompositeRepository()
    receipt = DpmCompositePublicationReceipt(
        tenant_id="tenant-sg",
        publication_sequence=1,
        membership_content_hash="sha256:missing-publication",
        consumer_id="lotus-performance",
        receipt_evidence_hash="sha256:retrieval-evidence",
        disposition="RECEIVED",
        received_at=datetime(2026, 10, 2, tzinfo=timezone.utc),
        correlation_id="corr-receipt",
    )

    with pytest.raises(DpmCompositeConflictError, match="COMPOSITE_PUBLICATION_NOT_FOUND"):
        repository.save_receipt(receipt=receipt)


def test_postgres_repository_fails_closed_when_its_required_runtime_capability_is_missing() -> None:
    with pytest.raises(RuntimeError, match="DPM_COMPOSITE_POSTGRES_DSN_REQUIRED"):
        PostgresDpmCompositeRepository(dsn="")

    with patch("src.infrastructure.composites.postgres.has_psycopg", return_value=False):
        with pytest.raises(RuntimeError, match="DPM_COMPOSITE_POSTGRES_DRIVER_MISSING"):
            PostgresDpmCompositeRepository(dsn="postgresql://example")


def test_postgres_payload_serializes_non_native_json_values_deterministically() -> None:
    assert _payload({"payload_json": datetime(2026, 10, 1, tzinfo=timezone.utc)}) == (
        '"2026-10-01 00:00:00+00:00"'
    )
