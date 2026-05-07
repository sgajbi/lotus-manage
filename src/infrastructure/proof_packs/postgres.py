from __future__ import annotations

import json
from contextlib import closing
from datetime import datetime
from typing import Any

from src.core.common.capabilities import has_psycopg
from src.core.proof_packs.models import (
    DpmPreTradeProofPack,
    DpmProofPackRetentionMetadata,
    DpmProofPackStoredRef,
)
from src.core.proof_packs.repository import DpmProofPackConflictError
from src.infrastructure.mandates.serialization import dump_model_json, load_model_json
from src.infrastructure.postgres_migrations import apply_postgres_migrations
from src.infrastructure.proof_packs.in_memory import RETENTION_POLICY_PRE_TRADE_PROOF_PACK


class PostgresDpmProofPackRepository:
    def __init__(self, *, dsn: str) -> None:
        if not dsn:
            raise RuntimeError("DPM_PROOF_PACK_POSTGRES_DSN_REQUIRED")
        if not has_psycopg():
            raise RuntimeError("DPM_PROOF_PACK_POSTGRES_DRIVER_MISSING")
        self._dsn = dsn
        self._init_db()

    def save_proof_pack(
        self,
        *,
        proof_pack: DpmPreTradeProofPack,
        idempotency_key: str | None,
        retention_expires_at: datetime | None,
    ) -> None:
        with closing(self._connect()) as connection:
            existing = connection.execute(
                """
                SELECT content_hash
                FROM dpm_pre_trade_proof_packs
                WHERE proof_pack_id = %s
                """,
                (proof_pack.proof_pack_id,),
            ).fetchone()
            if existing is not None and existing["content_hash"] != proof_pack.content_hash:
                raise DpmProofPackConflictError("DPM_PROOF_PACK_IMMUTABLE_CONFLICT")
            if idempotency_key is not None:
                existing_idempotency = connection.execute(
                    """
                    SELECT proof_pack_id
                    FROM dpm_pre_trade_proof_packs
                    WHERE idempotency_key = %s
                    """,
                    (idempotency_key,),
                ).fetchone()
                if (
                    existing_idempotency is not None
                    and existing_idempotency["proof_pack_id"] != proof_pack.proof_pack_id
                ):
                    raise DpmProofPackConflictError("DPM_PROOF_PACK_IDEMPOTENCY_CONFLICT")

            connection.execute(
                """
                INSERT INTO dpm_pre_trade_proof_packs (
                    proof_pack_id,
                    portfolio_id,
                    mandate_id,
                    source_type,
                    status,
                    content_hash,
                    idempotency_key,
                    retention_policy,
                    retention_expires_at,
                    payload_json,
                    created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (proof_pack_id) DO NOTHING
                """,
                (
                    proof_pack.proof_pack_id,
                    proof_pack.portfolio_id,
                    proof_pack.mandate_id,
                    proof_pack.source_type,
                    proof_pack.status,
                    proof_pack.content_hash,
                    idempotency_key,
                    RETENTION_POLICY_PRE_TRADE_PROOF_PACK,
                    retention_expires_at.isoformat() if retention_expires_at else None,
                    dump_model_json(proof_pack),
                    proof_pack.created_at.isoformat(),
                ),
            )
            for section in proof_pack.sections:
                connection.execute(
                    """
                    INSERT INTO dpm_pre_trade_proof_pack_sections (
                        proof_pack_id,
                        section_id,
                        section_type,
                        state,
                        content_hash,
                        payload_json,
                        created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (proof_pack_id, section_id) DO NOTHING
                    """,
                    (
                        proof_pack.proof_pack_id,
                        section.section_id,
                        section.section_type,
                        section.state,
                        section.content_hash,
                        dump_model_json(section),
                        section.generated_at,
                    ),
                )
            connection.commit()

    def get_proof_pack(self, *, proof_pack_id: str) -> DpmPreTradeProofPack | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT payload_json
                FROM dpm_pre_trade_proof_packs
                WHERE proof_pack_id = %s
                """,
                (proof_pack_id,),
            ).fetchone()
        if row is None:
            return None
        return load_model_json(DpmPreTradeProofPack, _payload(row))

    def get_proof_pack_by_idempotency(
        self,
        *,
        idempotency_key: str,
    ) -> DpmPreTradeProofPack | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT payload_json
                FROM dpm_pre_trade_proof_packs
                WHERE idempotency_key = %s
                """,
                (idempotency_key,),
            ).fetchone()
        if row is None:
            return None
        return load_model_json(DpmPreTradeProofPack, _payload(row))

    def list_proof_packs(
        self,
        *,
        portfolio_id: str | None = None,
        mandate_id: str | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[DpmPreTradeProofPack]:
        clauses: list[str] = []
        args: list[Any] = []
        for column, value in (
            ("portfolio_id", portfolio_id),
            ("mandate_id", mandate_id),
            ("status", status),
        ):
            if value is not None:
                clauses.append(f"{column} = %s")
                args.append(value)
        where_clause = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        args.extend([limit, offset])
        with closing(self._connect()) as connection:
            rows = connection.execute(
                f"""
                SELECT payload_json
                FROM dpm_pre_trade_proof_packs
                {where_clause}
                ORDER BY created_at DESC, proof_pack_id DESC
                LIMIT %s OFFSET %s
                """,
                tuple(args),
            ).fetchall()
        return [load_model_json(DpmPreTradeProofPack, _payload(row)) for row in rows]

    def get_retention_metadata(
        self,
        *,
        proof_pack_id: str,
    ) -> DpmProofPackRetentionMetadata | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT proof_pack_id, retention_policy, retention_expires_at
                FROM dpm_pre_trade_proof_packs
                WHERE proof_pack_id = %s
                """,
                (proof_pack_id,),
            ).fetchone()
        if row is None:
            return None
        expires_at = row["retention_expires_at"]
        return DpmProofPackRetentionMetadata(
            proof_pack_id=row["proof_pack_id"],
            retention_policy=row["retention_policy"],
            retention_expires_at=expires_at.isoformat()
            if hasattr(expires_at, "isoformat")
            else expires_at,
        )

    def append_ref(self, *, ref: DpmProofPackStoredRef) -> None:
        with closing(self._connect()) as connection:
            connection.execute(
                """
                INSERT INTO dpm_pre_trade_proof_pack_refs (
                    proof_pack_id,
                    ref_type,
                    ref_id,
                    source_system,
                    content_hash,
                    payload_json,
                    created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    ref.proof_pack_id,
                    ref.ref_type,
                    ref.ref_id,
                    ref.source_system,
                    ref.content_hash,
                    dump_model_json(ref),
                    ref.created_at,
                ),
            )
            connection.commit()

    def list_refs(self, *, proof_pack_id: str) -> list[DpmProofPackStoredRef]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT payload_json
                FROM dpm_pre_trade_proof_pack_refs
                WHERE proof_pack_id = %s
                ORDER BY created_at ASC, ref_type ASC, ref_id ASC
                """,
                (proof_pack_id,),
            ).fetchall()
        return [load_model_json(DpmProofPackStoredRef, _payload(row)) for row in rows]

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
