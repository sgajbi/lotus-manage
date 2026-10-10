"""Populated 0044 history remains byte-for-byte stable after forward admission migration."""

import json

import psycopg
from psycopg import sql
from psycopg.rows import dict_row
import pytest

import src.infrastructure.postgres_migrations as migrations
from src.infrastructure.composites.postgres import PostgresDpmCompositeRepository
from tests.composite_monthly_amendment_helpers import (
    corrected_monthly_proposal,
    seed_complete_monthly_root,
)
from tests.composite_staged_eligibility_helpers import finalization_material
from tests.integration.dpm.composites.test_composite_monthly_amendment_postgres import approval_for
from tests.integration.dpm.composites.test_composite_staged_upgrade_postgres import (
    CONTROL_TABLES,
    payload_rows,
)
from tests.integration.dpm.network_runtime import disposable_database


def without_legacy_control_versions(value):
    if isinstance(value, list):
        return [without_legacy_control_versions(item) for item in value]
    if not isinstance(value, dict):
        return value
    wire = {key: without_legacy_control_versions(item) for key, item in value.items()}
    if (
        wire.get("product_name")
        in {
            "CompositeMonthlyPolicyProposal",
            "CompositeMonthlyPolicyApproval",
            "CompositeMonthlyEvaluationProposal",
            "CompositeMonthlyEvaluationApproval",
        }
        and wire.get("product_version") == "v1"
    ):
        wire.pop("product_version")
    return wire


@pytest.mark.parametrize(
    "profile", ["v1", "v2", "staged", "v1_missing_versions", "v2_missing_versions"]
)
def test_populated_0044_upgrade_preserves_old_roots_corrections_and_staged_history(
    monkeypatch, profile
):
    loader = migrations._load_migrations
    omit_versions = profile.endswith("_missing_versions")
    with monkeypatch.context() as historical:
        historical.setattr(
            migrations,
            "_load_migrations",
            lambda *, namespace: [
                item for item in loader(namespace=namespace) if item.version <= "0044"
            ],
        )
        with disposable_database() as dsn:
            repository = PostgresDpmCompositeRepository(dsn=dsn)
            if profile == "staged":
                subject, controls, finalization = finalization_material()
                repository.save_eligibility_subject(subject=subject)
                for control in controls:
                    repository.save_subject_control(control=control)
                issued = repository.finalize_eligibility_subject(finalization=finalization)

                def resolve(fresh):
                    return fresh.finalize_eligibility_subject(finalization=finalization)
            else:
                scope, original, parent = seed_complete_monthly_root(
                    repository, definition_product_version=profile.removesuffix("_missing_versions")
                )
                issued = original
                if not omit_versions:
                    proposal = corrected_monthly_proposal(
                        original, parent, sequence=original.publication_sequence
                    )
                    repository.save_universe_attestation(attestation=proposal.universe)
                    repository.save_monthly_evaluation_proposal(proposal=proposal)
                    approval = approval_for(proposal, parent)
                    repository.save_monthly_evaluation_approval(approval=approval)
                    issued = repository.resolve_monthly_eligibility_evidence(
                        **scope,
                        evaluation_revision=proposal.evaluation_revision,
                        approval_content_hash=approval.content_hash,
                    )

                def resolve(fresh):
                    assert (
                        fresh.resolve_monthly_eligibility_evidence(
                            **scope,
                            evaluation_revision=original.approval.proposal.evaluation_revision,
                            approval_content_hash=original.approval.content_hash,
                        )
                        == original
                    )
                    return fresh.resolve_monthly_eligibility_evidence(
                        **scope,
                        evaluation_revision=issued.approval.proposal.evaluation_revision,
                        approval_content_hash=issued.approval.content_hash,
                    )

            with psycopg.connect(dsn, row_factory=dict_row) as connection:
                if omit_versions:
                    # These are valid pre-0045 v1 controls: omitted discriminators decode to v1.
                    # Keep the actual canonical hashes and relational selectors unchanged.
                    for table in CONTROL_TABLES:
                        rows = connection.execute(
                            sql.SQL("SELECT payload_json FROM {}").format(sql.Identifier(table))
                        ).fetchall()
                        assert len(rows) == 1
                        wire = without_legacy_control_versions(rows[0]["payload_json"])
                        assert "product_version" not in wire
                        connection.execute(
                            sql.SQL("UPDATE {} SET payload_json=%s::jsonb").format(
                                sql.Identifier(table)
                            ),
                            (json.dumps(wire),),
                        )
                    connection.commit()
                before = payload_rows(connection)
                checksums = connection.execute(
                    "SELECT version, checksum FROM schema_migrations ORDER BY version"
                ).fetchall()
            assert resolve(PostgresDpmCompositeRepository(dsn=dsn)) == issued
            historical.undo()
            for _ in range(2):
                with psycopg.connect(dsn, row_factory=dict_row) as connection:
                    migrations.apply_postgres_migrations(connection=connection, namespace="dpm")
                    assert payload_rows(connection) == before
                    assert (
                        connection.execute(
                            "SELECT version, checksum FROM schema_migrations WHERE version != 'dpm:0045' ORDER BY version"
                        ).fetchall()
                        == checksums
                    )
                    assert (
                        connection.execute(
                            "SELECT count(*) AS count FROM schema_migrations WHERE version='dpm:0045'"
                        ).fetchone()["count"]
                        == 1
                    )
                assert resolve(PostgresDpmCompositeRepository(dsn=dsn)) == issued
