"""
FILE: tests/api/test_api_rebalance.py
"""

import asyncio
import inspect
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
from threading import Barrier

import pytest
from fastapi.testclient import TestClient

import src.api.routers.rebalance_runs as dpm_runs_router
import src.api.services.core_resolver_service as core_resolver_service
from src.api.main import app, get_db_session
from src.api.routers.rebalance_runs import (
    get_dpm_run_support_service,
    reset_dpm_run_support_service_for_tests,
)
from src.core.common.canonical import hash_canonical_payload, strip_keys
from src.core.dpm_source_context import (
    DpmCoreClientRestrictionProfileResponse,
    DpmCoreExecutionContext,
)
from src.core.rebalance_runs import (
    DpmAsyncOperationStatusResponse,
    DpmRunNotFoundError,
    DpmWorkflowDisabledError,
    DpmWorkflowTransitionError,
)
from src.core.models import BatchRebalanceResult, RebalanceResult
from tests.shared.factories import valid_api_payload


async def override_get_db_session():
    yield None


@pytest.fixture(autouse=True)
def override_db_dependency():
    original_overrides = dict(app.dependency_overrides)
    app.dependency_overrides[get_db_session] = override_get_db_session
    reset_dpm_run_support_service_for_tests()
    yield
    reset_dpm_run_support_service_for_tests()
    app.dependency_overrides = original_overrides


@pytest.fixture
def client():
    class _StatelessEnvelopeClient:
        def __init__(self, test_client: TestClient) -> None:
            self._test_client = test_client

        def post(self, url: str, *args, **kwargs):
            if url in {
                "/api/v1/rebalance/simulate",
                "/api/v1/rebalance/analyze",
                "/api/v1/rebalance/analyze/async",
            }:
                body = kwargs.get("json")
                if isinstance(body, dict) and "stateless_input" not in body:
                    kwargs["json"] = {"input_mode": "stateless", "stateless_input": body}
            headers = dict(kwargs.get("headers") or {})
            headers.setdefault("X-Tenant-Id", "tenant-test")
            kwargs["headers"] = headers
            return self._test_client.post(url, *args, **kwargs)

        def get(self, url: str, *args, **kwargs):
            headers = dict(kwargs.get("headers") or {})
            headers.setdefault("X-Tenant-Id", "tenant-test")
            kwargs["headers"] = headers
            return self._test_client.get(url, *args, **kwargs)

        def put(self, url: str, *args, **kwargs):
            headers = dict(kwargs.get("headers") or {})
            headers.setdefault("X-Tenant-Id", "tenant-test")
            kwargs["headers"] = headers
            return self._test_client.put(url, *args, **kwargs)

        def delete(self, url: str, *args, **kwargs):
            return self._test_client.delete(url, *args, **kwargs)

    with TestClient(app) as test_client:
        yield _StatelessEnvelopeClient(test_client)


def get_valid_payload():
    return valid_api_payload()


def test_concurrent_simulate_requests_publish_one_tenant_owned_run() -> None:
    payload = {"input_mode": "stateless", "stateless_input": get_valid_payload()}
    shared_key = "test-key-concurrent-tenant-owned"
    barrier = Barrier(2)

    with TestClient(app) as raw_client:

        def submit(correlation_id: str):
            barrier.wait(timeout=5)
            return raw_client.post(
                "/api/v1/rebalance/simulate",
                json=payload,
                headers={
                    "Idempotency-Key": shared_key,
                    "X-Correlation-Id": correlation_id,
                    "X-Tenant-Id": "tenant-concurrent-a",
                },
            )

        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(submit, ["corr-concurrent-a", "corr-concurrent-b"]))

        assert [response.status_code for response in responses] == [200, 200]
        run_ids = {response.json()["rebalance_run_id"] for response in responses}
        assert len(run_ids) == 1
        run_id = run_ids.pop()

        owned = raw_client.get(
            f"/api/v1/rebalance/runs/{run_id}",
            headers={"X-Tenant-Id": "tenant-concurrent-a"},
        )
        foreign = raw_client.get(
            f"/api/v1/rebalance/runs/{run_id}",
            headers={"X-Tenant-Id": "tenant-concurrent-b"},
        )
        foreign_key = raw_client.get(
            f"/api/v1/rebalance/runs/idempotency/{shared_key}",
            headers={"X-Tenant-Id": "tenant-concurrent-b"},
        )
        foreign_bundle = raw_client.get(
            f"/api/v1/rebalance/runs/{run_id}/support-bundle",
            headers={"X-Tenant-Id": "tenant-concurrent-b"},
        )
        missing_scope = raw_client.get(f"/api/v1/rebalance/runs/{run_id}")

        assert owned.status_code == 200
        assert foreign.status_code == 404
        assert foreign_key.status_code == 404
        assert foreign_bundle.status_code == 404
        assert missing_scope.status_code == 422

        independent = raw_client.post(
            "/api/v1/rebalance/simulate",
            json=payload,
            headers={
                "Idempotency-Key": shared_key,
                "X-Correlation-Id": "corr-concurrent-tenant-b",
                "X-Tenant-Id": "tenant-concurrent-b",
            },
        )
        assert independent.status_code == 200
        assert independent.json()["rebalance_run_id"] != run_id


def _stateful_input_payload() -> dict[str, object]:
    return {
        "portfolio_id": "PB_SG_GLOBAL_BAL_001",
        "as_of": "2026-03-25",
        "mandate_id": "mandate_balanced_discretionary",
        "model_portfolio_id": "model_balanced_sgd",
        "tenant_id": "tenant_001",
        "booking_center_code": "SG",
    }


def _core_execution_context() -> DpmCoreExecutionContext:
    return DpmCoreExecutionContext.model_validate(
        {
            "portfolio_snapshot": {
                "snapshot_id": "core-pf-snap-001",
                "portfolio_id": "PB_SG_GLOBAL_BAL_001",
                "base_currency": "SGD",
                "positions": [{"instrument_id": "EQ_1", "quantity": "100"}],
                "cash_balances": [{"currency": "SGD", "amount": "10000"}],
            },
            "market_data_snapshot": {
                "snapshot_id": "core-md-snap-001",
                "prices": [{"instrument_id": "EQ_1", "price": "100", "currency": "SGD"}],
                "fx_rates": [],
            },
            "model_portfolio": {"targets": [{"instrument_id": "EQ_1", "weight": "1.0"}]},
            "shelf_entries": [
                {
                    "instrument_id": "EQ_1",
                    "status": "APPROVED",
                    "asset_class": "EQUITY",
                    "issuer_id": "ISSUER_1",
                    "settlement_days": 2,
                }
            ],
            "policy_context": {
                "recommended_policy_pack_id": "dpm_standard_v1",
                "tenant_id": "tenant_001",
                "booking_center_code": "SG",
                "mandate_id": "mandate_balanced_discretionary",
            },
            "source_lineage": {
                "portfolio_snapshot_id": "core-pf-snap-001",
                "market_data_snapshot_id": "core-md-snap-001",
                "model_portfolio_id": "model_balanced_sgd",
                "model_portfolio_version": "2026-03-25",
                "shelf_version": "shelf_sg_v1",
                "integration_policy_version": "dpm-core-context.v1",
                "source_lineage_bundle_id": "lineage-bundle-001",
            },
            "supportability": {
                "state": "READY",
                "reason": "DPM_CORE_CONTEXT_READY",
                "freshness_bucket": "same_day",
            },
        }
    )


def _core_restriction_profile(*, restricted: bool) -> DpmCoreClientRestrictionProfileResponse:
    rules = (
        [
            {
                "restriction_scope": "instrument",
                "restriction_code": "NO_EQ_1_BUY",
                "restriction_status": "active",
                "restriction_source": "client_mandate",
                "applies_to_buy": True,
                "applies_to_sell": False,
                "instrument_ids": ["EQ_1"],
                "effective_from": "2026-01-01",
                "restriction_version": 3,
                "source_record_id": "restriction-eq-1-v3",
            }
        ]
        if restricted
        else []
    )
    return DpmCoreClientRestrictionProfileResponse.model_validate(
        {
            "product_name": "ClientRestrictionProfile",
            "product_version": "v1",
            "portfolio_id": "PB_SG_GLOBAL_BAL_001",
            "client_id": "CIF_SG_000184",
            "mandate_id": "mandate_balanced_discretionary",
            "as_of_date": "2026-03-25",
            "restrictions": rules,
            "supportability": {
                "state": "READY",
                "reason": "CLIENT_RESTRICTION_PROFILE_READY",
                "restriction_count": len(rules),
                "missing_data_families": [],
            },
            "lineage": {"contract_version": "rfc_040_client_restriction_profile_v1"},
            "data_quality_status": "COMPLETE",
            "latest_evidence_timestamp": "2026-03-25T09:00:00Z",
            "source_batch_fingerprint": (
                "sha256:client-restrictions-v3"
                if restricted
                else "sha256:client-restrictions-empty"
            ),
        }
    )


def test_stateful_simulate_blocks_matching_hard_restriction_and_invalidates_old_replay(
    monkeypatch,
) -> None:
    fake_resolver = _install_fake_core_resolver(monkeypatch)
    source_payload = _core_execution_context().model_dump(mode="json")
    source_payload["shelf_entries"][0]["settlement_days"] = 0
    source_payload["portfolio_snapshot"]["positions"][0]["market_value"] = {
        "amount": "10000",
        "currency": "SGD",
    }
    source = DpmCoreExecutionContext.model_validate(source_payload)
    unrestricted = source.model_copy(
        update={"client_restriction_profile": _core_restriction_profile(restricted=False)}
    )
    restricted = source.model_copy(
        update={"client_restriction_profile": _core_restriction_profile(restricted=True)}
    )
    request = {"input_mode": "stateful", "stateful_input": _stateful_input_payload()}
    headers = {"Idempotency-Key": "hard-policy-context-revision", "X-Tenant-Id": "tenant_001"}
    with TestClient(app) as raw_client:
        fake_resolver.context = unrestricted
        accepted = raw_client.post("/api/v1/rebalance/simulate", json=request, headers=headers)
        fake_resolver.context = restricted
        stale_replay = raw_client.post("/api/v1/rebalance/simulate", json=request, headers=headers)
        blocked = raw_client.post(
            "/api/v1/rebalance/simulate",
            json=request,
            headers={**headers, "Idempotency-Key": "hard-policy-restricted"},
        )
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "READY", accepted.json()["reconciliation"]
    assert Decimal(accepted.json()["before"]["total_value"]["amount"]) == Decimal("20000")
    assert Decimal(accepted.json()["after_simulated"]["total_value"]["amount"]) == Decimal("20000")
    assert Decimal(accepted.json()["after_simulated"]["cash_balances"][0]["amount"]) == 0
    assert [
        (intent["side"], Decimal(intent["quantity"]), Decimal(intent["notional"]["amount"]))
        for intent in accepted.json()["intents"]
        if intent["intent_type"] == "SECURITY_TRADE"
    ] == [("BUY", Decimal("100"), Decimal("10000"))]
    assert accepted.json()["client_restriction_policy"]["decision"] == "READY"
    assert stale_replay.status_code == 409
    assert blocked.status_code == 200
    assert blocked.json()["status"] == "BLOCKED"
    assert blocked.json()["gate_decision"]["gate"] == "BLOCKED"
    assert blocked.json()["client_restriction_policy"]["decision"] == "BLOCKED"
    assert blocked.json()["client_restriction_policy"]["violated_rule_refs"] == [
        "NO_EQ_1_BUY:3:restriction-eq-1-v3:BUY:EQ_1"
    ]
    assert blocked.json()["client_restriction_policy"]["applicable_rule_refs"] == [
        "NO_EQ_1_BUY:3:restriction-eq-1-v3:BUY:EQ_1"
    ]
    assert (
        blocked.json()["client_restriction_policy"]["content_hash"]
        != (accepted.json()["client_restriction_policy"]["content_hash"])
    )
    assert blocked.json()["intents"] == accepted.json()["intents"]


class _FakeCoreResolver:
    def __init__(self, context: DpmCoreExecutionContext | None = None) -> None:
        self.calls: list[tuple[str, str | None, str | None]] = []
        self.context = context or _core_execution_context()

    def resolve_execution_context(self, *, stateful_input, correlation_id):
        self.calls.append((stateful_input.portfolio_id, correlation_id, stateful_input.tenant_id))
        return self.context


def _install_fake_core_resolver(monkeypatch) -> _FakeCoreResolver:
    fake_resolver = _FakeCoreResolver()
    monkeypatch.setenv("DPM_STATEFUL_CORE_SOURCING_ENABLED", "true")
    monkeypatch.setattr(
        core_resolver_service,
        "build_core_resolver_client",
        lambda: fake_resolver,
    )
    return fake_resolver


def test_direct_stateless_body_is_rejected_without_envelope():
    with TestClient(app) as raw_client:
        response = raw_client.post(
            "/api/v1/rebalance/simulate",
            json=get_valid_payload(),
            headers={"Idempotency-Key": "test-key-direct-body-rejected"},
        )

    assert response.status_code == 422
    assert "DPM_STATELESS_INPUT_REQUIRED" in response.text


def test_stateful_simulate_is_feature_gated_by_default():
    with TestClient(app) as raw_client:
        response = raw_client.post(
            "/api/v1/rebalance/simulate",
            json={
                "input_mode": "stateful",
                "stateful_input": {
                    "portfolio_id": "PB_SG_GLOBAL_BAL_001",
                    "as_of": "2026-03-25",
                    "mandate_id": "mandate_balanced_discretionary",
                    "model_portfolio_id": "model_balanced_sgd",
                    "tenant_id": "tenant_001",
                    "booking_center_code": "SG",
                },
            },
            headers={
                "Idempotency-Key": "test-key-stateful-disabled",
                "X-Tenant-Id": "tenant_001",
            },
        )

    assert response.status_code == 409
    assert response.json()["detail"] == "DPM_STATEFUL_INPUT_DISABLED"


def test_stateful_simulate_enabled_without_core_base_url_returns_unavailable(monkeypatch):
    monkeypatch.setenv("DPM_STATEFUL_CORE_SOURCING_ENABLED", "true")
    monkeypatch.delenv("DPM_CORE_BASE_URL", raising=False)

    with TestClient(app) as raw_client:
        response = raw_client.post(
            "/api/v1/rebalance/simulate",
            json={
                "input_mode": "stateful",
                "stateful_input": _stateful_input_payload(),
            },
            headers={"Idempotency-Key": "test-key-stateful-no-core", "X-Tenant-Id": "tenant_001"},
        )

    assert response.status_code == 503
    assert response.json()["detail"] == "DPM_CORE_RESOLVER_UNAVAILABLE"


def test_stateful_simulate_uses_resolved_core_context_and_lineage(monkeypatch):
    fake_resolver = _install_fake_core_resolver(monkeypatch)

    with TestClient(app) as raw_client:
        response = raw_client.post(
            "/api/v1/rebalance/simulate",
            json={
                "input_mode": "stateful",
                "stateful_input": _stateful_input_payload(),
                "options_override": {"enable_settlement_awareness": True},
            },
            headers={
                "Idempotency-Key": "test-key-stateful-simulate-ready",
                "X-Correlation-Id": "corr-stateful-simulate",
                "X-Tenant-Id": " tenant_001 ",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert fake_resolver.calls == [("PB_SG_GLOBAL_BAL_001", "corr-stateful-simulate", "tenant_001")]
    assert body["correlation_id"] == "corr-stateful-simulate"
    assert body["lineage"]["input_mode"] == "stateful"
    assert body["lineage"]["source_system"] == "lotus-core"
    assert body["lineage"]["portfolio_snapshot_id"] == "core-pf-snap-001"
    assert body["lineage"]["market_data_snapshot_id"] == "core-md-snap-001"
    assert body["lineage"]["model_portfolio_id"] == "model_balanced_sgd"
    assert body["lineage"]["model_portfolio_version"] == "2026-03-25"
    assert body["lineage"]["shelf_version"] == "shelf_sg_v1"
    assert body["lineage"]["integration_policy_version"] == "dpm-core-context.v1"
    assert body["lineage"]["source_lineage_bundle_id"] == "lineage-bundle-001"
    assert body["lineage"]["source_supportability_state"] == "READY"
    assert body["lineage"]["stateful_context_hash"].startswith("sha256:")


def test_stateful_simulate_applies_source_cash_reserve_target_and_reports_lineage(monkeypatch):
    source_payload = _core_execution_context().model_dump(mode="python")
    source_payload["portfolio_snapshot"]["positions"][0]["market_value"] = {
        "amount": "10000",
        "currency": "SGD",
    }
    source_payload["policy_context"].update(
        {
            "mandate_product_version": "v1",
            "mandate_binding_version": 3,
            "mandate_effective_from": "2026-03-01",
            "mandate_effective_to": None,
            "mandate_lineage": {"source_record_id": "mandate-balanced-v3"},
            "cash_reserve_target_weight": "0.02",
        }
    )
    fake_resolver = _FakeCoreResolver(DpmCoreExecutionContext.model_validate(source_payload))
    monkeypatch.setenv("DPM_STATEFUL_CORE_SOURCING_ENABLED", "true")
    monkeypatch.setattr(core_resolver_service, "build_core_resolver_client", lambda: fake_resolver)

    with TestClient(app) as raw_client:
        response = raw_client.post(
            "/api/v1/rebalance/simulate",
            json={"input_mode": "stateful", "stateful_input": _stateful_input_payload()},
            headers={
                "Idempotency-Key": "stateful-source-cash-target-v3",
                "X-Tenant-Id": "tenant_001",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert Decimal(body["after_simulated"]["cash_balances"][0]["amount"]) == Decimal("400")
    cash_allocation = next(
        row for row in body["after_simulated"]["allocation_by_asset_class"] if row["key"] == "CASH"
    )
    assert Decimal(cash_allocation["weight"]) == Decimal("0.02")
    reserve_rule = next(
        row for row in body["rule_results"] if row["rule_id"] == "CASH_RESERVE_TARGET"
    )
    assert reserve_rule["status"] == "PASS"
    assert reserve_rule["reason_code"] == "TARGET_MET_WITHIN_TOLERANCE"
    assert Decimal(reserve_rule["threshold"]["target"]) == Decimal("0.02")
    assert body["gate_decision"]["gate"] == "COMPLIANCE_REVIEW_REQUIRED"
    assert body["lineage"]["source_mandate_id"] == "mandate_balanced_discretionary"
    assert body["lineage"]["source_mandate_product_version"] == "v1"
    assert body["lineage"]["source_mandate_binding_version"] == 3
    assert body["lineage"]["source_mandate_effective_from"] == "2026-03-01"
    assert body["lineage"]["source_mandate_lineage"] == {"source_record_id": "mandate-balanced-v3"}
    assert Decimal(body["lineage"]["source_cash_reserve_target_weight"]) == Decimal("0.02")
    assert body["lineage"]["cash_reserve_override_authority"] == "NONE"


@pytest.mark.parametrize(
    ("options_override", "expected_code"),
    [
        (
            {"min_cash_buffer_pct": "0.01"},
            "DPM_CORE_MANDATE_CASH_RESERVE_OVERRIDE_CONFLICT",
        ),
        (
            {"cash_reserve_target_tolerance": "1"},
            "DPM_CORE_MANDATE_CASH_RESERVE_TOLERANCE_OVERRIDE_FORBIDDEN",
        ),
    ],
)
def test_stateful_simulate_rejects_unauthorized_cash_reserve_override(
    monkeypatch,
    options_override,
    expected_code,
):
    source_payload = _core_execution_context().model_dump(mode="python")
    source_payload["policy_context"]["cash_reserve_target_weight"] = "0.02"
    fake_resolver = _FakeCoreResolver(DpmCoreExecutionContext.model_validate(source_payload))
    monkeypatch.setenv("DPM_STATEFUL_CORE_SOURCING_ENABLED", "true")
    monkeypatch.setattr(core_resolver_service, "build_core_resolver_client", lambda: fake_resolver)

    with TestClient(app) as raw_client:
        response = raw_client.post(
            "/api/v1/rebalance/simulate",
            json={
                "input_mode": "stateful",
                "stateful_input": _stateful_input_payload(),
                "options_override": options_override,
            },
            headers={
                "Idempotency-Key": f"stateful-source-cash-target-{expected_code}",
                "X-Tenant-Id": "tenant_001",
            },
        )

    assert response.status_code == 424
    assert response.json()["detail"] == expected_code


def test_stateful_simulate_normalizes_request_policy_against_source_resolved_currency(
    monkeypatch,
) -> None:
    source_payload = _core_execution_context().model_dump(mode="python")
    rebalance_payload = _minimum_trade_payload(
        price_currency="USD",
        first_price="50",
        second_price="25",
        fx_rates=[{"pair": "USD/SGD", "rate": "2"}],
    )
    for field in (
        "portfolio_snapshot",
        "market_data_snapshot",
        "model_portfolio",
        "shelf_entries",
    ):
        source_payload[field] = rebalance_payload[field]
    source_context = DpmCoreExecutionContext.model_validate(source_payload)
    fake_resolver = _FakeCoreResolver(source_context)
    monkeypatch.setenv("DPM_STATEFUL_CORE_SOURCING_ENABLED", "true")
    monkeypatch.setattr(
        core_resolver_service,
        "build_core_resolver_client",
        lambda: fake_resolver,
    )

    with TestClient(app) as raw_client:
        response = raw_client.post(
            "/api/v1/rebalance/simulate",
            json={
                "input_mode": "stateful",
                "stateful_input": _stateful_input_payload(),
                "options_override": {
                    "min_trade_notional": {"amount": "3000", "currency": "SGD"},
                    "suppress_dust_trades": True,
                    "fx_buffer_pct": "0",
                },
            },
            headers={
                "Idempotency-Key": "min-trade-stateful-source-context",
                "X-Tenant-Id": "tenant_001",
            },
        )

    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "PENDING_REVIEW"
    assert result["client_restriction_policy"]["reason_codes"] == [
        "CLIENT_RESTRICTION_PROFILE_UNAVAILABLE"
    ]
    assert result["lineage"]["input_mode"] == "stateful"
    assert {
        intent["instrument_id"]
        for intent in result["intents"]
        if intent["intent_type"] == "SECURITY_TRADE"
    } == {"EQ_A", "EQ_B"}
    evaluations = result["diagnostics"]["minimum_trade_threshold_evaluations"]
    assert {row["configured_threshold"]["currency"] for row in evaluations} == {"SGD"}
    assert {Decimal(row["comparison_threshold"]["amount"]) for row in evaluations} == {
        Decimal("1500")
    }
    assert {row["comparison_threshold"]["currency"] for row in evaluations} == {"USD"}
    assert {row["conversion_direction"] for row in evaluations} == {"INVERSE"}


def test_stateful_analyze_uses_shared_core_context_for_each_scenario(monkeypatch):
    source_payload = _core_execution_context().model_dump(mode="python")
    source_payload["portfolio_snapshot"]["positions"][0]["market_value"] = {
        "amount": "10000",
        "currency": "SGD",
    }
    source_payload["policy_context"].update(
        {
            "mandate_product_version": "v1",
            "mandate_binding_version": 3,
            "mandate_effective_from": "2026-03-01",
            "cash_reserve_target_weight": "0.02",
        }
    )
    fake_resolver = _FakeCoreResolver(DpmCoreExecutionContext.model_validate(source_payload))
    monkeypatch.setenv("DPM_STATEFUL_CORE_SOURCING_ENABLED", "true")
    monkeypatch.setattr(core_resolver_service, "build_core_resolver_client", lambda: fake_resolver)

    with TestClient(app) as raw_client:
        response = raw_client.post(
            "/api/v1/rebalance/analyze",
            json={
                "input_mode": "stateful",
                "stateful_input": _stateful_input_payload(),
                "scenarios": {
                    "baseline": {"options": {}},
                    "position_cap": {"options": {"single_position_max_weight": "0.5"}},
                },
            },
            headers={"X-Correlation-Id": "corr-stateful-analyze", "X-Tenant-Id": "tenant_001"},
        )

    assert response.status_code == 200
    body = response.json()
    assert fake_resolver.calls == [("PB_SG_GLOBAL_BAL_001", "corr-stateful-analyze", "tenant_001")]
    assert set(body["results"]) == {"baseline", "position_cap"}
    assert body["base_snapshot_ids"] == {
        "portfolio_snapshot_id": "core-pf-snap-001",
        "market_data_snapshot_id": "core-md-snap-001",
    }
    for scenario_name, result in body["results"].items():
        assert result["correlation_id"] == f"corr-stateful-analyze:{scenario_name}"
        assert result["lineage"]["input_mode"] == "stateful"
        assert result["lineage"]["source_system"] == "lotus-core"
        assert result["lineage"]["stateful_context_hash"].startswith("sha256:")
        assert Decimal(result["lineage"]["source_cash_reserve_target_weight"]) == Decimal("0.02")
    baseline_rule = next(
        row
        for row in body["results"]["baseline"]["rule_results"]
        if row["rule_id"] == "CASH_RESERVE_TARGET"
    )
    constrained_rule = next(
        row
        for row in body["results"]["position_cap"]["rule_results"]
        if row["rule_id"] == "CASH_RESERVE_TARGET"
    )
    assert baseline_rule["status"] == "PASS"
    assert constrained_rule["status"] == "FAIL"
    assert constrained_rule["reason_code"] == "TARGET_DEVIATION"
    assert body["results"]["baseline"]["gate_decision"]["gate"] == "EXECUTION_READY"
    constrained_gate = body["results"]["position_cap"]["gate_decision"]
    assert constrained_gate["gate"] == "RISK_REVIEW_REQUIRED"
    assert {reason["reason_code"] for reason in constrained_gate["reasons"]} >= {
        "SOFT_RULE_FAIL:CASH_RESERVE_TARGET"
    }


def test_stateful_analyze_async_persists_resolved_core_lineage(monkeypatch):
    fake_resolver = _install_fake_core_resolver(monkeypatch)

    with TestClient(app) as raw_client:
        accepted = raw_client.post(
            "/api/v1/rebalance/analyze/async",
            json={
                "input_mode": "stateful",
                "stateful_input": _stateful_input_payload(),
                "scenarios": {"baseline": {"options": {}}},
            },
            headers={"X-Correlation-Id": "corr-stateful-async", "X-Tenant-Id": "tenant_001"},
        )
        operation = raw_client.get(
            f"/api/v1/rebalance/operations/{accepted.json()['operation_id']}",
            headers={"X-Tenant-Id": "tenant_001"},
        )

    assert accepted.status_code == 202
    assert fake_resolver.calls == [("PB_SG_GLOBAL_BAL_001", "corr-stateful-async", "tenant_001")]
    assert operation.status_code == 200
    operation_body = operation.json()
    assert operation_body["status"] == "SUCCEEDED"
    result = operation_body["result"]["results"]["baseline"]
    assert result["lineage"]["input_mode"] == "stateful"
    assert result["lineage"]["source_system"] == "lotus-core"
    assert result["lineage"]["stateful_context_hash"].startswith("sha256:")


@pytest.mark.parametrize(
    ("tenant_header", "expected_detail"),
    [
        (None, "DPM_STATEFUL_TENANT_HEADER_REQUIRED"),
        ("tenant_other", "DPM_STATEFUL_TENANT_MISMATCH"),
    ],
)
def test_stateful_simulate_rejects_unadmitted_tenant_before_core_sourcing(
    monkeypatch, tenant_header, expected_detail
):
    fake_resolver = _install_fake_core_resolver(monkeypatch)
    headers = {"Idempotency-Key": "test-key-stateful-tenant-rejected"}
    if tenant_header is not None:
        headers["X-Tenant-Id"] = tenant_header

    with TestClient(app) as raw_client:
        response = raw_client.post(
            "/api/v1/rebalance/simulate",
            json={"input_mode": "stateful", "stateful_input": _stateful_input_payload()},
            headers=headers,
        )

    assert response.status_code == 422
    if tenant_header is None:
        assert response.json()["detail"][0]["loc"] == ["header", "x-tenant-id"]
        assert response.json()["detail"][0]["type"] == "missing"
    else:
        assert response.json()["detail"] == expected_detail
    assert fake_resolver.calls == []


def test_simulate_endpoint_success(client):
    payload = get_valid_payload()
    headers = {"Idempotency-Key": "test-key-1", "X-Correlation-Id": "corr-1"}
    response = client.post("/api/v1/rebalance/simulate", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "READY"
    assert data["rebalance_run_id"].startswith("rr_")
    assert data["correlation_id"] == "corr-1"
    assert "before" in data
    assert "after_simulated" in data
    assert "rule_results" in data
    assert "diagnostics" in data
    assert data["gate_decision"]["gate"] in {
        "BLOCKED",
        "RISK_REVIEW_REQUIRED",
        "COMPLIANCE_REVIEW_REQUIRED",
        "MANDATE_APPROVAL_REQUIRED",
        "EXECUTION_READY",
        "NONE",
    }
    metrics = client.get("/metrics")
    assert metrics.status_code == 200
    assert "lotus_manage_execution_total" in metrics.text
    assert 'input_mode="stateless"' in metrics.text
    assert 'operation="simulate"' in metrics.text
    assert "lotus_manage_policy_pack_resolution_total" in metrics.text
    assert 'enabled="false"' in metrics.text
    assert 'surface="simulate"' in metrics.text


def _minimum_trade_payload(
    *,
    price_currency: str = "SGD",
    first_price: str = "100",
    second_price: str = "50",
    fx_rates: list[dict[str, str]] | None = None,
) -> dict[str, object]:
    payload = get_valid_payload()
    payload["portfolio_snapshot"] = {
        "portfolio_id": "pf_min_trade_fx",
        "base_currency": "SGD",
        "positions": [{"instrument_id": "EQ_A", "quantity": "100"}],
        "cash_balances": [{"currency": "SGD", "amount": "1000"}],
    }
    payload["market_data_snapshot"] = {
        "prices": [
            {"instrument_id": "EQ_A", "price": first_price, "currency": price_currency},
            {"instrument_id": "EQ_B", "price": second_price, "currency": price_currency},
        ],
        "fx_rates": fx_rates or [],
    }
    payload["model_portfolio"] = {
        "targets": [
            {"instrument_id": "EQ_A", "weight": "0.50"},
            {"instrument_id": "EQ_B", "weight": "0.50"},
        ]
    }
    payload["shelf_entries"] = [
        {"instrument_id": "EQ_A", "status": "APPROVED"},
        {"instrument_id": "EQ_B", "status": "APPROVED"},
    ]
    payload["options"] = {"suppress_dust_trades": True}
    return payload


@pytest.mark.parametrize(
    ("threshold_source", "fx_pair", "fx_rate", "expected_direction"),
    [
        ("request", "USD/SGD", "2", "DIRECT"),
        ("request", "SGD/USD", "0.5", "INVERSE"),
        ("shelf", "USD/SGD", "2", "DIRECT"),
        ("shelf", "SGD/USD", "0.5", "INVERSE"),
    ],
)
def test_simulate_normalizes_request_and_shelf_minimums_into_trade_currency(
    client,
    threshold_source: str,
    fx_pair: str,
    fx_rate: str,
    expected_direction: str,
) -> None:
    payload = _minimum_trade_payload(fx_rates=[{"pair": fx_pair, "rate": fx_rate}])
    threshold = {"amount": "3000", "currency": "USD"}
    if threshold_source == "request":
        payload["options"]["min_trade_notional"] = threshold
    else:
        for shelf_record in payload["shelf_entries"]:
            shelf_record["min_notional"] = threshold

    response = client.post(
        "/api/v1/rebalance/simulate",
        json=payload,
        headers={"Idempotency-Key": f"min-trade-{threshold_source}-{expected_direction.lower()}"},
    )

    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "READY"
    assert result["intents"] == []
    suppressed = result["diagnostics"]["suppressed_intents"]
    assert {
        (
            row["instrument_id"],
            row["reason"],
            row["intended_notional"]["amount"],
            row["intended_notional"]["currency"],
            row["threshold"]["amount"],
            row["threshold"]["currency"],
        )
        for row in suppressed
    } == {
        ("EQ_A", "BELOW_MIN_NOTIONAL", "4500", "SGD", "3000", "USD"),
        ("EQ_B", "BELOW_MIN_NOTIONAL", "5500", "SGD", "3000", "USD"),
    }
    evaluations = result["diagnostics"]["minimum_trade_threshold_evaluations"]
    assert {
        (row["instrument_id"], row["side"], row["comparison_outcome"]) for row in evaluations
    } == {
        ("EQ_A", "SELL", "SUPPRESSED"),
        ("EQ_B", "BUY", "SUPPRESSED"),
    }
    assert {row["configured_threshold"]["amount"] for row in evaluations} == {"3000"}
    assert {row["comparison_threshold"]["amount"] for row in evaluations} == {"6000"}
    assert {row["comparison_threshold"]["currency"] for row in evaluations} == {"SGD"}
    expected_quote_rate = "2" if expected_direction == "DIRECT" else "0.5"
    assert {row["fx_quote_rate"] for row in evaluations} == {expected_quote_rate}
    assert {row["conversion_rate"] for row in evaluations} == {"2"}
    assert {row["conversion_direction"] for row in evaluations} == {expected_direction}


@pytest.mark.parametrize(
    ("fx_rates", "expected_pair", "expected_reason", "expected_quote_rate"),
    [
        ([], "USD/SGD", "MIN_TRADE_THRESHOLD_FX_MISSING", None),
        ([{"pair": "USD/SGD", "rate": "0"}], "USD/SGD", "MIN_TRADE_THRESHOLD_FX_INVALID", "0"),
        (
            [{"pair": "SGD/USD", "rate": "-0.5"}],
            "SGD/USD",
            "MIN_TRADE_THRESHOLD_FX_INVALID",
            "-0.5",
        ),
    ],
)
def test_simulate_blocks_when_minimum_trade_fx_is_missing_or_invalid(
    client,
    fx_rates: list[dict[str, str]],
    expected_pair: str,
    expected_reason: str,
    expected_quote_rate: str | None,
) -> None:
    payload = _minimum_trade_payload(fx_rates=fx_rates)
    payload["options"]["min_trade_notional"] = {"amount": "3000", "currency": "USD"}
    payload["options"]["block_on_missing_fx"] = False

    response = client.post(
        "/api/v1/rebalance/simulate",
        json=payload,
        headers={"Idempotency-Key": f"min-trade-refusal-{expected_reason}-{expected_quote_rate}"},
    )

    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "BLOCKED"
    assert [
        intent for intent in result["intents"] if intent["intent_type"] == "SECURITY_TRADE"
    ] == []
    assert result["diagnostics"]["data_quality"]["fx_missing"] == []
    assert result["diagnostics"]["data_quality"]["minimum_trade_threshold_fx_unavailable"] == [
        expected_pair,
        expected_pair,
    ]
    assert result["gate_decision"]["gate"] == "BLOCKED"
    assert {reason["reason_code"] for reason in result["gate_decision"]["reasons"]} >= {
        "DATA_QUALITY_MIN_TRADE_THRESHOLD_FX_UNAVAILABLE"
    }
    evaluations = result["diagnostics"]["minimum_trade_threshold_evaluations"]
    assert len(evaluations) == 2
    assert {row["comparison_outcome"] for row in evaluations} == {"BLOCKED"}
    assert {row["reason_code"] for row in evaluations} == {expected_reason}
    assert {row["fx_quote_pair"] for row in evaluations} == {expected_pair}
    assert {row["fx_quote_rate"] for row in evaluations} == {expected_quote_rate}
    assert {row["comparison_threshold"] for row in evaluations} == {None}


@pytest.mark.parametrize(
    (
        "threshold",
        "expected_instruments",
        "expected_outcomes",
        "expected_status",
        "expected_cash",
        "expected_gate",
    ),
    [
        (
            "4499.99",
            {"EQ_A", "EQ_B"},
            {"EQ_A": "KEPT", "EQ_B": "KEPT"},
            "READY",
            "0",
            "COMPLIANCE_REVIEW_REQUIRED",
        ),
        (
            "4500",
            {"EQ_A", "EQ_B"},
            {"EQ_A": "KEPT", "EQ_B": "KEPT"},
            "READY",
            "0",
            "COMPLIANCE_REVIEW_REQUIRED",
        ),
        (
            "4500.01",
            {"EQ_B"},
            {"EQ_A": "SUPPRESSED", "EQ_B": "KEPT"},
            "BLOCKED",
            "-4500",
            "BLOCKED",
        ),
        (
            "5500",
            {"EQ_B"},
            {"EQ_A": "SUPPRESSED", "EQ_B": "KEPT"},
            "BLOCKED",
            "-4500",
            "BLOCKED",
        ),
        (
            "5500.01",
            set(),
            {"EQ_A": "SUPPRESSED", "EQ_B": "SUPPRESSED"},
            "READY",
            "1000",
            "COMPLIANCE_REVIEW_REQUIRED",
        ),
    ],
)
def test_simulate_includes_exact_minimum_and_suppresses_only_below_threshold(
    client,
    threshold: str,
    expected_instruments: set[str],
    expected_outcomes: dict[str, str],
    expected_status: str,
    expected_cash: str,
    expected_gate: str,
) -> None:
    payload = _minimum_trade_payload()
    payload["options"]["min_trade_notional"] = {"amount": threshold, "currency": "SGD"}

    response = client.post(
        "/api/v1/rebalance/simulate",
        json=payload,
        headers={"Idempotency-Key": f"min-trade-boundary-{threshold}"},
    )

    assert response.status_code == 200
    result = response.json()
    assert result["status"] == expected_status
    security_intents = [
        intent for intent in result["intents"] if intent["intent_type"] == "SECURITY_TRADE"
    ]
    assert {intent["instrument_id"] for intent in security_intents} == expected_instruments
    assert {
        row["instrument_id"]: row["comparison_outcome"]
        for row in result["diagnostics"]["minimum_trade_threshold_evaluations"]
    } == expected_outcomes
    assert Decimal(result["before"]["total_value"]["amount"]) == Decimal("11000")
    assert Decimal(result["after_simulated"]["total_value"]["amount"]) == Decimal("11000")
    assert [
        (row["currency"], Decimal(row["amount"]))
        for row in result["after_simulated"]["cash_balances"]
    ] == [("SGD", Decimal(expected_cash))]
    assert result["gate_decision"]["gate"] == expected_gate


@pytest.mark.parametrize(
    (
        "threshold",
        "fx_pair",
        "fx_rate",
        "expected_direction",
        "expected_pair",
        "expected_conversion_rate",
    ),
    [
        (
            {"amount": "3000", "currency": "SGD"},
            "USD/SGD",
            "2",
            "INVERSE",
            "USD/SGD",
            "0.5",
        ),
        (
            {"amount": "3000", "currency": "SGD"},
            "SGD/USD",
            "0.5",
            "DIRECT",
            "SGD/USD",
            "0.5",
        ),
        (
            {"amount": "1500", "currency": "USD"},
            "USD/SGD",
            "2",
            "IDENTITY",
            "USD/USD",
            "1",
        ),
    ],
)
def test_simulate_retains_equivalent_foreign_currency_trades(
    client,
    threshold: dict[str, str],
    fx_pair: str,
    fx_rate: str,
    expected_direction: str,
    expected_pair: str,
    expected_conversion_rate: str,
) -> None:
    payload = _minimum_trade_payload(
        price_currency="USD",
        first_price="50",
        second_price="25",
        fx_rates=[{"pair": fx_pair, "rate": fx_rate}],
    )
    payload["options"]["min_trade_notional"] = threshold
    payload["options"]["fx_buffer_pct"] = "0"

    response = client.post(
        "/api/v1/rebalance/simulate",
        json=payload,
        headers={"Idempotency-Key": f"min-trade-foreign-{threshold['currency']}"},
    )

    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "READY"
    security_intents = {
        intent["instrument_id"]: intent
        for intent in result["intents"]
        if intent["intent_type"] == "SECURITY_TRADE"
    }
    assert security_intents["EQ_A"]["side"] == "SELL"
    assert security_intents["EQ_A"]["quantity"] == "45"
    assert security_intents["EQ_A"]["notional"] == {"amount": "2250", "currency": "USD"}
    assert security_intents["EQ_B"]["side"] == "BUY"
    assert security_intents["EQ_B"]["quantity"] == "110"
    assert security_intents["EQ_B"]["notional"] == {"amount": "2750", "currency": "USD"}
    evaluations = result["diagnostics"]["minimum_trade_threshold_evaluations"]
    assert {row["comparison_outcome"] for row in evaluations} == {"KEPT"}
    assert {Decimal(row["comparison_threshold"]["amount"]) for row in evaluations} == {
        Decimal("1500")
    }
    assert {row["comparison_threshold"]["currency"] for row in evaluations} == {"USD"}
    assert {row["conversion_direction"] for row in evaluations} == {expected_direction}
    assert {row["fx_quote_pair"] for row in evaluations} == {expected_pair}
    assert {Decimal(row["conversion_rate"]) for row in evaluations} == {
        Decimal(expected_conversion_rate)
    }


def test_simulate_preserves_request_threshold_precedence_over_shelf_threshold(client) -> None:
    payload = _minimum_trade_payload(fx_rates=[{"pair": "USD/SGD", "rate": "2"}])
    payload["options"]["min_trade_notional"] = {"amount": "1000", "currency": "USD"}
    for shelf_record in payload["shelf_entries"]:
        shelf_record["min_notional"] = {"amount": "3000", "currency": "USD"}

    response = client.post(
        "/api/v1/rebalance/simulate",
        json=payload,
        headers={"Idempotency-Key": "min-trade-request-before-shelf"},
    )

    assert response.status_code == 200
    result = response.json()
    assert {
        intent["instrument_id"]
        for intent in result["intents"]
        if intent["intent_type"] == "SECURITY_TRADE"
    } == {"EQ_A", "EQ_B"}
    evaluations = result["diagnostics"]["minimum_trade_threshold_evaluations"]
    assert {row["configured_threshold"]["amount"] for row in evaluations} == {"1000"}
    assert {row["comparison_threshold"]["amount"] for row in evaluations} == {"2000"}


def test_simulate_skips_policy_catalog_when_policy_packs_disabled(client, monkeypatch):
    monkeypatch.setenv("DPM_POLICY_PACKS_ENABLED", "false")

    def _fail_if_catalog_loaded():
        raise AssertionError("policy catalog should not be loaded when policy packs are disabled")

    monkeypatch.setattr(
        "src.api.services.rebalance_simulation_service.load_dpm_policy_pack_catalog",
        _fail_if_catalog_loaded,
    )

    response = client.post(
        "/api/v1/rebalance/simulate",
        json=get_valid_payload(),
        headers={"Idempotency-Key": "test-key-policy-disabled-no-catalog"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "READY"


def test_simulate_missing_idempotency_key_422(client):
    """Verifies that Idempotency-Key is mandatory."""
    payload = get_valid_payload()
    response = client.post("/api/v1/rebalance/simulate", json=payload)
    assert response.status_code == 422
    errors = response.json()["detail"]
    assert any(e["type"] == "missing" and "idempotency-key" in e["loc"] for e in errors)


def test_simulate_blank_idempotency_key_422(client):
    response = client.post(
        "/api/v1/rebalance/simulate",
        json=get_valid_payload(),
        headers={"Idempotency-Key": "   "},
    )
    assert response.status_code == 422


def test_simulate_payload_validation_error_422(client):
    """Verifies that invalid payloads still return 422."""
    payload = get_valid_payload()
    del payload["portfolio_snapshot"]
    headers = {"Idempotency-Key": "test-key-val"}
    response = client.post("/api/v1/rebalance/simulate", json=payload, headers=headers)
    assert response.status_code == 422
    assert "detail" in response.json()


def test_simulate_idempotency_replay_returns_same_payload(client):
    payload = get_valid_payload()
    headers = {"Idempotency-Key": "test-key-idem-replay", "X-Correlation-Id": "corr-idem-replay"}

    first = client.post("/api/v1/rebalance/simulate", json=payload, headers=headers)
    second = client.post("/api/v1/rebalance/simulate", json=payload, headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()


def test_simulate_idempotency_conflict_returns_409(client):
    payload = get_valid_payload()
    headers = {"Idempotency-Key": "test-key-idem-conflict"}

    first = client.post("/api/v1/rebalance/simulate", json=payload, headers=headers)
    assert first.status_code == 200

    changed = get_valid_payload()
    changed["options"]["max_turnover_pct"] = "0.05"
    conflict = client.post("/api/v1/rebalance/simulate", json=changed, headers=headers)
    assert conflict.status_code == 409
    assert conflict.json()["detail"] == "IDEMPOTENCY_KEY_CONFLICT: request hash mismatch"


def test_rebalance_simulation_http_exception_mapping():
    from src.api.routers.rebalance_simulation_http import rebalance_simulation_http_exception
    from src.api.services.rebalance_simulation_errors import (
        DpmRebalanceIdempotencyConflictError,
        DpmRebalanceIdempotencyStoreInconsistentError,
        DpmRebalanceIdempotencyStoreWriteFailedError,
        DpmRebalanceSimulationError,
        DpmRebalanceSupportabilityStoreUnavailableError,
    )

    mappings = [
        (DpmRebalanceIdempotencyConflictError("conflict"), 409, "conflict"),
        (
            DpmRebalanceIdempotencyStoreInconsistentError("inconsistent"),
            503,
            "inconsistent",
        ),
        (DpmRebalanceIdempotencyStoreWriteFailedError("write-failed"), 503, "write-failed"),
        (
            DpmRebalanceSupportabilityStoreUnavailableError("support-unavailable"),
            503,
            "support-unavailable",
        ),
        (DpmRebalanceSimulationError("generic"), 500, "DpmRebalanceSimulationError"),
    ]

    for exc, status_code, detail in mappings:
        http_exc = rebalance_simulation_http_exception(exc)

        assert http_exc.status_code == status_code
        assert http_exc.detail == detail


def test_rebalance_async_operation_http_exception_mapping():
    from src.api.routers.rebalance_simulation_http import rebalance_async_operation_http_exception
    from src.api.services.rebalance_simulation_errors import (
        DpmRebalanceAsyncManualExecutionDisabledError,
        DpmRebalanceAsyncOperationConflictError,
        DpmRebalanceAsyncOperationError,
        DpmRebalanceAsyncOperationNotExecutableError,
        DpmRebalanceAsyncOperationNotFoundError,
        DpmRebalanceAsyncOperationSupportUnavailableError,
        DpmRebalanceAsyncOperationsDisabledError,
    )

    mappings = [
        (DpmRebalanceAsyncOperationsDisabledError("disabled"), 404, "disabled"),
        (DpmRebalanceAsyncManualExecutionDisabledError("manual-disabled"), 404, "manual-disabled"),
        (DpmRebalanceAsyncOperationNotFoundError("missing"), 404, "missing"),
        (DpmRebalanceAsyncOperationConflictError("conflict"), 409, "conflict"),
        (DpmRebalanceAsyncOperationNotExecutableError("not-executable"), 409, "not-executable"),
        (
            DpmRebalanceAsyncOperationSupportUnavailableError("support-unavailable"),
            503,
            "support-unavailable",
        ),
        (DpmRebalanceAsyncOperationError("generic"), 500, "DpmRebalanceAsyncOperationError"),
    ]

    for exc, status_code, detail in mappings:
        http_exc = rebalance_async_operation_http_exception(exc)

        assert http_exc.status_code == status_code
        assert http_exc.detail == detail


def test_simulate_durable_idempotency_cannot_be_disabled(client, monkeypatch):
    monkeypatch.setenv("DPM_IDEMPOTENCY_REPLAY_ENABLED", "false")
    payload = get_valid_payload()
    headers = {"Idempotency-Key": "test-key-idem-disabled"}

    first = client.post("/api/v1/rebalance/simulate", json=payload, headers=headers)
    second = client.post("/api/v1/rebalance/simulate", json=payload, headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["rebalance_run_id"] == second.json()["rebalance_run_id"]


def test_dpm_support_apis_lookup_by_run_correlation_and_idempotency(client):
    payload = get_valid_payload()
    headers = {"Idempotency-Key": "test-key-support-1", "X-Correlation-Id": "corr-support-1"}
    simulate = client.post("/api/v1/rebalance/simulate", json=payload, headers=headers)
    assert simulate.status_code == 200
    body = simulate.json()

    by_run = client.get(f"/api/v1/rebalance/runs/{body['rebalance_run_id']}")
    assert by_run.status_code == 200
    run_body = by_run.json()
    assert run_body["rebalance_run_id"] == body["rebalance_run_id"]
    assert run_body["correlation_id"] == "corr-support-1"
    assert run_body["idempotency_key"] == "test-key-support-1"
    assert run_body["request_hash"].startswith("sha256:")
    assert run_body["result"]["rebalance_run_id"] == body["rebalance_run_id"]
    assert run_body["portfolio_id"] == payload["portfolio_snapshot"]["portfolio_id"]
    assert run_body["result"]["lineage"]["request_hash"] == run_body["request_hash"]

    by_correlation = client.get("/api/v1/rebalance/runs/by-correlation/corr-support-1")
    assert by_correlation.status_code == 200
    correlation_body = by_correlation.json()
    assert correlation_body == run_body

    by_request_hash = client.get(
        f"/api/v1/rebalance/runs/by-request-hash/{run_body['request_hash']}"
    )
    assert by_request_hash.status_code == 200
    assert by_request_hash.json() == run_body

    by_idempotency = client.get("/api/v1/rebalance/runs/idempotency/test-key-support-1")
    assert by_idempotency.status_code == 200
    idem_body = by_idempotency.json()
    assert idem_body["idempotency_key"] == "test-key-support-1"
    assert idem_body["rebalance_run_id"] == body["rebalance_run_id"]
    assert idem_body["request_hash"] == run_body["request_hash"]
    assert idem_body["created_at"] == run_body["created_at"]

    unsupported_lookup_queries = [
        f"/api/v1/rebalance/runs/{body['rebalance_run_id']}?include_artifact=true",
        "/api/v1/rebalance/runs/by-correlation/corr-support-1?limit=1",
        f"/api/v1/rebalance/runs/by-request-hash/{run_body['request_hash']}?include_lineage=true",
        "/api/v1/rebalance/runs/idempotency/test-key-support-1?history=true",
    ]
    for url in unsupported_lookup_queries:
        unsupported = client.get(url)
        assert unsupported.status_code == 422
        assert unsupported.json()["detail"].startswith("UNSUPPORTED_QUERY_PARAMETER:")

    artifact = client.get(f"/api/v1/rebalance/runs/{body['rebalance_run_id']}/artifact")
    assert artifact.status_code == 200
    artifact_body = artifact.json()
    assert artifact_body["artifact_id"].startswith("dra_")
    assert artifact_body["artifact_version"] == "1.0"
    assert artifact_body["rebalance_run_id"] == body["rebalance_run_id"]
    assert artifact_body["correlation_id"] == "corr-support-1"
    assert artifact_body["idempotency_key"] == "test-key-support-1"
    assert artifact_body["portfolio_id"] == payload["portfolio_snapshot"]["portfolio_id"]
    assert artifact_body["status"] == body["status"]
    assert artifact_body["request_snapshot"]["request_hash"].startswith("sha256:")
    assert (
        artifact_body["request_snapshot"]["portfolio_id"]
        == payload["portfolio_snapshot"]["portfolio_id"]
    )
    assert artifact_body["evidence"]["hashes"]["request_hash"].startswith("sha256:")
    assert artifact_body["evidence"]["hashes"]["artifact_hash"].startswith("sha256:")
    expected_artifact_hash = hash_canonical_payload(
        strip_keys(artifact_body, exclude={"artifact_hash"})
    )
    assert artifact_body["evidence"]["hashes"]["artifact_hash"] == expected_artifact_hash
    assert artifact_body["result"]["rebalance_run_id"] == body["rebalance_run_id"]

    artifact_again = client.get(f"/api/v1/rebalance/runs/{body['rebalance_run_id']}/artifact")
    assert artifact_again.status_code == 200
    assert (
        artifact_again.json()["evidence"]["hashes"]["artifact_hash"]
        == artifact_body["evidence"]["hashes"]["artifact_hash"]
    )

    unsupported_query = client.get(
        f"/api/v1/rebalance/runs/{body['rebalance_run_id']}/artifact?include_lineage=true"
    )
    assert unsupported_query.status_code == 422
    assert unsupported_query.json()["detail"] == (
        "UNSUPPORTED_QUERY_PARAMETER: include_lineage not supported for this endpoint"
    )


@pytest.mark.parametrize(
    ("backend_value", "path_env_var"),
    [("SQLITE", "DPM_SUPPORTABILITY_SQLITE_PATH"), ("SQL", "DPM_SUPPORTABILITY_SQL_PATH")],
)
def test_dpm_supportability_sql_backend_selection(client, monkeypatch, backend_value, path_env_var):
    with TemporaryDirectory() as tmp_dir:
        sqlite_path = str(Path(tmp_dir) / "dpm_supportability.sqlite")
        monkeypatch.setenv("DPM_SUPPORTABILITY_STORE_BACKEND", backend_value)
        monkeypatch.setenv(path_env_var, sqlite_path)
        reset_dpm_run_support_service_for_tests()

        payload = get_valid_payload()
        headers = {
            "Idempotency-Key": "test-key-support-sqlite",
            "X-Correlation-Id": "corr-sqlite-1",
        }
        simulate = client.post("/api/v1/rebalance/simulate", json=payload, headers=headers)
        assert simulate.status_code == 503
        assert simulate.json()["detail"] == "DPM_SUPPORTABILITY_POSTGRES_CONNECTION_FAILED"


def test_dpm_support_runs_list_filters_and_cursor(client):
    payload = get_valid_payload()
    first = client.post(
        "/api/v1/rebalance/simulate",
        json=payload,
        headers={"Idempotency-Key": "test-key-runs-list-1", "X-Correlation-Id": "corr-runs-list-1"},
    )
    assert first.status_code == 200
    first_body = first.json()

    payload["options"]["single_position_max_weight"] = "0.50"
    second = client.post(
        "/api/v1/rebalance/simulate",
        json=payload,
        headers={"Idempotency-Key": "test-key-runs-list-2", "X-Correlation-Id": "corr-runs-list-2"},
    )
    assert second.status_code == 200
    second_body = second.json()

    all_rows = client.get("/api/v1/rebalance/runs?limit=10")
    assert all_rows.status_code == 200
    all_body = all_rows.json()
    ids = [item["rebalance_run_id"] for item in all_body["items"]]
    assert second_body["rebalance_run_id"] in ids
    assert first_body["rebalance_run_id"] in ids

    ready_rows = client.get("/api/v1/rebalance/runs?status_filter=READY&limit=10")
    assert ready_rows.status_code == 200
    ready_body = ready_rows.json()
    assert len(ready_body["items"]) >= 1
    assert all(item["status"] == "READY" for item in ready_body["items"])

    portfolio_rows = client.get(
        f"/api/v1/rebalance/runs?portfolio_id={payload['portfolio_snapshot']['portfolio_id']}&limit=10"
    )
    assert portfolio_rows.status_code == 200
    assert len(portfolio_rows.json()["items"]) >= 2

    first_lookup = client.get(f"/api/v1/rebalance/runs/{first_body['rebalance_run_id']}")
    assert first_lookup.status_code == 200
    first_request_hash = first_lookup.json()["request_hash"]

    request_hash_rows = client.get(
        f"/api/v1/rebalance/runs?request_hash={first_request_hash}&limit=10"
    )
    assert request_hash_rows.status_code == 200
    request_hash_body = request_hash_rows.json()
    assert len(request_hash_body["items"]) == 1
    assert request_hash_body["items"][0]["rebalance_run_id"] == first_body["rebalance_run_id"]

    page_one = client.get("/api/v1/rebalance/runs?limit=1")
    assert page_one.status_code == 200
    page_one_body = page_one.json()
    assert len(page_one_body["items"]) == 1
    assert page_one_body["next_cursor"] is not None

    page_two = client.get(f"/api/v1/rebalance/runs?limit=1&cursor={page_one_body['next_cursor']}")
    assert page_two.status_code == 200
    page_two_body = page_two.json()
    assert len(page_two_body["items"]) == 1
    assert (
        page_two_body["items"][0]["rebalance_run_id"]
        != page_one_body["items"][0]["rebalance_run_id"]
    )

    unsupported_status_alias = client.get("/api/v1/rebalance/runs?status=READY")
    assert unsupported_status_alias.status_code == 422
    assert unsupported_status_alias.json()["detail"] == (
        "UNSUPPORTED_QUERY_PARAMETER: status not supported for this endpoint"
    )


def test_dpm_support_runs_list_respects_retention_policy(client, monkeypatch):
    monkeypatch.setenv("DPM_SUPPORTABILITY_RETENTION_DAYS", "1")
    reset_dpm_run_support_service_for_tests()

    payload = get_valid_payload()
    recent = client.post(
        "/api/v1/rebalance/simulate",
        json=payload,
        headers={"Idempotency-Key": "test-key-runs-retention-recent"},
    )
    assert recent.status_code == 200
    recent_body = recent.json()
    recent_result = RebalanceResult.model_validate(recent_body)

    old_result = recent_result.model_copy(
        update={
            "rebalance_run_id": "rr_runs_retention_old",
            "correlation_id": "corr-runs-retention-old",
        }
    )
    service = get_dpm_run_support_service()
    service.record_run(
        result=old_result,
        request_hash="sha256:runs-retention-old",
        portfolio_id=payload["portfolio_snapshot"]["portfolio_id"],
        idempotency_key="idem-runs-retention-old",
        tenant_id="tenant-test",
        created_at=datetime.now(timezone.utc) - timedelta(days=2),
    )

    listed = client.get(
        f"/api/v1/rebalance/runs?portfolio_id={payload['portfolio_snapshot']['portfolio_id']}&limit=20"
    )
    assert listed.status_code == 200
    rows = listed.json()["items"]
    assert any(row["rebalance_run_id"] == recent_body["rebalance_run_id"] for row in rows)
    assert all(row["rebalance_run_id"] != "rr_runs_retention_old" for row in rows)


def test_dpm_lineage_api_disabled_and_enabled(client, monkeypatch):
    payload = get_valid_payload()
    simulate = client.post(
        "/api/v1/rebalance/simulate",
        json=payload,
        headers={"Idempotency-Key": "test-key-lineage-1", "X-Correlation-Id": "corr-lineage-api-1"},
    )
    assert simulate.status_code == 200
    run_id = simulate.json()["rebalance_run_id"]

    disabled = client.get("/api/v1/rebalance/lineage/corr-lineage-api-1")
    assert disabled.status_code == 404
    assert disabled.json()["detail"] == "DPM_LINEAGE_APIS_DISABLED"

    monkeypatch.setenv("DPM_LINEAGE_APIS_ENABLED", "true")
    reset_dpm_run_support_service_for_tests()
    simulate_enabled = client.post(
        "/api/v1/rebalance/simulate",
        json=payload,
        headers={
            "Idempotency-Key": "test-key-lineage-2",
            "X-Correlation-Id": "corr-lineage-api-2",
        },
    )
    assert simulate_enabled.status_code == 200
    run_id_enabled = simulate_enabled.json()["rebalance_run_id"]

    by_correlation = client.get("/api/v1/rebalance/lineage/corr-lineage-api-2")
    assert by_correlation.status_code == 200
    correlation_edges = by_correlation.json()["edges"]
    assert len(correlation_edges) == 1
    assert correlation_edges[0]["edge_type"] == "CORRELATION_TO_RUN"
    assert correlation_edges[0]["target_entity_id"] == run_id_enabled

    by_idempotency = client.get("/api/v1/rebalance/lineage/test-key-lineage-2")
    assert by_idempotency.status_code == 200
    idempotency_edges = by_idempotency.json()["edges"]
    assert len(idempotency_edges) == 1
    assert idempotency_edges[0]["edge_type"] == "IDEMPOTENCY_TO_RUN"
    assert idempotency_edges[0]["target_entity_id"] == run_id_enabled

    by_run = client.get(f"/api/v1/rebalance/lineage/{run_id_enabled}")
    assert by_run.status_code == 200
    run_edges = by_run.json()["edges"]
    assert len(run_edges) == 2
    assert {edge["edge_type"] for edge in run_edges} == {"CORRELATION_TO_RUN", "IDEMPOTENCY_TO_RUN"}

    assert run_id != run_id_enabled


def test_dpm_idempotency_history_api_disabled_enabled_and_history_payload(client, monkeypatch):
    payload = get_valid_payload()
    monkeypatch.setenv("DPM_IDEMPOTENCY_REPLAY_ENABLED", "false")
    simulate_one = client.post(
        "/api/v1/rebalance/simulate",
        json=payload,
        headers={"Idempotency-Key": "test-key-history-1", "X-Correlation-Id": "corr-history-1"},
    )
    assert simulate_one.status_code == 200
    run_one = simulate_one.json()["rebalance_run_id"]

    payload["options"]["single_position_max_weight"] = "0.50"
    simulate_two = client.post(
        "/api/v1/rebalance/simulate",
        json=payload,
        headers={"Idempotency-Key": "test-key-history-1", "X-Correlation-Id": "corr-history-2"},
    )
    assert simulate_two.status_code == 409
    assert simulate_two.json()["detail"] == "IDEMPOTENCY_KEY_CONFLICT: request hash mismatch"

    disabled = client.get("/api/v1/rebalance/idempotency/test-key-history-1/history")
    assert disabled.status_code == 404
    assert disabled.json()["detail"] == "DPM_IDEMPOTENCY_HISTORY_APIS_DISABLED"

    monkeypatch.setenv("DPM_IDEMPOTENCY_HISTORY_APIS_ENABLED", "true")
    history = client.get("/api/v1/rebalance/idempotency/test-key-history-1/history")
    assert history.status_code == 200
    body = history.json()
    assert body["idempotency_key"] == "test-key-history-1"
    assert len(body["history"]) == 1
    assert [event["correlation_id"] for event in body["history"]] == ["corr-history-1"]
    assert body["history"][0]["rebalance_run_id"] == run_one
    assert body["history"][0]["correlation_id"] == "corr-history-1"
    assert body["history"][0]["request_hash"].startswith("sha256:")

    missing = client.get("/api/v1/rebalance/idempotency/test-key-history-missing/history")
    assert missing.status_code == 404
    assert missing.json()["detail"] == "DPM_IDEMPOTENCY_KEY_NOT_FOUND"

    unsupported_query = client.get(
        "/api/v1/rebalance/idempotency/test-key-history-1/history?limit=1"
    )
    assert unsupported_query.status_code == 422
    assert unsupported_query.json()["detail"] == (
        "UNSUPPORTED_QUERY_PARAMETER: limit not supported for this endpoint"
    )


def test_dpm_support_apis_not_found_and_disabled(client, monkeypatch):
    missing_run = client.get("/api/v1/rebalance/runs/rr_missing")
    assert missing_run.status_code == 404
    assert missing_run.json()["detail"] == "DPM_RUN_NOT_FOUND"

    missing_correlation = client.get("/api/v1/rebalance/runs/by-correlation/corr-missing")
    assert missing_correlation.status_code == 404
    assert missing_correlation.json()["detail"] == "DPM_RUN_NOT_FOUND"

    missing_request_hash = client.get("/api/v1/rebalance/runs/by-request-hash/sha256:missing")
    assert missing_request_hash.status_code == 404
    assert missing_request_hash.json()["detail"] == "DPM_RUN_NOT_FOUND"

    missing_idem = client.get("/api/v1/rebalance/runs/idempotency/idem-missing")
    assert missing_idem.status_code == 404
    assert missing_idem.json()["detail"] == "DPM_IDEMPOTENCY_KEY_NOT_FOUND"

    missing_artifact = client.get("/api/v1/rebalance/runs/rr_missing/artifact")
    assert missing_artifact.status_code == 404
    assert missing_artifact.json()["detail"] == "DPM_RUN_NOT_FOUND"

    monkeypatch.setenv("DPM_SUPPORT_APIS_ENABLED", "false")
    disabled_urls = [
        "/api/v1/rebalance/runs/rr_missing",
        "/api/v1/rebalance/runs/by-correlation/corr-missing",
        "/api/v1/rebalance/runs/by-request-hash/sha256:missing",
        "/api/v1/rebalance/runs/idempotency/idem-missing",
    ]
    for url in disabled_urls:
        disabled = client.get(url)
        assert disabled.status_code == 404
        assert disabled.json()["detail"] == "DPM_SUPPORT_APIS_DISABLED"

    monkeypatch.setenv("DPM_SUPPORT_APIS_ENABLED", "true")
    monkeypatch.setenv("DPM_ARTIFACTS_ENABLED", "false")
    artifact_disabled = client.get("/api/v1/rebalance/runs/rr_missing/artifact")
    assert artifact_disabled.status_code == 404
    assert artifact_disabled.json()["detail"] == "DPM_ARTIFACTS_DISABLED"

    monkeypatch.setenv("DPM_ARTIFACTS_ENABLED", "true")
    monkeypatch.setenv("DPM_ARTIFACT_STORE_MODE", "PERSISTED")
    artifact_mode_enabled = client.get("/api/v1/rebalance/runs/rr_missing/artifact")
    assert artifact_mode_enabled.status_code == 404
    assert artifact_mode_enabled.json()["detail"] == "DPM_RUN_NOT_FOUND"

    monkeypatch.setenv("DPM_ARTIFACT_STORE_MODE", "UNKNOWN_MODE")
    artifact_mode_fallback = client.get("/api/v1/rebalance/runs/rr_missing/artifact")
    assert artifact_mode_fallback.status_code == 404
    assert artifact_mode_fallback.json()["detail"] == "DPM_RUN_NOT_FOUND"


def test_dpm_support_repository_backend_init_errors_return_503(client, monkeypatch):
    monkeypatch.setenv("DPM_SUPPORTABILITY_STORE_BACKEND", "POSTGRES")
    monkeypatch.delenv("DPM_SUPPORTABILITY_POSTGRES_DSN", raising=False)
    reset_dpm_run_support_service_for_tests()

    missing_dsn = client.get("/api/v1/rebalance/runs?limit=1")
    assert missing_dsn.status_code == 503
    assert missing_dsn.json()["detail"] == "DPM_SUPPORTABILITY_POSTGRES_DSN_REQUIRED"

    monkeypatch.setenv(
        "DPM_SUPPORTABILITY_POSTGRES_DSN",
        "postgresql://user:pass@localhost:5432/dpm",
    )
    monkeypatch.setattr(
        "src.api.services.rebalance_run_support_repository.PostgresDpmRunRepository",
        lambda *args, **kwargs: (_ for _ in ()).throw(ConnectionError("boom")),
    )
    reset_dpm_run_support_service_for_tests()
    missing_driver = client.get("/api/v1/rebalance/runs?limit=1")
    assert missing_driver.status_code == 503
    assert missing_driver.json()["detail"] == "DPM_SUPPORTABILITY_POSTGRES_CONNECTION_FAILED"


def test_dpm_async_operation_lookup_not_found_and_disabled(client, monkeypatch):
    missing = client.get("/api/v1/rebalance/operations/dop_missing")
    assert missing.status_code == 404
    assert missing.json()["detail"] == "DPM_ASYNC_OPERATION_NOT_FOUND"

    missing_by_corr = client.get("/api/v1/rebalance/operations/by-correlation/corr-missing")
    assert missing_by_corr.status_code == 404
    assert missing_by_corr.json()["detail"] == "DPM_ASYNC_OPERATION_NOT_FOUND"

    monkeypatch.setenv("DPM_ASYNC_OPERATIONS_ENABLED", "false")
    disabled = client.get("/api/v1/rebalance/operations/dop_missing")
    assert disabled.status_code == 404
    assert disabled.json()["detail"] == "DPM_ASYNC_OPERATIONS_DISABLED"


def test_dpm_async_operation_lookup_by_id_and_correlation(client):
    service = get_dpm_run_support_service()
    accepted = service.submit_analyze_async(
        tenant_id="tenant-test",
        correlation_id="corr-dpm-async-support-1",
        request_json={"scenarios": {"baseline": {"options": {}}}},
    )

    by_operation = client.get(f"/api/v1/rebalance/operations/{accepted.operation_id}")
    assert by_operation.status_code == 200
    by_operation_body = by_operation.json()
    assert by_operation_body["operation_id"] == accepted.operation_id
    assert by_operation_body["operation_type"] == "ANALYZE_SCENARIOS"
    assert by_operation_body["status"] == "PENDING"
    assert by_operation_body["is_executable"] is True
    assert by_operation_body["correlation_id"] == "corr-dpm-async-support-1"
    assert by_operation_body["result"] is None
    assert by_operation_body["error"] is None

    by_correlation = client.get(
        "/api/v1/rebalance/operations/by-correlation/corr-dpm-async-support-1"
    )
    assert by_correlation.status_code == 200
    assert by_correlation.json()["operation_id"] == accepted.operation_id


def test_dpm_async_operations_are_non_disclosing_and_correlation_is_tenant_scoped(client):
    service = get_dpm_run_support_service()
    tenant_a = service.submit_analyze_async(
        tenant_id="tenant-a",
        correlation_id="corr-shared-across-tenants",
        request_json={"scenarios": {"baseline": {"options": {}}}},
    )
    tenant_b = service.submit_analyze_async(
        tenant_id="tenant-b",
        correlation_id="corr-shared-across-tenants",
        request_json={"scenarios": {"baseline": {"options": {}}}},
    )

    assert (
        client.get(
            f"/api/v1/rebalance/operations/{tenant_a.operation_id}",
            headers={"X-Tenant-Id": "tenant-b"},
        ).status_code
        == 404
    )
    by_correlation = client.get(
        "/api/v1/rebalance/operations/by-correlation/corr-shared-across-tenants",
        headers={"X-Tenant-Id": "tenant-b"},
    )
    assert by_correlation.status_code == 200
    assert by_correlation.json()["operation_id"] == tenant_b.operation_id
    inventory = client.get(
        "/api/v1/rebalance/operations",
        headers={"X-Tenant-Id": "tenant-b"},
    )
    assert inventory.status_code == 200
    assert [item["operation_id"] for item in inventory.json()["items"]] == [tenant_b.operation_id]


def test_dpm_async_operation_lookup_by_id_returns_typed_terminal_result(client):
    payload = get_valid_payload()
    payload.pop("options")
    payload["scenarios"] = {
        "baseline": {"options": {}},
        "invalid_case": {"options": {"group_constraints": {"sectorTECH": {"max_weight": "0.2"}}}},
    }

    accepted = client.post(
        "/api/v1/rebalance/analyze/async",
        json=payload,
        headers={"X-Correlation-Id": "corr-dpm-async-terminal-detail"},
    )
    assert accepted.status_code == 202
    operation_id = accepted.json()["operation_id"]

    by_operation = client.get(f"/api/v1/rebalance/operations/{operation_id}")

    assert by_operation.status_code == 200
    typed_status = DpmAsyncOperationStatusResponse.model_validate(by_operation.json())
    assert typed_status.operation_id == operation_id
    assert typed_status.status == "SUCCEEDED"
    assert typed_status.is_executable is False
    assert typed_status.error is None
    assert typed_status.result is not None
    typed_result = BatchRebalanceResult.model_validate(typed_status.result)
    assert set(typed_result.results) == {"baseline"}
    assert set(typed_result.comparison_metrics) == {"baseline"}
    assert set(typed_result.failed_scenarios) == {"invalid_case"}
    assert "PARTIAL_BATCH_FAILURE" in typed_result.warnings


def test_dpm_async_operation_lookup_by_correlation_returns_typed_terminal_result(client):
    payload = get_valid_payload()
    payload.pop("options")
    payload["scenarios"] = {"baseline": {"options": {}}}
    correlation_id = "corr-dpm-async-correlation-terminal-detail"

    accepted = client.post(
        "/api/v1/rebalance/analyze/async",
        json=payload,
        headers={"X-Correlation-Id": correlation_id},
    )
    assert accepted.status_code == 202
    operation_id = accepted.json()["operation_id"]

    by_correlation = client.get(f"/api/v1/rebalance/operations/by-correlation/{correlation_id}")

    assert by_correlation.status_code == 200
    typed_status = DpmAsyncOperationStatusResponse.model_validate(by_correlation.json())
    assert typed_status.operation_id == operation_id
    assert typed_status.correlation_id == correlation_id
    assert typed_status.status == "SUCCEEDED"
    assert typed_status.is_executable is False
    assert typed_status.error is None
    assert typed_status.result is not None
    typed_result = BatchRebalanceResult.model_validate(typed_status.result)
    assert set(typed_result.results) == {"baseline"}
    assert set(typed_result.failed_scenarios) == set()


def test_dpm_async_operation_list_rejects_unsupported_query_parameters(client):
    response = client.get("/api/v1/rebalance/operations?status=SUCCEEDED")

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "UNSUPPORTED_QUERY_PARAMETER: status not supported for this endpoint"
    )


def test_dpm_async_operation_list_filters_and_cursor(client):
    service = get_dpm_run_support_service()
    one = service.submit_analyze_async(
        tenant_id="tenant-test",
        correlation_id="corr-dpm-ops-list-1",
        request_json={"scenarios": {"baseline": {"options": {}}}},
    )
    two = service.submit_analyze_async(
        tenant_id="tenant-test",
        correlation_id="corr-dpm-ops-list-2",
        request_json={"scenarios": {"baseline": {"options": {}}}},
    )

    pending = client.get("/api/v1/rebalance/operations?status_filter=PENDING&limit=10")
    assert pending.status_code == 200
    pending_body = pending.json()
    assert any(item["operation_id"] == one.operation_id for item in pending_body["items"])
    assert any(item["operation_id"] == two.operation_id for item in pending_body["items"])
    assert all(item["status"] == "PENDING" for item in pending_body["items"])

    by_correlation = client.get(
        "/api/v1/rebalance/operations?correlation_id=corr-dpm-ops-list-1&limit=10"
    )
    assert by_correlation.status_code == 200
    correlation_body = by_correlation.json()
    assert len(correlation_body["items"]) == 1
    assert correlation_body["items"][0]["operation_id"] == one.operation_id
    assert correlation_body["items"][0]["is_executable"] is True

    page_one = client.get("/api/v1/rebalance/operations?limit=1")
    assert page_one.status_code == 200
    page_one_body = page_one.json()
    assert len(page_one_body["items"]) == 1
    assert page_one_body["next_cursor"] is not None
    page_two = client.get(
        f"/api/v1/rebalance/operations?limit=1&cursor={page_one_body['next_cursor']}"
    )
    assert page_two.status_code == 200
    page_two_body = page_two.json()
    assert len(page_two_body["items"]) == 1
    assert page_one_body["items"][0]["operation_id"] != page_two_body["items"][0]["operation_id"]


def test_dpm_async_operation_list_filters_by_created_window_and_operation_type(client):
    service = get_dpm_run_support_service()
    now = datetime.now(timezone.utc)
    old_created_at = now - timedelta(hours=3)
    in_window_created_at = now - timedelta(hours=1)
    out_of_window_created_at = now + timedelta(hours=1)
    old = service.submit_analyze_async(
        tenant_id="tenant-test",
        correlation_id="corr-dpm-ops-old",
        request_json={"scenarios": {"baseline": {"options": {}}}},
        created_at=old_created_at,
    )
    in_window = service.submit_analyze_async(
        tenant_id="tenant-test",
        correlation_id="corr-dpm-ops-window",
        request_json={"scenarios": {"baseline": {"options": {}}}},
        created_at=in_window_created_at,
    )
    future = service.submit_analyze_async(
        tenant_id="tenant-test",
        correlation_id="corr-dpm-ops-future",
        request_json={"scenarios": {"baseline": {"options": {}}}},
        created_at=out_of_window_created_at,
    )

    response = client.get(
        "/api/v1/rebalance/operations",
        params={
            "created_from": (now - timedelta(hours=2)).isoformat(),
            "created_to": now.isoformat(),
            "operation_type": "ANALYZE_SCENARIOS",
            "status_filter": "PENDING",
            "limit": 10,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert [item["operation_id"] for item in body["items"]] == [in_window.operation_id]
    assert old.operation_id not in {item["operation_id"] for item in body["items"]}
    assert future.operation_id not in {item["operation_id"] for item in body["items"]}
    assert body["items"][0]["operation_type"] == "ANALYZE_SCENARIOS"
    assert body["items"][0]["status"] == "PENDING"


def test_dpm_async_operation_ttl_expiry_by_id_and_correlation(client, monkeypatch):
    monkeypatch.setenv("DPM_ASYNC_OPERATIONS_TTL_SECONDS", "1")
    reset_dpm_run_support_service_for_tests()
    service = get_dpm_run_support_service()
    accepted = service.submit_analyze_async(
        tenant_id="tenant-test",
        correlation_id="corr-dpm-async-ttl-expired",
        request_json={"scenarios": {"baseline": {"options": {}}}},
        created_at=datetime.now(timezone.utc) - timedelta(seconds=10),
    )

    by_operation = client.get(f"/api/v1/rebalance/operations/{accepted.operation_id}")
    assert by_operation.status_code == 404
    assert by_operation.json()["detail"] == "DPM_ASYNC_OPERATION_NOT_FOUND"

    by_correlation = client.get(
        "/api/v1/rebalance/operations/by-correlation/corr-dpm-async-ttl-expired"
    )
    assert by_correlation.status_code == 404
    assert by_correlation.json()["detail"] == "DPM_ASYNC_OPERATION_NOT_FOUND"

    bundle = client.get(
        f"/api/v1/rebalance/runs/by-operation/{accepted.operation_id}/support-bundle"
    )
    assert bundle.status_code == 404
    assert bundle.json()["detail"] == "DPM_ASYNC_OPERATION_NOT_FOUND"


def test_dpm_supportability_summary_endpoint(client):
    payload = get_valid_payload()
    simulate = client.post(
        "/api/v1/rebalance/simulate",
        json=payload,
        headers={
            "Idempotency-Key": "test-key-support-summary-1",
            "X-Correlation-Id": "corr-support-summary-run-1",
        },
    )
    assert simulate.status_code == 200

    service = get_dpm_run_support_service()
    service.submit_analyze_async(
        tenant_id="tenant-test",
        correlation_id="corr-support-summary-op-1",
        request_json={"scenarios": {"baseline": {"options": {}}}},
    )

    response = client.get("/api/v1/rebalance/supportability/summary")
    assert response.status_code == 200
    body = response.json()
    assert body["store_backend"] == "POSTGRES"
    assert body["retention_days"] == 0
    assert body["run_count"] == 1
    assert body["operation_count"] == 1
    assert body["run_status_counts"] == {"READY": 1}
    assert body["operation_status_counts"] == {"PENDING": 1}
    assert body["workflow_decision_count"] == 0
    assert body["workflow_action_counts"] == {}
    assert body["workflow_reason_code_counts"] == {}
    assert body["lineage_edge_count"] == 3
    assert body["portfolio_id"] is None
    assert body["portfolio_scope_confirmed"] is False
    assert body["evidence_as_of_date"] is None
    assert body["producer_generated_at"].endswith("+00:00")
    assert body["temporal_identity_status"] == "store_wide"
    assert body["oldest_run_created_at"] is not None
    assert body["newest_run_created_at"] is not None
    assert body["oldest_operation_created_at"] is not None
    assert body["newest_operation_created_at"] is not None
    assert body["supportability"] == {
        "state": "ready",
        "reason": "supportability_summary_ready",
        "freshness_bucket": "current",
        "temporal_identity_status": "store_wide",
        "evidence_as_of_date": None,
        "producer_generated_at": body["producer_generated_at"],
        "run_count": 1,
        "operation_count": 1,
        "workflow_decision_count": 0,
        "portfolio_id": None,
        "portfolio_scope_confirmed": False,
    }

    metrics = client.get("/metrics")
    assert metrics.status_code == 200
    assert "lotus_manage_action_register_supportability_total" in metrics.text
    assert 'surface="rebalance/supportability/summary"' in metrics.text
    assert 'supportability_state="ready"' in metrics.text
    assert 'reason="supportability_summary_ready"' in metrics.text
    assert 'freshness_bucket="current"' in metrics.text


def test_dpm_supportability_summary_endpoint_disabled(client, monkeypatch):
    monkeypatch.setenv("DPM_SUPPORTABILITY_SUMMARY_APIS_ENABLED", "false")
    response = client.get("/api/v1/rebalance/supportability/summary")
    assert response.status_code == 404
    assert response.json()["detail"] == "DPM_SUPPORTABILITY_SUMMARY_APIS_DISABLED"


def test_dpm_supportability_summary_backend_init_error_returns_503(client, monkeypatch):
    monkeypatch.setenv("DPM_SUPPORTABILITY_STORE_BACKEND", "POSTGRES")
    monkeypatch.delenv("DPM_SUPPORTABILITY_POSTGRES_DSN", raising=False)
    reset_dpm_run_support_service_for_tests()

    response = client.get("/api/v1/rebalance/supportability/summary")

    assert response.status_code == 503
    assert response.json()["detail"] == "DPM_SUPPORTABILITY_POSTGRES_DSN_REQUIRED"


def test_dpm_supportability_summary_rejects_unexpected_query_params(client):
    response = client.get("/api/v1/rebalance/supportability/summary?status=READY")
    assert response.status_code == 422
    assert response.json()["detail"] == (
        "UNSUPPORTED_QUERY_PARAMETER: status not supported for this endpoint"
    )


def test_dpm_supportability_summary_includes_workflow_aggregates(client, monkeypatch):
    monkeypatch.setenv("DPM_WORKFLOW_ENABLED", "true")
    payload = get_valid_payload()
    payload["options"]["single_position_max_weight"] = "0.5"
    simulate = client.post(
        "/api/v1/rebalance/simulate",
        json=payload,
        headers={
            "Idempotency-Key": "test-key-support-summary-workflow-1",
            "X-Correlation-Id": "corr-support-summary-workflow-1",
        },
    )
    assert simulate.status_code == 200
    run_id = simulate.json()["rebalance_run_id"]

    action = client.post(
        f"/api/v1/rebalance/runs/{run_id}/workflow/actions",
        json={
            "action": "APPROVE",
            "reason_code": "REVIEW_APPROVED",
            "actor_id": "reviewer_summary",
        },
        headers={"X-Correlation-Id": "corr-support-summary-workflow-action-1"},
    )
    assert action.status_code == 200

    response = client.get("/api/v1/rebalance/supportability/summary")
    assert response.status_code == 200
    body = response.json()
    assert body["workflow_decision_count"] == 1
    assert body["workflow_action_counts"] == {"APPROVE": 1}
    assert body["workflow_reason_code_counts"] == {"REVIEW_APPROVED": 1}


def test_dpm_run_support_bundle_endpoint(client):
    payload = get_valid_payload()
    simulate = client.post(
        "/api/v1/rebalance/simulate",
        json=payload,
        headers={
            "Idempotency-Key": "test-key-support-bundle-1",
            "X-Correlation-Id": "corr-support-bundle-1",
        },
    )
    assert simulate.status_code == 200
    run_id = simulate.json()["rebalance_run_id"]

    service = get_dpm_run_support_service()
    service.submit_analyze_async(
        tenant_id="tenant-test",
        correlation_id="corr-support-bundle-1",
        request_json={"scenarios": {"baseline": {"options": {}}}},
    )

    response = client.get(f"/api/v1/rebalance/runs/{run_id}/support-bundle")
    assert response.status_code == 200
    body = response.json()
    assert body["run"]["rebalance_run_id"] == run_id
    assert body["run"]["correlation_id"] == "corr-support-bundle-1"
    assert body["artifact"] is not None
    assert body["artifact"]["rebalance_run_id"] == run_id
    # A matching correlation on an unrelated synchronous run is not membership.
    assert body["async_operation"] is None
    assert body["workflow_history"]["run_id"] == run_id
    assert body["workflow_history"]["decisions"] == []
    assert body["lineage"]["entity_id"] == run_id
    assert len(body["lineage"]["edges"]) == 2
    assert body["idempotency_history"] is not None
    assert body["idempotency_history"]["idempotency_key"] == "test-key-support-bundle-1"
    assert len(body["idempotency_history"]["history"]) == 1

    compact = client.get(
        f"/api/v1/rebalance/runs/{run_id}/support-bundle"
        "?include_artifact=false&include_async_operation=false&include_idempotency_history=false"
    )
    assert compact.status_code == 200
    compact_body = compact.json()
    assert compact_body["artifact"] is None
    assert compact_body["async_operation"] is None
    assert compact_body["idempotency_history"] is None
    assert compact_body["lineage"]["entity_id"] == run_id
    assert compact_body["workflow_history"]["run_id"] == run_id

    unsupported_query = client.get(
        f"/api/v1/rebalance/runs/{run_id}/support-bundle?include_lineage=false"
    )
    assert unsupported_query.status_code == 422
    assert unsupported_query.json()["detail"] == (
        "UNSUPPORTED_QUERY_PARAMETER: include_lineage not supported for this endpoint"
    )


def test_dpm_run_support_bundle_endpoint_by_correlation_and_idempotency(client):
    payload = get_valid_payload()
    simulate = client.post(
        "/api/v1/rebalance/simulate",
        json=payload,
        headers={
            "Idempotency-Key": "test-key-support-bundle-2",
            "X-Correlation-Id": "corr-support-bundle-2",
        },
    )
    assert simulate.status_code == 200
    run_id = simulate.json()["rebalance_run_id"]

    by_correlation = client.get(
        "/api/v1/rebalance/runs/by-correlation/corr-support-bundle-2/support-bundle"
    )
    assert by_correlation.status_code == 200
    by_correlation_body = by_correlation.json()
    assert by_correlation_body["run"]["rebalance_run_id"] == run_id
    assert by_correlation_body["run"]["correlation_id"] == "corr-support-bundle-2"

    by_idempotency = client.get(
        "/api/v1/rebalance/runs/idempotency/test-key-support-bundle-2/support-bundle"
    )
    assert by_idempotency.status_code == 200
    by_idempotency_body = by_idempotency.json()
    assert by_idempotency_body["run"]["rebalance_run_id"] == run_id
    assert by_idempotency_body["idempotency_history"] is not None
    assert (
        by_idempotency_body["idempotency_history"]["idempotency_key"] == "test-key-support-bundle-2"
    )

    missing_by_correlation = client.get(
        "/api/v1/rebalance/runs/by-correlation/corr_missing/support-bundle"
    )
    assert missing_by_correlation.status_code == 404
    assert missing_by_correlation.json()["detail"] == "DPM_RUN_NOT_FOUND"

    missing_by_idempotency = client.get(
        "/api/v1/rebalance/runs/idempotency/idem_missing/support-bundle"
    )
    assert missing_by_idempotency.status_code == 404
    assert missing_by_idempotency.json()["detail"] == "DPM_IDEMPOTENCY_KEY_NOT_FOUND"

    unsupported_by_correlation = client.get(
        "/api/v1/rebalance/runs/by-correlation/corr-support-bundle-2/support-bundle?lineage=true"
    )
    assert unsupported_by_correlation.status_code == 422
    assert unsupported_by_correlation.json()["detail"] == (
        "UNSUPPORTED_QUERY_PARAMETER: lineage not supported for this endpoint"
    )


def test_dpm_run_support_bundle_endpoint_by_operation(client, monkeypatch):
    monkeypatch.setenv("DPM_ASYNC_EXECUTION_MODE", "ACCEPT_ONLY")
    unrelated = client.post(
        "/api/v1/rebalance/simulate",
        json=get_valid_payload(),
        headers={
            "X-Correlation-Id": "corr-support-bundle-3",
            "Idempotency-Key": "idem-unrelated-support-bundle-3",
        },
    )
    assert unrelated.status_code == 200
    unrelated_id = unrelated.json()["rebalance_run_id"]
    payload = get_valid_payload()
    payload.pop("options")
    payload["scenarios"] = {"baseline": {"options": {}}, "alternative": {"options": {}}}
    accepted = client.post(
        "/api/v1/rebalance/analyze/async",
        json=payload,
        headers={"X-Correlation-Id": "corr-support-bundle-3"},
    )
    assert accepted.status_code == 202
    operation_id = accepted.json()["operation_id"]
    executed = client.post(f"/api/v1/rebalance/operations/{operation_id}/execute")
    assert executed.status_code == 200
    assert executed.json()["status"] == "SUCCEEDED"

    by_operation = client.get(f"/api/v1/rebalance/runs/by-operation/{operation_id}/support-bundle")
    assert by_operation.status_code == 200
    by_operation_body = by_operation.json()
    assert by_operation_body["operation_id"] == operation_id
    assert by_operation_body["async_operation"] is not None
    assert by_operation_body["async_operation"]["operation_id"] == operation_id
    assert by_operation_body["historical_runs"] == []
    assert set(by_operation_body["scenarios"]) == {"baseline", "alternative"}
    for scenario_key, evidence in by_operation_body["scenarios"].items():
        assert evidence["status"] == "succeeded"
        run_id = evidence["bundle"]["run"]["rebalance_run_id"]
        assert run_id == executed.json()["result"]["results"][scenario_key]["rebalance_run_id"]
        direct = client.get(f"/api/v1/rebalance/runs/{run_id}/support-bundle")
        assert direct.status_code == 200
        assert direct.json()["async_operation"]["operation_id"] == operation_id
        assert run_id != unrelated_id
    assert (
        client.get(f"/api/v1/rebalance/runs/{unrelated_id}/support-bundle").json()[
            "async_operation"
        ]
        is None
    )

    omitted = client.get(
        f"/api/v1/rebalance/runs/by-operation/{operation_id}/support-bundle"
        "?include_artifact=false&include_async_operation=false&include_idempotency_history=false"
    )
    assert omitted.status_code == 200
    assert omitted.json()["async_operation"] is None
    for evidence in omitted.json()["scenarios"].values():
        assert evidence["bundle"]["artifact"] is None
        assert evidence["bundle"]["async_operation"] is None
        assert evidence["bundle"]["idempotency_history"] is None

    foreign = client.get(
        f"/api/v1/rebalance/runs/by-operation/{operation_id}/support-bundle",
        headers={"X-Tenant-Id": "another-tenant"},
    )
    assert foreign.status_code == 404
    assert foreign.json()["detail"] == "DPM_ASYNC_OPERATION_NOT_FOUND"

    missing = client.get("/api/v1/rebalance/runs/by-operation/dop_missing/support-bundle")
    assert missing.status_code == 404
    assert missing.json()["detail"] == "DPM_ASYNC_OPERATION_NOT_FOUND"

    unsupported_by_operation = client.get(
        f"/api/v1/rebalance/runs/by-operation/{operation_id}/support-bundle?artifact=false"
    )
    assert unsupported_by_operation.status_code == 422
    assert unsupported_by_operation.json()["detail"] == (
        "UNSUPPORTED_QUERY_PARAMETER: artifact not supported for this endpoint"
    )


def test_operation_support_bundle_exposes_partial_failure_without_inventing_run(
    client, monkeypatch
):
    monkeypatch.setenv("DPM_ASYNC_EXECUTION_MODE", "ACCEPT_ONLY")
    payload = get_valid_payload()
    payload.pop("options")
    payload["scenarios"] = {
        "baseline": {"options": {}},
        "invalid": {"options": {"max_turnover_pct": "-1"}},
    }
    accepted = client.post("/api/v1/rebalance/analyze/async", json=payload)
    assert accepted.status_code == 202
    operation_id = accepted.json()["operation_id"]
    executed = client.post(f"/api/v1/rebalance/operations/{operation_id}/execute")
    assert executed.status_code == 200
    assert executed.json()["status"] == "SUCCEEDED"
    bundle = client.get(f"/api/v1/rebalance/runs/by-operation/{operation_id}/support-bundle")
    assert bundle.status_code == 200
    scenarios = bundle.json()["scenarios"]
    assert scenarios["baseline"]["status"] == "succeeded"
    assert scenarios["invalid"]["status"] == "failed"
    assert scenarios["invalid"]["bundle"] is None
    assert scenarios["invalid"]["error"].startswith("INVALID_OPTIONS")


def test_dpm_run_support_bundle_endpoint_disabled_and_not_found(client, monkeypatch):
    missing = client.get("/api/v1/rebalance/runs/rr_missing/support-bundle")
    assert missing.status_code == 404
    assert missing.json()["detail"] == "DPM_RUN_NOT_FOUND"

    monkeypatch.setenv("DPM_SUPPORT_BUNDLE_APIS_ENABLED", "false")
    disabled = client.get("/api/v1/rebalance/runs/rr_missing/support-bundle")
    assert disabled.status_code == 404
    assert disabled.json()["detail"] == "DPM_SUPPORT_BUNDLE_APIS_DISABLED"
    disabled_operation = client.get(
        "/api/v1/rebalance/runs/by-operation/dop_missing/support-bundle"
    )
    assert disabled_operation.status_code == 404
    assert disabled_operation.json()["detail"] == "DPM_SUPPORT_BUNDLE_APIS_DISABLED"


def test_dpm_run_support_service_env_parsing_defaults(monkeypatch):
    monkeypatch.setenv("DPM_ASYNC_OPERATIONS_TTL_SECONDS", "not-an-int")
    monkeypatch.setenv("DPM_ASYNC_EXECUTION_LEASE_SECONDS", "not-an-int")
    monkeypatch.setenv("DPM_SUPPORTABILITY_RETENTION_DAYS", "not-an-int")
    monkeypatch.setenv("DPM_WORKFLOW_ENABLED", "true")
    monkeypatch.setenv("DPM_WORKFLOW_REQUIRES_REVIEW_FOR_STATUSES", " , ")
    dpm_runs_router._REPOSITORY = None
    dpm_runs_router._SERVICE = None

    service = get_dpm_run_support_service()
    assert service._async_operation_ttl_seconds == 86400
    assert service._async_execution_lease_seconds == 300
    assert service._supportability_retention_days == 0
    assert service._workflow_enabled is True
    assert service._workflow_requires_review_for_statuses == {"PENDING_REVIEW"}


def test_dpm_workflow_router_not_found_mappings(client, monkeypatch):
    monkeypatch.setenv("DPM_WORKFLOW_ENABLED", "true")

    by_run = client.get("/api/v1/rebalance/runs/rr_missing/workflow")
    assert by_run.status_code == 404
    assert by_run.json()["detail"] == "DPM_RUN_NOT_FOUND"

    history_by_run = client.get("/api/v1/rebalance/runs/rr_missing/workflow/history")
    assert history_by_run.status_code == 404
    assert history_by_run.json()["detail"] == "DPM_RUN_NOT_FOUND"

    history_by_correlation = client.get(
        "/api/v1/rebalance/runs/by-correlation/corr_missing/workflow/history"
    )
    assert history_by_correlation.status_code == 404
    assert history_by_correlation.json()["detail"] == "DPM_RUN_NOT_FOUND"
    decisions_by_correlation = client.get(
        "/api/v1/rebalance/workflow/decisions/by-correlation/corr_missing"
    )
    assert decisions_by_correlation.status_code == 404
    assert decisions_by_correlation.json()["detail"] == "DPM_RUN_NOT_FOUND"

    history_by_idempotency = client.get(
        "/api/v1/rebalance/runs/idempotency/idem_missing/workflow/history"
    )
    assert history_by_idempotency.status_code == 404
    assert history_by_idempotency.json()["detail"] == "DPM_IDEMPOTENCY_KEY_NOT_FOUND"


def test_dpm_workflow_action_router_exception_mappings(client, monkeypatch):
    monkeypatch.setenv("DPM_WORKFLOW_ENABLED", "true")
    payload = {
        "action": "APPROVE",
        "reason_code": "REVIEW_APPROVED",
        "actor_id": "reviewer_001",
    }

    with patch.object(
        dpm_runs_router.DpmRunSupportService,
        "apply_workflow_action_for_tenant",
        side_effect=DpmRunNotFoundError("DPM_RUN_NOT_FOUND"),
    ):
        not_found = client.post("/api/v1/rebalance/runs/rr_missing/workflow/actions", json=payload)
    assert not_found.status_code == 404
    assert not_found.json()["detail"] == "DPM_RUN_NOT_FOUND"

    with patch.object(
        dpm_runs_router.DpmRunSupportService,
        "apply_workflow_action_for_tenant",
        side_effect=DpmWorkflowDisabledError("DPM_WORKFLOW_DISABLED"),
    ):
        disabled = client.post("/api/v1/rebalance/runs/rr_missing/workflow/actions", json=payload)
    assert disabled.status_code == 404
    assert disabled.json()["detail"] == "DPM_WORKFLOW_DISABLED"

    with patch.object(
        dpm_runs_router.DpmRunSupportService,
        "apply_workflow_action_by_correlation_for_tenant",
        side_effect=DpmWorkflowTransitionError("DPM_WORKFLOW_INVALID_TRANSITION"),
    ):
        transition = client.post(
            "/api/v1/rebalance/runs/by-correlation/corr_missing/workflow/actions",
            json=payload,
        )
    assert transition.status_code == 409
    assert transition.json()["detail"] == "DPM_WORKFLOW_INVALID_TRANSITION"

    with patch.object(
        dpm_runs_router.DpmRunSupportService,
        "apply_workflow_action_by_correlation_for_tenant",
        side_effect=DpmWorkflowDisabledError("DPM_WORKFLOW_DISABLED"),
    ):
        disabled_by_correlation = client.post(
            "/api/v1/rebalance/runs/by-correlation/corr_missing/workflow/actions",
            json=payload,
        )
    assert disabled_by_correlation.status_code == 404
    assert disabled_by_correlation.json()["detail"] == "DPM_WORKFLOW_DISABLED"

    missing_idempotency = client.post(
        "/api/v1/rebalance/runs/idempotency/idem_missing/workflow/actions",
        json=payload,
    )
    assert missing_idempotency.status_code == 404
    assert missing_idempotency.json()["detail"] == "DPM_IDEMPOTENCY_KEY_NOT_FOUND"

    with patch.object(
        dpm_runs_router.DpmRunSupportService,
        "apply_workflow_action_by_idempotency_for_tenant",
        side_effect=DpmWorkflowDisabledError("DPM_WORKFLOW_DISABLED"),
    ):
        disabled_idem = client.post(
            "/api/v1/rebalance/runs/idempotency/idem_any/workflow/actions",
            json=payload,
        )
    assert disabled_idem.status_code == 404
    assert disabled_idem.json()["detail"] == "DPM_WORKFLOW_DISABLED"

    with patch.object(
        dpm_runs_router.DpmRunSupportService,
        "apply_workflow_action_by_idempotency_for_tenant",
        side_effect=DpmWorkflowTransitionError("DPM_WORKFLOW_INVALID_TRANSITION"),
    ):
        transition_idem = client.post(
            "/api/v1/rebalance/runs/idempotency/idem_any/workflow/actions",
            json=payload,
        )
    assert transition_idem.status_code == 409
    assert transition_idem.json()["detail"] == "DPM_WORKFLOW_INVALID_TRANSITION"


def test_simulate_generates_correlation_id_when_header_missing(client):
    payload = get_valid_payload()
    response = client.post(
        "/api/v1/rebalance/simulate",
        json=payload,
        headers={"Idempotency-Key": "test-key-corr-none"},
    )
    assert response.status_code == 200
    assert response.json()["correlation_id"].startswith("corr_")


def test_simulate_returns_503_when_idempotency_store_write_fails(client):
    payload = get_valid_payload()
    with patch(
        "src.core.rebalance_runs.DpmRunSupportService.complete_simulation_submission",
        side_effect=RuntimeError("boom"),
    ):
        response = client.post(
            "/api/v1/rebalance/simulate",
            json=payload,
            headers={"Idempotency-Key": "test-key-supportability-error"},
        )
    assert response.status_code == 503
    assert response.json()["detail"] == "DPM_IDEMPOTENCY_STORE_WRITE_FAILED"


def test_simulate_returns_503_when_idempotency_lookup_points_to_missing_run(client):
    payload = get_valid_payload()

    class _InconsistentIdempotencyService:
        def claim_simulation_submission(self, **kwargs):
            return SimpleNamespace(
                request_hash="sha256:matches",
                status="COMPLETED",
                claim_token="winner",
                rebalance_run_id="rr_missing_for_idem",
            )

        def get_run_for_tenant(self, *, tenant_id, rebalance_run_id):
            raise DpmRunNotFoundError("DPM_RUN_NOT_FOUND")

    with (
        patch(
            "src.api.services.rebalance_simulation_service.hash_canonical_payload",
            return_value="sha256:matches",
        ),
        patch(
            "src.api.services.rebalance_simulation_service.get_dpm_run_support_service",
            return_value=_InconsistentIdempotencyService(),
        ),
    ):
        response = client.post(
            "/api/v1/rebalance/simulate",
            json=payload,
            headers={"Idempotency-Key": "test-key-idem-store-inconsistent"},
        )
    assert response.status_code == 503
    assert response.json()["detail"] == "DPM_IDEMPOTENCY_STORE_INCONSISTENT"


def test_simulate_keeps_durable_persistence_mandatory_when_replay_flag_is_disabled(
    client, monkeypatch
):
    monkeypatch.setenv("DPM_IDEMPOTENCY_REPLAY_ENABLED", "false")
    payload = get_valid_payload()
    with patch(
        "src.core.rebalance_runs.DpmRunSupportService.complete_simulation_submission",
        side_effect=RuntimeError("boom"),
    ):
        response = client.post(
            "/api/v1/rebalance/simulate",
            json=payload,
            headers={"Idempotency-Key": "test-key-supportability-error-disabled"},
        )
    assert response.status_code == 503
    assert response.json()["detail"] == "DPM_IDEMPOTENCY_STORE_WRITE_FAILED"


def test_simulate_rfc7807_domain_error_mapping(client):
    payload = get_valid_payload()
    payload["options"]["single_position_max_weight"] = "0.50"

    payload["model_portfolio"]["targets"] = [{"instrument_id": "EQ_1", "weight": "1.0"}]
    payload["shelf_entries"] = [{"instrument_id": "EQ_1", "status": "APPROVED"}]

    headers = {"Idempotency-Key": "test-key-err", "X-Correlation-Id": "corr-err"}
    response = client.post("/api/v1/rebalance/simulate", json=payload, headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "PENDING_REVIEW"


def test_get_db_session_dependency():
    """Verify DB dependency yields expected stub session value."""
    gen = get_db_session()
    assert inspect.isasyncgen(gen)

    async def consume():
        first = await gen.__anext__()
        assert first is None
        with pytest.raises(StopAsyncIteration):
            await gen.__anext__()

    asyncio.run(consume())


def test_simulate_blocked_logs_warning(client):
    """
    Force a 'BLOCKED' status (e.g. missing price) to verify the API logging branch.
    """
    payload = get_valid_payload()
    payload["market_data_snapshot"]["prices"] = []

    headers = {"Idempotency-Key": "test-key-block"}
    with patch("src.api.main.logger") as mock_logger:
        response = client.post("/api/v1/rebalance/simulate", json=payload, headers=headers)
        assert response.status_code == 200
        assert response.json()["status"] == "BLOCKED"

        mock_logger.warning.assert_called()
        args, _ = mock_logger.warning.call_args
        assert "Run blocked" in args[0]
        assert len(args) == 1
        assert "Diagnostics" not in args[0]


def test_simulate_logs_do_not_embed_request_identifiers(client):
    payload = get_valid_payload()
    headers = {
        "Idempotency-Key": "test-key-log-redaction",
        "X-Correlation-Id": "corr-log-redaction",
    }

    with patch("src.api.main.logger") as mock_logger:
        response = client.post("/api/v1/rebalance/simulate", json=payload, headers=headers)

    assert response.status_code == 200
    logged_text = " ".join(
        str(arg) for call in mock_logger.info.call_args_list for arg in call.args
    )
    assert "corr-log-redaction" not in logged_text
    assert "test-key-log-redaction" not in logged_text
    assert "Idempotency" not in logged_text
    assert "CID=" not in logged_text


def test_simulate_missing_price_can_continue_when_non_blocking(client):
    payload = get_valid_payload()
    payload["market_data_snapshot"]["prices"] = []
    payload["options"]["block_on_missing_prices"] = False

    response = client.post(
        "/api/v1/rebalance/simulate",
        json=payload,
        headers={"Idempotency-Key": "test-key-missing-price-nonblock"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"READY", "PENDING_REVIEW"}
    assert "EQ_1" in body["diagnostics"]["data_quality"]["price_missing"]


def test_simulate_rejects_invalid_group_constraint_key(client):
    payload = get_valid_payload()
    payload["options"]["group_constraints"] = {"sectorTECH": {"max_weight": "0.2"}}

    response = client.post(
        "/api/v1/rebalance/simulate",
        json=payload,
        headers={"Idempotency-Key": "test-key-invalid-group-key"},
    )

    assert response.status_code == 422


def test_analyze_endpoint_success(client):
    payload = get_valid_payload()
    payload.pop("options")
    payload["portfolio_snapshot"]["snapshot_id"] = "ps_13"
    payload["market_data_snapshot"]["snapshot_id"] = "md_13"
    payload["scenarios"] = {
        "baseline": {"options": {}},
        "position_cap": {"options": {"single_position_max_weight": "0.5"}},
    }

    response = client.post(
        "/api/v1/rebalance/analyze",
        json=payload,
        headers={"X-Correlation-Id": "corr-batch-1"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["batch_run_id"].startswith("batch_")
    assert "run_at_utc" in body
    assert body["base_snapshot_ids"]["portfolio_snapshot_id"] == "ps_13"
    assert body["base_snapshot_ids"]["market_data_snapshot_id"] == "md_13"
    assert set(body["results"].keys()) == {"baseline", "position_cap"}
    assert set(body["comparison_metrics"].keys()) == {"baseline", "position_cap"}
    assert body["failed_scenarios"] == {}
    assert body["warnings"] == []

    for scenario_result in body["results"].values():
        assert scenario_result["lineage"]["request_hash"].startswith(body["batch_run_id"])
    assert body["results"]["baseline"]["correlation_id"] == "corr-batch-1:baseline"
    assert body["results"]["position_cap"]["correlation_id"] == "corr-batch-1:position_cap"
    for metrics in body["comparison_metrics"].values():
        assert metrics["status"] in {"READY", "PENDING_REVIEW", "BLOCKED"}
        assert isinstance(metrics["security_intent_count"], int)
        assert (
            metrics["gross_turnover_notional_base"]["currency"]
            == payload["portfolio_snapshot"]["base_currency"]
        )


def test_analyze_skips_policy_catalog_when_policy_packs_disabled(client, monkeypatch):
    monkeypatch.setenv("DPM_POLICY_PACKS_ENABLED", "false")

    def _fail_if_catalog_loaded():
        raise AssertionError("policy catalog should not be loaded when policy packs are disabled")

    monkeypatch.setattr(
        "src.api.services.rebalance_simulation_service.load_dpm_policy_pack_catalog",
        _fail_if_catalog_loaded,
    )
    payload = get_valid_payload()
    payload.pop("options")
    payload["scenarios"] = {"baseline": {"options": {}}}

    response = client.post("/api/v1/rebalance/analyze", json=payload)

    assert response.status_code == 200
    assert set(response.json()["results"].keys()) == {"baseline"}


def test_analyze_async_accept_and_lookup_succeeded(client):
    payload = get_valid_payload()
    payload.pop("options")
    payload["scenarios"] = {"baseline": {"options": {}}}

    accepted = client.post(
        "/api/v1/rebalance/analyze/async",
        json=payload,
        headers={"X-Correlation-Id": "corr-batch-async-1"},
    )
    assert accepted.status_code == 202
    accepted_body = accepted.json()
    assert accepted_body["operation_type"] == "ANALYZE_SCENARIOS"
    assert accepted_body["status"] == "PENDING"
    assert accepted_body["correlation_id"] == "corr-batch-async-1"
    assert (
        accepted_body["execute_url"]
        == f"/api/v1/rebalance/operations/{accepted_body['operation_id']}/execute"
    )
    assert accepted.headers["X-Correlation-Id"] == "corr-batch-async-1"
    operation_id = accepted_body["operation_id"]

    by_operation = client.get(f"/api/v1/rebalance/operations/{operation_id}")
    assert by_operation.status_code == 200
    by_operation_body = by_operation.json()
    assert by_operation_body["status"] == "SUCCEEDED"
    assert by_operation_body["is_executable"] is False
    assert by_operation_body["correlation_id"] == "corr-batch-async-1"
    assert by_operation_body["result"]["batch_run_id"].startswith("batch_")
    assert set(by_operation_body["result"]["results"].keys()) == {"baseline"}
    assert by_operation_body["error"] is None

    by_correlation = client.get("/api/v1/rebalance/operations/by-correlation/corr-batch-async-1")
    assert by_correlation.status_code == 200
    assert by_correlation.json()["operation_id"] == operation_id
    assert by_correlation.json()["status"] == "SUCCEEDED"


def test_analyze_async_generates_and_echoes_correlation_header_when_missing(client):
    payload = get_valid_payload()
    payload.pop("options")
    payload["scenarios"] = {"baseline": {"options": {}}}

    accepted = client.post("/api/v1/rebalance/analyze/async", json=payload)
    assert accepted.status_code == 202
    accepted_body = accepted.json()
    assert accepted_body["correlation_id"].startswith("corr_")
    assert accepted.headers["X-Correlation-Id"] == accepted_body["correlation_id"]


def test_analyze_async_duplicate_correlation_returns_domain_conflict(client):
    payload = get_valid_payload()
    payload.pop("options")
    payload["scenarios"] = {"baseline": {"options": {}}}
    headers = {"X-Correlation-Id": "corr-batch-async-duplicate"}

    first = client.post("/api/v1/rebalance/analyze/async", json=payload, headers=headers)
    second = client.post("/api/v1/rebalance/analyze/async", json=payload, headers=headers)

    assert first.status_code == 202
    assert second.status_code == 409
    assert second.json()["detail"] == "DPM_ASYNC_OPERATION_CORRELATION_CONFLICT"


def test_analyze_async_failure_is_captured_in_operation_status(client):
    payload = get_valid_payload()
    payload.pop("options")
    payload["scenarios"] = {"baseline": {"options": {}}}

    with patch("src.api.main._execute_batch_analysis", side_effect=RuntimeError("boom")):
        accepted = client.post(
            "/api/v1/rebalance/analyze/async",
            json=payload,
            headers={"X-Correlation-Id": "corr-batch-async-failure"},
        )

    assert accepted.status_code == 202
    operation_id = accepted.json()["operation_id"]
    operation = client.get(f"/api/v1/rebalance/operations/{operation_id}")
    assert operation.status_code == 200
    operation_body = operation.json()
    assert operation_body["status"] == "FAILED"
    assert operation_body["result"] is None
    assert operation_body["error"]["code"] == "RuntimeError"
    assert operation_body["error"]["message"] == "boom"


def test_analyze_async_disabled_returns_404(client, monkeypatch):
    payload = get_valid_payload()
    payload.pop("options")
    payload["scenarios"] = {"baseline": {"options": {}}}
    monkeypatch.setenv("DPM_ASYNC_OPERATIONS_ENABLED", "false")

    response = client.post("/api/v1/rebalance/analyze/async", json=payload)
    assert response.status_code == 404
    assert response.json()["detail"] == "DPM_ASYNC_OPERATIONS_DISABLED"


def test_dpm_policy_pack_header_is_accepted_without_behavior_change(client, monkeypatch):
    monkeypatch.setenv("DPM_POLICY_PACKS_ENABLED", "true")
    monkeypatch.setenv("DPM_DEFAULT_POLICY_PACK_ID", "dpm_default_pack")
    payload = get_valid_payload()

    response = client.post(
        "/api/v1/rebalance/simulate",
        json=payload,
        headers={
            "Idempotency-Key": "test-key-policy-pack-header",
            "X-Policy-Pack-Id": "dpm_request_pack",
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] in {"READY", "PENDING_REVIEW", "BLOCKED"}


def test_dpm_policy_pack_catalog_overrides_turnover_option(client, monkeypatch):
    monkeypatch.setenv("DPM_POLICY_PACKS_ENABLED", "true")
    monkeypatch.setenv("DPM_DEFAULT_POLICY_PACK_ID", "dpm_default_pack")
    monkeypatch.setenv(
        "DPM_POLICY_PACK_CATALOG_JSON",
        (
            '{"dpm_request_pack":{"version":"1","turnover_policy":{"max_turnover_pct":"0.01"},'
            '"tax_policy":{"enable_tax_awareness":true,"max_realized_capital_gains":"55"},'
            '"settlement_policy":{"enable_settlement_awareness":true,"settlement_horizon_days":3},'
            '"constraint_policy":{"single_position_max_weight":"0.25",'
            '"group_constraints":{"sector:TECH":{"max_weight":"0.20"}}},'
            '"workflow_policy":{"enable_workflow_gates":false,'
            '"workflow_requires_mandate_approval":true,'
            '"mandate_approval_already_obtained":true}}}'
        ),
    )

    payload = get_valid_payload()
    from src.core.rebalance.engine import run_simulation as real_run
    from src.core.models import (
        EngineOptions,
        MarketDataSnapshot,
        ModelPortfolio,
        PortfolioSnapshot,
        ShelfEntry,
    )

    seed_payload = get_valid_payload()
    real_result = real_run(
        portfolio=PortfolioSnapshot(**seed_payload["portfolio_snapshot"]),
        market_data=MarketDataSnapshot(**seed_payload["market_data_snapshot"]),
        model=ModelPortfolio(**seed_payload["model_portfolio"]),
        shelf=[ShelfEntry(**entry) for entry in seed_payload["shelf_entries"]],
        options=EngineOptions(**seed_payload["options"]),
        request_hash="seed-policy-pack",
    )

    with patch("src.api.main.run_simulation") as mock_run:
        mock_run.return_value = real_result

        simulate = client.post(
            "/api/v1/rebalance/simulate",
            json=payload,
            headers={
                "Idempotency-Key": "test-key-policy-pack-override-simulate",
                "X-Policy-Pack-Id": "dpm_request_pack",
            },
        )
        assert simulate.status_code == 200
        simulate_options = mock_run.call_args_list[0].kwargs["options"]
        assert simulate_options.max_turnover_pct == Decimal("0.01")
        assert simulate_options.enable_tax_awareness is True
        assert simulate_options.max_realized_capital_gains == Decimal("55")
        assert simulate_options.enable_settlement_awareness is True
        assert simulate_options.settlement_horizon_days == 3
        assert simulate_options.single_position_max_weight == Decimal("0.25")
        assert "sector:TECH" in simulate_options.group_constraints
        assert simulate_options.group_constraints["sector:TECH"].max_weight == Decimal("0.20")
        assert simulate_options.enable_workflow_gates is False
        assert simulate_options.workflow_requires_mandate_approval is True
        assert simulate_options.mandate_approval_already_obtained is True

        batch_payload = get_valid_payload()
        batch_payload.pop("options")
        batch_payload["scenarios"] = {"baseline": {"options": {}}}
        analyze = client.post(
            "/api/v1/rebalance/analyze",
            json=batch_payload,
            headers={"X-Policy-Pack-Id": "dpm_request_pack"},
        )
        assert analyze.status_code == 200
        analyze_options = mock_run.call_args_list[1].kwargs["options"]
        assert analyze_options.max_turnover_pct == Decimal("0.01")
        assert analyze_options.enable_tax_awareness is True
        assert analyze_options.max_realized_capital_gains == Decimal("55")
        assert analyze_options.enable_settlement_awareness is True
        assert analyze_options.settlement_horizon_days == 3
        assert analyze_options.single_position_max_weight == Decimal("0.25")
        assert "sector:TECH" in analyze_options.group_constraints
        assert analyze_options.group_constraints["sector:TECH"].max_weight == Decimal("0.20")
        assert analyze_options.enable_workflow_gates is False
        assert analyze_options.workflow_requires_mandate_approval is True
        assert analyze_options.mandate_approval_already_obtained is True


def test_effective_policy_pack_endpoint_resolution_precedence(client, monkeypatch):
    disabled = client.get(
        "/api/v1/rebalance/policies/effective", headers={"X-Policy-Pack-Id": "req_pack"}
    )
    assert disabled.status_code == 200
    assert disabled.json() == {
        "enabled": False,
        "selected_policy_pack_id": None,
        "source": "DISABLED",
    }

    monkeypatch.setenv("DPM_POLICY_PACKS_ENABLED", "true")
    monkeypatch.setenv("DPM_DEFAULT_POLICY_PACK_ID", "global_pack")

    request_level = client.get(
        "/api/v1/rebalance/policies/effective",
        headers={
            "X-Policy-Pack-Id": "req_pack",
            "X-Tenant-Policy-Pack-Id": "tenant_pack",
        },
    )
    assert request_level.status_code == 200
    assert request_level.json() == {
        "enabled": True,
        "selected_policy_pack_id": "req_pack",
        "source": "REQUEST",
    }

    tenant_level = client.get(
        "/api/v1/rebalance/policies/effective",
        headers={"X-Tenant-Policy-Pack-Id": "tenant_pack"},
    )
    assert tenant_level.status_code == 200
    assert tenant_level.json() == {
        "enabled": True,
        "selected_policy_pack_id": "tenant_pack",
        "source": "TENANT_DEFAULT",
    }

    global_level = client.get("/api/v1/rebalance/policies/effective")
    assert global_level.status_code == 200
    assert global_level.json() == {
        "enabled": True,
        "selected_policy_pack_id": "global_pack",
        "source": "GLOBAL_DEFAULT",
    }


def test_policy_pack_supportability_routes_reject_unexpected_query_params(client):
    unsupported_urls = {
        "/api/v1/rebalance/policies/effective?tenant_id=tenant_001": "tenant_id",
        "/api/v1/rebalance/policies/effective?policyPackId=pack_001": "policyPackId",
        "/api/v1/rebalance/policies/catalog?tenant_id=tenant_001": "tenant_id",
        "/api/v1/rebalance/policies/catalog?include_disabled=true": "include_disabled",
    }

    for url, unsupported_param in unsupported_urls.items():
        response = client.get(url)
        assert response.status_code == 422
        assert response.json()["detail"] == (
            f"UNSUPPORTED_QUERY_PARAMETER: {unsupported_param} not supported for this endpoint"
        )


def test_lineage_supportability_route_rejects_unexpected_query_params(client, monkeypatch):
    monkeypatch.setenv("DPM_LINEAGE_APIS_ENABLED", "true")

    response = client.get("/api/v1/rebalance/lineage/corr_001?edgeType=CORRELATION_TO_RUN")

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "UNSUPPORTED_QUERY_PARAMETER: edgeType not supported for this endpoint"
    )


def test_workflow_decision_list_rejects_unexpected_query_params(client, monkeypatch):
    monkeypatch.setenv("DPM_WORKFLOW_ENABLED", "true")

    response = client.get("/api/v1/rebalance/workflow/decisions?runId=rr_001")

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "UNSUPPORTED_QUERY_PARAMETER: runId not supported for this endpoint"
    )


def test_effective_policy_pack_endpoint_uses_tenant_resolver_when_enabled(client, monkeypatch):
    monkeypatch.setenv("DPM_POLICY_PACKS_ENABLED", "true")
    monkeypatch.setenv("DPM_DEFAULT_POLICY_PACK_ID", "global_pack")
    monkeypatch.setenv("DPM_TENANT_POLICY_PACK_RESOLUTION_ENABLED", "true")
    monkeypatch.setenv("DPM_TENANT_POLICY_PACK_MAP_JSON", '{"tenant_001":"tenant_pack"}')

    tenant_level = client.get(
        "/api/v1/rebalance/policies/effective",
        headers={"X-Tenant-Id": "tenant_001"},
    )
    assert tenant_level.status_code == 200
    assert tenant_level.json() == {
        "enabled": True,
        "selected_policy_pack_id": "tenant_pack",
        "source": "TENANT_DEFAULT",
    }


def test_effective_policy_pack_explicit_tenant_header_precedence_over_resolver(client, monkeypatch):
    monkeypatch.setenv("DPM_POLICY_PACKS_ENABLED", "true")
    monkeypatch.setenv("DPM_DEFAULT_POLICY_PACK_ID", "global_pack")
    monkeypatch.setenv("DPM_TENANT_POLICY_PACK_RESOLUTION_ENABLED", "true")
    monkeypatch.setenv("DPM_TENANT_POLICY_PACK_MAP_JSON", '{"tenant_001":"tenant_pack"}')

    tenant_level = client.get(
        "/api/v1/rebalance/policies/effective",
        headers={
            "X-Tenant-Id": "tenant_001",
            "X-Tenant-Policy-Pack-Id": "tenant_header_pack",
        },
    )
    assert tenant_level.status_code == 200
    assert tenant_level.json() == {
        "enabled": True,
        "selected_policy_pack_id": "tenant_header_pack",
        "source": "TENANT_DEFAULT",
    }


def test_policy_pack_catalog_endpoint_returns_resolution_and_items(client, monkeypatch):
    monkeypatch.setenv("DPM_POLICY_PACKS_ENABLED", "true")
    monkeypatch.setenv("DPM_DEFAULT_POLICY_PACK_ID", "global_pack")
    monkeypatch.setenv(
        "DPM_POLICY_PACK_CATALOG_JSON",
        (
            '{"dpm_request_pack":{"version":"2","turnover_policy":{"max_turnover_pct":"0.03"}},'
            '"global_pack":{"version":"1"}}'
        ),
    )

    response = client.get(
        "/api/v1/rebalance/policies/catalog",
        headers={
            "X-Policy-Pack-Id": "dpm_request_pack",
            "X-Tenant-Policy-Pack-Id": "tenant_pack",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["enabled"] is True
    assert body["total"] == 2
    assert body["selected_policy_pack_id"] == "dpm_request_pack"
    assert body["selected_policy_pack_present"] is True
    assert body["selected_policy_pack_source"] == "REQUEST"
    assert [item["policy_pack_id"] for item in body["items"]] == ["dpm_request_pack", "global_pack"]
    assert body["items"][0]["version"] == "2"
    assert body["items"][0]["turnover_policy"]["max_turnover_pct"] == "0.03"
    assert body["items"][0]["tax_policy"]["enable_tax_awareness"] is None
    assert body["items"][0]["settlement_policy"]["settlement_horizon_days"] is None
    assert body["items"][0]["constraint_policy"]["group_constraints"] == {}
    assert body["items"][0]["workflow_policy"]["enable_workflow_gates"] is None
    assert body["items"][0]["idempotency_policy"]["replay_enabled"] is None


def test_policy_pack_catalog_endpoint_uses_tenant_resolver(client, monkeypatch):
    monkeypatch.setenv("DPM_POLICY_PACKS_ENABLED", "true")
    monkeypatch.setenv("DPM_DEFAULT_POLICY_PACK_ID", "global_pack")
    monkeypatch.setenv("DPM_TENANT_POLICY_PACK_RESOLUTION_ENABLED", "true")
    monkeypatch.setenv("DPM_TENANT_POLICY_PACK_MAP_JSON", '{"tenant_001":"tenant_pack"}')
    monkeypatch.setenv(
        "DPM_POLICY_PACK_CATALOG_JSON",
        '{"tenant_pack":{"version":"1"}}',
    )

    response = client.get(
        "/api/v1/rebalance/policies/catalog",
        headers={"X-Tenant-Id": "tenant_001"},
    )
    assert response.status_code == 200
    assert response.json()["selected_policy_pack_id"] == "tenant_pack"
    assert response.json()["selected_policy_pack_present"] is True
    assert response.json()["selected_policy_pack_source"] == "TENANT_DEFAULT"


def test_policy_pack_catalog_endpoint_selected_not_present(client, monkeypatch):
    monkeypatch.setenv("DPM_POLICY_PACKS_ENABLED", "true")
    monkeypatch.setenv("DPM_DEFAULT_POLICY_PACK_ID", "global_pack")
    monkeypatch.setenv("DPM_POLICY_PACK_CATALOG_JSON", '{"global_pack":{"version":"1"}}')

    response = client.get(
        "/api/v1/rebalance/policies/catalog",
        headers={"X-Policy-Pack-Id": "unknown_pack"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["selected_policy_pack_id"] == "unknown_pack"
    assert body["selected_policy_pack_present"] is False
    assert body["selected_policy_pack_source"] == "REQUEST"


def test_dpm_policy_pack_catalog_overrides_options_using_tenant_resolver(client, monkeypatch):
    monkeypatch.setenv("DPM_POLICY_PACKS_ENABLED", "true")
    monkeypatch.setenv("DPM_DEFAULT_POLICY_PACK_ID", "dpm_default_pack")
    monkeypatch.setenv("DPM_TENANT_POLICY_PACK_RESOLUTION_ENABLED", "true")
    monkeypatch.setenv("DPM_TENANT_POLICY_PACK_MAP_JSON", '{"tenant_001":"tenant_pack"}')
    monkeypatch.setenv(
        "DPM_POLICY_PACK_CATALOG_JSON",
        '{"tenant_pack":{"version":"1","turnover_policy":{"max_turnover_pct":"0.02"}}}',
    )
    payload = get_valid_payload()
    from src.core.rebalance.engine import run_simulation as real_run
    from src.core.models import (
        EngineOptions,
        MarketDataSnapshot,
        ModelPortfolio,
        PortfolioSnapshot,
        ShelfEntry,
    )

    seed_payload = get_valid_payload()
    real_result = real_run(
        portfolio=PortfolioSnapshot(**seed_payload["portfolio_snapshot"]),
        market_data=MarketDataSnapshot(**seed_payload["market_data_snapshot"]),
        model=ModelPortfolio(**seed_payload["model_portfolio"]),
        shelf=[ShelfEntry(**entry) for entry in seed_payload["shelf_entries"]],
        options=EngineOptions(**seed_payload["options"]),
        request_hash="seed-policy-pack-tenant",
    )

    with patch("src.api.main.run_simulation") as mock_run:
        mock_run.return_value = real_result

        simulate = client.post(
            "/api/v1/rebalance/simulate",
            json=payload,
            headers={
                "Idempotency-Key": "test-key-policy-pack-tenant-override-simulate",
                "X-Tenant-Id": "tenant_001",
            },
        )
        assert simulate.status_code == 200
        simulate_options = mock_run.call_args.kwargs["options"]
        assert simulate_options.max_turnover_pct == Decimal("0.02")


def test_simulate_policy_pack_explicit_tenant_header_precedence_over_resolver(client, monkeypatch):
    monkeypatch.setenv("DPM_POLICY_PACKS_ENABLED", "true")
    monkeypatch.setenv("DPM_TENANT_POLICY_PACK_RESOLUTION_ENABLED", "true")
    monkeypatch.setenv("DPM_TENANT_POLICY_PACK_MAP_JSON", '{"tenant_001":"tenant_resolver_pack"}')
    monkeypatch.setenv(
        "DPM_POLICY_PACK_CATALOG_JSON",
        (
            '{"tenant_resolver_pack":{"version":"1","turnover_policy":{"max_turnover_pct":"0.02"}},'
            '"tenant_header_pack":{"version":"1","turnover_policy":{"max_turnover_pct":"0.07"}}}'
        ),
    )
    payload = get_valid_payload()
    from src.core.models import (
        EngineOptions,
        MarketDataSnapshot,
        ModelPortfolio,
        PortfolioSnapshot,
        ShelfEntry,
    )
    from src.core.rebalance.engine import run_simulation as real_run

    seed_payload = get_valid_payload()
    real_result = real_run(
        portfolio=PortfolioSnapshot(**seed_payload["portfolio_snapshot"]),
        market_data=MarketDataSnapshot(**seed_payload["market_data_snapshot"]),
        model=ModelPortfolio(**seed_payload["model_portfolio"]),
        shelf=[ShelfEntry(**entry) for entry in seed_payload["shelf_entries"]],
        options=EngineOptions(**seed_payload["options"]),
        request_hash="seed-policy-pack-tenant-header",
    )

    with patch("src.api.main.run_simulation") as mock_run:
        mock_run.return_value = real_result

        simulate = client.post(
            "/api/v1/rebalance/simulate",
            json=payload,
            headers={
                "Idempotency-Key": "test-key-policy-pack-tenant-header-simulate",
                "X-Tenant-Id": "tenant_001",
                "X-Tenant-Policy-Pack-Id": "tenant_header_pack",
            },
        )

    assert simulate.status_code == 200
    simulate_options = mock_run.call_args.kwargs["options"]
    assert simulate_options.max_turnover_pct == Decimal("0.07")


def test_analyze_policy_pack_explicit_tenant_header_precedence_over_resolver(client, monkeypatch):
    monkeypatch.setenv("DPM_POLICY_PACKS_ENABLED", "true")
    monkeypatch.setenv("DPM_TENANT_POLICY_PACK_RESOLUTION_ENABLED", "true")
    monkeypatch.setenv("DPM_TENANT_POLICY_PACK_MAP_JSON", '{"tenant_001":"tenant_resolver_pack"}')
    monkeypatch.setenv(
        "DPM_POLICY_PACK_CATALOG_JSON",
        (
            '{"tenant_resolver_pack":{"version":"1","turnover_policy":{"max_turnover_pct":"0.02"}},'
            '"tenant_header_pack":{"version":"1","turnover_policy":{"max_turnover_pct":"0.07"}}}'
        ),
    )
    payload = get_valid_payload()
    payload.pop("options")
    payload["scenarios"] = {"baseline": {"options": {}}}
    from src.core.models import (
        EngineOptions,
        MarketDataSnapshot,
        ModelPortfolio,
        PortfolioSnapshot,
        ShelfEntry,
    )
    from src.core.rebalance.engine import run_simulation as real_run

    seed_payload = get_valid_payload()
    real_result = real_run(
        portfolio=PortfolioSnapshot(**seed_payload["portfolio_snapshot"]),
        market_data=MarketDataSnapshot(**seed_payload["market_data_snapshot"]),
        model=ModelPortfolio(**seed_payload["model_portfolio"]),
        shelf=[ShelfEntry(**entry) for entry in seed_payload["shelf_entries"]],
        options=EngineOptions(**seed_payload["options"]),
        request_hash="seed-policy-pack-analyze-tenant-header",
    )

    with patch("src.api.main.run_simulation") as mock_run:
        mock_run.return_value = real_result

        analyze = client.post(
            "/api/v1/rebalance/analyze",
            json=payload,
            headers={
                "X-Tenant-Id": "tenant_001",
                "X-Tenant-Policy-Pack-Id": "tenant_header_pack",
            },
        )

    assert analyze.status_code == 200
    analyze_options = mock_run.call_args.kwargs["options"]
    assert analyze_options.max_turnover_pct == Decimal("0.07")


def test_dpm_policy_pack_cannot_disable_durable_idempotency(client, monkeypatch):
    monkeypatch.setenv("DPM_IDEMPOTENCY_REPLAY_ENABLED", "true")
    monkeypatch.setenv("DPM_POLICY_PACKS_ENABLED", "true")
    monkeypatch.setenv(
        "DPM_POLICY_PACK_CATALOG_JSON",
        '{"dpm_request_pack":{"idempotency_policy":{"replay_enabled":false}}}',
    )
    payload = get_valid_payload()
    headers = {
        "Idempotency-Key": "test-key-policy-idem-disable",
        "X-Policy-Pack-Id": "dpm_request_pack",
    }

    first = client.post("/api/v1/rebalance/simulate", json=payload, headers=headers)
    second = client.post("/api/v1/rebalance/simulate", json=payload, headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["rebalance_run_id"] == second.json()["rebalance_run_id"]


def test_dpm_policy_pack_idempotency_override_enables_replay(client, monkeypatch):
    monkeypatch.setenv("DPM_IDEMPOTENCY_REPLAY_ENABLED", "false")
    monkeypatch.setenv("DPM_POLICY_PACKS_ENABLED", "true")
    monkeypatch.setenv(
        "DPM_POLICY_PACK_CATALOG_JSON",
        '{"dpm_request_pack":{"idempotency_policy":{"replay_enabled":true}}}',
    )
    payload = get_valid_payload()
    headers = {
        "Idempotency-Key": "test-key-policy-idem-enable",
        "X-Policy-Pack-Id": "dpm_request_pack",
    }

    first = client.post("/api/v1/rebalance/simulate", json=payload, headers=headers)
    second = client.post("/api/v1/rebalance/simulate", json=payload, headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()


def test_analyze_async_accept_only_mode_keeps_operation_pending(client, monkeypatch):
    monkeypatch.setenv("DPM_ASYNC_EXECUTION_MODE", "ACCEPT_ONLY")
    payload = get_valid_payload()
    payload.pop("options")
    payload["scenarios"] = {"baseline": {"options": {}}}

    accepted = client.post(
        "/api/v1/rebalance/analyze/async",
        json=payload,
        headers={"X-Correlation-Id": "corr-batch-async-accept-only"},
    )
    assert accepted.status_code == 202
    operation_id = accepted.json()["operation_id"]

    operation = client.get(f"/api/v1/rebalance/operations/{operation_id}")
    assert operation.status_code == 200
    operation_body = operation.json()
    assert operation_body["status"] == "PENDING"
    assert operation_body["is_executable"] is True
    assert operation_body["started_at"] is None
    assert operation_body["finished_at"] is None
    assert operation_body["result"] is None
    assert operation_body["error"] is None

    by_correlation = client.get(
        "/api/v1/rebalance/operations/by-correlation/corr-batch-async-accept-only"
    )
    assert by_correlation.status_code == 200
    assert by_correlation.json()["operation_id"] == operation_id
    assert by_correlation.json()["status"] == "PENDING"


def test_analyze_async_accept_only_mode_can_be_executed_manually(client, monkeypatch):
    monkeypatch.setenv("DPM_ASYNC_EXECUTION_MODE", "ACCEPT_ONLY")
    payload = get_valid_payload()
    payload.pop("options")
    payload["scenarios"] = {"baseline": {"options": {}}}

    accepted = client.post(
        "/api/v1/rebalance/analyze/async",
        json=payload,
        headers={"X-Correlation-Id": "corr-batch-async-manual"},
    )
    assert accepted.status_code == 202
    operation_id = accepted.json()["operation_id"]

    executed = client.post(f"/api/v1/rebalance/operations/{operation_id}/execute")
    assert executed.status_code == 200
    executed_body = executed.json()
    assert executed_body["operation_id"] == operation_id
    assert executed_body["status"] == "SUCCEEDED"
    assert executed_body["is_executable"] is False
    assert executed_body["result"]["batch_run_id"].startswith("batch_")


def test_analyze_async_accept_only_manual_execute_captures_failure(client, monkeypatch):
    monkeypatch.setenv("DPM_ASYNC_EXECUTION_MODE", "ACCEPT_ONLY")
    payload = get_valid_payload()
    payload.pop("options")
    payload["scenarios"] = {"baseline": {"options": {}}}

    accepted = client.post(
        "/api/v1/rebalance/analyze/async",
        json=payload,
        headers={"X-Correlation-Id": "corr-batch-async-manual-failure"},
    )
    assert accepted.status_code == 202
    operation_id = accepted.json()["operation_id"]

    with patch("src.api.main._execute_batch_analysis", side_effect=RuntimeError("boom")):
        executed = client.post(
            f"/api/v1/rebalance/operations/{operation_id}/execute",
            headers={"X-Tenant-Id": "tenant-test"},
        )

    assert executed.status_code == 200
    executed_body = executed.json()
    assert executed_body["operation_id"] == operation_id
    assert executed_body["status"] == "FAILED"
    assert executed_body["is_executable"] is False
    assert executed_body["result"] is None
    assert executed_body["error"] == {"code": "RuntimeError", "message": "boom"}

    repeated = client.post(f"/api/v1/rebalance/operations/{operation_id}/execute")
    assert repeated.status_code == 409
    assert repeated.json()["detail"] == "DPM_ASYNC_OPERATION_NOT_EXECUTABLE"


def test_analyze_async_accept_only_manual_execute_preserves_tenant_policy_context(
    client, monkeypatch
):
    monkeypatch.setenv("DPM_ASYNC_EXECUTION_MODE", "ACCEPT_ONLY")
    monkeypatch.setenv("DPM_POLICY_PACKS_ENABLED", "true")
    monkeypatch.setenv("DPM_TENANT_POLICY_PACK_RESOLUTION_ENABLED", "true")
    monkeypatch.setenv("DPM_TENANT_POLICY_PACK_MAP_JSON", '{"tenant_001":"tenant_resolver_pack"}')
    monkeypatch.setenv(
        "DPM_POLICY_PACK_CATALOG_JSON",
        (
            '{"tenant_resolver_pack":{"version":"1","turnover_policy":{"max_turnover_pct":"0.02"}},'
            '"tenant_header_pack":{"version":"1","turnover_policy":{"max_turnover_pct":"0.07"}}}'
        ),
    )
    payload = get_valid_payload()
    payload.pop("options")
    payload["scenarios"] = {"baseline": {"options": {}}}
    from src.core.models import (
        EngineOptions,
        MarketDataSnapshot,
        ModelPortfolio,
        PortfolioSnapshot,
        ShelfEntry,
    )
    from src.core.rebalance.engine import run_simulation as real_run

    seed_payload = get_valid_payload()
    real_result = real_run(
        portfolio=PortfolioSnapshot(**seed_payload["portfolio_snapshot"]),
        market_data=MarketDataSnapshot(**seed_payload["market_data_snapshot"]),
        model=ModelPortfolio(**seed_payload["model_portfolio"]),
        shelf=[ShelfEntry(**entry) for entry in seed_payload["shelf_entries"]],
        options=EngineOptions(**seed_payload["options"]),
        request_hash="seed-policy-pack-async-manual-tenant-header",
    )

    accepted = client.post(
        "/api/v1/rebalance/analyze/async",
        json=payload,
        headers={
            "X-Correlation-Id": "corr-batch-async-policy-context",
            "X-Tenant-Id": "tenant_001",
            "X-Tenant-Policy-Pack-Id": "tenant_header_pack",
        },
    )
    assert accepted.status_code == 202
    operation_id = accepted.json()["operation_id"]

    with patch("src.api.main.run_simulation") as mock_run:
        mock_run.return_value = real_result
        executed = client.post(
            f"/api/v1/rebalance/operations/{operation_id}/execute",
            headers={"X-Tenant-Id": "tenant_001"},
        )

    assert executed.status_code == 200
    assert executed.json()["status"] == "SUCCEEDED"
    executed_options = mock_run.call_args.kwargs["options"]
    assert executed_options.max_turnover_pct == Decimal("0.07")


def test_analyze_async_manual_execute_not_found_not_executable_and_disabled(client, monkeypatch):
    missing = client.post("/api/v1/rebalance/operations/dop_missing/execute")
    assert missing.status_code == 404
    assert missing.json()["detail"] == "DPM_ASYNC_OPERATION_NOT_FOUND"

    payload = get_valid_payload()
    payload.pop("options")
    payload["scenarios"] = {"baseline": {"options": {}}}
    accepted = client.post("/api/v1/rebalance/analyze/async", json=payload)
    assert accepted.status_code == 202
    operation_id = accepted.json()["operation_id"]

    non_executable = client.post(f"/api/v1/rebalance/operations/{operation_id}/execute")
    assert non_executable.status_code == 409
    assert non_executable.json()["detail"] == "DPM_ASYNC_OPERATION_NOT_EXECUTABLE"

    monkeypatch.setenv("DPM_ASYNC_MANUAL_EXECUTION_ENABLED", "false")
    disabled = client.post(f"/api/v1/rebalance/operations/{operation_id}/execute")
    assert disabled.status_code == 404
    assert disabled.json()["detail"] == "DPM_ASYNC_MANUAL_EXECUTION_DISABLED"


def test_analyze_async_invalid_execution_mode_falls_back_to_inline(client, monkeypatch):
    monkeypatch.setenv("DPM_ASYNC_EXECUTION_MODE", "INVALID_MODE")
    payload = get_valid_payload()
    payload.pop("options")
    payload["scenarios"] = {"baseline": {"options": {}}}

    accepted = client.post(
        "/api/v1/rebalance/analyze/async",
        json=payload,
        headers={"X-Correlation-Id": "corr-batch-async-inline-fallback"},
    )
    assert accepted.status_code == 202
    operation_id = accepted.json()["operation_id"]

    operation = client.get(f"/api/v1/rebalance/operations/{operation_id}")
    assert operation.status_code == 200
    assert operation.json()["status"] == "SUCCEEDED"


def test_dpm_artifact_openapi_schema_has_descriptions_and_examples(client):
    openapi = client.get("/openapi.json").json()
    schema = openapi["components"]["schemas"]["DpmRunArtifactResponse"]
    for property_name in [
        "artifact_id",
        "artifact_version",
        "rebalance_run_id",
        "correlation_id",
        "portfolio_id",
        "status",
        "request_snapshot",
        "before_summary",
        "after_summary",
        "order_intents",
        "rule_outcomes",
        "diagnostics",
        "result",
        "evidence",
    ]:
        prop = schema["properties"][property_name]
        assert prop.get("description")
        assert prop.get("examples") or prop.get("$ref")


def test_openapi_title_and_tag_grouping(client):
    openapi = client.get("/openapi.json").json()
    assert openapi["info"]["title"] == "Private Banking Rebalance API"

    tags = {tag["name"] for tag in openapi.get("tags", [])}
    assert "lotus-manage Simulation" in tags
    assert "lotus-manage What-If Analysis" in tags
    assert "lotus-manage Run Supportability" in tags
    assert "Advisory Simulation" not in tags
    assert "Advisory Proposal Lifecycle" not in tags

    assert openapi["paths"]["/api/v1/rebalance/simulate"]["post"]["tags"] == [
        "lotus-manage Simulation"
    ]
    assert openapi["paths"]["/api/v1/rebalance/analyze"]["post"]["tags"] == [
        "lotus-manage What-If Analysis"
    ]
    assert openapi["paths"]["/api/v1/rebalance/analyze/async"]["post"]["tags"] == [
        "lotus-manage What-If Analysis"
    ]
    assert openapi["paths"]["/api/v1/rebalance/policies/effective"]["get"]["tags"] == [
        "lotus-manage Run Supportability"
    ]
    assert openapi["paths"]["/api/v1/rebalance/policies/catalog"]["get"]["tags"] == [
        "lotus-manage Run Supportability"
    ]
    assert "/api/v1/rebalance/proposals/simulate" not in openapi["paths"]
    assert "/api/v1/rebalance/proposals/artifact" not in openapi["paths"]
    assert "/api/v1/rebalance/proposals" not in openapi["paths"]


def test_openapi_exposes_only_canonical_product_routes(client):
    openapi = client.get("/openapi.json").json()
    paths = set(openapi["paths"])

    assert "/api/v1/integration/capabilities" in paths
    assert "/platform/capabilities" not in paths
    assert "/api/v1/platform/capabilities" not in paths
    assert "/api/v1/health" not in paths
    assert "/api/v1/health/live" not in paths
    assert "/api/v1/health/ready" not in paths

    allowed_unversioned_infrastructure_paths = {
        "/health",
        "/health/live",
        "/health/ready",
        "/metrics",
        "/version",
    }
    unversioned_paths = {path for path in paths if not path.startswith("/api/v1")}

    assert unversioned_paths == allowed_unversioned_infrastructure_paths


def test_openapi_async_analyze_documents_correlation_header(client):
    openapi = client.get("/openapi.json").json()
    simulate = openapi["paths"]["/api/v1/rebalance/simulate"]["post"]
    analyze = openapi["paths"]["/api/v1/rebalance/analyze"]["post"]
    analyze_async = openapi["paths"]["/api/v1/rebalance/analyze/async"]["post"]

    simulate_header_names = {parameter["name"] for parameter in simulate["parameters"]}
    analyze_header_names = {parameter["name"] for parameter in analyze["parameters"]}
    assert "x-policy-pack-id" in simulate_header_names
    assert "x-policy-pack-id" in analyze_header_names
    assert "x-tenant-id" in simulate_header_names
    assert "x-tenant-id" in analyze_header_names
    sync_correlation_header = next(
        parameter for parameter in analyze["parameters"] if parameter["name"] == "x-correlation-id"
    )
    assert sync_correlation_header["in"] == "header"
    assert "scenario name" in sync_correlation_header["description"]

    request_header = next(
        parameter
        for parameter in analyze_async["parameters"]
        if parameter["name"] == "x-correlation-id"
    )
    assert request_header["in"] == "header"
    assert request_header["description"]
    schema = request_header["schema"]
    if "type" in schema:
        assert schema["type"] == "string"
    else:
        assert any(item.get("type") == "string" for item in schema.get("anyOf", []))

    response_headers = analyze_async["responses"]["202"]["headers"]
    assert "X-Correlation-Id" in response_headers
    assert response_headers["X-Correlation-Id"]["description"]
    assert response_headers["X-Correlation-Id"]["schema"]["type"] == "string"
    conflict_example = analyze_async["responses"]["409"]["content"]["application/json"]["examples"][
        "correlation_conflict"
    ]["value"]
    assert conflict_example["detail"] == "DPM_ASYNC_OPERATION_CORRELATION_CONFLICT"

    policy_pack_header = next(
        parameter
        for parameter in analyze_async["parameters"]
        if parameter["name"] == "x-policy-pack-id"
    )
    assert policy_pack_header["in"] == "header"
    assert policy_pack_header["description"]
    policy_schema = policy_pack_header["schema"]
    if "type" in policy_schema:
        assert policy_schema["type"] == "string"
    else:
        assert any(item.get("type") == "string" for item in policy_schema.get("anyOf", []))

    tenant_header = next(
        parameter for parameter in analyze_async["parameters"] if parameter["name"] == "x-tenant-id"
    )
    assert tenant_header["in"] == "header"
    assert tenant_header["description"]
    tenant_schema = tenant_header["schema"]
    if "type" in tenant_schema:
        assert tenant_schema["type"] == "string"
    else:
        assert any(item.get("type") == "string" for item in tenant_schema.get("anyOf", []))

    simulate_examples = simulate["responses"]["200"]["content"]["application/json"]["examples"]
    ready_example = simulate_examples["ready"]["value"]
    pending_example = simulate_examples["pending_review"]["value"]
    blocked_example = simulate_examples["blocked"]["value"]
    assert "lineage" in ready_example
    assert "before" in ready_example
    assert "after_simulated" in ready_example
    assert pending_example["gate_decision"]["recommended_next_step"] == "RISK_REVIEW"
    assert blocked_example["gate_decision"]["gate"] == "BLOCKED"
    assert blocked_example["diagnostics"]["cash_ladder_breaches"][0]["reason_code"] == (
        "OVERDRAFT_ON_T_PLUS_1"
    )

    accepted_schema = openapi["components"]["schemas"]["DpmAsyncAcceptedResponse"]
    assert "execute_url" in accepted_schema["properties"]
    assert accepted_schema["properties"]["execute_url"]["description"]
    assert accepted_schema["properties"]["execute_url"]["examples"]
    async_status_schema = openapi["components"]["schemas"]["DpmAsyncOperationStatusResponse"]
    assert "is_executable" in async_status_schema["properties"]
    assert async_status_schema["properties"]["is_executable"]["description"]
    assert async_status_schema["properties"]["is_executable"]["examples"]
    assert "/api/v1/rebalance/operations/{operation_id}/execute" in openapi["paths"]


def test_analyze_rejects_invalid_scenario_name(client):
    payload = get_valid_payload()
    payload.pop("options")
    payload["scenarios"] = {"Invalid-Name": {"options": {}}}

    response = client.post("/api/v1/rebalance/analyze", json=payload)
    assert response.status_code == 422


def test_analyze_partial_failure_invalid_scenario_options(client):
    payload = get_valid_payload()
    payload.pop("options")
    payload["scenarios"] = {
        "valid_case": {"options": {}},
        "invalid_case": {"options": {"group_constraints": {"sectorTECH": {"max_weight": "0.2"}}}},
    }

    response = client.post("/api/v1/rebalance/analyze", json=payload)
    assert response.status_code == 200
    body = response.json()

    assert "valid_case" in body["results"]
    assert "invalid_case" in body["failed_scenarios"]
    assert body["failed_scenarios"]["invalid_case"].startswith("INVALID_OPTIONS:")
    assert "PARTIAL_BATCH_FAILURE" in body["warnings"]


def test_analyze_rejects_too_many_scenarios(client):
    payload = get_valid_payload()
    payload.pop("options")
    payload["scenarios"] = {f"s{i}": {"options": {}} for i in range(21)}

    response = client.post("/api/v1/rebalance/analyze", json=payload)
    assert response.status_code == 422


def test_analyze_fallback_snapshot_ids_when_not_provided(client):
    payload = get_valid_payload()
    payload.pop("options")
    payload["scenarios"] = {"baseline": {"options": {}}}

    response = client.post("/api/v1/rebalance/analyze", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert (
        body["base_snapshot_ids"]["portfolio_snapshot_id"]
        == payload["portfolio_snapshot"]["portfolio_id"]
    )
    assert body["base_snapshot_ids"]["market_data_snapshot_id"] == "md"


def test_analyze_scenarios_are_processed_in_sorted_name_order(client):
    payload = get_valid_payload()
    payload.pop("options")
    payload["scenarios"] = {"z_case": {"options": {}}, "a_case": {"options": {}}}

    from src.core.rebalance.engine import run_simulation as real_run
    from src.core.models import (
        EngineOptions,
        MarketDataSnapshot,
        ModelPortfolio,
        PortfolioSnapshot,
        ShelfEntry,
    )

    seed_payload = get_valid_payload()
    real_result = real_run(
        portfolio=PortfolioSnapshot(**seed_payload["portfolio_snapshot"]),
        market_data=MarketDataSnapshot(**seed_payload["market_data_snapshot"]),
        model=ModelPortfolio(**seed_payload["model_portfolio"]),
        shelf=[ShelfEntry(**entry) for entry in seed_payload["shelf_entries"]],
        options=EngineOptions(**seed_payload["options"]),
        request_hash="seed",
    )

    with patch("src.api.main.run_simulation") as mock_run:
        mock_run.return_value = real_result

        response = client.post("/api/v1/rebalance/analyze", json=payload)
        assert response.status_code == 200
        call_hashes = [c.kwargs["request_hash"] for c in mock_run.call_args_list]
        assert call_hashes[0].endswith(":a_case")
        assert call_hashes[1].endswith(":z_case")


def test_analyze_runtime_error_is_isolated_to_failing_scenario(client):
    payload = get_valid_payload()
    payload.pop("options")
    payload["scenarios"] = {"ok_case": {"options": {}}, "boom_case": {"options": {}}}

    from src.api.main import run_simulation as real_run

    def _side_effect(*args, **kwargs):
        if kwargs.get("request_hash", "").endswith(":boom_case"):
            raise RuntimeError("boom")
        return real_run(*args, **kwargs)

    with patch("src.api.main.run_simulation", side_effect=_side_effect):
        response = client.post("/api/v1/rebalance/analyze", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert "ok_case" in body["results"]
    assert "boom_case" in body["failed_scenarios"]
    assert body["failed_scenarios"]["boom_case"] == "SCENARIO_EXECUTION_ERROR: RuntimeError"
    assert "PARTIAL_BATCH_FAILURE" in body["warnings"]


def test_analyze_comparison_metrics_turnover_matches_intents(client):
    payload = get_valid_payload()
    payload.pop("options")
    payload["portfolio_snapshot"]["base_currency"] = "USD"
    payload["portfolio_snapshot"]["positions"] = [{"instrument_id": "EQ_1", "quantity": "100"}]
    payload["portfolio_snapshot"]["cash_balances"] = [{"currency": "USD", "amount": "0"}]
    payload["model_portfolio"]["targets"] = [{"instrument_id": "EQ_1", "weight": "0.0"}]
    payload["shelf_entries"] = [{"instrument_id": "EQ_1", "status": "APPROVED"}]
    payload["scenarios"] = {"de_risk": {"options": {}}}

    response = client.post("/api/v1/rebalance/analyze", json=payload)
    assert response.status_code == 200
    body = response.json()
    metric = body["comparison_metrics"]["de_risk"]
    result = body["results"]["de_risk"]
    expected_turnover = sum(
        Decimal(intent["notional_base"]["amount"])
        for intent in result["intents"]
        if intent["intent_type"] == "SECURITY_TRADE"
    )
    assert Decimal(metric["gross_turnover_notional_base"]["amount"]) == expected_turnover


def test_analyze_accepts_max_scenarios_boundary(client):
    payload = get_valid_payload()
    payload.pop("options")
    payload["scenarios"] = {f"s{i:02d}": {"options": {}} for i in range(20)}

    response = client.post("/api/v1/rebalance/analyze", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert len(body["results"]) == 20
    assert len(body["comparison_metrics"]) == 20
    assert body["failed_scenarios"] == {}


def test_analyze_run_at_utc_is_timezone_aware_iso8601(client):
    payload = get_valid_payload()
    payload.pop("options")
    payload["scenarios"] = {"baseline": {"options": {}}}

    response = client.post("/api/v1/rebalance/analyze", json=payload)
    assert response.status_code == 200
    run_at = datetime.fromisoformat(response.json()["run_at_utc"])
    assert run_at.tzinfo is not None


def test_analyze_results_and_metrics_keys_match_successful_scenarios_only(client):
    payload = get_valid_payload()
    payload.pop("options")
    payload["scenarios"] = {
        "ok_case": {"options": {}},
        "bad_case": {"options": {"group_constraints": {"sectorTECH": {"max_weight": "0.2"}}}},
    }

    response = client.post("/api/v1/rebalance/analyze", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert set(body["results"].keys()) == {"ok_case"}
    assert set(body["comparison_metrics"].keys()) == {"ok_case"}
    assert set(body["failed_scenarios"].keys()) == {"bad_case"}


def test_analyze_mixed_outcomes_ready_pending_review_blocked(client):
    payload = get_valid_payload()
    payload.pop("options")
    payload["shelf_entries"] = [
        {
            "instrument_id": "EQ_1",
            "status": "APPROVED",
            "attributes": {"sector": "TECH"},
        }
    ]
    payload["scenarios"] = {
        "ready_case": {"options": {}},
        "pending_case": {"options": {"single_position_max_weight": "0.5"}},
        "blocked_case": {"options": {"group_constraints": {"sector:TECH": {"max_weight": "0.2"}}}},
    }

    response = client.post("/api/v1/rebalance/analyze", json=payload)
    assert response.status_code == 200
    metrics = response.json()["comparison_metrics"]
    assert metrics["ready_case"]["status"] == "READY"
    assert metrics["pending_case"]["status"] == "PENDING_REVIEW"
    assert metrics["blocked_case"]["status"] == "BLOCKED"


def test_simulate_turnover_cap_emits_partial_rebalance_warning(client):
    payload = get_valid_payload()
    payload["portfolio_snapshot"]["base_currency"] = "USD"
    payload["portfolio_snapshot"]["cash_balances"] = [{"currency": "USD", "amount": "100000"}]
    payload["market_data_snapshot"]["prices"] = [
        {"instrument_id": "A", "price": "100", "currency": "USD"},
        {"instrument_id": "B", "price": "100", "currency": "USD"},
        {"instrument_id": "C", "price": "100", "currency": "USD"},
    ]
    payload["model_portfolio"]["targets"] = [
        {"instrument_id": "A", "weight": "0.10"},
        {"instrument_id": "B", "weight": "0.10"},
        {"instrument_id": "C", "weight": "0.02"},
    ]
    payload["shelf_entries"] = [
        {"instrument_id": "A", "status": "APPROVED"},
        {"instrument_id": "B", "status": "APPROVED"},
        {"instrument_id": "C", "status": "APPROVED"},
    ]
    payload["options"]["max_turnover_pct"] = "0.15"

    response = client.post(
        "/api/v1/rebalance/simulate",
        json=payload,
        headers={"Idempotency-Key": "test-key-turnover-cap"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "PARTIAL_REBALANCE_TURNOVER_LIMIT" in body["diagnostics"]["warnings"]
    assert len(body["diagnostics"]["dropped_intents"]) == 1


def test_simulate_settlement_awareness_toggle_is_request_scoped(client):
    payload = {
        "portfolio_snapshot": {
            "portfolio_id": "pf_settlement_api",
            "base_currency": "USD",
            "positions": [{"instrument_id": "SLOW_FUND", "quantity": "10"}],
            "cash_balances": [{"currency": "USD", "amount": "0"}],
        },
        "market_data_snapshot": {
            "prices": [
                {"instrument_id": "SLOW_FUND", "price": "100", "currency": "USD"},
                {"instrument_id": "FAST_STOCK", "price": "100", "currency": "USD"},
            ],
            "fx_rates": [],
        },
        "model_portfolio": {
            "targets": [
                {"instrument_id": "SLOW_FUND", "weight": "0.0"},
                {"instrument_id": "FAST_STOCK", "weight": "1.0"},
            ]
        },
        "shelf_entries": [
            {"instrument_id": "SLOW_FUND", "status": "APPROVED", "settlement_days": 3},
            {"instrument_id": "FAST_STOCK", "status": "APPROVED", "settlement_days": 1},
        ],
        "options": {"enable_settlement_awareness": False},
    }

    disabled = client.post(
        "/api/v1/rebalance/simulate",
        json=payload,
        headers={"Idempotency-Key": "test-key-settlement-off"},
    )
    assert disabled.status_code == 200
    assert disabled.json()["status"] == "READY"

    payload["options"]["enable_settlement_awareness"] = True
    payload["options"]["settlement_horizon_days"] = 3

    enabled = client.post(
        "/api/v1/rebalance/simulate",
        json=payload,
        headers={"Idempotency-Key": "test-key-settlement-on"},
    )
    assert enabled.status_code == 200
    body = enabled.json()
    assert body["status"] == "BLOCKED"
    assert "OVERDRAFT_ON_T_PLUS_1" in body["diagnostics"]["warnings"]


def test_simulate_tax_awareness_toggle_is_request_scoped(client):
    payload = {
        "portfolio_snapshot": {
            "portfolio_id": "pf_tax_api",
            "base_currency": "USD",
            "positions": [
                {
                    "instrument_id": "ABC",
                    "quantity": "100",
                    "lots": [
                        {
                            "lot_id": "L_LOW",
                            "quantity": "50",
                            "unit_cost": {"amount": "10", "currency": "USD"},
                            "purchase_date": "2024-01-01",
                        },
                        {
                            "lot_id": "L_HIGH",
                            "quantity": "50",
                            "unit_cost": {"amount": "100", "currency": "USD"},
                            "purchase_date": "2024-02-01",
                        },
                    ],
                }
            ],
            "cash_balances": [{"currency": "USD", "amount": "0"}],
        },
        "market_data_snapshot": {
            "prices": [{"instrument_id": "ABC", "price": "100", "currency": "USD"}],
            "fx_rates": [],
        },
        "model_portfolio": {"targets": [{"instrument_id": "ABC", "weight": "0.0"}]},
        "shelf_entries": [{"instrument_id": "ABC", "status": "APPROVED"}],
        "options": {
            "enable_tax_awareness": False,
            "max_realized_capital_gains": "100",
        },
    }

    disabled = client.post(
        "/api/v1/rebalance/simulate",
        json=payload,
        headers={"Idempotency-Key": "test-key-tax-off"},
    )
    assert disabled.status_code == 200
    assert Decimal(disabled.json()["intents"][0]["quantity"]) == Decimal("100")
    assert disabled.json()["tax_impact"] is None

    payload["options"]["enable_tax_awareness"] = True
    enabled = client.post(
        "/api/v1/rebalance/simulate",
        json=payload,
        headers={"Idempotency-Key": "test-key-tax-on"},
    )
    assert enabled.status_code == 200
    body = enabled.json()
    assert Decimal(body["intents"][0]["quantity"]) < Decimal("100")
    assert "TAX_BUDGET_LIMIT_REACHED" in body["diagnostics"]["warnings"]
    assert body["tax_impact"]["budget_used"]["amount"] == "100"


def test_dpm_run_workflow_endpoints_happy_path_and_invalid_transition(client, monkeypatch):
    monkeypatch.setenv("DPM_WORKFLOW_ENABLED", "true")
    payload = get_valid_payload()
    payload["options"]["single_position_max_weight"] = "0.5"
    simulate = client.post(
        "/api/v1/rebalance/simulate",
        json=payload,
        headers={"Idempotency-Key": "test-key-workflow-1", "X-Correlation-Id": "corr-workflow-1"},
    )
    assert simulate.status_code == 200
    run = simulate.json()
    assert run["status"] == "PENDING_REVIEW"
    run_id = run["rebalance_run_id"]

    workflow = client.get(f"/api/v1/rebalance/runs/{run_id}/workflow")
    assert workflow.status_code == 200
    workflow_body = workflow.json()
    assert workflow_body["run_id"] == run_id
    assert workflow_body["run_status"] == "PENDING_REVIEW"
    assert workflow_body["workflow_status"] == "PENDING_REVIEW"
    assert workflow_body["requires_review"] is True
    assert workflow_body["latest_decision"] is None

    workflow_by_correlation = client.get(
        "/api/v1/rebalance/runs/by-correlation/corr-workflow-1/workflow"
    )
    assert workflow_by_correlation.status_code == 200
    assert workflow_by_correlation.json()["run_id"] == run_id
    workflow_by_idempotency = client.get(
        "/api/v1/rebalance/runs/idempotency/test-key-workflow-1/workflow"
    )
    assert workflow_by_idempotency.status_code == 200
    assert workflow_by_idempotency.json()["run_id"] == run_id

    request_changes = client.post(
        f"/api/v1/rebalance/runs/{run_id}/workflow/actions",
        json={
            "action": "REQUEST_CHANGES",
            "reason_code": "REQUIRES_ADVISOR_NOTE",
            "comment": "Please add rationale.",
            "actor_id": "reviewer_1",
        },
        headers={"X-Correlation-Id": "corr-workflow-2"},
    )
    assert request_changes.status_code == 200
    request_changes_body = request_changes.json()
    assert request_changes_body["workflow_status"] == "PENDING_REVIEW"
    assert request_changes_body["latest_decision"]["action"] == "REQUEST_CHANGES"
    assert request_changes_body["latest_decision"]["correlation_id"] == "corr-workflow-2"

    request_changes_by_correlation = client.post(
        "/api/v1/rebalance/runs/by-correlation/corr-workflow-1/workflow/actions",
        json={
            "action": "REQUEST_CHANGES",
            "reason_code": "NEEDS_ONE_MORE_FIX",
            "comment": "Resolve minor note",
            "actor_id": "reviewer_1",
        },
        headers={"X-Correlation-Id": "corr-workflow-2b"},
    )
    assert request_changes_by_correlation.status_code == 200
    assert (
        request_changes_by_correlation.json()["latest_decision"]["correlation_id"]
        == "corr-workflow-2b"
    )

    approved = client.post(
        f"/api/v1/rebalance/runs/{run_id}/workflow/actions",
        json={
            "action": "APPROVE",
            "reason_code": "REVIEW_APPROVED",
            "comment": None,
            "actor_id": "reviewer_2",
        },
        headers={"X-Correlation-Id": "corr-workflow-3"},
    )
    assert approved.status_code == 200
    approved_body = approved.json()
    assert approved_body["workflow_status"] == "APPROVED"
    assert approved_body["latest_decision"]["action"] == "APPROVE"
    assert approved_body["latest_decision"]["actor_id"] == "reviewer_2"

    rejected_by_idempotency = client.post(
        "/api/v1/rebalance/runs/idempotency/test-key-workflow-1/workflow/actions",
        json={
            "action": "REJECT",
            "reason_code": "POLICY_BREACH_REJECTED",
            "comment": "Rejected for control reasons",
            "actor_id": "reviewer_3",
        },
        headers={"X-Correlation-Id": "corr-workflow-4"},
    )
    assert rejected_by_idempotency.status_code == 200
    rejected_body = rejected_by_idempotency.json()
    assert rejected_body["workflow_status"] == "REJECTED"
    assert rejected_body["latest_decision"]["action"] == "REJECT"
    assert rejected_body["latest_decision"]["correlation_id"] == "corr-workflow-4"

    history = client.get(f"/api/v1/rebalance/runs/{run_id}/workflow/history")
    assert history.status_code == 200
    history_body = history.json()
    assert history_body["run_id"] == run_id
    assert len(history_body["decisions"]) == 4
    assert history_body["decisions"][0]["action"] == "REQUEST_CHANGES"
    assert history_body["decisions"][1]["action"] == "REQUEST_CHANGES"
    assert history_body["decisions"][2]["action"] == "APPROVE"
    assert history_body["decisions"][3]["action"] == "REJECT"

    history_by_correlation = client.get(
        "/api/v1/rebalance/runs/by-correlation/corr-workflow-1/workflow/history"
    )
    assert history_by_correlation.status_code == 200
    history_by_correlation_body = history_by_correlation.json()
    assert history_by_correlation_body["run_id"] == run_id
    assert len(history_by_correlation_body["decisions"]) == 4
    history_by_idempotency = client.get(
        "/api/v1/rebalance/runs/idempotency/test-key-workflow-1/workflow/history"
    )
    assert history_by_idempotency.status_code == 200
    history_by_idempotency_body = history_by_idempotency.json()
    assert history_by_idempotency_body["run_id"] == run_id
    assert len(history_by_idempotency_body["decisions"]) == 4

    workflow_decisions_by_correlation = client.get(
        "/api/v1/rebalance/workflow/decisions/by-correlation/corr-workflow-1"
    )
    assert workflow_decisions_by_correlation.status_code == 200
    workflow_decisions_by_correlation_body = workflow_decisions_by_correlation.json()
    assert workflow_decisions_by_correlation_body["run_id"] == run_id
    assert len(workflow_decisions_by_correlation_body["decisions"]) == 4

    unsupported_workflow_queries = [
        f"/api/v1/rebalance/runs/{run_id}/workflow?include_history=true",
        "/api/v1/rebalance/runs/by-correlation/corr-workflow-1/workflow?runId=legacy",
        "/api/v1/rebalance/runs/idempotency/test-key-workflow-1/workflow?history=true",
        f"/api/v1/rebalance/runs/{run_id}/workflow/history?limit=1",
        "/api/v1/rebalance/runs/by-correlation/corr-workflow-1/workflow/history?limit=1",
        "/api/v1/rebalance/runs/idempotency/test-key-workflow-1/workflow/history?limit=1",
        "/api/v1/rebalance/workflow/decisions/by-correlation/corr-workflow-1?limit=1",
    ]
    for url in unsupported_workflow_queries:
        unsupported = client.get(url)
        assert unsupported.status_code == 422
        assert unsupported.json()["detail"].startswith("UNSUPPORTED_QUERY_PARAMETER:")

    unsupported_action_query = client.post(
        f"/api/v1/rebalance/runs/{run_id}/workflow/actions?dry_run=true",
        json={
            "action": "APPROVE",
            "reason_code": "REVIEW_APPROVED",
            "comment": None,
            "actor_id": "reviewer_2",
        },
    )
    assert unsupported_action_query.status_code == 422
    assert unsupported_action_query.json()["detail"] == (
        "UNSUPPORTED_QUERY_PARAMETER: dry_run not supported for this endpoint"
    )

    invalid = client.post(
        f"/api/v1/rebalance/runs/{run_id}/workflow/actions",
        json={
            "action": "REJECT",
            "reason_code": "REVIEW_APPROVED",
            "comment": None,
            "actor_id": "reviewer_2",
        },
    )
    assert invalid.status_code == 409
    assert invalid.json()["detail"] == "DPM_WORKFLOW_INVALID_TRANSITION"


def test_dpm_workflow_decision_list_endpoint_filters_and_cursor(client, monkeypatch):
    monkeypatch.setenv("DPM_WORKFLOW_ENABLED", "true")
    payload = get_valid_payload()
    payload["options"]["single_position_max_weight"] = "0.5"
    simulate = client.post(
        "/api/v1/rebalance/simulate",
        json=payload,
        headers={
            "Idempotency-Key": "test-key-workflow-list-1",
            "X-Correlation-Id": "corr-workflow-list-1",
        },
    )
    assert simulate.status_code == 200
    run_id = simulate.json()["rebalance_run_id"]

    action_one = client.post(
        f"/api/v1/rebalance/runs/{run_id}/workflow/actions",
        json={
            "action": "REQUEST_CHANGES",
            "reason_code": "REQUIRES_ADVISOR_NOTE",
            "comment": "Need additional detail",
            "actor_id": "reviewer_list_1",
        },
        headers={"X-Correlation-Id": "corr-workflow-list-2"},
    )
    assert action_one.status_code == 200
    action_two = client.post(
        f"/api/v1/rebalance/runs/{run_id}/workflow/actions",
        json={
            "action": "APPROVE",
            "reason_code": "REVIEW_APPROVED",
            "comment": None,
            "actor_id": "reviewer_list_2",
        },
        headers={"X-Correlation-Id": "corr-workflow-list-3"},
    )
    assert action_two.status_code == 200

    all_rows = client.get("/api/v1/rebalance/workflow/decisions?limit=10")
    assert all_rows.status_code == 200
    all_body = all_rows.json()
    assert len(all_body["items"]) >= 2
    assert (
        all_body["items"][0]["decision_id"] == action_two.json()["latest_decision"]["decision_id"]
    )
    assert (
        all_body["items"][1]["decision_id"] == action_one.json()["latest_decision"]["decision_id"]
    )

    by_actor = client.get("/api/v1/rebalance/workflow/decisions?actor_id=reviewer_list_2&limit=10")
    assert by_actor.status_code == 200
    by_actor_body = by_actor.json()
    assert [item["actor_id"] for item in by_actor_body["items"]] == ["reviewer_list_2"]

    by_run = client.get(f"/api/v1/rebalance/workflow/decisions?rebalance_run_id={run_id}&limit=10")
    assert by_run.status_code == 200
    assert len(by_run.json()["items"]) == 2

    page_one = client.get("/api/v1/rebalance/workflow/decisions?limit=1")
    assert page_one.status_code == 200
    page_one_body = page_one.json()
    assert len(page_one_body["items"]) == 1
    assert page_one_body["next_cursor"] is not None

    page_two = client.get(
        f"/api/v1/rebalance/workflow/decisions?limit=1&cursor={page_one_body['next_cursor']}"
    )
    assert page_two.status_code == 200
    page_two_body = page_two.json()
    assert len(page_two_body["items"]) == 1
    assert page_two_body["items"][0]["decision_id"] != page_one_body["items"][0]["decision_id"]


def test_dpm_run_workflow_endpoints_disabled_and_not_required_behavior(client, monkeypatch):
    payload = get_valid_payload()
    simulate = client.post(
        "/api/v1/rebalance/simulate",
        json=payload,
        headers={"Idempotency-Key": "test-key-workflow-2"},
    )
    assert simulate.status_code == 200
    run_id = simulate.json()["rebalance_run_id"]

    disabled = client.get(f"/api/v1/rebalance/runs/{run_id}/workflow")
    assert disabled.status_code == 404
    assert disabled.json()["detail"] == "DPM_WORKFLOW_DISABLED"
    decision_lookup_disabled = client.get(
        "/api/v1/rebalance/workflow/decisions/by-correlation/corr-missing"
    )
    assert decision_lookup_disabled.status_code == 404
    assert decision_lookup_disabled.json()["detail"] == "DPM_WORKFLOW_DISABLED"

    monkeypatch.setenv("DPM_WORKFLOW_ENABLED", "true")
    reset_dpm_run_support_service_for_tests()
    simulate_ready = client.post(
        "/api/v1/rebalance/simulate",
        json=payload,
        headers={"Idempotency-Key": "test-key-workflow-3"},
    )
    assert simulate_ready.status_code == 200
    ready_run_id = simulate_ready.json()["rebalance_run_id"]
    not_required = client.post(
        f"/api/v1/rebalance/runs/{ready_run_id}/workflow/actions",
        json={
            "action": "APPROVE",
            "reason_code": "REVIEW_APPROVED",
            "comment": None,
            "actor_id": "reviewer_1",
        },
    )
    assert not_required.status_code == 409
    assert not_required.json()["detail"] == "DPM_WORKFLOW_NOT_REQUIRED_FOR_RUN_STATUS"

    missing_by_correlation = client.get(
        "/api/v1/rebalance/runs/by-correlation/corr-missing/workflow"
    )
    assert missing_by_correlation.status_code == 404
    assert missing_by_correlation.json()["detail"] == "DPM_RUN_NOT_FOUND"
    missing_by_idempotency = client.get("/api/v1/rebalance/runs/idempotency/idem-missing/workflow")
    assert missing_by_idempotency.status_code == 404
    assert missing_by_idempotency.json()["detail"] == "DPM_IDEMPOTENCY_KEY_NOT_FOUND"
    missing_action_by_correlation = client.post(
        "/api/v1/rebalance/runs/by-correlation/corr-missing/workflow/actions",
        json={
            "action": "APPROVE",
            "reason_code": "REVIEW_APPROVED",
            "comment": None,
            "actor_id": "reviewer_1",
        },
    )
    assert missing_action_by_correlation.status_code == 404
    assert missing_action_by_correlation.json()["detail"] == "DPM_RUN_NOT_FOUND"
    missing_action_by_idempotency = client.post(
        "/api/v1/rebalance/runs/idempotency/idem-missing/workflow/actions",
        json={
            "action": "APPROVE",
            "reason_code": "REVIEW_APPROVED",
            "comment": None,
            "actor_id": "reviewer_1",
        },
    )
    assert missing_action_by_idempotency.status_code == 404
    assert missing_action_by_idempotency.json()["detail"] == "DPM_IDEMPOTENCY_KEY_NOT_FOUND"

    monkeypatch.setenv("DPM_WORKFLOW_ENABLED", "false")
    reset_dpm_run_support_service_for_tests()
    workflow_decision_list_disabled = client.get("/api/v1/rebalance/workflow/decisions?limit=10")
    assert workflow_decision_list_disabled.status_code == 404
    assert workflow_decision_list_disabled.json()["detail"] == "DPM_WORKFLOW_DISABLED"
