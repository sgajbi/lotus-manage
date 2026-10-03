"""API-created waves with controlled source contracts; not live Core/IAM/capacity proof."""

from copy import deepcopy
from decimal import Decimal
import uuid

import psycopg
import pytest

from tests.integration.dpm.controlled_core import AS_OF, controlled_core, controlled_products
from tests.integration.dpm.controlled_mandate_sources import mandate_sources
from tests.integration.dpm.network_runtime import disposable_database, native_api


def _headers(tenant):
    return {
        "X-Tenant-Id": tenant,
        "X-Actor-Id": "wave-pm",
        "X-Role": "PM",
        "X-Service-Identity": "local-source-wave-proof",
        "X-Capabilities": "manage.write",
        "Idempotency-Key": uuid.uuid4().hex,
        "X-Correlation-Id": uuid.uuid4().hex,
    }


def _call(client, method, path, headers, body=None, expected=200):
    response = client.request(method, path, headers=headers, json=body)
    assert response.status_code == expected, response.text
    return response.json()


def _checked_wave(client, portfolio, tenant, *, complete_health=True):
    refreshed = _call(
        client,
        "POST",
        "/api/v1/mandates/mandate-reserve/refresh-from-core",
        _headers(tenant),
        {"portfolio_id": portfolio, "tenant_id": tenant, "as_of_date": AS_OF},
    )
    assert refreshed["health_snapshot"]["health_state"] == "PENDING_REVIEW"
    assert refreshed["health_snapshot"]["source_readiness_state"] == "READY"
    twin = deepcopy(refreshed["mandate"])
    # A separate, explicit CALLER_SUPPLIED synthetic mandate completes the health
    # prerequisites. This is not a claim that Core supplied cash-band/turnover limits.
    twin["source_system"] = "controlled-caller-health-input"
    twin["constraints"].update(
        cash_band_min_weight="0", cash_band_max_weight="1", turnover_budget_applicable=False
    )
    twin["field_gap_codes"] = []
    if complete_health:
        health = _call(
            client,
            "POST",
            f"/api/v1/mandates/mandate-reserve/health/recalculate?tenant_id={tenant}",
            _headers(tenant),
            {
                "twin": twin,
                "current_weights": {"EQ_1": "0.975"},
                "target_weights": {"EQ_1": "1"},
                "cash_weight": "0.025",
            },
        )
        assert health["health_state"] == "READY", health["top_reasons"]
    created = _call(
        client,
        "POST",
        "/api/v1/rebalance/waves",
        _headers(tenant),
        {
            "trigger_type": "EXPLICIT_PORTFOLIO_LIST",
            "trigger_id": uuid.uuid4().hex,
            "rationale": "Source-bound mandate reserve validation",
            "as_of_date": AS_OF,
            "actor_id": "wave-pm",
            "portfolios": [{"portfolio_id": portfolio, "mandate_id": "mandate-reserve"}],
        },
        expected=201,
    )
    wave_id = created["wave"]["wave_id"]
    checked = _call(
        client,
        "POST",
        f"/api/v1/rebalance/waves/{wave_id}/source-check",
        _headers(tenant),
        {"actor_id": "wave-pm"},
    )["wave"]
    assert checked["state"] == "SOURCE_CHECKED"
    assert checked["items"][0]["state"] == (
        "SOURCE_READY" if complete_health else "REVIEW_REQUIRED"
    ), checked
    return checked


def _input(wave):
    return {
        "actor_id": "wave-pm",
        "methods": ["HEURISTIC_EXPLAINABLE"],
        "item_inputs": [
            {
                "wave_item_id": wave["items"][0]["wave_item_id"],
                "input_mode": "stateful",
                "options_override": {
                    "enable_settlement_awareness": False,
                    "enable_tax_awareness": False,
                },
            }
        ],
    }


def _assert_financial_artifact(client, headers, alternative_set_id, reserve):
    alternatives = _call(
        client, "GET", f"/api/v1/construction/alternative-sets/{alternative_set_id}", headers
    )
    alternative = alternatives["alternatives"][0]
    rid = alternative["rebalance_run_id"]
    artifact = _call(client, "GET", f"/api/v1/rebalance/runs/{rid}/artifact", headers)
    result = artifact["result"]
    assert Decimal(result["before"]["total_value"]["amount"]) == 100000
    target = Decimal(reserve) if reserve is not None else Decimal("0")
    shares, cash = (1 - target) * 1000, target * 100000
    assert Decimal(result["after_simulated"]["positions"][0]["quantity"]) == shares
    assert Decimal(result["after_simulated"]["cash_balances"][0]["amount"]) == cash
    assert shares * 100 + cash == 100000
    changes = alternative["diagnostics"]["proposed_changes"]
    assert len(changes) == 1 and changes[0]["action"] == ("BUY" if shares > 975 else "SELL")
    assert Decimal(changes[0]["quantity"]) == abs(shares - 975)
    lineage = result["lineage"]
    assert lineage["source_mandate_binding_version"] == 7
    if reserve is None:
        assert lineage["source_cash_reserve_target_weight"] is None
        assert not any(row["rule_id"] == "CASH_RESERVE_TARGET" for row in result["rule_results"])
    else:
        assert Decimal(lineage["source_cash_reserve_target_weight"]) == target
    assert lineage["source_cash_reserve_authority"] == "MANDATE_BINDING"
    assert lineage["source_cash_reserve_consumer_override_allowed"] is False
    assert lineage["source_mandate_effective_from"] == "2026-04-01"
    assert lineage["source_mandate_effective_to"] == "2026-04-30"
    return rid, artifact


@pytest.mark.parametrize("durable", [False, True])
@pytest.mark.parametrize("reserve", ["0.02", "0", None, "0.5"])
def test_source_bound_wave_financials_and_frozen_replay(durable, reserve):
    portfolio, tenant = f"wave-source-{uuid.uuid4().hex}", f"tenant-{uuid.uuid4().hex}"
    overrides = mandate_sources(portfolio)
    with disposable_database() as dsn:
        with controlled_core(
            portfolio=portfolio, reserve=reserve, starting_shares=975, product_overrides=overrides
        ) as (core_url, observations):
            with native_api(dsn, core_url=core_url) as (client, _original):
                wave = _checked_wave(client, portfolio, tenant)
                headers, body = _headers(tenant), _input(wave)
                suffix = "simulation-operations" if durable else "simulate"
                path = f"/api/v1/rebalance/waves/{wave['wave_id']}/{suffix}"
                response = _call(
                    client, "POST", path, headers, body, expected=202 if durable else 200
                )
                source_requests = observations.qsize()
                if not durable:
                    rid, artifact = _assert_financial_artifact(
                        client, headers, response["wave"]["items"][0]["alternative_set_id"], reserve
                    )
                else:
                    assert response["status"] == "PENDING"
        # Producer is now unavailable. Durable work and both replay modes must use frozen evidence.
        with native_api(dsn, core_url=core_url) as (client, _replacement):
            if durable:
                operation_path = (
                    f"/api/v1/rebalance/waves/simulation-operations/{response['operation_id']}"
                )
                worked = _call(
                    client,
                    "POST",
                    f"{operation_path}/work",
                    headers,
                    {"worker_id": "replacement-source", "max_items": 1},
                )
                assert (worked["completed_count"], worked["failed_count"]) == (1, 0)
                results = _call(client, "GET", f"{operation_path}/results", headers)
                rid, artifact = _assert_financial_artifact(
                    client, headers, results["items"][0]["alternative_set_id"], reserve
                )
            replay = _call(client, "POST", path, headers, body, expected=202 if durable else 200)
            assert replay["idempotent_replay"] is True
            assert (
                _call(client, "GET", f"/api/v1/rebalance/runs/{rid}/artifact", headers) == artifact
            )
            _call(
                client,
                "GET",
                f"/api/v1/rebalance/runs/{rid}/artifact",
                {**headers, "X-Tenant-Id": "foreign"},
                expected=404,
            )
            if durable:
                changed = deepcopy(body)
                changed["item_inputs"][0]["options_override"]["min_cash_buffer_pct"] = "0.03"
                _call(client, "POST", path, headers, changed, expected=409)
        assert observations.qsize() == source_requests
        with psycopg.connect(dsn) as connection:
            connection.execute("SET TRANSACTION READ ONLY")
            for table in ("dpm_runs", "dpm_run_artifacts", "dpm_construction_alternative_sets"):
                assert connection.execute(f"SELECT count(*) FROM {table}").fetchone() == (1,)


@pytest.mark.parametrize("durable", [False, True])
def test_source_bound_wave_refuses_unreviewed_health_without_source_or_financial_writes(durable):
    portfolio, tenant = f"wave-source-{uuid.uuid4().hex}", f"tenant-{uuid.uuid4().hex}"
    with controlled_core(
        portfolio=portfolio, starting_shares=975, product_overrides=mandate_sources(portfolio)
    ) as (core_url, observations):
        with disposable_database() as dsn, native_api(dsn, core_url=core_url) as (client, _process):
            wave = _checked_wave(client, portfolio, tenant, complete_health=False)
            before = observations.qsize()
            suffix = "simulation-operations" if durable else "simulate"
            rejected = _call(
                client,
                "POST",
                f"/api/v1/rebalance/waves/{wave['wave_id']}/{suffix}",
                _headers(tenant),
                _input(wave),
                expected=422,
            )
            assert rejected["detail"]["code"] == "DPM_WAVE_SIMULATION_SOURCE_SCOPE_REQUIRED"
            assert observations.qsize() == before
            with psycopg.connect(dsn) as connection:
                connection.execute("SET TRANSACTION READ ONLY")
                for table in ("dpm_runs", "dpm_wave_simulation_operations"):
                    assert connection.execute(f"SELECT count(*) FROM {table}").fetchone() == (0,)


@pytest.mark.parametrize("durable", [False, True])
def test_source_bound_wave_refuses_changed_authority_and_source_before_admission(durable):
    portfolio, tenant = f"wave-source-{uuid.uuid4().hex}", f"tenant-{uuid.uuid4().hex}"
    overrides = mandate_sources(portfolio)
    with controlled_core(portfolio=portfolio, starting_shares=975, product_overrides=overrides) as (
        core_url,
        _observations,
    ):
        with disposable_database() as dsn, native_api(dsn, core_url=core_url) as (client, _process):
            wave = _checked_wave(client, portfolio, tenant)
            suffix = "simulation-operations" if durable else "simulate"
            path = f"/api/v1/rebalance/waves/{wave['wave_id']}/{suffix}"
            for options, status in [
                ({"cash_reserve_target_weight": "0"}, 424),
                ({"cash_reserve_target_tolerance": "1"}, 424),
                ({"min_cash_buffer_pct": "0.5"}, 424),
                ({"unknown_option": "ADVERSARIAL_MARKER"}, 422),
                ({"min_cash_buffer_pct": "not-a-number"}, 422),
            ]:
                body = _input(wave)
                body["item_inputs"][0]["options_override"] = options
                rejected = _call(client, "POST", path, _headers(tenant), body, expected=status)
                assert "ADVERSARIAL_MARKER" not in str(rejected)
            for field, foreign in [
                ("portfolio_id", "other-portfolio"),
                ("model_portfolio_id", "other-model"),
                ("mandate_id", "other-mandate"),
            ]:
                binding = controlled_products(portfolio)["mandate-binding"]
                binding[field] = foreign
                overrides["mandate-binding"] = binding
                rejected = _call(client, "POST", path, _headers(tenant), _input(wave), expected=424)
                assert rejected["detail"] == "DPM_CORE_CONTEXT_INCOMPLETE"
            binding = controlled_products(portfolio)["mandate-binding"]
            binding["binding_version"] = 8
            overrides["mandate-binding"] = binding
            rejected = _call(client, "POST", path, _headers(tenant), _input(wave), expected=409)
            assert rejected["detail"]["code"] == "DPM_WAVE_SIMULATION_SOURCE_REVISION_CONFLICT"
            with psycopg.connect(dsn) as connection:
                connection.execute("SET TRANSACTION READ ONLY")
                for table in ("dpm_runs", "dpm_wave_simulation_operations"):
                    assert connection.execute(f"SELECT count(*) FROM {table}").fetchone() == (0,)
