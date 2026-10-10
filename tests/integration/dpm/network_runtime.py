"""Owned disposable PostgreSQL and native HTTP API (source-installed or image) runtime."""

from __future__ import annotations

import json
import multiprocessing
import os
import socket
import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass

import httpx
import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo
from psycopg.rows import dict_row

from src.infrastructure.postgres_migrations import apply_postgres_migrations
from tests.integration.dpm.postgres_prerequisite import postgres_dsn_or_skip


@dataclass(frozen=True)
class RiskRuntimeConfiguration:
    """Explicit proof inputs, not inherited credentials or arbitrary environment passthrough."""

    base_url: str
    capabilities_json: str
    consumer_identity: str
    policy_version: str
    posture: str = "header-trust"

    def environment(self) -> dict[str, str]:
        return {
            "DPM_RISK_BASE_URL": self.base_url,
            "DPM_RISK_REQUIRED_CAPABILITIES_JSON": self.capabilities_json,
            "DPM_RISK_CONSUMER_SERVICE_IDENTITY": self.consumer_identity,
            "ENTERPRISE_POLICY_VERSION": self.policy_version,
            "PRINCIPAL_RESOLUTION_POSTURE": self.posture,
            "ENVIRONMENT": "local",
        }


@contextmanager
def disposable_database():
    dsn = postgres_dsn_or_skip("native HTTP/API-process recovery")
    name = f"manage_network_{uuid.uuid4().hex}"
    with psycopg.connect(dsn, autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
        try:
            isolated = make_conninfo(dsn, dbname=name)
            with psycopg.connect(isolated, row_factory=dict_row) as connection:
                apply_postgres_migrations(connection=connection, namespace="dpm")
            yield isolated
        finally:
            # Only this successfully created UUID database is eligible for removal.
            admin.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))
            assert (
                admin.execute("SELECT 1 FROM pg_database WHERE datname=%s", (name,)).fetchone()
                is None
            )


def _serve(
    dsn,
    pipe,
    stop,
    core_url=None,
    risk_config=None,
    composite_config=None,
    composite_read_grants=None,
    institutional_config=None,
    historical_test_admission=False,
    historical_config=None,
):
    # Spawned interpreters do not inherit parent's in-process dependency overrides.
    for name in list(os.environ):
        if name.startswith(("DPM_", "ENTERPRISE_", "APP_")):
            del os.environ[name]
    os.environ.update(
        APP_PERSISTENCE_PROFILE="LOCAL",
        DPM_MANAGE_POSTGRES_DSN=dsn,
        DPM_SUPPORTABILITY_POSTGRES_DSN=dsn,
        DPM_ARTIFACT_STORE_MODE="PERSISTED",
        DPM_SUPPORT_APIS_ENABLED="true",
        DPM_ARTIFACTS_ENABLED="true",
        ENTERPRISE_ENFORCE_AUTHZ="true",
        ENTERPRISE_CAPABILITY_RULES_JSON=json.dumps({"POST /api/v1": "manage.write"}),
    )
    if core_url is not None:
        os.environ.update(
            DPM_STATEFUL_CORE_SOURCING_ENABLED="true",
            DPM_CAP_INPUT_MODE_PORTFOLIO_ID_ENABLED="true",
            DPM_CORE_BASE_URL=core_url,
            DPM_CORE_RESOLVER_MAX_ATTEMPTS="1",
        )
    if risk_config is not None:
        os.environ.update(risk_config.environment())
    if composite_config is not None:
        os.environ["DPM_COMPOSITE_SOURCES_JSON"] = composite_config
    if composite_read_grants is not None:
        os.environ["DPM_COMPOSITE_READ_SERVICE_GRANTS_JSON"] = composite_read_grants
    if institutional_config is not None:
        os.environ["DPM_COMPOSITE_ATTESTATION_VERIFICATION_JSON"] = institutional_config
    if historical_config is not None:
        os.environ["DPM_COMPOSITE_HISTORICAL_POLICY_ADMISSION_JSON"] = historical_config
    import uvicorn
    from src.api.main import app

    assert not app.dependency_overrides
    if historical_test_admission:
        from tests.integration.dpm.composites.historical_test_application import configure_app

        configure_app(app)
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", log_level="warning"))
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        pipe.send(listener.getsockname()[1])
        pipe.close()

        def shutdown():
            stop.wait()
            server.should_exit = True

        threading.Thread(target=shutdown, daemon=True).start()
        server.run(sockets=[listener])


@contextmanager
def native_api(
    dsn,
    *,
    core_url=None,
    risk_config: RiskRuntimeConfiguration | None = None,
    composite_config: str | None = None,
    composite_read_grants: str | None = None,
    institutional_config: str | None = None,
    historical_test_admission: bool = False,
    historical_config: str | None = None,
):
    if os.environ.get("DPM_NETWORK_IMAGE_ID"):
        if historical_test_admission or any(
            value is not None
            for value in (
                core_url,
                risk_config,
                composite_config,
                composite_read_grants,
                institutional_config,
                historical_config,
            )
        ):
            raise ValueError("Controlled source proof requires the native installed API.")
        from tests.integration.dpm.image_runtime import image_api

        with image_api(dsn) as runtime:
            yield runtime
        return
    context = multiprocessing.get_context("spawn")
    parent, child = context.Pipe(duplex=False)
    stop = context.Event()
    process = context.Process(
        target=_serve,
        args=(
            dsn,
            child,
            stop,
            core_url,
            risk_config,
            composite_config,
            composite_read_grants,
            institutional_config,
            historical_test_admission,
            historical_config,
        ),
    )
    process.start()
    child.close()
    port = None
    try:
        assert parent.poll(45), "Native API did not publish its bound port"
        port = parent.recv()
        with httpx.Client(
            base_url=f"http://127.0.0.1:{port}", timeout=30, trust_env=False
        ) as client:
            deadline = time.monotonic() + 45
            while True:
                assert process.is_alive(), "Native API exited before readiness"
                try:
                    if client.get("/health/ready").status_code == 200:
                        break
                except httpx.TransportError:
                    pass
                assert time.monotonic() < deadline, "Native API readiness timed out"
                time.sleep(0.1)
            yield client, process
    finally:
        parent.close()
        # A killed process can leave multiprocessing.Event's lock held. Never
        # signal that shared primitive after its owning process has terminated.
        if process.is_alive():
            stop.set()
        process.join(15)
        if process.is_alive():
            process.kill()
            process.join(10)
        assert not process.is_alive(), "Owned API process was not removed"
        process.close()
        if port is not None:
            with socket.socket() as probe:
                probe.settimeout(1)
                assert probe.connect_ex(("127.0.0.1", port)) != 0, "Owned listener survived"
