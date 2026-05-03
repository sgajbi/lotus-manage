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
  explainable heuristic, minimum-turnover, tax-aware, and governed second-wave alternatives with
  explicit supportability and degraded-source posture.
- `GET /api/v1/construction/alternative-sets/{alternative_set_id}`
  retrieves a previously generated alternative set without recomputation.
- `POST /api/v1/construction/alternative-sets/{alternative_set_id}/selections`
  records the actor-attributed selected alternative for audit and later workflow handoff.

These routes are manage-owned backend contracts. Gateway and Workbench are not yet integrated with
this surface; construction-specific realization requirements now live in Gateway RFC-0098,
Workbench RFC-0098, and
[`docs/architecture/dpm-construction-alternatives-gateway-workbench-handoff.md`](../docs/architecture/dpm-construction-alternatives-gateway-workbench-handoff.md).

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
