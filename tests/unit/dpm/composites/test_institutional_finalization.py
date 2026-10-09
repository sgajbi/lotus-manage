"""Controlled institutional contracts, unchanged v1 wire and one atomic publication authority."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy

import httpx
import pytest

from src.core.common.canonical import hash_canonical_payload
from src.api.services.composite_subject_application import CompositeSubjectApplicationService
from src.api.services.composite_subject_requests import SubjectFinalizationRequest
from src.core.composite_eligibility.staged_publication import (
    SubjectFinalizationReceipt,
    decode_subject_receipt,
    decode_subject_finalization,
)
from src.core.composite_eligibility.staged_subject import subject_key
from src.core.composite_eligibility.verification import VerificationReceipt, VerificationRequest
from src.infrastructure.composites.in_memory import InMemoryDpmCompositeRepository
from src.infrastructure.composites.institutional_verifier import (
    ConfiguredInstitutionalEvidenceVerifier,
)
from tests.composite_institutional_helpers import (
    institutional_material,
    configuration_material,
    authority_result,
    sign_artifact,
)
from tests.composite_staged_eligibility_helpers import finalization_material


def test_registered_routes_preserve_v2_receipt_and_resolver_discriminator(institutional_service):
    from fastapi.testclient import TestClient
    from src.api.dependencies import get_composite_subject_service
    from src.api.main import app
    from tests.composite_staged_eligibility_helpers import BASE, CHECKER, HEADERS

    service, subject, command, _ = institutional_service
    prior = app.dependency_overrides.copy()
    app.dependency_overrides[get_composite_subject_service] = lambda: service
    try:
        with TestClient(app) as client:
            response = client.put(
                BASE + "/finalization",
                json=command.model_dump(mode="json"),
                headers=HEADERS | {"X-Actor-Id": CHECKER},
            )
            assert response.status_code == 200, response.text
            wire = response.json()
            assert wire["product_version"] == wire["finalization"]["product_version"] == "v2"
            read = client.get(BASE + "/finalization", headers=HEADERS)
            assert read.status_code == 200 and read.json() == wire
            binding = wire["finalization"]["definition"]["source_authority"]["payload"][
                "eligibility_evaluation_binding"
            ]
            resolved = client.post(
                "/api/v1/rebalance/composites/synthetic-composite/definitions/synthetic-definition/eligibility-evidence/resolve",
                json=binding,
                headers=HEADERS,
            )
            assert resolved.status_code == 200 and resolved.json() == wire
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(prior)


def test_deployment_composition_selects_only_the_explicit_institutional_channel(
    institutional_service, monkeypatch
):
    from src.api.composition import composite_source_service as composition
    from src.core.composite_eligibility.source import (
        MonthlyEligibilitySourceRequest,
        UnavailableMonthlyEligibilitySource,
    )
    from src.core.composite_eligibility.policy import MonthlyPolicyScope

    service, subject, command, _ = institutional_service
    adapter = service.attestations
    monkeypatch.delenv("DPM_COMPOSITE_SOURCES_JSON", raising=False)
    monkeypatch.setenv(
        "DPM_COMPOSITE_ATTESTATION_VERIFICATION_JSON", adapter.configuration.model_dump_json()
    )
    families = []

    def shared_client(family, *, policy):
        families.append(family)
        return adapter.client

    monkeypatch.setattr(composition, "get_shared_source_http_client", shared_client)
    composed = composition.build_composite_subject_service(service.repository)
    receipt = composed.finalize(subject_key(subject), "synthetic-checker", command)
    assert receipt.product_version == "v2"
    assert composed.attestations.configuration == adapter.configuration
    assert families == ["composite"]
    monthly = composition.build_composite_monthly_service(service.repository)
    assert isinstance(monthly.source, UnavailableMonthlyEligibilitySource)
    request = MonthlyEligibilitySourceRequest(
        scope=MonthlyPolicyScope(
            tenant_id=subject.tenant_id,
            composite_id=subject.composite_id,
            definition_version=subject.definition_version,
            strategy_code=subject.strategy_code,
        ),
        month=subject.month,
        source_cut_id="missing",
        owner_service="missing",
        expected_source_revision="missing",
        expected_content_hash="sha256:" + "f" * 64,
        expected_portfolio_ids=tuple(member.member_id for member in subject.universe.members),
        reporting_currency=subject.reporting_currency,
    )
    assert monthly.source.resolve(request).observations is None
    # An institutional verification binding cannot qualify the separate financial source channel.
    monkeypatch.setenv(
        "DPM_COMPOSITE_SOURCES_JSON",
        '{"bindings":[' + adapter.configuration.verifier.model_dump_json() + "]}",
    )
    with pytest.raises(ValueError, match="COMPOSITE_SOURCE_INSTITUTIONAL_CHANNEL_REQUIRED"):
        composition.build_composite_subject_service(service.repository)
    assert families == ["composite"]


def test_missing_related_verification_never_publishes_partial_authority(institutional_service):
    service, subject, command, calls = institutional_service
    adapter = service.attestations

    class MissingRelatedVerifier:
        def verify(self, request):
            return adapter.verify(request)

        def verify_related(self, request):
            return None

    partial = CompositeSubjectApplicationService(
        repository=service.repository, attestations=MissingRelatedVerifier()
    )
    with pytest.raises(ValueError, match="COMPOSITE_SUBJECT_FINALIZATION_NOT_FOUND"):
        partial.finalization(subject_key(subject))
    with pytest.raises(
        ValueError, match="COMPOSITE_SUBJECT_INSTITUTIONAL_VERIFICATION_UNAVAILABLE"
    ):
        partial.finalize(subject_key(subject), "synthetic-checker", command)
    assert len(calls) == 1
    assert service.repository.get_eligibility_finalization(key=subject_key(subject)) is None
    assert service.repository._publications == service.repository._membership_revisions == {}


def test_different_original_reference_cannot_replace_retained_finalization(institutional_service):
    service, subject, command, calls = institutional_service
    key = subject_key(subject)
    receipt = service.finalize(key, "synthetic-checker", command)
    definition = receipt.finalization.definition.model_dump(mode="json")
    definition["authority_approval"]["attestation"]["attestation_id"] = "foreign-attestation"
    definition["content_hash"] = hash_canonical_payload(
        {name: value for name, value in definition.items() if name != "content_hash"}
    )
    wire = command.model_dump(mode="json")
    for field in ("authority_approval", "content_hash"):
        wire["definition"][field] = definition[field]
    changed = SubjectFinalizationRequest.model_validate(wire)
    with pytest.raises(ValueError, match="COMPOSITE_SUBJECT_IMMUTABLE_CONFLICT"):
        service.finalize(key, "synthetic-checker", changed)
    assert len(calls) == 4
    assert service.repository.get_eligibility_finalization(key=key) == receipt
    assert len(service.repository._publications) == 1


@pytest.mark.parametrize("wire", ["[]", "null", "false", '"untyped-receipt"'])
def test_retained_receipt_requires_a_json_object(wire):
    with pytest.raises(ValueError, match="COMPOSITE_SUBJECT_FINALIZATION_WIRE_INVALID"):
        decode_subject_receipt(wire)


@pytest.mark.parametrize("version", [None, "v0", "v3"])
def test_finalization_decoder_refuses_unsupported_explicit_version(version):
    with pytest.raises(ValueError, match="COMPOSITE_SUBJECT_FINALIZATION_VERSION_UNSUPPORTED"):
        decode_subject_finalization({"product_version": version})


@pytest.fixture
def institutional_service(monkeypatch):
    subject, controls, definition, artifact, request = institutional_material()
    configuration, signer, verifier = configuration_material()
    monkeypatch.setenv(configuration.verifier.credential_env, "controlled-test-only")
    calls = []

    def response(incoming):
        import json

        body = json.loads(incoming.content)
        calls.append(body)
        if body.get("product_version") == "v2":
            payload = authority_result(configuration, signer, request, artifact)
        else:
            related = VerificationRequest.model_validate(body)
            payload = VerificationReceipt(
                request=related,
                posture="QUALIFIED_RECEIPT",
                verifier_id=configuration.verifier.principal_id,
                issuer_id=configuration.verifier.receipt_issuer_id,
                artifact_revision=related.binding.revision,
                artifact_digest=related.binding.digest,
            ).model_dump(mode="json")
        return httpx.Response(
            200,
            json=dict(
                owner_service=configuration.verifier.owner_service,
                payload=payload,
                credential=sign_artifact(verifier, configuration.verifier, body, payload),
            ),
        )

    adapter = ConfiguredInstitutionalEvidenceVerifier(
        configuration, httpx.Client(transport=httpx.MockTransport(response))
    )
    repository = InMemoryDpmCompositeRepository()
    repository.save_eligibility_subject(subject=subject)
    for control in controls:
        repository.save_subject_control(control=control)
    command = SubjectFinalizationRequest.model_validate(
        dict(
            evaluation_revision=controls[-1].proposal.evaluation_revision,
            expected_approval_content_hash=controls[-1].content_hash,
            definition=definition.model_dump(
                mode="json",
                exclude={
                    "product_name",
                    "tenant_id",
                    "composite_id",
                    "definition_version",
                    "created_by",
                },
            ),
        )
    )
    service = CompositeSubjectApplicationService(repository=repository, attestations=adapter)
    return service, subject, command, calls


def test_v2_retains_full_proof_and_original_approval_without_promoting_history(
    institutional_service,
):
    service, subject, command, calls = institutional_service
    receipt = service.finalize(subject_key(subject), "synthetic-checker", command)
    assert receipt.product_version == receipt.finalization.product_version == "v2"
    assert receipt.finalization.verifications[0].product_version == "v2"
    assert all(item.posture == "QUALIFIED_RECEIPT" for item in receipt.finalization.verifications)
    assert receipt.completeness == "UNVERIFIED"
    assert receipt.finalization.official_activation == "UNAVAILABLE"
    assert len(calls) == 4  # Original attestation, method, and each per-fact provider selection.
    assert service.finalize(subject_key(subject), "synthetic-checker", command) == receipt
    assert len(calls) == 4
    assert decode_subject_receipt(receipt.model_dump(mode="json")) == receipt
    assert (
        service.repository.resolve_eligibility_evidence(
            tenant_id=subject.tenant_id,
            composite_id=subject.composite_id,
            definition_version=subject.definition_version,
            evaluation_revision=command.evaluation_revision,
            approval_content_hash=command.expected_approval_content_hash,
        )
        == receipt
    )
    with pytest.raises(ValueError):
        SubjectFinalizationReceipt.model_validate(receipt.model_dump(mode="json"))


def test_concurrent_identical_commands_retain_one_proof_even_with_fresh_admission_evidence(
    institutional_service,
):
    service, subject, command, _ = institutional_service
    with ThreadPoolExecutor(max_workers=4) as workers:
        results = list(
            workers.map(
                lambda _: service.finalize(subject_key(subject), "synthetic-checker", command),
                range(8),
            )
        )
    assert all(item == results[0] for item in results)
    publications = service.repository.list_publications(
        tenant_id=subject.tenant_id, after_sequence=0, limit=10
    )
    assert len(publications.items) == 1


def test_missing_institutional_channel_and_wrong_finalizer_fail_without_publication(
    institutional_service,
):
    service, subject, command, calls = institutional_service
    for actor in (subject.created_by, "foreign-checker"):
        with pytest.raises(ValueError, match="FINALIZER_FORBIDDEN"):
            service.finalize(subject_key(subject), actor, command)
    default = CompositeSubjectApplicationService(repository=service.repository)
    with pytest.raises(ValueError, match="INSTITUTIONAL_VERIFICATION_UNAVAILABLE"):
        default.finalize(subject_key(subject), "synthetic-checker", command)
    assert calls == []
    assert service.repository.get_eligibility_finalization(key=subject_key(subject)) is None
    assert (
        service.repository.list_publications(
            tenant_id=subject.tenant_id, after_sequence=0, limit=10
        ).items
        == []
    )


@pytest.mark.parametrize(
    "mutation",
    [
        "root_version",
        "null_version",
        "nested_version",
        "reference",
        "original",
        "related",
        "subject",
    ],
)
def test_v2_wire_tampering_refuses(institutional_service, mutation):
    service, subject, command, _ = institutional_service
    receipt = service.finalize(subject_key(subject), "synthetic-checker", command)
    wire = deepcopy(receipt.model_dump(mode="json"))
    if mutation == "root_version":
        wire["product_version"] = "v3"
    elif mutation == "null_version":
        wire["product_version"] = None
    elif mutation == "nested_version":
        wire["finalization"]["product_version"] = "v1"
    elif mutation == "reference":
        wire["finalization"]["definition"]["authority_approval"]["attestation"][
            "attestation_id"
        ] = "foreign"
    elif mutation == "original":
        wire["finalization"]["verifications"][0]["artifact"]["claims"]["approving_identity"] = (
            "foreign"
        )
    elif mutation == "related":
        wire["finalization"]["verifications"][1]["posture"] = "SYNTHETIC_NON_CERTIFYING"
    else:
        wire["finalization"]["subject"]["subject_revision"] = "foreign"
    with pytest.raises(ValueError):
        decode_subject_receipt(wire)
    assert service.repository.get_eligibility_finalization(key=subject_key(subject)) == receipt


def test_v1_strict_wire_and_hashes_remain_unchanged():
    subject, controls, finalization = finalization_material()
    repository = InMemoryDpmCompositeRepository()
    repository.save_eligibility_subject(subject=subject)
    for control in controls:
        repository.save_subject_control(control=control)
    receipt = repository.finalize_eligibility_subject(finalization=finalization)
    wire = receipt.model_dump(mode="json")
    assert wire["product_version"] == "v1"
    assert set(wire) == {
        "product_name",
        "product_version",
        "finalization",
        "publication_sequence",
        "membership_content_hash",
        "universe_content_hash",
        "completeness",
        "content_hash",
    }
    assert set(wire["finalization"]) == {
        "product_name",
        "product_version",
        "official_activation",
        "subject",
        "evaluation_approval",
        "definition",
        "verifications",
        "content_hash",
    }
    assert all(item["product_version"] == "v1" for item in wire["finalization"]["verifications"])
    assert decode_subject_finalization(wire["finalization"]) == finalization
    assert decode_subject_receipt(wire).model_dump(mode="json") == wire


@pytest.mark.parametrize("index", [1, 2, 3])
@pytest.mark.parametrize(
    "field,value",
    [
        ("artifact_revision", "foreign-revision"),
        ("artifact_digest", "sha256:" + "f" * 64),
        ("posture", "SYNTHETIC_NON_CERTIFYING"),
    ],
)
def test_rehashed_related_evidence_refuses_decode_retained_reads_and_custody(
    institutional_service, index, field, value
):
    service, subject, command, calls = institutional_service
    repository = service.repository
    key = subject_key(subject)
    receipt = service.finalize(key, "synthetic-checker", command)
    wire = deepcopy(receipt.model_dump(mode="json"))
    related = wire["finalization"]["verifications"][index]
    related[field] = value
    for item in (related, wire["finalization"], wire):
        item["content_hash"] = hash_canonical_payload(
            {name: content for name, content in item.items() if name != "content_hash"}
        )
    code = (
        "COMPOSITE_SUBJECT_INSTITUTIONAL_VERIFICATION_UNAVAILABLE"
        if field == "posture"
        else "COMPOSITE_ATTESTATION_RELATED_ARTIFACT_MISMATCH"
    )
    with pytest.raises(ValueError, match=code):
        decode_subject_receipt(wire)

    # Simulate corrupted retained storage, bypassing construction only to reach owning read guards.
    verifications = list(receipt.finalization.verifications)
    verifications[index] = VerificationReceipt.model_validate(related)
    finalization = receipt.finalization.model_copy(
        update={
            "verifications": verifications,
            "content_hash": wire["finalization"]["content_hash"],
        }
    )
    corrupted = receipt.model_copy(
        update={"finalization": finalization, "content_hash": wire["content_hash"]}
    )
    publications = deepcopy(repository._publications)
    memberships = deepcopy(repository._membership_revisions)
    repository._staged.receipts[key] = corrupted
    for read in (
        lambda: repository.get_eligibility_finalization(key=key),
        lambda: repository.resolve_eligibility_evidence(
            tenant_id=subject.tenant_id,
            composite_id=subject.composite_id,
            definition_version=subject.definition_version,
            evaluation_revision=command.evaluation_revision,
            approval_content_hash=command.expected_approval_content_hash,
        ),
        lambda: service.finalize(key, "synthetic-checker", command),
    ):
        with pytest.raises(ValueError, match=code):
            read()
    assert len(calls) == 4  # Retained failure does not invoke a fresh verifier.
    assert repository._publications == publications
    assert repository._membership_revisions == memberships

    clean = InMemoryDpmCompositeRepository()
    clean.save_eligibility_subject(subject=subject)
    for control in (
        receipt.finalization.evaluation_approval.proposal.policy_approval.proposal,
        receipt.finalization.evaluation_approval.proposal.policy_approval,
        receipt.finalization.evaluation_approval.proposal,
        receipt.finalization.evaluation_approval,
    ):
        clean.save_subject_control(control=control)
    with pytest.raises(ValueError, match=code):
        clean.finalize_eligibility_subject(finalization=finalization)
    assert clean.get_eligibility_finalization(key=key) is None
    assert clean._publications == clean._membership_revisions == clean._definitions == {}

    repository._staged.receipts[key] = receipt
    assert repository.get_eligibility_finalization(key=key) == receipt
