from __future__ import annotations

import json
from contextlib import closing
from typing import Any

from src.core.common.capabilities import has_psycopg
from src.core.pm_quality.models import DpmPmOperatingQualityScoreRun
from src.core.pm_quality.repository import DpmPmQualityScoreRunConflictError
from src.infrastructure.mandates.serialization import dump_model_json, load_model_json
from src.infrastructure.postgres_migrations import apply_postgres_migrations


class PostgresDpmPmQualityScoreRunRepository:
    def __init__(self, *, dsn: str) -> None:
        if not dsn:
            raise RuntimeError("DPM_PM_QUALITY_POSTGRES_DSN_REQUIRED")
        if not has_psycopg():
            raise RuntimeError("DPM_PM_QUALITY_POSTGRES_DRIVER_MISSING")
        self._dsn = dsn
        self._init_db()

    def save_score_run(self, *, score_run: DpmPmOperatingQualityScoreRun) -> None:
        with closing(self._connect()) as connection:
            connection.execute(
                """
                INSERT INTO dpm_pm_quality_score_runs (
                    score_run_id, pm_id, book_id, policy_id, policy_version, as_of_date,
                    state, score, content_hash, generated_at, generated_by, correlation_id,
                    payload_json
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (score_run_id) DO NOTHING
                """,
                (
                    score_run.score_run_id,
                    score_run.pm_id,
                    score_run.book_id,
                    score_run.policy_id,
                    score_run.policy_version,
                    score_run.as_of_date,
                    score_run.state,
                    str(score_run.score) if score_run.score is not None else None,
                    score_run.content_hash,
                    score_run.generated_at.isoformat(),
                    score_run.generated_by,
                    score_run.correlation_id,
                    dump_model_json(score_run),
                ),
            )
            persisted = connection.execute(
                """
                SELECT content_hash
                FROM dpm_pm_quality_score_runs
                WHERE score_run_id = %s
                """,
                (score_run.score_run_id,),
            ).fetchone()
            if persisted is None or persisted["content_hash"] != score_run.content_hash:
                connection.rollback()
                raise DpmPmQualityScoreRunConflictError("PM_QUALITY_SCORE_RUN_IMMUTABLE_CONFLICT")
            connection.commit()

    def get_score_run(
        self,
        *,
        score_run_id: str,
    ) -> DpmPmOperatingQualityScoreRun | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT payload_json
                FROM dpm_pm_quality_score_runs
                WHERE score_run_id = %s
                """,
                (score_run_id,),
            ).fetchone()
        if row is None:
            return None
        return load_model_json(DpmPmOperatingQualityScoreRun, _payload(row))

    def list_score_runs(
        self,
        *,
        pm_id: str | None = None,
        book_id: str | None = None,
        policy_id: str | None = None,
        as_of_date: str | None = None,
        state: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[DpmPmOperatingQualityScoreRun]:
        clauses: list[str] = []
        args: list[Any] = []
        for column, value in (
            ("pm_id", pm_id),
            ("book_id", book_id),
            ("policy_id", policy_id),
            ("as_of_date", as_of_date),
            ("state", state),
        ):
            if value is not None:
                clauses.append(f"{column} = %s")
                args.append(value)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        args.extend([limit, offset])
        with closing(self._connect()) as connection:
            rows = connection.execute(
                f"""
                SELECT payload_json
                FROM dpm_pm_quality_score_runs
                {where}
                ORDER BY generated_at DESC, score_run_id DESC
                LIMIT %s OFFSET %s
                """,
                tuple(args),
            ).fetchall()
        return [load_model_json(DpmPmOperatingQualityScoreRun, _payload(row)) for row in rows]

    def _connect(self) -> Any:
        psycopg, dict_row = _import_psycopg()
        return psycopg.connect(self._dsn, row_factory=dict_row)

    def _init_db(self) -> None:
        with closing(self._connect()) as connection:
            apply_postgres_migrations(connection=connection, namespace="dpm")


def _payload(row: Any) -> str | dict[str, Any]:
    payload = row["payload_json"]
    if isinstance(payload, dict):
        return payload
    if not isinstance(payload, str):
        return json.dumps(payload, default=str)
    return payload


def _import_psycopg() -> tuple[Any, Any]:
    import psycopg
    from psycopg.rows import dict_row

    return psycopg, dict_row
