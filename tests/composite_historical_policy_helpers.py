"""Controlled original raw signatures and independent normalized verification; never production."""

import base64
import hashlib
import json
from datetime import datetime, timedelta

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from src.core.common.canonical import hash_canonical_payload
from src.core.composite_eligibility.historical_policy import (
    HistoricalPolicyMapping,
    HistoricalPolicyReference,
    HistoricalPolicyVerification,
    HistoricalPolicyVerificationRequest,
    HistoricalMonthlyPolicyProposal,
    HistoricalMonthlyPolicyApproval,
    HistoricalPolicyTrust,
)
from src.core.composite_eligibility.evaluation_control import HistoricalMonthlyEvaluationProposal
from src.core.composite_eligibility.monthly_evidence import HistoricalMonthlyPublicationReceipt
from src.core.composite_eligibility.publication import build_monthly_publication
from src.infrastructure.composites.in_memory import InMemoryDpmCompositeRepository
from tests.composite_monthly_amendment_helpers import seed_complete_monthly_root


class ControlledHistoricalPolicyPort:
    """Test-only format adapter verifying exact raw bytes, not a new normalized original JWS."""

    def __init__(self, policy):
        self.signer = Ed25519PrivateKey.from_private_bytes(bytes(range(32)))
        self.verifier = Ed25519PrivateKey.from_private_bytes(bytes(range(32, 64)))
        original = policy.proposal
        body = {
            "CONTROLLED_TEST_HISTORY": True,
            "policy": original.policy.model_dump(mode="json"),
            "eligibility_policy_version": original.eligibility_policy_version,
            "attachments": [item.model_dump(mode="json") for item in original.attachments],
            "proposed_by": original.proposed_by,
            "proposed_at": original.proposed_at,
            "approved_by": policy.approved_by,
            "approved_at": policy.approved_at,
        }
        raw = (json.dumps(body, indent=3, ensure_ascii=False) + "\r\n").encode()
        self.mapping = HistoricalPolicyMapping(
            reference=HistoricalPolicyReference(
                issuer_id="controlled-original-owner",
                artifact_id="controlled-original-policy",
                revision="controlled-original-r1",
                raw_digest="sha256:" + hashlib.sha256(raw).hexdigest(),
                signing_contract="CONTROLLED_ED25519_RAW_BYTES_V1",
            ),
            raw_original_base64=base64.b64encode(raw).decode(),
            original_credential=base64.b64encode(self.signer.sign(raw)).decode(),
            policy=original.policy,
            eligibility_policy_version=original.eligibility_policy_version,
            reporting_currency="USD",
            attachments=original.attachments,
            original_proposed_by=original.proposed_by,
            original_proposed_at=original.proposed_at,
            original_approved_by=policy.approved_by,
            original_approved_at=policy.approved_at,
        )
        self.calls = []
        self.available = True
        self.trust = HistoricalPolicyTrust(
            tenant_id=original.policy.scope.tenant_id,
            signing_contract=self.mapping.reference.signing_contract,
            signer_principal_id="controlled-original-signer",
            verifier_principal_id="controlled-verifier",
            signer_key_digest=self._key_digest(self.signer),
            verifier_key_digest=self._key_digest(self.verifier),
            configuration_digest=hash_canonical_payload({"controlled": "configuration"}),
            posture="SYNTHETIC_NON_CERTIFYING",
        )

    def verify(self, request):
        self.calls.append(request)
        if not self.available:
            return None
        raw = base64.b64decode(self.mapping.raw_original_base64, validate=True)
        self.signer.public_key().verify(base64.b64decode(self.mapping.original_credential), raw)
        wire = dict(
            product_name="CompositeHistoricalPolicyVerification",
            product_version="v1",
            posture="SYNTHETIC_NON_CERTIFYING",
            request=request.model_dump(mode="json"),
            mapping=self.mapping.model_dump(mode="json"),
            original_signature_status="VERIFIED_AT_ORIGINAL_APPROVAL",
            current_revocation_status="CLEAR",
            verifier_id="controlled-independent-verifier",
            signer_principal_id="controlled-original-signer",
            verifier_principal_id="controlled-verifier",
            configuration_digest=hash_canonical_payload({"controlled": "configuration"}),
            signer_key_digest=self._key_digest(self.signer),
            verifier_key_digest=self._key_digest(self.verifier),
            verifier_public_key_base64=base64.b64encode(
                self.verifier.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
            ).decode(),
            revocation_revision="controlled-explicit-empty-r1",
            revocation_digest=hash_canonical_payload({"revoked": []}),
            checked_at=request.requested_at,
            admitted_at=request.requested_at,
            expires_at=(
                datetime.fromisoformat(request.requested_at) + timedelta(minutes=5)
            ).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        )
        signature = self.verifier.sign(hash_canonical_payload(wire).encode())
        self.verifier.public_key().verify(signature, hash_canonical_payload(wire).encode())
        return HistoricalPolicyVerification(
            **wire, verifier_credential=base64.b64encode(signature).decode()
        )

    @staticmethod
    def _key_digest(key):
        raw = key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        return "sha256:" + hashlib.sha256(raw).hexdigest()


def historical_contract_material(*, definition_product_version="v1"):
    """Construct actual typed example models from controlled existing monthly material."""
    repository = InMemoryDpmCompositeRepository()
    scope, old, _ = seed_complete_monthly_root(
        repository,
        parent_decided_at="2026-08-01T00:00:00.000000Z",
        definition_product_version=definition_product_version,
    )
    prior = old.approval.proposal
    port = ControlledHistoricalPolicyPort(prior.policy_approval)
    initial = HistoricalPolicyVerificationRequest(
        operation="POLICY_PROPOSAL",
        reference=port.mapping.reference,
        scope=port.mapping.policy.scope,
        month=port.mapping.policy.month,
        eligibility_policy_version=port.mapping.eligibility_policy_version,
        reporting_currency="USD",
        revision="controlled-admission-r1",
        actor_id="controlled-admission-maker",
        requested_at="2026-10-10T01:00:00.000000Z",
        intent_digest=hash_canonical_payload(
            {
                "reference": port.mapping.reference.model_dump(mode="json"),
                "proposal_revision": "controlled-admission-r1",
            }
        ),
    )
    proposal = HistoricalMonthlyPolicyProposal(
        proposal_revision=initial.revision,
        eligibility_policy_version=initial.eligibility_policy_version,
        policy=port.mapping.policy,
        attachments=port.mapping.attachments,
        proposed_by=initial.actor_id,
        proposed_at=initial.requested_at,
        verification=port.verify(initial),
    )
    approval_request = HistoricalPolicyVerificationRequest.model_validate(
        initial.model_dump(mode="json")
        | {
            "operation": "POLICY_APPROVAL",
            "actor_id": "controlled-admission-checker",
            "requested_at": "2026-10-10T01:01:00.000000Z",
            "intent_digest": proposal.content_hash,
        }
    )
    approved = HistoricalMonthlyPolicyApproval(
        proposal=proposal,
        approved_by=approval_request.actor_id,
        approved_at=approval_request.requested_at,
        verification=port.verify(approval_request),
    )
    wire = prior.model_dump(mode="json")
    wire.update(
        product_version="v3", policy_approval=approved.model_dump(mode="json"), content_hash=""
    )
    request = HistoricalPolicyVerificationRequest.model_validate(
        initial.model_dump(mode="json")
        | {
            "operation": "EVALUATION_PROPOSAL",
            "revision": prior.evaluation_revision,
            "actor_id": prior.proposed_by,
            "requested_at": prior.proposed_at,
            "intent_digest": hash_canonical_payload(
                {k: v for k, v in wire.items() if k != "content_hash"}
            ),
        }
    )
    # Use present operation clocks; the original external approval alone is historical.
    instant = "2026-10-10T01:02:00.000000Z"
    wire["proposed_at"] = instant
    wire["evaluation"]["evaluated_at"] = instant
    wire["evaluation"]["content_hash"] = ""
    from src.core.composite_eligibility.evaluation import MonthlyEligibilityEvaluation

    wire["evaluation"] = MonthlyEligibilityEvaluation.model_validate(wire["evaluation"]).model_dump(
        mode="json"
    )
    request = HistoricalPolicyVerificationRequest.model_validate(
        request.model_dump(mode="json")
        | {
            "requested_at": instant,
            "intent_digest": hash_canonical_payload(
                {k: v for k, v in wire.items() if k != "content_hash"}
            ),
        }
    )
    evaluated = HistoricalMonthlyEvaluationProposal.model_validate(
        wire | {"operation_verification": port.verify(request)}
    )
    checker_request = HistoricalPolicyVerificationRequest.model_validate(
        request.model_dump(mode="json")
        | {
            "operation": "EVALUATION_APPROVAL",
            "actor_id": "controlled-evaluation-checker",
            "requested_at": "2026-10-10T01:03:00.000000Z",
            "intent_digest": evaluated.content_hash,
        }
    )
    member = repository.get_membership_revision(
        **scope, membership_revision=prior.parent_membership_revision
    )
    evaluation_approval, published_member, published_universe = build_monthly_publication(
        evaluated,
        member,
        approved_by=checker_request.actor_id,
        approved_at=checker_request.requested_at,
        operation_verification=port.verify(checker_request),
    )
    receipt_wire = old.model_dump(mode="json")
    receipt_wire["membership_binding"]["digest"] = published_member.content_hash
    receipt_wire["universe_binding"]["digest"] = published_universe.content_hash
    receipt = HistoricalMonthlyPublicationReceipt.model_validate(
        receipt_wire
        | {
            "product_version": "v3",
            "approval": evaluation_approval.model_dump(mode="json"),
            "content_hash": "",
        }
    )
    return port, proposal, approved, evaluated, evaluation_approval, receipt


def historical_amendment_contract_material():
    from tests.composite_monthly_amendment_helpers import corrected_monthly_proposal
    from src.core.composite_eligibility.monthly_evidence import HistoricalMonthlyAmendmentReceipt

    port, policy, approved_policy, root, approved_root, receipt = historical_contract_material()
    # Reproduce the root projection from its exact input parent, retaining no invented history.
    repository = InMemoryDpmCompositeRepository()
    scope, _, _ = seed_complete_monthly_root(
        repository, parent_decided_at="2026-08-01T00:00:00.000000Z"
    )
    parent = repository.get_membership_revision(
        **scope, membership_revision=root.parent_membership_revision
    )
    _, current, _ = build_monthly_publication(
        root,
        parent,
        approved_by=approved_root.approved_by,
        approved_at=approved_root.approved_at,
        operation_verification=approved_root.operation_verification,
    )
    proposal = corrected_monthly_proposal(
        receipt, current, sequence=receipt.publication_sequence, historical_verifier=port
    )
    request = HistoricalPolicyVerificationRequest.model_validate(
        proposal.operation_verification.request.model_dump(mode="json")
        | {
            "operation": "EVALUATION_APPROVAL",
            "actor_id": "controlled-correction-checker",
            "requested_at": proposal.proposed_at,
            "intent_digest": proposal.content_hash,
        }
    )
    approval, member, universe = build_monthly_publication(
        proposal,
        current,
        approved_by=request.actor_id,
        approved_at=request.requested_at,
        operation_verification=port.verify(request),
    )
    wire = receipt.model_dump(mode="json")
    wire["membership_binding"].update(
        revision=member.membership_revision, digest=member.content_hash
    )
    wire["universe_binding"].update(
        revision=universe.attestation_version, digest=universe.content_hash
    )
    corrected = HistoricalMonthlyAmendmentReceipt.model_validate(
        wire
        | {
            "product_version": "v4",
            "approval": approval.model_dump(mode="json"),
            "lineage": proposal.amendment.model_dump(mode="json"),
            "publication_sequence": receipt.publication_sequence + 1,
            "content_hash": "",
        }
    )
    return proposal, approval, corrected


def seed_historical_root(repository, *, definition_product_version="v1"):
    port, policy, approved_policy, root, approved_root, expected = historical_contract_material(
        definition_product_version=definition_product_version
    )
    original = InMemoryDpmCompositeRepository()
    scope, _, _ = seed_complete_monthly_root(
        original,
        parent_decided_at="2026-08-01T00:00:00.000000Z",
        definition_product_version=definition_product_version,
    )
    repository.save_definition(definition=original.get_definition(**scope))
    repository.save_membership_revision(
        revision=original.get_membership_revision(
            **scope, membership_revision=root.parent_membership_revision
        )
    )
    repository.save_universe_attestation(attestation=root.universe)
    repository.save_monthly_policy_proposal(proposal=policy)
    repository.save_monthly_policy_approval(approval=approved_policy)
    repository.save_monthly_evaluation_proposal(proposal=root)
    repository.save_monthly_evaluation_approval(approval=approved_root)
    retained = repository.resolve_monthly_eligibility_evidence(
        **scope,
        evaluation_revision=root.evaluation_revision,
        approval_content_hash=approved_root.content_hash,
    )
    publications = repository.list_publications(
        tenant_id=scope["tenant_id"], after_sequence=0, limit=100
    ).items
    published = [
        item for item in publications if item.membership_revision == root.target_membership_revision
    ]
    assert len(published) == 1
    assert published[0].membership_content_hash == expected.membership_binding.digest
    # PostgreSQL identity allocation can have gaps after an idempotent publication INSERT.
    # Bind the complete golden receipt to the independently retained publication cursor.
    expected = type(expected).model_validate(
        expected.model_dump(mode="json")
        | {"publication_sequence": published[0].sequence, "content_hash": ""}
    )
    assert retained == expected
    current = repository.get_membership_revision(
        **scope, membership_revision=root.target_membership_revision
    )
    return port, scope, retained, current


def historical_approval_for(proposal, parent, port, actor="controlled-correction-checker"):
    request = HistoricalPolicyVerificationRequest.model_validate(
        proposal.operation_verification.request.model_dump(mode="json")
        | {
            "operation": "EVALUATION_APPROVAL",
            "actor_id": actor,
            "requested_at": proposal.proposed_at,
            "intent_digest": proposal.content_hash,
        }
    )
    return build_monthly_publication(
        proposal,
        parent,
        approved_by=actor,
        approved_at=proposal.proposed_at,
        operation_verification=port.verify(request),
    )
