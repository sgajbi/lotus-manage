"""Owning isolated PostgreSQL proof: source-authored, requires approved database execution."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import json
import hashlib
import os
from pathlib import Path
import subprocess

import psycopg
from psycopg.rows import dict_row
import pytest

from src.core.composite_eligibility.staged_subject import subject_key
from src.infrastructure.composites import universe_store
from src.infrastructure.composites.postgres import PostgresDpmCompositeRepository
from tests.composite_staged_eligibility_helpers import finalization_material, HEADERS
from tests.integration.dpm.network_runtime import disposable_database, native_api


@pytest.fixture
def database_material():
    with disposable_database() as dsn:
        repository = PostgresDpmCompositeRepository(dsn=dsn)
        subject, controls, finalization = finalization_material()
        repository.save_eligibility_subject(subject=subject)
        for control in controls:
            repository.save_subject_control(control=control)
        yield dsn, repository, subject, controls, finalization


def _accepted_source_freeze(path, expected_hash, root):
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == expected_hash
    freeze = json.loads(raw)
    for entry in freeze["files"]:
        source = (root / entry["path"]).resolve()
        source.relative_to(root.resolve())
        assert hashlib.sha256(source.read_bytes()).hexdigest() == entry["sha256"]
    return freeze


@pytest.mark.skipif(
    not os.environ.get("DPM_COMPOSITE_CONSUMER_RUNNER"),
    reason="Cross-repository native consumer proof requires an accepted source/runtime envelope",
)
def test_postgres_finalization_actual_performance_http_consumer_default_refusal(
    database_material, tmp_path
):
    runner = Path(os.environ["DPM_COMPOSITE_CONSUMER_RUNNER"])
    assert hashlib.sha256(runner.read_bytes()).hexdigest() == (
        "2fb498b5b546502d37d1193106eb8a39f6c3b65a338d823f16737efb7bc9f591"
    )
    consumer_freeze = Path(os.environ["DPM_COMPOSITE_CONSUMER_FREEZE"])
    consumer = json.loads(consumer_freeze.read_bytes())
    consumer_root = Path(consumer["root"]).resolve()
    consumer_hash = "c208585a4ea1e09935f9441cc82eb37aa834620d13ef78cf4422f077898f7633"
    _accepted_source_freeze(consumer_freeze, consumer_hash, consumer_root)
    producer_root = Path(__file__).resolve().parents[4]
    producer_hash = os.environ["DPM_COMPOSITE_PRODUCER_FREEZE_SHA256"]
    producer = _accepted_source_freeze(
        Path(os.environ["DPM_COMPOSITE_PRODUCER_FREEZE"]), producer_hash, producer_root
    )
    dsn, repository, subject, controls, finalization = database_material
    receipt = repository.finalize_eligibility_subject(finalization=finalization)
    scope = dict(
        tenant_id=subject.tenant_id,
        composite_id=subject.composite_id,
        definition_version=subject.definition_version,
    )
    membership_scope = scope | {"membership_revision": controls[2].target_membership_revision}
    canonical = {
        "definition": repository.get_definition(**scope),
        "membership": repository.get_membership_revision(**membership_scope),
        "attestation": repository.get_universe_attestation(
            **membership_scope, attestation_version=controls[2].evaluation_revision
        ),
    }
    assert all(value is not None for value in canonical.values())
    headers = HEADERS | {
        "X-Correlation-Id": "synthetic-native-consumer-proof",
        "X-Service-Identity": "local-network-proof",
        "X-Capabilities": "manage.write",
    }
    material = {
        "canonical": {key: value.model_dump(mode="json") for key, value in canonical.items()},
        "receipt": receipt.model_dump(mode="json"),
        "tenant_id": subject.tenant_id,
        "actor_id": headers["X-Actor-Id"],
        "role": headers["X-Role"],
        "admitted_headers": headers,
        "producer_provenance": {
            "repository": producer["repository"],
            "branch": producer["branch"],
            "base_head": producer["base"],
            "freeze_sha256": producer_hash,
        },
    }
    child_environment = os.environ.copy()
    # Each pinned interpreter must select its own standard library, not the parent's.
    child_environment.pop("PYTHONHOME", None)
    child_environment["PYTHONPATH"] = str(consumer_root)
    child_environment["LINEAGE_METADATA_DATABASE_URL"] = (
        "sqlite:///" + (tmp_path / "consumer-lineage.sqlite").as_posix()
    )
    with native_api(dsn) as (client, _):
        for case in ("positive-default-refusal", "foreign-tenant", "changed-digest"):
            result = subprocess.run(
                [
                    str(consumer_root / ".venv" / "Scripts" / "python.exe"),
                    str(runner),
                    "--manage-base-url",
                    str(client.base_url).rstrip("/") + "/api/v1",
                    "--consumer-freeze",
                    str(consumer_freeze),
                    "--consumer-freeze-sha256",
                    consumer_hash,
                    "--case",
                    case,
                ],
                cwd=consumer_root,
                env=child_environment,
                input=json.dumps(material),
                text=True,
                capture_output=True,
                timeout=60,
                check=False,
            )
            print(
                json.dumps(
                    {
                        "case": case,
                        "exit": result.returncode,
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                    }
                )
            )
            assert result.returncode == 0, result.stderr
            output = json.loads(result.stdout)
            assert output["case"] == case
            assert output["consumer_provenance"]["freeze_sha256"] == consumer_hash
        # A retained finalization cannot legally lose its publication. Do not disable
        # custody constraints to manufacture a consumer's hypothetical 409 state.
        with closing(psycopg.connect(dsn)) as connection:
            with pytest.raises(psycopg.errors.ForeignKeyViolation):
                connection.execute(
                    "DELETE FROM dpm_composite_membership_publications WHERE tenant_id=%s AND sequence=%s",
                    (subject.tenant_id, receipt.publication_sequence),
                )
            connection.rollback()
        assert repository.get_eligibility_finalization(key=subject_key(subject)) == receipt
        resolver_path = (
            f"/api/v1/rebalance/composites/{subject.composite_id}/definitions/"
            f"{subject.definition_version}/eligibility-evidence/resolve"
        )
        response = client.post(
            resolver_path,
            headers=headers,
            json=finalization.definition.source_authority.payload.eligibility_evaluation_binding.model_dump(
                mode="json"
            ),
        )
        assert response.status_code == 200, response.text
        assert response.json() == receipt.model_dump(mode="json")
    _accepted_source_freeze(consumer_freeze, consumer_hash, consumer_root)


def test_postgres_finalization_fresh_reader_and_registered_fresh_process_resolver(
    database_material,
):
    dsn, repository, subject, controls, finalization = database_material
    assert (
        repository.get_definition(
            tenant_id=subject.tenant_id,
            composite_id=subject.composite_id,
            definition_version=subject.definition_version,
        )
        is None
    )
    with ThreadPoolExecutor(max_workers=4) as workers:
        receipts = list(
            workers.map(
                lambda _: repository.finalize_eligibility_subject(finalization=finalization),
                range(8),
            )
        )
    assert all(receipt == receipts[0] for receipt in receipts)
    fresh = PostgresDpmCompositeRepository(dsn=dsn)
    assert fresh.get_eligibility_finalization(key=subject_key(subject)) == receipts[0]
    binding = finalization.definition.source_authority.payload.eligibility_evaluation_binding
    path = f"/api/v1/rebalance/composites/{subject.composite_id}/definitions/{subject.definition_version}/eligibility-evidence/resolve"
    # Genuine spawned API, no dependency override, no live/synthetic source registration.
    headers = HEADERS | {
        "X-Correlation-Id": "synthetic-staged-resolver-proof",
        "X-Service-Identity": "local-network-proof",
        "X-Capabilities": "manage.write",
    }
    with native_api(dsn) as (client, _):
        denied = client.post(path, headers=HEADERS, json=binding.model_dump(mode="json"))
        assert denied.status_code == 403
        assert denied.json()["reasonCode"] == "missing_headers:x-correlation-id"
        response = client.post(path, headers=headers, json=binding.model_dump(mode="json"))
        assert response.status_code == 200, response.text
        assert response.json() == receipts[0].model_dump(mode="json")
        wrong = binding.model_dump(mode="json") | {"digest": "sha256:" + "0" * 64}
        assert client.post(path, headers=headers, json=wrong).status_code == 422
    with psycopg.connect(dsn, row_factory=dict_row) as connection:
        catalog = connection.execute(
            "SELECT conname,pg_get_constraintdef(oid) AS definition FROM pg_constraint WHERE conname IN ('monthly_policy_approval_mode_fk','monthly_evaluation_policy_mode_fk','monthly_evaluation_approval_mode_fk') ORDER BY conname"
        ).fetchall()
        assert len(catalog) == 3
        assert all("custody_mode" in row["definition"] for row in catalog)
        print("Actual PostgreSQL custody FK catalog:", json.dumps(catalog, sort_keys=True))


def test_postgres_post_write_failure_rolls_back_definition_member_universe_publication_and_receipt(
    database_material, monkeypatch
):
    dsn, repository, subject, _, finalization = database_material
    actual = universe_store.store_universe_attestation

    def fail_after_universe(**kwargs):
        actual(**kwargs)
        raise RuntimeError("owned-fault-after-universe")

    with monkeypatch.context() as fault:
        fault.setattr(universe_store, "store_universe_attestation", fail_after_universe)
        with pytest.raises(RuntimeError, match="owned-fault-after-universe"):
            repository.finalize_eligibility_subject(finalization=finalization)
    with psycopg.connect(dsn) as connection:
        for table in (
            "dpm_composite_definitions",
            "dpm_composite_membership_revisions",
            "dpm_composite_universe_attestations",
            "dpm_composite_membership_publications",
            "dpm_composite_eligibility_finalizations",
        ):
            assert connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0] == 0
    assert repository.get_eligibility_subject(key=subject_key(subject)) == subject
    assert (
        repository.finalize_eligibility_subject(finalization=finalization).publication_sequence >= 1
    )


@pytest.mark.parametrize("kind", ["policy_approval", "evaluation_proposal", "evaluation_approval"])
def test_direct_sql_legacy_child_cannot_reference_staged_predecessor_through_nulls(
    database_material, kind
):
    dsn, repository, subject, controls, finalization = database_material
    repository.finalize_eligibility_subject(finalization=finalization)
    tables = {
        "policy_approval": "dpm_composite_monthly_policy_approvals",
        "evaluation_proposal": "dpm_composite_monthly_evaluation_proposals",
        "evaluation_approval": "dpm_composite_monthly_evaluation_approvals",
    }
    expected = {
        "policy_approval": "monthly_policy_approval_mode_fk",
        "evaluation_proposal": "monthly_evaluation_policy_mode_fk",
        "evaluation_approval": "monthly_evaluation_approval_mode_fk",
    }
    with psycopg.connect(dsn, row_factory=dict_row) as connection:
        connection.execute("DELETE FROM dpm_composite_eligibility_finalizations")
        connection.execute("DELETE FROM dpm_composite_monthly_evaluation_approvals")
        if kind != "evaluation_approval":
            connection.execute("DELETE FROM dpm_composite_monthly_evaluation_proposals")
        if kind == "policy_approval":
            connection.execute("DELETE FROM dpm_composite_monthly_policy_approvals")
        scope = (subject.tenant_id, subject.composite_id, subject.definition_version, subject.month)
        # NULL subject selectors recreate the exact MATCH SIMPLE hole: the mode FK must reject it.
        with pytest.raises(psycopg.errors.ForeignKeyViolation) as failure:
            if kind == "policy_approval":
                control = controls[1]
                connection.execute(
                    f"INSERT INTO {tables[kind]} (tenant_id,composite_id,definition_version,month,proposal_revision,proposal_content_hash,content_hash,payload_json) VALUES (%s,%s,%s,%s,%s,%s,%s,%s::jsonb)",
                    (
                        *scope,
                        controls[0].proposal.proposal_revision,
                        controls[0].content_hash,
                        control.content_hash,
                        control.model_dump_json(),
                    ),
                )
            elif kind == "evaluation_proposal":
                control = controls[2]
                connection.execute(
                    f"INSERT INTO {tables[kind]} (tenant_id,composite_id,definition_version,month,evaluation_revision,parent_membership_revision,content_hash,payload_json) VALUES (%s,%s,%s,%s,%s,%s,%s,%s::jsonb)",
                    (
                        *scope,
                        control.evaluation_revision,
                        control.target_membership_revision,
                        control.content_hash,
                        control.model_dump_json(),
                    ),
                )
            else:
                control = controls[3]
                connection.execute(
                    f"INSERT INTO {tables[kind]} (tenant_id,composite_id,definition_version,month,evaluation_revision,membership_revision,content_hash,payload_json) VALUES (%s,%s,%s,%s,%s,%s,%s,%s::jsonb)",
                    (
                        *scope,
                        control.proposal.evaluation_revision,
                        control.proposal.target_membership_revision,
                        control.content_hash,
                        control.model_dump_json(),
                    ),
                )
        assert failure.value.diag.constraint_name == expected[kind]
        connection.rollback()  # All deliberate destructive mutations remain uncommitted.
    assert repository.get_eligibility_finalization(key=subject_key(subject)) is not None


def test_reserved_definition_cannot_be_committed_without_atomic_finalization(database_material):
    dsn, repository, subject, _, finalization = database_material
    definition = finalization.definition
    with closing(psycopg.connect(dsn)) as connection:
        connection.execute(
            "INSERT INTO dpm_composite_definitions (tenant_id,composite_id,definition_version,inception_date,content_hash,payload_json) VALUES (%s,%s,%s,%s,%s,%s::jsonb)",
            (
                *subject_key(subject)[:3],
                definition.inception_date,
                definition.content_hash,
                json.dumps(definition.model_dump(mode="json")),
            ),
        )
        with pytest.raises(psycopg.errors.RaiseException, match="FINALIZATION_REQUIRED"):
            connection.commit()
    assert connection.closed
    assert repository.get_eligibility_finalization(key=subject_key(subject)) is None


@pytest.mark.parametrize("kind", ["policy_approval", "evaluation_proposal", "evaluation_approval"])
def test_direct_sql_staged_child_cannot_reference_legacy_predecessor(database_material, kind):
    dsn, repository, subject, controls, finalization = database_material
    repository.finalize_eligibility_subject(finalization=finalization)
    scope = (subject.tenant_id, subject.composite_id, subject.definition_version, subject.month)
    legacy_policy = controls[0].proposal
    legacy_approval = controls[1].approval
    with psycopg.connect(dsn, row_factory=dict_row) as connection:
        # Rebuild only this transaction's predecessor branch as legacy, preserving actual canonical parent.
        connection.execute("DELETE FROM dpm_composite_eligibility_finalizations")
        connection.execute("DELETE FROM dpm_composite_monthly_evaluation_approvals")
        connection.execute("DELETE FROM dpm_composite_monthly_evaluation_proposals")
        connection.execute("DELETE FROM dpm_composite_monthly_policy_approvals")
        connection.execute("DELETE FROM dpm_composite_monthly_policy_proposals")
        connection.execute(
            "INSERT INTO dpm_composite_monthly_policy_proposals (tenant_id,composite_id,definition_version,month,proposal_revision,content_hash,payload_json) VALUES (%s,%s,%s,%s,%s,%s,%s::jsonb)",
            (
                *scope,
                legacy_policy.proposal_revision,
                legacy_policy.content_hash,
                legacy_policy.model_dump_json(),
            ),
        )
        if kind != "policy_approval":
            connection.execute(
                "INSERT INTO dpm_composite_monthly_policy_approvals (tenant_id,composite_id,definition_version,month,proposal_revision,proposal_content_hash,content_hash,payload_json) VALUES (%s,%s,%s,%s,%s,%s,%s,%s::jsonb)",
                (
                    *scope,
                    legacy_policy.proposal_revision,
                    legacy_policy.content_hash,
                    legacy_approval.content_hash,
                    legacy_approval.model_dump_json(),
                ),
            )
        if kind == "evaluation_approval":
            payload = controls[2].model_dump(mode="json")
            payload["policy_approval"]["content_hash"] = legacy_approval.content_hash
            connection.execute(
                "INSERT INTO dpm_composite_monthly_evaluation_proposals (tenant_id,composite_id,definition_version,month,evaluation_revision,parent_membership_revision,content_hash,payload_json) VALUES (%s,%s,%s,%s,%s,%s,%s,%s::jsonb)",
                (
                    *scope,
                    controls[2].evaluation_revision,
                    controls[2].target_membership_revision,
                    controls[2].content_hash,
                    json.dumps(payload),
                ),
            )
        with pytest.raises(psycopg.errors.ForeignKeyViolation) as failure:
            if kind == "policy_approval":
                connection.execute(
                    "INSERT INTO dpm_composite_monthly_policy_approvals (tenant_id,composite_id,definition_version,month,proposal_revision,proposal_content_hash,content_hash,payload_json,subject_revision,subject_content_hash) VALUES (%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s)",
                    (
                        *scope,
                        legacy_policy.proposal_revision,
                        legacy_policy.content_hash,
                        controls[1].content_hash,
                        controls[1].model_dump_json(),
                        subject.subject_revision,
                        subject.content_hash,
                    ),
                )
            elif kind == "evaluation_proposal":
                payload = controls[2].model_dump(mode="json")
                payload["policy_approval"]["content_hash"] = legacy_approval.content_hash
                connection.execute(
                    "INSERT INTO dpm_composite_monthly_evaluation_proposals (tenant_id,composite_id,definition_version,month,evaluation_revision,parent_membership_revision,content_hash,payload_json,subject_revision,subject_content_hash,staged_policy_content_hash) VALUES (%s,%s,%s,%s,%s,NULL,%s,%s::jsonb,%s,%s,%s)",
                    (
                        *scope,
                        controls[2].evaluation_revision,
                        controls[2].content_hash,
                        json.dumps(payload),
                        subject.subject_revision,
                        subject.content_hash,
                        legacy_approval.content_hash,
                    ),
                )
            else:
                connection.execute(
                    "INSERT INTO dpm_composite_monthly_evaluation_approvals (tenant_id,composite_id,definition_version,month,evaluation_revision,membership_revision,content_hash,payload_json,subject_revision,subject_content_hash,staged_proposal_content_hash) VALUES (%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s,%s)",
                    (
                        *scope,
                        controls[2].evaluation_revision,
                        controls[2].target_membership_revision,
                        controls[3].content_hash,
                        controls[3].model_dump_json(),
                        subject.subject_revision,
                        subject.content_hash,
                        controls[2].content_hash,
                    ),
                )
        assert failure.value.diag.constraint_name in {
            "monthly_policy_approval_subject_fk",
            "monthly_policy_approval_mode_fk",
            "monthly_evaluation_subject_policy_fk",
            "monthly_evaluation_policy_mode_fk",
            "monthly_evaluation_approval_subject_fk",
            "monthly_evaluation_approval_mode_fk",
        }
        connection.rollback()
    assert repository.get_eligibility_finalization(key=subject_key(subject)) is not None
