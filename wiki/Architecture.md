# Architecture

## Runtime model

- FastAPI service
- management-side domain logic in `src/core/dpm/` and `src/core/dpm_runs/`
- PostgreSQL-backed persistence and migrations under `src/infrastructure/`
- consumed primarily through `lotus-gateway`

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

## Evidence flow

```mermaid
flowchart TD
    Validator[scripts/validate_live_api.py] --> DemoPack[Live demo pack]
    Validator --> Boundary[OpenAPI boundary probes]
    Validator --> Capabilities[Capability truth probes]
    Validator --> Supportability[Postgres supportability probes]
    Validator --> Metrics[Bounded metrics probes]
    DemoPack --> Manage[lotus-manage API]
    Boundary --> Manage
    Capabilities --> Manage
    Supportability --> Manage
    Metrics --> Manage
    Manage --> DpmDb[(DPM PostgreSQL schema)]
```

This evidence path is API-first. It is intended for `lotus-manage` certification before broader
Gateway or Workbench integration is treated as a product-surface dependency.

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
5. capability discovery is backend-owned through `/integration/capabilities`
