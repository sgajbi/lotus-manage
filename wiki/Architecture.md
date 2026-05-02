# Architecture

## Runtime model

- FastAPI service
- management-side domain logic in `src/core/dpm/` and `src/core/dpm_runs/`
- PostgreSQL-backed persistence and migrations under `src/infrastructure/`
- consumed primarily through `lotus-gateway`
- stateless execution is active and advertised
- stateful core-sourced execution is modeled, guarded, and intentionally disabled until upstream
  resolver certification is complete

```mermaid
flowchart LR
    Gateway[lotus-gateway] --> Manage[lotus-manage FastAPI]
    Manage --> Engine[DPM rebalance engine]
    Manage --> Runs[Run supportability services]
    Manage --> Policies[Policy-pack resolver]
    Runs --> Postgres[(PostgreSQL DPM schema)]
    Policies --> Postgres
    Core[lotus-core source data] -. governed input snapshots .-> Gateway
    Advise[lotus-advise] -. advisor-led proposal workflows .-> Gateway
```

## Execution Modes

```mermaid
flowchart TD
    Request[POST /api/v1/rebalance/simulate or analyze] --> Mode{input_mode}
    Mode -->|stateless| Bundle[Caller supplies portfolio, market data, model, shelf, and options]
    Bundle --> Engine[DPM engine]
    Mode -->|stateful| Gate{Stateful sourcing enabled and core base URL configured?}
    Gate -->|no| Disabled[DPM_STATEFUL_INPUT_DISABLED or DPM_CORE_RESOLVER_UNAVAILABLE]
    Gate -->|yes, future| Core[lotus-core DPM execution context]
    Core --> Transform[Transform governed context to engine input]
    Transform --> Engine
    Engine --> Result[READY, PENDING_REVIEW, or BLOCKED]
    Result --> Supportability[Run record, artifact, lineage, workflow, metrics]
```

The current implemented product mode is `stateless`. Stateful request models, resolver client,
transformation helpers, and lineage fields are present so the integration boundary is explicit, but
capabilities do not advertise stateful execution until the governed `lotus-core` source-data
contract is live-certified.

## Evidence flow

```mermaid
flowchart TD
    Validator[scripts/validate_live_api.py] --> DemoPack[Live demo pack]
    Validator --> Boundary[OpenAPI boundary probes]
    Validator --> Swagger[OpenAPI certification contract]
    Validator --> Capabilities[Capability truth probes]
    Validator --> CoreGuard[Stateful core-sourcing guard]
    Validator --> Supportability[Postgres supportability probes]
    Validator --> Metrics[Bounded metrics probes]
    DemoPack --> Manage[lotus-manage API]
    Boundary --> Manage
    Swagger --> Manage
    Capabilities --> Manage
    CoreGuard --> Manage
    Supportability --> Manage
    Metrics --> Manage
    Manage --> DpmDb[(DPM PostgreSQL schema)]
```

This evidence path is API-first. It certifies `lotus-manage` and its managed core-sourcing posture
before broader Gateway or Workbench product-surface integration is treated as proof.

## Code map

- `src/api/`
  routers, request handling, readiness, observability, and OpenAPI enrichment
- `src/core/dpm/`
  rebalance engine, policy-pack resolution, turnover, settlement, tax, and constraint logic
- `src/core/dpm_runs/`
  async operation, workflow, artifact, and supportability services
- `src/core/common/`
  shared simulation primitives, diagnostics, workflow gates, and canonical helpers
- `src/infrastructure/`
  persistence backends, policy-pack repositories, and PostgreSQL migrations

## Boundary notes

1. `lotus-manage` owns execution decisions produced from governed inputs
2. `lotus-core` remains source-data authority when request inputs are core-referenced
3. `lotus-gateway` is the primary downstream product consumer
4. REST/OpenAPI remains the canonical integration contract
5. capability discovery is backend-owned through `/api/v1/integration/capabilities`
