# DPM Rebalance Engine Know-How

Implementation scope:
- API: `src/api/main.py` (`/rebalance/simulate`, `/rebalance/analyze`)
- DPM run supportability router: `src/api/routers/dpm_runs.py`
- DPM policy-pack supportability router: `src/api/routers/dpm_policy_packs.py`
- DPM run supportability runtime config/env parsing: `src/api/routers/dpm_runs_config.py`
- DPM run supportability service orchestration: `src/core/dpm_runs/service.py`
- DPM run supportability DTO mappers: `src/core/dpm_runs/serializers.py`
- DPM run supportability workflow transition helpers: `src/core/dpm_runs/workflow.py`
- Models: `src/core/models.py`
- Core orchestration: `src/core/dpm/engine.py` (`run_simulation`)
- DPM modular internals:
  - `src/core/dpm/universe.py` (universe construction and shelf filtering)
  - `src/core/dpm/targets.py` (target generation and group-constraint application)
  - `src/core/dpm/intents.py` (security intent generation, tax-aware sell controls)
  - `src/core/dpm/turnover.py` (turnover ranking and budget enforcement)
  - `src/core/dpm/execution.py` (FX generation, settlement ladder, simulation execution)
- Shared simulation primitives: `src/core/common/simulation_shared.py`
- Shared intent dependency linker: `src/core/common/intent_dependencies.py`
- Shared workflow gate evaluator: `src/core/common/workflow_gates.py`
- Valuation: `src/core/valuation.py`
- Rules: `src/core/compliance.py`
- Target generation: `src/core/target_generation.py`

## API Surface

### `POST /rebalance/simulate`
- Purpose: deterministic rebalance simulation.
- Required header: `Idempotency-Key`
- Optional header: `X-Correlation-Id`
- Optional header: `X-Policy-Pack-Id` (selected pack may override configured engine options)
- Optional header: `X-Tenant-Id` (used for tenant default policy-pack resolver lookup)
  - Current policy transformations:
    - `max_turnover_pct`
    - `enable_tax_awareness`
    - `max_realized_capital_gains`
    - `enable_settlement_awareness`
    - `settlement_horizon_days`
    - `single_position_max_weight`
    - `group_constraints`
    - `enable_workflow_gates`
    - `workflow_requires_client_consent`
    - `client_consent_already_obtained`
  - Current non-options policy transformation:
    - `idempotency_policy.replay_enabled` controls simulate replay semantics.
- Output: `RebalanceResult` with status `READY | PENDING_REVIEW | BLOCKED` and `gate_decision`
- Correlation behavior:
  - response `correlation_id` echoes request `X-Correlation-Id` when provided
  - otherwise defaults to `c_none`
- Idempotency behavior:
  - same key + same canonical request payload returns cached result
  - same key + different canonical request payload returns `409 Conflict`
  - replay semantics can be disabled with `DPM_IDEMPOTENCY_REPLAY_ENABLED=false`

### `POST /rebalance/analyze`
- Purpose: multi-scenario what-if analysis using shared snapshots.
- Optional header: `X-Correlation-Id`
- Optional header: `X-Policy-Pack-Id` (selected pack may override configured engine options)
- Optional header: `X-Tenant-Id` (used for tenant default policy-pack resolver lookup)
  - Current policy transformations:
    - `max_turnover_pct`
    - `enable_tax_awareness`
    - `max_realized_capital_gains`
    - `enable_settlement_awareness`
    - `settlement_horizon_days`
    - `single_position_max_weight`
    - `group_constraints`
    - `enable_workflow_gates`
    - `workflow_requires_client_consent`
    - `client_consent_already_obtained`
- Output: `BatchRebalanceResult` with scenario-level results/metrics/failures.
- Scenario correlation behavior:
  - when `X-Correlation-Id` is provided, each scenario result uses `{header}:{scenario_name}`
  - when omitted, each scenario result uses `{batch_run_id}:{scenario_name}`

### `GET /rebalance/operations`
- Purpose: list asynchronous operations for supportability investigations.
- Filters:
  - `from` (created-at lower bound)
  - `to` (created-at upper bound)
  - `operation_type`
  - `status`
  - `correlation_id`
- Pagination:
  - `limit`
  - `cursor`

### `GET /rebalance/supportability/summary`
- Purpose: return operational supportability summary metrics without direct data store access.
- Output:
  - configured store backend and retention policy
  - run and async operation totals
  - workflow decision and lineage edge totals
  - workflow decision aggregate counts by action and reason code
  - run status distribution
  - async operation status distribution
  - oldest/newest created-at timestamps for runs and operations

### `GET /rebalance/policies/effective`
- Purpose: resolve and return effective DPM policy-pack selection for integration/support diagnostics.
- Optional headers:
  - `X-Policy-Pack-Id`
  - `X-Tenant-Policy-Pack-Id`
  - `X-Tenant-Id`
- Output:
  - `enabled`
  - `selected_policy_pack_id`
  - `source`

### `GET /rebalance/policies/catalog`
- Purpose: inspect configured policy-pack definitions and effective selection context for supportability.
- Optional headers:
  - `X-Policy-Pack-Id`
  - `X-Tenant-Policy-Pack-Id`
  - `X-Tenant-Id`
- Output:
  - `enabled`
  - `total`
  - `selected_policy_pack_id`
  - `selected_policy_pack_present`
  - `selected_policy_pack_source`
  - `items`

### `GET /rebalance/policies/catalog/{policy_pack_id}`
- Purpose: retrieve one policy-pack definition by identifier.

### `PUT /rebalance/policies/catalog/{policy_pack_id}`
- Purpose: create or update one policy-pack definition by identifier.
- Feature flag:
  - `DPM_POLICY_PACK_ADMIN_APIS_ENABLED` (default `false`)

### `DELETE /rebalance/policies/catalog/{policy_pack_id}`
- Purpose: delete one policy-pack definition by identifier.
- Feature flag:
  - `DPM_POLICY_PACK_ADMIN_APIS_ENABLED` (default `false`)

Swagger contract quality:
- Policy-pack and supportability DTOs are contract-tested for field-level `description` and `examples`.
- Policy endpoints are contract-tested as response-only (`GET` without request body).

### `GET /rebalance/runs/{rebalance_run_id}`
- Purpose: retrieve one DPM run with full result payload and lineage metadata for support investigations.

### `GET /rebalance/runs/{rebalance_run_id}/support-bundle`
- Purpose: retrieve one aggregated supportability bundle so investigations can run from one payload.
- Includes:
  - run payload (`run`)
  - workflow decision history (`workflow_history`)
  - lineage edges for run id (`lineage`)
  - optional deterministic run artifact (`artifact`)
  - optional async operation mapped by run correlation (`async_operation`)
  - optional idempotency mapping history (`idempotency_history`)
- Query options:
  - `include_artifact`
  - `include_async_operation`
  - `include_idempotency_history`

### `GET /rebalance/runs/by-correlation/{correlation_id}/support-bundle`
- Purpose: retrieve the same supportability bundle when run id is not known.
- Query options:
  - `include_artifact`
  - `include_async_operation`
  - `include_idempotency_history`

### `GET /rebalance/runs/idempotency/{idempotency_key}/support-bundle`
- Purpose: retrieve the same supportability bundle when only idempotency key is available.
- Query options:
  - `include_artifact`
  - `include_async_operation`
  - `include_idempotency_history`

### `GET /rebalance/runs/by-operation/{operation_id}/support-bundle`
- Purpose: retrieve the same supportability bundle when asynchronous operation id is available.
- Query options:
  - `include_artifact`
  - `include_async_operation`
  - `include_idempotency_history`

### `GET /rebalance/runs`
- Purpose: list DPM runs for supportability investigations.
- Filters:
  - `from` (created-at lower bound)
  - `to` (created-at upper bound)
  - `status` (`READY`, `PENDING_REVIEW`, `BLOCKED`)
  - `request_hash` (canonical request hash)
  - `portfolio_id`
- Pagination:
  - `limit`
  - `cursor`

### `GET /rebalance/runs/by-correlation/{correlation_id}`
- Purpose: retrieve latest DPM run mapped to correlation id.

### `GET /rebalance/runs/by-request-hash/{request_hash}`
- Purpose: retrieve latest DPM run mapped to canonical request hash.
- Note: URL-encode `request_hash` when calling via path parameter.

### `GET /rebalance/runs/idempotency/{idempotency_key}`
- Purpose: retrieve idempotency key to run mapping for retry and incident analysis.

### `GET /rebalance/lineage/{entity_id}`
- Purpose: retrieve supportability lineage edges for entity ids (correlation, idempotency, run, operation).
- Filters:
  - `edge_type`
  - `from`
  - `to`
- Pagination:
  - `limit`
  - `cursor`

### `GET /rebalance/idempotency/{idempotency_key}/history`
- Purpose: retrieve append-only idempotency key mapping history across recorded runs.

### `GET /rebalance/runs/{rebalance_run_id}/workflow`
- Purpose: retrieve workflow gate status and latest reviewer decision for a run.

### `GET /rebalance/runs/by-correlation/{correlation_id}/workflow`
- Purpose: retrieve workflow gate status when only correlation id is known.

### `GET /rebalance/runs/idempotency/{idempotency_key}/workflow`
- Purpose: retrieve workflow gate status when only idempotency key is known.

### `POST /rebalance/runs/{rebalance_run_id}/workflow/actions`
- Purpose: apply one workflow action (`APPROVE`, `REJECT`, `REQUEST_CHANGES`) with actor/reason trace.

### `POST /rebalance/runs/by-correlation/{correlation_id}/workflow/actions`
- Purpose: apply one workflow action when only run correlation id is known.

### `POST /rebalance/runs/idempotency/{idempotency_key}/workflow/actions`
- Purpose: apply one workflow action when only idempotency key is known.

### `GET /rebalance/runs/{rebalance_run_id}/workflow/history`
- Purpose: retrieve append-only workflow decision history for audit and investigation.

### `GET /rebalance/runs/by-correlation/{correlation_id}/workflow/history`
- Purpose: retrieve workflow decision history when only correlation id is known.

### `GET /rebalance/runs/idempotency/{idempotency_key}/workflow/history`
- Purpose: retrieve workflow decision history when only idempotency key is known.

### `GET /rebalance/workflow/decisions`
- Purpose: list workflow decisions across runs for supportability investigations.
- Filters:
  - `rebalance_run_id`
  - `action`
  - `actor_id`
  - `reason_code`
  - `from` (decision timestamp lower bound)
  - `to` (decision timestamp upper bound)
- Pagination:
  - `limit`
  - `cursor`

### `GET /rebalance/workflow/decisions/by-correlation/{correlation_id}`
- Purpose: retrieve workflow decision history when only correlation id is available in incident context.

## Pipeline (`run_simulation`)

1. Valuation
- Builds before-state via `build_simulated_state`.
- Captures data-quality buckets (`price_missing`, `fx_missing`, `shelf_missing`).

2. Universe
- Applies shelf status semantics (`APPROVED`, `RESTRICTED`, `SELL_ONLY`, `BANNED`, `SUSPENDED`).

3. Target Generation
- `HEURISTIC` or `SOLVER` path (`options.target_method`).
- Optional dual-method comparison via `compare_target_methods`.

4. Intent Generation
- Produces `SECURITY_TRADE` intents from drift.
- Applies dust suppression and optional turnover cap.
- Applies optional tax-aware lot logic (HIFO + gains budget).

5. Simulation + Rules + Reconciliation
- Generates FX funding/sweep intents.
- Optional settlement ladder checks.
- Simulates after-state and evaluates rules.
- Reconciliation guards value consistency.

## Status Semantics

- `READY`: no hard fails and no soft-rule breach.
- `PENDING_REVIEW`: at least one soft-rule fail and no hard fail.
- `BLOCKED`: any hard fail (rules, data quality, or reconciliation).

## DPM Feature Flags

- `target_method`
- `compare_target_methods`
- `enable_tax_awareness`
- `max_realized_capital_gains`
- `max_turnover_pct`
- `enable_settlement_awareness`
- `settlement_horizon_days`
- `fx_settlement_days`
- `max_overdraft_by_ccy`
- `enable_workflow_gates`
- `workflow_requires_client_consent`
- `client_consent_already_obtained`
- `link_buy_to_same_currency_sell_dependency`
- plus shared controls (`valuation_mode`, cash bands, dust/min-notional, data quality blocking)
- runtime API toggles:
  - `DPM_IDEMPOTENCY_REPLAY_ENABLED` (default `true`)
  - `DPM_IDEMPOTENCY_CACHE_MAX_SIZE` (default `1000`)
  - `DPM_SUPPORT_APIS_ENABLED` (default `true`)
  - `DPM_SUPPORTABILITY_STORE_BACKEND` (`IN_MEMORY` | `SQL`, default `IN_MEMORY`)
  - `DPM_SUPPORTABILITY_SQL_PATH` (preferred when backend is `SQL`)
  - `DPM_SUPPORTABILITY_SQLITE_PATH` (backward-compatible path alias)
  - `DPM_SUPPORTABILITY_RETENTION_DAYS` (default `0`, disabled when `0`)
  - `DPM_SUPPORTABILITY_SUMMARY_APIS_ENABLED` (default `true`)
  - `DPM_SUPPORT_BUNDLE_APIS_ENABLED` (default `true`)
  - `DPM_LINEAGE_APIS_ENABLED` (default `false`)
  - `DPM_IDEMPOTENCY_HISTORY_APIS_ENABLED` (default `false`)
  - `DPM_WORKFLOW_ENABLED` (default `false`)
  - `DPM_WORKFLOW_REQUIRES_REVIEW_FOR_STATUSES` (CSV list, default `PENDING_REVIEW`)
  - `DPM_POLICY_PACKS_ENABLED` (default `false`)
  - `DPM_DEFAULT_POLICY_PACK_ID`
  - `DPM_POLICY_PACK_CATALOG_JSON` (JSON map of policy-pack definitions)
  - `DPM_POLICY_PACK_CATALOG_BACKEND` (`ENV_JSON` | `POSTGRES`, default `ENV_JSON`)
  - `DPM_POLICY_PACK_POSTGRES_DSN` (fallbacks to `DPM_SUPPORTABILITY_POSTGRES_DSN`)
  - `DPM_POLICY_PACK_ADMIN_APIS_ENABLED` (default `false`)
  - `DPM_TENANT_POLICY_PACK_RESOLUTION_ENABLED` (default `false`)
  - `DPM_TENANT_POLICY_PACK_MAP_JSON` (JSON map: `tenant_id -> policy_pack_id`)

Dependency policy note:
- `link_buy_to_same_currency_sell_dependency=null` defaults to `true` in DPM.
- when `false`, BUY security intents no longer depend on same-currency SELL intents.

## PostgreSQL Migration Tooling

- Forward-only Postgres migrations are applied from versioned SQL files:
  - `src/infrastructure/postgres_migrations/dpm/`
  - `src/infrastructure/postgres_migrations/proposals/`
- Migration history is tracked in `schema_migrations`.
- Migration checksums are enforced to prevent edited-in-place migration drift.
- Manual migration command:
  - `python scripts/postgres_migrate.py --target dpm`
  - `python scripts/postgres_migrate.py --target proposals`
  - `python scripts/postgres_migrate.py --target all`
- DSN configuration sources:
  - `--dpm-dsn` / `DPM_SUPPORTABILITY_POSTGRES_DSN`
  - `--proposals-dsn` / `PROPOSAL_POSTGRES_DSN`
- Production rollout runbook:
  - `docs/documentation/postgres-migration-rollout-runbook.md`

## Tests That Lock DPM Behavior

- API: `tests/unit/dpm/api/test_api_rebalance.py`
- Engine: `tests/unit/dpm/engine/`
- Goldens: `tests/unit/dpm/golden/test_golden_scenarios.py`
- Batch goldens: `tests/unit/dpm/golden/test_golden_batch_analysis.py`

## Deprecation Notes

- `src/core/dpm_engine.py` is a compatibility shim and emits `DeprecationWarning`.
- Use `src/core/dpm/engine.py` as the stable DPM engine import path.
