"""Explicit synthetic monthly source and legacy custody fixtures; no upstream qualification."""

from datetime import datetime, timezone
from src.core.common.canonical import hash_canonical_payload
from src.core.composite_eligibility.observations import MonthlyEligibilityObservations
from src.core.composite_membership import (
    DpmCompositeDefinition,
    DpmCompositeMembershipDecision,
    DpmCompositeMembershipRevision,
    DpmCompositeSourceAuthority,
)
from src.core.composite_universe import (
    DpmCompositeUniverseAttestation,
    DpmCompositeUniverseSourceProduct,
)
from src.infrastructure.composites.in_memory import InMemoryDpmCompositeRepository

BASE = "/api/v1/rebalance/composites/synthetic-composite/definitions/synthetic-definition/monthly-eligibility"
HEADERS = {
    "X-Tenant-Id": "synthetic-tenant",
    "X-Actor-Id": "synthetic-maker",
    "X-Role": "DPM_COMPOSITE_ADMIN",
}


def source_snapshot() -> MonthlyEligibilityObservations:
    return MonthlyEligibilityObservations.model_validate(
        {
            "product_name": "CompositeMonthlyEligibilityObservations",
            "product_version": "v1",
            "evidence_class": "SYNTHETIC_UNQUALIFIED",
            "tenant_id": "synthetic-tenant",
            "composite_id": "synthetic-composite",
            "definition_version": "synthetic-definition",
            "month": "2026-09",
            "source_cut_id": "synthetic-monthly-cut",
            "source_revision": "synthetic-source-r1",
            "reporting_currency": "USD",
            "source_generated_at": "2026-10-01T00:00:00.000000Z",
            "expected_portfolio_ids": ["synthetic-member"],
            "portfolios": [
                {
                    "portfolio_id": "synthetic-member",
                    "currency": "USD",
                    "prior_month_end_assets": "1000",
                    "prior_assets_as_of": "2026-08-31",
                    "month_end_assets": "1000",
                    "settled_unencumbered_cash": "50",
                    "cash_as_of": "2026-09-30",
                    "discretionary": True,
                    "funded": True,
                    "invested": True,
                    "readiness_as_of": "2026-09-30",
                    "flow_coverage_from": "2026-09-01",
                    "flow_coverage_to": "2026-09-30",
                    "flows": [
                        {
                            "event_id": f"synthetic-flow-{index}",
                            "business_date": "2026-09-15",
                            "received_at": "2026-10-01T00:00:00.000000Z",
                            "currency": "USD",
                            "amount": amount,
                            "classification": "EXTERNAL_CASH",
                            "status": "POSTED",
                            "reverses_event_id": None,
                        }
                        for index, amount in enumerate(("150", "-100"))
                    ],
                }
            ],
        }
    )


def retained_repository(
    snapshot: MonthlyEligibilityObservations,
    *,
    coverage_from="2026-09-01",
    coverage_to="2026-09-30",
):
    repository = InMemoryDpmCompositeRepository()
    scope = {
        "tenant_id": snapshot.tenant_id,
        "composite_id": snapshot.composite_id,
        "definition_version": snapshot.definition_version,
    }
    repository.save_definition(
        definition=DpmCompositeDefinition(
            **scope,
            display_name="Synthetic Composite",
            strategy_code="synthetic-strategy",
            reporting_currency="USD",
            inception_date="2026-01-01",
            eligibility_policy_version="synthetic-policy",
            source_authority=DpmCompositeSourceAuthority(policy_version="synthetic-authority"),
            created_by="synthetic-maker",
            correlation_id="synthetic-definition",
        )
    )
    revision = DpmCompositeMembershipRevision(
        **scope,
        membership_revision="synthetic-membership",
        policy_version="synthetic-policy",
        source_cut_id="synthetic-universe-cut",
        decided_by="synthetic-maker",
        correlation_id="synthetic-membership",
        decisions=[
            DpmCompositeMembershipDecision(
                portfolio_id="synthetic-member",
                effective_from=coverage_from,
                effective_to=coverage_to,
                source_snapshot_id="synthetic-monthly-cut",
            )
        ],
    )
    repository.save_membership_revision(revision=revision)
    attestation = DpmCompositeUniverseAttestation(
        **scope,
        membership_revision=revision.membership_revision,
        membership_content_hash=revision.content_hash,
        attestation_version="synthetic-universe-r1",
        coverage_from=coverage_from,
        coverage_to=coverage_to,
        policy_version="synthetic-policy",
        source_cut_id="synthetic-universe-cut",
        source_products=[
            DpmCompositeUniverseSourceProduct(
                owner_service="lotus-manage",
                product_name="CompositeEligibilityUniverse",
                contract_version="v1",
                authority_scope="AUTHORITATIVE_UNIVERSE",
                source_cut_id="synthetic-universe-cut",
                source_watermark="synthetic-universe-r1",
                content_hash="sha256:" + "a" * 64,
            ),
            DpmCompositeUniverseSourceProduct(
                owner_service="synthetic-source",
                product_name=snapshot.product_name,
                contract_version=snapshot.product_version,
                authority_scope="POLICY_INPUT",
                source_cut_id=snapshot.source_cut_id,
                source_watermark=snapshot.source_revision,
                content_hash=hash_canonical_payload(snapshot.model_dump(mode="json")),
            ),
        ],
        posture="COMPLETE",
        expected_portfolio_ids=["synthetic-member"],
        expected_portfolio_count=1,
        observed_portfolio_count=1,
        attested_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
        attested_by="synthetic-maker",
        correlation_id="synthetic-universe",
    )
    repository.save_universe_attestation(attestation=attestation)
    return repository, attestation


def command(attestation):
    return {
        "month": "2026-09",
        "membership_revision": "synthetic-membership",
        "attestation_version": attestation.attestation_version,
        "universe_content_hash": attestation.content_hash,
        "layers": [
            {
                "level": "PLATFORM",
                "policy_id": "synthetic-policy",
                "revision": "r1",
                "effective_from": "2026-09-01",
                "effective_to": "2026-12-31",
                "flow_threshold": "0.10",
                "cash_threshold": "0.05",
                "permitted_overrides": [],
            }
        ],
    }


def prospective_proposal_body(attestation):
    return {
        "layers": command(attestation)["layers"],
        "attachments": [
            {
                "product_name": "SyntheticMonthlyMethodEvidence",
                "product_version": "v1",
                "revision": "synthetic-method-r1",
                "digest": "sha256:" + "b" * 64,
            }
        ],
    }
