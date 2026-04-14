# RFC-0082 Upstream Contract Family Map

This document records how `lotus-manage` fits the `lotus-platform` RFC-0082 boundary model.

`lotus-manage` owns discretionary portfolio-management execution, rebalance simulation, what-if
analysis, management-side workflow supportability, policy-pack behavior, idempotency, lineage, and
run-support contracts. It does not own canonical portfolio ledger data, market-data source truth,
performance analytics, risk analytics, advisory-only workflow, reporting, or UI experience
composition.

## Current Integration Posture

1. REST/OpenAPI remains the governed integration contract for current `lotus-manage` public and
   integration-facing APIs.
2. No current `lotus-manage` integration requires or justifies gRPC.
3. The current codebase does not contain an active outbound HTTP client to `lotus-core`,
   `lotus-performance`, or `lotus-risk`.
4. `lotus-manage` accepts portfolio snapshots, market-data snapshots, model targets, shelf data, and
   options through request contracts. When those inputs are core-referenced, `lotus-core` remains the
   source-data authority.
5. `lotus-gateway` is the primary product-facing consumer of `lotus-manage` capabilities and workflow
   surfaces.

## `lotus-core` Contract Family Posture

| Manage surface | Upstream authority relationship | RFC-0082 family | Manage use | Boundary rule |
| --- | --- | --- | --- | --- |
| `portfolio_snapshot` request payloads | source data should be `lotus-core`-governed when populated from platform state | Snapshot and simulation / Operational Read input | rebalance and what-if source state | manage may transform for execution, but must not become the ledger or portfolio read authority |
| `market_data_snapshot` request payloads | prices and FX should remain core-governed source data when populated from platform state | Operational Read input / Analytics Input watchlist | valuation, settlement, tax, and rebalance execution support | manage may use inputs for execution, but source truth remains upstream |
| `pas_ref` capability mode | references platform-owned state rather than accepting a full inline bundle | Snapshot and simulation input | stateful DPM execution posture advertised through capabilities | future stateful resolution must use governed core contracts rather than ad hoc reads |
| inline bundle mode | caller supplies full input bundle | Local execution input | deterministic local simulation and analysis | bundle acceptance does not transfer source-data authority to manage |

## Manage-Owned Contract Families

| Surface | Route family | Owner | Boundary rule |
| --- | --- | --- | --- |
| rebalance simulation | `POST /rebalance/simulate` | `lotus-manage` | owns deterministic DPM execution result, policy application, controls, and workflow gate output |
| what-if analysis | `POST /rebalance/analyze`, `POST /rebalance/analyze/async` | `lotus-manage` | owns scenario orchestration and run correlation semantics |
| async operation execution | `/rebalance/operations/*` | `lotus-manage` | owns management-side operation state and supportability |
| run supportability | `/rebalance/runs/*`, `/rebalance/supportability/summary` | `lotus-manage` | owns run lookup, lineage, idempotency mapping, support bundles, and deterministic artifacts |
| policy-pack supportability | `/rebalance/policies/*` | `lotus-manage` | owns DPM policy-pack selection and diagnostics |
| integration capabilities | `/integration/capabilities`, `/platform/capabilities` | `lotus-manage` | owns feature/workflow capability truth for gateway and platform consumers |

## Split-Boundary Posture

`lotus-advise` is the advisory workflow and proposal simulation authority after the repository split.
Any remaining advisory-labeled or proposal-lifecycle surface in `lotus-manage` is treated as
compatibility or managed cleanup surface unless a current repo RFC explicitly keeps it here.

Boundary rules:

1. advisor-led proposal workflow should not expand in `lotus-manage`,
2. new advisory decision-summary, alternatives, suitability, or consent behavior belongs in
   `lotus-advise`,
3. gateway-facing management workflow should consume `lotus-manage` for DPM execution and
   supportability only.

## Conformance Rules

1. `lotus-manage` may own execution decisions produced by its DPM engine from governed inputs.
2. `lotus-manage` must not own canonical portfolio state, account state, transaction state, price
   source truth, FX source truth, performance attribution, benchmark-relative interpretation, or risk
   methodology.
3. `pas_ref` and future stateful input modes must be implemented through governed `lotus-core`
   snapshot, operational-read, analytics-input, or control-plane contracts.
4. Inline bundle behavior must preserve lineage identifiers for portfolio and market-data snapshots so
   callers can trace source authority.
5. Gateway capability consumers must receive backend-owned feature and workflow truth from
   `/integration/capabilities`; UI or gateway layers must not infer manage feature flags.
6. Transport optimization discussions start with request shape, payload size, async execution,
   idempotency, caching, and supportability. gRPC is not a default answer for management workflows.

## Current Evidence

Existing tests that cover this posture include:

1. `tests/unit/dpm/api/test_integration_capabilities_api.py`
2. `tests/unit/dpm/api/test_api_rebalance.py`
3. `tests/unit/dpm/engine/test_engine_core_flows.py`
4. `tests/unit/dpm/engine/test_engine_valuation_service.py`
5. `tests/unit/dpm/engine/test_engine_workflow_gates.py`
6. `tests/unit/dpm/supportability/test_dpm_run_workflow_service.py`
7. `tests/unit/dpm/supportability/test_dpm_lineage_service.py`
8. `tests/unit/dpm/supportability/test_dpm_idempotency_history_service.py`
9. `tests/unit/dpm/contracts/test_contract_openapi_supportability_docs.py`
10. `tests/integration/dpm/api/test_dpm_api_workflow_integration.py`
11. `tests/integration/dpm/supportability/test_dpm_postgres_repository_integration.py`
12. `tests/integration/dpm/supportability/test_dpm_policy_pack_postgres_repository_integration.py`

This RFC-0082 documentation slice did not change runtime behavior, OpenAPI output, migrations, or
upstream request/response contracts.

## Gap Register

1. `pas_ref` is advertised as a supported input mode, but the current code inspection did not find an
   active outbound state-resolution client. When that becomes active, classify the exact `lotus-core`
   routes before stabilizing the contract.
2. Inline portfolio and market-data bundles are operationally useful, but they can blur source-data
   authority. Keep snapshot identifiers, request hashes, and supportability bundles mandatory for
   traceability.
3. Remaining advisory/proposal-lifecycle surfaces in `lotus-manage` should not receive new advisory
   scope unless a split-governance decision explicitly keeps them here.
4. If DPM simulation becomes latency-constrained, prefer async execution, payload shaping, policy-pack
   caching, and source-data retrieval design before considering a transport change.

## Validation Lane

This document is governed as Feature Lane documentation and contract proof. Escalate to PR Merge Gate
only when a future slice changes management runtime behavior, public API contracts, migrations, or
upstream coupling.
