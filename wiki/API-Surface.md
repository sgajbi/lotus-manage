# API Surface

## Core management surfaces

- `POST /rebalance/simulate`
  deterministic rebalance execution
- `POST /rebalance/analyze`
  synchronous what-if analysis
- `POST /rebalance/analyze/async`
  async what-if orchestration

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

## Compatibility surfaces

- advisory simulation and proposal lifecycle routes remain present in the router layout
- treat them as compatibility or managed cleanup scope unless a current repo RFC says otherwise

## Platform surfaces

- `/health`
- `/health/live`
- `/health/ready`
- `/docs`
