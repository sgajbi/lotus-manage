import argparse
import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

import httpx


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = ROOT / "output" / "rfc0042-outcome-proof"


class EvidenceError(RuntimeError):
    pass


def _stable_json(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=True, default=str)


def _content_hash(content: str) -> str:
    return f"sha256:{hashlib.sha256(content.encode('utf-8')).hexdigest()}"


def _write_json(output_dir: Path, name: str, data: Any) -> dict[str, str]:
    content = _stable_json(data) + "\n"
    path = output_dir / name
    path.write_text(content, encoding="utf-8")
    return {"path": path.relative_to(ROOT).as_posix(), "content_hash": _content_hash(content)}


def _write_text(output_dir: Path, name: str, content: str) -> dict[str, str]:
    path = output_dir / name
    path.write_text(content, encoding="utf-8")
    return {"path": path.relative_to(ROOT).as_posix(), "content_hash": _content_hash(content)}


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise EvidenceError(message)


def _request(
    client: httpx.Client,
    method: str,
    path: str,
    *,
    expected_status: int,
    json_body: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
) -> httpx.Response:
    response = client.request(method, path, json=json_body, headers=headers, params=params)
    _assert(
        response.status_code == expected_status,
        f"{method} {path}: expected {expected_status}, got {response.status_code}: {response.text}",
    )
    return response


def _json(response: httpx.Response) -> dict[str, Any]:
    return cast(dict[str, Any], response.json())


def _source_ref(
    *,
    source_system: str,
    source_type: str,
    source_id: str,
    content_hash: str,
) -> dict[str, Any]:
    return {
        "source_system": source_system,
        "source_type": source_type,
        "source_id": source_id,
        "source_version": "1.0.0",
        "content_hash": content_hash,
    }


def _metric(
    *,
    value: str | None,
    unit: str,
    source_ref: dict[str, Any],
    supportability_state: str = "READY",
    reason_code: str = "SOURCE_READY",
    freshness_state: str = "CURRENT",
) -> dict[str, Any]:
    return {
        "value": value,
        "unit": unit,
        "source_refs": [source_ref],
        "source_freshness": {
            "observed_at": "2026-05-06T01:10:00Z",
            "as_of_date": "2026-05-06",
            "freshness_state": freshness_state,
        },
        "supportability": {
            "state": supportability_state,
            "reason_codes": [reason_code],
            "required_source": True,
            "explanation": f"{source_ref['source_system']} source evidence is {supportability_state}.",
        },
    }


def _outcome_request(token: str) -> dict[str, Any]:
    expected_hash = _content_hash(f"rfc0042:expected:selected-alternative:{token}")
    realized_hash = _content_hash(f"rfc0042:realized:post-trade-holdings:{token}")
    selected_section_hash = _content_hash(f"rfc0042:section:selected-alternative:{token}")
    expected_ref = _source_ref(
        source_system="lotus-manage",
        source_type="DPM_SELECTED_ALTERNATIVE_EXPECTED_OUTCOME",
        source_id=f"selected-alternative-{token}",
        content_hash=expected_hash,
    )
    realized_ref = _source_ref(
        source_system="lotus-core",
        source_type="POST_TRADE_HOLDINGS_WINDOW",
        source_id=f"post-trade-holdings-{token}",
        content_hash=realized_hash,
    )
    expected_metric = _metric(
        value="0.0350",
        unit="ratio",
        source_ref=expected_ref,
        reason_code="EXPECTED_READY",
    )
    realized_metric = _metric(
        value="0.0340",
        unit="ratio",
        source_ref=realized_ref,
        reason_code="REALIZED_READY",
    )
    return {
        "expected_snapshot": {
            "portfolio_id": "PB_SG_GLOBAL_BAL_001",
            "mandate_id": "MANDATE_PB_SG_GLOBAL_BAL_001",
            "rebalance_run_id": f"rr_rfc0042_{token}",
            "alternative_set_id": f"cas_rfc0042_{token}",
            "selected_alternative_id": f"alt_min_turnover_{token}",
            "proof_pack_id": f"dpp_rfc0042_{token}",
            "wave_id": f"dwv_rfc0042_{token}",
            "wave_item_id": f"dwi_rfc0042_{token}",
            "operations_handoff_ref_id": f"dwh_rfc0042_{token}",
            "expected_values": {"DRIFT_REDUCTION": expected_metric},
            "supportability": {
                "state": "READY",
                "reason_codes": ["EXPECTED_READY"],
                "required_source": True,
                "explanation": "Expected drift reduction is sourced from selected pre-trade evidence.",
            },
            "source_lineage": [expected_ref],
            "source_hashes": {"selected_alternative": expected_ref["content_hash"]},
            "section_hashes": {"selected_alternative": selected_section_hash},
        },
        "realized_snapshot": {
            "portfolio_id": "PB_SG_GLOBAL_BAL_001",
            "review_window": {
                "start_at": "2026-05-05T01:00:00Z",
                "end_at": "2026-05-06T01:00:00Z",
                "as_of_date": "2026-05-06",
            },
            "realized_values": {"DRIFT_REDUCTION": realized_metric},
            "supportability": {
                "state": "READY",
                "reason_codes": ["REALIZED_READY"],
                "required_source": True,
                "explanation": "Realized drift reduction is supplied from post-trade holdings evidence.",
            },
            "source_lineage": [realized_ref],
            "source_hashes": {"post_trade_holdings": realized_ref["content_hash"]},
            "quality_summary": {"COMPLETE": 1},
        },
        "dimension_configs": [
            {
                "dimension": "DRIFT_REDUCTION",
                "tolerance": {"soft": "0.0025", "hard": "0.0100"},
                "materiality": "0.0050",
                "direction": "LOWER_IS_BETTER",
            }
        ],
        "actor_id": "rfc0042_evidence",
    }


def _degraded_request(token: str) -> dict[str, Any]:
    request = _outcome_request(f"{token}_degraded")
    metric = request["realized_snapshot"]["realized_values"]["DRIFT_REDUCTION"]
    metric["supportability"] = {
        "state": "DEGRADED",
        "reason_codes": ["SOURCE_EVIDENCE_INCOMPLETE"],
        "required_source": True,
        "explanation": "Post-trade holdings source is partial but still diagnostically comparable.",
    }
    metric["source_freshness"]["freshness_state"] = "STALE"
    request["realized_snapshot"]["supportability"] = {
        "state": "DEGRADED",
        "reason_codes": ["SOURCE_EVIDENCE_INCOMPLETE"],
        "required_source": True,
        "explanation": "Realized source evidence is partial for degraded-state proof.",
    }
    request["realized_snapshot"]["quality_summary"] = {"PARTIAL": 1}
    return request


def _refresh_request(create_request: dict[str, Any]) -> dict[str, Any]:
    realized_snapshot = cast(
        dict[str, Any], json.loads(json.dumps(create_request["realized_snapshot"]))
    )
    refreshed_hash = _content_hash(
        f"rfc0042:realized:post-trade-holdings-refresh:"
        f"{realized_snapshot['source_lineage'][0]['source_id']}"
    )
    realized_snapshot["realized_values"]["DRIFT_REDUCTION"]["value"] = "0.0345"
    realized_snapshot["source_hashes"]["post_trade_holdings"] = refreshed_hash
    realized_snapshot["source_lineage"][0]["content_hash"] = refreshed_hash
    realized_snapshot["source_lineage"][0]["source_id"] = (
        f"{realized_snapshot['source_lineage'][0]['source_id']}-refresh"
    )
    realized_snapshot["realized_values"]["DRIFT_REDUCTION"]["source_refs"][0]["content_hash"] = (
        refreshed_hash
    )
    realized_snapshot["realized_values"]["DRIFT_REDUCTION"]["source_refs"][0]["source_id"] = (
        realized_snapshot["source_lineage"][0]["source_id"]
    )
    return {
        "actor_id": "rfc0042_evidence",
        "realized_snapshot": realized_snapshot,
        "dimension_configs": create_request["dimension_configs"],
    }


def _openapi_certification(client: httpx.Client) -> dict[str, Any]:
    openapi = _json(_request(client, "GET", "/openapi.json", expected_status=200))
    required_paths = {
        "/api/v1/rebalance/outcome-reviews/preview": {"post"},
        "/api/v1/rebalance/outcome-reviews": {"get", "post"},
        "/api/v1/rebalance/outcome-reviews/{outcome_review_id}": {"get"},
        "/api/v1/rebalance/outcome-reviews/{outcome_review_id}/refresh-sources": {"post"},
        "/api/v1/rebalance/outcome-reviews/{outcome_review_id}/supportability": {"get"},
        "/api/v1/rebalance/outcome-reviews/{outcome_review_id}/report-input": {"get"},
        "/api/v1/rebalance/outcome-reviews/{outcome_review_id}/ai-evidence-input": {"get"},
        "/api/v1/rebalance/runs/{rebalance_run_id}/outcome-review": {"get"},
        "/api/v1/rebalance/waves/{wave_id}/outcome-reviews": {"get"},
    }
    missing: list[str] = []
    weak: list[str] = []
    paths = cast(dict[str, Any], openapi.get("paths", {}))
    for path, methods in required_paths.items():
        operations = cast(dict[str, Any], paths.get(path, {}))
        for method in methods:
            operation = cast(dict[str, Any] | None, operations.get(method))
            if operation is None:
                missing.append(f"{method.upper()} {path}")
                continue
            if operation.get("tags") != ["lotus-manage Outcome Reviews"]:
                weak.append(f"{method.upper()} {path} tag")
            description = str(operation.get("description", ""))
            if not all(marker in description for marker in ("What:", "When:", "How:")):
                weak.append(f"{method.upper()} {path} What/When/How")
            if not operation.get("summary"):
                weak.append(f"{method.upper()} {path} summary")
            if not operation.get("responses"):
                weak.append(f"{method.upper()} {path} responses")
    return {
        "required_path_count": len(required_paths),
        "missing": missing,
        "weak": weak,
        "passed": missing == [] and weak == [],
    }


def _variance_worked_example(create_response: dict[str, Any]) -> dict[str, Any]:
    result = create_response["outcome_review"]["dimension_results"][0]
    return {
        "dimension": result["dimension"],
        "expected": result["expected"],
        "realized": result["realized"],
        "variance": result["variance"],
        "direction": result["calculation_trace"]["direction"],
        "soft_tolerance": result["calculation_trace"]["soft_tolerance"],
        "hard_tolerance": result["calculation_trace"]["hard_tolerance"],
        "state": result["state"],
        "reason_code": result["reason_code"],
        "passed": result["state"] == "READY" and result["variance"] == "-0.0010",
    }


def _source_lineage(create_response: dict[str, Any]) -> dict[str, Any]:
    review = create_response["outcome_review"]
    return {
        "outcome_review_id": review["outcome_review_id"],
        "source_lineage": review["source_lineage"],
        "source_hashes": review["source_hashes"],
        "section_hashes": review["section_hashes"],
        "source_ref_count": len(review["source_lineage"]),
        "source_systems": sorted({source["source_system"] for source in review["source_lineage"]}),
    }


def _test_summary() -> dict[str, Any]:
    return {
        "local_gates": [
            "python -m pytest tests/unit/core/test_outcome_handoffs.py tests/unit/api/test_outcome_reviews_api.py tests/unit/core/test_outcome_comparison.py tests/unit/core/test_realized_outcome_sources.py tests/integration/dpm/test_outcome_expected_snapshot_assembly.py tests/unit/infrastructure/test_outcome_review_repository.py tests/unit/dpm/api/test_observability_api.py tests/unit/test_observability_contracts.py tests/unit/test_documentation_current_state.py -q",
            "python scripts/openapi_quality_gate.py",
            "python scripts/api_vocabulary_inventory.py --validate-only",
            "python scripts/no_alias_contract_guard.py",
            "python -m pytest tests/integration/test_openapi_certification_matrix.py -q",
        ],
        "live_evidence_script": "python scripts/generate_rfc0042_outcome_evidence.py --base-url http://127.0.0.1:8001",
    }


def build_critical_review(manifest: dict[str, Any]) -> dict[str, Any]:
    create_response = cast(dict[str, Any], manifest["create_response"])
    supportability = cast(dict[str, Any], manifest["supportability_response"])
    report_input = cast(dict[str, Any], manifest["report_input"])
    ai_evidence = cast(dict[str, Any], manifest["ai_evidence_input"])
    degraded = cast(dict[str, Any], manifest["degraded_source_example"])
    openapi = cast(dict[str, Any], manifest["openapi_certification"])
    variance = cast(dict[str, Any], manifest["variance_worked_example"])
    idempotency_replay = cast(dict[str, Any], manifest["idempotency_replay"])
    idempotency_conflict = cast(dict[str, Any], manifest["idempotency_conflict"])
    review = create_response["outcome_review"]
    checks = {
        "review_created_ready": review["state"] == "READY",
        "idempotency_replay_preserved_review": idempotency_replay["outcome_review"][
            "outcome_review_id"
        ]
        == review["outcome_review_id"],
        "idempotency_conflict_rejected": idempotency_conflict["detail"]
        == "DPM_OUTCOME_REVIEW_IDEMPOTENCY_CONFLICT",
        "source_lineage_preserved": len(review["source_lineage"]) >= 2,
        "supportability_operator_fields_present": supportability["source_ref_count"] >= 2
        and supportability["dimension_state_counts"].get("READY") == 1,
        "report_input_is_handoff_only": report_input["evidence_ref"]["source_type"]
        == "DPM_OUTCOME_REPORT_INPUT",
        "ai_evidence_guardrails_present": "score_portfolio_manager"
        in ai_evidence["forbidden_actions"],
        "degraded_source_example_visible": degraded["comparison"]["state"] == "DEGRADED",
        "refresh_appended_event": manifest["refresh_response"]["event"]["event_type"]
        == "OUTCOME_REVIEW_SOURCE_REFRESHED",
        "openapi_certification_passed": openapi["passed"] is True,
        "variance_worked_example_passed": variance["passed"] is True,
    }
    findings = [
        {
            "finding_id": "RFC0042-LIVE-001",
            "severity": "info",
            "status": "passed" if checks["review_created_ready"] else "failed",
            "summary": "Durable outcome review was created on the live manage runtime and classified READY.",
            "evidence": review["outcome_review_id"],
        },
        {
            "finding_id": "RFC0042-LIVE-002",
            "severity": "info",
            "status": "passed" if checks["source_lineage_preserved"] else "failed",
            "summary": "Expected and realized source refs, hashes, and section hashes are preserved in review evidence.",
            "evidence": manifest["source_lineage"]["source_systems"],
        },
        {
            "finding_id": "RFC0042-LIVE-003",
            "severity": "info",
            "status": "passed" if checks["degraded_source_example_visible"] else "failed",
            "summary": "Degraded realized source evidence remains explicit and does not become a ready claim.",
            "evidence": degraded["comparison"]["supportability"]["reason_codes"],
        },
        {
            "finding_id": "RFC0042-LIVE-004",
            "severity": "info",
            "status": "passed" if checks["ai_evidence_guardrails_present"] else "failed",
            "summary": "AI evidence input keeps forbidden actions explicit and does not generate narrative.",
            "evidence": ai_evidence["forbidden_actions"],
        },
        {
            "finding_id": "RFC0042-LIVE-005",
            "severity": "controlled_gap",
            "status": "accepted_boundary",
            "summary": "Gateway and Workbench realization RFCs are aligned, but downstream implementation and canonical UI proof are not claimed by manage Slice 11.",
            "evidence": {
                "lotus_gateway_commit": "38d46f9",
                "lotus_workbench_commit": "3b5182f",
            },
        },
    ]
    return {
        "rfc": "RFC-0042",
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "source_manifest": manifest["output_dir"],
        "result": "passed" if all(checks.values()) else "failed",
        "checks": checks,
        "findings": findings,
    }


def _render_critical_review(review: dict[str, Any]) -> str:
    lines = [
        "# RFC-0042 Live Outcome Proof Critical Review",
        "",
        f"- Result: `{review['result']}`",
        f"- Reviewed at: `{review['reviewed_at']}`",
        "",
        "## Checks",
    ]
    for name, passed in cast(dict[str, bool], review["checks"]).items():
        lines.append(f"- `{name}`: {'PASS' if passed else 'FAIL'}")
    lines.extend(["", "## Findings"])
    for finding in cast(list[dict[str, Any]], review["findings"]):
        lines.append(f"- `{finding['finding_id']}` {finding['status']}: {finding['summary']}")
    lines.append("")
    return "\n".join(lines)


def generate_evidence(base_url: str, output_root: Path) -> dict[str, Any]:
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    output_dir = output_root / run_id
    output_dir.mkdir(parents=True, exist_ok=False)
    token = uuid.uuid4().hex[:10]
    manifest_files: list[dict[str, str]] = []

    with httpx.Client(base_url=base_url, timeout=httpx.Timeout(90.0)) as client:
        ready = _json(_request(client, "GET", "/health/ready", expected_status=200))
        _assert(ready.get("status") == "ready", "service is not ready")
        manifest_files.append(_write_json(output_dir, "00-health-ready.json", ready))

        create_request = _outcome_request(token)
        manifest_files.append(_write_json(output_dir, "01-create-request.json", create_request))
        preview = _json(
            _request(
                client,
                "POST",
                "/api/v1/rebalance/outcome-reviews/preview",
                expected_status=200,
                json_body=create_request,
            )
        )
        manifest_files.append(_write_json(output_dir, "02-preview-response.json", preview))
        _assert(preview["comparison"]["state"] == "READY", "preview must be ready")

        create_response = _json(
            _request(
                client,
                "POST",
                "/api/v1/rebalance/outcome-reviews",
                expected_status=200,
                json_body=create_request,
                headers={
                    "Idempotency-Key": f"rfc0042-outcome-{token}",
                    "X-Correlation-Id": f"corr-rfc0042-{token}",
                },
            )
        )
        manifest_files.append(_write_json(output_dir, "03-create-response.json", create_response))
        outcome_review_id = str(create_response["outcome_review"]["outcome_review_id"])

        idempotency_replay = _json(
            _request(
                client,
                "POST",
                "/api/v1/rebalance/outcome-reviews",
                expected_status=200,
                json_body=create_request,
                headers={
                    "Idempotency-Key": f"rfc0042-outcome-{token}",
                    "X-Correlation-Id": f"corr-rfc0042-{token}-replay",
                },
            )
        )
        _assert(
            idempotency_replay["outcome_review"]["outcome_review_id"] == outcome_review_id,
            "same-key same-evidence replay must return the original review",
        )
        conflict_request = cast(dict[str, Any], json.loads(json.dumps(create_request)))
        conflict_request["realized_snapshot"]["realized_values"]["DRIFT_REDUCTION"]["value"] = (
            "0.0200"
        )
        idempotency_conflict = _json(
            _request(
                client,
                "POST",
                "/api/v1/rebalance/outcome-reviews",
                expected_status=409,
                json_body=conflict_request,
                headers={
                    "Idempotency-Key": f"rfc0042-outcome-{token}",
                    "X-Correlation-Id": f"corr-rfc0042-{token}-conflict",
                },
            )
        )

        retrieved_review = _json(
            _request(
                client,
                "GET",
                f"/api/v1/rebalance/outcome-reviews/{outcome_review_id}",
                expected_status=200,
            )
        )
        search_response = _json(
            _request(
                client,
                "GET",
                "/api/v1/rebalance/outcome-reviews",
                expected_status=200,
                params={"portfolio_id": "PB_SG_GLOBAL_BAL_001", "state": "READY"},
            )
        )
        supportability_response = _json(
            _request(
                client,
                "GET",
                f"/api/v1/rebalance/outcome-reviews/{outcome_review_id}/supportability",
                expected_status=200,
            )
        )
        report_input = _json(
            _request(
                client,
                "GET",
                f"/api/v1/rebalance/outcome-reviews/{outcome_review_id}/report-input",
                expected_status=200,
            )
        )
        ai_evidence_input = _json(
            _request(
                client,
                "GET",
                f"/api/v1/rebalance/outcome-reviews/{outcome_review_id}/ai-evidence-input",
                expected_status=200,
            )
        )
        source_lineage = _source_lineage(create_response)
        variance_worked_example = _variance_worked_example(create_response)
        refresh_response = _json(
            _request(
                client,
                "POST",
                f"/api/v1/rebalance/outcome-reviews/{outcome_review_id}/refresh-sources",
                expected_status=200,
                json_body=_refresh_request(create_request),
            )
        )
        run_lookup = _json(
            _request(
                client,
                "GET",
                f"/api/v1/rebalance/runs/{create_request['expected_snapshot']['rebalance_run_id']}/outcome-review",
                expected_status=200,
            )
        )
        wave_lookup = _json(
            _request(
                client,
                "GET",
                f"/api/v1/rebalance/waves/{create_request['expected_snapshot']['wave_id']}/outcome-reviews",
                expected_status=200,
            )
        )
        degraded_source_example = _json(
            _request(
                client,
                "POST",
                "/api/v1/rebalance/outcome-reviews/preview",
                expected_status=200,
                json_body=_degraded_request(token),
            )
        )
        openapi_certification = _openapi_certification(client)

    manifest_files.append(_write_json(output_dir, "04-retrieved-review.json", retrieved_review))
    manifest_files.append(
        _write_json(output_dir, "04a-idempotency-replay-response.json", idempotency_replay)
    )
    manifest_files.append(
        _write_json(output_dir, "04b-idempotency-conflict-response.json", idempotency_conflict)
    )
    manifest_files.append(_write_json(output_dir, "05-search-response.json", search_response))
    manifest_files.append(
        _write_json(output_dir, "06-supportability-response.json", supportability_response)
    )
    manifest_files.append(_write_json(output_dir, "07-report-input.json", report_input))
    manifest_files.append(_write_json(output_dir, "08-ai-evidence-input.json", ai_evidence_input))
    manifest_files.append(_write_json(output_dir, "09-source-lineage.json", source_lineage))
    manifest_files.append(
        _write_json(output_dir, "10-variance-worked-example.json", variance_worked_example)
    )
    manifest_files.append(
        _write_json(output_dir, "11-degraded-source-example.json", degraded_source_example)
    )
    manifest_files.append(_write_json(output_dir, "12-refresh-response.json", refresh_response))
    manifest_files.append(_write_json(output_dir, "13-run-lookup-response.json", run_lookup))
    manifest_files.append(_write_json(output_dir, "14-wave-lookup-response.json", wave_lookup))
    manifest_files.append(
        _write_json(output_dir, "15-openapi-certification.json", openapi_certification)
    )
    test_summary = _test_summary()
    manifest_files.append(_write_json(output_dir, "16-test-summary.json", test_summary))

    manifest = {
        "rfc": "RFC-0042",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "base_url": base_url,
        "output_dir": output_dir.relative_to(ROOT).as_posix(),
        "create_response": create_response,
        "idempotency_replay": idempotency_replay,
        "idempotency_conflict": idempotency_conflict,
        "supportability_response": supportability_response,
        "report_input": report_input,
        "ai_evidence_input": ai_evidence_input,
        "source_lineage": source_lineage,
        "variance_worked_example": variance_worked_example,
        "degraded_source_example": degraded_source_example,
        "refresh_response": refresh_response,
        "openapi_certification": openapi_certification,
        "test_summary": test_summary,
        "files": manifest_files,
    }
    critical_review = build_critical_review(manifest)
    manifest_files.append(_write_json(output_dir, "critical-review.json", critical_review))
    manifest_files.append(
        _write_text(output_dir, "critical-review.md", _render_critical_review(critical_review))
    )
    manifest["critical_review"] = {
        "path": f"{manifest['output_dir']}/critical-review.json",
        "result": critical_review["result"],
    }
    manifest_files.append(_write_json(output_dir, "manifest.json", manifest))
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate RFC-0042 outcome review evidence.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8001")
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    args = parser.parse_args()
    manifest = generate_evidence(args.base_url, Path(args.output_root))
    print(_stable_json(manifest))


if __name__ == "__main__":
    main()
