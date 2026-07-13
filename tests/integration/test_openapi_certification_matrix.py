import pytest

from src.api.main import app


OPENAPI_PATHS_UNDER_CERTIFICATION = [
    "/api/v1/integration/capabilities",
    "/api/v1/mandates/by-portfolio/{portfolio_id}",
    "/api/v1/mandates/{mandate_id}",
    "/api/v1/mandates/{mandate_id}/versions",
    "/api/v1/mandates/{mandate_id}/diff",
    "/api/v1/mandates/{mandate_id}/refresh-from-core",
    "/api/v1/mandates/{mandate_id}/health",
    "/api/v1/mandates/{mandate_id}/health/recalculate",
    "/api/v1/dpm/monitoring/run-once",
    "/api/v1/dpm/monitoring/runs",
    "/api/v1/dpm/monitoring/runs/{monitoring_run_id}",
    "/api/v1/dpm/command-center",
    "/api/v1/dpm/exceptions",
    "/api/v1/dpm/exceptions/{exception_id}/resolve",
    "/api/v1/rebalance/simulate",
    "/api/v1/rebalance/analyze",
    "/api/v1/rebalance/analyze/async",
    "/api/v1/rebalance/operations",
    "/api/v1/rebalance/operations/{operation_id}",
    "/api/v1/rebalance/operations/by-correlation/{correlation_id}",
    "/api/v1/rebalance/runs",
    "/api/v1/rebalance/runs/{rebalance_run_id}",
    "/api/v1/rebalance/runs/{rebalance_run_id}/artifact",
    "/api/v1/rebalance/runs/{rebalance_run_id}/support-bundle",
    "/api/v1/rebalance/runs/{rebalance_run_id}/workflow",
    "/api/v1/rebalance/runs/{rebalance_run_id}/workflow/actions",
    "/api/v1/rebalance/runs/{rebalance_run_id}/workflow/history",
    "/api/v1/rebalance/runs/by-correlation/{correlation_id}",
    "/api/v1/rebalance/runs/by-correlation/{correlation_id}/support-bundle",
    "/api/v1/rebalance/runs/by-correlation/{correlation_id}/workflow",
    "/api/v1/rebalance/runs/by-correlation/{correlation_id}/workflow/actions",
    "/api/v1/rebalance/runs/by-correlation/{correlation_id}/workflow/history",
    "/api/v1/rebalance/runs/by-operation/{operation_id}/support-bundle",
    "/api/v1/rebalance/runs/idempotency/{idempotency_key}",
    "/api/v1/rebalance/runs/idempotency/{idempotency_key}/support-bundle",
    "/api/v1/rebalance/runs/idempotency/{idempotency_key}/workflow",
    "/api/v1/rebalance/runs/idempotency/{idempotency_key}/workflow/actions",
    "/api/v1/rebalance/runs/idempotency/{idempotency_key}/workflow/history",
    "/api/v1/rebalance/pm-operating-quality/fairness-analyses",
    "/api/v1/rebalance/pm-operating-quality/fairness-analyses/preview",
    "/api/v1/rebalance/pm-operating-quality/fairness-analyses/{fairness_analysis_id}",
    "/api/v1/rebalance/pm-operating-quality/policies",
    "/api/v1/rebalance/pm-operating-quality/policies/{policy_id}/versions/{policy_version}",
    "/api/v1/rebalance/pm-operating-quality/review-actions",
    "/api/v1/rebalance/pm-operating-quality/review-actions/preview",
    "/api/v1/rebalance/pm-operating-quality/review-actions/{review_action_id}",
    "/api/v1/rebalance/pm-operating-quality/score-runs",
    "/api/v1/rebalance/pm-operating-quality/score-runs/preview",
    "/api/v1/rebalance/pm-operating-quality/score-runs/{score_run_id}",
    "/api/v1/rebalance/pm-operating-quality/summary-invocations",
    "/api/v1/rebalance/pm-operating-quality/summary-invocations/preview",
    "/api/v1/rebalance/pm-operating-quality/summary-invocations/{summary_invocation_id}",
    "/api/v1/rebalance/supportability/summary",
    "/api/v1/rebalance/workflow/decisions",
]


PM_QUALITY_OPENAPI_OPERATIONS_UNDER_CERTIFICATION = [
    ("/api/v1/rebalance/pm-operating-quality/fairness-analyses", "get"),
    ("/api/v1/rebalance/pm-operating-quality/fairness-analyses", "post"),
    ("/api/v1/rebalance/pm-operating-quality/fairness-analyses/preview", "post"),
    (
        "/api/v1/rebalance/pm-operating-quality/fairness-analyses/{fairness_analysis_id}",
        "get",
    ),
    ("/api/v1/rebalance/pm-operating-quality/policies", "get"),
    (
        "/api/v1/rebalance/pm-operating-quality/policies/{policy_id}/versions/{policy_version}",
        "get",
    ),
    (
        "/api/v1/rebalance/pm-operating-quality/policies/{policy_id}/versions/{policy_version}",
        "put",
    ),
    ("/api/v1/rebalance/pm-operating-quality/review-actions", "get"),
    ("/api/v1/rebalance/pm-operating-quality/review-actions", "post"),
    ("/api/v1/rebalance/pm-operating-quality/review-actions/preview", "post"),
    ("/api/v1/rebalance/pm-operating-quality/review-actions/{review_action_id}", "get"),
    ("/api/v1/rebalance/pm-operating-quality/score-runs", "get"),
    ("/api/v1/rebalance/pm-operating-quality/score-runs", "post"),
    ("/api/v1/rebalance/pm-operating-quality/score-runs/preview", "post"),
    ("/api/v1/rebalance/pm-operating-quality/score-runs/{score_run_id}", "get"),
    ("/api/v1/rebalance/pm-operating-quality/summary-invocations", "get"),
    ("/api/v1/rebalance/pm-operating-quality/summary-invocations", "post"),
    ("/api/v1/rebalance/pm-operating-quality/summary-invocations/preview", "post"),
    (
        "/api/v1/rebalance/pm-operating-quality/summary-invocations/{summary_invocation_id}",
        "get",
    ),
]


@pytest.mark.parametrize("path", OPENAPI_PATHS_UNDER_CERTIFICATION)
def test_openapi_path_has_certified_operation_documentation(path: str) -> None:
    operation = next(iter(app.openapi()["paths"][path].values()))

    assert operation["summary"]
    assert operation["description"]
    assert operation["tags"]
    assert any(
        str(code).startswith(("4", "5")) or str(code) == "default"
        for code in operation["responses"]
    )


@pytest.mark.parametrize("path", OPENAPI_PATHS_UNDER_CERTIFICATION)
def test_openapi_json_responses_have_examples_for_certified_paths(path: str) -> None:
    for operation in app.openapi()["paths"][path].values():
        for response in operation["responses"].values():
            json_content = response.get("content", {}).get("application/json")
            if json_content is not None:
                assert "example" in json_content or "examples" in json_content


@pytest.mark.parametrize(
    ("path", "method"),
    PM_QUALITY_OPENAPI_OPERATIONS_UNDER_CERTIFICATION,
)
def test_pm_quality_openapi_operation_contract_is_certified(
    path: str,
    method: str,
) -> None:
    operation = app.openapi()["paths"][path][method]

    assert operation["summary"]
    assert all(marker in operation["description"] for marker in ("What:", "When:", "How:"))
    assert operation["tags"] == ["lotus-manage PM Operating Quality"]
    assert operation["operationId"]
    assert set(operation["responses"]) >= {"404", "409", "422", "424", "503"}

    problem_schema = {
        response_code: operation["responses"][response_code]["content"]["application/problem+json"][
            "schema"
        ]["$ref"]
        for response_code in ("404", "409", "422", "424", "503")
    }
    assert set(problem_schema.values()) == {"#/components/schemas/PmQualityProblemDetails"}

    for response in operation["responses"].values():
        for media_type, content in response.get("content", {}).items():
            if media_type in {"application/json", "application/problem+json"}:
                assert "example" in content or "examples" in content
