"""Native HTTP and independent PostgreSQL sessions prove serialized source admission."""

from concurrent.futures import ThreadPoolExecutor
from threading import Event
import time
import uuid

import psycopg

from tests.integration.dpm.controlled_core import controlled_core, controlled_products
from tests.integration.dpm.controlled_mandate_sources import mandate_sources
from tests.integration.dpm.network_runtime import disposable_database, native_api
from tests.integration.dpm.waves.test_source_bound_wave_network import (
    _assert_financial_artifact,
    _call,
    _checked_wave,
    _headers,
    _input,
)


def test_concurrent_http_admission_freezes_one_source_revision_and_replays_winner():
    portfolio, tenant = f"wave-{uuid.uuid4().hex}", f"tenant-{uuid.uuid4().hex}"
    enabled, resolving, release = Event(), Event(), Event()
    overrides = mandate_sources(portfolio)

    def hold_binding(path, _payload):
        if enabled.is_set() and path.endswith("/mandate-binding"):
            resolving.set()
            assert release.wait(2), "Controller did not release owned source response"

    with controlled_core(
        portfolio=portfolio,
        starting_shares=975,
        product_overrides=overrides,
        response_hook=hold_binding,
    ) as (core_url, observations):
        with disposable_database() as dsn, native_api(dsn, core_url=core_url) as (client, _process):
            wave = _checked_wave(client, portfolio, tenant)
            path = f"/api/v1/rebalance/waves/{wave['wave_id']}/simulation-operations"
            headers, body = _headers(tenant), _input(wave)
            before = observations.qsize()
            enabled.set()
            with ThreadPoolExecutor(max_workers=2) as pool:
                first = pool.submit(_call, client, "POST", path, headers, body, 202)
                assert resolving.wait(5)
                second = pool.submit(_call, client, "POST", path, headers, body, 202)
                try:
                    with psycopg.connect(dsn, autocommit=True) as observer:
                        deadline = time.monotonic() + 1.5
                        blocked = False
                        while time.monotonic() < deadline:
                            blocked = observer.execute(
                                "SELECT EXISTS (SELECT 1 FROM pg_stat_activity "
                                "WHERE datname=current_database() AND wait_event='advisory')"
                            ).fetchone()[0]
                            if blocked:
                                break
                            time.sleep(0.02)
                        assert blocked, "Second admission must wait on the database-wide key guard"
                    # First response already owns version 7. A second resolution would see 8/conflict.
                    changed = controlled_products(portfolio)["mandate-binding"]
                    changed["binding_version"] = 8
                    overrides["mandate-binding"] = changed
                finally:
                    release.set()
                admitted, replay = first.result(10), second.result(10)
            assert admitted["operation_id"] == replay["operation_id"]
            assert (admitted["idempotent_replay"], replay["idempotent_replay"]) == (False, True)
            resolved_calls = list(observations.queue)[before:]
            assert (
                sum(path.endswith("/mandate-binding") for path, _body, _tenant in resolved_calls)
                == 1
            )
            op_path = f"/api/v1/rebalance/waves/simulation-operations/{admitted['operation_id']}"
            worked = _call(
                client, "POST", f"{op_path}/work", headers, {"worker_id": "worker", "max_items": 1}
            )
            assert (worked["completed_count"], worked["failed_count"]) == (1, 0)
            results = _call(client, "GET", f"{op_path}/results", headers)
            _assert_financial_artifact(
                client, headers, results["items"][0]["alternative_set_id"], "0.02"
            )
            with psycopg.connect(dsn) as observer:
                observer.execute("SET TRANSACTION READ ONLY")
                assert observer.execute(
                    "SELECT count(*) FROM dpm_wave_simulation_operations"
                ).fetchone() == (1,)
                assert observer.execute(
                    "SELECT count(*) FROM dpm_wave_simulation_items"
                ).fetchone() == (1,)
