"""An unchanged sealed pre-chronology synthetic receipt remains archival custody."""

import json
from pathlib import Path

import psycopg

from src.core.composite_eligibility.staged_publication import SubjectFinalizationReceipt
from src.infrastructure.composites.postgres import PostgresDpmCompositeRepository
from tests.composite_staged_eligibility_helpers import BASE, CHECKER, HEADERS
from tests.integration.dpm.network_runtime import disposable_database, native_api


def test_original_sealed_receipt_survives_upgrade_restart_resolution_and_exact_replay():
    wire = json.loads(
        (
            Path(__file__).parents[3]
            / "fixtures/composites/historical-configured-finalization.json"
        ).read_text(encoding="utf-8")
    )
    receipt = SubjectFinalizationReceipt.model_validate(wire)
    assert (
        receipt.content_hash
        == "sha256:2acd73156df13c857bdd019631b84f741e920dc887e4c5b6c48df2da63c969f3"
    )
    finalization = receipt.finalization
    subject, approval = finalization.subject, finalization.evaluation_approval
    assert (
        finalization.definition.authority_approval.claims.approved_at
        == "2026-10-02T00:00:00.000000Z"
    )
    assert approval.approved_at == "2026-10-09T04:11:39.899501Z"
    headers = HEADERS | {
        "X-Service-Identity": "synthetic-historical-upgrade",
        "X-Capabilities": "manage.write",
        "X-Correlation-Id": "synthetic-historical-upgrade",
    }
    key = (
        subject.tenant_id,
        subject.composite_id,
        subject.definition_version,
        subject.subject_revision,
    )
    binding = (
        finalization.definition.source_authority.payload.eligibility_evaluation_binding.model_dump(
            mode="json"
        )
    )
    resolve = "/api/v1/rebalance/composites/synthetic-composite/definitions/synthetic-definition/eligibility-evidence/resolve"
    command = {
        "evaluation_revision": approval.proposal.evaluation_revision,
        "expected_approval_content_hash": approval.content_hash,
        "definition": finalization.definition.model_dump(
            mode="json",
            exclude={
                "product_name",
                "tenant_id",
                "composite_id",
                "definition_version",
                "created_by",
            },
        ),
    }
    with disposable_database() as dsn:
        repository = PostgresDpmCompositeRepository(dsn=dsn)
        # Restore exact trusted historical custody, not a fresh API approval or reissued hash.
        repository.save_eligibility_subject(subject=subject)
        for control in (
            approval.proposal.policy_approval.proposal,
            approval.proposal.policy_approval,
            approval.proposal,
            approval,
        ):
            repository.save_subject_control(control=control)
        restored = repository.finalize_eligibility_subject(finalization=finalization)
        assert restored.model_dump(mode="json") == wire
        with psycopg.connect(dsn) as connection:
            before = connection.execute(
                "SELECT content_hash,payload_json FROM dpm_composite_eligibility_finalizations"
            ).fetchall()
        # Repeat migration initialization and exercise two genuinely fresh API processes.
        for _ in range(2):
            repository = PostgresDpmCompositeRepository(dsn=dsn)
            assert repository.get_eligibility_finalization(key=key) == receipt
            with native_api(dsn) as (client, _):
                for response in (
                    client.get(BASE + "/finalization", headers=headers),
                    client.post(resolve, json=binding, headers=headers),
                    client.put(
                        BASE + "/finalization",
                        json=command,
                        headers=headers | {"X-Actor-Id": CHECKER},
                    ),
                ):
                    assert response.status_code == 200, response.text
                    assert response.json() == wire
                    assert (
                        response.headers["X-Composite-Evidence-Diagnostic"]
                        == "HISTORICAL_AUTHORITY_CLOCK_MISMATCH"
                    )
                    assert response.json()["completeness"] == "UNVERIFIED"
                    assert response.json()["finalization"]["official_activation"] == "UNAVAILABLE"
                wrong = {**binding, "digest": "sha256:" + "0" * 64}
                refused = client.post(resolve, json=wrong, headers=headers)
                assert refused.status_code == 422, refused.text
                tenant = client.post(
                    resolve, json=binding, headers=headers | {"X-Tenant-Id": "foreign-tenant"}
                )
                assert tenant.status_code == 404, tenant.text
                changed = client.put(
                    BASE + "/finalization",
                    json={**command, "expected_approval_content_hash": wrong["digest"]},
                    headers=headers | {"X-Actor-Id": CHECKER},
                )
                assert changed.status_code == 409, changed.text
                publications = client.get(
                    "/api/v1/rebalance/composites/publications", headers=headers
                )
                assert publications.status_code == 200 and len(publications.json()["items"]) == 1
        with psycopg.connect(dsn) as connection:
            assert (
                connection.execute(
                    "SELECT content_hash,payload_json FROM dpm_composite_eligibility_finalizations"
                ).fetchall()
                == before
            )
