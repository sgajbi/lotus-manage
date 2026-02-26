# Advisory Proposal Engine Know-How

Implementation scope:
- API: `src/api/main.py` (`/rebalance/proposals/simulate`)
- API: `src/api/main.py` (`/rebalance/proposals/artifact`)
- API router: `src/api/routers/proposals.py` (`/rebalance/proposals` lifecycle family)
- Models: `src/core/models.py`
- Artifact models: `src/core/advisory/artifact_models.py`
- Proposal lifecycle domain:
  - `src/core/proposals/models.py`
  - `src/core/proposals/service.py`
  - `src/core/proposals/repository.py`
- Proposal lifecycle persistence adapter:
  - `src/infrastructure/proposals/in_memory.py`
  - `src/infrastructure/proposals/postgres.py`
- Core orchestration: `src/core/advisory_engine.py` (`run_proposal_simulation`)
- Advisory modular internals:
  - `src/core/advisory/ids.py` (deterministic run id generation)
  - `src/core/advisory/intents.py` (proposal cash/trade intent construction helpers)
  - `src/core/advisory/funding.py` (RFC-0014B auto-funding planner)
  - `src/core/advisory/artifact.py` (RFC-0014E artifact builder)
- Shared simulation primitives: `src/core/common/simulation_shared.py`
- Shared intent dependency linker: `src/core/common/intent_dependencies.py`
- Shared diagnostics builders: `src/core/common/diagnostics.py`
- Shared deterministic canonical serialization/hash: `src/core/common/canonical.py`
- Shared workflow gate evaluator: `src/core/common/workflow_gates.py`
- Shared advisory analytics:
  - `src/core/common/drift_analytics.py` (RFC-0014C drift analytics)
  - `src/core/common/suitability.py` (RFC-0014D suitability scanner)
- Valuation: `src/core/valuation.py`
- Rules: `src/core/compliance.py`

## API Surface

### `POST /rebalance/proposals/simulate`
- Purpose: simulate advisor-entered manual cash flows and manual security trades.
- Required header: `Idempotency-Key`
- Optional header: `X-Correlation-Id` (generated when missing)
- Output: `ProposalResult` with status `READY | PENDING_REVIEW | BLOCKED`
- Unhandled errors: `500` with `application/problem+json` payload.
- Idempotency behavior:
  - same key + same canonical payload: cached response
  - same key + different canonical payload: `409 Conflict`

### `POST /rebalance/proposals/artifact`
- Purpose: run proposal simulation and build deterministic advisory proposal package.
- Required header: `Idempotency-Key`
- Optional header: `X-Correlation-Id` (generated when missing)
- Output: `ProposalArtifact`
- Idempotency behavior:
  - Uses the same proposal simulation idempotency cache/hash behavior as `/rebalance/proposals/simulate`.
  - Same key + different canonical payload returns `409 Conflict`.

### `POST /rebalance/proposals`
- Purpose: run simulation+artifact and persist proposal aggregate/version/workflow event.
- Required header: `Idempotency-Key`
- Optional header: `X-Correlation-Id`
- Output: `ProposalCreateResponse`
- Idempotency behavior:
  - same key + same canonical request: returns same proposal/version
  - same key + different canonical request: `409 Conflict`

### `POST /rebalance/proposals/async`
- Purpose: accept proposal create for asynchronous execution.
- Required header: `Idempotency-Key`
- Optional header: `X-Correlation-Id`
- Output: async operation reference (`operation_id`, `status_url`).

### `GET /rebalance/proposals/{proposal_id}`
- Purpose: read proposal summary + current version + last gate decision.
- Query: `include_evidence=true|false` (defaults true)

### `GET /rebalance/proposals`
- Purpose: list proposals with filters and cursor pagination.
- Filters: `portfolio_id`, `state`, `created_by`, `created_from`, `created_to`, `limit`, `cursor`

### `GET /rebalance/proposals/{proposal_id}/versions/{version_no}`
- Purpose: read one immutable proposal version.
- Query: `include_evidence=true|false`

### `GET /rebalance/proposals/{proposal_id}/workflow-events`
- Purpose: retrieve append-only workflow timeline for operations investigation and audit.

### `GET /rebalance/proposals/{proposal_id}/approvals`
- Purpose: retrieve structured approval/consent records for supportability and controls review.

### `GET /rebalance/proposals/{proposal_id}/lineage`
- Purpose: retrieve immutable version lineage metadata (request/simulation/artifact hashes).

### `GET /rebalance/proposals/idempotency/{idempotency_key}`
- Purpose: resolve idempotency-key mappings during retry and incident investigations.

### `GET /rebalance/proposals/operations/{operation_id}`
- Purpose: retrieve asynchronous operation status and terminal result/error payload.

### `GET /rebalance/proposals/operations/by-correlation/{correlation_id}`
- Purpose: retrieve latest asynchronous operation by correlation id.

### `POST /rebalance/proposals/{proposal_id}/versions`
- Purpose: create immutable version `N+1` for existing proposal.
- Guard: same `portfolio_id` as aggregate unless `PROPOSAL_ALLOW_PORTFOLIO_CHANGE_ON_NEW_VERSION=true`.

### `POST /rebalance/proposals/{proposal_id}/versions/async`
- Purpose: accept proposal version create for asynchronous execution.
- Optional header: `X-Correlation-Id`
- Output: async operation reference (`operation_id`, `status_url`).

### `POST /rebalance/proposals/{proposal_id}/transitions`
- Purpose: apply one workflow transition.
- Concurrency: `expected_state` required by default (`PROPOSAL_REQUIRE_EXPECTED_STATE=true`).

### `POST /rebalance/proposals/{proposal_id}/approvals`
- Purpose: persist structured approval/consent and corresponding workflow event.
- Approval types: `RISK`, `COMPLIANCE`, `CLIENT_CONSENT`

Persistence note:
- Lifecycle persistence supports repository backends selected by runtime config.
- Postgres-backed persistence is implemented (`PROPOSAL_STORE_BACKEND=POSTGRES`).
- In-memory backend remains available for local/test workflows and emits deprecation warnings.

## Pipeline (`run_proposal_simulation`)

1. Validate and gate
- Requires `options.enable_proposal_simulation=true` at API layer.
- Validates proposal input models (`ProposedCashFlow`, `ProposedTrade`).

2. Before-state valuation
- Uses the same valuation stack as lotus-manage (`build_simulated_state`).

3. Apply proposal intents
- Cash flows can be applied before trades (`proposal_apply_cash_flows_first`).
- Trades are manually supplied and priced from market data.
- For notional-driven trades, `notional.currency` must match priced instrument currency; mismatch blocks with `PROPOSAL_INVALID_TRADE_INPUT`.
- RFC-0014B auto-funding:
  - Build funding plan per BUY currency.
  - Generate `FX_SPOT` intents for deficits using `BASE_ONLY` or `ANY_CASH` policy.
  - Apply deterministic dependencies from BUY intents to generated FX intent ids.
- Deterministic ordering:
  - `CASH_FLOW` (as provided)
  - `SECURITY_TRADE` SELL (instrument ascending)
  - `FX_SPOT` (pair ascending)
  - `SECURITY_TRADE` BUY (instrument ascending)

4. Safety and shelf guards
- Blocks on withdrawal-driven negative cash when enabled (`proposal_block_negative_cash`).
- Blocks disallowed BUY trades (`SELL_ONLY`, `BANNED`, `SUSPENDED`, and `RESTRICTED` unless `allow_restricted=true`).

5. After-state, rules, reconciliation
- Simulates portfolio mutation using shared primitives.
- Runs standard rule engine (`RuleEngine.evaluate`).
- Performs proposal reconciliation against expected cash-flow-adjusted total.
- Derives deterministic `proposal_run_id` from request hash when provided.

## Advisory Feature Flags

- `enable_proposal_simulation`
- `enable_workflow_gates`
- `workflow_requires_client_consent`
- `client_consent_already_obtained`
- `proposal_apply_cash_flows_first`
- `proposal_block_negative_cash`
- `link_buy_to_same_currency_sell_dependency`
- `enable_drift_analytics`
- `enable_suitability_scanner`
- `suitability_thresholds`:
  - `single_position_max_weight`
  - `issuer_max_weight`
  - `max_weight_by_liquidity_tier`
  - `cash_band_min_weight`
  - `cash_band_max_weight`
  - `data_quality_issue_severity`
- `enable_instrument_drift`
- `drift_top_contributors_limit`
- `drift_unmodeled_exposure_threshold`
- `auto_funding`
- `funding_mode`
- `fx_funding_source_currency`
- `fx_generation_policy`
- dependency policy note:
  - `link_buy_to_same_currency_sell_dependency=null` defaults to `false` in advisory.
  - when `true`, BUY security intents also depend on same-currency SELL intents.
- plus shared controls:
  - `block_on_missing_prices`
  - `block_on_missing_fx`
  - `allow_restricted`
  - cash-band options (affect final status via rule engine)

Lifecycle runtime config (env):
- `PROPOSAL_WORKFLOW_LIFECYCLE_ENABLED` (default `true`)
- `PROPOSAL_STORE_EVIDENCE_BUNDLE` (default `true`)
- `PROPOSAL_REQUIRE_EXPECTED_STATE` (default `true`)
- `PROPOSAL_ALLOW_PORTFOLIO_CHANGE_ON_NEW_VERSION` (default `false`)
- `PROPOSAL_REQUIRE_SIMULATION_FLAG` (default `true`)
- `PROPOSAL_SUPPORT_APIS_ENABLED` (default `true`)
- `PROPOSAL_ASYNC_OPERATIONS_ENABLED` (default `true`)

Swagger contract quality:
- Lifecycle request/response models include explicit attribute-level `description` and `examples`.
- Path/query/header parameters include explicit descriptions and examples in router definitions.

## Proposal-Specific Diagnostics/Outcomes

- `PROPOSAL_WITHDRAWAL_NEGATIVE_CASH`
- `PROPOSAL_TRADE_NOT_SUPPORTED_BY_SHELF`
- `PROPOSAL_INVALID_TRADE_INPUT`
- `PROPOSAL_MISSING_FX_FOR_FUNDING`
- `PROPOSAL_INSUFFICIENT_FUNDING_CASH`
- `REFERENCE_MODEL_BASE_CURRENCY_MISMATCH`
- `diagnostics.missing_fx_pairs`
- `diagnostics.funding_plan`
- `diagnostics.insufficient_cash`
- `drift_analysis` (when `reference_model` is provided and drift analytics is enabled)
- `suitability`:
  - `summary` (`new_count`, `resolved_count`, `persistent_count`, `highest_severity_new`)
  - deterministic ordered `issues` classified as `NEW`, `PERSISTENT`, `RESOLVED`
  - `recommended_gate` (`NONE`, `RISK_REVIEW`, `COMPLIANCE_REVIEW`)
- standard safety/data-quality rules continue to apply (`NO_SHORTING`, `INSUFFICIENT_CASH`, etc.)

## Proposal Artifact (RFC-0014E)

Deterministic sections:
- `gate_decision`
- `summary`
- `portfolio_impact`
- `trades_and_funding`
- `suitability_summary`
- `assumptions_and_limits`
- `disclosures`
- `evidence_bundle`

Determinism controls:
- Stable sorting for allocations and FX list.
- Stable trade ordering inherited from proposal simulation ordering policy.
- `artifact_hash` from canonical JSON that excludes volatile fields:
  - `created_at`
  - `evidence_bundle.hashes.artifact_hash`

## Tests That Lock Advisory Behavior

- API: `tests/unit/advisory/api/test_api_advisory_proposal_simulate.py`
- API: `tests/unit/advisory/api/test_api_advisory_proposal_lifecycle.py`
- Contract: `tests/unit/advisory/contracts/test_contract_advisory_models.py`
- Contract: `tests/unit/advisory/contracts/test_contract_proposal_artifact_models.py`
- Engine: `tests/unit/advisory/engine/test_engine_advisory_proposal_simulation.py`
- Engine: `tests/unit/advisory/engine/test_engine_proposal_artifact.py`
- Engine: `tests/unit/advisory/engine/test_engine_proposal_workflow_service.py`
- Engine: `tests/unit/dpm/engine/test_engine_workflow_gates.py`
- Proposal golden: `tests/unit/advisory/golden/test_golden_advisory_proposal_scenarios.py`
- Artifact golden: `tests/unit/advisory/golden/test_golden_advisory_proposal_artifact_scenarios.py`

Dependency quality gate:
- `scripts/dependency_health_check.py --requirements requirements.txt`
- CI runs this check before lint/test to enforce vulnerability visibility.

## Deprecation Notes

- `src/core/advisory/engine.py` is a compatibility shim and emits `DeprecationWarning`.
- Use `src/core/advisory_engine.py` as the current stable advisory engine import path.
