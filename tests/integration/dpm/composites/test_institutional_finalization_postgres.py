"""Native HTTPS and PostgreSQL verification proof over explicitly controlled prior history.

Fixture controls are not genuine historical institutional approvals. The API owns
fresh finalization, publication and subsequent exact persisted reads/replay.
"""

import json
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler

import pytest


from src.core.composite_eligibility.verification import VerificationReceipt, VerificationRequest
from src.infrastructure.composites.institutional_configuration import (
    InstitutionalVerificationConfiguration,
)
from src.infrastructure.composites.postgres import PostgresDpmCompositeRepository
from tests.composite_institutional_helpers import (
    authority_result,
    configuration_material,
    institutional_material,
    sign_artifact,
)
from tests.composite_staged_eligibility_helpers import BASE, CHECKER, HEADERS
from tests.integration.dpm.network_runtime import disposable_database, native_api
from tests.integration.dpm.https_runtime import trusted_https_server


@contextmanager
def controlled_https_verifier(tmp_path, monkeypatch, request, artifact):
    configuration, signer, verifier = configuration_material()
    state = {"calls": [], "deny": False}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_POST(self):
            assert self.headers["Authorization"] == "Bearer controlled-test-only"
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            state["calls"].append(body)
            if state["deny"]:
                self.send_response(503)
                self.end_headers()
                return
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
            envelope = dict(
                owner_service=configuration.verifier.owner_service,
                payload=payload,
                credential=sign_artifact(verifier, configuration.verifier, body, payload),
            )
            raw = json.dumps(envelope).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

    monkeypatch.setenv(configuration.verifier.credential_env, "controlled-test-only")
    with trusted_https_server(Handler, tmp_path, monkeypatch) as server:
        wire = configuration.model_dump(mode="json")
        wire["verifier"]["endpoint"] = f"https://127.0.0.1:{server.server_port}/verification"
        configuration = InstitutionalVerificationConfiguration.model_validate(wire)
        yield configuration.model_dump_json(), state


def capture(tmp_path, name, response):
    # Persist raw status, headers and body before inspecting admission outcomes.
    (tmp_path / (name + ".body")).write_bytes(response.content)
    (tmp_path / (name + ".json")).write_text(
        json.dumps(dict(status=response.status_code, headers=dict(response.headers)), indent=2),
        encoding="utf-8",
    )
    return response


@pytest.mark.parametrize("concurrent", [False, True])
def test_native_institutional_publication_restart_and_unchanged_replay(
    tmp_path, monkeypatch, concurrent
):
    subject, controls, definition, artifact, request = institutional_material()
    command = dict(
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
    headers = HEADERS | {
        "X-Actor-Id": CHECKER,
        "X-Service-Identity": "controlled-institutional-test",
        "X-Capabilities": "manage.write",
        "X-Correlation-Id": "controlled-institutional-test",
    }
    with disposable_database() as dsn:
        repository = PostgresDpmCompositeRepository(dsn=dsn)
        # Controlled adapter history only; never present these inserts as API approval lifecycle.
        repository.save_eligibility_subject(subject=subject)
        for control in controls:
            repository.save_subject_control(control=control)
        with controlled_https_verifier(tmp_path, monkeypatch, request, artifact) as (
            configuration,
            state,
        ):
            with native_api(dsn, institutional_config=configuration) as (client, process):

                def finalize(index):
                    return capture(
                        tmp_path,
                        f"finalize-{index}",
                        client.put(BASE + "/finalization", json=command, headers=headers),
                    )

                if concurrent:
                    with ThreadPoolExecutor(max_workers=4) as workers:
                        responses = list(workers.map(finalize, range(4)))
                else:
                    responses = [finalize(0)]
                response = responses[0]
                assert response.status_code == 200, response.text
                original = response.content
                assert all(
                    item.status_code == 200 and item.content == original for item in responses
                )
                receipt = response.json()
                assert receipt["product_version"] == "v2"
                assert receipt["completeness"] == "UNVERIFIED"
                assert receipt["finalization"]["official_activation"] == "UNAVAILABLE"
                assert 4 <= len(state["calls"]) <= (16 if concurrent else 4)
                admission_calls = len(state["calls"])
                first_pid = process.pid
            state["deny"] = True
            # Fresh default-unavailable API process retrieves original custody without new admission.
            with native_api(dsn) as (client, process):
                assert process.pid != first_pid
                replay = capture(
                    tmp_path,
                    "replay",
                    client.put(BASE + "/finalization", json=command, headers=headers),
                )
                assert replay.status_code == 200 and replay.content == original
                read = capture(
                    tmp_path, "read", client.get(BASE + "/finalization", headers=headers)
                )
                assert read.status_code == 200 and read.content == original
                binding = receipt["finalization"]["definition"]["source_authority"]["payload"][
                    "eligibility_evaluation_binding"
                ]
                resolved = capture(
                    tmp_path,
                    "resolve",
                    client.post(
                        "/api/v1/rebalance/composites/synthetic-composite/definitions/synthetic-definition/eligibility-evidence/resolve",
                        json=binding,
                        headers=headers,
                    ),
                )
                assert resolved.status_code == 200 and resolved.content == original
                changed = {**command, "expected_approval_content_hash": "sha256:" + "f" * 64}
                denied = capture(
                    tmp_path,
                    "changed",
                    client.put(BASE + "/finalization", json=changed, headers=headers),
                )
                assert denied.status_code == 409
                publications = client.get(
                    "/api/v1/rebalance/composites/publications", headers=headers
                )
                assert publications.status_code == 200 and len(publications.json()["items"]) == 1
            assert len(state["calls"]) == admission_calls
