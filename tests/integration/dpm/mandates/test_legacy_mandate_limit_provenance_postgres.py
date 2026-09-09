"""Legacy mandate-limit provenance is fail-closed in PostgreSQL (#674)."""

from __future__ import annotations

import hashlib
import json
import uuid
from contextlib import closing
from datetime import date
from pathlib import Path

import psycopg
import pytest

from src.core.mandates import (
    MANDATE_LIMIT_PROVENANCE_AMBIGUOUS,
    DpmMandateConstraintSet,
    DpmMandateDigitalTwin,
    DpmMandateReviewPolicy,
)
from src.infrastructure.mandates.postgres import PostgresDpmMandateRepository
from src.infrastructure.postgres_migrations import _split_sql_statements
from tests.integration.dpm.postgres_prerequisite import postgres_dsn_or_skip

_PROOF = "legacy mandate limit provenance proof"
_MIGRATION = Path(
    "src/infrastructure/postgres_migrations/dpm/0030_mandate_snapshot_producer_provenance.sql"
)


@pytest.fixture
def repository() -> PostgresDpmMandateRepository:
    return PostgresDpmMandateRepository(dsn=postgres_dsn_or_skip(_PROOF))


def _payload(*, mandate_id: str, portfolio_id: str, minimum: str = "0.02") -> str:
    return json.dumps(
        {
            "mandate_id": mandate_id,
            "portfolio_id": portfolio_id,
            "mandate_version": "3",
            "as_of_date": "2026-05-03",
            "source_system": "lotus-core",
            "base_currency": "SGD",
            "reference_currency": "SGD",
            "risk_profile": "BALANCED",
            "investment_objective": "LONG_TERM_TOTAL_RETURN",
            "time_horizon": "LONG_TERM",
            "model_portfolio_id": "MODEL_LEGACY",
            "constraints": {
                "cash_band_min_weight": minimum,
                "cash_band_max_weight": "0.10",
                "turnover_budget": "0.15",
            },
            "review_policy": {"review_frequency": "QUARTERLY"},
            # A caller could submit this same lineage, so it is deliberately
            # not used as a producer discriminator.
            "source_lineage": [
                {
                    "product_name": "DiscretionaryMandateBinding",
                    "product_version": "v1",
                    "source_system": "lotus-core",
                }
            ],
            "field_gap_codes": ["UNRELATED_GAP"],
        },
        separators=(",", ":"),
        sort_keys=True,
    )


def _apply_migration(repository: PostgresDpmMandateRepository) -> None:
    with closing(repository._connect()) as connection:
        for statement in _split_sql_statements(_MIGRATION.read_text(encoding="utf-8")):
            if statement.strip():
                connection.execute(statement)
        connection.commit()


def _insert_snapshot(
    repository: PostgresDpmMandateRepository,
    *,
    mandate_id: str,
    portfolio_id: str,
    tenant_id: str | None,
    minimum: str = "0.02",
) -> str:
    payload = _payload(mandate_id=mandate_id, portfolio_id=portfolio_id, minimum=minimum)
    with closing(repository._connect()) as connection:
        connection.execute(
            """
            INSERT INTO dpm_mandate_snapshots (
                mandate_snapshot_id, mandate_id, portfolio_id, mandate_version,
                as_of_date, source_hash, source_lineage_json, payload_json,
                created_at, created_by, tenant_id, producer_kind
            ) VALUES (%s, %s, %s, '3', '2026-05-03', %s, '[]', %s,
                      '2026-05-03T01:00:00+00:00', 'lotus-manage', %s, 'UNKNOWN_LEGACY')
            """,
            (
                f"ms_{uuid.uuid4().hex}",
                mandate_id,
                portfolio_id,
                "sha256:" + hashlib.sha256(payload.encode()).hexdigest(),
                payload,
                tenant_id,
            ),
        )
        connection.commit()
    return payload


def _cleanup(repository: PostgresDpmMandateRepository, mandate_id: str, run_id: str) -> None:
    with closing(repository._connect()) as connection:
        connection.execute(
            "DELETE FROM dpm_monitoring_exceptions WHERE mandate_id = %s", (mandate_id,)
        )
        connection.execute(
            "DELETE FROM dpm_mandate_health_snapshots WHERE mandate_id = %s", (mandate_id,)
        )
        connection.execute("DELETE FROM dpm_mandate_snapshots WHERE mandate_id = %s", (mandate_id,))
        connection.execute(
            "DELETE FROM dpm_monitoring_runs WHERE monitoring_run_id = %s", (run_id,)
        )
        connection.commit()


def test_unknown_legacy_limits_are_preserved_but_never_act_as_contractual_limits(
    repository: PostgresDpmMandateRepository,
) -> None:
    mandate_id = f"MANDATE_PROV_{uuid.uuid4().hex[:10]}"
    portfolio_id = f"PF_PROV_{uuid.uuid4().hex[:10]}"
    tenant_id = "tenant-provenance"
    other_tenant_id = "tenant-unrelated"
    run_id = f"dmr_{uuid.uuid4().hex}"
    earlier_run_id = f"dmr_{uuid.uuid4().hex}"
    failed_run_id = f"dmr_{uuid.uuid4().hex}"
    original_payload = _insert_snapshot(
        repository,
        mandate_id=mandate_id,
        portfolio_id=portfolio_id,
        tenant_id=tenant_id,
    )
    run_payload = {
        "monitoring_run_id": run_id,
        "tenant_id": tenant_id,
        "as_of_date": "2026-05-03",
        "requested_at": "2026-05-03T01:00:00Z",
        "completed_at": "2026-05-03T01:00:01Z",
        "status": "SUCCEEDED",
        "mandate_ids": [mandate_id],
        "filters": {"tenant_id": tenant_id},
        "total_mandates": 1,
        "health_distribution": {"READY": 1},
        "exception_count": 2,
        "source_readiness_summary": {"READY": 1},
    }
    try:
        with closing(repository._connect()) as connection:
            connection.execute(
                """
                INSERT INTO dpm_mandate_health_snapshots (
                    health_snapshot_id, mandate_id, portfolio_id, as_of_date,
                    health_score, health_state, source_readiness_state,
                    dimension_scores_json, payload_json, created_at, tenant_id
                ) VALUES (%s, %s, %s, '2026-05-03', 100, 'READY', 'READY',
                          '[]', '{}', '2026-05-03T01:00:01Z', %s)
                """,
                (f"mh_{uuid.uuid4().hex}", mandate_id, portfolio_id, tenant_id),
            )
            connection.execute(
                """
                INSERT INTO dpm_mandate_health_snapshots (
                    health_snapshot_id, mandate_id, portfolio_id, as_of_date,
                    health_score, health_state, source_readiness_state,
                    dimension_scores_json, payload_json, created_at, tenant_id
                ) VALUES (%s, %s, %s, '2026-05-02', 100, 'READY', 'READY',
                          '[]', '{}', '2026-05-03T02:00:01Z', %s)
                """,
                (f"mh_{uuid.uuid4().hex}", mandate_id, portfolio_id, tenant_id),
            )
            connection.execute(
                """
                INSERT INTO dpm_mandate_health_snapshots (
                    health_snapshot_id, mandate_id, portfolio_id, as_of_date,
                    health_score, health_state, source_readiness_state,
                    dimension_scores_json, payload_json, created_at, tenant_id
                ) VALUES (%s, %s, %s, '2026-05-03', 100, 'READY', 'READY',
                          '[]', '{}', '2026-05-03T01:00:01Z', %s)
                """,
                (f"mh_{uuid.uuid4().hex}", mandate_id, portfolio_id, other_tenant_id),
            )
            for dimension, reason in (
                ("CASH_LIQUIDITY", "CASH_ABOVE_BAND"),
                ("CASH_LIQUIDITY", "PROJECTED_CASHFLOW_PRESSURE"),
                ("TAX_TURNOVER", "TAX_LOTS_INCOMPLETE"),
                ("ELIGIBILITY_RESTRICTIONS", "RESTRICTED_INSTRUMENT_HELD"),
            ):
                connection.execute(
                    """
                    INSERT INTO dpm_monitoring_exceptions (
                        exception_id, monitoring_run_id, mandate_id, portfolio_id,
                        as_of_date, dimension, severity, reason_code, state,
                        recommended_action, source_lineage_json, payload_json,
                        detected_at, tenant_id
                    ) VALUES (%s, %s, %s, %s, '2026-05-03', %s, 'WARNING', %s,
                              'ACTIVE', 'REVIEW_MANDATE', '[]', '{}',
                              '2026-05-03T01:00:01Z', %s)
                    """,
                    (
                        f"me_{uuid.uuid4().hex}",
                        run_id,
                        mandate_id,
                        portfolio_id,
                        dimension,
                        reason,
                        tenant_id,
                    ),
                )
            connection.execute(
                """
                INSERT INTO dpm_monitoring_exceptions (
                    exception_id, monitoring_run_id, mandate_id, portfolio_id,
                    as_of_date, dimension, severity, reason_code, state,
                    recommended_action, source_lineage_json, payload_json,
                    detected_at, tenant_id
                ) VALUES (%s, %s, %s, %s, '2026-05-03', 'CASH_LIQUIDITY',
                          'WARNING', 'CASH_ABOVE_BAND', 'ACTIVE', 'REVIEW_MANDATE',
                          '[]', '{}', '2026-05-03T01:00:01Z', %s)
                """,
                (
                    f"me_{uuid.uuid4().hex}",
                    f"other_{run_id}",
                    mandate_id,
                    portfolio_id,
                    other_tenant_id,
                ),
            )
            connection.execute(
                """
                INSERT INTO dpm_monitoring_exceptions (
                    exception_id, monitoring_run_id, mandate_id, portfolio_id,
                    as_of_date, dimension, severity, reason_code, state,
                    recommended_action, source_lineage_json, payload_json,
                    detected_at, tenant_id
                ) VALUES (%s, %s, %s, %s, '2026-05-02', 'CASH_LIQUIDITY',
                          'WARNING', 'CASH_ABOVE_BAND', 'ACTIVE', 'REVIEW_MANDATE',
                          '[]', '{}', '2026-05-03T02:00:01Z', %s)
                """,
                (
                    f"me_{uuid.uuid4().hex}",
                    earlier_run_id,
                    mandate_id,
                    portfolio_id,
                    tenant_id,
                ),
            )
            connection.execute(
                """
                INSERT INTO dpm_monitoring_runs (
                    monitoring_run_id, as_of_date, status, tenant_id, filters_json,
                    source_readiness_summary_json, started_at, completed_at, payload_json
                ) VALUES (%s, '2026-05-03', 'SUCCEEDED', %s, %s, %s,
                          '2026-05-03T00:59:00Z', '2026-05-03T01:00:01Z', %s)
                """,
                (
                    run_id,
                    tenant_id,
                    json.dumps(run_payload["filters"]),
                    '{"READY":1}',
                    json.dumps(run_payload),
                ),
            )
            earlier_payload = {
                **run_payload,
                "monitoring_run_id": earlier_run_id,
                "as_of_date": "2026-05-02",
            }
            connection.execute(
                """
                INSERT INTO dpm_monitoring_runs (
                    monitoring_run_id, as_of_date, status, tenant_id, filters_json,
                    source_readiness_summary_json, started_at, completed_at, payload_json
                ) VALUES (%s, '2026-05-02', 'SUCCEEDED', %s, %s, %s,
                          '2026-05-03T02:00:00Z', '2026-05-03T02:00:01Z', %s)
                """,
                (
                    earlier_run_id,
                    tenant_id,
                    json.dumps(run_payload["filters"]),
                    '{"READY":1}',
                    json.dumps(earlier_payload),
                ),
            )
            failed_payload = {
                **run_payload,
                "monitoring_run_id": failed_run_id,
                "status": "FAILED",
                "failure_reason": "UPSTREAM_TIMEOUT",
            }
            connection.execute(
                """
                INSERT INTO dpm_monitoring_runs (
                    monitoring_run_id, as_of_date, status, failure_reason, tenant_id,
                    filters_json, source_readiness_summary_json, started_at,
                    completed_at, payload_json
                ) VALUES (%s, '2026-05-03', 'FAILED', 'UPSTREAM_TIMEOUT', %s, %s, %s,
                          '2026-05-03T01:00:00Z', '2026-05-03T01:00:01Z', %s)
                """,
                (
                    failed_run_id,
                    tenant_id,
                    json.dumps(run_payload["filters"]),
                    '{"READY":1}',
                    json.dumps(failed_payload),
                ),
            )
            clean_payload = json.loads(_payload(mandate_id=mandate_id, portfolio_id=portfolio_id))
            clean_payload["mandate_version"] = "4"
            clean_payload["as_of_date"] = "2026-05-04"
            clean_payload["constraints"] = {
                "cash_band_min_weight": None,
                "cash_band_max_weight": None,
                "turnover_budget": None,
            }
            clean_payload_json = json.dumps(clean_payload, separators=(",", ":"), sort_keys=True)
            connection.execute(
                """
                INSERT INTO dpm_mandate_snapshots (
                    mandate_snapshot_id, mandate_id, portfolio_id, mandate_version,
                    as_of_date, source_hash, source_lineage_json, payload_json,
                    created_at, created_by, tenant_id, producer_kind
                ) VALUES (%s, %s, %s, '4', '2026-05-04', %s, '[]', %s,
                          '2026-05-03T00:30:00Z', 'lotus-manage', %s, 'UNKNOWN_LEGACY')
                """,
                (
                    f"ms_{uuid.uuid4().hex}",
                    mandate_id,
                    portfolio_id,
                    "sha256:" + hashlib.sha256(clean_payload_json.encode()).hexdigest(),
                    clean_payload_json,
                    tenant_id,
                ),
            )
            # Historical upserts refreshed this timestamp after the derived
            # evidence had already been stamped, so time cannot recover the
            # snapshot/evidence relationship.
            connection.execute(
                """UPDATE dpm_mandate_snapshots
                   SET created_at = '2026-05-05T01:00:00Z'
                   WHERE mandate_id = %s AND mandate_version = '3'""",
                (mandate_id,),
            )
            connection.commit()

        _apply_migration(repository)
        _apply_migration(repository)  # replay is harmless and does not duplicate the marker

        with closing(repository._connect()) as connection:
            row = connection.execute(
                """SELECT payload_json, source_hash, producer_kind
                   FROM dpm_mandate_snapshots
                   WHERE mandate_id = %s AND mandate_version = '3'""",
                (mandate_id,),
            ).fetchone()
            clean_row = connection.execute(
                """SELECT payload_json FROM dpm_mandate_snapshots
                   WHERE mandate_id = %s AND mandate_version = '4'""",
                (mandate_id,),
            ).fetchone()
            health_count = connection.execute(
                """SELECT count(*) AS count FROM dpm_mandate_health_snapshots
                   WHERE mandate_id = %s AND tenant_id = %s""",
                (mandate_id, tenant_id),
            ).fetchone()["count"]
            exceptions = connection.execute(
                """SELECT as_of_date, dimension, reason_code FROM dpm_monitoring_exceptions
                   WHERE mandate_id = %s AND tenant_id = %s""",
                (mandate_id, tenant_id),
            ).fetchall()
            other_health_count = connection.execute(
                """SELECT count(*) AS count FROM dpm_mandate_health_snapshots
                   WHERE mandate_id = %s AND tenant_id = %s""",
                (mandate_id, other_tenant_id),
            ).fetchone()["count"]
            other_exception_count = connection.execute(
                """SELECT count(*) AS count FROM dpm_monitoring_exceptions
                   WHERE mandate_id = %s AND tenant_id = %s""",
                (mandate_id, other_tenant_id),
            ).fetchone()["count"]

        stored = (
            row["payload_json"]
            if isinstance(row["payload_json"], str)
            else json.dumps(row["payload_json"], separators=(",", ":"), sort_keys=True)
        )
        stored_payload = json.loads(stored)
        original_constraints = json.loads(original_payload)["constraints"]
        assert stored_payload["constraints"] == original_constraints
        assert "cash_reserve_weight" not in stored_payload["constraints"]
        assert stored_payload["field_gap_codes"].count(MANDATE_LIMIT_PROVENANCE_AMBIGUOUS) == 1
        assert stored_payload["field_gap_codes"].count("UNRELATED_GAP") == 1
        assert row["producer_kind"] == "UNKNOWN_LEGACY"
        assert row["source_hash"] == "sha256:" + hashlib.sha256(stored.encode()).hexdigest()
        assert clean_row is not None
        assert (
            MANDATE_LIMIT_PROVENANCE_AMBIGUOUS
            not in json.loads(clean_row["payload_json"])["field_gap_codes"]
        )

        effective = repository.get_latest_mandate(mandate_id=mandate_id, tenant_id=tenant_id)
        assert effective is not None
        assert effective.constraints.cash_band_min_weight is None
        assert effective.constraints.cash_band_max_weight is None
        assert effective.constraints.turnover_budget is None
        assert effective.constraints.cash_reserve_weight is None
        assert health_count == 0
        assert {
            (item["as_of_date"], item["dimension"], item["reason_code"]) for item in exceptions
        } == {
            ("2026-05-03", "CASH_LIQUIDITY", "PROJECTED_CASHFLOW_PRESSURE"),
            ("2026-05-03", "TAX_TURNOVER", "TAX_LOTS_INCOMPLETE"),
            ("2026-05-03", "ELIGIBILITY_RESTRICTIONS", "RESTRICTED_INSTRUMENT_HELD"),
        }
        assert other_health_count == 1
        assert other_exception_count == 1

        run = repository.get_monitoring_run(monitoring_run_id=run_id, tenant_id=tenant_id)
        assert run is not None
        assert run.status == "FAILED"
        assert run.failure_reason == MANDATE_LIMIT_PROVENANCE_AMBIGUOUS
        assert run.total_mandates == 0
        assert run.health_distribution == {}
        assert run.exception_count == 0

        earlier_run = repository.get_monitoring_run(
            monitoring_run_id=earlier_run_id, tenant_id=tenant_id
        )
        assert earlier_run is not None
        assert earlier_run.status == "FAILED"
        assert earlier_run.failure_reason == MANDATE_LIMIT_PROVENANCE_AMBIGUOUS
        assert earlier_run.total_mandates == 0
        assert earlier_run.health_distribution == {}
        assert earlier_run.exception_count == 0

        failed_run = repository.get_monitoring_run(
            monitoring_run_id=failed_run_id, tenant_id=tenant_id
        )
        assert failed_run is not None
        assert failed_run.status == "FAILED"
        assert failed_run.failure_reason == "UPSTREAM_TIMEOUT"
        assert failed_run.total_mandates == 1
        assert failed_run.health_distribution == {"READY": 1}
        assert failed_run.exception_count == 2
    finally:
        _cleanup(repository, mandate_id, run_id)
        with closing(repository._connect()) as connection:
            connection.execute(
                "DELETE FROM dpm_monitoring_runs WHERE monitoring_run_id = ANY(%s)",
                ([failed_run_id, earlier_run_id],),
            )
            connection.commit()


def test_future_repository_writes_record_their_actual_producer(
    repository: PostgresDpmMandateRepository,
) -> None:
    tenant_id = "tenant-producer"
    mandate_ids = [f"MANDATE_PRODUCER_{uuid.uuid4().hex[:10]}" for _ in range(2)]
    run_id = f"unused_{uuid.uuid4().hex}"
    try:
        for mandate_id, producer in zip(
            mandate_ids, ("CALLER_SUPPLIED", "CORE_COMPILED"), strict=True
        ):
            twin = DpmMandateDigitalTwin(
                mandate_id=mandate_id,
                portfolio_id=f"PF_{mandate_id}",
                mandate_version="1",
                as_of_date=date(2026, 9, 9),
                base_currency="SGD",
                reference_currency="SGD",
                risk_profile="BALANCED",
                investment_objective="LONG_TERM_TOTAL_RETURN",
                time_horizon="LONG_TERM",
                model_portfolio_id="MODEL_PRODUCER",
                constraints=DpmMandateConstraintSet(),
                review_policy=DpmMandateReviewPolicy(),
            )
            repository.save_mandate_snapshot(
                twin,
                tenant_id=tenant_id,
                producer_kind=producer,  # type: ignore[arg-type]
            )

        with closing(repository._connect()) as connection:
            rows = connection.execute(
                """SELECT mandate_id, producer_kind FROM dpm_mandate_snapshots
                   WHERE mandate_id = ANY(%s) ORDER BY producer_kind""",
                (mandate_ids,),
            ).fetchall()
        assert {(row["mandate_id"], row["producer_kind"]) for row in rows} == {
            (mandate_ids[0], "CALLER_SUPPLIED"),
            (mandate_ids[1], "CORE_COMPILED"),
        }
    finally:
        for mandate_id in mandate_ids:
            _cleanup(repository, mandate_id, run_id)


def test_post_migration_legacy_upsert_without_producer_is_rejected(
    repository: PostgresDpmMandateRepository,
) -> None:
    mandate_id = f"MANDATE_OLD_REPLICA_{uuid.uuid4().hex[:10]}"
    portfolio_id = f"PF_OLD_REPLICA_{uuid.uuid4().hex[:10]}"
    tenant_id = "tenant-old-replica"
    run_id = f"unused_{uuid.uuid4().hex}"
    original_payload = _insert_snapshot(
        repository,
        mandate_id=mandate_id,
        portfolio_id=portfolio_id,
        tenant_id=tenant_id,
    )
    try:
        _apply_migration(repository)
        legacy_payload = _payload(mandate_id=mandate_id, portfolio_id=portfolio_id)
        with closing(repository._connect()) as connection:
            with pytest.raises(psycopg.errors.NotNullViolation):
                connection.execute(
                    """
                    INSERT INTO dpm_mandate_snapshots (
                        mandate_snapshot_id, mandate_id, portfolio_id, mandate_version,
                        as_of_date, source_hash, source_lineage_json, payload_json,
                        created_at, created_by, tenant_id
                    ) VALUES (%s, %s, %s, '3', '2026-05-03', %s, '[]', %s,
                              '2026-05-03T02:00:00+00:00', 'old-lotus-manage', %s)
                    ON CONFLICT (tenant_id, mandate_id, mandate_version, as_of_date)
                    DO UPDATE SET payload_json = excluded.payload_json,
                                  source_hash = excluded.source_hash
                    """,
                    (
                        f"ms_{uuid.uuid4().hex}",
                        mandate_id,
                        portfolio_id,
                        "sha256:" + hashlib.sha256(legacy_payload.encode()).hexdigest(),
                        legacy_payload,
                        tenant_id,
                    ),
                )
            connection.rollback()

            row = connection.execute(
                """SELECT payload_json, producer_kind
                   FROM dpm_mandate_snapshots WHERE mandate_id = %s""",
                (mandate_id,),
            ).fetchone()
            column_default = connection.execute(
                """SELECT column_default FROM information_schema.columns
                   WHERE table_schema = current_schema()
                     AND table_name = 'dpm_mandate_snapshots'
                     AND column_name = 'producer_kind'"""
            ).fetchone()["column_default"]

        assert row is not None
        assert row["producer_kind"] == "UNKNOWN_LEGACY"
        assert (
            MANDATE_LIMIT_PROVENANCE_AMBIGUOUS in json.loads(row["payload_json"])["field_gap_codes"]
        )
        assert (
            json.loads(row["payload_json"])["constraints"]
            == json.loads(original_payload)["constraints"]
        )
        assert column_default is None
    finally:
        _cleanup(repository, mandate_id, run_id)


def test_migration_preserves_quarantined_null_tenant_evidence(
    repository: PostgresDpmMandateRepository,
) -> None:
    mandate_id = f"MANDATE_QUARANTINED_{uuid.uuid4().hex[:10]}"
    portfolio_id = f"PF_QUARANTINED_{uuid.uuid4().hex[:10]}"
    run_id = f"dmr_{uuid.uuid4().hex}"
    _insert_snapshot(
        repository,
        mandate_id=mandate_id,
        portfolio_id=portfolio_id,
        tenant_id=None,
    )
    run_payload = {
        "monitoring_run_id": run_id,
        "as_of_date": "2026-05-03",
        "requested_at": "2026-05-03T01:00:00Z",
        "completed_at": "2026-05-03T01:00:01Z",
        "status": "SUCCEEDED",
        "mandate_ids": [mandate_id],
        "filters": {},
        "total_mandates": 1,
        "health_distribution": {"READY": 1},
        "exception_count": 1,
        "source_readiness_summary": {"READY": 1},
    }
    try:
        with closing(repository._connect()) as connection:
            connection.execute(
                """
                INSERT INTO dpm_mandate_health_snapshots (
                    health_snapshot_id, mandate_id, portfolio_id, as_of_date,
                    health_score, health_state, source_readiness_state,
                    dimension_scores_json, payload_json, created_at, tenant_id
                ) VALUES (%s, %s, %s, '2026-05-03', 100, 'READY', 'READY',
                          '[]', '{}', '2026-05-03T01:00:01Z', NULL)
                """,
                (f"mh_{uuid.uuid4().hex}", mandate_id, portfolio_id),
            )
            connection.execute(
                """
                INSERT INTO dpm_monitoring_exceptions (
                    exception_id, monitoring_run_id, mandate_id, portfolio_id,
                    as_of_date, dimension, severity, reason_code, state,
                    recommended_action, source_lineage_json, payload_json,
                    detected_at, tenant_id
                ) VALUES (%s, %s, %s, %s, '2026-05-03', 'CASH_LIQUIDITY',
                          'WARNING', 'CASH_ABOVE_BAND', 'ACTIVE', 'REVIEW_MANDATE',
                          '[]', '{}', '2026-05-03T01:00:01Z', NULL)
                """,
                (f"me_{uuid.uuid4().hex}", run_id, mandate_id, portfolio_id),
            )
            connection.execute(
                """
                INSERT INTO dpm_monitoring_runs (
                    monitoring_run_id, as_of_date, status, tenant_id, filters_json,
                    source_readiness_summary_json, started_at, completed_at, payload_json
                ) VALUES (%s, '2026-05-03', 'SUCCEEDED', NULL, '{}', '{"READY":1}',
                          '2026-05-03T01:00:00Z', '2026-05-03T01:00:01Z', %s)
                """,
                (run_id, json.dumps(run_payload)),
            )
            connection.commit()

        _apply_migration(repository)

        with closing(repository._connect()) as connection:
            snapshot = connection.execute(
                """SELECT payload_json FROM dpm_mandate_snapshots
                   WHERE mandate_id = %s AND tenant_id IS NULL""",
                (mandate_id,),
            ).fetchone()
            run = connection.execute(
                """SELECT status, failure_reason FROM dpm_monitoring_runs
                   WHERE monitoring_run_id = %s AND tenant_id IS NULL""",
                (run_id,),
            ).fetchone()
            health_count = connection.execute(
                """SELECT count(*) AS count FROM dpm_mandate_health_snapshots
                   WHERE mandate_id = %s AND tenant_id IS NULL""",
                (mandate_id,),
            ).fetchone()["count"]
            exception_count = connection.execute(
                """SELECT count(*) AS count FROM dpm_monitoring_exceptions
                   WHERE mandate_id = %s AND tenant_id IS NULL""",
                (mandate_id,),
            ).fetchone()["count"]

        assert snapshot is not None
        snapshot_payload = json.loads(snapshot["payload_json"])
        assert MANDATE_LIMIT_PROVENANCE_AMBIGUOUS in snapshot_payload["field_gap_codes"]
        assert run == {"status": "SUCCEEDED", "failure_reason": None}
        assert health_count == 1
        assert exception_count == 1
    finally:
        _cleanup(repository, mandate_id, run_id)
