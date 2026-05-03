# API Surface

## Core management surfaces

- `POST /api/v1/rebalance/simulate`
  deterministic rebalance execution
- `POST /api/v1/rebalance/analyze`
  synchronous what-if analysis
- `POST /api/v1/rebalance/analyze/async`
  async what-if orchestration

Async operation correlation ids are unique operation handles. Reusing an existing async
correlation id returns `409 DPM_ASYNC_OPERATION_CORRELATION_CONFLICT` instead of leaking a
storage-layer constraint.

## Run supportability surfaces

- `/api/v1/rebalance/runs/*`
  run lookup, workflow state, artifacts, and support bundles
- `/api/v1/rebalance/operations/*`
  async operation status and execution
- `/api/v1/rebalance/lineage/*`
  lineage traversal
- `/api/v1/rebalance/idempotency/*`
  idempotency history and replay support
- `/api/v1/rebalance/supportability/summary`
  store-wide supportability snapshot

## Policy and capability surfaces

- `/api/v1/rebalance/policies/*`
  effective policy resolution and catalog supportability
- `/api/v1/integration/capabilities`
  backend-owned feature and workflow discovery for gateway and platform consumers

## Construction alternative surfaces

- `POST /api/v1/construction/alternative-sets/generate`
  generates and persists a comparable RFC-0039 construction alternative set with do-nothing,
  explainable heuristic, minimum-turnover, tax-aware, solver-constrained, risk-aware,
  liquidity-aware, currency-overlay, and regime-stress-aware alternatives with explicit
  supportability and source-authority posture. ESG/restriction-aware construction is intentionally
  deferred until source-backed restriction and sustainability profiles exist.
- `GET /api/v1/construction/alternative-sets/{alternative_set_id}`
  retrieves a previously generated alternative set without recomputation.
- `POST /api/v1/construction/alternative-sets/{alternative_set_id}/selections`
  records the actor-attributed selected alternative for audit and later workflow handoff.

These routes are manage-owned backend contracts. Gateway and Workbench are not yet integrated with
this surface; construction-specific realization requirements now live in Gateway RFC-0098,
Workbench RFC-0098, and
[`docs/architecture/dpm-construction-alternatives-gateway-workbench-handoff.md`](../docs/architecture/dpm-construction-alternatives-gateway-workbench-handoff.md).

## Proof-pack surfaces

- `POST /api/v1/rebalance/proof-packs`
  generates and persists an immutable RFC-0040 pre-trade proof pack from a persisted rebalance run
  or selected RFC-0039 construction alternative. Calls require `Idempotency-Key` and preserve
  source-backed degraded or blocked section states instead of inventing missing evidence.
- `GET /api/v1/rebalance/proof-packs/{proof_pack_id}`
  retrieves the persisted proof-pack JSON contract with section states, hashes, lineage, retention
  posture, source references, and supportability summary.
- `GET /api/v1/rebalance/proof-packs/{proof_pack_id}/summary.md`
  renders deterministic human-readable Markdown from the persisted proof pack.
- `GET /api/v1/rebalance/proof-packs/{proof_pack_id}/report-input`
  returns the generated report-input evidence reference when present. Before Slice 7 adapters
  generate the ref, the endpoint truthfully returns `424`.
- `GET /api/v1/rebalance/proof-packs/{proof_pack_id}/ai-evidence-input`
  returns the generated AI-evidence input reference when present. Before Slice 7 adapters generate
  the ref, the endpoint truthfully returns `424`.

These are manage-owned backend authority endpoints. Gateway and Workbench must consume these
contracts later without reconstructing proof-pack evidence. Report materialization and AI memo
generation remain downstream responsibilities and are not claimed by this API slice.

Default capability posture is intentionally conservative: inline bundle execution is enabled,
stateful `portfolio_id` execution is disabled until a governed `lotus-core` resolver is configured,
and solver target generation is runtime-discovered from installed solver dependencies.

Source-service callers must use the canonical snake_case query parameters `consumer_system` and
`tenant_id`. Gateway may expose camelCase on its public BFF contract, but direct calls into
`lotus-manage` should not rely on Gateway naming.

Endpoint certification details are tracked in [Endpoint Certification](Endpoint-Certification).

## Platform surfaces

- `/health`
  lightweight service health
- `/health/live`
  process liveness without persistence dependency checks
- `/health/ready`
  readiness with persistence guardrails and production migration cutover validation
- `/docs`
