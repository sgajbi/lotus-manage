import pytest

from src.api.main import app


OPENAPI_PATHS_UNDER_CERTIFICATION = [
    "/api/v1/integration/capabilities",
    "/api/v1/mandates/by-portfolio/{portfolio_id}",
    "/api/v1/mandates/{mandate_id}",
    "/api/v1/mandates/{mandate_id}/versions",
    "/api/v1/mandates/{mandate_id}/diff",
    "/api/v1/mandates/{mandate_id}/refresh-from-core",
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
    "/api/v1/rebalance/supportability/summary",
    "/api/v1/rebalance/workflow/decisions",
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
