import argparse
import json
import sys
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Literal, cast

import httpx

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_demo_pack_live import DEMO_DIR, DemoRunError, run_demo_pack  # noqa: E402


@dataclass(frozen=True)
class ProbeResult:
    name: str
    ok: bool
    details: dict[str, Any]


def _feature_flags(body: dict[str, Any]) -> dict[str, bool]:
    return {
        str(item.get("key")): bool(item.get("enabled"))
        for item in body.get("features", [])
        if isinstance(item, dict) and item.get("key")
    }


def _result(name: str, ok: bool, details: dict[str, Any]) -> ProbeResult:
    return ProbeResult(name=name, ok=ok, details=details)


def _load_demo_payload(filename: str) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads((DEMO_DIR / filename).read_text(encoding="utf-8")))


def _probe_ready(client: httpx.Client) -> ProbeResult:
    response = client.get("/health/ready")
    body = response.json() if response.content else {}
    return _result(
        "ready",
        response.status_code == 200 and body.get("status") == "ready",
        {"status_code": response.status_code, "body": body},
    )


StatefulSourcingExpectation = Literal["disabled", "available"]


def _probe_capabilities(
    client: httpx.Client,
    *,
    stateful_expectation: StatefulSourcingExpectation,
) -> ProbeResult:
    response = client.get(
        "/api/v1/integration/capabilities",
        params={"consumer_system": "lotus-gateway", "tenant_id": "default"},
    )
    body = response.json()
    features = _feature_flags(body)
    expected_modes = (
        ["stateful", "stateless"] if stateful_expectation == "available" else ["stateless"]
    )
    expected_stateful_enabled = stateful_expectation == "available"
    return _result(
        f"capabilities_truthful_{stateful_expectation}",
        response.status_code == 200
        and body.get("supported_input_modes") == expected_modes
        and features.get("dpm.execution.stateful_portfolio_id") is expected_stateful_enabled
        and features.get("dpm.execution.stateless") is True,
        {
            "status_code": response.status_code,
            "supported_input_modes": body.get("supported_input_modes"),
            "features": features,
        },
    )


def _probe_openapi_boundary(client: httpx.Client) -> ProbeResult:
    response = client.get("/openapi.json")
    body = response.json()
    matching_paths = [
        path
        for path in body.get("paths", {})
        if "proposal" in path.lower() or "advis" in path.lower()
    ]
    return _result(
        "openapi_no_advisory_or_proposals",
        response.status_code == 200 and matching_paths == [],
        {"status_code": response.status_code, "matching_paths": matching_paths},
    )


def _content_has_example(content: dict[str, Any]) -> bool:
    return bool(content.get("example") or content.get("examples"))


def _is_error_status(status_code: object) -> bool:
    normalized = str(status_code)
    return normalized.startswith(("4", "5")) or normalized == "default"


def _probe_openapi_certification_contract(client: httpx.Client) -> ProbeResult:
    response = client.get("/openapi.json")
    body = response.json()
    missing_examples: list[str] = []
    for path, operations in sorted(body.get("paths", {}).items()):
        for method, operation in sorted(operations.items()):
            if method not in {"get", "post", "put", "patch", "delete"}:
                continue
            request_content = (
                operation.get("requestBody", {}).get("content", {}).get("application/json")
            )
            if isinstance(request_content, dict) and not _content_has_example(request_content):
                missing_examples.append(f"{method.upper()} {path} request")

            for status_code, route_response in sorted(operation.get("responses", {}).items()):
                response_content = route_response.get("content", {}).get("application/json")
                if _is_error_status(status_code) and not isinstance(response_content, dict):
                    missing_examples.append(
                        f"{method.upper()} {path} {status_code} error response JSON content"
                    )
                if isinstance(response_content, dict) and not _content_has_example(
                    response_content
                ):
                    missing_examples.append(f"{method.upper()} {path} {status_code} response")

    metrics_content = (
        body.get("paths", {})
        .get("/metrics", {})
        .get("get", {})
        .get("responses", {})
        .get("200", {})
        .get("content", {})
    )
    metrics_media_types = sorted(metrics_content)
    metrics_is_prometheus = (
        "text/plain; version=0.0.4" in metrics_content and "application/json" not in metrics_content
    )

    return _result(
        "openapi_certification_contract",
        response.status_code == 200 and missing_examples == [] and metrics_is_prometheus,
        {
            "status_code": response.status_code,
            "missing_examples": missing_examples[:20],
            "missing_example_count": len(missing_examples),
            "metrics_media_types": metrics_media_types,
        },
    )


def _probe_removed_proposal_route(client: httpx.Client) -> ProbeResult:
    response = client.get("/api/v1/rebalance/proposals")
    return _result(
        "removed_proposal_route_404",
        response.status_code == 404,
        {"status_code": response.status_code, "body": response.text[:200]},
    )


def _probe_stateful_core_sourcing_guard(client: httpx.Client) -> ProbeResult:
    response = client.post(
        "/api/v1/rebalance/simulate",
        json=_stateful_simulate_payload(),
        headers={"Idempotency-Key": f"live-stateful-disabled-{uuid.uuid4().hex[:10]}"},
    )
    body = response.json() if response.content else {}
    return _result(
        "stateful_core_sourcing_guard",
        response.status_code == 409 and body.get("detail") == "DPM_STATEFUL_INPUT_DISABLED",
        {
            "status_code": response.status_code,
            "body": body,
        },
    )


def _probe_stateful_core_sourcing_available(
    client: httpx.Client,
    *,
    portfolio_id: str,
    as_of: str,
) -> ProbeResult:
    response = client.post(
        "/api/v1/rebalance/simulate",
        json=_stateful_simulate_payload(portfolio_id=portfolio_id, as_of=as_of),
        headers={
            "Idempotency-Key": f"live-stateful-available-{uuid.uuid4().hex[:10]}",
            "X-Correlation-Id": f"corr-live-stateful-available-{uuid.uuid4().hex[:10]}",
        },
    )
    body = response.json() if response.content else {}
    lineage = body.get("lineage") if isinstance(body, dict) else None
    lineage = lineage if isinstance(lineage, dict) else {}
    return _result(
        "stateful_core_sourcing_available",
        response.status_code == 200
        and lineage.get("input_mode") == "stateful"
        and lineage.get("source_system") == "lotus-core"
        and lineage.get("source_supportability_state") == "READY"
        and bool(lineage.get("stateful_context_hash"))
        and lineage.get("model_portfolio_id") == "MODEL_PB_SG_GLOBAL_BAL_DPM",
        {
            "status_code": response.status_code,
            "lineage": {
                "input_mode": lineage.get("input_mode"),
                "source_system": lineage.get("source_system"),
                "source_supportability_state": lineage.get("source_supportability_state"),
                "model_portfolio_id": lineage.get("model_portfolio_id"),
                "model_portfolio_version": lineage.get("model_portfolio_version"),
                "shelf_version": lineage.get("shelf_version"),
                "integration_policy_version": lineage.get("integration_policy_version"),
                "source_lineage_bundle_id": lineage.get("source_lineage_bundle_id"),
                "stateful_context_hash_present": bool(lineage.get("stateful_context_hash")),
            },
            "detail": body.get("detail") if isinstance(body, dict) else None,
        },
    )


def _construction_alternatives_payload(*, portfolio_id: str) -> dict[str, Any]:
    return {
        "input_mode": "stateless",
        "stateless_input": {
            "portfolio_snapshot": {
                "portfolio_id": portfolio_id,
                "base_currency": "SGD",
                "positions": [{"instrument_id": "EQ_1", "quantity": "100"}],
                "cash_balances": [{"currency": "SGD", "amount": "0.00"}],
            },
            "market_data_snapshot": {
                "prices": [
                    {"instrument_id": "EQ_1", "price": "100.00", "currency": "SGD"},
                    {"instrument_id": "EQ_2", "price": "100.00", "currency": "SGD"},
                ],
                "fx_rates": [],
            },
            "model_portfolio": {
                "targets": [
                    {"instrument_id": "EQ_1", "weight": "0.50"},
                    {"instrument_id": "EQ_2", "weight": "0.50"},
                ]
            },
            "shelf_entries": [
                {"instrument_id": "EQ_1", "status": "APPROVED"},
                {"instrument_id": "EQ_2", "status": "APPROVED"},
            ],
            "options": {},
        },
    }


def _probe_construction_alternatives(
    client: httpx.Client,
    *,
    portfolio_id: str,
) -> ProbeResult:
    response = client.post(
        "/api/v1/construction/alternative-sets/generate",
        json=_construction_alternatives_payload(portfolio_id=portfolio_id),
        headers={
            "Idempotency-Key": f"live-construction-{uuid.uuid4().hex[:10]}",
            "X-Correlation-Id": f"corr-live-construction-{uuid.uuid4().hex[:10]}",
        },
    )
    body = response.json() if response.content else {}
    alternatives = body.get("alternatives") if isinstance(body, dict) else []
    alternatives = alternatives if isinstance(alternatives, list) else []
    by_method = {
        alternative.get("method"): alternative
        for alternative in alternatives
        if isinstance(alternative, dict)
    }
    alternative_set_id = body.get("alternative_set_id") if isinstance(body, dict) else None
    read_status = None
    selection_status = None
    if isinstance(alternative_set_id, str) and alternative_set_id:
        read_status = client.get(
            f"/api/v1/construction/alternative-sets/{alternative_set_id}"
        ).status_code
        selection_status = client.post(
            f"/api/v1/construction/alternative-sets/{alternative_set_id}/selections",
            json={
                "alternative_id": "alt_heuristic_explainable",
                "actor_id": "live_validator",
                "reason_code": "MAX_DRIFT_REDUCTION_ACCEPTABLE_TURNOVER",
                "comment": "Live validator selected the heuristic alternative for proof.",
            },
            headers={"X-Correlation-Id": f"corr-live-selection-{uuid.uuid4().hex[:10]}"},
        ).status_code
    baseline = by_method.get("DO_NOTHING_BASELINE", {})
    heuristic = by_method.get("HEURISTIC_EXPLAINABLE", {})
    min_turnover = by_method.get("MIN_TURNOVER", {})
    baseline_metrics = baseline.get("comparison_metrics", {})
    heuristic_metrics = heuristic.get("comparison_metrics", {})
    min_turnover_metrics = min_turnover.get("comparison_metrics", {})
    expected_methods = {
        "DO_NOTHING_BASELINE",
        "HEURISTIC_EXPLAINABLE",
        "MIN_TURNOVER",
        "TAX_AWARE",
    }
    ok = (
        response.status_code == 200
        and set(by_method) == expected_methods
        and read_status == 200
        and selection_status == 200
        and baseline_metrics.get("trade_count") == 0
        and str(baseline_metrics.get("drift_after")) == "1.0000"
        and int(heuristic_metrics.get("trade_count", -1)) > 0
        and str(heuristic_metrics.get("drift_after")) == "0.0000"
        and min_turnover.get("method_status") == "PENDING_REVIEW"
        and str(min_turnover_metrics.get("turnover_weight")) == "0.0000"
    )
    return _result(
        "construction_alternatives_first_wave",
        ok,
        {
            "status_code": response.status_code,
            "alternative_set_id": alternative_set_id,
            "read_status": read_status,
            "selection_status": selection_status,
            "methods": sorted(by_method),
            "baseline": {
                "status": baseline.get("method_status"),
                "drift_after": baseline_metrics.get("drift_after"),
                "turnover_weight": baseline_metrics.get("turnover_weight"),
                "trade_count": baseline_metrics.get("trade_count"),
            },
            "heuristic": {
                "status": heuristic.get("method_status"),
                "drift_after": heuristic_metrics.get("drift_after"),
                "turnover_weight": heuristic_metrics.get("turnover_weight"),
                "trade_count": heuristic_metrics.get("trade_count"),
            },
            "min_turnover": {
                "status": min_turnover.get("method_status"),
                "drift_after": min_turnover_metrics.get("drift_after"),
                "turnover_weight": min_turnover_metrics.get("turnover_weight"),
                "trade_count": min_turnover_metrics.get("trade_count"),
            },
        },
    )


def _stateful_selector_payload(
    *,
    portfolio_id: str = "PB_SG_GLOBAL_BAL_001",
    as_of: str = "2026-04-10",
) -> dict[str, str]:
    return {
        "portfolio_id": portfolio_id,
        "as_of": as_of,
        "mandate_id": "MANDATE_PB_SG_GLOBAL_BAL_001",
        "model_portfolio_id": "MODEL_PB_SG_GLOBAL_BAL_DPM",
        "tenant_id": "default",
        "booking_center_code": "Singapore",
    }


def _stateful_simulate_payload(
    *,
    portfolio_id: str = "PB_SG_GLOBAL_BAL_001",
    as_of: str = "2026-04-10",
) -> dict[str, Any]:
    return {
        "input_mode": "stateful",
        "stateful_input": _stateful_selector_payload(portfolio_id=portfolio_id, as_of=as_of),
        "options_override": {
            "enable_settlement_awareness": True,
            "enable_tax_awareness": True,
        },
    }


def _probe_core_dpm_execution_context_route(
    client: httpx.Client,
    *,
    core_base_url: str,
    portfolio_id: str,
    as_of: str,
    expectation: Literal["absent", "available"],
) -> ProbeResult:
    response = client.post(
        f"/integration/portfolios/{portfolio_id}/dpm-execution-context",
        json=_stateful_selector_payload(portfolio_id=portfolio_id, as_of=as_of),
    )
    body: Any
    try:
        body = response.json() if response.content else {}
    except ValueError:
        body = response.text[:500]

    if expectation == "absent":
        ok = response.status_code == 404
    else:
        ok = response.status_code == 200 and isinstance(body, dict) and "source_lineage" in body

    return _result(
        "core_dpm_execution_context_route",
        ok,
        {
            "core_base_url": core_base_url,
            "expectation": expectation,
            "status_code": response.status_code,
            "body": body,
        },
    )


def _probe_async_duplicate_correlation(client: httpx.Client) -> ProbeResult:
    payload = _load_demo_payload("26_dpm_async_batch_analysis.json")
    correlation_id = f"live-dup-{uuid.uuid4().hex[:10]}"
    headers = {"X-Correlation-Id": correlation_id}
    first = client.post("/api/v1/rebalance/analyze/async", json=payload, headers=headers)
    second = client.post("/api/v1/rebalance/analyze/async", json=payload, headers=headers)
    second_body = second.json() if second.content else {}
    return _result(
        "async_duplicate_correlation_conflict",
        first.status_code == 202
        and second.status_code == 409
        and second_body.get("detail") == "DPM_ASYNC_OPERATION_CORRELATION_CONFLICT",
        {
            "first_status": first.status_code,
            "second_status": second.status_code,
            "second_body": second_body,
        },
    )


def _probe_supportability_summary(client: httpx.Client) -> ProbeResult:
    response = client.get("/api/v1/rebalance/supportability/summary")
    body = response.json()
    return _result(
        "supportability_postgres_summary",
        response.status_code == 200
        and body.get("store_backend") == "POSTGRES"
        and body.get("run_count", 0) > 0,
        {
            "status_code": response.status_code,
            "store_backend": body.get("store_backend"),
            "run_count": body.get("run_count"),
            "operation_count": body.get("operation_count"),
        },
    )


def _probe_metrics(client: httpx.Client) -> ProbeResult:
    response = client.get("/metrics")
    has_action_register_metric = (
        "lotus_manage_action_register_supportability_total" in response.text
    )
    return _result(
        "metrics_exposed_bounded_supportability",
        response.status_code == 200 and has_action_register_metric,
        {
            "status_code": response.status_code,
            "has_action_register_metric": has_action_register_metric,
        },
    )


def run_live_api_validation(
    base_url: str,
    *,
    include_demo_pack: bool = True,
    core_base_urls: list[str] | None = None,
    expect_core_dpm_route: Literal["absent", "available"] = "absent",
    expect_stateful_core_sourcing: StatefulSourcingExpectation = "disabled",
    portfolio_id: str = "PB_SG_GLOBAL_BAL_001",
    as_of: str = "2026-04-10",
    transport: httpx.BaseTransport | None = None,
) -> list[ProbeResult]:
    results: list[ProbeResult] = []
    timeout = httpx.Timeout(30.0)

    if include_demo_pack:
        try:
            run_demo_pack(base_url)
            results.append(_result("demo_pack", True, {"base_url": base_url}))
        except (DemoRunError, httpx.HTTPError) as exc:
            results.append(_result("demo_pack", False, {"error": str(exc)}))

    with httpx.Client(base_url=base_url, timeout=timeout, transport=transport) as client:
        probe_calls: list[tuple[str, Callable[[], ProbeResult]]] = [
            ("ready", lambda: _probe_ready(client)),
            (
                f"capabilities_truthful_{expect_stateful_core_sourcing}",
                lambda: _probe_capabilities(
                    client,
                    stateful_expectation=expect_stateful_core_sourcing,
                ),
            ),
            ("openapi_no_advisory_or_proposals", lambda: _probe_openapi_boundary(client)),
            (
                "openapi_certification_contract",
                lambda: _probe_openapi_certification_contract(client),
            ),
            ("removed_proposal_route_404", lambda: _probe_removed_proposal_route(client)),
        ]
        if expect_stateful_core_sourcing == "available":
            probe_calls.append(
                (
                    "stateful_core_sourcing_available",
                    lambda: _probe_stateful_core_sourcing_available(
                        client,
                        portfolio_id=portfolio_id,
                        as_of=as_of,
                    ),
                )
            )
        else:
            probe_calls.append(
                (
                    "stateful_core_sourcing_guard",
                    lambda: _probe_stateful_core_sourcing_guard(client),
                )
            )
        probe_calls.append(
            (
                "construction_alternatives_first_wave",
                lambda: _probe_construction_alternatives(
                    client,
                    portfolio_id=portfolio_id,
                ),
            )
        )
        probe_calls.extend(
            [
                (
                    "async_duplicate_correlation_conflict",
                    lambda: _probe_async_duplicate_correlation(client),
                ),
                ("supportability_postgres_summary", lambda: _probe_supportability_summary(client)),
                ("metrics_exposed_bounded_supportability", lambda: _probe_metrics(client)),
            ]
        )
        for probe_name, probe in probe_calls:
            try:
                results.append(probe())
            except (httpx.HTTPError, ValueError, KeyError, TypeError, AssertionError) as exc:
                results.append(_result(probe_name, False, {"error": str(exc)}))

    for core_base_url in core_base_urls or []:
        with httpx.Client(base_url=core_base_url, timeout=timeout, transport=transport) as client:
            try:
                results.append(
                    _probe_core_dpm_execution_context_route(
                        client,
                        core_base_url=core_base_url,
                        portfolio_id=portfolio_id,
                        as_of=as_of,
                        expectation=expect_core_dpm_route,
                    )
                )
            except (httpx.HTTPError, ValueError, KeyError, TypeError, AssertionError) as exc:
                results.append(
                    _result(
                        "core_dpm_execution_context_route",
                        False,
                        {
                            "core_base_url": core_base_url,
                            "expectation": expect_core_dpm_route,
                            "error": str(exc),
                        },
                    )
                )

    return results


def summarize(results: list[ProbeResult]) -> dict[str, Any]:
    failures = [asdict(result) for result in results if not result.ok]
    return {
        "total": len(results),
        "failed": len(failures),
        "failures": failures,
        "results": [asdict(result) for result in results],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate live lotus-manage API evidence.")
    parser.add_argument("--base-url", required=True, help="lotus-manage API base URL.")
    parser.add_argument(
        "--skip-demo-pack",
        action="store_true",
        help="Skip the full live demo pack and run only focused API probes.",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        help="Optional path for machine-readable validation evidence.",
    )
    parser.add_argument(
        "--core-base-url",
        action="append",
        default=[],
        help=(
            "Optional lotus-core base URL to probe for the DPM execution-context route. "
            "May be supplied more than once."
        ),
    )
    parser.add_argument(
        "--expect-core-dpm-route",
        choices=["absent", "available"],
        default="absent",
        help=(
            "Expected lotus-core DPM execution-context route posture. Use 'absent' for the "
            "current RFC-0036 blocked state and 'available' once lotus-core implements the "
            "governed resolver contract."
        ),
    )
    parser.add_argument(
        "--expect-stateful-core-sourcing",
        choices=["disabled", "available"],
        default="disabled",
        help=(
            "Expected lotus-manage stateful core-sourcing posture. Use 'available' when "
            "RFC-087 source products and DPM_STATEFUL_CORE_SOURCING_ENABLED are active."
        ),
    )
    parser.add_argument(
        "--portfolio-id",
        default="PB_SG_GLOBAL_BAL_001",
        help="Portfolio id used for optional lotus-core DPM execution-context probing.",
    )
    parser.add_argument(
        "--as-of",
        default="2026-03-25",
        help="As-of date used for optional lotus-core DPM execution-context probing.",
    )
    args = parser.parse_args()

    results = run_live_api_validation(
        args.base_url,
        include_demo_pack=not args.skip_demo_pack,
        core_base_urls=args.core_base_url,
        expect_core_dpm_route=args.expect_core_dpm_route,
        expect_stateful_core_sourcing=args.expect_stateful_core_sourcing,
        portfolio_id=args.portfolio_id,
        as_of=args.as_of,
    )
    summary = summarize(results)
    rendered = json.dumps(summary, indent=2, sort_keys=True)
    print(rendered)
    if args.json_output is not None:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(rendered + "\n", encoding="utf-8")
    return 1 if summary["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
