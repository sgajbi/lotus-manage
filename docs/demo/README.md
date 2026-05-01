# lotus-manage Rebalance Engine Demo Scenarios

This folder contains JSON input files demonstrating key capabilities of the lotus-manage Rebalance Engine. Run these scenarios through the API endpoints.

Canonical local service identity:
- `http://manage.dev.lotus`

## Running Scenarios

### API Usage

For simulate demos, POST the content of a scenario file to `/api/v1/rebalance/simulate` with `Idempotency-Key`.

Example:
```bash
curl -X POST "http://manage.dev.lotus/api/v1/rebalance/simulate" -H "Content-Type: application/json" -H "Idempotency-Key: demo-01" --data-binary "@docs/demo/01_standard_drift.json"
```

For batch what-if demos, POST to `/api/v1/rebalance/analyze`:
```bash
curl -X POST "http://manage.dev.lotus/api/v1/rebalance/analyze" -H "Content-Type: application/json" --data-binary "@docs/demo/09_batch_what_if_analysis.json"
```

For asynchronous batch what-if demos, POST to `/api/v1/rebalance/analyze/async` and retrieve operation status:
```bash
curl -X POST "http://manage.dev.lotus/api/v1/rebalance/analyze/async" -H "Content-Type: application/json" -H "X-Correlation-Id: demo-corr-26-async" --data-binary "@docs/demo/26_dpm_async_batch_analysis.json"
curl -X GET "http://manage.dev.lotus/api/v1/rebalance/operations?status_filter=SUCCEEDED&operation_type=ANALYZE_SCENARIOS&limit=20"
curl -X GET "http://manage.dev.lotus/api/v1/rebalance/operations/by-correlation/demo-corr-26-async"
```

For lotus-manage policy-pack resolution supportability:
```bash
curl -X GET "http://manage.dev.lotus/api/v1/rebalance/policies/effective" -H "X-Policy-Pack-Id: dpm_standard_v1" -H "X-Tenant-Policy-Pack-Id: dpm_tenant_default_v1" -H "X-Tenant-Id: tenant_001"
```

For lotus-manage policy-pack catalog and selected-pack presence diagnostics:
```bash
curl -X GET "http://manage.dev.lotus/api/v1/rebalance/policies/catalog" -H "X-Policy-Pack-Id: dpm_standard_v1" -H "X-Tenant-Policy-Pack-Id: dpm_tenant_default_v1" -H "X-Tenant-Id: tenant_001"
```

For lotus-manage policy-pack supportability + diagnostics scenario:
```bash
curl -X POST "http://manage.dev.lotus/api/v1/rebalance/simulate" -H "Content-Type: application/json" -H "Idempotency-Key: demo-31-policy-pack" -H "X-Policy-Pack-Id: dpm_standard_v1" -H "X-Tenant-Policy-Pack-Id: dpm_tenant_default_v1" -H "X-Tenant-Id: tenant_001" --data-binary "@docs/demo/31_dpm_policy_pack_supportability_diagnostics.json"
curl -X GET "http://manage.dev.lotus/api/v1/rebalance/policies/effective" -H "X-Policy-Pack-Id: dpm_standard_v1" -H "X-Tenant-Policy-Pack-Id: dpm_tenant_default_v1" -H "X-Tenant-Id: tenant_001"
curl -X GET "http://manage.dev.lotus/api/v1/rebalance/policies/catalog" -H "X-Policy-Pack-Id: dpm_standard_v1" -H "X-Tenant-Policy-Pack-Id: dpm_tenant_default_v1" -H "X-Tenant-Id: tenant_001"
```

For lotus-manage supportability summary metrics scenario:
```bash
curl -X POST "http://manage.dev.lotus/api/v1/rebalance/simulate" -H "Content-Type: application/json" -H "Idempotency-Key: demo-32-support-summary" -H "X-Correlation-Id: demo-corr-32-support-summary" --data-binary "@docs/demo/32_dpm_supportability_summary_metrics.json"
curl -X GET "http://manage.dev.lotus/api/v1/rebalance/supportability/summary"
```

For lotus-manage policy-pack turnover override demo (requires `DPM_POLICY_PACKS_ENABLED=true`):
```bash
export DPM_POLICY_PACK_CATALOG_JSON='{"dpm_standard_v1":{"version":"1","turnover_policy":{"max_turnover_pct":"0.01"},"tax_policy":{"enable_tax_awareness":true,"max_realized_capital_gains":"100"}}}'
export DPM_TENANT_POLICY_PACK_RESOLUTION_ENABLED=true
export DPM_TENANT_POLICY_PACK_MAP_JSON='{"tenant_001":"dpm_standard_v1"}'
curl -X POST "http://manage.dev.lotus/api/v1/rebalance/simulate" -H "Content-Type: application/json" -H "Idempotency-Key: demo-policy-pack-turnover-1" -H "X-Policy-Pack-Id: dpm_standard_v1" --data-binary "@docs/demo/01_standard_drift.json"
```

Settlement-policy override example:
```bash
export DPM_POLICY_PACK_CATALOG_JSON='{"dpm_standard_v1":{"version":"1","settlement_policy":{"enable_settlement_awareness":true,"settlement_horizon_days":3}}}'
curl -X POST "http://manage.dev.lotus/api/v1/rebalance/simulate" -H "Content-Type: application/json" -H "Idempotency-Key: demo-policy-pack-settlement-1" -H "X-Policy-Pack-Id: dpm_standard_v1" --data-binary "@docs/demo/07_settlement_overdraft_block.json"
```

Constraint-policy override example:
```bash
export DPM_POLICY_PACK_CATALOG_JSON='{"dpm_standard_v1":{"version":"1","constraint_policy":{"single_position_max_weight":"0.25","group_constraints":{"sector:TECH":{"max_weight":"0.20"}}}}}'
curl -X POST "http://manage.dev.lotus/api/v1/rebalance/simulate" -H "Content-Type: application/json" -H "Idempotency-Key: demo-policy-pack-constraints-1" -H "X-Policy-Pack-Id: dpm_standard_v1" --data-binary "@docs/demo/01_standard_drift.json"
```

Workflow-policy override example:
```bash
export DPM_POLICY_PACK_CATALOG_JSON='{"dpm_standard_v1":{"version":"1","workflow_policy":{"enable_workflow_gates":false,"workflow_requires_mandate_approval":true,"mandate_approval_already_obtained":true}}}'
curl -X POST "http://manage.dev.lotus/api/v1/rebalance/simulate" -H "Content-Type: application/json" -H "Idempotency-Key: demo-policy-pack-workflow-1" -H "X-Policy-Pack-Id: dpm_standard_v1" --data-binary "@docs/demo/01_standard_drift.json"
```

Idempotency-policy override example:
```bash
export DPM_IDEMPOTENCY_REPLAY_ENABLED=true
export DPM_POLICY_PACK_CATALOG_JSON='{"dpm_standard_v1":{"version":"1","idempotency_policy":{"replay_enabled":false}}}'
curl -X POST "http://manage.dev.lotus/api/v1/rebalance/simulate" -H "Content-Type: application/json" -H "Idempotency-Key: demo-policy-pack-idempotency-1" -H "X-Policy-Pack-Id: dpm_standard_v1" --data-binary "@docs/demo/01_standard_drift.json"
curl -X POST "http://manage.dev.lotus/api/v1/rebalance/simulate" -H "Content-Type: application/json" -H "Idempotency-Key: demo-policy-pack-idempotency-1" -H "X-Policy-Pack-Id: dpm_standard_v1" --data-binary "@docs/demo/01_standard_drift.json"
```

For lotus-manage supportability and deterministic artifact retrieval flow:
```bash
curl -X POST "http://manage.dev.lotus/api/v1/rebalance/simulate" -H "Content-Type: application/json" -H "Idempotency-Key: demo-27-supportability" -H "X-Correlation-Id: demo-corr-27-supportability" --data-binary "@docs/demo/27_dpm_supportability_artifact_flow.json"
curl -X GET "http://manage.dev.lotus/api/v1/rebalance/runs?status_filter=READY&portfolio_id=pf_demo_support_27&limit=20"
curl -X GET "http://manage.dev.lotus/api/v1/rebalance/runs?request_hash=<request_hash>&limit=20"
curl -X GET "http://manage.dev.lotus/api/v1/rebalance/runs/by-request-hash/<url_encoded_request_hash>"
curl -X GET "http://manage.dev.lotus/api/v1/rebalance/supportability/summary"
curl -X GET "http://manage.dev.lotus/api/v1/rebalance/runs/by-correlation/demo-corr-27-supportability"
curl -X GET "http://manage.dev.lotus/api/v1/rebalance/runs/idempotency/demo-27-supportability"
curl -X GET "http://manage.dev.lotus/api/v1/rebalance/runs/<rebalance_run_id>/support-bundle"
curl -X GET "http://manage.dev.lotus/api/v1/rebalance/runs/by-correlation/<correlation_id>/support-bundle"
curl -X GET "http://manage.dev.lotus/api/v1/rebalance/runs/idempotency/<idempotency_key>/support-bundle"
curl -X GET "http://manage.dev.lotus/api/v1/rebalance/runs/by-operation/<operation_id>/support-bundle"
curl -X GET "http://manage.dev.lotus/api/v1/rebalance/runs/<rebalance_run_id>/support-bundle?include_artifact=false&include_async_operation=false&include_idempotency_history=false"
curl -X GET "http://manage.dev.lotus/api/v1/rebalance/runs/<rebalance_run_id>/artifact"
```

Retention can be enabled for supportability records with:
- `DPM_SUPPORTABILITY_RETENTION_DAYS=<positive_integer>`

For lotus-manage lineage supportability (enabled when `DPM_LINEAGE_APIS_ENABLED=true`):
```bash
curl -X GET "http://manage.dev.lotus/api/v1/rebalance/lineage/<entity_id>?edge_type=CORRELATION_TO_RUN&limit=20"
```
Use canonical snake_case query params only; unsupported aliases are rejected with `422`.

For lotus-manage idempotency history supportability (enabled when `DPM_IDEMPOTENCY_HISTORY_APIS_ENABLED=true`):
```bash
curl -X GET "http://manage.dev.lotus/api/v1/rebalance/idempotency/<idempotency_key>/history"
```

For lotus-manage workflow supportability endpoints (enabled only when `DPM_WORKFLOW_ENABLED=true`):
```bash
curl -X GET "http://manage.dev.lotus/api/v1/rebalance/runs/<rebalance_run_id>/workflow"
curl -X GET "http://manage.dev.lotus/api/v1/rebalance/runs/by-correlation/<correlation_id>/workflow"
curl -X GET "http://manage.dev.lotus/api/v1/rebalance/runs/idempotency/<idempotency_key>/workflow"
curl -X POST "http://manage.dev.lotus/api/v1/rebalance/runs/<rebalance_run_id>/workflow/actions" -H "Content-Type: application/json" -H "X-Correlation-Id: demo-corr-workflow-1" --data-binary '{"action":"APPROVE","reason_code":"REVIEW_APPROVED","actor_id":"reviewer_001"}'
curl -X POST "http://manage.dev.lotus/api/v1/rebalance/runs/by-correlation/<correlation_id>/workflow/actions" -H "Content-Type: application/json" -H "X-Correlation-Id: demo-corr-workflow-2" --data-binary '{"action":"REQUEST_CHANGES","reason_code":"NEEDS_DETAIL","actor_id":"reviewer_001"}'
curl -X POST "http://manage.dev.lotus/api/v1/rebalance/runs/idempotency/<idempotency_key>/workflow/actions" -H "Content-Type: application/json" -H "X-Correlation-Id: demo-corr-workflow-3" --data-binary '{"action":"REJECT","reason_code":"POLICY_REJECTED","actor_id":"reviewer_001"}'
curl -X GET "http://manage.dev.lotus/api/v1/rebalance/runs/<rebalance_run_id>/workflow/history"
curl -X GET "http://manage.dev.lotus/api/v1/rebalance/runs/by-correlation/<correlation_id>/workflow/history"
curl -X GET "http://manage.dev.lotus/api/v1/rebalance/runs/idempotency/<idempotency_key>/workflow/history"
curl -X GET "http://manage.dev.lotus/api/v1/rebalance/workflow/decisions?action=APPROVE&actor_id=reviewer_001&limit=20"
curl -X GET "http://manage.dev.lotus/api/v1/rebalance/workflow/decisions/by-correlation/<correlation_id>"
```

For full live demo-pack validation:
```bash
python scripts/run_demo_pack_live.py --base-url http://manage.dev.lotus
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
| `09_batch_what_if_analysis.json` | **Batch What-If Analysis** | Mixed by scenario | Runs baseline/tax/settlement scenarios in one `/api/v1/rebalance/analyze` call. |
| `26_dpm_async_batch_analysis.json` | **lotus-manage Async Batch Analysis** | Async operation `SUCCEEDED` with partial-failure warning | Demonstrates `/api/v1/rebalance/analyze/async` acceptance + operation lookup with `failed_scenarios` diagnostics. |
| `27_dpm_supportability_artifact_flow.json` | **lotus-manage Supportability + Artifact Flow** | `READY` run + deterministic artifact hash | Demonstrates run lookup by run id/correlation/idempotency and deterministic retrieval from `/api/v1/rebalance/runs/{rebalance_run_id}/artifact`. |
| `28_dpm_async_manual_execute_guard.json` | **lotus-manage Async Manual Execute Guard** | Manual execute returns `409` on non-pending run | Demonstrates `/api/v1/rebalance/operations/{operation_id}/execute` conflict guard when operation already completed inline. |
| `29_dpm_workflow_gate_disabled_contract.json` | **lotus-manage Workflow Gate Default Guard** | Workflow endpoints return `404 DPM_WORKFLOW_DISABLED` | Demonstrates feature-toggle default behavior for workflow supportability endpoints. |
| `30_dpm_idempotency_history_supportability.json` | **lotus-manage Idempotency History Supportability** | History returns two run mappings for same idempotency key | Demonstrates replay-disabled run recording and `GET /api/v1/rebalance/idempotency/{idempotency_key}/history`. |
| `31_dpm_policy_pack_supportability_diagnostics.json` | **lotus-manage Policy-Pack Supportability Diagnostics** | `READY` plus policy diagnostics responses | Demonstrates policy endpoint diagnostics (`/policies/effective`, `/policies/catalog`) with policy headers and request simulation context. |
| `32_dpm_supportability_summary_metrics.json` | **lotus-manage Supportability Summary Metrics** | `READY` and summary response with expected metric fields | Demonstrates `/api/v1/rebalance/supportability/summary` as the primary no-DB operational overview endpoint. |

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
  - `POST /api/v1/rebalance/analyze/async` for async batch acceptance
  - `GET /api/v1/rebalance/operations/{operation_id}` and `/by-correlation/{correlation_id}` for operation retrieval
  - partial-failure batch behavior (`warnings=["PARTIAL_BATCH_FAILURE"]`) with successful operation completion
- `27_dpm_supportability_artifact_flow.json`:
  - `POST /api/v1/rebalance/simulate` with idempotency and correlation headers
  - `GET /api/v1/rebalance/supportability/summary`
  - `GET /api/v1/rebalance/runs/{rebalance_run_id}`
  - `GET /api/v1/rebalance/runs/{rebalance_run_id}/support-bundle`
  - `GET /api/v1/rebalance/runs/by-correlation/{correlation_id}/support-bundle`
  - `GET /api/v1/rebalance/runs/idempotency/{idempotency_key}/support-bundle`
  - `GET /api/v1/rebalance/runs/by-operation/{operation_id}/support-bundle`
  - `GET /api/v1/rebalance/runs/by-correlation/{correlation_id}`
  - `GET /api/v1/rebalance/runs/idempotency/{idempotency_key}`
  - `GET /api/v1/rebalance/runs/{rebalance_run_id}/artifact` with deterministic artifact hash on repeated retrieval
- `28_dpm_async_manual_execute_guard.json`:
  - `POST /api/v1/rebalance/analyze/async` (default inline mode)
  - `POST /api/v1/rebalance/operations/{operation_id}/execute` guard path returns `DPM_ASYNC_OPERATION_NOT_EXECUTABLE` for non-pending operations
- `29_dpm_workflow_gate_disabled_contract.json`:
  - `POST /api/v1/rebalance/simulate` to create a pending-review candidate run
  - `GET /api/v1/rebalance/runs/{rebalance_run_id}/workflow` returns `DPM_WORKFLOW_DISABLED` when workflow feature is off
  - `GET /api/v1/rebalance/runs/{rebalance_run_id}/workflow/history` returns `DPM_WORKFLOW_DISABLED` when workflow feature is off
- `30_dpm_idempotency_history_supportability.json`:
  - `DPM_IDEMPOTENCY_REPLAY_ENABLED=false`
  - `DPM_IDEMPOTENCY_HISTORY_APIS_ENABLED=true`
  - `GET /api/v1/rebalance/idempotency/{idempotency_key}/history` returns append-only mapping history with run id, correlation id, and request hash
- `31_dpm_policy_pack_supportability_diagnostics.json`:
  - `POST /api/v1/rebalance/simulate` with policy headers (`X-Policy-Pack-Id`, `X-Tenant-Policy-Pack-Id`, `X-Tenant-Id`)
  - `GET /api/v1/rebalance/policies/effective` and `GET /api/v1/rebalance/policies/catalog` for policy selection diagnostics
- `32_dpm_supportability_summary_metrics.json`:
  - `POST /api/v1/rebalance/simulate` to create supportability records
  - `GET /api/v1/rebalance/supportability/summary` for run/operation/workflow/lineage aggregate metrics
## Understanding Output Statuses

* **READY:** All constraints met, trades generated, safety checks passed. Ready for execution.
* **PENDING_REVIEW:** Trades generated but require human approval (e.g., cash drift, soft constraint breach).
* **BLOCKED:** Critical failure (Data Quality, Hard Constraint, Safety Violation). No trades valid.

