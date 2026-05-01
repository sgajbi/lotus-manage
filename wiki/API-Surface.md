# API Surface

## Core management surfaces

- `POST /rebalance/simulate`
  deterministic rebalance execution
- `POST /rebalance/analyze`
  synchronous what-if analysis
- `POST /rebalance/analyze/async`
  async what-if orchestration

Async operation correlation ids are unique operation handles. Reusing an existing async
correlation id returns `409 DPM_ASYNC_OPERATION_CORRELATION_CONFLICT` instead of leaking a
storage-layer constraint.

## Run supportability surfaces

- `/rebalance/runs/*`
  run lookup, workflow state, artifacts, and support bundles
- `/rebalance/operations/*`
  async operation status and execution
- `/rebalance/lineage/*`
  lineage traversal
- `/rebalance/idempotency/*`
  idempotency history and replay support
- `/rebalance/supportability/summary`
  store-wide supportability snapshot

## Policy and capability surfaces

- `/rebalance/policies/*`
  effective policy resolution and catalog supportability
- `/integration/capabilities`
- `/platform/capabilities`
  backend-owned feature and workflow discovery for gateway and platform consumers

Default capability posture is intentionally conservative: inline bundle execution is enabled,
stateful `portfolio_id` execution is disabled until a governed `lotus-core` resolver is configured,
and solver target generation is runtime-discovered from installed solver dependencies.

## Platform surfaces

- `/health`
- `/health/live`
- `/health/ready`
- `/docs`
