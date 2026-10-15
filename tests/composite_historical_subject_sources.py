"""In-process signed transport; no external HTTP or business-history installation."""

import json
from contextlib import contextmanager

import httpx
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from src.api.composition import composite_source_service
from src.core.composite_eligibility.historical_policy import HistoricalPolicyVerificationRequest
from src.core.composite_eligibility.verification import VerificationRequest
from src.infrastructure.composites.historical_configuration import HistoricalPolicyConfiguration
from src.infrastructure.composites.source_configuration import (
    CompositeSourceConfiguration,
    SourceBinding,
)
from tests.composite_historical_subject_helpers import empty_historical_subject_service
from tests.composite_monthly_source_helpers import assembly_material
from tests.composite_staged_eligibility_helpers import synthetic_verification
from tests.unit.dpm.infrastructure.test_composite_configured_sources import encoded, signed


@contextmanager
def configured_historical_subject_service(monkeypatch):
    _, repository, historical, subject, policy, evaluation = empty_historical_subject_service()
    source_key, verifier_key = Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate()
    bindings = {}
    purposes = (
        "ELIGIBILITY_POLICY",
        "ELIGIBILITY_POLICY_EVALUATION",
        "COMPOSITE_MONTHLY_SOURCE_CUT",
        "COMPOSITE_ECONOMIC_AUTHORITY_PROFILE",
        "RETURN_METHOD_CALENDAR",
        "PROVIDER_REGISTRATION",
    )
    for operation in ("candidates", "observations", "verification"):
        key = verifier_key if operation == "verification" else source_key
        bindings[operation] = SourceBinding(
            operation=operation,
            tenant_id=subject.tenant_id,
            owner_service="synthetic-source",
            endpoint="https://synthetic.invalid/" + operation,
            issuer="urn:synthetic:fixture:issuer",
            receipt_issuer_id="synthetic-fixture-issuer" if operation == "verification" else None,
            principal_id="synthetic-fixture-verifier"
            if operation == "verification"
            else "synthetic-fixture-source",
            credential_env="SYNTHETIC_SUBJECT_UNIT_SOURCE_CREDENTIAL",
            evidence_posture="SYNTHETIC_NON_CERTIFYING",
            verification_purposes=purposes if operation == "verification" else (),
            keys=[
                {
                    "kid": "test-key",
                    "x": encoded(key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)),
                }
            ],
        )
    configuration = CompositeSourceConfiguration(bindings=tuple(bindings.values()))
    historical_config = HistoricalPolicyConfiguration(
        endpoint="https://synthetic.invalid/historical",
        credential_env="SYNTHETIC_SUBJECT_UNIT_SOURCE_CREDENTIAL",
        trust=historical.trust,
    )
    _, assembly = assembly_material()
    state = {"calls": [], "failure": None, "assembly": assembly}

    def respond(request):
        operation = request.url.path[1:]
        body = json.loads(request.content)
        state["calls"].append(operation)
        if state["failure"] == "unavailable":
            return httpx.Response(503)
        if operation == "historical":
            result = historical.verify(HistoricalPolicyVerificationRequest.model_validate(body))
            return httpx.Response(200, json=result.model_dump(mode="json"))
        binding = bindings[operation]
        key = verifier_key if operation == "verification" else source_key
        if operation == "candidates":
            payload = subject.universe.model_dump(mode="json")
        elif operation == "observations":
            payload = state["assembly"]
        else:
            payload = synthetic_verification(VerificationRequest.model_validate(body)).model_dump(
                mode="json"
            )
        credential = signed(key, binding, body, payload)
        if state["failure"] == "signature":
            credential = signed(
                source_key if operation == "verification" else verifier_key, binding, body, payload
            )
        return httpx.Response(
            200,
            json={
                "owner_service": binding.owner_service,
                "payload": payload,
                "credential": credential,
            },
        )

    monkeypatch.setenv("SYNTHETIC_SUBJECT_UNIT_SOURCE_CREDENTIAL", "synthetic-unit-only")
    monkeypatch.setenv("DPM_COMPOSITE_SOURCES_JSON", configuration.model_dump_json())
    monkeypatch.setenv(
        "DPM_COMPOSITE_HISTORICAL_POLICY_ADMISSION_JSON", historical_config.model_dump_json()
    )
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        monkeypatch.setattr(
            composite_source_service,
            "get_shared_source_http_client",
            lambda *args, **kwargs: client,
        )
        service = composite_source_service.build_composite_subject_service(repository)
        yield service, repository, historical, subject, policy, evaluation, state
