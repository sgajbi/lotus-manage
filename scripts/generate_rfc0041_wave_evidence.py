import argparse
import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

import httpx


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = ROOT / "output" / "rfc0041-wave-proof"


class EvidenceError(RuntimeError):
    pass


def _stable_json(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False, default=str)


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


def _seed_health_input(
    *,
    mandate_id: str,
    portfolio_id: str,
    health_profile: str,
) -> dict[str, Any]:
    source_readiness_state = "READY"
    extra: dict[str, Any] = {}
    if health_profile == "degraded":
        source_readiness_state = "DEGRADED"
        extra["degraded_source_families"] = ["MARKET_DATA_COVERAGE"]
    if health_profile == "pending_review":
        extra["approval_required"] = True
    return {
        "twin": {
            "mandate_id": mandate_id,
            "portfolio_id": portfolio_id,
            "mandate_version": "3",
            "as_of_date": "2026-05-03",
            "base_currency": "SGD",
            "reference_currency": "SGD",
            "risk_profile": "BALANCED",
            "investment_objective": "LONG_TERM_TOTAL_RETURN",
            "time_horizon": "LONG_TERM",
            "model_portfolio_id": "MODEL_PB_SG_GLOBAL_BAL_DPM",
            "model_portfolio_version": "2026.04",
            "constraints": {
                "cash_band_min_weight": "0.02",
                "cash_band_max_weight": "0.10",
                "turnover_budget": "0.15",
            },
            "review_policy": {"next_review_due_date": "2026-06-30"},
            "source_lineage": [
                {
                    "product_name": "DiscretionaryMandateBinding",
                    "product_version": "v1",
                    "source_system": "lotus-core",
                    "source_record_id": f"DiscretionaryMandateBinding:v1:{portfolio_id}",
                    "data_quality_status": "READY",
                    "latest_evidence_timestamp": "2026-05-03T01:00:00Z",
                    "lineage": {"contract_version": "DiscretionaryMandateBinding:v1"},
                }
            ],
        },
        "current_weights": {"CASH": "0.05", "EQ_1": "0.80"},
        "target_weights": {"CASH": "0.05", "EQ_1": "0.80"},
        "cash_weight": "0.05",
        "source_readiness_state": source_readiness_state,
        **extra,
    }


def _wave_request(token: str) -> dict[str, Any]:
    return {
        "trigger_type": "EXPLICIT_PORTFOLIO_LIST",
        "trigger_id": f"rfc0041-live-wave-{token}",
        "rationale": "RFC-0041 live proof for affected-portfolio wave orchestration.",
        "as_of_date": "2026-05-03",
        "actor_id": "rfc0041_evidence",
        "portfolios": [
            {"portfolio_id": "PB_SG_GLOBAL_BAL_001"},
            {"portfolio_id": "PB_SG_DEGRADED_002"},
            {"portfolio_id": "PB_SG_PENDING_003"},
            {"portfolio_id": "PB_SG_UNSOURCED_004"},
        ],
    }


def _rebalance_request(token: str) -> dict[str, Any]:
    instrument_id = f"EQ_RFC0041_{token.upper()}"
    return {
        "portfolio_snapshot": {
            "portfolio_id": "PB_SG_GLOBAL_BAL_001",
            "base_currency": "SGD",
            "positions": [{"instrument_id": instrument_id, "quantity": "100"}],
            "cash_balances": [{"currency": "SGD", "amount": "5000"}],
        },
        "market_data_snapshot": {
            "prices": [{"instrument_id": instrument_id, "price": "100", "currency": "SGD"}],
            "fx_rates": [],
        },
        "model_portfolio": {"targets": [{"instrument_id": instrument_id, "weight": "0.80"}]},
        "shelf_entries": [{"instrument_id": instrument_id, "status": "APPROVED"}],
        "options": {"target_method": "HEURISTIC"},
    }


def _analytics_authority_context(token: str) -> dict[str, Any]:
    return {
        "risk_context": {
            "supportability_status": "READY",
            "source_system": "lotus-risk",
            "source_product_name": "ConcentrationAnalysis",
            "source_product_version": "v1",
            "source_id": f"risk-rfc0041-{token}",
            "content_hash": f"sha256:risk-rfc0041-{token}",
            "concentration_breaches": 0,
            "concentration_hhi_delta": "125.50",
            "top_position_weight_proposed": "0.2100",
            "issuer_coverage_status": "complete",
            "reason_codes": ["LOTUS_RISK_CONCENTRATION_READY"],
        },
        "performance_context": {
            "supportability_status": "DEGRADED",
            "source_system": "lotus-performance",
            "source_product_name": "PerformanceBenchmarkContext",
            "source_product_version": "v1",
            "source_id": f"performance-rfc0041-{token}",
            "content_hash": f"sha256:performance-rfc0041-{token}",
            "benchmark_id": "BMK_PB_GLOBAL_BALANCED_60_40",
            "active_return": "-0.0125",
            "underperformance_flag": True,
            "reason_codes": ["PERFORMANCE_CONTEXT_STALE"],
        },
    }


def _state_counts(wave_response: dict[str, Any]) -> dict[str, int]:
    return cast(dict[str, int], wave_response["wave"]["aggregate_metrics"]["state_counts"])


def _selected_ready_item(wave_response: dict[str, Any]) -> dict[str, Any]:
    for item in wave_response["wave"]["items"]:
        if item["portfolio_id"] == "PB_SG_GLOBAL_BAL_001":
            return cast(dict[str, Any], item)
    raise EvidenceError("ready portfolio item missing from wave response")


def _generate_wave_lifecycle(
    client: httpx.Client,
    output_dir: Path,
    manifest_files: list[dict[str, str]],
    token: str,
) -> dict[str, Any]:
    seeds = []
    seed_requests = [
        _seed_health_input(
            mandate_id="MANDATE_PB_SG_GLOBAL_BAL_001",
            portfolio_id="PB_SG_GLOBAL_BAL_001",
            health_profile="ready",
        ),
        _seed_health_input(
            mandate_id="MANDATE_PB_SG_DEGRADED_002",
            portfolio_id="PB_SG_DEGRADED_002",
            health_profile="degraded",
        ),
        _seed_health_input(
            mandate_id="MANDATE_PB_SG_PENDING_003",
            portfolio_id="PB_SG_PENDING_003",
            health_profile="pending_review",
        ),
    ]
    for seed_index, seed_request in enumerate(seed_requests, start=1):
        mandate_id = str(seed_request["twin"]["mandate_id"])
        seed = _json(
            _request(
                client,
                "POST",
                f"/api/v1/mandates/{mandate_id}/health/recalculate",
                expected_status=200,
                json_body=seed_request,
            )
        )
        seeds.append(seed)
        manifest_files.append(
            _write_json(output_dir, f"01-{seed_index}-seed-mandate-health.json", seed)
        )
    _assert(
        [seed["source_readiness_state"] for seed in seeds] == ["READY", "DEGRADED", "READY"],
        "seed source-readiness states did not match ready/degraded/pending proof setup",
    )

    preview = _json(
        _request(
            client,
            "POST",
            "/api/v1/rebalance/waves/preview",
            expected_status=200,
            json_body=_wave_request(token),
            headers={"X-Correlation-Id": f"corr-rfc0041-preview-{token}"},
        )
    )
    manifest_files.append(_write_json(output_dir, "02-wave-preview.json", preview))
    _assert(preview["durable"] is False, "preview must be non-durable")
    _assert(
        _state_counts(preview) == {"CANDIDATE": 3, "SOURCE_BLOCKED": 1},
        "unexpected preview state counts",
    )

    created = _json(
        _request(
            client,
            "POST",
            "/api/v1/rebalance/waves",
            expected_status=201,
            json_body=_wave_request(token),
            headers={
                "Idempotency-Key": f"rfc0041-wave-create-{token}",
                "X-Correlation-Id": f"corr-rfc0041-create-{token}",
            },
        )
    )
    manifest_files.append(_write_json(output_dir, "03-wave-create.json", created))
    wave_id = str(created["wave"]["wave_id"])
    _assert(created["durable"] is True, "created wave must be durable")

    source_checked = _json(
        _request(
            client,
            "POST",
            f"/api/v1/rebalance/waves/{wave_id}/source-check",
            expected_status=200,
            json_body={"actor_id": "rfc0041_evidence"},
            headers={"X-Correlation-Id": f"corr-rfc0041-source-{token}"},
        )
    )
    manifest_files.append(_write_json(output_dir, "04-wave-source-check.json", source_checked))
    _assert(
        _state_counts(source_checked)
        == {
            "SOURCE_READY": 1,
            "SOURCE_DEGRADED": 1,
            "REVIEW_REQUIRED": 1,
            "SOURCE_BLOCKED": 1,
        },
        "unexpected source-check state counts",
    )

    ready_item = _selected_ready_item(source_checked)
    simulated = _json(
        _request(
            client,
            "POST",
            f"/api/v1/rebalance/waves/{wave_id}/simulate",
            expected_status=200,
            json_body={
                "actor_id": "rfc0041_evidence",
                "methods": ["RISK_AWARE", "MIN_TURNOVER"],
                "item_inputs": [
                    {
                        "wave_item_id": ready_item["wave_item_id"],
                        "stateless_input": _rebalance_request(token),
                        "authority_context": _analytics_authority_context(token),
                    }
                ],
            },
            headers={"X-Correlation-Id": f"corr-rfc0041-simulate-{token}"},
        )
    )
    manifest_files.append(_write_json(output_dir, "05-wave-simulate.json", simulated))
    _assert(_state_counts(simulated).get("SIMULATED") == 1, "ready item was not simulated")
    source_analytics = simulated["wave"]["aggregate_metrics"]["source_analytics"]
    families = {entry["source_family"]: entry for entry in source_analytics}
    _assert(
        families["RISK"]["supportability_state"] == "READY",
        "risk source analytics was not ready",
    )
    _assert(
        families["PERFORMANCE"]["supportability_state"] == "DEGRADED",
        "performance source analytics degraded posture was not preserved",
    )
    simulated_item = _selected_ready_item(simulated)
    alternative_set_id = str(simulated_item["alternative_set_id"])

    alternative_set = _json(
        _request(
            client,
            "GET",
            f"/api/v1/construction/alternative-sets/{alternative_set_id}",
            expected_status=200,
        )
    )
    manifest_files.append(
        _write_json(output_dir, "06-alternative-set-detail.json", alternative_set)
    )
    selected_alternative_id = str(alternative_set["alternatives"][0]["alternative_id"])

    selected = _json(
        _request(
            client,
            "POST",
            f"/api/v1/rebalance/waves/{wave_id}/items/{simulated_item['wave_item_id']}/select",
            expected_status=200,
            json_body={
                "alternative_id": selected_alternative_id,
                "actor_id": "rfc0041_evidence",
                "reason_code": "RFC0041_LIVE_PROOF_SELECTED",
                "comment": "Selected during RFC-0041 live proof.",
                "generate_proof_pack": True,
            },
            headers={"X-Correlation-Id": f"corr-rfc0041-select-{token}"},
        )
    )
    manifest_files.append(_write_json(output_dir, "07-wave-select-proof-pack.json", selected))
    selected_item = _selected_ready_item(selected)
    _assert(selected_item["proof_pack_id"], "proof-pack id missing after selection")
    _assert(
        selected_item["state"] == "PROOF_PACK_READY",
        "selected item did not become proof-pack ready",
    )

    proof_pack_id = str(selected_item["proof_pack_id"])
    proof_pack = _json(
        _request(
            client,
            "GET",
            f"/api/v1/rebalance/proof-packs/{proof_pack_id}",
            expected_status=200,
        )
    )
    manifest_files.append(_write_json(output_dir, "08-linked-proof-pack-detail.json", proof_pack))

    approved = _json(
        _request(
            client,
            "POST",
            f"/api/v1/rebalance/waves/{wave_id}/approve",
            expected_status=200,
            json_body={
                "actor_id": "rfc0041_evidence",
                "reason_code": "RFC0041_LIVE_PROOF_APPROVED",
                "comment": "Approved eligible item while preserving blocked exceptions.",
            },
            headers={"X-Correlation-Id": f"corr-rfc0041-approve-{token}"},
        )
    )
    manifest_files.append(_write_json(output_dir, "09-wave-approve.json", approved))
    _assert(
        approved["wave"]["state"] == "APPROVED_WITH_EXCEPTIONS",
        "mixed wave approval did not preserve exceptions",
    )

    staged = _json(
        _request(
            client,
            "POST",
            f"/api/v1/rebalance/waves/{wave_id}/stage",
            expected_status=200,
            json_body={
                "actor_id": "rfc0041_evidence",
                "reason_code": "RFC0041_LIVE_PROOF_STAGED",
                "comment": "Staged approved item only.",
            },
            headers={"X-Correlation-Id": f"corr-rfc0041-stage-{token}"},
        )
    )
    manifest_files.append(_write_json(output_dir, "10-wave-stage.json", staged))
    _assert(staged["wave"]["state"] == "STAGED", "wave did not stage approved item")

    handoff = _json(
        _request(
            client,
            "POST",
            f"/api/v1/rebalance/waves/{wave_id}/handoff",
            expected_status=200,
            json_body={
                "actor_id": "rfc0041_evidence",
                "reason_code": "RFC0041_LIVE_PROOF_HANDOFF",
                "comment": "Prepared internal operations handoff evidence.",
            },
            headers={"X-Correlation-Id": f"corr-rfc0041-handoff-{token}"},
        )
    )
    manifest_files.append(_write_json(output_dir, "11-wave-handoff.json", handoff))
    handoff_refs = cast(list[dict[str, Any]], handoff["wave"]["handoff_refs"])
    _assert(handoff["wave"]["state"] == "HANDOFF_READY", "wave did not reach handoff-ready state")
    _assert(
        handoff_refs and handoff_refs[0]["external_execution_claimed"] is False,
        "handoff must not claim external execution",
    )

    detail = _json(
        _request(client, "GET", f"/api/v1/rebalance/waves/{wave_id}", expected_status=200)
    )
    items = _json(
        _request(client, "GET", f"/api/v1/rebalance/waves/{wave_id}/items", expected_status=200)
    )
    proof_posture = _json(
        _request(
            client, "GET", f"/api/v1/rebalance/waves/{wave_id}/proof-pack", expected_status=200
        )
    )
    supportability = _json(
        _request(
            client, "GET", f"/api/v1/rebalance/waves/{wave_id}/supportability", expected_status=200
        )
    )
    search = _json(
        _request(
            client,
            "GET",
            "/api/v1/rebalance/waves",
            expected_status=200,
            params={
                "state": "HANDOFF_READY",
                "trigger_type": "EXPLICIT_PORTFOLIO_LIST",
                "as_of_date": "2026-05-03",
                "supportability_state": "blocked",
            },
        )
    )
    manifest_files.append(_write_json(output_dir, "12-wave-detail.json", detail))
    manifest_files.append(_write_json(output_dir, "13-wave-items.json", items))
    manifest_files.append(_write_json(output_dir, "14-wave-proof-pack-posture.json", proof_posture))
    manifest_files.append(_write_json(output_dir, "15-wave-supportability.json", supportability))
    manifest_files.append(_write_json(output_dir, "16-wave-search.json", search))

    _assert(detail["wave"]["wave_id"] == wave_id, "detail did not return created wave")
    _assert(len(items["items"]) == 4, "items endpoint did not return all wave items")
    _assert(
        proof_posture["linked_item_count"] == 1, "proof-pack posture did not include linked proof"
    )
    _assert(
        proof_posture["external_execution_claimed"] is False,
        "proof posture claimed external execution",
    )
    _assert(
        supportability["supportability_state"] == "blocked",
        "supportability should remain blocked because blocked exceptions are visible",
    )
    _assert(
        any(item["wave_id"] == wave_id for item in search["items"]),
        "search did not return the handoff-ready wave",
    )

    cancel_request = _wave_request(f"{token}-cancel")
    cancel_request["portfolios"] = [{"portfolio_id": "PB_SG_GLOBAL_BAL_001"}]
    cancel_created = _json(
        _request(
            client,
            "POST",
            "/api/v1/rebalance/waves",
            expected_status=201,
            json_body=cancel_request,
            headers={
                "Idempotency-Key": f"rfc0041-wave-cancel-{token}",
                "X-Correlation-Id": f"corr-rfc0041-cancel-create-{token}",
            },
        )
    )
    cancel_wave_id = str(cancel_created["wave"]["wave_id"])
    cancelled = _json(
        _request(
            client,
            "POST",
            f"/api/v1/rebalance/waves/{cancel_wave_id}/cancel",
            expected_status=200,
            json_body={
                "actor_id": "rfc0041_evidence",
                "reason_code": "RFC0041_LIVE_PROOF_CANCELLED",
                "comment": "Cancelled separate proof wave before downstream work.",
            },
            headers={"X-Correlation-Id": f"corr-rfc0041-cancel-{token}"},
        )
    )
    manifest_files.append(_write_json(output_dir, "16b-wave-cancel.json", cancelled))
    _assert(cancelled["wave"]["state"] == "CANCELLED", "cancel proof wave did not cancel")
    _assert(
        cancelled["wave"]["items"][0]["diagnostics"]["external_execution_claimed"] is False,
        "cancelled wave item must not claim external execution",
    )

    return {
        "wave_id": wave_id,
        "cancel_wave_id": cancel_wave_id,
        "proof_pack_id": proof_pack_id,
        "alternative_set_id": alternative_set_id,
        "selected_alternative_id": selected_alternative_id,
        "final_wave_state": handoff["wave"]["state"],
        "cancel_wave_state": cancelled["wave"]["state"],
        "final_item_state_counts": handoff["wave"]["aggregate_metrics"]["state_counts"],
        "source_analytics": handoff["wave"]["aggregate_metrics"]["source_analytics"],
        "supportability_state": supportability["supportability_state"],
        "supportability_reason": supportability["reason"],
        "proof_pack_linked_item_count": proof_posture["linked_item_count"],
        "handoff_ref_count": len(handoff_refs),
        "external_execution_claimed": proof_posture["external_execution_claimed"],
    }


def _openapi_certification(client: httpx.Client) -> dict[str, Any]:
    openapi = _json(_request(client, "GET", "/openapi.json", expected_status=200))
    required_paths = {
        "/api/v1/rebalance/waves": {"get", "post"},
        "/api/v1/rebalance/waves/preview": {"post"},
        "/api/v1/rebalance/waves/{wave_id}": {"get"},
        "/api/v1/rebalance/waves/{wave_id}/items": {"get"},
        "/api/v1/rebalance/waves/{wave_id}/source-check": {"post"},
        "/api/v1/rebalance/waves/{wave_id}/simulate": {"post"},
        "/api/v1/rebalance/waves/{wave_id}/items/{wave_item_id}/select": {"post"},
        "/api/v1/rebalance/waves/{wave_id}/approve": {"post"},
        "/api/v1/rebalance/waves/{wave_id}/stage": {"post"},
        "/api/v1/rebalance/waves/{wave_id}/handoff": {"post"},
        "/api/v1/rebalance/waves/{wave_id}/cancel": {"post"},
        "/api/v1/rebalance/waves/{wave_id}/proof-pack": {"get"},
        "/api/v1/rebalance/waves/{wave_id}/supportability": {"get"},
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
            if operation.get("tags") != ["lotus-manage Rebalance Waves"]:
                weak.append(f"{method.upper()} {path} tag")
            if not operation.get("summary") or not operation.get("description"):
                weak.append(f"{method.upper()} {path} summary/description")
            responses = cast(dict[str, Any], operation.get("responses", {}))
            if not responses:
                weak.append(f"{method.upper()} {path} responses")
            for status_code, response in responses.items():
                if not cast(dict[str, Any], response).get("description"):
                    weak.append(f"{method.upper()} {path} {status_code} response description")
    return {
        "required_path_count": len(required_paths),
        "missing": missing,
        "weak": weak,
        "passed": missing == [] and weak == [],
    }


def _aggregate_reconciliation(lifecycle: dict[str, Any]) -> dict[str, Any]:
    counts = cast(dict[str, int], lifecycle["final_item_state_counts"])
    source_analytics = cast(list[dict[str, Any]], lifecycle["source_analytics"])
    source_families = {entry["source_family"]: entry for entry in source_analytics}
    item_total = sum(counts.values())
    ready_total = counts.get("HANDOFF_READY", 0)
    blocked_total = counts.get("SOURCE_BLOCKED", 0) + counts.get("SIMULATION_BLOCKED", 0)
    return {
        "state_counts": counts,
        "item_total": item_total,
        "ready_total": ready_total,
        "blocked_total": blocked_total,
        "source_analytics_families": sorted(source_families),
        "risk_source_state": source_families.get("RISK", {}).get("supportability_state"),
        "performance_source_state": source_families.get("PERFORMANCE", {}).get(
            "supportability_state"
        ),
        "passed": item_total == 4
        and ready_total == 1
        and blocked_total == 1
        and source_families.get("RISK", {}).get("supportability_state") == "READY"
        and source_families.get("PERFORMANCE", {}).get("supportability_state") == "DEGRADED"
        and lifecycle["external_execution_claimed"] is False,
    }


def build_critical_review(manifest: dict[str, Any]) -> dict[str, Any]:
    lifecycle = cast(dict[str, Any], manifest["lifecycle"])
    openapi = cast(dict[str, Any], manifest["openapi_certification"])
    reconciliation = cast(dict[str, Any], manifest["aggregate_reconciliation"])
    checks = {
        "wave_reached_handoff_ready": lifecycle["final_wave_state"] == "HANDOFF_READY",
        "blocked_exceptions_remain_visible": lifecycle["supportability_state"] == "blocked",
        "proof_pack_linkage_present": lifecycle["proof_pack_linked_item_count"] == 1,
        "source_owned_analytics_aggregated": (
            reconciliation["risk_source_state"] == "READY"
            and reconciliation["performance_source_state"] == "DEGRADED"
        ),
        "handoff_no_external_execution_claim": lifecycle["external_execution_claimed"] is False,
        "cancel_transition_proven": lifecycle["cancel_wave_state"] == "CANCELLED",
        "openapi_certification_passed": openapi["passed"] is True,
        "aggregate_reconciliation_passed": reconciliation["passed"] is True,
    }
    findings = [
        {
            "finding_id": "RFC0041-LIVE-001",
            "severity": "info",
            "status": "passed" if checks["wave_reached_handoff_ready"] else "failed",
            "summary": "Wave lifecycle was driven through preview, create, source-check, simulation, selection, approval, staging, and handoff.",
            "evidence": lifecycle["wave_id"],
        },
        {
            "finding_id": "RFC0041-LIVE-002",
            "severity": "info",
            "status": "passed" if checks["blocked_exceptions_remain_visible"] else "failed",
            "summary": "Blocked exceptions remain visible after eligible item handoff; manage does not hide partial-completion risk.",
            "evidence": lifecycle["supportability_reason"],
        },
        {
            "finding_id": "RFC0041-LIVE-003",
            "severity": "info",
            "status": "passed" if checks["proof_pack_linkage_present"] else "failed",
            "summary": "Selected wave item links to an RFC-0040 proof pack generated through the proof-pack authority.",
            "evidence": lifecycle["proof_pack_id"],
        },
        {
            "finding_id": "RFC0041-LIVE-004",
            "severity": "info",
            "status": "passed" if checks["source_owned_analytics_aggregated"] else "failed",
            "summary": "Wave aggregate metrics preserve source-owned risk and performance analytics supportability without recalculating analytics in manage.",
            "evidence": reconciliation["source_analytics_families"],
        },
        {
            "finding_id": "RFC0041-LIVE-005",
            "severity": "info",
            "status": "passed" if checks["handoff_no_external_execution_claim"] else "failed",
            "summary": "Operations handoff evidence is internal-only and carries no external execution claim.",
            "evidence": {"handoff_ref_count": lifecycle["handoff_ref_count"]},
        },
        {
            "finding_id": "RFC0041-LIVE-006",
            "severity": "info",
            "status": "passed" if checks["cancel_transition_proven"] else "failed",
            "summary": "A separate durable wave was cancelled before downstream work and preserved the no-external-execution boundary.",
            "evidence": lifecycle["cancel_wave_id"],
        },
        {
            "finding_id": "RFC0041-LIVE-007",
            "severity": "controlled_gap",
            "status": "accepted_boundary",
            "summary": "Gateway and Workbench realization are planned through downstream RFC-0098 addenda; manage live proof does not claim UI product support.",
            "evidence": "lotus-gateway PR #183 and lotus-workbench PR #143 merged RFC realization direction.",
        },
    ]
    return {
        "rfc": "RFC-0041",
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "source_manifest": manifest["output_dir"],
        "result": "passed" if all(checks.values()) else "failed",
        "checks": checks,
        "findings": findings,
    }


def _render_critical_review(review: dict[str, Any]) -> str:
    lines = [
        "# RFC-0041 Live Proof Critical Review",
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

        lifecycle = _generate_wave_lifecycle(client, output_dir, manifest_files, token)
        openapi_certification = _openapi_certification(client)
        manifest_files.append(
            _write_json(output_dir, "17-openapi-certification.json", openapi_certification)
        )
        aggregate_reconciliation = _aggregate_reconciliation(lifecycle)
        manifest_files.append(
            _write_json(output_dir, "18-aggregate-reconciliation.json", aggregate_reconciliation)
        )

    manifest = {
        "rfc": "RFC-0041",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "base_url": base_url,
        "output_dir": output_dir.relative_to(ROOT).as_posix(),
        "lifecycle": lifecycle,
        "openapi_certification": openapi_certification,
        "aggregate_reconciliation": aggregate_reconciliation,
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
    parser = argparse.ArgumentParser(description="Generate RFC-0041 wave orchestration evidence.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8001")
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    args = parser.parse_args()
    manifest = generate_evidence(args.base_url, Path(args.output_root))
    print(_stable_json(manifest))


if __name__ == "__main__":
    main()
