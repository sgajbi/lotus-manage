# DPM Rebalance Engine Demo Scenarios

This folder contains JSON input files demonstrating key capabilities of the DPM Rebalance Engine. Run these scenarios through the API endpoints.

## Running Scenarios

### API Usage

For simulate demos, POST the content of a scenario file to `/rebalance/simulate` with `Idempotency-Key`.

Example:
```bash
curl -X POST "http://127.0.0.1:8000/rebalance/simulate" -H "Content-Type: application/json" -H "Idempotency-Key: demo-01" --data-binary "@docs/demo/01_standard_drift.json"
```

For batch what-if demos, POST to `/rebalance/analyze`:
```bash
curl -X POST "http://127.0.0.1:8000/rebalance/analyze" -H "Content-Type: application/json" --data-binary "@docs/demo/09_batch_what_if_analysis.json"
```

For asynchronous batch what-if demos, POST to `/rebalance/analyze/async` and retrieve operation status:
```bash
curl -X POST "http://127.0.0.1:8000/rebalance/analyze/async" -H "Content-Type: application/json" -H "X-Correlation-Id: demo-corr-26-async" --data-binary "@docs/demo/26_dpm_async_batch_analysis.json"
curl -X GET "http://127.0.0.1:8000/rebalance/operations?status=SUCCEEDED&operation_type=ANALYZE_SCENARIOS&limit=20"
curl -X GET "http://127.0.0.1:8000/rebalance/operations/by-correlation/demo-corr-26-async"
```

For DPM policy-pack resolution supportability:
```bash
curl -X GET "http://127.0.0.1:8000/rebalance/policies/effective" -H "X-Policy-Pack-Id: dpm_standard_v1" -H "X-Tenant-Policy-Pack-Id: dpm_tenant_default_v1" -H "X-Tenant-Id: tenant_001"
```

For DPM policy-pack catalog and selected-pack presence diagnostics:
```bash
curl -X GET "http://127.0.0.1:8000/rebalance/policies/catalog" -H "X-Policy-Pack-Id: dpm_standard_v1" -H "X-Tenant-Policy-Pack-Id: dpm_tenant_default_v1" -H "X-Tenant-Id: tenant_001"
```

For DPM policy-pack supportability + diagnostics scenario:
```bash
curl -X POST "http://127.0.0.1:8000/rebalance/simulate" -H "Content-Type: application/json" -H "Idempotency-Key: demo-31-policy-pack" -H "X-Policy-Pack-Id: dpm_standard_v1" -H "X-Tenant-Policy-Pack-Id: dpm_tenant_default_v1" -H "X-Tenant-Id: tenant_001" --data-binary "@docs/demo/31_dpm_policy_pack_supportability_diagnostics.json"
curl -X GET "http://127.0.0.1:8000/rebalance/policies/effective" -H "X-Policy-Pack-Id: dpm_standard_v1" -H "X-Tenant-Policy-Pack-Id: dpm_tenant_default_v1" -H "X-Tenant-Id: tenant_001"
curl -X GET "http://127.0.0.1:8000/rebalance/policies/catalog" -H "X-Policy-Pack-Id: dpm_standard_v1" -H "X-Tenant-Policy-Pack-Id: dpm_tenant_default_v1" -H "X-Tenant-Id: tenant_001"
```

For DPM supportability summary metrics scenario:
```bash
curl -X POST "http://127.0.0.1:8000/rebalance/simulate" -H "Content-Type: application/json" -H "Idempotency-Key: demo-32-support-summary" -H "X-Correlation-Id: demo-corr-32-support-summary" --data-binary "@docs/demo/32_dpm_supportability_summary_metrics.json"
curl -X GET "http://127.0.0.1:8000/rebalance/supportability/summary"
```

For DPM policy-pack turnover override demo (requires `DPM_POLICY_PACKS_ENABLED=true`):
```bash
export DPM_POLICY_PACK_CATALOG_JSON='{"dpm_standard_v1":{"version":"1","turnover_policy":{"max_turnover_pct":"0.01"},"tax_policy":{"enable_tax_awareness":true,"max_realized_capital_gains":"100"}}}'
export DPM_TENANT_POLICY_PACK_RESOLUTION_ENABLED=true
export DPM_TENANT_POLICY_PACK_MAP_JSON='{"tenant_001":"dpm_standard_v1"}'
curl -X POST "http://127.0.0.1:8000/rebalance/simulate" -H "Content-Type: application/json" -H "Idempotency-Key: demo-policy-pack-turnover-1" -H "X-Policy-Pack-Id: dpm_standard_v1" --data-binary "@docs/demo/01_standard_drift.json"
```

Settlement-policy override example:
```bash
export DPM_POLICY_PACK_CATALOG_JSON='{"dpm_standard_v1":{"version":"1","settlement_policy":{"enable_settlement_awareness":true,"settlement_horizon_days":3}}}'
curl -X POST "http://127.0.0.1:8000/rebalance/simulate" -H "Content-Type: application/json" -H "Idempotency-Key: demo-policy-pack-settlement-1" -H "X-Policy-Pack-Id: dpm_standard_v1" --data-binary "@docs/demo/07_settlement_overdraft_block.json"
```

Constraint-policy override example:
```bash
export DPM_POLICY_PACK_CATALOG_JSON='{"dpm_standard_v1":{"version":"1","constraint_policy":{"single_position_max_weight":"0.25","group_constraints":{"sector:TECH":{"max_weight":"0.20"}}}}}'
curl -X POST "http://127.0.0.1:8000/rebalance/simulate" -H "Content-Type: application/json" -H "Idempotency-Key: demo-policy-pack-constraints-1" -H "X-Policy-Pack-Id: dpm_standard_v1" --data-binary "@docs/demo/01_standard_drift.json"
```

Workflow-policy override example:
```bash
export DPM_POLICY_PACK_CATALOG_JSON='{"dpm_standard_v1":{"version":"1","workflow_policy":{"enable_workflow_gates":false,"workflow_requires_client_consent":true,"client_consent_already_obtained":true}}}'
curl -X POST "http://127.0.0.1:8000/rebalance/simulate" -H "Content-Type: application/json" -H "Idempotency-Key: demo-policy-pack-workflow-1" -H "X-Policy-Pack-Id: dpm_standard_v1" --data-binary "@docs/demo/01_standard_drift.json"
```

Idempotency-policy override example:
```bash
export DPM_IDEMPOTENCY_REPLAY_ENABLED=true
export DPM_POLICY_PACK_CATALOG_JSON='{"dpm_standard_v1":{"version":"1","idempotency_policy":{"replay_enabled":false}}}'
curl -X POST "http://127.0.0.1:8000/rebalance/simulate" -H "Content-Type: application/json" -H "Idempotency-Key: demo-policy-pack-idempotency-1" -H "X-Policy-Pack-Id: dpm_standard_v1" --data-binary "@docs/demo/01_standard_drift.json"
curl -X POST "http://127.0.0.1:8000/rebalance/simulate" -H "Content-Type: application/json" -H "Idempotency-Key: demo-policy-pack-idempotency-1" -H "X-Policy-Pack-Id: dpm_standard_v1" --data-binary "@docs/demo/01_standard_drift.json"
```

For DPM supportability and deterministic artifact retrieval flow:
```bash
curl -X POST "http://127.0.0.1:8000/rebalance/simulate" -H "Content-Type: application/json" -H "Idempotency-Key: demo-27-supportability" -H "X-Correlation-Id: demo-corr-27-supportability" --data-binary "@docs/demo/27_dpm_supportability_artifact_flow.json"
curl -X GET "http://127.0.0.1:8000/rebalance/runs?status=READY&portfolio_id=pf_demo_support_27&limit=20"
curl -X GET "http://127.0.0.1:8000/rebalance/runs?request_hash=<request_hash>&limit=20"
curl -X GET "http://127.0.0.1:8000/rebalance/runs/by-request-hash/<url_encoded_request_hash>"
curl -X GET "http://127.0.0.1:8000/rebalance/supportability/summary"
curl -X GET "http://127.0.0.1:8000/rebalance/runs/by-correlation/demo-corr-27-supportability"
curl -X GET "http://127.0.0.1:8000/rebalance/runs/idempotency/demo-27-supportability"
curl -X GET "http://127.0.0.1:8000/rebalance/runs/<rebalance_run_id>/support-bundle"
curl -X GET "http://127.0.0.1:8000/rebalance/runs/by-correlation/<correlation_id>/support-bundle"
curl -X GET "http://127.0.0.1:8000/rebalance/runs/idempotency/<idempotency_key>/support-bundle"
curl -X GET "http://127.0.0.1:8000/rebalance/runs/by-operation/<operation_id>/support-bundle"
curl -X GET "http://127.0.0.1:8000/rebalance/runs/<rebalance_run_id>/support-bundle?include_artifact=false&include_async_operation=false&include_idempotency_history=false"
curl -X GET "http://127.0.0.1:8000/rebalance/runs/<rebalance_run_id>/artifact"
```

Retention can be enabled for supportability records with:
- `DPM_SUPPORTABILITY_RETENTION_DAYS=<positive_integer>`

For DPM lineage supportability (enabled when `DPM_LINEAGE_APIS_ENABLED=true`):
```bash
curl -X GET "http://127.0.0.1:8000/rebalance/lineage/<entity_id>"
```

For DPM idempotency history supportability (enabled when `DPM_IDEMPOTENCY_HISTORY_APIS_ENABLED=true`):
```bash
curl -X GET "http://127.0.0.1:8000/rebalance/idempotency/<idempotency_key>/history"
```

For DPM workflow supportability endpoints (enabled only when `DPM_WORKFLOW_ENABLED=true`):
```bash
curl -X GET "http://127.0.0.1:8000/rebalance/runs/<rebalance_run_id>/workflow"
curl -X GET "http://127.0.0.1:8000/rebalance/runs/by-correlation/<correlation_id>/workflow"
curl -X GET "http://127.0.0.1:8000/rebalance/runs/idempotency/<idempotency_key>/workflow"
curl -X POST "http://127.0.0.1:8000/rebalance/runs/<rebalance_run_id>/workflow/actions" -H "Content-Type: application/json" -H "X-Correlation-Id: demo-corr-workflow-1" --data-binary '{"action":"APPROVE","reason_code":"REVIEW_APPROVED","actor_id":"reviewer_001"}'
curl -X POST "http://127.0.0.1:8000/rebalance/runs/by-correlation/<correlation_id>/workflow/actions" -H "Content-Type: application/json" -H "X-Correlation-Id: demo-corr-workflow-2" --data-binary '{"action":"REQUEST_CHANGES","reason_code":"NEEDS_DETAIL","actor_id":"reviewer_001"}'
curl -X POST "http://127.0.0.1:8000/rebalance/runs/idempotency/<idempotency_key>/workflow/actions" -H "Content-Type: application/json" -H "X-Correlation-Id: demo-corr-workflow-3" --data-binary '{"action":"REJECT","reason_code":"POLICY_REJECTED","actor_id":"reviewer_001"}'
curl -X GET "http://127.0.0.1:8000/rebalance/runs/<rebalance_run_id>/workflow/history"
curl -X GET "http://127.0.0.1:8000/rebalance/runs/by-correlation/<correlation_id>/workflow/history"
curl -X GET "http://127.0.0.1:8000/rebalance/runs/idempotency/<idempotency_key>/workflow/history"
curl -X GET "http://127.0.0.1:8000/rebalance/workflow/decisions?action=APPROVE&actor_id=reviewer_001&limit=20"
curl -X GET "http://127.0.0.1:8000/rebalance/workflow/decisions/by-correlation/<correlation_id>"
```

For advisory proposal simulation demos, POST to `/rebalance/proposals/simulate`:
```bash
curl -X POST "http://127.0.0.1:8000/rebalance/proposals/simulate" -H "Content-Type: application/json" -H "Idempotency-Key: demo-proposal-01" --data-binary "@docs/demo/10_advisory_proposal_simulate.json"
```

For advisory proposal artifact demos, POST to `/rebalance/proposals/artifact`:
```bash
curl -X POST "http://127.0.0.1:8000/rebalance/proposals/artifact" -H "Content-Type: application/json" -H "Idempotency-Key: demo-proposal-artifact-01" --data-binary "@docs/demo/19_advisory_proposal_artifact.json"
```

For advisory proposal persistence/lifecycle create demo, POST to `/rebalance/proposals`:
```bash
curl -X POST "http://127.0.0.1:8000/rebalance/proposals" -H "Content-Type: application/json" -H "Idempotency-Key: demo-proposal-persist-01" --data-binary "@docs/demo/20_advisory_proposal_persist_create.json"
```

For full live demo-pack validation (all scenarios, including lifecycle flow):
```bash
python scripts/run_demo_pack_live.py --base-url http://127.0.0.1:8001
python scripts/run_demo_pack_live.py --base-url http://127.0.0.1:8000
```

---

## Scenario Index

| File | Scenario | Expected Status | Key Feature |
| --- | --- | --- | --- |
| `01_standard_drift.json` | **Standard Rebalance** | `READY` | Simple Buy/Sell to align weights. |
| `02_sell_to_fund.json` | **Sell to Fund** | `READY` | Selling existing holdings to generate cash for purchases. |
| `03_multi_currency_fx.json` | **Multi-Currency** | `READY` | Auto-generation of FX Spot trades for foreign assets. |
| `04_safety_sell_only.json` | **Sell Only (Safety)** | `PENDING_REVIEW` | Prevents buying restricted assets; flags unallocated cash. |
| `05_safety_hard_block_price.json` | **DQ Block (Safety)** | `BLOCKED` | Halts execution due to missing price data. |
| `06_tax_aware_hifo.json` | **Tax-Aware HIFO** | `READY` | Tax-lot aware selling with gains budget control enabled. |
| `07_settlement_overdraft_block.json` | **Settlement Overdraft Block** | `BLOCKED` | Settlement-day cash ladder blocks run on projected overdraft. |
| `08_solver_mode.json` | **Solver Target Generation** | `READY` | Runs Stage-3 target generation in solver mode (`target_method=SOLVER`). |
| `09_batch_what_if_analysis.json` | **Batch What-If Analysis** | Mixed by scenario | Runs baseline/tax/settlement scenarios in one `/rebalance/analyze` call. |
| `10_advisory_proposal_simulate.json` | **Advisory Proposal Simulation** | `READY` | Simulates manual cash flows and manual trades in `/rebalance/proposals/simulate`. |
| `11_advisory_auto_funding_single_ccy.json` | **Advisory Auto-Funding (Single CCY)** | `READY` | Generates funding `FX_SPOT` and links BUY dependency. |
| `12_advisory_partial_funding.json` | **Advisory Partial Funding** | `READY` | Uses existing foreign cash first, then tops up with FX. |
| `13_advisory_missing_fx_blocked.json` | **Advisory Missing FX (Blocked)** | `BLOCKED` | Blocks advisory proposal when required FX funding pair is missing. |
| `14_advisory_drift_asset_class.json` | **Advisory Drift Analytics (Asset Class)** | `READY` | Returns `drift_analysis.asset_class` against inline `reference_model`. |
| `15_advisory_drift_instrument.json` | **Advisory Drift Analytics (Instrument)** | `READY` | Returns both asset-class and instrument drift with unmodeled exposures. |
| `16_advisory_suitability_resolved_single_position.json` | **Suitability Resolved Concentration** | `READY` | Returns a `RESOLVED` single-position issue after proposal trades. |
| `17_advisory_suitability_new_issuer_breach.json` | **Suitability New Issuer Breach** | `READY` | Returns a `NEW` high-severity issuer concentration issue and gate recommendation. |
| `18_advisory_suitability_sell_only_violation.json` | **Suitability Sell-Only Violation** | `BLOCKED` | Returns a `NEW` governance issue when proposal attempts BUY in `SELL_ONLY`. |
| `19_advisory_proposal_artifact.json` | **Advisory Proposal Artifact** | `READY` | Returns a deterministic proposal package from `/rebalance/proposals/artifact` with evidence bundle and hash. |
| `20_advisory_proposal_persist_create.json` | **Proposal Persist Create** | `DRAFT` lifecycle state | Creates persisted proposal aggregate + immutable version via `/rebalance/proposals`. |
| `21_advisory_proposal_new_version.json` | **Proposal New Version** | `DRAFT` lifecycle state | Creates immutable version `N+1` via `/rebalance/proposals/{proposal_id}/versions`. |
| `22_advisory_proposal_transition_to_compliance.json` | **Proposal Transition** | `COMPLIANCE_REVIEW` lifecycle state | Transitions proposal workflow using optimistic `expected_state`. |
| `23_advisory_proposal_approval_client_consent.json` | **Proposal Consent Approval** | `EXECUTION_READY` lifecycle state | Records structured client consent and emits workflow event. |
| `24_advisory_proposal_approval_compliance.json` | **Proposal Compliance Approval** | `AWAITING_CLIENT_CONSENT` lifecycle state | Records compliance approval and advances lifecycle. |
| `25_advisory_proposal_transition_executed.json` | **Proposal Execution Transition** | `EXECUTED` lifecycle state | Records execution confirmation transition from execution-ready state. |
| `26_dpm_async_batch_analysis.json` | **DPM Async Batch Analysis** | Async operation `SUCCEEDED` with partial-failure warning | Demonstrates `/rebalance/analyze/async` acceptance + operation lookup with `failed_scenarios` diagnostics. |
| `27_dpm_supportability_artifact_flow.json` | **DPM Supportability + Artifact Flow** | `READY` run + deterministic artifact hash | Demonstrates run lookup by run id/correlation/idempotency and deterministic retrieval from `/rebalance/runs/{rebalance_run_id}/artifact`. |
| `28_dpm_async_manual_execute_guard.json` | **DPM Async Manual Execute Guard** | Manual execute returns `409` on non-pending run | Demonstrates `/rebalance/operations/{operation_id}/execute` conflict guard when operation already completed inline. |
| `29_dpm_workflow_gate_disabled_contract.json` | **DPM Workflow Gate Default Guard** | Workflow endpoints return `404 DPM_WORKFLOW_DISABLED` | Demonstrates feature-toggle default behavior for workflow supportability endpoints. |
| `30_dpm_idempotency_history_supportability.json` | **DPM Idempotency History Supportability** | History returns two run mappings for same idempotency key | Demonstrates replay-disabled run recording and `GET /rebalance/idempotency/{idempotency_key}/history`. |
| `31_dpm_policy_pack_supportability_diagnostics.json` | **DPM Policy-Pack Supportability Diagnostics** | `READY` plus policy diagnostics responses | Demonstrates policy endpoint diagnostics (`/policies/effective`, `/policies/catalog`) with policy headers and request simulation context. |
| `32_dpm_supportability_summary_metrics.json` | **DPM Supportability Summary Metrics** | `READY` and summary response with expected metric fields | Demonstrates `/rebalance/supportability/summary` as the primary no-DB operational overview endpoint. |

## Feature Toggles Demonstrated

- `06_tax_aware_hifo.json`:
  - `options.enable_tax_awareness=true`
  - `options.max_realized_capital_gains=100`
- `07_settlement_overdraft_block.json`:
  - `options.enable_settlement_awareness=true`
  - `options.settlement_horizon_days=3`
- `08_solver_mode.json`:
  - `options.target_method=SOLVER`
- `09_batch_what_if_analysis.json`:
  - `scenarios.<name>.options` for per-scenario configuration in batch mode.
- `26_dpm_async_batch_analysis.json`:
  - `POST /rebalance/analyze/async` for async batch acceptance
  - `GET /rebalance/operations/{operation_id}` and `/by-correlation/{correlation_id}` for operation retrieval
  - partial-failure batch behavior (`warnings=["PARTIAL_BATCH_FAILURE"]`) with successful operation completion
- `27_dpm_supportability_artifact_flow.json`:
  - `POST /rebalance/simulate` with idempotency and correlation headers
  - `GET /rebalance/supportability/summary`
  - `GET /rebalance/runs/{rebalance_run_id}`
  - `GET /rebalance/runs/{rebalance_run_id}/support-bundle`
  - `GET /rebalance/runs/by-correlation/{correlation_id}/support-bundle`
  - `GET /rebalance/runs/idempotency/{idempotency_key}/support-bundle`
  - `GET /rebalance/runs/by-operation/{operation_id}/support-bundle`
  - `GET /rebalance/runs/by-correlation/{correlation_id}`
  - `GET /rebalance/runs/idempotency/{idempotency_key}`
  - `GET /rebalance/runs/{rebalance_run_id}/artifact` with deterministic artifact hash on repeated retrieval
- `28_dpm_async_manual_execute_guard.json`:
  - `POST /rebalance/analyze/async` (default inline mode)
  - `POST /rebalance/operations/{operation_id}/execute` guard path returns `DPM_ASYNC_OPERATION_NOT_EXECUTABLE` for non-pending operations
- `29_dpm_workflow_gate_disabled_contract.json`:
  - `POST /rebalance/simulate` to create a pending-review candidate run
  - `GET /rebalance/runs/{rebalance_run_id}/workflow` returns `DPM_WORKFLOW_DISABLED` when workflow feature is off
  - `GET /rebalance/runs/{rebalance_run_id}/workflow/history` returns `DPM_WORKFLOW_DISABLED` when workflow feature is off
- `30_dpm_idempotency_history_supportability.json`:
  - `DPM_IDEMPOTENCY_REPLAY_ENABLED=false`
  - `DPM_IDEMPOTENCY_HISTORY_APIS_ENABLED=true`
  - `GET /rebalance/idempotency/{idempotency_key}/history` returns append-only mapping history with run id, correlation id, and request hash
- `31_dpm_policy_pack_supportability_diagnostics.json`:
  - `POST /rebalance/simulate` with policy headers (`X-Policy-Pack-Id`, `X-Tenant-Policy-Pack-Id`, `X-Tenant-Id`)
  - `GET /rebalance/policies/effective` and `GET /rebalance/policies/catalog` for policy selection diagnostics
- `32_dpm_supportability_summary_metrics.json`:
  - `POST /rebalance/simulate` to create supportability records
  - `GET /rebalance/supportability/summary` for run/operation/workflow/lineage aggregate metrics
- `10_advisory_proposal_simulate.json`:
  - `options.enable_proposal_simulation=true`
  - `options.proposal_apply_cash_flows_first=true`
  - `options.proposal_block_negative_cash=true`
- `11_advisory_auto_funding_single_ccy.json`:
  - `options.auto_funding=true`
  - `options.funding_mode=AUTO_FX`
  - `options.fx_generation_policy=ONE_FX_PER_CCY`
- `12_advisory_partial_funding.json`:
  - `options.auto_funding=true`
  - existing foreign cash + FX top-up behavior
- `13_advisory_missing_fx_blocked.json`:
  - `options.block_on_missing_fx=true`
  - hard block + missing FX diagnostics
- `14_advisory_drift_asset_class.json`:
  - `options.enable_drift_analytics=true`
  - `reference_model.asset_class_targets` controls drift comparison buckets
- `15_advisory_drift_instrument.json`:
  - `options.enable_instrument_drift=true`
  - `reference_model.instrument_targets` enables instrument-level drift output
- `16_advisory_suitability_resolved_single_position.json`:
  - `options.enable_suitability_scanner=true`
  - `options.suitability_thresholds.single_position_max_weight=0.10`
- `17_advisory_suitability_new_issuer_breach.json`:
  - `options.enable_suitability_scanner=true`
  - `options.suitability_thresholds.issuer_max_weight=0.20`
- `18_advisory_suitability_sell_only_violation.json`:
  - `options.enable_suitability_scanner=true`
  - governance scan emits `NEW` issue for blocked BUY attempt in `SELL_ONLY`
- `19_advisory_proposal_artifact.json`:
  - `POST /rebalance/proposals/artifact`
  - deterministic `artifact_hash` excludes volatile fields (`created_at`, hash field)
  - includes `summary`, `portfolio_impact`, `trades_and_funding`, `suitability_summary`, `assumptions_and_limits`, `disclosures`, and `evidence_bundle`
- `20_advisory_proposal_persist_create.json`:
  - `POST /rebalance/proposals`
  - `Idempotency-Key` required, create is idempotent by canonical request hash
  - persists proposal metadata, immutable version payload, and `CREATED` event
- `21_advisory_proposal_new_version.json`:
  - `POST /rebalance/proposals/{proposal_id}/versions`
  - same portfolio context by default (`PROPOSAL_ALLOW_PORTFOLIO_CHANGE_ON_NEW_VERSION=false`)
- `22_advisory_proposal_transition_to_compliance.json`:
  - `POST /rebalance/proposals/{proposal_id}/transitions`
  - requires `expected_state` by default (`PROPOSAL_REQUIRE_EXPECTED_STATE=true`)
- `23_advisory_proposal_approval_client_consent.json`:
  - `POST /rebalance/proposals/{proposal_id}/approvals`
  - persists approval record and workflow event in one operation
- `24_advisory_proposal_approval_compliance.json`:
  - `POST /rebalance/proposals/{proposal_id}/approvals`
  - validates compliance approval transition from `COMPLIANCE_REVIEW`
- `25_advisory_proposal_transition_executed.json`:
  - `POST /rebalance/proposals/{proposal_id}/transitions`
  - validates transition to `EXECUTED` from `EXECUTION_READY`

## Understanding Output Statuses

* **READY:** All constraints met, trades generated, safety checks passed. Ready for execution.
* **PENDING_REVIEW:** Trades generated but require human approval (e.g., cash drift, soft constraint breach).
* **BLOCKED:** Critical failure (Data Quality, Hard Constraint, Safety Violation). No trades valid.
