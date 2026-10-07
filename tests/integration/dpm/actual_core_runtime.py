"""Opt-in access to an isolated, source-pinned Core cohort producer.

No service is started here. The operator owns the archived Core source, migrated
database and QCP process. Writes use Core's real DTO/writer, not a substitute
supplier; HTTP reads use its normally composed registered route.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tarfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import httpx
import psycopg
import pytest
from psycopg.conninfo import conninfo_to_dict

CORE_REVISION = "5dc98e084be70821544c4d2d1de2203ddccc4260"
CORE_ARCHIVE_SHA256 = "edb6296e92b77511918afa21204791affe3cbcf3345de4d4903ff5a28c0af59a"
_CORE_BLOBS = {
    "src/services/query_control_plane_service/app/infrastructure/"
    "dpm_portfolio_population_sources.py": "210f9c1b2f315cafac042ef80168b3064e41ac57",
    "src/services/query_control_plane_service/app/infrastructure/"
    "effective_mandate_sources.py": "edaa9290482714fb4c9070559bfa885bf24e08c6",
    "src/services/ingestion_service/app/services/"
    "reference_data_ingestion_service.py": "58bce6071817e3f067ddd7ccfbf30172c1778c03",
}
_SEED = """
import asyncio, json, sys
from datetime import date, datetime
from pathlib import Path
import portfolio_common
from portfolio_common.db import get_async_engine, get_async_session_factory
from portfolio_common.database_models import ModelPortfolioDefinition, Portfolio
from src.services.ingestion_service.app.DTOs.reference_data_discretionary_mandate_dto import (
    DiscretionaryMandateBindingRecord,
)
from src.services.ingestion_service.app.services.reference_data_ingestion_service import (
    ReferenceDataIngestionService,
)

async def main():
    assert Path(portfolio_common.__file__).resolve().is_relative_to(Path.cwd())
    payload = json.load(sys.stdin)
    try:
        async with get_async_session_factory()() as session:
            if payload.get("initialize"):
                session.add(Portfolio(
                    tenant_id=payload["tenant"], portfolio_id=payload["portfolio"],
                    base_currency="SGD", open_date=date(2020, 1, 1),
                    risk_exposure="BALANCED", investment_time_horizon="LONG_TERM",
                    portfolio_type="DISCRETIONARY", booking_center_code="Singapore",
                    client_id=payload["client"], is_leverage_allowed=False, status="ACTIVE",
                ))
                for model in payload["models"]:
                    session.add(ModelPortfolioDefinition(
                        model_portfolio_id=model, model_portfolio_version="2026.01",
                        display_name="Cohort consumer proof", base_currency="SGD",
                        risk_profile="balanced", mandate_type="discretionary",
                        approval_status="approved", approved_at=datetime.fromisoformat(
                            "2025-12-31T00:00:00+00:00"), effective_from=date(2026, 1, 1),
                        source_system="cohort-consumer-proof", source_record_id="model:" + model,
                        observed_at=datetime.fromisoformat("2025-12-31T00:00:00+00:00"),
                        quality_status="accepted",
                    ))
                await session.commit()
            records = [DiscretionaryMandateBindingRecord.model_validate(record).model_dump()
                       for record in payload["bindings"]]
            await ReferenceDataIngestionService(session).upsert_discretionary_mandate_bindings(
                records)
    finally:
        await get_async_engine().dispose()

asyncio.run(main())
"""


@dataclass(frozen=True)
class ActualCore:
    client: httpx.Client
    source: Path
    python: Path
    dsn: str

    def ingest(self, payload: dict[str, object]) -> None:
        environment = os.environ.copy()
        environment.update(
            HOST_DATABASE_URL=self.dsn,
            DATABASE_URL=self.dsn,
            PYTHONPATH=str(self.source / "src/libs/portfolio-common"),
        )
        result = subprocess.run(
            [str(self.python), "-c", _SEED],
            input=json.dumps(payload),
            text=True,
            cwd=self.source,
            env=environment,
            capture_output=True,
            timeout=45,
            check=False,
        )
        # Do not echo credentials or upstream diagnostics into persisted evidence.
        assert result.returncode == 0, "Core's production fixture writer failed"


def _verify_source_archive(source: Path, archive: Path) -> None:
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == CORE_ARCHIVE_SHA256
    expected_paths = set()
    with tarfile.open(archive) as exported:
        assert exported.pax_headers["comment"] == CORE_REVISION
        for member in exported:
            if member.isdir():
                continue
            assert member.isfile(), "Unexpected non-file in pinned Core source archive"
            expected_paths.add(member.name)
            path = (source / member.name).resolve(strict=True)
            assert path.is_relative_to(source), "Archive path escapes owned source directory"
            stream = exported.extractfile(member)
            assert stream is not None
            with stream:
                assert (
                    hashlib.sha256(path.read_bytes()).digest()
                    == hashlib.sha256(stream.read()).digest()
                ), f"Exported Core source changed: {member.name}"
    actual_paths = {
        path.relative_to(source).as_posix() for path in source.rglob("*") if path.is_file()
    }
    assert actual_paths == expected_paths, (
        "Core archive source contains missing or additional files"
    )


@contextmanager
def actual_core():
    names = (
        "DPM_ACTUAL_CORE_URL",
        "DPM_ACTUAL_CORE_SOURCE_DIR",
        "DPM_ACTUAL_CORE_PYTHON",
        "DPM_ACTUAL_CORE_DSN",
        "DPM_ACTUAL_CORE_ARCHIVE",
    )
    values = {name: os.environ.get(name, "").strip() for name in names}
    if not any(values.values()) and os.environ.get("DPM_ACTUAL_CORE_REQUIRED") != "1":
        pytest.skip("Actual Core cohort runtime was not requested; no upstream proof ran")
    missing = [name for name, value in values.items() if not value]
    assert not missing, f"Actual Core prerequisite missing: {', '.join(missing)}"
    source = Path(values["DPM_ACTUAL_CORE_SOURCE_DIR"]).resolve(strict=True)
    python = Path(values["DPM_ACTUAL_CORE_PYTHON"]).resolve(strict=True)
    assert not (source / ".git").exists(), "Use an immutable archive, not a shared checkout"
    _verify_source_archive(source, Path(values["DPM_ACTUAL_CORE_ARCHIVE"]).resolve(strict=True))
    for path, expected in _CORE_BLOBS.items():
        # Windows git archive honors core.autocrlf. The full archive comparison above
        # remains byte-exact; this supplementary check compares canonical Git blobs.
        content = (source / path).read_bytes().replace(b"\r\n", b"\n")
        blob = hashlib.sha1(b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest()
        assert blob == expected, f"Core producer differs from {CORE_REVISION}: {path}"
    url = urlparse(values["DPM_ACTUAL_CORE_URL"])
    assert url.scheme == "http" and url.hostname == "127.0.0.1" and url.port
    connection = conninfo_to_dict(values["DPM_ACTUAL_CORE_DSN"])
    assert connection.get("host") == "127.0.0.1", (
        "Only the isolated local proof database is allowed"
    )
    assert re.fullmatch(r"manage_actual_core_715_[0-9a-f]{32}", connection.get("dbname", ""))
    with psycopg.connect(values["DPM_ACTUAL_CORE_DSN"]) as observer:
        observer.execute("SET TRANSACTION READ ONLY")
        owner = observer.execute(
            "SELECT shobj_description(oid, 'pg_database') FROM pg_database "
            "WHERE datname=current_database()"
        ).fetchone()
        assert owner == (f"lotus-manage:715:{connection['dbname']}:{CORE_REVISION}",), (
            "Actual Core database lacks this proof's source-bound owner marker"
        )
    with httpx.Client(
        base_url=values["DPM_ACTUAL_CORE_URL"], timeout=30, trust_env=False
    ) as client:
        assert client.get("/health/ready").status_code == 200, "Actual Core is not ready"
        yield ActualCore(client, source, python, values["DPM_ACTUAL_CORE_DSN"])
