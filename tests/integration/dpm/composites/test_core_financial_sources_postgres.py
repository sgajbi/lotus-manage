"""Ordinary native HTTP composition, PostgreSQL custody and source-off restart.

This synthetic retained-provider test requires Root's qualified PostgreSQL action.
It proves adapter composition, not a live Core producer, IAM or financial acceptance.
Prospective policy history is explicitly seeded through the existing service API.
"""

from datetime import UTC, datetime

from src.api.services.composite_monthly_eligibility import (
    CompositeMonthlyEligibilityApplicationService,
    MonthlyApprovalRequest,
    MonthlyProposalRequest,
)
from src.core.composite_membership import (
    DpmCompositeDefinition,
    DpmCompositeMembershipDecision,
    DpmCompositeMembershipRevision,
    DpmCompositeSourceAuthority,
)
from src.core.composite_universe import DpmCompositeUniverseAttestation
from src.infrastructure.composites.native_assembly_configuration import (
    NativeAssemblyConfiguration,
    native_monthly_signer,
)
from src.infrastructure.composites.postgres import PostgresDpmCompositeRepository
from tests.integration.dpm.composites.native_source_provider import native_source_provider
from tests.integration.dpm.network_runtime import disposable_database, native_api

SCOPE = {"tenant_id": "tenant", "composite_id": "composite", "definition_version": "v1"}
ROOT = "/api/v1/rebalance/composites/composite/definitions/v1"
BASE = ROOT + "/monthly-eligibility"
HEADERS = {
    "X-Tenant-Id": "tenant",
    "X-Actor-Id": "synthetic-maker",
    "X-Role": "DPM_COMPOSITE_ADMIN",
    "X-Service-Identity": "synthetic-native-proof",
    "X-Capabilities": "manage.write",
    "X-Correlation-Id": "synthetic-native-proof",
}


def seed_recurring_history(repository, config, expected):
    repository.save_definition(
        definition=DpmCompositeDefinition(
            **SCOPE,
            display_name="Synthetic native composite",
            strategy_code="strategy",
            reporting_currency="USD",
            inception_date="2025-01-01",
            eligibility_policy_version="policy",
            source_authority=DpmCompositeSourceAuthority(policy_version="synthetic-authority"),
            created_by="synthetic-maker",
            correlation_id="synthetic-native-history",
            created_at=datetime(2024, 12, 19, tzinfo=UTC),
        )
    )
    membership = DpmCompositeMembershipRevision(
        **SCOPE,
        membership_revision="native.parent.r1",
        policy_version="policy",
        source_cut_id=config.financial.registry.source_cut_id,
        decided_by="synthetic-maker",
        correlation_id="native-parent",
        decisions=[
            DpmCompositeMembershipDecision(
                portfolio_id=pid,
                effective_from="2025-01-01",
                effective_to="2025-01-31",
                source_snapshot_id=expected.source_cut_id,
            )
            for pid in expected.expected_portfolio_ids
        ],
    )
    repository.save_membership_revision(revision=membership)
    financial = config.financial
    universe = DpmCompositeUniverseAttestation(
        **SCOPE,
        membership_revision=membership.membership_revision,
        membership_content_hash=membership.content_hash,
        attestation_version="native-universe-r1",
        coverage_from="2025-01-01",
        coverage_to="2025-01-31",
        policy_version="policy",
        source_cut_id=financial.registry.source_cut_id,
        posture="COMPLETE",
        expected_portfolio_ids=expected.expected_portfolio_ids,
        expected_portfolio_count=3,
        observed_portfolio_count=3,
        attested_at=datetime.now(UTC),
        attested_by="synthetic-maker",
        correlation_id="native-universe",
        source_products=[
            {
                "owner_service": "lotus-core",
                "product_name": "PortfolioHistoricalRegistry",
                "contract_version": "v1",
                "authority_scope": "AUTHORITATIVE_UNIVERSE",
                "source_cut_id": financial.registry.source_cut_id,
                "source_watermark": str(financial.registry.revision),
                "content_hash": financial.registry.content_hash,
            },
            {
                "owner_service": "lotus-manage",
                "product_name": expected.product_name,
                "contract_version": "v1",
                "authority_scope": "POLICY_INPUT",
                "source_cut_id": expected.source_cut_id,
                "source_watermark": expected.source_revision,
                "content_hash": config.verification.expected_observations_digest,
            },
        ],
    )
    repository.save_universe_attestation(attestation=universe)
    history = CompositeMonthlyEligibilityApplicationService(
        repository=repository, clock=lambda: "2024-12-20T00:00:00.000000Z"
    )
    proposed = history.propose_policy(
        **SCOPE,
        month="2025-01",
        proposal_revision="native.policy.r1",
        actor_id="synthetic-maker",
        command=MonthlyProposalRequest.model_validate(
            {
                "layers": [
                    {
                        "level": "PLATFORM",
                        "policy_id": "policy",
                        "revision": "r1",
                        "effective_from": "2025-01-01",
                        "effective_to": "2025-01-31",
                        "flow_threshold": "0.10",
                        "cash_threshold": "0.05",
                        "permitted_overrides": [],
                    }
                ],
                "attachments": [
                    {
                        "product_name": "SyntheticPolicyHistory",
                        "product_version": "v1",
                        "revision": "r1",
                        "digest": "sha256:" + "b" * 64,
                    }
                ],
            }
        ),
    )
    approved = history.approve_policy(
        **SCOPE,
        month="2025-01",
        proposal_revision=proposed.proposal_revision,
        actor_id="synthetic-checker",
        command=MonthlyApprovalRequest(expected_proposal_content_hash=proposed.content_hash),
    )
    return universe, approved


def staged_subject_body(config):
    return {
        "display_name": "Synthetic native",
        "strategy_code": "strategy",
        "reporting_currency": "USD",
        "inception_date": "2025-01-01",
        "termination_date": None,
        "eligibility_policy_version": "policy",
        "month": "2025-01",
        "correlation_id": "native-subject",
        "registry_binding": {
            "product_name": "PortfolioHistoricalRegistry",
            "product_version": "v1",
            "revision": "1",
            "digest": config.financial.registry.content_hash,
        },
    }


def test_registered_native_staged_admission_and_default_off_restart(tmp_path):
    # This database has no published definition or earlier staged reservation.
    with (
        disposable_database() as dsn,
        native_source_provider(tmp_path) as (runtime, state, _expected),
    ):
        config = NativeAssemblyConfiguration.model_validate_json(runtime.document)
        assert native_monthly_signer(config) is not None
        repository = PostgresDpmCompositeRepository(dsn=dsn)
        key = ("tenant", "composite", "v1", "native-subject")
        subject_url = (
            "/api/v1/rebalance/composites/composite/eligibility-subjects/v1/native-subject"
        )
        body = staged_subject_body(config)
        assert repository.get_definition(**SCOPE) is None
        assert repository.get_eligibility_subject(key=key) is None
        with native_api(dsn) as (client, _):
            unavailable = client.put(subject_url, headers=HEADERS, json=body)
            assert unavailable.status_code == 503, unavailable.text
            assert unavailable.json()["detail"]["code"] == "COMPOSITE_SUBJECT_UNIVERSE_UNAVAILABLE"
            assert repository.get_eligibility_subject(key=key) is None
            assert repository.get_definition(**SCOPE) is None
        assert state["calls"] == []
        # The identical fresh request now succeeds, proving refusal reserved nothing.
        with native_api(dsn, native_composite_config=runtime) as (client, _):
            admitted = client.put(subject_url, headers=HEADERS, json=body)
            assert admitted.status_code == 200, admitted.text
            subject = admitted.json()
            assert subject["universe"]["population_verification"] == "UNVERIFIED"
            assert [member["member_id"] for member in subject["universe"]["members"]] == [
                "P1",
                "P2",
                "P3",
            ]
            assert repository.get_eligibility_subject(key=key).model_dump(mode="json") == subject
            assert repository.get_definition(**SCOPE) is None
        assert state["calls"] and {call[0] for call in state["calls"]} == {"assembly"}
        state["deny"].add("assembly")
        calls = list(state["calls"])
        with native_api(dsn) as (client, _):
            replay = client.put(subject_url, headers=HEADERS, json=body)
            assert replay.status_code == 200 and replay.json() == subject, replay.text
            assert repository.get_eligibility_subject(key=key).model_dump(mode="json") == subject
        assert state["calls"] == calls


def test_registered_native_recurring_refusal_publication_and_default_off_restart(tmp_path):
    # Published recurring history belongs to a different UUID database from staging.
    with (
        disposable_database() as dsn,
        native_source_provider(tmp_path) as (runtime, state, expected),
    ):
        config = NativeAssemblyConfiguration.model_validate_json(runtime.document)
        # A writable synthetic key is a failed runtime prerequisite, never bypassed by a mock.
        assert native_monthly_signer(config) is not None
        repository = PostgresDpmCompositeRepository(dsn=dsn)
        universe, policy = seed_recurring_history(repository, config, expected)
        command = {
            "month": "2025-01",
            "policy_approval_content_hash": policy.content_hash,
            "parent_membership_revision": universe.membership_revision,
            "parent_membership_content_hash": universe.membership_content_hash,
            "attestation_version": universe.attestation_version,
            "universe_content_hash": universe.content_hash,
            "target_membership_revision": "native.membership.r2",
            "correlation_id": "native-eval",
        }
        url = BASE + "/evaluations/native.evaluation.r1"
        simulation = {
            "month": "2025-01",
            "membership_revision": universe.membership_revision,
            "attestation_version": universe.attestation_version,
            "universe_content_hash": universe.content_hash,
            "layers": [layer.model_dump(mode="json") for layer in policy.proposal.policy.layers],
        }
        with native_api(dsn, native_composite_config=runtime) as (client, _):
            publications_url = "/api/v1/rebalance/composites/publications"
            baseline_response = client.get(publications_url, headers=HEADERS)
            assert baseline_response.status_code == 200, baseline_response.text
            publication_baseline = baseline_response.json()
            assert len(publication_baseline["items"]) == 1
            seeded_publication = publication_baseline["items"][0]
            assert {field: seeded_publication[field] for field in SCOPE} == SCOPE
            assert (
                seeded_publication["product_name"],
                seeded_publication["product_version"],
                seeded_publication["membership_revision"],
                seeded_publication["membership_content_hash"],
                seeded_publication["policy_version"],
                seeded_publication["source_cut_id"],
                seeded_publication["decision_count"],
                seeded_publication["completeness"],
            ) == (
                "CompositeMembershipPublication",
                "v1",
                universe.membership_revision,
                universe.membership_content_hash,
                universe.policy_version,
                universe.source_cut_id,
                len(expected.expected_portfolio_ids),
                "UNVERIFIED",
            )
            assert (
                publication_baseline["high_watermark"]
                == publication_baseline["next_sequence"]
                == seeded_publication["sequence"]
                == 1
            )
            assert publication_baseline["has_more"] is False
            state["deny"].add("verification")
            refused = client.put(url, headers=HEADERS, json=command)
            assert refused.status_code == 503, refused.text
            assert state["calls"][-1][0] == "verification"
            assert any(call[0] == "assembly" for call in state["calls"])
            assert (
                repository.get_monthly_evaluation_proposal(
                    **SCOPE, evaluation_revision="native.evaluation.r1"
                )
                is None
            )
            after_denial = client.get(publications_url, headers=HEADERS)
            assert after_denial.status_code == baseline_response.status_code == 200, (
                after_denial.text
            )
            assert after_denial.json() == publication_baseline
            state["deny"].clear()
            accepted = client.put(url, headers=HEADERS, json=command)
            assert accepted.status_code == 200, accepted.text
            proposal = accepted.json()
            assert proposal["observations"] == expected.model_dump(mode="json")
            evidence = proposal["source_assembly_evidence"]
            assert evidence["assembly"]["product_version"] == "v2"
            assert evidence["native_proof"]["result"]["receipt"] == evidence["verification"]
            assert evidence["verification"]["posture"] == "SYNTHETIC_NON_CERTIFYING"
            assert len(evidence["assembly"]["native_custody"]["portfolios"]) == 3
            assert len(evidence["assembly"]["inputs"]) == 5
            for portfolio in proposal["evaluation"]["portfolios"]:
                flow = portfolio["assessments"][0]
                assert (flow["numerator"], flow["denominator"], flow["ratio"]) == (
                    "-10.00",
                    "100.00",
                    "0.1",
                )
                assert flow["outcome"] == "FAIL"
            assert {call[0] for call in state["calls"]} == {"assembly", "verification"}
            state["deny"].update(("assembly", "verification"))
            assert (
                client.post(BASE + "/simulate", headers=HEADERS, json=simulation).status_code == 503
            )
            calls_after_refusal = list(state["calls"])
            replay = client.put(url, headers=HEADERS, json=command)
            assert replay.status_code == 200 and replay.json() == proposal, replay.text
            approval_body = {"expected_proposal_content_hash": proposal["content_hash"]}
            checker = HEADERS | {"X-Actor-Id": "synthetic-checker"}
            approved = client.put(url + "/approval", headers=checker, json=approval_body)
            assert approved.status_code == 200, approved.text
            approval = approved.json()
            assert approval["official_activation"] == "UNAVAILABLE"
            binding = {
                "product_name": "CompositeMonthlyEvaluationApproval",
                "product_version": "v1",
                "revision": "native.evaluation.r1",
                "digest": approval["content_hash"],
            }
            receipt = client.post(
                ROOT + "/eligibility-evidence/resolve", headers=HEADERS, json=binding
            )
            assert receipt.status_code == 200, receipt.text
            retained = receipt.json()
            assert retained["approval"]["proposal"] == proposal
            assert retained["completeness"] == "UNVERIFIED"
            assert state["calls"] == calls_after_refusal
        calls = list(state["calls"])
        with native_api(dsn) as (client, _):
            replay = client.put(url, headers=HEADERS, json=command)
            assert replay.status_code == 200 and replay.json() == proposal, replay.text
            replay_approval = client.put(url + "/approval", headers=checker, json=approval_body)
            assert replay_approval.status_code == 200 and replay_approval.json() == approval
            replay_receipt = client.post(
                ROOT + "/eligibility-evidence/resolve", headers=HEADERS, json=binding
            )
            assert replay_receipt.status_code == 200 and replay_receipt.json() == retained
            assert (
                client.post(BASE + "/simulate", headers=HEADERS, json=simulation).status_code == 503
            )
        assert state["calls"] == calls
