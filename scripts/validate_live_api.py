import argparse
import json
import sys
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

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
    return json.loads((DEMO_DIR / filename).read_text(encoding="utf-8"))


def _probe_ready(client: httpx.Client) -> ProbeResult:
    response = client.get("/health/ready")
    body = response.json() if response.content else {}
    return _result(
        "ready",
        response.status_code == 200 and body.get("status") == "ready",
        {"status_code": response.status_code, "body": body},
    )


def _probe_capabilities(client: httpx.Client) -> ProbeResult:
    response = client.get(
        "/platform/capabilities",
        params={"consumer_system": "lotus-gateway", "tenant_id": "default"},
    )
    body = response.json()
    features = _feature_flags(body)
    return _result(
        "capabilities_truthful_default",
        response.status_code == 200
        and body.get("supported_input_modes") == ["inline_bundle"]
        and features.get("dpm.execution.stateful_portfolio_id") is False
        and features.get("dpm.execution.stateless_inline_bundle") is True,
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


def _probe_removed_proposal_route(client: httpx.Client) -> ProbeResult:
    response = client.get("/rebalance/proposals")
    return _result(
        "removed_proposal_route_404",
        response.status_code == 404,
        {"status_code": response.status_code, "body": response.text[:200]},
    )


def _probe_async_duplicate_correlation(client: httpx.Client) -> ProbeResult:
    payload = _load_demo_payload("26_dpm_async_batch_analysis.json")
    correlation_id = f"live-dup-{uuid.uuid4().hex[:10]}"
    headers = {"X-Correlation-Id": correlation_id}
    first = client.post("/rebalance/analyze/async", json=payload, headers=headers)
    second = client.post("/rebalance/analyze/async", json=payload, headers=headers)
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
    response = client.get("/rebalance/supportability/summary")
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
    transport: httpx.BaseTransport | None = None,
) -> list[ProbeResult]:
    results: list[ProbeResult] = []
    timeout = httpx.Timeout(30.0)

    if include_demo_pack:
        try:
            run_demo_pack(base_url)
            results.append(_result("demo_pack", True, {"base_url": base_url}))
        except DemoRunError as exc:
            results.append(_result("demo_pack", False, {"error": str(exc)}))

    with httpx.Client(base_url=base_url, timeout=timeout, transport=transport) as client:
        probes = [
            _probe_ready,
            _probe_capabilities,
            _probe_openapi_boundary,
            _probe_removed_proposal_route,
            _probe_async_duplicate_correlation,
            _probe_supportability_summary,
            _probe_metrics,
        ]
        for probe in probes:
            try:
                results.append(probe(client))
            except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
                results.append(_result(probe.__name__, False, {"error": str(exc)}))

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
    args = parser.parse_args()

    results = run_live_api_validation(
        args.base_url,
        include_demo_pack=not args.skip_demo_pack,
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
