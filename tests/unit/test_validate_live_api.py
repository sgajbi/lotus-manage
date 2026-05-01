import json

import httpx

from scripts.validate_live_api import run_live_api_validation, summarize


def _json_response(status_code: int, body: dict) -> httpx.Response:
    return httpx.Response(status_code, json=body)


def test_live_api_validation_probes_expected_contracts(monkeypatch) -> None:
    monkeypatch.setattr(
        "scripts.validate_live_api._load_demo_payload",
        lambda _filename: {
            "input_mode": "stateless",
            "stateless_input": {"portfolio_snapshot": {"portfolio_id": "pf_api_live"}},
        },
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
                    "supported_input_modes": ["stateless"],
                    "features": [
                        {"key": "dpm.execution.stateful_portfolio_id", "enabled": False},
                        {"key": "dpm.execution.stateless", "enabled": True},
                    ],
                },
            )
        if path == "/openapi.json":
            return _json_response(
                200,
                {
                    "paths": {
                        "/metrics": {
                            "get": {
                                "responses": {
                                    "200": {
                                        "content": {
                                            "text/plain; version=0.0.4": {
                                                "schema": {"type": "string"},
                                                "examples": {"prometheus": {"value": "metric 1"}},
                                            }
                                        }
                                    }
                                }
                            }
                        },
                        "/api/v1/rebalance/simulate": {
                            "post": {
                                "requestBody": {
                                    "content": {
                                        "application/json": {
                                            "schema": {"type": "object"},
                                            "examples": {"default": {"value": {}}},
                                        }
                                    }
                                },
                                "responses": {
                                    "200": {
                                        "content": {
                                            "application/json": {
                                                "schema": {"type": "object"},
                                                "examples": {"default": {"value": {}}},
                                            }
                                        }
                                    }
                                },
                            }
                        },
                    }
                },
            )
        if path == "/api/v1/rebalance/proposals":
            return _json_response(404, {"detail": "Not Found"})
        if path == "/api/v1/rebalance/simulate":
            return _json_response(409, {"detail": "DPM_STATEFUL_INPUT_DISABLED"})
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
        "openapi_certification_contract",
        "removed_proposal_route_404",
        "stateful_core_sourcing_guard",
        "async_duplicate_correlation_conflict",
        "supportability_postgres_summary",
        "metrics_exposed_bounded_supportability",
    }


def test_live_api_validation_reports_openapi_boundary_failure(monkeypatch) -> None:
    monkeypatch.setattr(
        "scripts.validate_live_api._load_demo_payload",
        lambda _filename: {
            "input_mode": "stateless",
            "stateless_input": {"portfolio_snapshot": {"portfolio_id": "pf_api_live"}},
        },
    )

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/health/ready":
            return _json_response(200, {"status": "ready"})
        if path == "/api/v1/integration/capabilities":
            return _json_response(
                200,
                {
                    "supported_input_modes": ["stateless"],
                    "features": [
                        {"key": "dpm.execution.stateful_portfolio_id", "enabled": False},
                        {"key": "dpm.execution.stateless", "enabled": True},
                    ],
                },
            )
        if path == "/openapi.json":
            return _json_response(
                200,
                {
                    "paths": {
                        "/metrics": {
                            "get": {
                                "responses": {
                                    "200": {
                                        "content": {
                                            "text/plain; version=0.0.4": {
                                                "schema": {"type": "string"},
                                                "examples": {"prometheus": {"value": "metric 1"}},
                                            }
                                        }
                                    }
                                }
                            }
                        },
                        "/api/v1/rebalance/proposals": {},
                    }
                },
            )
        if path == "/api/v1/rebalance/proposals":
            return _json_response(404, {"detail": "Not Found"})
        if path == "/api/v1/rebalance/simulate":
            return _json_response(409, {"detail": "DPM_STATEFUL_INPUT_DISABLED"})
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


def test_live_api_validation_reports_stale_openapi_certification_contract(monkeypatch) -> None:
    monkeypatch.setattr(
        "scripts.validate_live_api._load_demo_payload",
        lambda _filename: {
            "input_mode": "stateless",
            "stateless_input": {"portfolio_snapshot": {"portfolio_id": "pf_api_live"}},
        },
    )

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/health/ready":
            return _json_response(200, {"status": "ready"})
        if path == "/api/v1/integration/capabilities":
            return _json_response(
                200,
                {
                    "supported_input_modes": ["stateless"],
                    "features": [
                        {"key": "dpm.execution.stateful_portfolio_id", "enabled": False},
                        {"key": "dpm.execution.stateless", "enabled": True},
                    ],
                },
            )
        if path == "/openapi.json":
            return _json_response(
                200,
                {
                    "paths": {
                        "/metrics": {
                            "get": {
                                "responses": {
                                    "200": {"content": {"application/json": {"schema": {}}}}
                                }
                            }
                        },
                        "/api/v1/rebalance/simulate": {
                            "post": {
                                "requestBody": {
                                    "content": {"application/json": {"schema": {"type": "object"}}}
                                },
                                "responses": {
                                    "200": {
                                        "content": {
                                            "application/json": {"schema": {"type": "object"}}
                                        }
                                    }
                                },
                            }
                        },
                    }
                },
            )
        if path == "/api/v1/rebalance/proposals":
            return _json_response(404, {"detail": "Not Found"})
        if path == "/api/v1/rebalance/simulate":
            return _json_response(409, {"detail": "DPM_STATEFUL_INPUT_DISABLED"})
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

    failure_names = {failure["name"] for failure in summary["failures"]}
    assert "openapi_certification_contract" in failure_names
    failure = next(
        failure
        for failure in summary["failures"]
        if failure["name"] == "openapi_certification_contract"
    )
    assert failure["details"]["missing_example_count"] == 3
    assert failure["details"]["metrics_media_types"] == ["application/json"]


def test_live_api_validation_reports_missing_error_response_examples(monkeypatch) -> None:
    monkeypatch.setattr(
        "scripts.validate_live_api._load_demo_payload",
        lambda _filename: {
            "input_mode": "stateless",
            "stateless_input": {"portfolio_snapshot": {"portfolio_id": "pf_api_live"}},
        },
    )

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/health/ready":
            return _json_response(200, {"status": "ready"})
        if path == "/api/v1/integration/capabilities":
            return _json_response(
                200,
                {
                    "supported_input_modes": ["stateless"],
                    "features": [
                        {"key": "dpm.execution.stateful_portfolio_id", "enabled": False},
                        {"key": "dpm.execution.stateless", "enabled": True},
                    ],
                },
            )
        if path == "/openapi.json":
            return _json_response(
                200,
                {
                    "paths": {
                        "/metrics": {
                            "get": {
                                "responses": {
                                    "200": {
                                        "content": {
                                            "text/plain; version=0.0.4": {
                                                "schema": {"type": "string"},
                                                "examples": {"prometheus": {"value": "metric 1"}},
                                            }
                                        }
                                    }
                                }
                            }
                        },
                        "/api/v1/rebalance/simulate": {
                            "post": {
                                "requestBody": {
                                    "content": {
                                        "application/json": {
                                            "schema": {"type": "object"},
                                            "examples": {"default": {"value": {}}},
                                        }
                                    }
                                },
                                "responses": {
                                    "200": {
                                        "content": {
                                            "application/json": {
                                                "schema": {"type": "object"},
                                                "examples": {"default": {"value": {}}},
                                            }
                                        }
                                    },
                                    "409": {"description": "Conflict."},
                                },
                            }
                        },
                    }
                },
            )
        if path == "/api/v1/rebalance/proposals":
            return _json_response(404, {"detail": "Not Found"})
        if path == "/api/v1/rebalance/simulate":
            return _json_response(409, {"detail": "DPM_STATEFUL_INPUT_DISABLED"})
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

    failure = next(
        failure
        for failure in summary["failures"]
        if failure["name"] == "openapi_certification_contract"
    )
    assert (
        "POST /api/v1/rebalance/simulate 409 error response JSON content"
        in (failure["details"]["missing_examples"])
    )


def test_live_api_validation_can_probe_current_core_route_absence(monkeypatch) -> None:
    monkeypatch.setattr(
        "scripts.validate_live_api._load_demo_payload",
        lambda _filename: {
            "input_mode": "stateless",
            "stateless_input": {"portfolio_snapshot": {"portfolio_id": "pf_api_live"}},
        },
    )

    async_posts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal async_posts
        path = request.url.path
        if request.url.host == "core.test":
            if path == "/integration/portfolios/PB_SG_GLOBAL_BAL_001/dpm-execution-context":
                return _json_response(404, {"detail": "Not Found"})
            raise AssertionError(f"Unexpected core request path: {path}")
        if path == "/health/ready":
            return _json_response(200, {"status": "ready"})
        if path == "/api/v1/integration/capabilities":
            return _json_response(
                200,
                {
                    "supported_input_modes": ["stateless"],
                    "features": [
                        {"key": "dpm.execution.stateful_portfolio_id", "enabled": False},
                        {"key": "dpm.execution.stateless", "enabled": True},
                    ],
                },
            )
        if path == "/openapi.json":
            return _json_response(
                200,
                {
                    "paths": {
                        "/metrics": {
                            "get": {
                                "responses": {
                                    "200": {
                                        "content": {
                                            "text/plain; version=0.0.4": {
                                                "schema": {"type": "string"},
                                                "examples": {"prometheus": {"value": "metric 1"}},
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                },
            )
        if path == "/api/v1/rebalance/proposals":
            return _json_response(404, {"detail": "Not Found"})
        if path == "/api/v1/rebalance/simulate":
            return _json_response(409, {"detail": "DPM_STATEFUL_INPUT_DISABLED"})
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
            return httpx.Response(200, text="lotus_manage_action_register_supportability_total 1")
        raise AssertionError(f"Unexpected manage request path: {path}")

    results = run_live_api_validation(
        "http://manage.test",
        include_demo_pack=False,
        core_base_urls=["http://core.test"],
        expect_core_dpm_route="absent",
        transport=httpx.MockTransport(handler),
    )
    summary = summarize(results)

    assert summary["failed"] == 0
    core_probe = next(
        result for result in results if result.name == "core_dpm_execution_context_route"
    )
    assert core_probe.details["core_base_url"] == "http://core.test"
    assert core_probe.details["expectation"] == "absent"
    assert core_probe.details["status_code"] == 404


def test_live_api_validation_fails_when_core_route_posture_changes_unexpectedly(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "scripts.validate_live_api._load_demo_payload",
        lambda _filename: {
            "input_mode": "stateless",
            "stateless_input": {"portfolio_snapshot": {"portfolio_id": "pf_api_live"}},
        },
    )

    async_posts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal async_posts
        if request.url.host == "core.test":
            return _json_response(200, {"source_lineage": {"source_system": "lotus-core"}})
        path = request.url.path
        if path == "/health/ready":
            return _json_response(200, {"status": "ready"})
        if path == "/api/v1/integration/capabilities":
            return _json_response(
                200,
                {
                    "supported_input_modes": ["stateless"],
                    "features": [
                        {"key": "dpm.execution.stateful_portfolio_id", "enabled": False},
                        {"key": "dpm.execution.stateless", "enabled": True},
                    ],
                },
            )
        if path == "/openapi.json":
            return _json_response(
                200,
                {
                    "paths": {
                        "/metrics": {
                            "get": {
                                "responses": {
                                    "200": {
                                        "content": {
                                            "text/plain; version=0.0.4": {
                                                "schema": {"type": "string"},
                                                "examples": {"prometheus": {"value": "metric 1"}},
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                },
            )
        if path == "/api/v1/rebalance/proposals":
            return _json_response(404, {"detail": "Not Found"})
        if path == "/api/v1/rebalance/simulate":
            return _json_response(409, {"detail": "DPM_STATEFUL_INPUT_DISABLED"})
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
            return httpx.Response(200, text="lotus_manage_action_register_supportability_total 1")
        raise AssertionError(f"Unexpected manage request path: {path}")

    results = run_live_api_validation(
        "http://manage.test",
        include_demo_pack=False,
        core_base_urls=["http://core.test"],
        expect_core_dpm_route="absent",
        transport=httpx.MockTransport(handler),
    )
    summary = summarize(results)

    failure_names = {failure["name"] for failure in summary["failures"]}
    assert "core_dpm_execution_context_route" in failure_names
