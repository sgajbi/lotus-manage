# Architecture

## Runtime model

- FastAPI service
- management-side domain logic in `src/core/rebalance/` and `src/core/rebalance_runs/`
- PostgreSQL-backed persistence and migrations under `src/infrastructure/`
- consumed primarily through `lotus-gateway`
- stateless execution is active and advertised
- stateful core-sourced execution is implemented behind explicit runtime gates and advertised only
  when core source-product readiness, stateful capability flags, and resolver configuration prove
  the posture

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
    Gate -->|yes| Core[lotus-core RFC-087 source products]
    Core --> Transform[Transform governed context to engine input]
    Transform --> Engine
    Engine --> Result[READY, PENDING_REVIEW, or BLOCKED]
    Result --> Supportability[Run record, artifact, lineage, workflow, metrics]
```

The default product mode is `stateless`. Stateful request models, resolver client, transformation
helpers, and lineage fields are implemented behind explicit runtime gates. Capabilities advertise
stateful execution only when `DPM_CAP_INPUT_MODE_PORTFOLIO_ID_ENABLED`,
`DPM_STATEFUL_CORE_SOURCING_ENABLED`, and `DPM_CORE_BASE_URL` prove a usable core-sourcing posture.

## Target DPM Operating System Architecture

```mermaid
flowchart TD
    Core[lotus-core<br/>portfolio, mandate, model, tax, cash, FX, eligibility]
    Risk[lotus-risk<br/>risk, stress, concentration]
    Perf[lotus-performance<br/>returns, attribution, outcome]
    Manage[lotus-manage<br/>DPM operating system]
    Report[lotus-report<br/>client, PM, audit packs]
    AI[lotus-ai<br/>governed PM copilot]
    Gateway[lotus-gateway]
    Workbench[lotus-workbench]

    Core --> Manage
    Risk --> Manage
    Perf --> Manage
    Manage --> Report
    Manage --> AI
    Manage --> Gateway
    Gateway --> Workbench
```

Target-state RFCs may redesign or delete existing manage APIs. The architecture preference is a
clean, certified, domain-driven `/api/v1` contract rather than backward-compatible aliases for stale
or poorly named endpoints.

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

## Mandate Command-Center Flow

RFC-0038 introduces a command-center foundation for discretionary mandate supervision. The
backend-owned flow is:

```mermaid
flowchart TD
    Core[lotus-core source products] --> Twin[Mandate digital twin]
    Twin --> Health[Mandate health score]
    Health --> Run[DPM monitoring run]
    Run --> Exceptions[Monitoring exceptions]
    Run --> Command[Command-center summary]
    Exceptions --> Command
    Command --> Gateway[lotus-gateway product contract]
    Gateway --> Workbench[Workbench PM cockpit]
```

The important boundary is that `lotus-manage` owns health and command-center truth, while Gateway
and Workbench own composition and presentation. Workbench should not call `lotus-manage` directly or
reconstruct health state client-side.

## Construction Alternatives Flow

RFC-0039 introduces a construction-alternative foundation for discretionary mandate decisioning.
The backend-owned flow is:

```mermaid
flowchart TD
    Core[lotus-core source products] --> Context[Stateful or stateless construction context]
    Context --> Methods[Construction method registry]
    Methods --> Baseline[Do-nothing baseline]
    Methods --> Heuristic[Explainable heuristic]
    Methods --> Turnover[Minimum-turnover posture]
    Methods --> Tax[Tax-aware posture]
    Baseline --> Set[Persisted alternative set]
    Heuristic --> Set
    Turnover --> Set
    Tax --> Set
    Set --> Select[Actor-attributed selection]
    Select --> Gateway[Future gateway construction module]
    Gateway --> Workbench[Future construction lab]
```

The important boundary is that `lotus-manage` owns construction alternatives and selection truth.
Gateway and Workbench must consume that truth without recomputing construction methods or bypassing
the experience API. The downstream handoff is maintained in
[`docs/architecture/dpm-construction-alternatives-gateway-workbench-handoff.md`](../docs/architecture/dpm-construction-alternatives-gateway-workbench-handoff.md).

## Code map

- `src/api/`
  routers, request handling, readiness, observability, and OpenAPI enrichment
- `src/core/rebalance/`
  rebalance engine, policy-pack resolution, turnover, settlement, tax, and constraint logic
- `src/core/rebalance_runs/`
  async operation, workflow, artifact, and supportability services
- `src/core/mandates.py`
  RFC-0038 mandate digital-twin, health-score, and monitoring-exception domain foundation
- `src/core/mandate_repository.py` and `src/infrastructure/mandates/`
  RFC-0038 mandate, health, and monitoring-exception repository contract plus in-memory and
  Postgres-backed persistence foundation
- `src/api/routers/mandates.py` and `src/api/services/mandate_service.py`
  RFC-0038 mandate refresh, read, version, diff, health, monitoring orchestration, and exception
  service foundation backed by product-specific `lotus-core` sourcing and the mandate repository
- `src/api/routers/monitoring.py`
  RFC-0038 bounded monitoring run, exception queue, and command-center summary APIs
- `docs/architecture/dpm-command-center-gateway-workbench-handoff.md`
  RFC-0038 downstream integration handoff for Gateway and Workbench command-center adoption
- `src/core/construction/`, `src/api/routers/construction.py`,
  `src/api/services/construction_service.py`, and `src/infrastructure/construction/`
  RFC-0039 construction-alternative domain, API, service, and persistence foundation
- `docs/architecture/dpm-construction-alternatives-gateway-workbench-handoff.md`
  RFC-0039 downstream integration handoff for Gateway and Workbench construction-lab adoption
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
