"""Operator quarantine inventory proof against PostgreSQL (#699)."""

from __future__ import annotations

import hashlib
import uuid
from contextlib import closing

import psycopg
from psycopg.rows import dict_row

from src.infrastructure.mandates.postgres import PostgresDpmMandateRepository
from src.infrastructure.proof_packs.postgres import PostgresDpmProofPackRepository
from src.infrastructure.quarantined_tenant_inventory import (
    QUARANTINED_TENANT_DATASETS,
    build_quarantined_tenant_inventory,
)
from src.infrastructure.waves.postgres import PostgresDpmWaveRepository

from tests.integration.dpm.postgres_prerequisite import postgres_dsn_or_skip

_PROOF = "quarantined tenant inventory proof"
_TENANT = "tenant-inventory-proof"


def test_inventory_reports_every_quarantine_without_making_it_tenant_readable() -> None:
    dsn = postgres_dsn_or_skip(_PROOF)
    suffix = uuid.uuid4().hex[:12]
    ids = {
        "mandate_snapshot_id": f"aaa_inventory_ms_{suffix}",
        "health_snapshot_id": f"aaa_inventory_hs_{suffix}",
        "exception_id": f"aaa_inventory_ex_{suffix}",
        "idempotency_key": f"aaa-inventory-idem-{suffix}",
        "wave_id": f"aaa_inventory_wave_{suffix}",
        "proof_pack_id": f"aaa_inventory_pp_{suffix}",
        "monitoring_run_id": f"aaa_inventory_run_{suffix}",
        "mandate_id": f"MANDATE_INVENTORY_{suffix}",
        "portfolio_id": f"PF_INVENTORY_{suffix}",
    }

    _insert_quarantined_rows(dsn=dsn, ids=ids)
    try:
        before = _row_counts(dsn=dsn, ids=ids)
        with closing(psycopg.connect(dsn, row_factory=dict_row)) as connection:
            inventory = build_quarantined_tenant_inventory(connection=connection, limit=100)
        after = _row_counts(dsn=dsn, ids=ids)

        assert inventory["status"] == "success"
        assert inventory["readOnly"] is True
        assert before == after == {dataset.name: 1 for dataset in QUARANTINED_TENANT_DATASETS}

        with psycopg.connect(dsn, row_factory=dict_row) as connection:
            index_row = connection.execute(
                """
                SELECT indexdef
                FROM pg_indexes
                WHERE schemaname = current_schema()
                  AND indexname = 'idx_dpm_monitoring_runs_null_tenant_inventory'
                """
            ).fetchone()
        assert index_row is not None
        assert "WHERE (tenant_id IS NULL)" in index_row["indexdef"]

        by_name = {item["dataset"]: item for item in inventory["datasets"]}
        assert set(by_name) == {dataset.name for dataset in QUARANTINED_TENANT_DATASETS}
        assert all(item["totalCount"] >= 1 for item in by_name.values())
        assert all(item["migration"]["checksum"] for item in by_name.values())

        expected_identifiers = {
            "dpm_mandate_snapshots": ("mandate_snapshot_id", ids["mandate_snapshot_id"]),
            "dpm_mandate_health_snapshots": (
                "health_snapshot_id",
                ids["health_snapshot_id"],
            ),
            "dpm_monitoring_exceptions": ("exception_id", ids["exception_id"]),
            "dpm_rebalance_waves": ("wave_id", ids["wave_id"]),
            "dpm_pre_trade_proof_packs": ("proof_pack_id", ids["proof_pack_id"]),
            "dpm_monitoring_runs": ("monitoring_run_id", ids["monitoring_run_id"]),
        }
        for dataset, (column, value) in expected_identifiers.items():
            assert any(row[column] == value for row in by_name[dataset]["rows"])
        expected_key_hash = hashlib.sha256(ids["idempotency_key"].encode()).hexdigest()
        assert any(
            row["idempotency_keySha256"] == expected_key_hash
            for row in by_name["dpm_rebalance_wave_idempotency"]["rows"]
        )

        mandate_repository = PostgresDpmMandateRepository(dsn=dsn)
        wave_repository = PostgresDpmWaveRepository(dsn=dsn)
        proof_pack_repository = PostgresDpmProofPackRepository(dsn=dsn)
        assert (
            mandate_repository.get_latest_mandate(mandate_id=ids["mandate_id"], tenant_id=_TENANT)
            is None
        )
        assert (
            mandate_repository.get_monitoring_run(
                monitoring_run_id=ids["monitoring_run_id"], tenant_id=_TENANT
            )
            is None
        )
        exceptions, _ = mandate_repository.list_monitoring_exceptions(
            monitoring_run_id=ids["monitoring_run_id"],
            mandate_id=None,
            portfolio_id=None,
            state=None,
            limit=50,
            cursor=None,
            tenant_id=_TENANT,
        )
        assert exceptions == []
        assert wave_repository.get_wave(wave_id=ids["wave_id"], tenant_id=_TENANT) is None
        assert (
            wave_repository.get_wave_by_idempotency(
                idempotency_key=ids["idempotency_key"], tenant_id=_TENANT
            )
            is None
        )
        assert (
            proof_pack_repository.get_proof_pack(
                proof_pack_id=ids["proof_pack_id"], tenant_id=_TENANT
            )
            is None
        )
    finally:
        _delete_quarantined_rows(dsn=dsn, ids=ids)


def _insert_quarantined_rows(*, dsn: str, ids: dict[str, str]) -> None:
    with psycopg.connect(dsn, row_factory=dict_row) as connection:
        connection.execute(
            """
            INSERT INTO dpm_mandate_snapshots (
                mandate_snapshot_id, mandate_id, portfolio_id, mandate_version, as_of_date,
                source_hash, source_lineage_json, payload_json, created_at, created_by
            ) VALUES (%s, %s, %s, '1', '2026-09-09', 'sha256:inventory', '[]', '{}',
                      '2026-09-09T00:00:00+00:00', 'inventory-proof')
            """,
            (
                ids["mandate_snapshot_id"],
                ids["mandate_id"],
                ids["portfolio_id"],
            ),
        )
        connection.execute(
            """
            INSERT INTO dpm_mandate_health_snapshots (
                health_snapshot_id, mandate_id, portfolio_id, as_of_date, health_score,
                health_state, source_readiness_state, dimension_scores_json, payload_json,
                created_at
            ) VALUES (%s, %s, %s, '2026-09-09', 50, 'REVIEW', 'COMPLETE', '[]', '{}',
                      '2026-09-09T00:00:00+00:00')
            """,
            (ids["health_snapshot_id"], ids["mandate_id"], ids["portfolio_id"]),
        )
        connection.execute(
            """
            INSERT INTO dpm_monitoring_runs (
                monitoring_run_id, as_of_date, status, filters_json,
                source_readiness_summary_json, started_at
            ) VALUES (%s, '2026-09-09', 'SUCCEEDED', '{}', '{}',
                      '2026-09-09T00:00:00+00:00')
            """,
            (ids["monitoring_run_id"],),
        )
        connection.execute(
            """
            INSERT INTO dpm_monitoring_exceptions (
                exception_id, monitoring_run_id, mandate_id, portfolio_id, as_of_date,
                dimension, severity, reason_code, state, recommended_action,
                source_lineage_json, payload_json, detected_at
            ) VALUES (%s, %s, %s, %s, '2026-09-09', 'RISK', 'MEDIUM', 'INVENTORY',
                      'OPEN', 'Review attribution', '[]', '{}',
                      '2026-09-09T00:00:00+00:00')
            """,
            (
                ids["exception_id"],
                ids["monitoring_run_id"],
                ids["mandate_id"],
                ids["portfolio_id"],
            ),
        )
        connection.execute(
            """
            INSERT INTO dpm_rebalance_waves (
                wave_id, state, trigger_type, as_of_date, created_at, created_by,
                correlation_id, version, wave_json, retention_policy
            ) VALUES (%s, 'CREATED', 'EXPLICIT_PORTFOLIO_LIST', '2026-09-09',
                      '2026-09-09T00:00:00+00:00', 'inventory-proof', %s, 1, '{}', 'STANDARD')
            """,
            (ids["wave_id"], f"corr-{ids['wave_id']}"),
        )
        connection.execute(
            """
            INSERT INTO dpm_rebalance_wave_idempotency (
                idempotency_key, wave_id, request_hash, created_at
            ) VALUES (%s, %s, 'inventory-hash', '2026-09-09T00:00:00+00:00')
            """,
            (ids["idempotency_key"], ids["wave_id"]),
        )
        connection.execute(
            """
            INSERT INTO dpm_pre_trade_proof_packs (
                proof_pack_id, portfolio_id, mandate_id, source_type, status, content_hash,
                retention_policy, payload_json, created_at
            ) VALUES (%s, %s, %s, 'OPERATOR', 'READY', 'inventory-hash', 'STANDARD', '{}',
                      '2026-09-09T00:00:00+00:00')
            """,
            (ids["proof_pack_id"], ids["portfolio_id"], ids["mandate_id"]),
        )
        connection.commit()


def _row_counts(*, dsn: str, ids: dict[str, str]) -> dict[str, int]:
    predicates = {
        "dpm_mandate_snapshots": ("mandate_snapshot_id", ids["mandate_snapshot_id"]),
        "dpm_mandate_health_snapshots": ("health_snapshot_id", ids["health_snapshot_id"]),
        "dpm_monitoring_exceptions": ("exception_id", ids["exception_id"]),
        "dpm_rebalance_wave_idempotency": ("idempotency_key", ids["idempotency_key"]),
        "dpm_rebalance_waves": ("wave_id", ids["wave_id"]),
        "dpm_pre_trade_proof_packs": ("proof_pack_id", ids["proof_pack_id"]),
        "dpm_monitoring_runs": ("monitoring_run_id", ids["monitoring_run_id"]),
    }
    with psycopg.connect(dsn, row_factory=dict_row) as connection:
        return {
            table: connection.execute(
                f"SELECT COUNT(*) AS count FROM {table} WHERE {column} = %s AND tenant_id IS NULL",
                (value,),
            ).fetchone()["count"]
            for table, (column, value) in predicates.items()
        }


def _delete_quarantined_rows(*, dsn: str, ids: dict[str, str]) -> None:
    with psycopg.connect(dsn) as connection:
        connection.execute(
            "DELETE FROM dpm_monitoring_exceptions WHERE exception_id = %s",
            (ids["exception_id"],),
        )
        connection.execute(
            "DELETE FROM dpm_monitoring_runs WHERE monitoring_run_id = %s",
            (ids["monitoring_run_id"],),
        )
        connection.execute(
            "DELETE FROM dpm_mandate_health_snapshots WHERE health_snapshot_id = %s",
            (ids["health_snapshot_id"],),
        )
        connection.execute(
            "DELETE FROM dpm_mandate_snapshots WHERE mandate_snapshot_id = %s",
            (ids["mandate_snapshot_id"],),
        )
        connection.execute(
            "DELETE FROM dpm_pre_trade_proof_packs WHERE proof_pack_id = %s",
            (ids["proof_pack_id"],),
        )
        connection.execute("DELETE FROM dpm_rebalance_waves WHERE wave_id = %s", (ids["wave_id"],))
        connection.commit()
