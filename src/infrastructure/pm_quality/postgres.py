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
    DpmPmQualityReviewAction,
    DpmPmQualitySummaryInvocation,
)
from src.core.pm_quality.repository import (
    DpmPmQualityFairnessAnalysisConflictError,
    DpmPmQualityPolicyConflictError,
    DpmPmQualityReviewActionConflictError,
    DpmPmQualityReviewActionIntegrityError,
    DpmPmQualityScoreRunConflictError,
    DpmPmQualitySummaryInvocationConflictError,
    DpmPmQualitySummaryInvocationIntegrityError,
)
from src.infrastructure.mandates.serialization import dump_model_json, load_model_json
from src.infrastructure.postgres_access import connect_postgres
from src.infrastructure.postgres_migrations import apply_postgres_migrations


class PostgresDpmPmQualityScoreRunRepository:
    def __init__(self, *, dsn: str) -> None:
        if not dsn:
            raise RuntimeError("DPM_PM_QUALITY_POSTGRES_DSN_REQUIRED")
        if not has_psycopg():
            raise RuntimeError("DPM_PM_QUALITY_POSTGRES_DRIVER_MISSING")
        self._dsn = dsn
        self._init_db()

    def save_score_run(self, *, tenant_id: str, score_run: DpmPmOperatingQualityScoreRun) -> None:
        _ensure_record_tenant(tenant_id=tenant_id, record_tenant_id=score_run.tenant_id)
        with closing(self._connect()) as connection:
            connection.execute(
                """
                INSERT INTO dpm_pm_quality_score_runs (
                    tenant_id, score_run_id, pm_id, book_id, policy_id, policy_version, as_of_date,
                    state, score, content_hash, generated_at, generated_by, correlation_id,
                    payload_json
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (tenant_id, score_run_id) DO NOTHING
                """,
                (
                    tenant_id,
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
                WHERE tenant_id = %s AND score_run_id = %s
                """,
                (tenant_id, score_run.score_run_id),
            ).fetchone()
            if persisted is None or persisted["content_hash"] != score_run.content_hash:
                connection.rollback()
                raise DpmPmQualityScoreRunConflictError("PM_QUALITY_SCORE_RUN_IMMUTABLE_CONFLICT")
            connection.commit()

    def get_score_run(
        self,
        *,
        tenant_id: str,
        score_run_id: str,
    ) -> DpmPmOperatingQualityScoreRun | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT payload_json
                FROM dpm_pm_quality_score_runs
                WHERE tenant_id = %s AND score_run_id = %s
                """,
                (tenant_id, score_run_id),
            ).fetchone()
        if row is None:
            return None
        return load_model_json(DpmPmOperatingQualityScoreRun, _payload(row))

    def list_score_runs(
        self,
        *,
        tenant_id: str,
        pm_id: str | None = None,
        book_id: str | None = None,
        policy_id: str | None = None,
        as_of_date: str | None = None,
        state: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[DpmPmOperatingQualityScoreRun]:
        clauses: list[str] = ["tenant_id = %s"]
        args: list[Any] = [tenant_id]
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
        return _connect_pm_quality_postgres(
            dsn=self._dsn,
            application_name="lotus-manage:pm-quality-score-runs",
        )

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

    def save_policy(self, *, tenant_id: str, policy: DpmPmOperatingQualityPolicy) -> None:
        _ensure_record_tenant(tenant_id=tenant_id, record_tenant_id=policy.tenant_id)
        payload = dump_model_json(policy)
        content_hash = _content_hash(payload)
        with closing(self._connect()) as connection:
            connection.execute(
                """
                INSERT INTO dpm_pm_quality_policies (
                    tenant_id, policy_id, policy_version, enabled, as_of_date, access_purpose,
                    content_hash, payload_json
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (tenant_id, policy_id, policy_version) DO NOTHING
                """,
                (
                    tenant_id,
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
                WHERE tenant_id = %s AND policy_id = %s AND policy_version = %s
                """,
                (tenant_id, policy.policy_id, policy.policy_version),
            ).fetchone()
            if persisted is None or persisted["content_hash"] != content_hash:
                connection.rollback()
                raise DpmPmQualityPolicyConflictError("PM_QUALITY_POLICY_IMMUTABLE_CONFLICT")
            connection.commit()

    def get_policy(
        self,
        *,
        tenant_id: str,
        policy_id: str,
        policy_version: str,
    ) -> DpmPmOperatingQualityPolicy | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT payload_json
                FROM dpm_pm_quality_policies
                WHERE tenant_id = %s AND policy_id = %s AND policy_version = %s
                """,
                (tenant_id, policy_id, policy_version),
            ).fetchone()
        if row is None:
            return None
        return load_model_json(DpmPmOperatingQualityPolicy, _payload(row))

    def list_policies(
        self,
        *,
        tenant_id: str,
        policy_id: str | None = None,
        enabled: bool | None = None,
        as_of_date: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[DpmPmOperatingQualityPolicy]:
        clauses: list[str] = ["tenant_id = %s"]
        args: list[Any] = [tenant_id]
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
        return _connect_pm_quality_postgres(
            dsn=self._dsn,
            application_name="lotus-manage:pm-quality-policies",
        )

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

    def save_fairness_analysis(
        self, *, tenant_id: str, analysis: DpmPmQualityFairnessAnalysis
    ) -> None:
        _ensure_record_tenant(tenant_id=tenant_id, record_tenant_id=analysis.tenant_id)
        with closing(self._connect()) as connection:
            connection.execute(
                """
                INSERT INTO dpm_pm_quality_fairness_analyses (
                    tenant_id, fairness_analysis_id, policy_id, policy_version, as_of_date,
                    state, observed_average_score_spread, content_hash, generated_at,
                    generated_by, correlation_id, payload_json
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (tenant_id, fairness_analysis_id) DO NOTHING
                """,
                (
                    tenant_id,
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
                WHERE tenant_id = %s AND fairness_analysis_id = %s
                """,
                (tenant_id, analysis.fairness_analysis_id),
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
        tenant_id: str,
        fairness_analysis_id: str,
    ) -> DpmPmQualityFairnessAnalysis | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT payload_json
                FROM dpm_pm_quality_fairness_analyses
                WHERE tenant_id = %s AND fairness_analysis_id = %s
                """,
                (tenant_id, fairness_analysis_id),
            ).fetchone()
        if row is None:
            return None
        return load_model_json(DpmPmQualityFairnessAnalysis, _payload(row))

    def list_fairness_analyses(
        self,
        *,
        tenant_id: str,
        policy_id: str | None = None,
        policy_version: str | None = None,
        as_of_date: str | None = None,
        state: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[DpmPmQualityFairnessAnalysis]:
        clauses: list[str] = ["tenant_id = %s"]
        args: list[Any] = [tenant_id]
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
        return _connect_pm_quality_postgres(
            dsn=self._dsn,
            application_name="lotus-manage:pm-quality-fairness",
        )

    def _init_db(self) -> None:
        with closing(self._connect()) as connection:
            apply_postgres_migrations(connection=connection, namespace="dpm")


class PostgresDpmPmQualityReviewActionRepository:
    def __init__(self, *, dsn: str) -> None:
        if not dsn:
            raise RuntimeError("DPM_PM_QUALITY_POSTGRES_DSN_REQUIRED")
        if not has_psycopg():
            raise RuntimeError("DPM_PM_QUALITY_POSTGRES_DRIVER_MISSING")
        self._dsn = dsn
        self._init_db()

    def save_review_action(self, *, tenant_id: str, action: DpmPmQualityReviewAction) -> None:
        _ensure_record_tenant(tenant_id=tenant_id, record_tenant_id=action.tenant_id)
        with closing(self._connect()) as connection:
            _validate_postgres_review_action_parent(
                connection=connection,
                tenant_id=tenant_id,
                action=action,
            )
            connection.execute(
                """
                INSERT INTO dpm_pm_quality_review_actions (
                    tenant_id, review_action_id, review_action_ref, target_type, target_id,
                    policy_id, policy_version, as_of_date, target_state, action_type,
                    action_state, content_hash, generated_at, actor_id, correlation_id,
                    payload_json
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (tenant_id, review_action_id) DO NOTHING
                """,
                (
                    tenant_id,
                    action.review_action_id,
                    action.review_action_ref,
                    action.target_type,
                    action.target_id,
                    action.policy_id,
                    action.policy_version,
                    action.as_of_date,
                    action.target_state,
                    action.action_type,
                    action.action_state,
                    action.content_hash,
                    action.generated_at.isoformat(),
                    action.actor_id,
                    action.correlation_id,
                    dump_model_json(action),
                ),
            )
            persisted = connection.execute(
                """
                SELECT content_hash
                FROM dpm_pm_quality_review_actions
                WHERE tenant_id = %s AND review_action_id = %s
                """,
                (tenant_id, action.review_action_id),
            ).fetchone()
            if persisted is None or persisted["content_hash"] != action.content_hash:
                connection.rollback()
                raise DpmPmQualityReviewActionConflictError(
                    "PM_QUALITY_REVIEW_ACTION_IMMUTABLE_CONFLICT"
                )
            connection.commit()

    def get_review_action(
        self,
        *,
        tenant_id: str,
        review_action_id: str,
    ) -> DpmPmQualityReviewAction | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT payload_json
                FROM dpm_pm_quality_review_actions
                WHERE tenant_id = %s AND review_action_id = %s
                """,
                (tenant_id, review_action_id),
            ).fetchone()
        if row is None:
            return None
        return load_model_json(DpmPmQualityReviewAction, _payload(row))

    def list_review_actions(
        self,
        *,
        tenant_id: str,
        target_type: str | None = None,
        target_id: str | None = None,
        policy_id: str | None = None,
        as_of_date: str | None = None,
        action_state: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[DpmPmQualityReviewAction]:
        clauses: list[str] = ["tenant_id = %s"]
        args: list[Any] = [tenant_id]
        for column, value in (
            ("target_type", target_type),
            ("target_id", target_id),
            ("policy_id", policy_id),
            ("as_of_date", as_of_date),
            ("action_state", action_state),
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
                FROM dpm_pm_quality_review_actions
                {where}
                ORDER BY generated_at DESC, review_action_id DESC
                LIMIT %s OFFSET %s
                """,
                tuple(args),
            ).fetchall()
        return [load_model_json(DpmPmQualityReviewAction, _payload(row)) for row in rows]

    def _connect(self) -> Any:
        return _connect_pm_quality_postgres(
            dsn=self._dsn,
            application_name="lotus-manage:pm-quality-review-actions",
        )

    def _init_db(self) -> None:
        with closing(self._connect()) as connection:
            apply_postgres_migrations(connection=connection, namespace="dpm")


class PostgresDpmPmQualitySummaryInvocationRepository:
    def __init__(self, *, dsn: str) -> None:
        if not dsn:
            raise RuntimeError("DPM_PM_QUALITY_POSTGRES_DSN_REQUIRED")
        if not has_psycopg():
            raise RuntimeError("DPM_PM_QUALITY_POSTGRES_DRIVER_MISSING")
        self._dsn = dsn
        self._init_db()

    def save_summary_invocation(
        self, *, tenant_id: str, invocation: DpmPmQualitySummaryInvocation
    ) -> None:
        _ensure_record_tenant(tenant_id=tenant_id, record_tenant_id=invocation.tenant_id)
        with closing(self._connect()) as connection:
            _validate_postgres_summary_invocation_parents(
                connection=connection,
                tenant_id=tenant_id,
                invocation=invocation,
            )
            try:
                connection.execute(
                    """
                    INSERT INTO dpm_pm_quality_summary_invocations (
                        tenant_id, summary_invocation_id, score_run_id, review_action_id, policy_id,
                        policy_version, as_of_date, invocation_state, summary_ref,
                        workflow_pack_name, workflow_pack_version, workflow_run_id,
                        summary_artifact_ref, summary_content_hash, content_hash,
                        generated_at, requested_by, correlation_id, payload_json
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (tenant_id, summary_invocation_id) DO NOTHING
                    """,
                    (
                        tenant_id,
                        invocation.summary_invocation_id,
                        invocation.score_run_id,
                        invocation.review_action_id,
                        invocation.policy_id,
                        invocation.policy_version,
                        invocation.as_of_date,
                        invocation.invocation_state,
                        invocation.summary_ref,
                        invocation.workflow_pack_name,
                        invocation.workflow_pack_version,
                        invocation.workflow_run_id,
                        invocation.summary_artifact_ref,
                        invocation.summary_content_hash,
                        invocation.content_hash,
                        invocation.generated_at.isoformat(),
                        invocation.requested_by,
                        invocation.correlation_id,
                        dump_model_json(invocation),
                    ),
                )
            except Exception as exc:
                _raise_if_foreign_key_violation(
                    exc,
                    DpmPmQualitySummaryInvocationIntegrityError(
                        "PM_QUALITY_SUMMARY_INVOCATION_PARENT_NOT_FOUND"
                    ),
                )
                raise
            persisted = connection.execute(
                """
                SELECT content_hash
                FROM dpm_pm_quality_summary_invocations
                WHERE tenant_id = %s AND summary_invocation_id = %s
                """,
                (tenant_id, invocation.summary_invocation_id),
            ).fetchone()
            if persisted is None or persisted["content_hash"] != invocation.content_hash:
                connection.rollback()
                raise DpmPmQualitySummaryInvocationConflictError(
                    "PM_QUALITY_SUMMARY_INVOCATION_IMMUTABLE_CONFLICT"
                )
            connection.commit()

    def get_summary_invocation(
        self,
        *,
        tenant_id: str,
        summary_invocation_id: str,
    ) -> DpmPmQualitySummaryInvocation | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT payload_json
                FROM dpm_pm_quality_summary_invocations
                WHERE tenant_id = %s AND summary_invocation_id = %s
                """,
                (tenant_id, summary_invocation_id),
            ).fetchone()
        if row is None:
            return None
        return load_model_json(DpmPmQualitySummaryInvocation, _payload(row))

    def list_summary_invocations(
        self,
        *,
        tenant_id: str,
        score_run_id: str | None = None,
        review_action_id: str | None = None,
        policy_id: str | None = None,
        as_of_date: str | None = None,
        invocation_state: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[DpmPmQualitySummaryInvocation]:
        clauses: list[str] = ["tenant_id = %s"]
        args: list[Any] = [tenant_id]
        for column, value in (
            ("score_run_id", score_run_id),
            ("review_action_id", review_action_id),
            ("policy_id", policy_id),
            ("as_of_date", as_of_date),
            ("invocation_state", invocation_state),
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
                FROM dpm_pm_quality_summary_invocations
                {where}
                ORDER BY generated_at DESC, summary_invocation_id DESC
                LIMIT %s OFFSET %s
                """,
                tuple(args),
            ).fetchall()
        return [load_model_json(DpmPmQualitySummaryInvocation, _payload(row)) for row in rows]

    def _connect(self) -> Any:
        return _connect_pm_quality_postgres(
            dsn=self._dsn,
            application_name="lotus-manage:pm-quality-summaries",
        )

    def _init_db(self) -> None:
        with closing(self._connect()) as connection:
            apply_postgres_migrations(connection=connection, namespace="dpm")


def _validate_postgres_review_action_parent(
    *,
    connection: Any,
    tenant_id: str,
    action: DpmPmQualityReviewAction,
) -> None:
    if action.target_type == "SCORE_RUN":
        row = _pm_quality_parent_row(
            connection=connection,
            table="dpm_pm_quality_score_runs",
            id_column="score_run_id",
            tenant_id=tenant_id,
            identifier=action.target_id,
        )
    elif action.target_type == "FAIRNESS_ANALYSIS":
        row = _pm_quality_parent_row(
            connection=connection,
            table="dpm_pm_quality_fairness_analyses",
            id_column="fairness_analysis_id",
            tenant_id=tenant_id,
            identifier=action.target_id,
        )
    else:
        raise DpmPmQualityReviewActionIntegrityError(
            "PM_QUALITY_REVIEW_ACTION_TARGET_TYPE_UNSUPPORTED"
        )
    if row is None:
        raise DpmPmQualityReviewActionIntegrityError("PM_QUALITY_REVIEW_ACTION_TARGET_NOT_FOUND")
    if (
        row["content_hash"] != action.target_content_hash
        or row["policy_id"] != action.policy_id
        or row["policy_version"] != action.policy_version
        or row["as_of_date"] != action.as_of_date
        or row["state"] != action.target_state
    ):
        raise DpmPmQualityReviewActionIntegrityError("PM_QUALITY_REVIEW_ACTION_TARGET_MISMATCH")


def _validate_postgres_summary_invocation_parents(
    *,
    connection: Any,
    tenant_id: str,
    invocation: DpmPmQualitySummaryInvocation,
) -> None:
    score_run = _pm_quality_parent_row(
        connection=connection,
        table="dpm_pm_quality_score_runs",
        id_column="score_run_id",
        tenant_id=tenant_id,
        identifier=invocation.score_run_id,
    )
    if score_run is None:
        raise DpmPmQualitySummaryInvocationIntegrityError(
            "PM_QUALITY_SUMMARY_INVOCATION_SCORE_RUN_NOT_FOUND"
        )
    if (
        score_run["content_hash"] != invocation.score_run_content_hash
        or score_run["policy_id"] != invocation.policy_id
        or score_run["policy_version"] != invocation.policy_version
        or score_run["as_of_date"] != invocation.as_of_date
    ):
        raise DpmPmQualitySummaryInvocationIntegrityError(
            "PM_QUALITY_SUMMARY_INVOCATION_SCORE_RUN_MISMATCH"
        )
    review_action = connection.execute(
        """
        SELECT content_hash, target_type, target_id, policy_id, policy_version, as_of_date
        FROM dpm_pm_quality_review_actions
        WHERE tenant_id = %s AND review_action_id = %s
        """,
        (tenant_id, invocation.review_action_id),
    ).fetchone()
    if review_action is None:
        raise DpmPmQualitySummaryInvocationIntegrityError(
            "PM_QUALITY_SUMMARY_INVOCATION_REVIEW_ACTION_NOT_FOUND"
        )
    if (
        review_action["content_hash"] != invocation.review_action_content_hash
        or review_action["target_type"] != "SCORE_RUN"
        or review_action["target_id"] != invocation.score_run_id
        or review_action["policy_id"] != invocation.policy_id
        or review_action["policy_version"] != invocation.policy_version
        or review_action["as_of_date"] != invocation.as_of_date
    ):
        raise DpmPmQualitySummaryInvocationIntegrityError(
            "PM_QUALITY_SUMMARY_INVOCATION_REVIEW_ACTION_MISMATCH"
        )


def _pm_quality_parent_row(
    *,
    connection: Any,
    table: str,
    id_column: str,
    tenant_id: str,
    identifier: str,
) -> Any:
    return connection.execute(
        f"""
        SELECT content_hash, policy_id, policy_version, as_of_date, state
        FROM {table}
        WHERE tenant_id = %s AND {id_column} = %s
        """,
        (tenant_id, identifier),
    ).fetchone()


def _ensure_record_tenant(*, tenant_id: str, record_tenant_id: str) -> None:
    if not tenant_id.strip():
        raise ValueError("PM_QUALITY_TENANT_REQUIRED")
    if record_tenant_id != tenant_id:
        raise ValueError("PM_QUALITY_TENANT_MISMATCH")


def _raise_if_foreign_key_violation(exc: Exception, replacement: Exception) -> None:
    sqlstate = getattr(exc, "sqlstate", None)
    if sqlstate is None:
        sqlstate = getattr(getattr(exc, "diag", None), "sqlstate", None)
    if sqlstate == "23503":
        raise replacement from exc


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


def _connect_pm_quality_postgres(*, dsn: str, application_name: str) -> Any:
    psycopg, dict_row = _import_psycopg()
    return connect_postgres(
        dsn,
        connect_fn=psycopg.connect,
        row_factory=dict_row,
        application_name=application_name,
    )
