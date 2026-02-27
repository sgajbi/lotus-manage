"""
FILE: tests/demo/test_demo_scenarios.py
Verifies that the public demo scenarios in docs/demo/ execute correctly.
"""

import json
import os
from importlib.util import find_spec

import pytest
from fastapi.testclient import TestClient

from src.api.main import app, get_db_session
from src.api.routers.dpm_runs import reset_dpm_run_support_service_for_tests
from src.api.routers.proposals import reset_proposal_workflow_service_for_tests
from src.core.dpm_engine import run_simulation
from src.core.models import (
    EngineOptions,
    MarketDataSnapshot,
    ModelPortfolio,
    PortfolioSnapshot,
    ShelfEntry,
)
from tests.shared.factories import valid_api_payload

DEMO_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "docs", "demo")
_SOLVER_AVAILABLE = find_spec("cvxpy") is not None and find_spec("numpy") is not None


def load_demo_scenario(filename):
    path = os.path.join(DEMO_DIR, filename)
    with open(path, "r") as f:
        data = json.load(f)
    return data


def _proposal_create_payload(portfolio_id: str) -> dict:
    return {
        "created_by": "advisor_e2e",
        "metadata": {
            "title": "E2E proposal",
            "advisor_notes": "workflow validation",
            "jurisdiction": "SG",
            "mandate_id": "mandate_e2e",
        },
        "simulate_request": {
            "portfolio_snapshot": {
                "portfolio_id": portfolio_id,
                "base_currency": "USD",
                "positions": [{"instrument_id": "EQ_OLD", "quantity": "10"}],
                "cash_balances": [{"currency": "USD", "amount": "1000"}],
            },
            "market_data_snapshot": {
                "prices": [
                    {"instrument_id": "EQ_OLD", "price": "100", "currency": "USD"},
                    {"instrument_id": "EQ_NEW", "price": "50", "currency": "USD"},
                ],
                "fx_rates": [],
            },
            "shelf_entries": [
                {"instrument_id": "EQ_OLD", "status": "APPROVED"},
                {"instrument_id": "EQ_NEW", "status": "APPROVED"},
            ],
            "options": {"enable_proposal_simulation": True},
            "proposed_cash_flows": [{"currency": "USD", "amount": "100"}],
            "proposed_trades": [{"side": "BUY", "instrument_id": "EQ_NEW", "quantity": "2"}],
        },
    }


@pytest.mark.parametrize(
    "filename, expected_status",
    [
        ("01_standard_drift.json", "READY"),
        ("02_sell_to_fund.json", "READY"),
        ("03_multi_currency_fx.json", "READY"),
        ("04_safety_sell_only.json", "PENDING_REVIEW"),
        ("05_safety_hard_block_price.json", "BLOCKED"),
        ("06_tax_aware_hifo.json", "READY"),
        ("07_settlement_overdraft_block.json", "BLOCKED"),
        ("08_solver_mode.json", "READY"),
    ],
)
def test_demo_scenario_execution(filename, expected_status):
    data = load_demo_scenario(filename)

    portfolio = PortfolioSnapshot(**data["portfolio_snapshot"])
    market_data = MarketDataSnapshot(**data["market_data_snapshot"])
    model = ModelPortfolio(**data["model_portfolio"])
    shelf = [ShelfEntry(**s) for s in data["shelf_entries"]]
    options = EngineOptions(**data.get("options", {}))

    result = run_simulation(portfolio, market_data, model, shelf, options)

    effective_expected = expected_status
    if filename == "08_solver_mode.json" and not _SOLVER_AVAILABLE:
        effective_expected = "BLOCKED"

    assert result.status == effective_expected, (
        f"Scenario {filename} failed. Got {result.status}, expected {effective_expected}"
    )


async def _override_get_db_session():
    yield None


def test_demo_batch_scenario_execution():
    data = load_demo_scenario("09_batch_what_if_analysis.json")
    with TestClient(app) as client:
        original_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db_session] = _override_get_db_session
        try:
            response = client.post("/api/v1/rebalance/analyze", json=data)
        finally:
            app.dependency_overrides = original_overrides

    assert response.status_code == 200
    body = response.json()
    assert set(body["results"].keys()) == {"baseline", "tax_budget", "settlement_guard"}
    assert set(body["comparison_metrics"].keys()) == {"baseline", "tax_budget", "settlement_guard"}
    assert body["failed_scenarios"] == {}


def test_demo_async_batch_scenario_execution():
    data = load_demo_scenario("26_dpm_async_batch_analysis.json")
    with TestClient(app) as client:
        original_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db_session] = _override_get_db_session
        try:
            accepted = client.post(
                "/api/v1/rebalance/analyze/async",
                json=data,
                headers={"X-Correlation-Id": "demo-corr-26-async"},
            )
            assert accepted.status_code == 202
            operation_id = accepted.json()["operation_id"]
            operation = client.get(f"/api/v1/rebalance/operations/{operation_id}")
        finally:
            app.dependency_overrides = original_overrides

    assert operation.status_code == 200
    operation_body = operation.json()
    assert operation_body["status"] == "SUCCEEDED"
    assert operation_body["result"]["warnings"] == ["PARTIAL_BATCH_FAILURE"]
    assert set(operation_body["result"]["failed_scenarios"].keys()) == {"invalid_options"}
    assert set(operation_body["result"]["results"].keys()) == {"baseline"}


def test_demo_dpm_supportability_artifact_flow_via_api():
    data = load_demo_scenario("27_dpm_supportability_artifact_flow.json")
    with TestClient(app) as client:
        original_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db_session] = _override_get_db_session
        try:
            simulate = client.post(
                "/api/v1/rebalance/simulate",
                json=data,
                headers={
                    "Idempotency-Key": "demo-27-supportability",
                    "X-Correlation-Id": "demo-corr-27-supportability",
                },
            )
            assert simulate.status_code == 200
            run_id = simulate.json()["rebalance_run_id"]

            by_run = client.get(f"/api/v1/rebalance/runs/{run_id}")
            by_correlation = client.get(
                "/api/v1/rebalance/runs/by-correlation/demo-corr-27-supportability"
            )
            by_idempotency = client.get("/api/v1/rebalance/runs/idempotency/demo-27-supportability")
            artifact_one = client.get(f"/api/v1/rebalance/runs/{run_id}/artifact")
            artifact_two = client.get(f"/api/v1/rebalance/runs/{run_id}/artifact")
        finally:
            app.dependency_overrides = original_overrides

    assert by_run.status_code == 200
    assert by_correlation.status_code == 200
    assert by_idempotency.status_code == 200
    assert artifact_one.status_code == 200
    assert artifact_two.status_code == 200
    assert by_run.json()["rebalance_run_id"] == run_id
    assert by_correlation.json()["rebalance_run_id"] == run_id
    assert by_idempotency.json()["rebalance_run_id"] == run_id
    assert artifact_one.json()["rebalance_run_id"] == run_id
    assert (
        artifact_one.json()["evidence"]["hashes"]["artifact_hash"]
        == artifact_two.json()["evidence"]["hashes"]["artifact_hash"]
    )


def test_demo_dpm_async_manual_execute_guard_via_api():
    data = load_demo_scenario("28_dpm_async_manual_execute_guard.json")
    with TestClient(app) as client:
        original_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db_session] = _override_get_db_session
        try:
            accepted = client.post(
                "/api/v1/rebalance/analyze/async",
                json=data,
                headers={"X-Correlation-Id": "demo-corr-28-async-inline"},
            )
            assert accepted.status_code == 202
            operation_id = accepted.json()["operation_id"]
            execute = client.post(f"/api/v1/rebalance/operations/{operation_id}/execute")
        finally:
            app.dependency_overrides = original_overrides

    assert execute.status_code == 409
    assert execute.json()["detail"] == "DPM_ASYNC_OPERATION_NOT_EXECUTABLE"


def test_demo_dpm_idempotency_history_supportability_via_api(monkeypatch):
    data = load_demo_scenario("30_dpm_idempotency_history_supportability.json")
    monkeypatch.setenv("DPM_IDEMPOTENCY_REPLAY_ENABLED", "false")
    monkeypatch.setenv("DPM_IDEMPOTENCY_HISTORY_APIS_ENABLED", "true")
    with TestClient(app) as client:
        original_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db_session] = _override_get_db_session
        try:
            first = client.post(
                "/api/v1/rebalance/simulate",
                json=data,
                headers={
                    "Idempotency-Key": "demo-30-idem-history",
                    "X-Correlation-Id": "demo-corr-30-idem-history-1",
                },
            )
            assert first.status_code == 200
            first_run = first.json()["rebalance_run_id"]

            data["options"]["single_position_max_weight"] = "0.50"
            second = client.post(
                "/api/v1/rebalance/simulate",
                json=data,
                headers={
                    "Idempotency-Key": "demo-30-idem-history",
                    "X-Correlation-Id": "demo-corr-30-idem-history-2",
                },
            )
            assert second.status_code == 200
            second_run = second.json()["rebalance_run_id"]

            history = client.get("/api/v1/rebalance/idempotency/demo-30-idem-history/history")
        finally:
            app.dependency_overrides = original_overrides

    assert history.status_code == 200
    body = history.json()
    assert body["idempotency_key"] == "demo-30-idem-history"
    assert len(body["history"]) == 2
    assert body["history"][0]["rebalance_run_id"] == first_run
    assert body["history"][0]["correlation_id"] == "demo-corr-30-idem-history-1"
    assert body["history"][1]["rebalance_run_id"] == second_run
    assert body["history"][1]["correlation_id"] == "demo-corr-30-idem-history-2"


def test_demo_dpm_policy_pack_supportability_diagnostics_via_api():
    data = load_demo_scenario("31_dpm_policy_pack_supportability_diagnostics.json")
    with TestClient(app) as client:
        original_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db_session] = _override_get_db_session
        try:
            simulate = client.post(
                "/api/v1/rebalance/simulate",
                json=data,
                headers={
                    "Idempotency-Key": "demo-31-policy-pack",
                    "X-Policy-Pack-Id": "dpm_standard_v1",
                    "X-Tenant-Policy-Pack-Id": "dpm_tenant_default_v1",
                    "X-Tenant-Id": "tenant_001",
                },
            )
            assert simulate.status_code == 200

            effective = client.get(
                "/api/v1/rebalance/policies/effective",
                headers={
                    "X-Policy-Pack-Id": "dpm_standard_v1",
                    "X-Tenant-Policy-Pack-Id": "dpm_tenant_default_v1",
                    "X-Tenant-Id": "tenant_001",
                },
            )
            catalog = client.get(
                "/api/v1/rebalance/policies/catalog",
                headers={
                    "X-Policy-Pack-Id": "dpm_standard_v1",
                    "X-Tenant-Policy-Pack-Id": "dpm_tenant_default_v1",
                    "X-Tenant-Id": "tenant_001",
                },
            )
        finally:
            app.dependency_overrides = original_overrides

    assert effective.status_code == 200
    assert catalog.status_code == 200
    effective_body = effective.json()
    assert set({"enabled", "selected_policy_pack_id", "source"}).issubset(effective_body.keys())
    catalog_body = catalog.json()
    assert set(
        {
            "enabled",
            "total",
            "selected_policy_pack_id",
            "selected_policy_pack_present",
            "selected_policy_pack_source",
            "items",
        }
    ).issubset(catalog_body.keys())


def test_demo_dpm_supportability_summary_metrics_via_api():
    data = load_demo_scenario("32_dpm_supportability_summary_metrics.json")
    with TestClient(app) as client:
        original_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db_session] = _override_get_db_session
        try:
            simulate = client.post(
                "/api/v1/rebalance/simulate",
                json=data,
                headers={
                    "Idempotency-Key": "demo-32-support-summary",
                    "X-Correlation-Id": "demo-corr-32-support-summary",
                },
            )
            assert simulate.status_code == 200

            summary = client.get("/api/v1/rebalance/supportability/summary")
        finally:
            app.dependency_overrides = original_overrides

    assert summary.status_code == 200
    body = summary.json()
    assert set(
        {
            "store_backend",
            "retention_days",
            "run_count",
            "operation_count",
            "operation_status_counts",
            "run_status_counts",
            "workflow_decision_count",
            "workflow_action_counts",
            "workflow_reason_code_counts",
            "lineage_edge_count",
        }
    ).issubset(body.keys())
    assert body["run_count"] >= 1


def test_demo_dpm_support_bundle_optional_sections_via_api():
    data = load_demo_scenario("27_dpm_supportability_artifact_flow.json")
    with TestClient(app) as client:
        original_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db_session] = _override_get_db_session
        try:
            simulate = client.post(
                "/api/v1/rebalance/simulate",
                json=data,
                headers={
                    "Idempotency-Key": "demo-33-bundle-optional",
                    "X-Correlation-Id": "demo-corr-33-bundle-optional",
                },
            )
            assert simulate.status_code == 200
            run_id = simulate.json()["rebalance_run_id"]
            bundle = client.get(
                f"/api/v1/rebalance/runs/{run_id}/support-bundle"
                "?include_artifact=false&include_async_operation=false&include_idempotency_history=false"
            )
        finally:
            app.dependency_overrides = original_overrides

    assert bundle.status_code == 200
    body = bundle.json()
    assert body["run"]["rebalance_run_id"] == run_id
    assert body["artifact"] is None
    assert body["async_operation"] is None
    assert body["idempotency_history"] is None


def test_demo_dpm_lineage_filtering_via_api(monkeypatch):
    monkeypatch.setenv("DPM_LINEAGE_APIS_ENABLED", "true")
    data = load_demo_scenario("27_dpm_supportability_artifact_flow.json")
    with TestClient(app) as client:
        original_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db_session] = _override_get_db_session
        try:
            simulate = client.post(
                "/api/v1/rebalance/simulate",
                json=data,
                headers={
                    "Idempotency-Key": "demo-34-lineage-filter",
                    "X-Correlation-Id": "demo-corr-34-lineage-filter",
                },
            )
            assert simulate.status_code == 200
            run_id = simulate.json()["rebalance_run_id"]
            filtered = client.get(
                "/api/v1/rebalance/lineage/demo-corr-34-lineage-filter?edge_type=CORRELATION_TO_RUN"
            )
        finally:
            app.dependency_overrides = original_overrides

    assert filtered.status_code == 200
    edges = filtered.json()["edges"]
    assert len(edges) == 1
    assert edges[0]["edge_type"] == "CORRELATION_TO_RUN"
    assert edges[0]["target_entity_id"] == run_id


def test_demo_dpm_workflow_decision_listing_via_api(monkeypatch):
    monkeypatch.setenv("DPM_WORKFLOW_ENABLED", "true")
    reset_dpm_run_support_service_for_tests()
    data = valid_api_payload()
    data["options"]["single_position_max_weight"] = "0.5"
    with TestClient(app) as client:
        original_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db_session] = _override_get_db_session
        try:
            simulate = client.post(
                "/api/v1/rebalance/simulate",
                json=data,
                headers={
                    "Idempotency-Key": "demo-35-workflow",
                    "X-Correlation-Id": "demo-corr-35-workflow",
                },
            )
            assert simulate.status_code == 200
            run_id = simulate.json()["rebalance_run_id"]
            approve = client.post(
                f"/api/v1/rebalance/runs/{run_id}/workflow/actions",
                json={
                    "action": "APPROVE",
                    "reason_code": "REVIEW_APPROVED",
                    "comment": None,
                    "actor_id": "e2e_reviewer",
                },
            )
            decision_list = client.get(
                "/api/v1/rebalance/workflow/decisions?action=APPROVE&limit=10"
            )
        finally:
            app.dependency_overrides = original_overrides

    assert approve.status_code == 200
    assert decision_list.status_code == 200
    assert any(item["run_id"] == run_id for item in decision_list.json()["items"])


def test_demo_advisory_async_create_and_lookup_via_api():
    with TestClient(app) as client:
        original_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db_session] = _override_get_db_session
        reset_proposal_workflow_service_for_tests()
        try:
            accepted = client.post(
                "/api/v1/rebalance/proposals/async",
                json=_proposal_create_payload("pf_demo_async_1"),
                headers={
                    "Idempotency-Key": "demo-36-proposal-async",
                    "X-Correlation-Id": "demo-corr-36-proposal-async",
                },
            )
            assert accepted.status_code == 202
            operation_id = accepted.json()["operation_id"]
            by_operation = client.get(f"/api/v1/rebalance/proposals/operations/{operation_id}")
            by_correlation = client.get(
                "/api/v1/rebalance/proposals/operations/by-correlation/demo-corr-36-proposal-async"
            )
        finally:
            app.dependency_overrides = original_overrides
            reset_proposal_workflow_service_for_tests()

    assert by_operation.status_code == 200
    assert by_correlation.status_code == 200
    assert by_operation.json()["operation_id"] == operation_id
    assert by_correlation.json()["operation_id"] == operation_id


def test_demo_advisory_async_version_via_api():
    with TestClient(app) as client:
        original_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db_session] = _override_get_db_session
        reset_proposal_workflow_service_for_tests()
        try:
            created = client.post(
                "/api/v1/rebalance/proposals",
                json=_proposal_create_payload("pf_demo_async_2"),
                headers={"Idempotency-Key": "demo-37-proposal-async-base"},
            )
            assert created.status_code == 200
            proposal_id = created.json()["proposal"]["proposal_id"]

            accepted = client.post(
                f"/api/v1/rebalance/proposals/{proposal_id}/versions/async",
                json={
                    "created_by": "advisor_e2e",
                    "metadata": {"title": "E2E async version"},
                    "simulate_request": _proposal_create_payload("pf_demo_async_2")[
                        "simulate_request"
                    ],
                },
                headers={"X-Correlation-Id": "demo-corr-37-proposal-async-version"},
            )
            assert accepted.status_code == 202
            operation_id = accepted.json()["operation_id"]
            operation = client.get(f"/api/v1/rebalance/proposals/operations/{operation_id}")
        finally:
            app.dependency_overrides = original_overrides
            reset_proposal_workflow_service_for_tests()

    assert operation.status_code == 200
    assert operation.json()["operation_id"] == operation_id


@pytest.mark.parametrize(
    "filename, expected_status",
    [
        ("10_advisory_proposal_simulate.json", "READY"),
        ("11_advisory_auto_funding_single_ccy.json", "READY"),
        ("12_advisory_partial_funding.json", "READY"),
        ("13_advisory_missing_fx_blocked.json", "BLOCKED"),
        ("14_advisory_drift_asset_class.json", "READY"),
        ("15_advisory_drift_instrument.json", "READY"),
        ("16_advisory_suitability_resolved_single_position.json", "READY"),
        ("17_advisory_suitability_new_issuer_breach.json", "READY"),
        ("18_advisory_suitability_sell_only_violation.json", "BLOCKED"),
    ],
)
def test_demo_advisory_scenarios_via_api(filename, expected_status):
    data = load_demo_scenario(filename)
    with TestClient(app) as client:
        original_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db_session] = _override_get_db_session
        reset_proposal_workflow_service_for_tests()
        try:
            response = client.post(
                "/api/v1/rebalance/proposals/simulate",
                json=data,
                headers={"Idempotency-Key": f"demo-{filename}"},
            )
        finally:
            app.dependency_overrides = original_overrides
            reset_proposal_workflow_service_for_tests()

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == expected_status

    if filename in {"11_advisory_auto_funding_single_ccy.json", "12_advisory_partial_funding.json"}:
        assert [intent["intent_type"] for intent in body["intents"]] == [
            "FX_SPOT",
            "SECURITY_TRADE",
        ]
        assert body["intents"][1]["dependencies"] == [body["intents"][0]["intent_id"]]
    if filename in {"14_advisory_drift_asset_class.json", "15_advisory_drift_instrument.json"}:
        assert "drift_analysis" in body
    if filename in {
        "16_advisory_suitability_resolved_single_position.json",
        "17_advisory_suitability_new_issuer_breach.json",
        "18_advisory_suitability_sell_only_violation.json",
    }:
        assert "suitability" in body


def test_demo_advisory_artifact_scenario_via_api():
    data = load_demo_scenario("19_advisory_proposal_artifact.json")
    with TestClient(app) as client:
        original_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db_session] = _override_get_db_session
        reset_proposal_workflow_service_for_tests()
        try:
            response = client.post(
                "/api/v1/rebalance/proposals/artifact",
                json=data,
                headers={"Idempotency-Key": "demo-19-advisory-artifact"},
            )
        finally:
            app.dependency_overrides = original_overrides
            reset_proposal_workflow_service_for_tests()

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "READY"
    assert body["summary"]["recommended_next_step"] == "CLIENT_CONSENT"
    assert body["trades_and_funding"]["trade_list"]
    assert body["evidence_bundle"]["hashes"]["artifact_hash"].startswith("sha256:")


@pytest.mark.parametrize(
    ("path", "expected_detail"),
    [
        ("/api/v1/rebalance/runs/rr_missing", "DPM_RUN_NOT_FOUND"),
        ("/api/v1/rebalance/runs/by-correlation/corr_missing", "DPM_RUN_NOT_FOUND"),
        ("/api/v1/rebalance/runs/idempotency/idem_missing", "DPM_IDEMPOTENCY_KEY_NOT_FOUND"),
        ("/api/v1/rebalance/operations/op_missing", "DPM_ASYNC_OPERATION_NOT_FOUND"),
        (
            "/api/v1/rebalance/operations/by-correlation/corr_missing",
            "DPM_ASYNC_OPERATION_NOT_FOUND",
        ),
    ],
)
def test_demo_supportability_lookup_not_found_matrix(path, expected_detail):
    with TestClient(app) as client:
        original_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db_session] = _override_get_db_session
        try:
            response = client.get(path)
        finally:
            app.dependency_overrides = original_overrides

    assert response.status_code == 404
    assert response.json()["detail"] == expected_detail


@pytest.mark.parametrize(
    ("env_name", "env_value", "path", "expected_detail"),
    [
        (
            "DPM_ASYNC_OPERATIONS_ENABLED",
            "false",
            "/api/v1/rebalance/operations",
            "DPM_ASYNC_OPERATIONS_DISABLED",
        ),
        (
            "DPM_LINEAGE_APIS_ENABLED",
            "false",
            "/api/v1/rebalance/lineage/corr_missing",
            "DPM_LINEAGE_APIS_DISABLED",
        ),
        (
            "DPM_WORKFLOW_ENABLED",
            "false",
            "/api/v1/rebalance/workflow/decisions",
            "DPM_WORKFLOW_DISABLED",
        ),
    ],
)
def test_demo_supportability_feature_flag_guard_matrix(
    monkeypatch, env_name, env_value, path, expected_detail
):
    monkeypatch.setenv(env_name, env_value)
    with TestClient(app) as client:
        original_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db_session] = _override_get_db_session
        try:
            response = client.get(path)
        finally:
            app.dependency_overrides = original_overrides

    assert response.status_code == 404
    assert response.json()["detail"] == expected_detail
