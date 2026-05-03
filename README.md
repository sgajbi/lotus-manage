# lotus-manage

Discretionary mandate portfolio-management execution, workflow review, and operational
supportability service for the Lotus ecosystem.

Repository-local engineering context:
[REPOSITORY-ENGINEERING-CONTEXT.md](REPOSITORY-ENGINEERING-CONTEXT.md)

RFC-0082 upstream contract-family map:
[docs/standards/RFC-0082-upstream-contract-family-map.md](docs/standards/RFC-0082-upstream-contract-family-map.md)

## Purpose And Scope

`lotus-manage` owns management-side workflows:

- deterministic rebalance simulation
- multi-scenario what-if analysis
- async operation execution and polling
- run supportability, lineage, idempotency, and artifact retrieval
- policy-pack resolution and management-side workflow gating

It does not own advisor-led proposal workflows. Those belong to `lotus-advise`.

It also does not own canonical portfolio ledger data, market-data truth, risk methodology, or
performance analytics authority.

## Ownership And Boundaries

`lotus-manage` is the management-side execution and supportability authority, but it is not the
system of record for the upstream portfolio ecosystem.

It depends on:

- `lotus-core`
  source-data authority for core-referenced portfolio, market-data, price, and FX inputs
- `lotus-gateway`
  primary product-facing consumer of rebalance, supportability, and capability-discovery surfaces

Current posture under RFC-0082:

1. rebalance simulation, policy-pack behavior, async operations, and run-support contracts are
   owned here
2. `input_mode=stateless` is the supported default execution mode for caller-supplied source
   bundles
3. stateful `portfolio_id` mode is implemented behind explicit runtime gates and remains anchored
   to governed `lotus-core` authority; it is advertised in `/api/v1/integration/capabilities` only
   when the stateful capability flag, stateful sourcing gate, and `DPM_CORE_BASE_URL` are all
   configured, and the retired monolithic core route is not configured
4. advisor-led proposal simulation, artifacts, consent, and lifecycle workflows are out of scope
   for this repository and belong in `lotus-advise`

## Current Operational Posture

1. `lotus-manage` is the management-side service after the split from `lotus-advise`.
2. Canonical local host runtime uses port `8001` so it can coexist with `lotus-advise` on `8000`.
3. CI enforces no-alias, OpenAPI, API vocabulary, migration-smoke, security-audit validation, and
   a 99% coverage gate across the unit, integration, and e2e pyramid.
4. Host/runtime coexistence and gateway-facing capability discovery are part of the operational
   contract.
5. Solver-capable development and CI installs include the `solver` extra (`cvxpy` and `numpy`) so
   solver-mode target generation is validated instead of silently skipped.

## Strategic DPM Roadmap

RFC-0037 through RFC-0043 define the revamp from a certified rebalance/supportability service into
a discretionary mandate portfolio-management operating system.

RFC-0038 is now implementation-backed for the mandate digital-twin, health-score, monitoring, and
command-center backend foundation. RFC-0039 is implementation-backed for the manage-side
construction-alternative foundation: first-wave and authority-backed generate/read/select APIs,
do-nothing baseline, explainable heuristic, minimum-turnover, tax-aware, solver-constrained,
risk-aware, liquidity-aware, currency-overlay, and regime-stress-aware methods. ESG/restriction-aware
construction is explicitly deferred until source-backed restriction and sustainability profiles
exist. Postgres persistence, live proof, and downstream Gateway/Workbench realization requirements
are documented, but full product-surface support still requires Gateway and Workbench implementation
and proof. RFC-0040 is now implementation-backed for manage-owned pre-trade proof packs: durable
JSON, deterministic Markdown, report-input handoff, AI-evidence handoff, hashes, lineage, retention
metadata, immutable persistence, certified APIs, and canonical Postgres-backed live proof. Gateway
composition, Workbench review UX, report materialization, and AI memo generation remain downstream
work in their owning apps. The remaining target-state RFCs cover decision timelines, CIO/model-change
rebalance waves, post-trade outcome feedback, and governed AI PM support. Target-state features are
not support claims until the owning RFC is implemented, certified, live-proven, and reflected in
[wiki/Supported-Features.md](wiki/Supported-Features.md).

The revamp is strategic-first: duplicate, stale, advisory-era, or poorly named APIs may be removed
or redesigned rather than preserved for backward compatibility. Future gateway and Workbench
integration should be rebuilt against the certified target contract.

## Architecture At A Glance

Main runtime surfaces come from [src/api/main.py](src/api/main.py):

- rebalance simulation
  `/api/v1/rebalance/simulate`, `/api/v1/rebalance/analyze`, `/api/v1/rebalance/analyze/async`
- run supportability
  `/api/v1/rebalance/runs/*`, `/api/v1/rebalance/operations/*`, `/api/v1/rebalance/supportability/summary`,
  `/api/v1/rebalance/lineage/*`, `/api/v1/rebalance/idempotency/*`
- policy-pack supportability
  `/api/v1/rebalance/policies/*`
- mandate digital twin and health
  `/api/v1/mandates/*`
- DPM monitoring, exceptions, and command center
  `/api/v1/dpm/monitoring/*`, `/api/v1/dpm/exceptions*`, `/api/v1/dpm/command-center`
- construction alternatives
  `/api/v1/construction/alternative-sets/generate`,
  `/api/v1/construction/alternative-sets/{alternative_set_id}`,
  `/api/v1/construction/alternative-sets/{alternative_set_id}/selections`
- integration capabilities
  `/api/v1/integration/capabilities`
- platform surfaces
  `/health`, `/health/live`, `/health/ready`, `/docs`

Key code areas:

- `src/api/`
  FastAPI entrypoints, routers, readiness, observability, and OpenAPI enrichment
- `src/core/rebalance/`
  discretionary portfolio-management simulation engine and supporting rebalance modules
- `src/core/dpm_source_context.py`
  stateful source-context models and transformation helpers for governed core sourcing
- `src/core/mandates.py`
  mandate digital-twin, mandate health, monitoring exception, monitoring run, and command-center
  domain models
- `src/core/rebalance_runs/`
  async operation, workflow, artifact, and supportability services for rebalance runs
- `src/api/routers/mandates.py` and `src/api/routers/monitoring.py`
  mandate, health, monitoring-run, exception, and command-center API routers
- `src/infrastructure/mandates/`
  in-memory and PostgreSQL mandate/health/monitoring repository implementations
- `src/infrastructure/core_sourcing/`
  bounded `lotus-core` resolver client that composes RFC-087 source products for stateful execution
- `src/infrastructure/`
  PostgreSQL migrations, repository backends, and policy-pack persistence
- `docs/`
  project overview, RFCs, runbooks, standards, and operational documentation

## Quick Start

Install dependencies:

```bash
make install
```

Run the service locally on the default development port:

```bash
make run
```

Run the canonical host runtime that coexists with `lotus-advise`:

```bash
make run-canonical
```

API docs endpoint: `/docs`

## Validation And CI Lanes

`lotus-manage` follows the Lotus multi-lane model:

1. `Remote Feature Lane`
2. `Pull Request Merge Gate`
3. `Main Releasability Gate`

Repo-native gate mapping:

- `make check`
  lint, no-alias, typecheck, OpenAPI gate, API vocabulary gate, and unit tests
- `make ci`
  merge-gate style local proof with migration smoke, full coverage-backed tests, and security audit
- `make ci-local`
  local feature-lane split by unit, integration, and e2e coverage phases
- `make ci-local-docker`
  Docker parity for the local CI contract
- `make live-api-validate`
  live API evidence against a running `lotus-manage` instance
- `make live-api-validate-core`
  live API evidence against `lotus-manage` plus current `lotus-core` DPM source-product posture;
  set `LOTUS_MANAGE_EXPECT_STATEFUL_CORE_SOURCING=available` when RFC-087 source products and
  stateful manage gates are active
- `make mesh-contract-validate`
  repo-native domain product, trust telemetry, and observability monitoring contract validation
  against Lotus platform governance

When the README changes, also run:

```bash
python -m pytest tests/unit/test_local_docker_runtime_contract.py -q
```

That test protects the local Docker runtime contract language.

When DPM supportability or OpenAPI-facing docs change materially, also run:

```bash
python -m pytest tests/unit/dpm/contracts/test_contract_openapi_supportability_docs.py -q
```

## Runtime And Docker Posture

Canonical host runtime:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/Start-CanonicalManage.ps1
```

This starts `lotus-manage` on host port `8001` so it can coexist with `lotus-advise` on `8000`
while remaining reachable through canonical ingress as `http://manage.dev.lotus`.

Local Docker runtime does not publish the internal PostgreSQL port by default.
`postgres:5432` remains internal to the Compose network, and only the application port `8000`
is published for local API access.

Docker startup applies the forward-only PostgreSQL migrations before `uvicorn` starts, and the
container healthcheck uses `/health/ready` rather than `/docs`. In production profile,
`/health/ready` validates persistence guardrails and applied migration versions so supportability
APIs cannot look healthy while their backing store is missing or unmigrated.

Async scenario analysis defaults to inline execution in Docker. For accept-now/execute-later live
proof, start the stack with `DPM_ASYNC_EXECUTION_MODE=ACCEPT_ONLY`; manual execution can be disabled
with `DPM_ASYNC_MANUAL_EXECUTION_ENABLED=false` when the execute endpoint must be hidden.
Lineage lookup remains feature-gated by default; set `DPM_LINEAGE_APIS_ENABLED=true` when running
lineage endpoint certification or supportability incident drills.
Idempotency history remains feature-gated by default; set
`DPM_IDEMPOTENCY_HISTORY_APIS_ENABLED=true` for retry-history certification or incident drills.

Operationally important truths:

1. readiness and migration posture matter because supportability flows depend on persistence truth
2. capability discovery through `/api/v1/integration/capabilities` remains backend-owned and uses
   canonical snake_case query parameters
3. advisory proposal routes should be served by `lotus-advise`, not reintroduced here
4. stateful DPM promotion requires `make live-api-validate-core` to pass with
   `LOTUS_MANAGE_EXPECT_STATEFUL_CORE_SOURCING=available` after `lotus-core` exposes the
   RFC-087 certified source-data products and canonical data is seeded

## Documentation Map

- project overview:
  [docs/documentation/project-overview.md](docs/documentation/project-overview.md)
- architecture review ledger:
  [docs/architecture/CODEBASE-REVIEW-LEDGER.md](docs/architecture/CODEBASE-REVIEW-LEDGER.md)
- DPM command-center gateway and Workbench handoff:
  [docs/architecture/dpm-command-center-gateway-workbench-handoff.md](docs/architecture/dpm-command-center-gateway-workbench-handoff.md)
- operations and CI strategy:
  [docs/operations/development-workflow-and-ci-strategy.md](docs/operations/development-workflow-and-ci-strategy.md)
- service runbook:
  [docs/runbooks/service-operations.md](docs/runbooks/service-operations.md)
- RFC index:
  [docs/rfcs/README.md](docs/rfcs/README.md)
- local standards:
  [docs/standards](docs/standards)

## Wiki Source

Repository-authored wiki pages live under [wiki/](wiki). If the GitHub wiki is published later,
keep `wiki/` as the canonical source and treat any separate `*.wiki.git` clone as publication
plumbing only.
