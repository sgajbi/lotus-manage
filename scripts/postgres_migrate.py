import argparse
import os
import sys
from importlib.util import find_spec
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Apply forward-only PostgreSQL migrations for lotus-manage supportability stores."
    )
    parser.add_argument(
        "--target",
        choices=["dpm"],
        default="dpm",
        help="Migration target namespace.",
    )
    parser.add_argument(
        "--dpm-dsn",
        default=os.getenv("DPM_SUPPORTABILITY_POSTGRES_DSN", "").strip(),
        help="PostgreSQL DSN for lotus-manage supportability migrations.",
    )
    args = parser.parse_args()

    if find_spec("psycopg") is None:
        raise RuntimeError("POSTGRES_MIGRATION_DRIVER_MISSING")
    import psycopg
    from psycopg.rows import dict_row

    from src.infrastructure.postgres_migrations import apply_postgres_migrations

    targets = _resolve_targets(args.target, args.dpm_dsn)
    for namespace, dsn in targets:
        if not dsn:
            raise RuntimeError(f"POSTGRES_MIGRATION_DSN_REQUIRED:{namespace}")
        with psycopg.connect(dsn, row_factory=dict_row) as connection:
            apply_postgres_migrations(connection=connection, namespace=namespace)
        print(f"Applied migrations for namespace={namespace}")
    return 0


def _resolve_targets(target: str, dpm_dsn: str) -> list[tuple[str, str]]:
    if target == "dpm":
        return [("dpm", dpm_dsn)]
    raise RuntimeError(f"POSTGRES_MIGRATION_TARGET_UNSUPPORTED:{target}")


if __name__ == "__main__":
    raise SystemExit(main())
