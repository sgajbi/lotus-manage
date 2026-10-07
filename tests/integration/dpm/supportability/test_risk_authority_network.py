"""Source-pinned, registered Risk HTTP consumer pilot; not bank IAM or capacity proof."""

import hashlib
import json
import os
import subprocess
import tarfile
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from pathlib import Path
from dataclasses import replace
from urllib.parse import urlparse

import httpx
import psycopg
from psycopg.rows import dict_row
from psycopg.conninfo import conninfo_to_dict
import pytest

from tests.integration.dpm.network_runtime import (
    RiskRuntimeConfiguration,
    disposable_database,
    native_api,
)
from tests.shared.factories import valid_api_payload
from tests.integration.dpm.postgres_prerequisite import postgres_dsn_or_skip

RISK_REVISION = "067df854b05e2ea5e54e8409fa9efde22d9bb7d7"
RISK_ARCHIVE_SHA256 = "6292bf41c23780c8b62d5c6125ab1b5e7645892afff0bc7b3208cefe7fa410de"
CAPABILITIES = {
    "concentration": "risk.concentration",
    "regime_scenario": "risk.regime",
    "risk_event_cohort": "risk.cohort",
}
WAVES = "/api/v1/rebalance/waves"
GENERATE = "/api/v1/construction/alternative-sets/generate"


def _verify_export(source, archive):
    assert not (source / ".git").exists(), "A mutable checkout is not proof source"
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == RISK_ARCHIVE_SHA256
    expected = set()
    with tarfile.open(archive) as exported:
        assert exported.pax_headers["comment"] == RISK_REVISION
        for member in exported:
            if member.isdir():
                continue
            assert member.isfile()
            path = (source / member.name).resolve(strict=True)
            assert path.is_relative_to(source)
            expected.add(member.name)
            with exported.extractfile(member) as content:
                assert path.read_bytes() == content.read(), member.name
    assert {p.relative_to(source).as_posix() for p in source.rglob("*") if p.is_file()} == expected


@pytest.fixture
def actual_risk():
    names = (
        "DPM_ACTUAL_RISK_URL",
        "DPM_ACTUAL_RISK_SOURCE_DIR",
        "DPM_ACTUAL_RISK_ARCHIVE",
        "DPM_ACTUAL_RISK_AUDIT",
    )
    values = {name: os.getenv(name, "").strip() for name in names}
    if not any(values.values()) and os.getenv("DPM_ACTUAL_RISK_REQUIRED") != "1":
        pytest.skip("Source-pinned actual Risk runtime not requested; no producer proof ran")
    assert all(values.values()), "Incomplete actual Risk proof prerequisites"
    source = Path(values[names[1]]).resolve(strict=True)
    archive = Path(values[names[2]]).resolve(strict=True)
    audit = Path(values[names[3]]).resolve(strict=True)
    url = urlparse(values[names[0]])
    assert url.scheme == "http" and url.hostname == "127.0.0.1" and url.port
    _verify_export(source, archive)
    try:
        with httpx.Client(base_url=values[names[0]], timeout=30, trust_env=False) as client:
            assert client.get("/health/ready").status_code == 200
            yield (
                client,
                RiskRuntimeConfiguration(
                    base_url=values[names[0]],
                    capabilities_json=json.dumps(CAPABILITIES),
                    consumer_identity="manage-local-consumer",
                    policy_version="synthetic-risk-pilot-v1",
                ),
                audit,
            )
    finally:
        _verify_export(source, archive)


def _headers(tenant, *, actor="risk-pm", grants=True):
    return {
        "X-Tenant-Id": tenant,
        "X-Actor-Id": actor,
        "X-Role": "PM",
        "X-Service-Identity": "synthetic-caller-not-forwarded",
        "X-Correlation-Id": uuid.uuid4().hex,
        "Idempotency-Key": uuid.uuid4().hex,
        "X-Capabilities": "manage.write"
        + (",risk.concentration,risk.regime,risk.cohort" if grants else ""),
    }


def _call(client, method, path, headers, body=None, expected=200):
    response = client.request(method, path, headers=headers, json=body)
    assert response.status_code == expected, response.text
    return response.json()


def _financial_request(portfolio):
    payload = valid_api_payload()
    payload["portfolio_snapshot"].update(
        portfolio_id=portfolio,
        base_currency="USD",
        positions=[{"instrument_id": "EQ_1", "quantity": "975"}],
        cash_balances=[{"currency": "USD", "amount": "2500"}],
    )
    payload["market_data_snapshot"] = {
        "snapshot_id": "risk-proof-2026-05-10",
        "prices": [{"instrument_id": "EQ_1", "price": "100", "currency": "USD"}],
        "fx_rates": [],
    }
    payload["model_portfolio"]["targets"] = [{"instrument_id": "EQ_1", "weight": "1"}]
    payload["shelf_entries"] = [
        {"instrument_id": "EQ_1", "status": "APPROVED", "asset_class": "EQUITY"}
    ]
    payload["options"] = {
        "min_cash_buffer_pct": "0.02",
        "enable_settlement_awareness": False,
        "enable_tax_awareness": False,
    }
    return payload


def _construction_request(portfolio):
    return {
        "input_mode": "stateless",
        "stateless_input": _financial_request(portfolio),
        "methods": ["RISK_AWARE", "REGIME_STRESS_AWARE"],
    }


def _event_request(portfolio):
    return {
        "trigger_type": "RISK_EVENT",
        "trigger_id": uuid.uuid4().hex,
        "rationale": "Synthetic protected Risk consumer proof",
        "as_of_date": "2026-05-10",
        "actor_id": "risk-pm",
        "risk_event_id": "RISK_EVENT_2026_Q2_RATES_UP",
        "minimum_impact_score": "0.05",
        "portfolios": [
            {
                "portfolio_id": portfolio,
                "mandate_id": "mandate-proof",
                "exposure_weights": {"EQUITY": "0.55", "FIXED_INCOME": "0.35", "CASH": "0.10"},
                "source_refs": [
                    {
                        "source_system": "synthetic-proof",
                        "source_type": "DPM_SOURCE_READINESS",
                        "source_id": "synthetic-source-ready",
                        "source_version": "v1",
                        "supportability_state": "READY",
                    }
                ],
            },
            {
                "portfolio_id": portfolio + "-excluded",
                "exposure_weights": {"FIXED_INCOME": "0.10", "CASH": "0.90"},
            },
        ],
    }


def _assert_financial_results(client, owned, headers):
    for row in owned["alternatives"]:
        result = _call(
            client, "GET", f"/api/v1/rebalance/runs/{row['rebalance_run_id']}/artifact", headers
        )["result"]
        assert Decimal(result["before"]["total_value"]["amount"]) == 100000
        shares = 300 if row["method"] == "RISK_AWARE" else 980
        cash = 70000 if row["method"] == "RISK_AWARE" else 2000
        assert Decimal(result["after_simulated"]["positions"][0]["quantity"]) == shares
        assert Decimal(result["after_simulated"]["cash_balances"][0]["amount"]) == cash
        assert shares * 100 + cash == 100000
        reasons = row["diagnostics"]["enrichment_summary"]["reason_codes"]
        assert (
            "RISK_AUTHORITY_NOT_CONNECTED" not in reasons
            if row["method"] == "RISK_AWARE"
            else "REGIME_SCENARIO_PACK_UNAVAILABLE" not in reasons
        )
        assert row["method_status"] != "READY", (
            "Missing issuer or breached stress threshold must remain qualified"
        )
        _call(
            client,
            "GET",
            f"/api/v1/rebalance/runs/{row['rebalance_run_id']}/artifact",
            {**headers, "X-Tenant-Id": "foreign"},
            expected=404,
        )


def test_registered_risk_three_operation_consumer_and_admission_denials(
    actual_risk, record_testsuite_property
):
    risk, config, audit = actual_risk
    tenant, portfolio = "risk-" + uuid.uuid4().hex, "risk-portfolio-" + uuid.uuid4().hex
    headers = _headers(tenant)
    with disposable_database() as dsn, native_api(dsn, risk_config=config) as (client, _):
        owned = _call(client, "POST", GENERATE, headers, _construction_request(portfolio))
        _assert_financial_results(client, owned, headers)
        request = _event_request(portfolio)
        preview = _call(client, "POST", WAVES + "/preview", headers, request)
        created = _call(client, "POST", WAVES, headers, request, expected=201)
        assert [item["portfolio_id"] for item in preview["wave"]["items"]] == [portfolio]
        assert [item["portfolio_id"] for item in created["wave"]["items"]] == [portfolio]
        _call(client, "POST", WAVES, headers, request, expected=201)
        _call(
            client,
            "GET",
            WAVES + "/" + created["wave"]["wave_id"],
            {**headers, "X-Tenant-Id": "foreign"},
            expected=404,
        )
        _call(
            client,
            "POST",
            WAVES,
            _headers(tenant, grants=False),
            _event_request(portfolio),
            expected=503,
        )
        _call(client, "POST", WAVES, {**headers, "X-Actor-Id": ""}, request, expected=403)
        _call(client, "POST", WAVES, {**headers, "X-Tenant-Id": ""}, request, expected=403)
        with psycopg.connect(dsn, row_factory=dict_row) as observer:
            observer.execute("SET TRANSACTION READ ONLY")
            assert (
                observer.execute("SELECT count(*) AS count FROM dpm_rebalance_waves").fetchone()[
                    "count"
                ]
                == 1
            )

        def interleave(actor):
            admitted = _headers(tenant + "-" + actor, actor=actor)
            _call(
                client, "POST", GENERATE, admitted, _construction_request(portfolio + "-" + actor)
            )
            return admitted

        with ThreadPoolExecutor(max_workers=4) as workers:
            identities = list(workers.map(interleave, ["caller-A", "caller-B"]))
        observations = [json.loads(line) for line in audit.read_text(encoding="utf-8").splitlines()]
        for admitted in identities:
            matches = [
                row
                for row in observations
                if row.get("correlation_id") == admitted["X-Correlation-Id"]
            ]
            assert len(matches) == 2
            assert all(
                row["actor_id"] == admitted["X-Actor-Id"]
                and row["tenant_id"] == admitted["X-Tenant-Id"]
                for row in matches
            )

    # Independent figure controls use actual registered producer, not Manage/Risk calculation helpers.
    source_headers = {**headers, "X-Capabilities": "risk.cohort"}
    body = {key: request[key] for key in ("risk_event_id", "as_of_date", "minimum_impact_score")}
    body["portfolios"] = [
        {key: row[key] for key in ("portfolio_id", "exposure_weights")}
        for row in request["portfolios"]
    ]
    cohort = _call(
        risk, "POST", "/analytics/risk/risk-event-cohorts/evaluate", source_headers, body
    )
    assert Decimal(str(cohort["affected_portfolios"][0]["impact_score"])) == Decimal("0.0745")
    assert Decimal(str(cohort["excluded_portfolios"][0]["impact_score"])) == Decimal("0.015")
    assert cohort["metadata"]["request_fingerprint"]
    record_testsuite_property("risk_cohort_response", json.dumps(cohort, sort_keys=True))
    _call(
        risk,
        "POST",
        "/analytics/risk/risk-event-cohorts/evaluate",
        {**source_headers, "X-Capabilities": "manage.write"},
        body,
        expected=403,
    )
    concentration_input = {
        "input_mode": "stateless",
        "issuer_grouping_level": "ultimate_parent",
        "enrichment_policy": "use_caller_only",
        "stateless_input": {
            "current_positions": [
                {
                    "security_id": "EQ_1",
                    "quantity": "975",
                    "market_value_base": "97500",
                    "weight": "0.975",
                }
            ],
            "projected_positions": [
                {
                    "security_id": "EQ_1",
                    "proposed_quantity": "980",
                    "projected_market_value_base": "98000",
                    "projected_weight": "0.98",
                }
            ],
            "top_n": 10,
        },
    }
    concentration = _call(
        risk,
        "POST",
        "/analytics/risk/concentration",
        {**headers, "X-Capabilities": "risk.concentration"},
        concentration_input,
    )
    # One security, normalized over securities (cash is not an issuer): 1^2 * 10000.
    assert concentration["source_service"] == "lotus-risk"
    assert concentration["metadata"]["product_name"] == "ConcentrationRiskReport"
    assert concentration["metadata"]["product_version"] == "v1"
    assert concentration["metadata"]["source_services"] == ["lotus-risk"]
    assert concentration["metadata"]["request_fingerprint"]
    assert concentration["risk_proxy"]["hhi_current"] == 10000
    assert concentration["risk_proxy"]["hhi_proposed"] == 10000
    assert concentration["risk_proxy"]["hhi_delta"] == 0
    assert concentration["single_position_concentration"]["top_position_weight_proposed"] == 1
    assert concentration["issuer_concentration"]["coverage_status"] == "unavailable"
    record_testsuite_property(
        "risk_concentration_response", json.dumps(concentration, sort_keys=True)
    )
    regime_input = {
        "scenario_pack_id": "CIO_REGIME_2026_Q2",
        "portfolio_id": portfolio,
        "as_of_date": "2026-05-10",
        "maximum_allowed_loss_pct": 0.12,
        "exposures": [{"bucket": "EQUITY", "weight": 0.98}, {"bucket": "CASH", "weight": 0.02}],
    }
    regime = _call(
        risk,
        "POST",
        "/analytics/risk/regime-scenario-pack/evaluate",
        {**headers, "X-Capabilities": "risk.regime"},
        regime_input,
    )
    # Worst pack shock: equity -18%, cash 0%; .98 * .18 = .1764 > .12.
    assert Decimal(str(regime["worst_case_loss_pct"])) == Decimal("0.1764")
    assert Decimal(str(regime["maximum_allowed_loss_pct"])) == Decimal("0.12")
    assert regime["metadata"]["source_service"] == "lotus-risk"
    assert regime["metadata"]["request_fingerprint"]
    record_testsuite_property("risk_regime_response", json.dumps(regime, sort_keys=True))


def _synthetic_checked_wave(client, tenant, portfolio, headers):
    # Explicit CALLER_SUPPLIED health evidence, not a bank/Core mandate grant.
    twin = {
        "mandate_id": "mandate-proof",
        "portfolio_id": portfolio,
        "mandate_version": "synthetic-v1",
        "as_of_date": "2026-05-10",
        "source_system": "synthetic-caller-health-input",
        "base_currency": "USD",
        "reference_currency": "USD",
        "risk_profile": "BALANCED",
        "investment_objective": "synthetic-proof",
        "time_horizon": "LONG_TERM",
        "model_portfolio_id": "synthetic-model",
        "constraints": {
            "cash_band_min_weight": "0",
            "cash_band_max_weight": "1",
            "turnover_budget_applicable": False,
        },
        "review_policy": {"next_review_due_date": "2026-12-31"},
    }
    health = _call(
        client,
        "POST",
        f"/api/v1/mandates/mandate-proof/health/recalculate?tenant_id={tenant}",
        headers,
        {
            "twin": twin,
            "current_weights": {"EQ_1": "0.975"},
            "target_weights": {"EQ_1": "1"},
            "cash_weight": "0.025",
        },
    )
    assert health["health_state"] == "READY", health
    created = _call(
        client,
        "POST",
        WAVES,
        headers,
        {
            "trigger_type": "EXPLICIT_PORTFOLIO_LIST",
            "trigger_id": uuid.uuid4().hex,
            "rationale": "Synthetic retained authority proof",
            "as_of_date": "2026-05-10",
            "actor_id": "risk-pm",
            "portfolios": [{"portfolio_id": portfolio, "mandate_id": "mandate-proof"}],
        },
        expected=201,
    )
    wave = _call(
        client,
        "POST",
        f"{WAVES}/{created['wave']['wave_id']}/source-check",
        headers,
        {"actor_id": "risk-pm"},
    )["wave"]
    assert wave["items"][0]["state"] == "SOURCE_READY", wave
    return wave


def _custody(dsn, operation_id):
    with psycopg.connect(dsn, row_factory=dict_row) as connection:
        connection.execute("SET TRANSACTION READ ONLY")
        return connection.execute(
            "SELECT actor_id, tenant_id, correlation_id, request_hash, risk_authority_context_json, risk_authority_context_hash FROM dpm_wave_simulation_operations WHERE operation_id=%s",
            (operation_id,),
        ).fetchone()


def _restart_owned_postgres(dsn):
    """Fault injection only for an explicitly reserved, label-checked disposable database."""
    assert os.getenv("DPM_ACTUAL_RISK_RESTART_POSTGRES") == "1"
    container = os.environ["DPM_ACTUAL_RISK_POSTGRES_CONTAINER"]
    owner = os.environ["DPM_ACTUAL_RISK_POSTGRES_OWNER"]
    assert owner.startswith("lotus-manage:") and len(owner) > 30
    inspected = json.loads(
        subprocess.run(
            ["docker", "inspect", container], check=True, capture_output=True, text=True
        ).stdout
    )[0]
    assert inspected["Config"]["Labels"]["lotus.proof.owner"] == owner
    assert inspected["Config"]["Labels"]["lotus.proof.risk_revision"] == RISK_REVISION
    connection = conninfo_to_dict(dsn)
    bindings = inspected["NetworkSettings"]["Ports"]["5432/tcp"]
    assert bindings == [{"HostIp": "127.0.0.1", "HostPort": connection["port"]}]
    assert connection["host"] == "127.0.0.1"
    assert "POSTGRES_DB=" + connection["dbname"] in inspected["Config"]["Env"]
    subprocess.run(
        ["docker", "restart", "--time", "10", inspected["Id"]],
        check=True,
        capture_output=True,
        text=True,
    )
    deadline = time.monotonic() + 40
    while True:
        try:
            with psycopg.connect(dsn, connect_timeout=2) as database:
                assert database.execute("SELECT 1").fetchone() == (1,)
            break
        except psycopg.OperationalError:
            assert time.monotonic() < deadline, "Owned PostgreSQL did not recover"
            time.sleep(0.1)
    return inspected["Id"]


def test_registered_durable_risk_context_after_api_and_postgres_restart(
    actual_risk, record_testsuite_property
):
    _, config, audit = actual_risk
    # Primary DB is wholly disposable/owned. No disposable_database admin connection
    # spans this PostgreSQL restart; no foreign/canonical resource is eligible.
    dsn = postgres_dsn_or_skip("actual Risk durable API/database recovery")
    tenant, portfolio = "risk-recovery-" + uuid.uuid4().hex, "risk-pf-" + uuid.uuid4().hex
    headers = _headers(tenant)
    with native_api(dsn, risk_config=config) as (client, original):
        original_pid = original.pid
        wave = _synthetic_checked_wave(client, tenant, portfolio, headers)
        path = f"{WAVES}/{wave['wave_id']}/simulation-operations"
        body = {
            "actor_id": "risk-pm",
            "methods": ["RISK_AWARE", "REGIME_STRESS_AWARE"],
            "item_inputs": [
                {
                    "wave_item_id": wave["items"][0]["wave_item_id"],
                    "input_mode": "stateless",
                    "stateless_input": _financial_request(portfolio),
                }
            ],
        }
        admitted = _call(client, "POST", path, headers, body, expected=202)
        retained = _custody(dsn, admitted["operation_id"])
        context = retained["risk_authority_context_json"]
        assert context["actor_id"] == retained["actor_id"] == "risk-pm"
        assert context["tenant_id"] == retained["tenant_id"] == tenant
        assert context["correlation_id"] == headers["X-Correlation-Id"]
        assert context["authority_basis"] == "caller_asserted_header_trust"
        assert context["service_identity"] == config.consumer_identity
        assert "Authorization" not in json.dumps(context)
        # Independent canonical SHA-256 custody control, not model fingerprint helper.
        canonical = json.dumps(context, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        assert (
            retained["risk_authority_context_hash"]
            == "sha256:" + hashlib.sha256(canonical.encode()).hexdigest()
        )
        original.kill()
        original.join(10)
        assert not original.is_alive() and original.exitcode != 0
    record_testsuite_property("restarted_postgres_container_id", _restart_owned_postgres(dsn))
    assert _custody(dsn, admitted["operation_id"]) == retained
    operation_path = f"{WAVES}/simulation-operations/{admitted['operation_id']}"
    worker = _headers(tenant, actor="replacement-worker", grants=False)
    with native_api(dsn, risk_config=config) as (client, replacement):
        assert replacement.pid != original_pid
        _call(client, "GET", operation_path, {**worker, "X-Tenant-Id": "foreign"}, expected=404)
        worked = _call(
            client,
            "POST",
            operation_path + "/work",
            worker,
            {"worker_id": "replacement-worker", "max_items": 1},
        )
        assert (worked["completed_count"], worked["failed_count"]) == (1, 0), worked
        results = _call(client, "GET", operation_path + "/results", worker)
        alternative_id = results["items"][0]["alternative_set_id"]
        alternatives = _call(
            client, "GET", "/api/v1/construction/alternative-sets/" + alternative_id, worker
        )
        _assert_financial_results(client, alternatives, worker)
        assert _call(client, "POST", path, headers, body, expected=202)["idempotent_replay"]
        assert _custody(dsn, admitted["operation_id"]) == retained
    matches = [
        json.loads(line)
        for line in audit.read_text(encoding="utf-8").splitlines()
        if json.loads(line).get("correlation_id")
        == f"{admitted['operation_id']}:{wave['items'][0]['wave_item_id']}"
    ]
    assert len(matches) == 2, matches
    assert all(row["actor_id"] == "risk-pm" and row["tenant_id"] == tenant for row in matches)
    record_testsuite_property("retained_risk_context_hash", retained["risk_authority_context_hash"])
    record_testsuite_property("original_admission_correlation", retained["correlation_id"])
    record_testsuite_property("risk_worker_audit", json.dumps(matches, sort_keys=True))


@pytest.mark.parametrize("failure", ["missing_mapping", "verified"])
def test_registered_risk_unconfigured_and_verified_postures_refuse(actual_risk, failure):
    _, config, audit = actual_risk
    config = (
        replace(config, capabilities_json="{}")
        if failure == "missing_mapping"
        else replace(config, posture="verified")
    )
    tenant = "risk-denied-" + uuid.uuid4().hex
    headers = _headers(tenant)
    with disposable_database() as dsn, native_api(dsn, risk_config=config) as (client, _):
        _call(client, "POST", WAVES, headers, _event_request("denied-pf"), expected=503)
        with psycopg.connect(dsn) as observer:
            observer.execute("SET TRANSACTION READ ONLY")
            assert observer.execute("SELECT count(*) FROM dpm_rebalance_waves").fetchone() == (0,)
    assert not any(
        json.loads(line).get("correlation_id") == headers["X-Correlation-Id"]
        for line in audit.read_text(encoding="utf-8").splitlines()
    )
