from __future__ import annotations

import json
from contextlib import closing
from datetime import datetime
from typing import Any

from src.core.common.capabilities import has_psycopg
from src.core.outcomes.models import (
    DpmOutcomeEvent,
    DpmOutcomeRetentionMetadata,
    DpmPostTradeOutcomeReview,
)
from src.core.outcomes.repository import DpmOutcomeReviewConflictError
from src.infrastructure.mandates.serialization import dump_model_json, load_model_json
from src.infrastructure.postgres_migrations import apply_postgres_migrations


class PostgresDpmOutcomeReviewRepository:
    def __init__(self, *, dsn: str) -> None:
        if not dsn:
            raise RuntimeError("DPM_OUTCOME_REVIEW_POSTGRES_DSN_REQUIRED")
        if not has_psycopg():
            raise RuntimeError("DPM_OUTCOME_REVIEW_POSTGRES_DRIVER_MISSING")
        self._dsn = dsn
        self._init_db()

    def save_outcome_review(
        self,
        *,
        review: DpmPostTradeOutcomeReview,
        retention_expires_at: datetime | None,
    ) -> None:
        with closing(self._connect()) as connection:
            existing = connection.execute(
                """
                SELECT content_hash
                FROM dpm_post_trade_outcome_reviews
                WHERE outcome_review_id = %s
                """,
                (review.outcome_review_id,),
            ).fetchone()
            if existing is not None and existing["content_hash"] != review.content_hash:
                raise DpmOutcomeReviewConflictError("DPM_OUTCOME_REVIEW_IMMUTABLE_CONFLICT")
            if review.idempotency_key:
                existing_idempotency = connection.execute(
                    """
                    SELECT outcome_review_id
                    FROM dpm_post_trade_outcome_reviews
                    WHERE idempotency_key = %s
                    """,
                    (review.idempotency_key,),
                ).fetchone()
                if (
                    existing_idempotency is not None
                    and existing_idempotency["outcome_review_id"] != review.outcome_review_id
                ):
                    raise DpmOutcomeReviewConflictError("DPM_OUTCOME_REVIEW_IDEMPOTENCY_CONFLICT")
            connection.execute(
                """
                INSERT INTO dpm_post_trade_outcome_reviews (
                    outcome_review_id, portfolio_id, mandate_id, rebalance_run_id,
                    alternative_set_id, selected_alternative_id, proof_pack_id,
                    wave_id, wave_item_id, state, content_hash, idempotency_key,
                    retention_policy, retention_expires_at, legal_hold_state, payload_json,
                    created_at, created_by, correlation_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (outcome_review_id) DO NOTHING
                """,
                (
                    review.outcome_review_id,
                    review.portfolio_id,
                    review.mandate_id,
                    review.rebalance_run_id,
                    review.alternative_set_id,
                    review.selected_alternative_id,
                    review.proof_pack_id,
                    review.wave_id,
                    review.wave_item_id,
                    review.state,
                    review.content_hash,
                    review.idempotency_key,
                    review.retention_policy,
                    retention_expires_at.isoformat() if retention_expires_at else None,
                    review.legal_hold_state,
                    dump_model_json(review),
                    review.created_at.isoformat(),
                    review.created_by,
                    review.correlation_id,
                ),
            )
            for event in review.events:
                _insert_event(connection=connection, event=event)
            connection.commit()

    def get_outcome_review(
        self,
        *,
        outcome_review_id: str,
    ) -> DpmPostTradeOutcomeReview | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT payload_json
                FROM dpm_post_trade_outcome_reviews
                WHERE outcome_review_id = %s
                """,
                (outcome_review_id,),
            ).fetchone()
        if row is None:
            return None
        return load_model_json(DpmPostTradeOutcomeReview, _payload(row))

    def get_outcome_review_by_idempotency(
        self,
        *,
        idempotency_key: str,
    ) -> DpmPostTradeOutcomeReview | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT payload_json
                FROM dpm_post_trade_outcome_reviews
                WHERE idempotency_key = %s
                """,
                (idempotency_key,),
            ).fetchone()
        if row is None:
            return None
        return load_model_json(DpmPostTradeOutcomeReview, _payload(row))

    def list_outcome_reviews(
        self,
        *,
        portfolio_id: str | None = None,
        mandate_id: str | None = None,
        wave_id: str | None = None,
        rebalance_run_id: str | None = None,
        state: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[DpmPostTradeOutcomeReview]:
        clauses: list[str] = []
        args: list[Any] = []
        for column, value in (
            ("portfolio_id", portfolio_id),
            ("mandate_id", mandate_id),
            ("wave_id", wave_id),
            ("rebalance_run_id", rebalance_run_id),
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
                FROM dpm_post_trade_outcome_reviews
                {where}
                ORDER BY created_at DESC, outcome_review_id DESC
                LIMIT %s OFFSET %s
                """,
                tuple(args),
            ).fetchall()
        return [load_model_json(DpmPostTradeOutcomeReview, _payload(row)) for row in rows]

    def get_retention_metadata(
        self,
        *,
        outcome_review_id: str,
    ) -> DpmOutcomeRetentionMetadata | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT outcome_review_id, retention_policy, retention_expires_at, legal_hold_state
                FROM dpm_post_trade_outcome_reviews
                WHERE outcome_review_id = %s
                """,
                (outcome_review_id,),
            ).fetchone()
        if row is None:
            return None
        expires_at = row["retention_expires_at"]
        return DpmOutcomeRetentionMetadata(
            outcome_review_id=row["outcome_review_id"],
            retention_policy=row["retention_policy"],
            retention_expires_at=expires_at.isoformat()
            if hasattr(expires_at, "isoformat")
            else expires_at,
            legal_hold_state=row["legal_hold_state"],
        )

    def append_event(self, *, event: DpmOutcomeEvent) -> None:
        with closing(self._connect()) as connection:
            _insert_event(connection=connection, event=event)
            connection.commit()

    def list_events(self, *, outcome_review_id: str) -> list[DpmOutcomeEvent]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT payload_json
                FROM dpm_post_trade_outcome_events
                WHERE outcome_review_id = %s
                ORDER BY event_time ASC, event_id ASC
                """,
                (outcome_review_id,),
            ).fetchall()
        return [load_model_json(DpmOutcomeEvent, _payload(row)) for row in rows]

    def _connect(self) -> Any:
        psycopg, dict_row = _import_psycopg()
        return psycopg.connect(self._dsn, row_factory=dict_row)

    def _init_db(self) -> None:
        with closing(self._connect()) as connection:
            apply_postgres_migrations(connection=connection, namespace="dpm")


def _insert_event(*, connection: Any, event: DpmOutcomeEvent) -> None:
    connection.execute(
        """
        INSERT INTO dpm_post_trade_outcome_events (
            event_id, outcome_review_id, event_type, event_time, actor, state, payload_json
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (event_id) DO NOTHING
        """,
        (
            event.event_id,
            event.outcome_review_id,
            event.event_type,
            event.event_time,
            event.actor,
            event.state,
            dump_model_json(event),
        ),
    )


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
