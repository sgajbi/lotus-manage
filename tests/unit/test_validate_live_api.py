import json

import httpx

from scripts.validate_live_api import run_live_api_validation, summarize


def _json_response(status_code: int, body: dict) -> httpx.Response:
    return httpx.Response(status_code, json=body)


def _construction_alternative_set() -> dict:
    return {
        "alternative_set_id": "cas_live_test",
        "alternatives": [
            {
                "alternative_id": "alt_do_nothing_baseline",
                "method": "DO_NOTHING_BASELINE",
                "method_status": "READY",
                "comparison_metrics": {
                    "drift_after": "1.0000",
                    "turnover_weight": "0.0000",
                    "trade_count": 0,
                },
            },
            {
                "alternative_id": "alt_heuristic_explainable",
                "method": "HEURISTIC_EXPLAINABLE",
                "method_status": "READY",
                "comparison_metrics": {
                    "drift_after": "0.0000",
                    "turnover_weight": "1.0000",
                    "trade_count": 2,
                },
            },
            {
                "alternative_id": "alt_min_turnover",
                "method": "MIN_TURNOVER",
                "method_status": "PENDING_REVIEW",
                "comparison_metrics": {
                    "drift_after": "1.0000",
                    "turnover_weight": "0.0000",
                    "trade_count": 0,
                },
            },
            {
                "alternative_id": "alt_tax_aware",
                "method": "TAX_AWARE",
                "method_status": "READY",
                "comparison_metrics": {
                    "drift_after": "0.0000",
                    "turnover_weight": "1.0000",
                    "trade_count": 2,
                },
            },
        ],
    }


def _construction_second_wave_alternative_set() -> dict:
    methods = [
        "SOLVER_CONSTRAINED",
        "LIQUIDITY_AWARE",
        "RISK_AWARE",
        "ESG_AWARE",
        "CURRENCY_OVERLAY",
        "REGIME_STRESS_AWARE",
    ]
    reason_codes = {
        "SOLVER_CONSTRAINED": ["TARGET_METHOD_COMPARISON_AVAILABLE"],
        "LIQUIDITY_AWARE": ["SETTLEMENT_AWARENESS_ENABLED"],
        "RISK_AWARE": ["RISK_AUTHORITY_NOT_CONNECTED"],
        "ESG_AWARE": ["ESG_PROFILE_SOURCE_PRESENT"],
        "CURRENCY_OVERLAY": ["CURRENCY_OVERLAY_FX_SOURCE_READY"],
        "REGIME_STRESS_AWARE": ["REGIME_SCENARIO_PACK_UNAVAILABLE"],
    }
    return {
        "alternative_set_id": "cas_live_test_second_wave",
        "alternatives": [
            {
                "alternative_id": f"alt_{method.lower()}",
                "method": method,
                "method_status": "READY" if method != "REGIME_STRESS_AWARE" else "DEGRADED",
                "comparison_metrics": {
                    "drift_after": "0.0000",
                    "turnover_weight": "1.0000",
                    "trade_count": 2,
                },
                "diagnostics": {"enrichment_summary": {"reason_codes": reason_codes[method]}},
            }
            for method in methods
        ],
    }


def _construction_response(request: httpx.Request) -> httpx.Response | None:
    path = request.url.path
    if path == "/api/v1/construction/alternative-sets/generate":
        body = json.loads(request.content.decode("utf-8")) if request.content else {}
        if "SOLVER_CONSTRAINED" in body.get("methods", []):
            return _json_response(200, _construction_second_wave_alternative_set())
        return _json_response(200, _construction_alternative_set())
    if path == "/api/v1/construction/alternative-sets/cas_live_test":
        return _json_response(200, _construction_alternative_set())
    if path == "/api/v1/construction/alternative-sets/cas_live_test/selections":
        return _json_response(
            200,
            {
                "selection_id": "casel_live_test",
                "alternative_set_id": "cas_live_test",
                "alternative_id": "alt_heuristic_explainable",
                "actor_id": "live_validator",
                "reason_code": "MAX_DRIFT_REDUCTION_ACCEPTABLE_TURNOVER",
            },
        )
    return None


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
        construction = _construction_response(request)
        if construction is not None:
            return construction
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
        "capabilities_truthful_disabled",
        "openapi_no_advisory_or_proposals",
        "openapi_certification_contract",
        "removed_proposal_route_404",
        "stateful_core_sourcing_guard",
        "construction_alternatives_first_wave",
        "construction_alternatives_second_wave",
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
        construction = _construction_response(request)
        if construction is not None:
            return construction
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
        construction = _construction_response(request)
        if construction is not None:
            return construction
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
        construction = _construction_response(request)
        if construction is not None:
            return construction
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
        construction = _construction_response(request)
        if construction is not None:
            return construction
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


def test_live_api_validation_can_probe_available_stateful_core_sourcing(monkeypatch) -> None:
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
        construction = _construction_response(request)
        if construction is not None:
            return construction
        if path == "/health/ready":
            return _json_response(200, {"status": "ready"})
        if path == "/api/v1/integration/capabilities":
            return _json_response(
                200,
                {
                    "supported_input_modes": ["stateful", "stateless"],
                    "features": [
                        {"key": "dpm.execution.stateful_portfolio_id", "enabled": True},
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
            request_body = json.loads(request.content.decode())
            assert request_body["stateful_input"]["portfolio_id"] == "PB_SG_GLOBAL_BAL_001"
            assert request_body["stateful_input"]["model_portfolio_id"] == (
                "MODEL_PB_SG_GLOBAL_BAL_DPM"
            )
            return _json_response(
                200,
                {
                    "lineage": {
                        "input_mode": "stateful",
                        "source_system": "lotus-core",
                        "source_supportability_state": "READY",
                        "model_portfolio_id": "MODEL_PB_SG_GLOBAL_BAL_DPM",
                        "model_portfolio_version": "2026.04",
                        "shelf_version": "rfc_087_v1",
                        "integration_policy_version": "rfc_087_v1",
                        "source_lineage_bundle_id": "rfc-087:PB_SG_GLOBAL_BAL_001:2026-04-10",
                        "stateful_context_hash": "hash_123",
                    }
                },
            )
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
        raise AssertionError(f"Unexpected request path: {path}")

    results = run_live_api_validation(
        "http://manage.test",
        include_demo_pack=False,
        expect_stateful_core_sourcing="available",
        transport=httpx.MockTransport(handler),
    )
    summary = summarize(results)

    assert summary["failed"] == 0
    stateful_probe = next(
        result for result in results if result.name == "stateful_core_sourcing_available"
    )
    assert stateful_probe.details["lineage"]["source_supportability_state"] == "READY"
    assert stateful_probe.details["lineage"]["stateful_context_hash_present"] is True


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
        construction = _construction_response(request)
        if construction is not None:
            return construction
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


def test_live_api_validation_records_demo_connectivity_failure(monkeypatch) -> None:
    def fail_demo_pack(_base_url: str) -> None:
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr("scripts.validate_live_api.run_demo_pack", fail_demo_pack)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/health/ready":
            return _json_response(503, {"status": "unavailable"})
        return _json_response(404, {"detail": "not found"})

    results = run_live_api_validation(
        "http://manage.test",
        include_demo_pack=True,
        transport=httpx.MockTransport(handler),
    )
    summary = summarize(results)

    failures = {failure["name"]: failure for failure in summary["failures"]}
    assert failures["demo_pack"]["details"]["error"] == "connection refused"
    assert "ready" in failures
