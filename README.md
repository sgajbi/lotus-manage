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
   to governed `lotus-core` authority. Manage composes the current source products and consumes
   `DpmSourceReadiness:v1` as the source-family promotion gate before treating stateful execution
   context as ready; it is advertised in `/api/v1/integration/capabilities` only when the stateful
   capability flag, stateful sourcing gate, and `DPM_CORE_BASE_URL` are all configured, and the
   retired monolithic core route is not configured. `DPM_CORE_QUERY_BASE_URL` is also required when
   stateful construction consumes query-plane source products such as `PortfolioCashflowProjection:v1`.
4. advisor-led proposal simulation, artifacts, consent, and lifecycle workflows are out of scope
   for this repository and belong in `lotus-advise`

## Current Operational Posture

1. `lotus-manage` is the management-side service after the split from `lotus-advise`.
2. Canonical local host runtime uses port `8001` so it can coexist with `lotus-advise` on `8000`.
3. CI enforces no-alias, OpenAPI, API vocabulary, migration-smoke, security-audit validation, a
   99% coverage gate across the unit, integration, and e2e pyramid, and semantic test-family
   breadth so proof loss cannot hide behind total coverage.
4. Host/runtime coexistence and gateway-facing capability discovery are part of the operational
   contract.
5. Solver-capable development and CI installs include the `solver` extra (`cvxpy` and `numpy`) so
   solver-mode target generation is validated instead of silently skipped.

## Strategic DPM Roadmap

RFC-0037 through RFC-0043 define the revamp from a certified rebalance/supportability service into
a discretionary mandate portfolio-management operating system.

RFC-0038 is implementation-backed for the mandate digital twin, health-score engine, derived
monitoring exceptions, persistence foundation, and the mandate, health, monitoring and
command-centre APIs. For slice-level status - what is certified and what remains - the authoritative sources are the RFCs
under [`docs/rfcs/`](docs/rfcs/) and
[Supported Features](https://github.com/sgajbi/lotus-manage/wiki/Supported-Features), which are
updated as work merges. The [Roadmap](https://github.com/sgajbi/lotus-manage/wiki/Roadmap) wiki page
is the readable summary over them. Three of its rows were found trailing the RFCs while this change
was in review; two are corrected and the third is pinned by a documentation test
([#652](https://github.com/sgajbi/lotus-manage/issues/652)), so prefer the RFCs and Supported
Features where the two disagree.

What Manage consumes from upstream is declared, not narrated:
`contracts/domain-data-products/lotus-manage-consumers.v1.json` governs 29 source-product
dependencies under RFC-0084 - 24 from `lotus-core`, 3 from `lotus-risk`, and one each from
`lotus-performance` and `lotus-advise` - each with its required trust metadata, migration posture
and consumption mode. Six are the external treasury and execution products -
`ExternalCurrencyExposure`, `ExternalHedgePolicy`, `ExternalFXForwardCurve`,
`ExternalEligibleHedgeInstrument`, `ExternalHedgeExecutionReadiness` and
`ExternalOrderExecutionAcknowledgement` - which Core exposes as fail-closed routes and which Manage
preserves in construction diagnostics as blocked external evidence rather than treating as
available. That file is the authority; read it rather than a prose list, which cannot stay current.

RFC-0040 is implementation-backed for Manage-owned pre-trade proof packs - durable JSON,
deterministic Markdown, report-input and AI-evidence handoffs, hashes, lineage, retention metadata,
immutable persistence, certified APIs, and source-backed mandate-context attachment. Downstream
realization has landed in the owning apps: Gateway composition and Workbench review UX, report
materialization in `lotus-render`/`lotus-report`/`lotus-archive`, and governed AI PM memo support in
`lotus-ai`/`lotus-gateway`/`lotus-workbench`. Proof packs support **internal review only** - the
handoffs carry `DPM_PROOF_PACK_CLIENT_COMMUNICATION_BOUNDARY` evidence so no consumer can read them
as client contact, client-ready message generation, client approval, delivery confirmation or
communication audit truth.

PM operating quality is governed rather than merely implemented. Scoring is documented in
[docs/methodologies/pm-quality/scoring-and-fairness.md](docs/methodologies/pm-quality/scoring-and-fairness.md).
It is **disabled by default**; enabled policies require bank approval and fairness-review evidence,
and the paths fail closed on missing required evidence, invalid or expired governance approval, and
unauthorized actors. HR, compensation, conduct-enforcement and autonomous-ranking uses are
prohibited and sit outside the product contract.

One consumption path is worth stating here because it changes how a caller builds a request:
`BULK_REVIEW_CAMPAIGN` preview and create can resolve their candidate set from `lotus-core`
`DpmPortfolioUniverseCandidate:v1` by setting `campaign_candidate_source=CORE_DPM_PORTFOLIO_UNIVERSE`.
In that mode Manage preserves Core candidate lineage, rejects caller-supplied portfolios, walks
bounded continuation pages to terminal exhaustion, and fails closed on unavailable, incomplete,
degraded, empty, duplicate, non-terminating or still-truncated Core pages. It claims no
relationship householding, no global portfolio-universe ownership, no PM ranking, no external
workflow orchestration, no OMS execution and no client-communication workflow. See
[Supported Features](https://github.com/sgajbi/lotus-manage/wiki/Supported-Features) for the full
posture.

The per-PR integration history for those products previously sat here as a single 470-line
paragraph of cross-repo PR numbers and commit SHAs. It is in the commit history and the RFCs, where
it is searchable and attributable.

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
  Portfolio-scoped supportability summary responses carry Manage-generated receipt time,
  authoritative mandate-health evidence as-of date when available, and a closed temporal identity
  status. Downstream consumers must fail closed rather than substitute request dates or caller
  clocks when temporal identity is missing or mixed. Current preserved mandate-health refs do not
  carry source-owned Risk/Performance as-of dates, so downstream proof must treat
  `missing_source_evidence` as non-certifying until that owner evidence is preserved.
- idea action-intake receipt
  `/api/v1/rebalance/idea-action-intake` accepts source-safe `lotus-idea`
  conversion-intent handoff evidence and returns a not-certified executable receipt with trusted
  local/dev caller scope, idempotency conflict detection, replay, and accepted/rejected outcomes.
  It does not create action-register records, approve rebalances, create orders, route OMS
  instructions, contact clients, authorize publication, bind production IdP claims, or promote a
  supported feature. It is represented as route-foundation evidence, not as a certified
  `PortfolioActionRegister:v1` serving route.
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
- rebalance waves
  `/api/v1/rebalance/waves`, `/api/v1/rebalance/waves/preview`,
  `/api/v1/rebalance/waves/{wave_id}`, `/api/v1/rebalance/waves/{wave_id}/items`,
  `/api/v1/rebalance/waves/{wave_id}/source-check`,
  `/api/v1/rebalance/waves/{wave_id}/simulate`,
  `/api/v1/rebalance/waves/{wave_id}/items/{wave_item_id}/select`,
  `/api/v1/rebalance/waves/{wave_id}/approve`, `/api/v1/rebalance/waves/{wave_id}/stage`,
  `/api/v1/rebalance/waves/{wave_id}/handoff`, `/api/v1/rebalance/waves/{wave_id}/cancel`,
  `/api/v1/rebalance/waves/{wave_id}/proof-pack`,
  `/api/v1/rebalance/waves/{wave_id}/report-input`,
  `/api/v1/rebalance/waves/{wave_id}/supportability`
  Bulk-review campaign membership is catalog-visible but mesh-deferred/future-wave in trust
  telemetry until product-specific platform policy and runtime certification evidence are promoted.
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
  lint, no-alias, typecheck, OpenAPI gate, API vocabulary gate, test-family inventory, and unit
  tests
- `make test-unit`, `make test-integration`, `make test-e2e`
  repo-native suite execution; override paths with `UNIT_TESTS`, `INTEGRATION_TESTS`, or
  `E2E_TESTS` for focused local proof
- `make test-unit-coverage`, `make test-integration-coverage`, `make test-e2e-coverage`
  repo-native suite coverage execution used by PR Merge and Main Releasability workflows; the
  combined coverage decision remains `make coverage-gate`
- `make test-family-inventory`
  validates the current test proof-family baseline in `quality/test_family_inventory_baseline.json`
  across API/runtime, contract/governance, observability/security, domain/lifecycle/methodology,
  integration/runtime, and uncategorized tests
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
  the canonical source-ready stack defaults to `LOTUS_MANAGE_EXPECT_STATEFUL_CORE_SOURCING=available`
  because RFC-087 source products and stateful manage gates are active. Set
  `LOTUS_MANAGE_EXPECT_STATEFUL_CORE_SOURCING=disabled` only when deliberately validating a
  non-source-ready local runtime.
- `make demo-certify`
  app-level demo certification against the canonical live stack. It writes machine-readable
  evidence to `output/live-api/demo-certification/summary.json` by default and asserts capability
  truth, stateful source-backed construction, supportability persistence, metrics, and retired
  route absence for `PB_SG_GLOBAL_BAL_001` as of `2026-04-10`.
- `make mesh-contract-validate`
  repo-native domain product, trust telemetry, and observability monitoring contract validation
  against Lotus platform governance. PM-quality trust telemetry is intentionally
  certification-blocked until linked PM-quality blockers are merged to `main` and runtime trust
  evidence is regenerated; catalog visibility is not customer-reliance certification.

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
`/health/ready` validates persistence guardrails, applied migration versions, and trusted write
authorization posture so supportability APIs cannot look healthy while their backing store,
authz enforcement, primary key id, or capability policy is missing. The checked-in Compose defaults
enable authz for local production-profile proof; real deployments must replace the local key id and
capability policy with bank-managed identity configuration.

Runtime Postgres adapters use one bounded access policy instead of direct unbounded driver calls.
Production operators should set and monitor:

- `DPM_POSTGRES_MAX_CONNECTIONS` (default `10`, allowed `1..100`)
- `DPM_POSTGRES_CONNECT_TIMEOUT_SECONDS` (default `3`, allowed `1..30`)
- `DPM_POSTGRES_STATEMENT_TIMEOUT_MS` (default `5000`, allowed `100..60000`)
- `DPM_POSTGRES_IDLE_IN_TRANSACTION_TIMEOUT_MS` (default `10000`, allowed `1000..120000`)
- `DPM_POSTGRES_ACQUIRE_TIMEOUT_SECONDS` (default `2`, allowed `1..30`)

Invalid values fail production readiness with `POSTGRES_ACCESS_POLICY_INVALID:*` or
`POSTGRES_ACCESS_POLICY_OUT_OF_RANGE:*`. Runtime acquisition and driver failures emit sanitized
`lotus_manage_postgres_access_total` metrics and structured logs without DSNs, portfolio ids,
request hashes, or payload content. Runtime repositories do not retry writes blindly; operators
should treat database failures as infrastructure faults and follow the Postgres rollout runbook.

Async scenario analysis defaults to inline execution in Docker. For accept-now/execute-later live
proof, start the stack with `DPM_ASYNC_EXECUTION_MODE=ACCEPT_ONLY`; manual execution can be disabled
with `DPM_ASYNC_MANUAL_EXECUTION_ENABLED=false` when the execute endpoint must be hidden.
Lineage lookup remains feature-gated by default; set `DPM_LINEAGE_APIS_ENABLED=true` when running
lineage endpoint certification or supportability incident drills.
Idempotency history remains feature-gated by default; set
`DPM_IDEMPOTENCY_HISTORY_APIS_ENABLED=true` for retry-history certification or incident drills.

Docker supply-chain evidence is repo-native:

```powershell
make docker-build
make docker-image-evidence
```

`make docker-image-evidence` writes `output/docker-image-evidence/release-manifest.json` plus
image inspect, SBOM status, vulnerability scan status, signature status, and provenance summary
files. The Dockerfile sets non-secret OCI labels for Git SHA, branch, build timestamp, repo URL,
image digest, CI run id, and app version. `/version` exposes the same runtime metadata.

Operationally important truths:

1. readiness and migration posture matter because supportability flows depend on persistence truth
2. capability discovery through `/api/v1/integration/capabilities` remains backend-owned and uses
   canonical snake_case query parameters
3. advisory proposal routes should be served by `lotus-advise`, not reintroduced here
4. stateful DPM promotion requires `make live-api-validate-core` to pass with
   `LOTUS_MANAGE_EXPECT_STATEFUL_CORE_SOURCING=available`, which is the repo-native default for the
   canonical source-ready stack after `lotus-core` exposes the RFC-087 certified source-data
   products and canonical data is seeded. The live proof now includes
   stateful source-backed construction over `TransactionCostCurve:v1`,
   `PortfolioCashflowProjection:v1`, `ClientRestrictionProfile:v1`, and
   `SustainabilityPreferenceProfile:v1`, not only stateful simulate lineage.
   Demo certification uses the same proof family through `make demo-certify`; the GitHub
   `Demo Certification` workflow is manual because normal hosted CI runners do not own the
   canonical local stack, while Quality Baseline keeps the deterministic command-contract tests
   visible as report-only evidence.
5. `DPM_CORE_TRANSACTION_COST_LOOKBACK_DAYS` defaults to 400 days so low-turnover private-banking
   portfolios can consume observed booked-fee evidence without treating it as predictive execution
   cost, venue, or market-impact methodology.
6. proof packs preserve source-owned `RegimeScenarioPackEvaluation:v1` evidence when scenario
   context is carried by the chosen construction alternative or supplied directly at generation
   time as `regime_stress_context`. Selected-alternative evidence takes precedence. Manage records
   scenario pack id, worst-case loss, policy threshold, supportability, lineage, reason codes, and
   bounded `scenario_evidence_posture` for missing, stale/effective-period-exception,
   inapplicable, or contribution-partial source evidence; it does not generate scenario
   methodology, contribution rows, CIO approval evidence, effective-period exceptions, or
   portfolio/mandate applicability evidence locally. `lotus-risk` now owns the auditable
   scenario/contribution methodology for this source product through PR #140.
7. Core and Risk source-product adapters fail closed on incomplete response payloads. Manage
   requires Core portfolio snapshots to carry portfolio identity, business date, valuation
   currency, `positions_baseline`, `portfolio_totals`, row identifiers, explicit quantities,
   row currencies, and position market values before constructing a `PortfolioSnapshot`. It
   requires Risk concentration, regime-scenario, and risk-event cohort responses to carry source
   metadata, product/version or methodology version, request fingerprint, supportability, and
   required numeric measures before constructing authority context. Explicit source-supplied zero
   remains valid; omitted values are not converted to `USD`, `v1`, empty lists, or zero metrics.
8. wave simulation item diagnostics can expose bounded `proposed_changes` from selected
   construction alternatives. These rows are pre-trade review evidence only and are not orders,
   executions, fills, or OMS instructions.
9. source-owned cash methodology depth is consumed as evidence from `lotus-core`. Current Core
   products include `PortfolioCashflowProjection:v1`, `PortfolioLiquidityLadder:v1`, and
   `PortfolioCashMovementSummary:v1`; Manage does not forecast cashflows, issue funding or
   treasury instructions, or acknowledge OMS execution.
10. source-owned external OMS acknowledgement posture is consumed as fail-closed evidence from
   `lotus-core` `ExternalOrderExecutionAcknowledgement:v1`; Manage records blocked diagnostics
   and exposes structured `DPM_OUTCOME_EXTERNAL_EXECUTION_BOUNDARY` evidence on supportability,
   report-input, and AI-evidence handoffs only, including promotion requirements for certified
   OMS source ownership, reconciliation controls, consumer declaration, and downstream realization.
   Manage does not generate orders, route venues, certify best execution, ingest OMS
   acknowledgements, confirm fills, project settlement, or reconcile execution status.
11. outcome-review search exposes bounded source-owner and source-type filters plus facets over
    persisted review lineage only. It does not query source-owner stores, recalculate realized
    source truth, project OMS execution events, or create client-communication workflow evidence.
12. outcome-review supportability, report-input, and AI-evidence handoffs also expose structured
    `DPM_OUTCOME_CLIENT_COMMUNICATION_BOUNDARY` evidence. Manage may support internal PM, CIO,
    compliance, operations, report, and AI review workflows, but it does not contact clients,
    generate client-ready messages, collect client approval, confirm delivery, or certify client
    communication audit truth; the boundary lists the source-owner, delivery/audit, consent, and
    downstream realization requirements before promotion. AI-evidence handoff source refs are bounded to persisted
    outcome-review lineage and deduplicated review, snapshot, dimension-result, and metric-level
    evidence refs.
13. wave proof-pack posture and report-input handoffs expose structured
    `DPM_WAVE_CLIENT_COMMUNICATION_BOUNDARY` evidence. Manage wave evidence stops at internal
    operations handoff and does not contact clients, generate client-ready wave messages, collect
    client approval, confirm delivery, or certify communication audit truth.
14. proof-pack report-input and AI-evidence handoffs expose structured
    `DPM_PROOF_PACK_CLIENT_COMMUNICATION_BOUNDARY` evidence with the same source-owner,
    delivery/audit, consent, and downstream-realization promotion bar.
15. bulk-review campaign wave report-input handoffs expose structured
    `DPM_WAVE_CAMPAIGN_UNIVERSE_BOUNDARY` evidence when the trigger is
    `BULK_REVIEW_CAMPAIGN`. Manage preserves persisted source-backed campaign-definition
    candidates only and does not discover the global portfolio universe, recalculate source facts,
    recompute membership, generate orders, or claim OMS execution.
16. PM operating-quality review actions expose structured
    `PM_QUALITY_APPROVAL_WORKFLOW_BOUNDARY` evidence. Manage records immutable review-action
    ledger rows over existing score-run or fairness-analysis evidence only; it does not mutate
    approval workflow state, approve policies or trades, contact clients, create HR or conduct
    decisions, route orders, or claim OMS execution.
17. PM operating-quality summary invocations expose structured
    `PM_QUALITY_SUMMARY_TEXT_BOUNDARY` evidence. Manage records score-run/review-action identity
    and state-specific workflow, artifact, hash, or bounded failure evidence only; it does not
    store or expose generated summary text, project downstream summary UX, reconstruct prompts or
    model responses, contact clients, generate client-ready messages, approve trades, route
    orders, or claim OMS execution.

## Documentation Map

- local repository navigation:
  [docs/README.md](docs/README.md), [contracts/README.md](contracts/README.md),
  [scripts/README.md](scripts/README.md), [tests/README.md](tests/README.md),
  [src/README.md](src/README.md), [quality/README.md](quality/README.md), and
  [monitoring/README.md](monitoring/README.md)
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

`wiki/` intentionally does not contain a local `README.md` because every Markdown page in that
folder is authored wiki source and may be published. Use [docs/README.md](docs/README.md) for wiki
editing and publication guidance.
