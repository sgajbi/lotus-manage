"""PostgreSQL upgrade and concurrency proof for tenant-owned construction state."""

from __future__ import annotations

import json
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from typing import Any

import pytest

import src.api.services.construction_service as construction_service
from src.api.request_models import RebalanceRequest
from src.core.construction.models import (
    ConstructionAlternativeSelection,
    ConstructionAlternativeSet,
)
from src.core.construction.repository import ConstructionAlternativeSetNotFoundError
from src.core.construction.vocabulary import ConstructionMethodStatus
from src.core.construction.vocabulary import ConstructionMethod
from src.core.rebalance_runs.service import DpmRunSupportService
from src.infrastructure import postgres_migrations
from src.infrastructure.construction.postgres import PostgresConstructionRepository
from src.infrastructure.postgres_access import connect_postgres
from src.infrastructure.rebalance_runs import PostgresDpmRunRepository
from tests.integration.dpm.postgres_prerequisite import postgres_dsn_or_skip
from tests.shared.factories import valid_api_payload


def _set(*, set_id: str, tenant_id: str | None, request_hash: str) -> ConstructionAlternativeSet:
    return ConstructionAlternativeSet(
        alternative_set_id=set_id,
        tenant_id=tenant_id,
        portfolio_id="pf_construction_tenant_proof",
        as_of="2026-10-02",
        status=ConstructionMethodStatus.BLOCKED,
        alternatives=[],
        request_hash=request_hash,
    )


def _selection(*, set_id: str, tenant_id: str | None) -> ConstructionAlternativeSelection:
    return ConstructionAlternativeSelection(
        selection_id=f"casel_{uuid.uuid4().hex}",
        tenant_id=tenant_id,
        alternative_set_id=set_id,
        alternative_id="alt_proof",
        actor_id="pm_tenant_proof",
        reason_code="TENANT_FENCE_PROOF",
    )


def test_construction_owner_constraint_is_created_in_each_schema() -> None:
    dsn = postgres_dsn_or_skip("construction tenant constraint schema ownership")
    import psycopg
    from psycopg import sql
    from psycopg.rows import dict_row

    schemas = [f"construction_owner_{uuid.uuid4().hex[:12]}" for _ in range(2)]
    with psycopg.connect(dsn, row_factory=dict_row) as connection:
        try:
            for schema in schemas:
                connection.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
                connection.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
                postgres_migrations.apply_postgres_migrations(
                    connection=connection,
                    namespace="dpm",
                )

            constraints = connection.execute(
                """
                SELECT namespace.nspname AS schema_name
                FROM pg_constraint constraint_record
                JOIN pg_class relation
                  ON relation.oid = constraint_record.conrelid
                JOIN pg_namespace namespace
                  ON namespace.oid = relation.relnamespace
                WHERE constraint_record.conname = 'fk_dpm_construction_selection_owner'
                  AND namespace.nspname = ANY(%s)
                ORDER BY namespace.nspname
                """,
                (schemas,),
            ).fetchall()
            assert [row["schema_name"] for row in constraints] == sorted(schemas)
        finally:
            connection.execute("SET search_path TO public")
            for schema in schemas:
                connection.execute(
                    sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(schema))
                )
            connection.commit()


def test_construction_tenant_migration_quarantines_legacy_and_scopes_concurrent_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dsn = postgres_dsn_or_skip("construction tenant migration and concurrency")
    import psycopg
    from psycopg.conninfo import make_conninfo
    from psycopg.rows import dict_row

    schema = f"construction_tenant_{uuid.uuid4().hex[:12]}"
    admin = psycopg.connect(dsn, row_factory=dict_row)
    try:
        admin.execute(f'CREATE SCHEMA "{schema}"')
        admin.commit()
        admin.execute(f'SET search_path TO "{schema}"')
        migrations = postgres_migrations._load_migrations(namespace="dpm")
        versions = [migration.version for migration in migrations]
        migration_index = versions.index("0037")
        assert migration_index == len(versions) - 1
        monkeypatch.setattr(
            postgres_migrations,
            "_load_migrations",
            lambda *, namespace: migrations[:migration_index],
        )
        postgres_migrations.apply_postgres_migrations(connection=admin, namespace="dpm")

        legacy_set = _set(
            set_id=f"cas_legacy_{uuid.uuid4().hex}",
            tenant_id=None,
            request_hash="sha256:legacy-construction",
        )
        legacy_selection = _selection(set_id=legacy_set.alternative_set_id, tenant_id=None)
        admin.execute(
            """
            INSERT INTO dpm_construction_alternative_sets (
                alternative_set_id, portfolio_id, as_of, status, request_hash,
                idempotency_key, input_mode, source_supportability_state,
                payload_json, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                legacy_set.alternative_set_id,
                legacy_set.portfolio_id,
                legacy_set.as_of,
                legacy_set.status.value,
                legacy_set.request_hash,
                "legacy-shared-key",
                legacy_set.input_mode,
                legacy_set.source_supportability_state,
                json.dumps(legacy_set.model_dump(mode="json", exclude={"tenant_id"})),
                legacy_set.generated_at.isoformat(),
            ),
        )
        admin.execute(
            """
            INSERT INTO dpm_construction_alternative_selections (
                selection_id, alternative_set_id, alternative_id, actor_id,
                reason_code, comment, correlation_id, payload_json, selected_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                legacy_selection.selection_id,
                legacy_selection.alternative_set_id,
                legacy_selection.alternative_id,
                legacy_selection.actor_id,
                legacy_selection.reason_code,
                None,
                None,
                json.dumps(legacy_selection.model_dump(mode="json", exclude={"tenant_id"})),
                legacy_selection.selected_at.isoformat(),
            ),
        )
        admin.commit()

        monkeypatch.setattr(
            postgres_migrations,
            "_load_migrations",
            lambda *, namespace: migrations,
        )
        postgres_migrations.apply_postgres_migrations(connection=admin, namespace="dpm")
        quarantined = admin.execute(
            """
            SELECT s.tenant_id AS set_tenant, d.tenant_id AS selection_tenant
            FROM dpm_construction_alternative_sets s
            JOIN dpm_construction_alternative_selections d
              ON d.alternative_set_id = s.alternative_set_id
            WHERE s.alternative_set_id = %s
            """,
            (legacy_set.alternative_set_id,),
        ).fetchone()
        assert quarantined == {"set_tenant": None, "selection_tenant": None}

        schema_dsn = make_conninfo(dsn, options=f"-csearch_path={schema}")
        monkeypatch.setenv("DPM_POSTGRES_MAX_CONNECTIONS", "1")
        monkeypatch.setenv("DPM_POSTGRES_COORDINATION_MAX_CONNECTIONS", "2")
        monkeypatch.setenv("DPM_POSTGRES_STATEMENT_TIMEOUT_MS", "100")
        monkeypatch.setenv("DPM_POSTGRES_COORDINATION_WAIT_TIMEOUT_MS", "3000")
        monkeypatch.setenv("DPM_POSTGRES_IDLE_IN_TRANSACTION_TIMEOUT_MS", "1000")

        def managed_schema_connect(*, application_name: str) -> Any:
            def connect_with_schema(_dsn: str, **kwargs: Any) -> Any:
                ordinary_options = kwargs.pop("options")
                return psycopg.connect(
                    dsn,
                    options=f"-csearch_path={schema} {ordinary_options}",
                    **kwargs,
                )

            return connect_postgres(
                dsn,
                connect_fn=connect_with_schema,
                row_factory=dict_row,
                application_name=application_name,
            )

        repository = PostgresConstructionRepository(dsn=schema_dsn)
        monkeypatch.setattr(
            repository,
            "_connect",
            lambda: managed_schema_connect(application_name="lotus-manage:test-construction-a"),
        )
        for tenant in ("tenant-a", "tenant-b"):
            assert (
                repository.get_alternative_set(
                    alternative_set_id=legacy_set.alternative_set_id,
                    tenant_id=tenant,
                )
                is None
            )
            assert (
                repository.get_selection(
                    alternative_set_id=legacy_set.alternative_set_id,
                    tenant_id=tenant,
                )
                is None
            )

        tenant_a = _set(
            set_id=f"cas_a_{uuid.uuid4().hex}",
            tenant_id="tenant-a",
            request_hash="sha256:tenant-a",
        )
        tenant_b = _set(
            set_id=f"cas_b_{uuid.uuid4().hex}",
            tenant_id="tenant-b",
            request_hash="sha256:tenant-b",
        )
        assert (
            repository.save_alternative_set(alternative_set=tenant_a, idempotency_key="shared-key")
            == tenant_a
        )
        assert (
            repository.save_alternative_set(alternative_set=tenant_b, idempotency_key="shared-key")
            == tenant_b
        )
        assert (
            repository.get_alternative_set(
                alternative_set_id=tenant_a.alternative_set_id,
                tenant_id="tenant-b",
            )
            is None
        )

        repository.save_selection(
            selection=_selection(set_id=tenant_a.alternative_set_id, tenant_id="tenant-a")
        )
        assert (
            repository.get_selection(
                alternative_set_id=tenant_a.alternative_set_id,
                tenant_id="tenant-b",
            )
            is None
        )
        with pytest.raises(
            ConstructionAlternativeSetNotFoundError,
            match="CONSTRUCTION_ALTERNATIVE_SET_NOT_FOUND",
        ):
            repository.save_selection(
                selection=_selection(set_id=tenant_a.alternative_set_id, tenant_id="tenant-b")
            )

        concurrent_key = f"concurrent-{uuid.uuid4().hex}"
        candidates = [
            _set(
                set_id=f"cas_concurrent_{index}_{uuid.uuid4().hex}",
                tenant_id="tenant-a",
                request_hash=f"sha256:concurrent-{index}",
            )
            for index in range(2)
        ]
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(
                executor.map(
                    lambda candidate: repository.save_alternative_set(
                        alternative_set=candidate,
                        idempotency_key=concurrent_key,
                    ),
                    candidates,
                )
            )
        assert len({row.alternative_set_id for row in results}) == 1
        with closing(repository._connect()) as connection:
            stored = connection.execute(
                """
                SELECT COUNT(*) AS count
                FROM dpm_construction_alternative_sets
                WHERE tenant_id = %s AND idempotency_key = %s
                """,
                ("tenant-a", concurrent_key),
            ).fetchone()
        assert stored["count"] == 1

        service_key = f"concurrent-service-{uuid.uuid4().hex}"
        service_tenant = f"tenant-service-{uuid.uuid4().hex[:12]}"
        service_portfolio = f"PF_CONSTRUCTION_SERVICE_{uuid.uuid4().hex[:12]}"
        request_payload = valid_api_payload()
        request_payload["portfolio_snapshot"]["portfolio_id"] = service_portfolio
        request = RebalanceRequest.model_validate(request_payload)
        second_repository = PostgresConstructionRepository(dsn=schema_dsn)
        monkeypatch.setattr(
            second_repository,
            "_connect",
            lambda: managed_schema_connect(application_name="lotus-manage:test-construction-b"),
        )
        run_repository = PostgresDpmRunRepository(dsn=schema_dsn)
        monkeypatch.setattr(
            run_repository,
            "_connect",
            lambda: managed_schema_connect(application_name="lotus-manage:test-runs"),
        )
        durable_run_service = DpmRunSupportService(repository=run_repository)

        class SlowRunService:
            def record_run(
                self,
                *,
                result,
                request_hash,
                portfolio_id,
                idempotency_key,
                tenant_id,
            ) -> None:
                durable_run_service.record_run(
                    result=result,
                    request_hash=request_hash,
                    portfolio_id=portfolio_id,
                    idempotency_key=idempotency_key,
                    tenant_id=tenant_id,
                )
                time.sleep(1.25)

        run_service = SlowRunService()

        def generate(candidate_repository: PostgresConstructionRepository):
            return construction_service.generate_construction_alternative_set(
                request=request,
                idempotency_key=service_key,
                correlation_id=None,
                repository=candidate_repository,
                methods=[ConstructionMethod.HEURISTIC_EXPLAINABLE],
                run_service=run_service,  # type: ignore[arg-type]
                admitted_tenant_id=service_tenant,
            )

        with ThreadPoolExecutor(max_workers=2) as executor:
            generated = list(executor.map(generate, (repository, second_repository)))
        assert len({row.alternative_set_id for row in generated}) == 1
        with closing(repository._connect()) as connection:
            run_count = connection.execute(
                """
                SELECT COUNT(*) AS count
                FROM dpm_runs
                WHERE tenant_id = %s AND portfolio_id = %s
                """,
                (service_tenant, service_portfolio),
            ).fetchone()
        assert run_count["count"] == 1

        restarted = PostgresConstructionRepository(dsn=schema_dsn)
        monkeypatch.setattr(
            restarted,
            "_connect",
            lambda: managed_schema_connect(
                application_name="lotus-manage:test-construction-restarted"
            ),
        )
        assert (
            restarted.get_alternative_set(
                alternative_set_id=tenant_a.alternative_set_id,
                tenant_id="tenant-a",
            )
            == tenant_a
        )
        assert (
            restarted.get_alternative_set(
                alternative_set_id=tenant_a.alternative_set_id,
                tenant_id="tenant-b",
            )
            is None
        )
    finally:
        admin.rollback()
        admin.execute("SET search_path TO public")
        admin.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
        admin.commit()
        admin.close()
