from __future__ import annotations

import hashlib
import json
from contextlib import closing
from typing import Any

from src.core.common.capabilities import has_psycopg
from src.core.pm_quality.models import (
    DpmPmOperatingQualityPolicy,
    DpmPmOperatingQualityScoreRun,
    DpmPmQualityFairnessAnalysis,
)
from src.core.pm_quality.repository import (
    DpmPmQualityFairnessAnalysisConflictError,
    DpmPmQualityPolicyConflictError,
    DpmPmQualityScoreRunConflictError,
)
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


class PostgresDpmPmQualityPolicyRepository:
    def __init__(self, *, dsn: str) -> None:
        if not dsn:
            raise RuntimeError("DPM_PM_QUALITY_POSTGRES_DSN_REQUIRED")
        if not has_psycopg():
            raise RuntimeError("DPM_PM_QUALITY_POSTGRES_DRIVER_MISSING")
        self._dsn = dsn
        self._init_db()

    def save_policy(self, *, policy: DpmPmOperatingQualityPolicy) -> None:
        payload = dump_model_json(policy)
        content_hash = _content_hash(payload)
        with closing(self._connect()) as connection:
            connection.execute(
                """
                INSERT INTO dpm_pm_quality_policies (
                    policy_id, policy_version, enabled, as_of_date, access_purpose,
                    content_hash, payload_json
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (policy_id, policy_version) DO NOTHING
                """,
                (
                    policy.policy_id,
                    policy.policy_version,
                    policy.enabled,
                    policy.as_of_date,
                    policy.access_purpose,
                    content_hash,
                    payload,
                ),
            )
            persisted = connection.execute(
                """
                SELECT content_hash
                FROM dpm_pm_quality_policies
                WHERE policy_id = %s AND policy_version = %s
                """,
                (policy.policy_id, policy.policy_version),
            ).fetchone()
            if persisted is None or persisted["content_hash"] != content_hash:
                connection.rollback()
                raise DpmPmQualityPolicyConflictError("PM_QUALITY_POLICY_IMMUTABLE_CONFLICT")
            connection.commit()

    def get_policy(
        self,
        *,
        policy_id: str,
        policy_version: str,
    ) -> DpmPmOperatingQualityPolicy | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT payload_json
                FROM dpm_pm_quality_policies
                WHERE policy_id = %s AND policy_version = %s
                """,
                (policy_id, policy_version),
            ).fetchone()
        if row is None:
            return None
        return load_model_json(DpmPmOperatingQualityPolicy, _payload(row))

    def list_policies(
        self,
        *,
        policy_id: str | None = None,
        enabled: bool | None = None,
        as_of_date: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[DpmPmOperatingQualityPolicy]:
        clauses: list[str] = []
        args: list[Any] = []
        for column, value in (
            ("policy_id", policy_id),
            ("enabled", enabled),
            ("as_of_date", as_of_date),
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
                FROM dpm_pm_quality_policies
                {where}
                ORDER BY as_of_date DESC, policy_id DESC, policy_version DESC
                LIMIT %s OFFSET %s
                """,
                tuple(args),
            ).fetchall()
        return [load_model_json(DpmPmOperatingQualityPolicy, _payload(row)) for row in rows]

    def _connect(self) -> Any:
        psycopg, dict_row = _import_psycopg()
        return psycopg.connect(self._dsn, row_factory=dict_row)

    def _init_db(self) -> None:
        with closing(self._connect()) as connection:
            apply_postgres_migrations(connection=connection, namespace="dpm")


class PostgresDpmPmQualityFairnessAnalysisRepository:
    def __init__(self, *, dsn: str) -> None:
        if not dsn:
            raise RuntimeError("DPM_PM_QUALITY_POSTGRES_DSN_REQUIRED")
        if not has_psycopg():
            raise RuntimeError("DPM_PM_QUALITY_POSTGRES_DRIVER_MISSING")
        self._dsn = dsn
        self._init_db()

    def save_fairness_analysis(self, *, analysis: DpmPmQualityFairnessAnalysis) -> None:
        with closing(self._connect()) as connection:
            connection.execute(
                """
                INSERT INTO dpm_pm_quality_fairness_analyses (
                    fairness_analysis_id, policy_id, policy_version, as_of_date,
                    state, observed_average_score_spread, content_hash, generated_at,
                    generated_by, correlation_id, payload_json
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (fairness_analysis_id) DO NOTHING
                """,
                (
                    analysis.fairness_analysis_id,
                    analysis.policy_id,
                    analysis.policy_version,
                    analysis.as_of_date,
                    analysis.state,
                    str(analysis.observed_average_score_spread)
                    if analysis.observed_average_score_spread is not None
                    else None,
                    analysis.content_hash,
                    analysis.generated_at.isoformat(),
                    analysis.generated_by,
                    analysis.correlation_id,
                    dump_model_json(analysis),
                ),
            )
            persisted = connection.execute(
                """
                SELECT content_hash
                FROM dpm_pm_quality_fairness_analyses
                WHERE fairness_analysis_id = %s
                """,
                (analysis.fairness_analysis_id,),
            ).fetchone()
            if persisted is None or persisted["content_hash"] != analysis.content_hash:
                connection.rollback()
                raise DpmPmQualityFairnessAnalysisConflictError(
                    "PM_QUALITY_FAIRNESS_ANALYSIS_IMMUTABLE_CONFLICT"
                )
            connection.commit()

    def get_fairness_analysis(
        self,
        *,
        fairness_analysis_id: str,
    ) -> DpmPmQualityFairnessAnalysis | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT payload_json
                FROM dpm_pm_quality_fairness_analyses
                WHERE fairness_analysis_id = %s
                """,
                (fairness_analysis_id,),
            ).fetchone()
        if row is None:
            return None
        return load_model_json(DpmPmQualityFairnessAnalysis, _payload(row))

    def list_fairness_analyses(
        self,
        *,
        policy_id: str | None = None,
        policy_version: str | None = None,
        as_of_date: str | None = None,
        state: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[DpmPmQualityFairnessAnalysis]:
        clauses: list[str] = []
        args: list[Any] = []
        for column, value in (
            ("policy_id", policy_id),
            ("policy_version", policy_version),
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
                FROM dpm_pm_quality_fairness_analyses
                {where}
                ORDER BY generated_at DESC, fairness_analysis_id DESC
                LIMIT %s OFFSET %s
                """,
                tuple(args),
            ).fetchall()
        return [load_model_json(DpmPmQualityFairnessAnalysis, _payload(row)) for row in rows]

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


def _content_hash(payload: str) -> str:
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _import_psycopg() -> tuple[Any, Any]:
    import psycopg
    from psycopg.rows import dict_row

    return psycopg, dict_row
