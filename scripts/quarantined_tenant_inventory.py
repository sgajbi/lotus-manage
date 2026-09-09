"""Emit a bounded read-only inventory of NULL-tenant quarantine rows."""

from __future__ import annotations

import argparse
import json
import os
import sys
from importlib.util import find_spec
from pathlib import Path
from typing import Sequence


_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.infrastructure.quarantined_tenant_inventory import INVENTORY_SCHEMA_VERSION  # noqa: E402


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Report every retained NULL-tenant dataset without changing database rows."
    )
    parser.add_argument(
        "--dsn",
        default=os.getenv("DPM_SUPPORTABILITY_POSTGRES_DSN", "").strip(),
        help="PostgreSQL DSN; defaults to DPM_SUPPORTABILITY_POSTGRES_DSN.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum identifying rows returned per dataset (1-100; default 20).",
    )
    args = parser.parse_args(argv)

    try:
        if not args.dsn:
            raise RuntimeError("QUARANTINE_INVENTORY_DSN_REQUIRED")
        if find_spec("psycopg") is None:
            raise RuntimeError("QUARANTINE_INVENTORY_DRIVER_MISSING")
        report = _run_inventory(dsn=args.dsn, limit=args.limit)
    except Exception:
        print(
            json.dumps(
                {
                    "schemaVersion": INVENTORY_SCHEMA_VERSION,
                    "status": "error",
                    "errorCode": "QUARANTINE_INVENTORY_FAILED",
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 1

    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


def _run_inventory(*, dsn: str, limit: int) -> dict[str, object]:
    import psycopg
    from psycopg.rows import dict_row

    from src.infrastructure.postgres_access import connect_postgres
    from src.infrastructure.quarantined_tenant_inventory import (
        build_quarantined_tenant_inventory,
    )

    with connect_postgres(
        dsn,
        connect_fn=psycopg.connect,
        row_factory=dict_row,
        application_name="lotus-manage-quarantine-inventory",
    ) as connection:
        return build_quarantined_tenant_inventory(connection=connection, limit=limit)


if __name__ == "__main__":
    raise SystemExit(main())
