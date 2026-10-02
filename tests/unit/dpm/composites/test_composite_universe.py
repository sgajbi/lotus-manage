from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.api.services.composite_membership_application import (
    DpmCompositeMembershipApplicationService,
    DpmCompositeUniverseAttestationCommand,
)
from src.core.composite_membership import (
    DpmCompositeDefinition,
    DpmCompositeMembershipDecision,
    DpmCompositeMembershipRevision,
    DpmCompositeSourceAuthority,
)
from src.core.composite_repository import DpmCompositeConflictError
from src.core.composite_universe import DpmCompositeUniverseSourceProduct
from src.infrastructure.composites.in_memory import InMemoryDpmCompositeRepository


def _service() -> tuple[DpmCompositeMembershipApplicationService, DpmCompositeMembershipRevision]:
    repository = InMemoryDpmCompositeRepository()
    repository.save_definition(
        definition=DpmCompositeDefinition(
            tenant_id="tenant-sg",
            composite_id="GLOBAL_BALANCED",
            definition_version="2026.10",
            display_name="Global Balanced",
            strategy_code="GLOBAL_BALANCED",
            reporting_currency="USD",
            inception_date="2026-01-01",
            eligibility_policy_version="eligibility.v1",
            source_authority=DpmCompositeSourceAuthority(policy_version="authority.v1"),
            created_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
            created_by="maker",
            correlation_id="corr-definition",
        )
    )
    revision = DpmCompositeMembershipRevision(
        tenant_id="tenant-sg",
        composite_id="GLOBAL_BALANCED",
        definition_version="2026.10",
        membership_revision="2026.10.1",
        policy_version="eligibility.v1",
        source_cut_id="manage-universe-cut-001",
        decisions=[
            DpmCompositeMembershipDecision(
                portfolio_id="PORTFOLIO_A",
                effective_from="2026-01-01",
                effective_to="2026-01-31",
                source_snapshot_id="snapshot-001",
            ),
            DpmCompositeMembershipDecision(
                portfolio_id="PORTFOLIO_A",
                effective_from="2026-02-01",
                status="EXCLUDED",
                reason_code="PROSPECTIVE_EXCLUSION",
                source_snapshot_id="snapshot-002",
            ),
            DpmCompositeMembershipDecision(
                portfolio_id="PORTFOLIO_B",
                effective_from="2026-01-01",
                source_snapshot_id="snapshot-001",
            ),
        ],
        decided_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
        decided_by="committee",
        correlation_id="corr-membership",
    )
    repository.save_membership_revision(revision=revision)
    return DpmCompositeMembershipApplicationService(repository=repository), revision


def _command(**updates: object) -> DpmCompositeUniverseAttestationCommand:
    values: dict[str, object] = {
        "tenant_id": "tenant-sg",
        "composite_id": "GLOBAL_BALANCED",
        "definition_version": "2026.10",
        "membership_revision": "2026.10.1",
        "attestation_version": "2026.10.1",
        "coverage_from": "2026-01-01",
        "coverage_to": "2026-03-31",
        "policy_version": "eligibility.v1",
        "source_cut_id": "manage-universe-cut-001",
        "source_products": [
            DpmCompositeUniverseSourceProduct(
                owner_service="lotus-manage",
                product_name="CompositeEligibilityUniverse",
                contract_version="v1",
                authority_scope="AUTHORITATIVE_UNIVERSE",
                source_cut_id="manage-universe-cut-001",
                source_watermark="universe-sequence:1",
                content_hash="sha256:universe-001",
            )
        ],
        "posture": "COMPLETE",
        "expected_portfolio_ids": ["PORTFOLIO_B", "PORTFOLIO_A"],
        "reason_code": None,
        "actor_id": "checker",
        "correlation_id": "corr-attestation",
    }
    values.update(updates)
    return DpmCompositeUniverseAttestationCommand(**values)  # type: ignore[arg-type]


def test_complete_attestation_requires_exact_continuous_effective_dated_coverage() -> None:
    service, revision = _service()

    attestation = service.save_universe_attestation(command=_command())
    replay = service.save_universe_attestation(command=_command())

    assert replay == attestation
    assert attestation.membership_content_hash == revision.content_hash
    assert attestation.expected_portfolio_ids == ["PORTFOLIO_A", "PORTFOLIO_B"]
    assert attestation.expected_portfolio_count == attestation.observed_portfolio_count == 2
    assert attestation.missing_portfolio_ids == []
    assert attestation.unexpected_portfolio_ids == []
    assert attestation.coverage_gap_portfolio_ids == []
    assert attestation.content_hash

    with pytest.raises(DpmCompositeConflictError, match="COMPOSITE_UNIVERSE_COMPLETENESS_MISMATCH"):
        service.save_universe_attestation(
            command=_command(
                attestation_version="missing-member",
                expected_portfolio_ids=["PORTFOLIO_A", "PORTFOLIO_B", "PORTFOLIO_C"],
            )
        )
    with pytest.raises(DpmCompositeConflictError, match="COMPOSITE_UNIVERSE_COMPLETENESS_MISMATCH"):
        service.save_universe_attestation(
            command=_command(
                attestation_version="date-gap",
                coverage_from="2025-12-31",
            )
        )


def test_incomplete_and_unavailable_postures_are_explicit_and_immutable() -> None:
    service, _ = _service()
    incomplete = service.save_universe_attestation(
        command=_command(
            attestation_version="incomplete-001",
            posture="INCOMPLETE",
            expected_portfolio_ids=["PORTFOLIO_A", "PORTFOLIO_B", "PORTFOLIO_C"],
            reason_code="SOURCE_MEMBER_MISSING",
        )
    )
    assert incomplete.missing_portfolio_ids == ["PORTFOLIO_C"]
    assert incomplete.posture == "INCOMPLETE"

    unavailable = service.save_universe_attestation(
        command=_command(
            attestation_version="unavailable-001",
            posture="UNAVAILABLE",
            expected_portfolio_ids=[],
            reason_code="SOURCE_CUT_UNAVAILABLE",
        )
    )
    assert unavailable.posture == "UNAVAILABLE"
    assert unavailable.expected_portfolio_count == 0
    assert unavailable.observed_portfolio_count == 2
    assert unavailable.unexpected_portfolio_ids == []

    with pytest.raises(
        DpmCompositeConflictError,
        match="COMPOSITE_UNIVERSE_ATTESTATION_IMMUTABLE_CONFLICT",
    ):
        service.save_universe_attestation(
            command=_command(
                attestation_version="unavailable-001",
                posture="UNAVAILABLE",
                expected_portfolio_ids=[],
                reason_code="DIFFERENT_REASON",
            )
        )


@pytest.mark.parametrize(
    ("updates", "error"),
    [
        ({"policy_version": "eligibility.v2"}, "COMPOSITE_UNIVERSE_POLICY_VERSION_MISMATCH"),
        ({"source_cut_id": "different-cut"}, "COMPOSITE_UNIVERSE_SOURCE_CUT_MISMATCH"),
        (
            {"expected_portfolio_ids": ["PORTFOLIO_A", "PORTFOLIO_A"]},
            "COMPOSITE_UNIVERSE_PORTFOLIO_ID_DUPLICATE",
        ),
        (
            {"posture": "INCOMPLETE", "reason_code": "SOURCE_GAP"},
            "COMPOSITE_UNIVERSE_INCOMPLETE_CONTRADICTED",
        ),
    ],
)
def test_attestation_refuses_mismatched_authority_or_contradictory_posture(
    updates: dict[str, object], error: str
) -> None:
    service, _ = _service()
    with pytest.raises(ValueError, match=error):
        service.save_universe_attestation(command=_command(**updates))


def test_complete_attestation_requires_one_matching_authoritative_source_watermark() -> None:
    service, _ = _service()
    source = _command().source_products[0]
    with pytest.raises(ValueError, match="COMPOSITE_UNIVERSE_AUTHORITATIVE_SOURCE_REQUIRED"):
        service.save_universe_attestation(
            command=_command(
                attestation_version="policy-only",
                source_products=[source.model_copy(update={"authority_scope": "POLICY_INPUT"})],
            )
        )
    with pytest.raises(ValueError, match="COMPOSITE_UNIVERSE_AUTHORITATIVE_SOURCE_CUT_MISMATCH"):
        service.save_universe_attestation(
            command=_command(
                attestation_version="wrong-authority-cut",
                source_products=[source.model_copy(update={"source_cut_id": "different-cut"})],
            )
        )
