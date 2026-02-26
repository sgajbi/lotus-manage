import argparse
import json
import uuid
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
DEMO_DIR = ROOT / "docs" / "demo"


class DemoRunError(RuntimeError):
    pass


def _load_json(filename: str) -> dict[str, Any]:
    return json.loads((DEMO_DIR / filename).read_text(encoding="utf-8"))


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise DemoRunError(message)


def _run_scenario(
    client: httpx.Client,
    *,
    name: str,
    method: str,
    path: str,
    expected_http: int,
    payload_file: str | None = None,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    payload = _load_json(payload_file) if payload_file else None
    response = client.request(method, path, json=payload, headers=headers)
    _assert(
        response.status_code == expected_http,
        f"{name}: expected HTTP {expected_http}, got {response.status_code}, body={response.text}",
    )
    if response.content:
        return response.json()
    return {}


def run_demo_pack(base_url: str) -> None:
    timeout = httpx.Timeout(30.0)
    run_token = uuid.uuid4().hex[:8]
    corr_27 = f"live-corr-27-supportability-{run_token}"
    idem_27 = f"live-demo-27-supportability-{run_token}"
    corr_29 = f"live-corr-29-workflow-disabled-{run_token}"
    idem_29 = f"live-demo-29-workflow-disabled-{run_token}"
    idem_31 = f"live-demo-31-policy-pack-{run_token}"
    corr_32 = f"live-corr-32-support-summary-{run_token}"
    idem_32 = f"live-demo-32-support-summary-{run_token}"
    lifecycle_idem_20 = f"live-demo-lifecycle-20-{run_token}"
    with httpx.Client(base_url=base_url, timeout=timeout) as client:
        # lotus-manage single-run demos
        dpm_files = [
            "01_standard_drift.json",
            "02_sell_to_fund.json",
            "03_multi_currency_fx.json",
            "04_safety_sell_only.json",
            "05_safety_hard_block_price.json",
            "06_tax_aware_hifo.json",
            "07_settlement_overdraft_block.json",
            "08_solver_mode.json",
        ]
        for index, expected in [
            (1, "READY"),
            (2, "READY"),
            (3, "READY"),
            (4, "PENDING_REVIEW"),
            (5, "BLOCKED"),
            (6, "READY"),
            (7, "BLOCKED"),
            (8, "READY"),
        ]:
            file_name = dpm_files[index - 1]
            body = _run_scenario(
                client,
                name=file_name,
                method="POST",
                path="/rebalance/simulate",
                expected_http=200,
                payload_file=file_name,
                headers={
                    "Idempotency-Key": f"live-demo-{index:02d}",
                    "X-Correlation-Id": f"live-corr-{index:02d}-{run_token}",
                },
            )
            _assert(
                body.get("status") == expected,
                f"{file_name}: unexpected status {body.get('status')}",
            )

        supportability = _run_scenario(
            client,
            name="27_dpm_supportability_artifact_flow.json",
            method="POST",
            path="/rebalance/simulate",
            expected_http=200,
            payload_file="27_dpm_supportability_artifact_flow.json",
            headers={
                "Idempotency-Key": idem_27,
                "X-Correlation-Id": corr_27,
            },
        )
        run_id = supportability["rebalance_run_id"]

        by_run = _run_scenario(
            client,
            name="27_get_run",
            method="GET",
            path=f"/rebalance/runs/{run_id}",
            expected_http=200,
        )
        _assert(by_run["rebalance_run_id"] == run_id, "27: run lookup mismatch")

        by_correlation = _run_scenario(
            client,
            name="27_get_run_by_correlation",
            method="GET",
            path=f"/rebalance/runs/by-correlation/{corr_27}",
            expected_http=200,
        )
        _assert(by_correlation["rebalance_run_id"] == run_id, "27: correlation lookup mismatch")

        by_idempotency = _run_scenario(
            client,
            name="27_get_run_by_idempotency",
            method="GET",
            path=f"/rebalance/runs/idempotency/{idem_27}",
            expected_http=200,
        )
        _assert(by_idempotency["rebalance_run_id"] == run_id, "27: idempotency lookup mismatch")

        artifact_one = _run_scenario(
            client,
            name="27_get_artifact_one",
            method="GET",
            path=f"/rebalance/runs/{run_id}/artifact",
            expected_http=200,
        )
        artifact_two = _run_scenario(
            client,
            name="27_get_artifact_two",
            method="GET",
            path=f"/rebalance/runs/{run_id}/artifact",
            expected_http=200,
        )
        _assert(
            artifact_one["evidence"]["hashes"]["artifact_hash"]
            == artifact_two["evidence"]["hashes"]["artifact_hash"],
            "27: artifact hash not deterministic",
        )

        # Batch demo
        batch = _run_scenario(
            client,
            name="09_batch_what_if_analysis.json",
            method="POST",
            path="/rebalance/analyze",
            expected_http=200,
            payload_file="09_batch_what_if_analysis.json",
        )
        _assert(
            set(batch.get("results", {}).keys()) == {"baseline", "tax_budget", "settlement_guard"},
            "09_batch_what_if_analysis.json: unexpected scenario keys",
        )

        async_batch = _run_scenario(
            client,
            name="26_dpm_async_batch_analysis.json",
            method="POST",
            path="/rebalance/analyze/async",
            expected_http=202,
            payload_file="26_dpm_async_batch_analysis.json",
            headers={"X-Correlation-Id": "demo-corr-26-async"},
        )
        operation_id = async_batch["operation_id"]
        operation = _run_scenario(
            client,
            name="get_async_operation",
            method="GET",
            path=f"/rebalance/operations/{operation_id}",
            expected_http=200,
        )
        _assert(operation["status"] == "SUCCEEDED", "26: async operation did not succeed")
        _assert(
            operation.get("result", {}).get("warnings") == ["PARTIAL_BATCH_FAILURE"],
            "26: expected PARTIAL_BATCH_FAILURE warning",
        )
        _assert(
            set(operation.get("result", {}).get("failed_scenarios", {}).keys())
            == {"invalid_options"},
            "26: expected invalid_options failed scenario",
        )

        manual_guard = _run_scenario(
            client,
            name="28_dpm_async_manual_execute_guard.json",
            method="POST",
            path="/rebalance/analyze/async",
            expected_http=202,
            payload_file="28_dpm_async_manual_execute_guard.json",
            headers={"X-Correlation-Id": "demo-corr-28-async-inline"},
        )
        manual_execute_conflict = client.post(
            f"/rebalance/operations/{manual_guard['operation_id']}/execute"
        )
        _assert(
            manual_execute_conflict.status_code == 409,
            "28: expected 409 when executing non-pending operation",
        )
        _assert(
            manual_execute_conflict.json().get("detail") == "DPM_ASYNC_OPERATION_NOT_EXECUTABLE",
            "28: unexpected non-executable detail",
        )

        workflow_disabled = _run_scenario(
            client,
            name="29_dpm_workflow_gate_disabled_contract.json",
            method="POST",
            path="/rebalance/simulate",
            expected_http=200,
            payload_file="29_dpm_workflow_gate_disabled_contract.json",
            headers={
                "Idempotency-Key": idem_29,
                "X-Correlation-Id": corr_29,
            },
        )
        workflow_run_id = workflow_disabled["rebalance_run_id"]
        workflow_disabled_state = client.get(f"/rebalance/runs/{workflow_run_id}/workflow")
        _assert(
            workflow_disabled_state.status_code == 404,
            "29: expected workflow state endpoint to be disabled by default",
        )
        _assert(
            workflow_disabled_state.json().get("detail") == "DPM_WORKFLOW_DISABLED",
            "29: unexpected workflow disabled detail",
        )
        workflow_disabled_history = client.get(
            f"/rebalance/runs/{workflow_run_id}/workflow/history"
        )
        _assert(
            workflow_disabled_history.status_code == 404,
            "29: expected workflow history endpoint to be disabled by default",
        )
        _assert(
            workflow_disabled_history.json().get("detail") == "DPM_WORKFLOW_DISABLED",
            "29: unexpected workflow history disabled detail",
        )

        policy_headers = {
            "X-Policy-Pack-Id": "dpm_standard_v1",
            "X-Tenant-Policy-Pack-Id": "dpm_tenant_default_v1",
            "X-Tenant-Id": "tenant_001",
        }
        policy_simulate = _run_scenario(
            client,
            name="31_dpm_policy_pack_supportability_diagnostics.json",
            method="POST",
            path="/rebalance/simulate",
            expected_http=200,
            payload_file="31_dpm_policy_pack_supportability_diagnostics.json",
            headers={
                "Idempotency-Key": idem_31,
                **policy_headers,
            },
        )
        _assert(
            policy_simulate.get("status") in {"READY", "PENDING_REVIEW", "BLOCKED"},
            "31: simulate status must be valid domain status",
        )

        effective_policy = _run_scenario(
            client,
            name="31_get_effective_policy_pack",
            method="GET",
            path="/rebalance/policies/effective",
            expected_http=200,
            headers=policy_headers,
        )
        _assert(
            {"enabled", "selected_policy_pack_id", "source"}.issubset(effective_policy.keys()),
            "31: effective policy response missing expected fields",
        )

        catalog = _run_scenario(
            client,
            name="31_get_policy_catalog",
            method="GET",
            path="/rebalance/policies/catalog",
            expected_http=200,
            headers=policy_headers,
        )
        _assert(
            {
                "enabled",
                "total",
                "selected_policy_pack_id",
                "selected_policy_pack_present",
                "selected_policy_pack_source",
                "items",
            }.issubset(catalog.keys()),
            "31: policy catalog response missing expected fields",
        )

        _run_scenario(
            client,
            name="32_dpm_supportability_summary_metrics.json",
            method="POST",
            path="/rebalance/simulate",
            expected_http=200,
            payload_file="32_dpm_supportability_summary_metrics.json",
            headers={
                "Idempotency-Key": idem_32,
                "X-Correlation-Id": corr_32,
            },
        )
        support_summary = _run_scenario(
            client,
            name="32_get_supportability_summary",
            method="GET",
            path="/rebalance/supportability/summary",
            expected_http=200,
        )
        _assert(
            {
                "store_backend",
                "retention_days",
                "run_count",
                "operation_count",
                "operation_status_counts",
                "run_status_counts",
                "workflow_decision_count",
                "workflow_action_counts",
                "workflow_reason_code_counts",
                "lineage_edge_count",
            }.issubset(support_summary.keys()),
            "32: supportability summary response missing expected fields",
        )
        _assert(
            support_summary.get("run_count", 0) >= 1,
            "32: supportability summary should include at least one run",
        )

        # Advisory simulate demos
        advisory_expected = {
            "10_advisory_proposal_simulate.json": "READY",
            "11_advisory_auto_funding_single_ccy.json": "READY",
            "12_advisory_partial_funding.json": "READY",
            "13_advisory_missing_fx_blocked.json": "BLOCKED",
            "14_advisory_drift_asset_class.json": "READY",
            "15_advisory_drift_instrument.json": "READY",
            "16_advisory_suitability_resolved_single_position.json": "READY",
            "17_advisory_suitability_new_issuer_breach.json": "READY",
            "18_advisory_suitability_sell_only_violation.json": "BLOCKED",
        }
        for file_name, expected in advisory_expected.items():
            body = _run_scenario(
                client,
                name=file_name,
                method="POST",
                path="/rebalance/proposals/simulate",
                expected_http=200,
                payload_file=file_name,
                headers={"Idempotency-Key": f"live-{file_name}"},
            )
            _assert(
                body.get("status") == expected,
                f"{file_name}: unexpected status {body.get('status')}",
            )

        artifact = _run_scenario(
            client,
            name="19_advisory_proposal_artifact.json",
            method="POST",
            path="/rebalance/proposals/artifact",
            expected_http=200,
            payload_file="19_advisory_proposal_artifact.json",
            headers={"Idempotency-Key": "live-demo-artifact-19"},
        )
        _assert(artifact.get("status") == "READY", "19_advisory_proposal_artifact.json: not READY")
        _assert(
            artifact.get("evidence_bundle", {})
            .get("hashes", {})
            .get("artifact_hash", "")
            .startswith("sha256:"),
            "19_advisory_proposal_artifact.json: missing artifact hash",
        )

        # Lifecycle flow demos
        create = _run_scenario(
            client,
            name="20_advisory_proposal_persist_create.json",
            method="POST",
            path="/rebalance/proposals",
            expected_http=200,
            payload_file="20_advisory_proposal_persist_create.json",
            headers={"Idempotency-Key": lifecycle_idem_20},
        )
        proposal_id = create["proposal"]["proposal_id"]
        _assert(create["proposal"]["current_state"] == "DRAFT", "20: unexpected lifecycle state")

        version = _run_scenario(
            client,
            name="21_advisory_proposal_new_version.json",
            method="POST",
            path=f"/rebalance/proposals/{proposal_id}/versions",
            expected_http=200,
            payload_file="21_advisory_proposal_new_version.json",
        )
        _assert(version["proposal"]["current_version_no"] == 2, "21: version increment failed")

        transition = _run_scenario(
            client,
            name="22_advisory_proposal_transition_to_compliance.json",
            method="POST",
            path=f"/rebalance/proposals/{proposal_id}/transitions",
            expected_http=200,
            payload_file="22_advisory_proposal_transition_to_compliance.json",
        )
        _assert(transition["current_state"] == "COMPLIANCE_REVIEW", "22: unexpected state")

        compliance = _run_scenario(
            client,
            name="24_advisory_proposal_approval_compliance.json",
            method="POST",
            path=f"/rebalance/proposals/{proposal_id}/approvals",
            expected_http=200,
            payload_file="24_advisory_proposal_approval_compliance.json",
        )
        _assert(compliance["current_state"] == "AWAITING_CLIENT_CONSENT", "24: unexpected state")

        consent = _run_scenario(
            client,
            name="23_advisory_proposal_approval_client_consent.json",
            method="POST",
            path=f"/rebalance/proposals/{proposal_id}/approvals",
            expected_http=200,
            payload_file="23_advisory_proposal_approval_client_consent.json",
        )
        _assert(consent["current_state"] == "EXECUTION_READY", "23: unexpected state")

        executed = _run_scenario(
            client,
            name="25_advisory_proposal_transition_executed.json",
            method="POST",
            path=f"/rebalance/proposals/{proposal_id}/transitions",
            expected_http=200,
            payload_file="25_advisory_proposal_transition_executed.json",
        )
        _assert(executed["current_state"] == "EXECUTED", "25: unexpected state")

        listed = _run_scenario(
            client,
            name="list_proposals",
            method="GET",
            path="/rebalance/proposals?portfolio_id=pf_demo_lifecycle_1&limit=5",
            expected_http=200,
        )
        _assert(len(listed.get("items", [])) >= 1, "list_proposals: expected at least one item")

    print(f"Demo pack validation passed for {base_url}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run live demo pack scenarios against API base URL"
    )
    parser.add_argument(
        "--base-url", required=True, help="API base URL, for example http://127.0.0.1:8001"
    )
    args = parser.parse_args()
    run_demo_pack(args.base_url)
