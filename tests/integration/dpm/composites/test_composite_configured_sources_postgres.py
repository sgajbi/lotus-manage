"""Configured signed sources over actual HTTP and PostgreSQL without API overrides.

Prospective controls are retained fixture history; runtime owns current evaluation
time. This is a synthetic adapter proof, not bank identity or financial qualification.
"""

from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from src.core.composite_eligibility.verification import VerificationRequest
from src.core.composite_eligibility.staged_subject import CandidateUniverse
from src.infrastructure.composites.postgres import PostgresDpmCompositeRepository
from tests.composite_staged_eligibility_helpers import (
    BASE,
    HEADERS,
    CHECKER,
    lifecycle_material,
    synthetic_verification,
)
from tests.integration.dpm.network_runtime import disposable_database, native_api
from tests.unit.api.test_composite_subject_lifecycle_routes import subject_body, evaluation_body
from tests.unit.dpm.infrastructure.test_composite_configured_sources import encoded, signed
from tests.unit.dpm.infrastructure.test_composite_monthly_source_assembly import assembly_material
from src.infrastructure.composites.source_configuration import (
    SourceBinding,
    CompositeSourceConfiguration,
)


@contextmanager
def synthetic_sources(monkeypatch):
    _, assembly = assembly_material()
    _, subject, *_ = lifecycle_material()
    source_key, verifier_key = Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate()
    state = {"deny": False, "calls": []}
    bindings = {}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_POST(self):
            assert self.headers["Authorization"] == "Bearer synthetic-test-only"
            request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            operation = self.path[1:]
            state["calls"].append(operation)
            binding = bindings[operation]
            if operation == "candidates":
                key, payload = source_key, subject.universe.model_dump(mode="json")
                payload["definition_version"] = request["definition_version"]
                payload["content_hash"] = ""
                payload = CandidateUniverse.model_validate(payload).model_dump(mode="json")
            elif operation == "observations":
                key, payload = source_key, assembly
            else:
                if state["deny"]:
                    self.send_response(503)
                    self.end_headers()
                    return
                key = verifier_key
                payload = synthetic_verification(
                    VerificationRequest.model_validate(request)
                ).model_dump(mode="json")
            body = json.dumps(
                {
                    "owner_service": binding.owner_service,
                    "payload": payload,
                    "credential": signed(key, binding, request, payload),
                }
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    for operation in ("candidates", "observations", "verification"):
        key = verifier_key if operation == "verification" else source_key
        bindings[operation] = SourceBinding(
            operation=operation,
            tenant_id=subject.tenant_id,
            owner_service="synthetic-source",
            endpoint=f"http://127.0.0.1:{server.server_port}/{operation}",
            allow_local_http=True,
            issuer="urn:synthetic:fixture:issuer",
            receipt_issuer_id="synthetic-fixture-issuer" if operation == "verification" else None,
            principal_id="synthetic-fixture-verifier" if operation == "verification" else "source",
            credential_env="SYNTHETIC_CONFIGURED_SOURCE_CREDENTIAL",
            evidence_posture="SYNTHETIC_NON_CERTIFYING",
            verification_purposes=("ELIGIBILITY_POLICY_EVALUATION", "COMPOSITE_MONTHLY_SOURCE_CUT")
            if operation == "verification"
            else (),
            keys=[
                {
                    "kid": "test-key",
                    "x": encoded(key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)),
                }
            ],
        )
    configuration = CompositeSourceConfiguration(bindings=tuple(bindings.values()))
    monkeypatch.setenv("SYNTHETIC_CONFIGURED_SOURCE_CREDENTIAL", "synthetic-test-only")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield configuration.model_dump_json(), state
    finally:
        server.shutdown()
        server.server_close()
        thread.join(10)
        assert not thread.is_alive()


def test_registered_configured_evaluation_refusal_recovery_and_restart(monkeypatch):
    _, subject, policy, approved_policy, evaluation, *_ = lifecycle_material()
    headers = HEADERS | {
        "X-Service-Identity": "synthetic-native-source-proof",
        "X-Capabilities": "manage.write",
        "X-Correlation-Id": "synthetic-source-proof",
    }
    url = BASE + "/evaluations/synthetic.evaluation.r1"
    with disposable_database() as dsn, synthetic_sources(monkeypatch) as (configuration, state):
        repository = PostgresDpmCompositeRepository(dsn=dsn)
        repository.save_eligibility_subject(subject=subject)
        for control in (policy, approved_policy):
            repository.save_subject_control(control=control)
        with native_api(dsn, composite_config=configuration) as (client, _):
            fresh = client.put(
                BASE.replace("synthetic-definition", "runtime-definition"),
                json=subject_body(subject),
                headers=headers,
            )
            assert fresh.status_code == 200, fresh.text
            assert fresh.json()["universe"]["population_verification"] == "UNVERIFIED"
            state["deny"] = True
            refused = client.put(
                url, json=evaluation_body(policy, approved_policy, evaluation), headers=headers
            )
            assert refused.status_code == 503, refused.text
            assert refused.json()["detail"]["code"] == "COMPOSITE_SOURCE_TRANSPORT_UNAVAILABLE"
            assert (
                repository.get_subject_control(
                    key=(
                        subject.tenant_id,
                        subject.composite_id,
                        subject.definition_version,
                        subject.subject_revision,
                    ),
                    kind="CompositeSubjectEvaluationProposal",
                    revision=evaluation.evaluation_revision,
                )
                is None
            )
            state["deny"] = False
            accepted = client.put(
                url, json=evaluation_body(policy, approved_policy, evaluation), headers=headers
            )
            assert accepted.status_code == 200, accepted.text
            retained = accepted.json()
            assert (
                retained["source_assembly_evidence"]["assembly"]["inputs"]
                == assembly_material()[1]["inputs"]
            )
            assert (
                retained["source_assembly_evidence"]["verification"]["posture"]
                == "SYNTHETIC_NON_CERTIFYING"
            )
            flow = next(
                item
                for item in retained["evaluation"]["portfolios"][0]["assessments"]
                if item["rule"] == "SIGNIFICANT_FLOW"
            )
            assert (flow["numerator"], flow["denominator"], flow["ratio"]) == ("50", "1000", "0.05")
            body = {"expected_proposal_content_hash": retained["content_hash"]}
            self_approval = client.put(url + "/approval", json=body, headers=headers)
            assert self_approval.status_code == 403, self_approval.text
            approved = client.put(
                url + "/approval", json=body, headers=headers | {"X-Actor-Id": CHECKER}
            )
            assert approved.status_code == 200, approved.text
            assert approved.json()["evidence_kind"] == "SYNTHETIC_UNSIGNED"
            approval = approved.json()
        calls = list(state["calls"])
        # Default unavailable composition replays retained custody after process restart.
        with native_api(dsn) as (client, _):
            replay = client.put(
                url, json=evaluation_body(policy, approved_policy, evaluation), headers=headers
            )
            assert replay.status_code == 200 and replay.json() == retained
            assert (
                client.put(
                    url + "/approval", json=body, headers=headers | {"X-Actor-Id": CHECKER}
                ).json()
                == approval
            )
        assert state["calls"] == calls
