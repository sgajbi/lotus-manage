import json

import httpx

from scripts.validate_live_api import run_live_api_validation, summarize


def _json_response(status_code: int, body: dict) -> httpx.Response:
    return httpx.Response(status_code, json=body)


def test_live_api_validation_probes_expected_contracts(monkeypatch) -> None:
    monkeypatch.setattr(
        "scripts.validate_live_api._load_demo_payload",
        lambda _filename: {"portfolio_snapshot": {"portfolio_id": "pf_api_live"}},
    )
    async_posts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal async_posts
        path = request.url.path
        if path == "/health/ready":
            return _json_response(200, {"status": "ready"})
        if path == "/api/v1/integration/capabilities":
            return _json_response(
                200,
                {
                    "supported_input_modes": ["inline_bundle"],
                    "features": [
                        {"key": "dpm.execution.stateful_portfolio_id", "enabled": False},
                        {"key": "dpm.execution.stateless_inline_bundle", "enabled": True},
                    ],
                },
            )
        if path == "/openapi.json":
            return _json_response(200, {"paths": {"/api/v1/rebalance/simulate": {}}})
        if path == "/api/v1/rebalance/proposals":
            return _json_response(404, {"detail": "Not Found"})
        if path == "/api/v1/rebalance/analyze/async":
            async_posts += 1
            if async_posts == 1:
                return _json_response(202, {"operation_id": "dop_test"})
            return _json_response(409, {"detail": "DPM_ASYNC_OPERATION_CORRELATION_CONFLICT"})
        if path == "/api/v1/rebalance/supportability/summary":
            return _json_response(
                200,
                {"store_backend": "POSTGRES", "run_count": 1, "operation_count": 1},
            )
        if path == "/metrics":
            return httpx.Response(
                200,
                text='lotus_manage_action_register_supportability_total{surface="summary"} 1',
            )
        raise AssertionError(f"Unexpected request path: {path}")

    results = run_live_api_validation(
        "http://manage.test",
        include_demo_pack=False,
        transport=httpx.MockTransport(handler),
    )
    summary = summarize(results)

    assert summary["failed"] == 0
    assert {result.name for result in results} == {
        "ready",
        "capabilities_truthful_default",
        "openapi_no_advisory_or_proposals",
        "removed_proposal_route_404",
        "async_duplicate_correlation_conflict",
        "supportability_postgres_summary",
        "metrics_exposed_bounded_supportability",
    }


def test_live_api_validation_reports_openapi_boundary_failure(monkeypatch) -> None:
    monkeypatch.setattr(
        "scripts.validate_live_api._load_demo_payload",
        lambda _filename: {"portfolio_snapshot": {"portfolio_id": "pf_api_live"}},
    )

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/health/ready":
            return _json_response(200, {"status": "ready"})
        if path == "/api/v1/integration/capabilities":
            return _json_response(
                200,
                {
                    "supported_input_modes": ["inline_bundle"],
                    "features": [
                        {"key": "dpm.execution.stateful_portfolio_id", "enabled": False},
                        {"key": "dpm.execution.stateless_inline_bundle", "enabled": True},
                    ],
                },
            )
        if path == "/openapi.json":
            return _json_response(200, {"paths": {"/api/v1/rebalance/proposals": {}}})
        if path == "/api/v1/rebalance/proposals":
            return _json_response(404, {"detail": "Not Found"})
        if path == "/api/v1/rebalance/analyze/async":
            return _json_response(409, {"detail": "DPM_ASYNC_OPERATION_CORRELATION_CONFLICT"})
        if path == "/api/v1/rebalance/supportability/summary":
            return _json_response(
                200,
                {"store_backend": "POSTGRES", "run_count": 1, "operation_count": 1},
            )
        if path == "/metrics":
            return httpx.Response(200, text="lotus_manage_action_register_supportability_total 1")
        raise AssertionError(f"Unexpected request path: {path}")

    results = run_live_api_validation(
        "http://manage.test",
        include_demo_pack=False,
        transport=httpx.MockTransport(handler),
    )
    summary = summarize(results)

    assert summary["failed"] >= 1
    failure_names = {failure["name"] for failure in summary["failures"]}
    assert "openapi_no_advisory_or_proposals" in failure_names
    assert json.dumps(summary)
