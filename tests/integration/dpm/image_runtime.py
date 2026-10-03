"""Run the unchanged application image by immutable ID on an owned loopback port."""

from __future__ import annotations

import json
import os
import subprocess
import time
import uuid
from contextlib import contextmanager

import httpx
from psycopg.conninfo import conninfo_to_dict, make_conninfo


def _docker(*args):
    return subprocess.check_output(["docker", *args], text=True, timeout=30).strip()


class ImageProcess:
    """The recovery cases' minimal process interface, backed by an owned container."""

    def __init__(self, container_id):
        self.pid = container_id

    def _state(self):
        return json.loads(_docker("inspect", self.pid))[0]["State"]

    def is_alive(self):
        return self._state()["Running"]

    @property
    def exitcode(self):
        state = self._state()
        return None if state["Running"] else state["ExitCode"]

    def kill(self):
        _docker("kill", "--signal=KILL", self.pid)

    def join(self, timeout):
        deadline = time.monotonic() + timeout
        while self.is_alive() and time.monotonic() < deadline:
            time.sleep(0.1)


@contextmanager
def image_api(dsn):
    image_id = os.environ["DPM_NETWORK_IMAGE_ID"]
    revision = os.environ["DPM_NETWORK_IMAGE_REVISION"]
    connection = conninfo_to_dict(dsn)
    assert connection.get("host") in {"localhost", "127.0.0.1"}, "Loopback database required"
    container_dsn = make_conninfo(dsn, host="host.docker.internal")
    owner = uuid.uuid4().hex
    container_id = _docker(
        "create",
        "--pull=never",
        "--label",
        f"lotus.validation_owner={owner}",
        "--publish",
        "127.0.0.1::8000",
        "--add-host",
        "host.docker.internal:host-gateway",
        "--env",
        "APP_PERSISTENCE_PROFILE=LOCAL",
        "--env",
        f"DPM_MANAGE_POSTGRES_DSN={container_dsn}",
        "--env",
        f"DPM_SUPPORTABILITY_POSTGRES_DSN={container_dsn}",
        "--env",
        "DPM_ARTIFACT_STORE_MODE=PERSISTED",
        "--env",
        "DPM_SUPPORT_APIS_ENABLED=true",
        "--env",
        "DPM_ARTIFACTS_ENABLED=true",
        "--env",
        "ENTERPRISE_ENFORCE_AUTHZ=true",
        "--env",
        'ENTERPRISE_CAPABILITY_RULES_JSON={"POST /api/v1":"manage.write"}',
        image_id,
    )
    process = ImageProcess(container_id)
    try:
        # Separate creation/start so even a failed start has an exact cleanup target.
        _docker("start", container_id)
        inspected = json.loads(_docker("inspect", container_id))[0]
        assert inspected["Image"] == image_id
        assert inspected["Mounts"] == [], "Financial proof must not mount source or dependencies"
        port = inspected["NetworkSettings"]["Ports"]["8000/tcp"][0]["HostPort"]
        with httpx.Client(
            base_url=f"http://127.0.0.1:{port}", timeout=30, trust_env=False
        ) as client:
            deadline = time.monotonic() + 60
            while True:
                assert process.is_alive(), "Application image exited before readiness"
                try:
                    if client.get("/health/ready").status_code == 200:
                        break
                except httpx.TransportError:
                    pass
                assert time.monotonic() < deadline, "Application image readiness timed out"
                time.sleep(0.1)
            version = client.get("/version")
            assert version.status_code == 200
            assert version.json()["git_commit_sha"] == revision
            yield client, process
    finally:
        # The exact ID was returned by our run; never enumerate or prune shared resources.
        _docker("rm", "--force", "--volumes", container_id)
