# lotus-manage

Discretionary portfolio-management execution, supportability, and lifecycle service for the Lotus
ecosystem.

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
2. stateful `portfolio_id` mode must remain anchored to governed `lotus-core` authority
3. remaining advisory or proposal-lifecycle routes in this repo are compatibility or cleanup
   surfaces, not a mandate to expand advisory scope here

## Current Operational Posture

1. `lotus-manage` is the management-side service after the split from `lotus-advise`.
2. Canonical local host runtime uses port `8001` so it can coexist with `lotus-advise` on `8000`.
3. CI already enforces no-alias, OpenAPI, API vocabulary, migration-smoke, and security-audit
   validation.
4. Host/runtime coexistence and gateway-facing capability discovery are part of the operational
   contract.

## Architecture At A Glance

Main runtime surfaces come from [src/api/main.py](src/api/main.py):

- rebalance simulation
  `/rebalance/simulate`, `/rebalance/analyze`, `/rebalance/analyze/async`
- run supportability
  `/rebalance/runs/*`, `/rebalance/operations/*`, `/rebalance/supportability/summary`,
  `/rebalance/lineage/*`, `/rebalance/idempotency/*`
- policy-pack supportability
  `/rebalance/policies/*`
- integration capabilities
  `/integration/capabilities`, `/platform/capabilities`
- compatibility advisory surfaces
  proposal simulation and proposal lifecycle routes that remain present during split cleanup
- platform surfaces
  `/health`, `/health/live`, `/health/ready`, `/docs`

Key code areas:

- `src/api/`
  FastAPI entrypoints, routers, readiness, observability, and OpenAPI enrichment
- `src/core/dpm/`
  discretionary portfolio-management simulation engine and supporting rebalance modules
- `src/core/dpm_runs/`
  async operation, workflow, artifact, and supportability services for rebalance runs
- `src/core/proposals/`
  compatibility proposal-lifecycle models and services still carried in this repo
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

Operationally important truths:

1. readiness and migration posture matter because supportability flows depend on persistence truth
2. capability discovery through `/integration/capabilities` remains backend-owned and uses
   canonical snake_case query parameters
3. compatibility advisory routes should be maintained carefully but should not grow advisory scope

## Documentation Map

- project overview:
  [docs/documentation/project-overview.md](docs/documentation/project-overview.md)
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
