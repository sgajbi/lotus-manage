"""Populated 0043 custody survives amendment migration without changing issued products."""

import psycopg
from psycopg.rows import dict_row
import pytest

import src.infrastructure.postgres_migrations as migrations
from src.infrastructure.composites.postgres import PostgresDpmCompositeRepository
from tests.composite_monthly_amendment_helpers import seed_complete_monthly_root
from tests.composite_staged_eligibility_helpers import finalization_material
from tests.integration.dpm.composites.test_composite_staged_upgrade_postgres import payload_rows
from tests.integration.dpm.network_runtime import disposable_database


@pytest.mark.parametrize("profile", ["v1", "v2", "staged"])
def test_populated_0043_upgrade_retains_exact_products_and_receipts(monkeypatch, profile):
    loader = migrations._load_migrations
    with monkeypatch.context() as historical:
        historical.setattr(
            migrations,
            "_load_migrations",
            lambda *, namespace: [
                item for item in loader(namespace=namespace) if item.version <= "0043"
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
                scope, issued, _ = seed_complete_monthly_root(
                    repository, definition_product_version=profile
                )

                def resolve(fresh):
                    return fresh.resolve_monthly_eligibility_evidence(
                        **scope,
                        evaluation_revision=issued.approval.proposal.evaluation_revision,
                        approval_content_hash=issued.approval.content_hash,
                    )

            with psycopg.connect(dsn, row_factory=dict_row) as connection:
                before = payload_rows(connection)
                assert all(before.values())
                assert (
                    connection.execute(
                        "SELECT max(version) AS version FROM schema_migrations WHERE version LIKE 'dpm:%'"
                    ).fetchone()["version"]
                    == "dpm:0043"
                )
            historical.undo()
            for _ in range(2):
                with psycopg.connect(dsn, row_factory=dict_row) as connection:
                    migrations.apply_postgres_migrations(connection=connection, namespace="dpm")
                    assert payload_rows(connection) == before
                    assert (
                        connection.execute(
                            "SELECT count(*) AS count FROM schema_migrations WHERE version='dpm:0044'"
                        ).fetchone()["count"]
                        == 1
                    )
                fresh = PostgresDpmCompositeRepository(dsn=dsn)
                assert resolve(fresh).model_dump(mode="json") == issued.model_dump(mode="json")
