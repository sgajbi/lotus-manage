"""New synthetic subject fixture; the original shared V2 pack is never modified."""

from src.core.composite_authority_models import EvidenceBinding
from src.core.composite_eligibility.approval import MonthlyPolicyApproval, MonthlyPolicyProposal
from src.core.composite_eligibility.evaluation import evaluate_monthly_eligibility
from src.core.composite_eligibility.policy import (
    MonthlyPolicyLayer,
    MonthlyPolicyScope,
    resolve_monthly_policy,
)
from src.core.composite_eligibility.staged_subject import CandidateUniverse, EligibilitySubject
from src.core.composite_eligibility.staged_controls import (
    SubjectPolicyProposal,
    SubjectPolicyApproval,
    SubjectEvaluationProposal,
    SubjectEvaluationApproval,
    subject_approval_claims,
)
from src.core.composite_eligibility.staged_publication import (
    initial_projection,
    SubjectFinalization,
    finalization_verification_requests,
)
from src.core.composite_eligibility.verification import VerificationRequest, VerificationReceipt
from src.core.composite_definition_versions import DpmCompositeDefinitionV2
from src.core.composite_universe import DpmCompositeUniverseSourceProduct
from tests.composite_monthly_eligibility_helpers import source_snapshot, command
from tests.composite_authority_helpers import independent_digest

MAKER = "synthetic-maker"
CHECKER = "synthetic-checker"
PROSPECTIVE = "2026-08-20T00:00:00.000000Z"
OBSERVED = "2026-10-02T00:00:00.000000Z"
HEADERS = {"X-Tenant-Id": "synthetic-tenant", "X-Actor-Id": MAKER, "X-Role": "DPM_COMPOSITE_ADMIN"}
BASE = "/api/v1/rebalance/composites/synthetic-composite/eligibility-subjects/synthetic-definition/synthetic-subject"


def finalization_material():
    """Construct a complete non-certifying graph, not a financial authority proof."""
    _, subject, policy, policy_approval, evaluation, approval, _, _ = lifecycle_material()
    definition = final_definition(subject, approval)
    finalization = SubjectFinalization(
        subject=subject,
        evaluation_approval=approval,
        definition=definition,
        verifications=[
            synthetic_verification(request)
            for request in finalization_verification_requests(definition, subject)
        ],
    )
    return subject, (policy, policy_approval, evaluation, approval), finalization


class SyntheticEvidenceVerifier:
    """Constructor-injected test-only verifier, never selected by application configuration."""

    def verify(self, request):
        return synthetic_verification(request)


def synthetic_verification(request: VerificationRequest) -> VerificationReceipt:
    return VerificationReceipt(
        request=request,
        posture="SYNTHETIC_NON_CERTIFYING",
        verifier_id="synthetic-fixture-verifier",
        issuer_id="synthetic-fixture-issuer",
        artifact_revision="synthetic.r1",
        artifact_digest=independent_digest(request.model_dump(mode="json")),
    )


def verification_request(subject, purpose, claims, binding=None, source_product=None):
    return VerificationRequest(
        purpose=purpose,
        tenant_id=subject.tenant_id,
        composite_id=subject.composite_id,
        definition_version=subject.definition_version,
        subject_content_hash=subject.content_hash,
        claims_digest=claims,
        effective_from="2026-09-01",
        effective_to="2026-09-30",
        binding=binding,
        source_product=source_product,
    )


def lifecycle_material():
    snapshot = source_snapshot()
    registry = {
        "tenant_id": snapshot.tenant_id,
        "registry_revision": "synthetic.registry.r1",
        "members": [
            {
                "member_id": "synthetic-member",
                "identity_kind": "EXTERNAL_MEMBER",
                "namespace": "synthetic-external",
                "provider_id": "synthetic-provider",
                "source_member_id": "synthetic-account",
            }
        ],
    }
    registry_binding = EvidenceBinding(
        product_name="SyntheticCandidateRegistry",
        product_version="v1",
        revision=registry["registry_revision"],
        digest=independent_digest(registry),
    )
    universe = CandidateUniverse(
        tenant_id=snapshot.tenant_id,
        composite_id=snapshot.composite_id,
        definition_version=snapshot.definition_version,
        month=snapshot.month,
        registry_binding=registry_binding,
        reporting_currency="USD",
        members=registry["members"],
        source_products=[
            DpmCompositeUniverseSourceProduct(
                owner_service="synthetic-provider",
                product_name=registry_binding.product_name,
                contract_version="v1",
                authority_scope="AUTHORITATIVE_UNIVERSE",
                source_cut_id="synthetic-universe-cut",
                source_watermark=registry_binding.revision,
                content_hash=registry_binding.digest,
            )
        ],
        observation_owner="synthetic-source",
        coverage_from="2026-09-01",
        coverage_to="2026-09-30",
        posture="COMPLETE",
        source_cut_id="synthetic-universe-cut",
        generated_at=PROSPECTIVE,
    )
    subject = EligibilitySubject(
        tenant_id=snapshot.tenant_id,
        composite_id=snapshot.composite_id,
        definition_version=snapshot.definition_version,
        subject_revision="synthetic-subject",
        display_name="Synthetic external monthly composite",
        strategy_code="synthetic-strategy",
        reporting_currency="USD",
        inception_date="2026-09-01",
        termination_date=None,
        eligibility_policy_version="synthetic-policy",
        month=snapshot.month,
        universe=universe,
        created_by=MAKER,
        created_at=PROSPECTIVE,
        correlation_id="synthetic-subject",
    )
    layers = command(
        type("Fixture", (), {"attestation_version": "unused", "content_hash": "unused"})()
    )["layers"]
    policy = resolve_monthly_policy(
        [MonthlyPolicyLayer.model_validate(layer) for layer in layers],
        month=subject.month,
        scope=MonthlyPolicyScope(
            tenant_id=subject.tenant_id,
            composite_id=subject.composite_id,
            definition_version=subject.definition_version,
            strategy_code=subject.strategy_code,
        ),
    )
    proposal = SubjectPolicyProposal(
        subject=subject,
        proposal=MonthlyPolicyProposal(
            proposal_revision="synthetic.policy.r1",
            eligibility_policy_version=subject.eligibility_policy_version,
            policy=policy,
            attachments=[registry_binding],
            proposed_by=MAKER,
            proposed_at=PROSPECTIVE,
        ),
    )
    approval = MonthlyPolicyApproval(
        proposal=proposal.proposal, approved_by=CHECKER, approved_at=PROSPECTIVE
    )
    policy_claims = independent_digest(
        {
            "subject_content_hash": subject.content_hash,
            "approval_content_hash": approval.content_hash,
        }
    )
    policy_approval = SubjectPolicyApproval(
        proposal=proposal,
        approval=approval,
        verification=synthetic_verification(
            verification_request(subject, "ELIGIBILITY_POLICY", policy_claims)
        ),
    )
    evaluation = evaluate_monthly_eligibility(
        policy, snapshot, evaluated_at=OBSERVED, universe_content_hash=universe.content_hash
    )
    observation_binding = DpmCompositeUniverseSourceProduct(
        owner_service=universe.observation_owner,
        product_name=snapshot.product_name,
        contract_version=snapshot.product_version,
        authority_scope="POLICY_INPUT",
        source_cut_id=snapshot.source_cut_id,
        source_watermark=snapshot.source_revision,
        content_hash=independent_digest(snapshot.model_dump(mode="json")),
    )
    evaluation_proposal = SubjectEvaluationProposal(
        policy_approval=policy_approval,
        evaluation_revision="synthetic.evaluation.r1",
        target_membership_revision="synthetic.membership.r1",
        observations=snapshot,
        observation_binding=observation_binding,
        evaluation=evaluation,
        proposed_by=MAKER,
        proposed_at=OBSERVED,
    )
    claims = subject_approval_claims(evaluation_proposal, CHECKER, OBSERVED)
    membership, published_universe = initial_projection(
        evaluation_proposal, claims, CHECKER, OBSERVED
    )
    evaluation_approval = SubjectEvaluationApproval(
        evidence_kind="SYNTHETIC_UNSIGNED",
        proposal=evaluation_proposal,
        approved_by=CHECKER,
        approved_at=OBSERVED,
        claims_digest=claims,
        membership_content_hash=membership.content_hash,
        universe_content_hash=published_universe.content_hash,
        verification=synthetic_verification(
            verification_request(subject, "ELIGIBILITY_POLICY_EVALUATION", claims)
        ),
    )
    return (
        registry,
        subject,
        proposal,
        policy_approval,
        evaluation_proposal,
        evaluation_approval,
        membership,
        published_universe,
    )


def final_definition(subject, approval):
    provider_binding = EvidenceBinding(
        product_name="SyntheticProviderRegistration",
        product_version="v1",
        revision="synthetic.provider.r1",
        digest=independent_digest(
            {"provider_id": "synthetic-provider", "tenant_id": subject.tenant_id}
        ),
    )
    method = EvidenceBinding(
        product_name="SyntheticReturnMethodCalendar",
        product_version="v1",
        revision="synthetic.method.r1",
        digest=independent_digest({"method": "ASSET_WEIGHTED", "calendar": "CALENDAR_MONTH"}),
    )
    profile = {
        "product_name": "CompositeSourceAuthority",
        "product_version": "v2",
        "profile_id": "synthetic.subject.authority",
        "profile_revision": "synthetic.subject.authority.r1",
        "tenant_id": subject.tenant_id,
        "composite_id": subject.composite_id,
        "effective_from": "2026-09-01",
        "effective_to": "2026-09-30",
        "mode": "EXTERNAL",
        "definition_owner": "lotus-manage",
        "membership_owner": "lotus-manage",
        "publisher": "lotus-manage",
        "materialization_owner": "lotus-performance",
        "calculation_owner": "lotus-performance",
        "member_identities": [m.model_dump(mode="json") for m in subject.universe.members],
        "providers": [
            {
                "provider_id": "synthetic-provider",
                "source_kind": "EXTERNAL_PROVIDER",
                "registry_revision": provider_binding.revision,
                "registry_digest": provider_binding.digest,
                "trust_registration_ref": "synthetic.registration",
            }
        ],
        "eligibility_evaluation_binding": {
            "product_name": approval.product_name,
            "product_version": "v1",
            "revision": approval.proposal.evaluation_revision,
            "digest": approval.content_hash,
        },
        "return_method_binding": method.model_dump(mode="json"),
        "selections": [],
    }
    for fact, selection_id in (("BEGINNING_ASSETS", "assets"), ("MEMBER_RETURN", "returns")):
        profile["selections"].append(
            {
                "selection_id": selection_id,
                "fact": fact,
                "member_ids": ["synthetic-member"],
                "effective_from": "2026-09-01",
                "effective_to": "2026-09-30",
                "provider_id": "synthetic-provider",
                "economic_authority": "synthetic-provider",
                "publisher_service": "synthetic-provider",
                "source_product": "Synthetic" + selection_id.title(),
                "source_contract_version": "v1",
                "source_revision": "synthetic." + selection_id + ".r1",
                "source_watermark": "synthetic." + selection_id + ".r1",
                "source_cut_id": "synthetic." + selection_id + ".cut",
                "source_digest": independent_digest({"fact": fact}),
                "method_profile_binding": method.model_dump(mode="json")
                if fact == "MEMBER_RETURN"
                else None,
            }
        )
    wire = {
        name: getattr(subject, name)
        for name in (
            "tenant_id",
            "composite_id",
            "definition_version",
            "display_name",
            "strategy_code",
            "reporting_currency",
            "inception_date",
            "termination_date",
            "eligibility_policy_version",
            "created_by",
            "created_at",
            "correlation_id",
        )
    }
    wire.update(
        product_name="CompositeDefinition",
        product_version="v2",
        calculation_method="ASSET_WEIGHTED",
        source_authority={"payload": profile, "profile_digest": independent_digest(profile)},
    )
    business_digest = independent_digest(wire)
    claims = {
        "purpose": "COMPOSITE_ECONOMIC_AUTHORITY_PROFILE",
        "schema_version": "synthetic-approval-claims.v1",
        "tenant_id": subject.tenant_id,
        "composite_id": subject.composite_id,
        "definition_version": subject.definition_version,
        "profile_id": profile["profile_id"],
        "profile_revision": profile["profile_revision"],
        "profile_digest": independent_digest(profile),
        "definition_payload_digest": business_digest,
        "effective_from": profile["effective_from"],
        "effective_to": profile["effective_to"],
        "approving_identity": CHECKER,
        "approved_at": OBSERVED,
        "eligibility_evidence_digest": approval.content_hash,
        "method_evidence_digest": method.digest,
    }
    wire.update(
        definition_payload_digest=business_digest,
        authority_approval={
            "evidence_kind": "SYNTHETIC_UNSIGNED",
            "claims": claims,
            "official_activation": "UNAVAILABLE",
        },
    )
    wire["content_hash"] = independent_digest(wire)
    return DpmCompositeDefinitionV2.model_validate(wire)
