import json
from contextlib import closing
from datetime import datetime, timezone
from importlib.util import find_spec
from typing import Any, cast

from src.core.dpm.policy_packs import DpmPolicyPackDefinition
from src.infrastructure.postgres_migrations import apply_postgres_migrations


class PostgresDpmPolicyPackRepository:
    def __init__(self, *, dsn: str) -> None:
        if not dsn:
            raise RuntimeError("DPM_POLICY_PACK_POSTGRES_DSN_REQUIRED")
        if find_spec("psycopg") is None:
            raise RuntimeError("DPM_POLICY_PACK_POSTGRES_DRIVER_MISSING")
        self._dsn = dsn
        self._init_db()

    def list_policy_packs(self) -> list[DpmPolicyPackDefinition]:
        query = """
            SELECT
                policy_pack_id,
                version,
                definition_json
            FROM dpm_policy_packs
            ORDER BY policy_pack_id ASC
        """
        with closing(self._connect()) as connection:
            rows = connection.execute(query).fetchall()
        return [_row_to_policy_pack(row) for row in rows]

    def get_policy_pack(self, *, policy_pack_id: str) -> DpmPolicyPackDefinition | None:
        query = """
            SELECT
                policy_pack_id,
                version,
                definition_json
            FROM dpm_policy_packs
            WHERE policy_pack_id = %s
        """
        with closing(self._connect()) as connection:
            row = connection.execute(query, (policy_pack_id,)).fetchone()
        if row is None:
            return None
        return _row_to_policy_pack(row)

    def upsert_policy_pack(self, policy_pack: DpmPolicyPackDefinition) -> None:
        query = """
            INSERT INTO dpm_policy_packs (
                policy_pack_id,
                version,
                definition_json,
                updated_at,
                created_at
            ) VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (policy_pack_id) DO UPDATE SET
                version=excluded.version,
                definition_json=excluded.definition_json,
                updated_at=excluded.updated_at
        """
        now = datetime.now(timezone.utc).isoformat()
        with closing(self._connect()) as connection:
            connection.execute(
                query,
                (
                    policy_pack.policy_pack_id,
                    policy_pack.version,
                    _json_dump(policy_pack.model_dump(mode="json")),
                    now,
                    now,
                ),
            )
            connection.commit()

    def delete_policy_pack(self, *, policy_pack_id: str) -> bool:
        query = "DELETE FROM dpm_policy_packs WHERE policy_pack_id = %s"
        with closing(self._connect()) as connection:
            cursor = connection.execute(query, (policy_pack_id,))
            connection.commit()
            return int(cursor.rowcount) > 0

    def _connect(self) -> Any:
        psycopg, dict_row = _import_psycopg()
        return psycopg.connect(self._dsn, row_factory=dict_row)

    def _init_db(self) -> None:
        with closing(self._connect()) as connection:
            apply_postgres_migrations(connection=connection, namespace="dpm")


def _import_psycopg() -> tuple[Any, Any]:
    import psycopg
    from psycopg.rows import dict_row

    return psycopg, dict_row


def _row_to_policy_pack(row: Any) -> DpmPolicyPackDefinition:
    payload = json.loads(row["definition_json"])
    payload["policy_pack_id"] = row["policy_pack_id"]
    payload["version"] = row["version"]
    return cast(DpmPolicyPackDefinition, DpmPolicyPackDefinition.model_validate(payload))


def _json_dump(value: dict[str, Any]) -> str:
    return json.dumps(value, separators=(",", ":"), sort_keys=True)
