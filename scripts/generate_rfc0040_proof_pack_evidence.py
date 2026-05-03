import argparse
import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

import httpx


ROOT = Path(__file__).resolve().parents[1]
DEMO_DIR = ROOT / "docs" / "demo"
DEFAULT_OUTPUT_ROOT = ROOT / "output" / "rfc0040-proof"
FORBIDDEN_AI_FIELD_NAMES = {
    "client_name",
    "client_id",
    "account_number",
    "email",
    "phone",
    "raw_payload",
    "raw_request",
    "raw_response",
    "secret",
    "token",
}


class EvidenceError(RuntimeError):
    pass


def _load_demo_payload(name: str) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads((DEMO_DIR / name).read_text(encoding="utf-8")))


def _stable_json(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False)


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
) -> httpx.Response:
    response = client.request(method, path, json=json_body, headers=headers)
    _assert(
        response.status_code == expected_status,
        f"{method} {path}: expected {expected_status}, got {response.status_code}: {response.text}",
    )
    return response


def _json(response: httpx.Response) -> dict[str, Any]:
    return cast(dict[str, Any], response.json())


def _section_states(proof_pack: dict[str, Any]) -> dict[str, str]:
    return {
        str(section["section_type"]): str(section["state"])
        for section in proof_pack.get("sections", [])
        if isinstance(section, dict)
    }


def _contains_forbidden_ai_field(value: Any) -> bool:
    if isinstance(value, dict):
        return any(
            str(key).lower() in FORBIDDEN_AI_FIELD_NAMES or _contains_forbidden_ai_field(child)
            for key, child in value.items()
        )
    if isinstance(value, list):
        return any(_contains_forbidden_ai_field(child) for child in value)
    return False


def _assert_ready_handoff_pack(proof_pack: dict[str, Any]) -> None:
    states = _section_states(proof_pack)
    _assert(proof_pack["content_hash"].startswith("sha256:"), "proof-pack hash missing")
    _assert(states.get("reporting_refs") == "READY", "reporting_refs section not READY")
    _assert(states.get("ai_refs") == "READY", "ai_refs section not READY")
    _assert(
        proof_pack.get("report_input_ref", {}).get("ref_type") == "DPM_PROOF_PACK_REPORT_INPUT",
        "report input ref missing",
    )
    _assert(
        proof_pack.get("ai_evidence_ref", {}).get("ref_type") == "DPM_PROOF_PACK_AI_EVIDENCE_INPUT",
        "AI evidence ref missing",
    )


def _generate_direct_run_evidence(
    client: httpx.Client,
    output_dir: Path,
    manifest_files: list[dict[str, str]],
    token: str,
) -> dict[str, Any]:
    simulate_response = _request(
        client,
        "POST",
        "/api/v1/rebalance/simulate",
        expected_status=200,
        json_body=_load_demo_payload("27_dpm_supportability_artifact_flow.json"),
        headers={
            "Idempotency-Key": f"rfc0040-direct-run-{token}",
            "X-Correlation-Id": f"corr-rfc0040-direct-run-{token}",
        },
    )
    simulate_body = _json(simulate_response)
    manifest_files.append(_write_json(output_dir, "01-direct-run-simulate.json", simulate_body))
    run_id = str(simulate_body["rebalance_run_id"])

    generate_response = _request(
        client,
        "POST",
        "/api/v1/rebalance/proof-packs",
        expected_status=200,
        json_body={
            "source_type": "REBALANCE_RUN",
            "rebalance_run_id": run_id,
            "include_markdown": True,
            "include_report_input": True,
            "include_ai_evidence_input": True,
            "actor_id": "rfc0040_evidence",
            "reason": "RFC-0040 live evidence generation from a persisted rebalance run.",
            "mandate_id": "PB_SG_GLOBAL_BAL_001",
        },
        headers={
            "Idempotency-Key": f"rfc0040-proof-pack-direct-{token}",
            "X-Correlation-Id": f"corr-rfc0040-proof-direct-{token}",
        },
    )
    generated = _json(generate_response)
    manifest_files.append(
        _write_json(output_dir, "02-direct-run-proof-pack-generation.json", generated)
    )
    proof_pack = cast(dict[str, Any], generated["proof_pack"])
    proof_pack_id = str(proof_pack["proof_pack_id"])

    detail = _json(
        _request(
            client,
            "GET",
            f"/api/v1/rebalance/proof-packs/{proof_pack_id}",
            expected_status=200,
        )
    )
    manifest_files.append(_write_json(output_dir, "03-direct-run-proof-pack-detail.json", detail))
    _assert_ready_handoff_pack(cast(dict[str, Any], detail["proof_pack"]))

    markdown = _request(
        client,
        "GET",
        f"/api/v1/rebalance/proof-packs/{proof_pack_id}/summary.md",
        expected_status=200,
    ).text
    _assert("# Pre-Trade Proof Pack" in markdown, "Markdown proof-pack heading missing")
    _assert("| `reporting_refs` | `READY` |" in markdown, "Markdown report readiness missing")
    _assert("| `ai_refs` | `READY` |" in markdown, "Markdown AI readiness missing")
    manifest_files.append(_write_text(output_dir, "04-direct-run-summary.md", markdown))

    report_input = _json(
        _request(
            client,
            "GET",
            f"/api/v1/rebalance/proof-packs/{proof_pack_id}/report-input",
            expected_status=200,
        )
    )
    _assert(
        report_input["proof_pack_content_hash"] == proof_pack["content_hash"],
        "report input hash does not tie to proof pack",
    )
    manifest_files.append(_write_json(output_dir, "05-direct-run-report-input.json", report_input))

    ai_evidence_input = _json(
        _request(
            client,
            "GET",
            f"/api/v1/rebalance/proof-packs/{proof_pack_id}/ai-evidence-input",
            expected_status=200,
        )
    )
    _assert(
        ai_evidence_input["proof_pack_content_hash"] == proof_pack["content_hash"],
        "AI evidence hash does not tie to proof pack",
    )
    _assert("place_orders" in ai_evidence_input["forbidden_actions"], "AI actions not guarded")
    _assert(
        not _contains_forbidden_ai_field(ai_evidence_input),
        "AI evidence contains forbidden field names",
    )
    manifest_files.append(
        _write_json(output_dir, "06-direct-run-ai-evidence-input.json", ai_evidence_input)
    )

    return {
        "rebalance_run_id": run_id,
        "proof_pack_id": proof_pack_id,
        "status": proof_pack["status"],
        "content_hash": proof_pack["content_hash"],
        "section_states": _section_states(proof_pack),
    }


def _generate_selected_alternative_evidence(
    client: httpx.Client,
    output_dir: Path,
    manifest_files: list[dict[str, str]],
    token: str,
) -> dict[str, Any]:
    alternative_set = _json(
        _request(
            client,
            "POST",
            "/api/v1/construction/alternative-sets/generate",
            expected_status=200,
            json_body={
                **_load_demo_payload("27_dpm_supportability_artifact_flow.json"),
                "methods": ["DO_NOTHING_BASELINE", "HEURISTIC_EXPLAINABLE"],
            },
            headers={
                "Idempotency-Key": f"rfc0040-alt-set-{token}",
                "X-Correlation-Id": f"corr-rfc0040-alt-set-{token}",
            },
        )
    )
    manifest_files.append(
        _write_json(output_dir, "07-selected-alternative-generation.json", alternative_set)
    )
    alternative_set_id = str(alternative_set["alternative_set_id"])
    selected_alternative_id = str(alternative_set["alternatives"][1]["alternative_id"])

    selection = _json(
        _request(
            client,
            "POST",
            f"/api/v1/construction/alternative-sets/{alternative_set_id}/selections",
            expected_status=200,
            json_body={
                "alternative_id": selected_alternative_id,
                "actor_id": "rfc0040_evidence",
                "reason_code": "LOWER_DRIFT_WITH_SOURCE_TRACE",
                "comment": "RFC-0040 evidence selected explainable construction path.",
            },
            headers={"X-Correlation-Id": f"corr-rfc0040-alt-selection-{token}"},
        )
    )
    manifest_files.append(
        _write_json(output_dir, "08-selected-alternative-selection.json", selection)
    )

    generated = _json(
        _request(
            client,
            "POST",
            "/api/v1/rebalance/proof-packs",
            expected_status=200,
            json_body={
                "source_type": "SELECTED_ALTERNATIVE",
                "alternative_set_id": alternative_set_id,
                "selected_alternative_id": selected_alternative_id,
                "include_markdown": True,
                "include_report_input": True,
                "include_ai_evidence_input": True,
                "actor_id": "rfc0040_evidence",
                "reason": "RFC-0040 live evidence generation from selected construction alternative.",
                "mandate_id": "PB_SG_GLOBAL_BAL_001",
            },
            headers={
                "Idempotency-Key": f"rfc0040-proof-pack-alt-{token}",
                "X-Correlation-Id": f"corr-rfc0040-proof-alt-{token}",
            },
        )
    )
    manifest_files.append(
        _write_json(output_dir, "09-selected-alternative-proof-pack-generation.json", generated)
    )
    proof_pack = cast(dict[str, Any], generated["proof_pack"])
    _assert_ready_handoff_pack(proof_pack)
    _assert(
        _section_states(proof_pack).get("selected_alternative") == "READY",
        "selected alternative section is not READY",
    )
    return {
        "alternative_set_id": alternative_set_id,
        "selected_alternative_id": selected_alternative_id,
        "proof_pack_id": proof_pack["proof_pack_id"],
        "status": proof_pack["status"],
        "content_hash": proof_pack["content_hash"],
        "section_states": _section_states(proof_pack),
    }


def _generate_missing_source_evidence(
    client: httpx.Client,
    output_dir: Path,
    manifest_files: list[dict[str, str]],
    token: str,
) -> dict[str, Any]:
    simulate_body = _json(
        _request(
            client,
            "POST",
            "/api/v1/rebalance/simulate",
            expected_status=200,
            json_body=_load_demo_payload("27_dpm_supportability_artifact_flow.json"),
            headers={
                "Idempotency-Key": f"rfc0040-missing-mandate-run-{token}",
                "X-Correlation-Id": f"corr-rfc0040-missing-mandate-run-{token}",
            },
        )
    )
    generated = _json(
        _request(
            client,
            "POST",
            "/api/v1/rebalance/proof-packs",
            expected_status=200,
            json_body={
                "source_type": "REBALANCE_RUN",
                "rebalance_run_id": str(simulate_body["rebalance_run_id"]),
                "include_markdown": True,
                "include_report_input": True,
                "include_ai_evidence_input": True,
                "actor_id": "rfc0040_evidence",
                "reason": "RFC-0040 missing-mandate evidence should block promotion truthfully.",
            },
            headers={
                "Idempotency-Key": f"rfc0040-proof-pack-missing-mandate-{token}",
                "X-Correlation-Id": f"corr-rfc0040-proof-missing-mandate-{token}",
            },
        )
    )
    manifest_files.append(
        _write_json(output_dir, "10-missing-mandate-proof-pack-generation.json", generated)
    )
    proof_pack = cast(dict[str, Any], generated["proof_pack"])
    states = _section_states(proof_pack)
    _assert(proof_pack["status"] == "BLOCKED", "missing mandate proof pack should be BLOCKED")
    _assert(states.get("mandate_context") == "BLOCKED", "mandate context should be BLOCKED")
    _assert(
        "DPM_PROOF_PACK_MANDATE_ID_MISSING"
        in proof_pack.get("supportability", {}).get("reason_codes", []),
        "missing mandate reason code absent",
    )
    _assert_ready_handoff_pack(proof_pack)
    return {
        "rebalance_run_id": str(simulate_body["rebalance_run_id"]),
        "proof_pack_id": proof_pack["proof_pack_id"],
        "status": proof_pack["status"],
        "content_hash": proof_pack["content_hash"],
        "section_states": states,
        "reason_codes": proof_pack.get("supportability", {}).get("reason_codes", []),
    }


def build_critical_review(manifest: dict[str, Any]) -> dict[str, Any]:
    scenarios = cast(dict[str, dict[str, Any]], manifest["scenarios"])
    selected_states = cast(dict[str, str], scenarios["selected_alternative"]["section_states"])
    direct_states = cast(dict[str, str], scenarios["direct_rebalance_run"]["section_states"])
    missing_states = cast(dict[str, str], scenarios["missing_mandate_blocked"]["section_states"])

    findings: list[dict[str, Any]] = [
        {
            "finding_id": "RFC0040-LIVE-001",
            "severity": "info",
            "status": "passed",
            "summary": "Direct rebalance-run proof pack generated durable JSON, Markdown, report input, and AI evidence input.",
            "evidence": scenarios["direct_rebalance_run"]["proof_pack_id"],
        },
        {
            "finding_id": "RFC0040-LIVE-002",
            "severity": "info",
            "status": "passed",
            "summary": "Selected-alternative proof pack retained READY selected-alternative, before-state, and handoff sections.",
            "evidence": scenarios["selected_alternative"]["proof_pack_id"],
        },
        {
            "finding_id": "RFC0040-LIVE-003",
            "severity": "info",
            "status": "passed",
            "summary": "Missing mandate identity blocks proof-pack promotion without hiding other ready evidence.",
            "evidence": scenarios["missing_mandate_blocked"]["proof_pack_id"],
        },
        {
            "finding_id": "RFC0040-LIVE-004",
            "severity": "controlled_gap",
            "status": "accepted_boundary",
            "summary": "Risk, performance, sustainability, currency-overlay, scenario, and tax evidence remain degraded unless source-authority evidence is attached.",
            "evidence": {
                "direct_run_degraded_sections": sorted(
                    section for section, state in direct_states.items() if state == "DEGRADED"
                ),
                "selected_alternative_degraded_sections": sorted(
                    section for section, state in selected_states.items() if state == "DEGRADED"
                ),
            },
        },
        {
            "finding_id": "RFC0040-LIVE-005",
            "severity": "controlled_gap",
            "status": "accepted_boundary",
            "summary": "Full front-office product readiness is not claimed by manage evidence; Gateway, Workbench, report materialization, and AI memo generation remain downstream-owned.",
            "evidence": "RFC-0040 Section 20 and downstream RFC-0098 contracts",
        },
    ]

    return {
        "rfc": "RFC-0040",
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "source_manifest": manifest["output_dir"],
        "result": "passed_with_controlled_downstream_boundaries",
        "checks": {
            "direct_run_handoffs_ready": direct_states.get("reporting_refs") == "READY"
            and direct_states.get("ai_refs") == "READY",
            "selected_alternative_trace_ready": selected_states.get("selected_alternative")
            == "READY",
            "missing_mandate_blocks_promotion": scenarios["missing_mandate_blocked"]["status"]
            == "BLOCKED"
            and missing_states.get("mandate_context") == "BLOCKED",
            "ai_guardrail_passed": manifest["validation"]["ai_forbidden_field_guardrail"]
            == "passed",
            "full_front_office_claim_withheld": True,
        },
        "findings": findings,
    }


def generate_evidence(base_url: str, output_root: Path) -> dict[str, Any]:
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    output_dir = output_root / run_id
    output_dir.mkdir(parents=True, exist_ok=False)
    token = uuid.uuid4().hex[:10]
    manifest_files: list[dict[str, str]] = []

    with httpx.Client(base_url=base_url, timeout=httpx.Timeout(60.0)) as client:
        ready = _json(_request(client, "GET", "/health/ready", expected_status=200))
        _assert(ready.get("status") == "ready", "service is not ready")
        manifest_files.append(_write_json(output_dir, "00-health-ready.json", ready))

        direct_run = _generate_direct_run_evidence(client, output_dir, manifest_files, token)
        selected_alternative = _generate_selected_alternative_evidence(
            client, output_dir, manifest_files, token
        )
        missing_mandate = _generate_missing_source_evidence(
            client, output_dir, manifest_files, token
        )

    manifest = {
        "rfc": "RFC-0040",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "base_url": base_url,
        "output_dir": output_dir.relative_to(ROOT).as_posix(),
        "scenarios": {
            "direct_rebalance_run": direct_run,
            "selected_alternative": selected_alternative,
            "missing_mandate_blocked": missing_mandate,
        },
        "files": manifest_files,
        "validation": {
            "ready_probe": "passed",
            "direct_run_json_markdown_report_ai": "passed",
            "selected_alternative_source": "passed",
            "missing_mandate_blocked_state": "passed",
            "ai_forbidden_field_guardrail": "passed",
        },
    }
    critical_review = build_critical_review(manifest)
    manifest_files.append(_write_json(output_dir, "critical-review.json", critical_review))
    manifest["critical_review"] = {
        "path": f"{manifest['output_dir']}/critical-review.json",
        "result": critical_review["result"],
    }
    manifest_files.append(_write_json(output_dir, "manifest.json", manifest))
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate RFC-0040 proof-pack evidence.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8001")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    args = parser.parse_args()

    manifest = generate_evidence(base_url=args.base_url, output_root=args.output_root)
    print(_stable_json(manifest))


if __name__ == "__main__":
    main()
