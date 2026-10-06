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
- immutable composite-definition and effective-dated membership source records
- immutable, approval-bound DPM instruction packages for execution-adapter retrieval

It does not own advisor-led proposal workflows. Those belong to `lotus-advise`.

It also does not own canonical portfolio ledger data, market-data truth, risk methodology, or
performance analytics authority.

Composite definitions and eligibility revisions are a tenant-scoped Manage source product at
`/api/v1/rebalance/composites/*`. Writes require trusted tenant, actor, and a
`DPM_COMPOSITE_ADMIN` or `DPM_PORTFOLIO_MANAGER` role; immutable replays are idempotent and changed
content conflicts. Each committed membership revision atomically creates a durable, cursor-paged
publication (including pre-publication revisions backfilled by migration `0036`); a pinned-hash
consumer retrieval receipt is immutable and tenant-fenced. Reconciliation distinguishes
`UNACKNOWLEDGED`, `RECEIVED`, and `REJECTED`, but retrieval is not fact materialization. Publication
completeness is explicitly `UNVERIFIED`: Manage has not proved the authoritative full portfolio
universe, Performance member-return ingestion, or capacity. Caller-provided identity headers require
a trusted ingress; they are not standalone production authentication. The API preserves pinned
historical revisions and correction impact windows. It does not calculate composite returns, infer
eligibility from current book membership, or publish Performance member-return facts; those remain
explicit consumer and source-owner responsibilities.
Versioned v2 economic-authority profiles distinguish internal, external and hybrid inputs from
publisher ownership while preserving v1 history. Production provider trust and institutional
attestation verification fail closed; controlled fixtures are not official approval. See the
[authority and onboarding guide](docs/guides/composite-source-authority.md).
Definition and membership-revision list `count` values are total tenant/scoped record counts from
the same read snapshot as their bounded `items`, not page lengths. Offset pages can shift if new
revisions arrive between requests; consumers needing an ordered handoff should use the publication
cursor and its high watermark. Neither count nor watermark certifies source-universe completeness.
Migration `0036` installs lock-before-insert and publication-after-insert triggers before its
backfill, so a previous app replica writing during the migrate-before-traffic-switch window
cannot leave a revision unpublished or invert the lock order against a new replica.
An exact HTTP retry succeeds only when the original revision's publication is still present with
the matching content hash; missing or divergent publication evidence fails closed with a conflict.
Publication list/detail/reconciliation reads also verify the stored publication hash against the
source revision rather than reconstructing a misleading healthy envelope from source payload alone.
Receipt retries preserve the original server timestamp and require the same caller correlation;
a changed correlation is an immutable conflict, not a silently accepted replay.

A separate immutable universe-attestation resource can qualify one pinned membership revision for
an explicit inclusive business-date range. Only the `DPM_COMPOSITE_UNIVERSE_ATTESTER` role with the
`lotus-manage` service identity can write it. The attestation names every source product, contract
version, authority scope, source cut, source watermark, content hash and policy version, and
requires exactly one source product to own the authoritative universe. `COMPLETE` is accepted only
when the exact declared portfolio set has continuous effective-dated decision coverage for the
whole range.
Missing, unexpected and date-gap portfolios are retained under `INCOMPLETE`; an unavailable
authoritative cut is recorded as `UNAVAILABLE`, never converted to an empty complete universe.
Attestations are tenant-fenced, immutable, restart-safe and independently versioned. They do not
change the publication envelope's `UNVERIFIED` posture or prove live Core delivery, Performance
materialization, calculated returns, production identity, or scale.

Approved DPM instruction packages are a separate, tenant-scoped retrieval product at
`/api/v1/rebalance/instruction-packages/*`. A release pins the reviewed run, READY proof pack,
current mandate/model, exact economic instructions, account/instrument mapping revisions, funding
posture, approval-material hash, and correlation lineage. Preview returns **pending approval
material**, not a releaseable package. The bounded batch route explicitly releases only independent
eligible candidates and returns typed refusals for blocked candidates. Adapter receipts prove only
retrieval. Manage neither submits an order nor claims acknowledgement, fills, settlement,
reconciliation, or authoritative core booking. The product contract is
[`contracts/approved-instruction-packages/lotus-manage-approved-instruction-package.v1.json`](contracts/approved-instruction-packages/lotus-manage-approved-instruction-package.v1.json).

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
   Stateful rebalance and construction requests require matching `X-Tenant-Id` and
   `stateful_input.tenant_id` before Core resolution. Synchronous stateless simulation and
   construction generation also require `X-Tenant-Id` for durable run ownership. Construction
   preserves the effective `DiscretionaryMandateBinding:v1` cash reserve as a target for heuristic
   and solver paths. Missing and explicit zero remain distinct; conflicting request overrides fail
   before simulation, callers cannot widen its tolerance, and post-trade deviation is reported with
   a bounded tolerance. Successful target scaling remains ready; only deviation requires review.
   Source-declared reserve basis and no-override authority are retained in run lineage; missing
   authority or invalid legacy source targets fail closed. An absent source target does not permit
   a caller target override; the independent request-level cash buffer remains available.
   Controlled HTTP/PostgreSQL proof is
   not real Core or bank acceptance; source-bound wave enforcement remains tracked in issue #733.
   Out-of-date bindings fail closed. Construction runs, alternative sets, selections,
   selected-alternative proof-pack sourcing, portfolio-memory
   projections, and wave simulation/selection are tenant-fenced at their repository boundaries.
   PostgreSQL generation serializes each `(tenant_id, idempotency_key)` on a dedicated autocommit
   advisory-lock session before method-run side effects. Coordination sessions use an independent
   bounded connection budget and lock-wait timeout, so waiters do not consume repository-write
   capacity or inherit the shorter ordinary statement timeout. Horizontally concurrent exact
   replays return one canonical set without orphan runs or idle-transaction fence expiry.
   Legacy construction rows without attributable ownership remain quarantined and unreachable.
   These local headers are caller assertions, not production identity-provider proof.
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
   Enterprise write audit events retain structured asserted identity and outcome in the JSON
   logger, but trusted-ingress identity and durable audit-sink delivery are separate deployment
   obligations; see [enterprise readiness](docs/standards/enterprise-readiness.md) and the
   [Security and Governance wiki source](wiki/Security-and-Governance.md).
   Ordinary `extra_fields` logging is a separate bounded contract: only the checked-in operational
   field inventory is serialized, only scalar values are admitted, and credential or identity keys
   are redacted case-insensitively. Unknown or structured fields are dropped at the formatter.
   Application-produced enterprise refusals (`400`, `403`, and `413`) remain inside the same outer
   request-observability envelope as routed responses: they return correlated Problem Details and
   security/policy headers and contribute exactly one bounded completion log and HTTP observation.
   This correlation is local propagation, not evidence of exported tracing or evaluated alerts.
5. Solver-capable production installs use the `solver` extra (`cvxpy` and `numpy`), while
   development and CI declare both as required `dev` dependencies. Solver-mode proof surfaces load
   that prerequisite during test collection and execute unconditionally; a missing, suppressed, or
   broken solver runtime must fail the lane instead of becoming a passing skip.
6. `POST /api/v1/rebalance/simulate` requires `X-Tenant-Id` in both input modes. Its durable
   PostgreSQL admission key is `(tenant_id, Idempotency-Key)` plus the canonical request hash, so
   concurrent identical submissions publish one authoritative run and changed-payload reuse is
   rejected. Run, artifact, history, workflow, and support-bundle descendants are tenant-fenced;
   unattributed legacy rows are quarantined rather than assigned to a caller.
   Async batch support bundles are operation-scoped: each requested scenario has an explicit
   succeeded/failed/missing outcome, successful runs have attempt-fenced operation membership,
   run and membership edges commit atomically in PostgreSQL, and recovered attempts remain
   identified as non-authoritative historical evidence. Direct
   run bundles link to async operations only through that durable membership, not correlation text.
7. Currency-bearing request and shelf minimum-trade thresholds are compared in each candidate
   trade's price currency. The engine uses Decimal direct/inverse quotes from the supplied governed
   market-data snapshot, records quote and applied-conversion provenance in diagnostics, preserves
   request-before-shelf precedence, and blocks when a required quote is missing or non-positive.
   This is deterministic proposal qualification, not live FX pricing or execution authority.

## Strategic DPM Roadmap

RFC-0037 through RFC-0043 define the revamp from a certified rebalance/supportability service into
a discretionary mandate portfolio-management operating system.

RFC-0038 is implementation-backed for the mandate digital twin, health-score engine, derived
monitoring exceptions, persistence foundation, and the mandate, health, monitoring and
command-centre APIs. For slice-level status - what is certified and what remains - the authoritative sources are the RFCs
under [`docs/rfcs/`](docs/rfcs/) and
[`wiki/Supported-Features.md`](wiki/Supported-Features.md), which are updated as work merges. Those
are the repo-local authored sources, current with this commit; the published wiki lags them until
the next publication. The [`wiki/Roadmap.md`](wiki/Roadmap.md) page
is the readable summary over them. Three of its rows were found trailing the RFCs while this change
was in review and all three are now corrected; prefer the RFCs where the two ever disagree.

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
immutable persistence, required tenant-fenced reads/replay/listing, certified APIs, and source-backed
mandate-context attachment. Legacy proof packs without attributable tenant ownership remain
quarantined rather than being assigned to an assumed caller. Downstream
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
[`wiki/Supported-Features.md`](wiki/Supported-Features.md) for the full posture.

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
- idea-originated management review realization
  `/api/v1/rebalance/idea-action-intake` accepts source-safe `lotus-idea`
  conversion-intent evidence. An accepted `REVIEW_FOR_REBALANCE` intent creates exactly one
  durable, portfolio-scoped `PENDING_REVIEW` management action. The related outcome routes expose
  append-only Manage-owned review history and use optimistic source-event versions to reject stale
  decisions. A read-only lookup by exact conversion intent and portfolio recovers the current
  owner history without creating or repeating work. The implementation remains not-certified
  because production IdP scope and live
  consumer proof are outstanding. Approval is a management-review outcome; it does not prove
  rebalance or order execution, suitability, OMS state, or client publication. These routes remain
  route-foundation evidence rather than certified `PortfolioActionRegister:v1` serving routes.
- policy-pack supportability
  `/api/v1/rebalance/policies/*`
- mandate digital twin and health
  `/api/v1/mandates/*`
  `POST /api/v1/mandates/{mandate_id}/refresh-from-core` requires matching normalized
  `X-Tenant-Id` and body `tenant_id` before Core sourcing or Manage persistence. Manage
  forwards that caller-asserted scope per Core request; it is not authenticated-principal proof.
- DPM monitoring, exceptions, and command center
  `/api/v1/dpm/monitoring/*`, `/api/v1/dpm/exceptions*`, `/api/v1/dpm/command-center`
  `POST /api/v1/dpm/monitoring/run-once` requires `X-Tenant-Id`; its normalized value must
  match the body `tenant_id` before Manage calls Core or persists health, exception, or run
  evidence. The header is caller-asserted routing scope in the current no-auth posture, not proof
  of an authenticated principal.
- construction alternatives
  `/api/v1/construction/alternative-sets/generate`,
  `/api/v1/construction/alternative-sets/{alternative_set_id}`,
  `/api/v1/construction/alternative-sets/{alternative_set_id}/selections`
  require caller-asserted `X-Tenant-Id`. Their PostgreSQL identity is tenant scoped, including
  idempotency keys; another tenant receives `404` for an owned set or selection and may use the
  same idempotency key for an independent request.
- no-action construction
  Construction `DO_NOTHING_BASELINE` has no economic `rebalance_run_id`, intents or proposed
  changes. Its typed `evaluation_context` references only the source run's `BEFORE` state for
  audit; it is not an executable proposal. Selection projects only the chosen alternative's
  proposals. No-action proof packs have no economic run and remain blocked for trade release.
  Blocked proof packs remain visible for audit and cannot advance wave approval, staging or handoff.
  Historical borrowed references are interpreted as evaluation context without rewriting stored
  records; inconsistent historical proof packs cannot be replayed or released as trade authority.
  Native network recovery checks cover USD/FX readback and idempotent replay after API-process
  replacement and wave-worker recovery at the financial-commit/checkpoint boundary;
  see the [operations runbook](wiki/Operations-Runbook.md) for scope and prerequisites.
  [All-method construction tests](tests/integration/dpm/supportability/test_construction_method_network.py)
  cover ownership, restriction side/date/selector boundaries and API-process recovery with
  independent USD calculations. Durable construction artifacts retain evaluated hard-policy
  evidence; comparison mechanics remain counterfactual. Controlled contracts do not certify release.

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
  Durable create identity is `(tenant, Idempotency-Key)` plus the canonical request fingerprint.
  Exact retries return the original wave; changed requests under a claimed key return
  `WAVE_CREATE_CONFLICT`. When `X-Correlation-Id` is omitted, Manage derives a stable correlation
  from that tenant-scoped command, so distinct commands for one business trigger remain
  independent. Explicit correlation ids are unique per tenant, and concurrent exact creates
  converge without leaving an orphan wave or idempotency mapping.
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
  domain models. A configured maximum tracking-error limit is applicable only when Manage receives
  an explicit measurement or usable source-owned Risk health context: missing evidence produces
  `TRACKING_ERROR_EVIDENCE_MISSING`, score 60, `PENDING_REVIEW`, and `FIX_SOURCE_DATA`; explicit
  zero remains a valid measured pass, while a mandate with no such limit is non-applicable.
  A supplied observation must be finite and non-negative even if a source Risk context is
  present or the mandate has no tracking-error limit; invalid input returns validation 422
  before health or exception persistence.
  An explicitly declared `tax_budget_base` is a cumulative realized-gain allowance in the
  portfolio base currency, not tax payable. `/health/recalculate` compares non-negative
  `tax_budget_used_base` through the twin as-of date: below-limit is a qualified pass, equality
  is exhausted/review-required, above-limit is blocked, and missing or conflicting evidence is
  pending review. `budget_assessments` retains the nominal remaining amount, comparison basis,
  declared source references, and the independent turnover finding in stored health and
  monitoring exceptions. Caller-supplied evidence is not live bank tax-source certification.
  A declared turnover budget is a cumulative portfolio-value fraction, not a cash amount.
  Missing `turnover_budget_used` is not zero: it requires review, as do unmatched measurement
  periods or as-of cuts. Explicit zero passes; 80% through below the limit is near-limit/review,
  equality is exhausted/review, and excess blocks. Unknown/unsourced limits remain unassessed;
  only an explicit `turnover_budget_applicable=false` declaration is non-applicable. Health,
  monitoring exceptions and wave source-readiness retain that distinction. Caller-declared
  measurements and applicability are not verified Core turnover authority or release approval.
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

Prerequisites, each pinned by a source you can check:

| Tool | Version | Needed for | Where that version is pinned |
| --- | --- | --- | --- |
| Python | 3.12 | everything | `pyproject.toml` (`requires-python = ">=3.12"`), `mypy.ini`, ruff `target-version`, every CI lane, and the `Dockerfile` base image |
| `make` | any | every repo-native command | `Makefile` |
| Docker | any current release | the containerised stack and PostgreSQL-backed runs | `Dockerfile`, `docker-compose.yml` |

`>=3.12` permits newer interpreters, but every gate — CI, type checking, the lint target, and the
runtime image — runs 3.12, so 3.12 is what reproduces the gates locally.

From a fresh checkout, create and activate a virtual environment first: `make install` installs
into whichever interpreter `python` resolves to, and installing into a system Python fails outright
on distributions that follow PEP 668.

Linux and macOS:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
```

Install dependencies (this also registers the pre-commit hooks):

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

Docker startup applies the forward-only PostgreSQL migrations before `uvicorn` starts. The
API and migration command accept only `LOCAL` or `PRODUCTION` persistence profiles. Native unset
profiles default to `LOCAL`; Compose defaults to `PRODUCTION` only when unset and preserves
explicit blanks. Blank or unknown values refuse admission before migrations or API startup.
The container healthcheck uses `/health/ready` rather than `/docs`. In production profile,
`/health/ready` validates persistence guardrails, applied migration versions, and trusted write
authorization posture so supportability APIs cannot look healthy while their backing store,
authz enforcement, primary key id, or capability policy is missing. The checked-in Compose defaults
enable authz for local production-profile proof; real deployments must replace the local key id and
capability policy with bank-managed identity configuration.

Runtime Postgres adapters use one bounded access policy instead of direct unbounded driver calls.
Production operators should set and monitor:

- `DPM_POSTGRES_MAX_CONNECTIONS` (default `10`, allowed `1..100`)
- `DPM_POSTGRES_COORDINATION_MAX_CONNECTIONS` (default `4`, allowed `1..100`)
- `DPM_POSTGRES_CONNECT_TIMEOUT_SECONDS` (default `3`, allowed `1..30`)
- `DPM_POSTGRES_STATEMENT_TIMEOUT_MS` (default `5000`, allowed `100..60000`)
- `DPM_POSTGRES_COORDINATION_WAIT_TIMEOUT_MS` (default `60000`, allowed `1000..300000`)
- `DPM_POSTGRES_IDLE_IN_TRANSACTION_TIMEOUT_MS` (default `10000`, allowed `1000..120000`)
- `DPM_POSTGRES_ACQUIRE_TIMEOUT_SECONDS` (default `2`, allowed `1..30`)

Invalid values fail production readiness with `POSTGRES_ACCESS_POLICY_INVALID:*` or
`POSTGRES_ACCESS_POLICY_OUT_OF_RANGE:*`. Runtime acquisition and driver failures emit sanitized
`lotus_manage_postgres_access_total` metrics and structured logs without DSNs, portfolio ids,
request hashes, or payload content. Runtime repositories do not retry writes blindly; operators
should treat database failures as infrastructure faults and follow the Postgres rollout runbook.

Rows retained without verified tenant attribution remain deliberately quarantined: normal tenant
reads match none of them. Operators can inventory every governed quarantine dataset without
changing it by setting `DPM_SUPPORTABILITY_POSTGRES_DSN` and running:

```bash
make quarantine-inventory
```

The command reports counts, at most 20 identifying rows per dataset by default, truncation, and
applied migration checksums. Migration `0029` supplies the partial NULL-tenant index that keeps the
monitoring-run count and sample bounded as history grows. Set `QUARANTINE_INVENTORY_LIMIT` to
`1..100` for a different bound.
It runs in a repeatable-read, read-only transaction; an explicit successful zero is healthy, while
missing migration provenance, connection failure, or an unsafe bound exits nonzero with a
sanitized error. Idempotency keys are SHA-256 hashed and payloads, DSNs, and tenant guesses are
never emitted. See [the operations runbook](docs/operations-runbook.md#null-tenant-quarantine-inventory).

Migration `0030` closes the historical fabricated-limit ambiguity without guessing from the old
`0.02`/`0.10`/`0.15` numeric shape. Existing snapshots did not record whether the Core compiler or
`/health/recalculate` supplied their twin, and caller-supplied lineage could look identical. Rows
with legacy limit values are preserved and marked `MANDATE_LIMIT_PROVENANCE_AMBIGUOUS`; effective
reads and health scoring suppress those unverified limits. Their derived health evidence is
retired, affected successful monitoring runs fail closed, and unrelated cash-flow, tax-lot,
restriction, and workflow findings survive. Already-failed runs retain their evidence. Future
writes persist `CORE_COMPILED` or `CALLER_SUPPLIED` producer provenance.

Async scenario analysis defaults to inline execution in Docker. For accept-now/execute-later live
proof, start the stack with `DPM_ASYNC_EXECUTION_MODE=ACCEPT_ONLY`; manual execution can be disabled
with `DPM_ASYNC_MANUAL_EXECUTION_ENABLED=false` when the execute endpoint must be hidden. Every
async route requires normalized `X-Tenant-Id`. PostgreSQL atomically claims execution with an
opaque, expiring fence (`DPM_ASYNC_EXECUTION_LEASE_SECONDS`, default `300`); only the current owner
may publish terminal evidence. Status exposes the monotonic attempt and lease expiry, never the
token. Expired work can be reclaimed after a crash, while stale workers cannot replace the accepted
result. This is durable ownership and recovery proof, not a queue, capacity claim, or external trade
execution guarantee.
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

From the repository root, run `make test-image-financial-runtime` after building the image.
`make workflow-policy-gate` protects its PR/Main execution chain against skips and failure masking.
Set `DPM_POSTGRES_INTEGRATION_DSN` to an isolated loopback PostgreSQL test server with `CREATEDB`.
The PR/Main Docker lane runs the same command: immutable image ID and OCI/`/version` revision
checks, no source mounts, USD/EUR financial recovery and durable wave recovery. It requires all
three cases to pass without skips; receipts are under `output/docker-image-evidence/financial-runtime`.
This is synthetic image acceptance, not actual-source, live IAM or production-capacity certification.

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
   Direct stateful simulation and every construction method now qualify candidate trades against
   Core `ClientRestrictionProfile:v1` independently of optimization method. A valid empty profile
   differs from an unavailable profile: unavailable or unclassifiable hard-policy evidence cannot
   produce mandate-compliant `READY`; active matching buy/sell restrictions block the candidate.
   Stateless simulation remains a mechanical counterfactual: its arithmetic may be `READY`, but
   `client_restriction_policy.decision=NOT_ASSESSED` and its consumer gate requires review. This
   is not trade approval, instruction release, acknowledgement, a fill, or core booking. Instruction
   package release now refuses runs without READY source-backed client-policy evidence and scope;
   wave simulation must propagate that evidence before its items can become releaseable.
5. `DPM_CORE_TRANSACTION_COST_LOOKBACK_DAYS` defaults to 400 days so low-turnover private-banking
   portfolios can consume observed booked-fee evidence without treating it as predictive execution
   cost, venue, or market-impact methodology. `COST_AWARE` publishes an aggregate only when the
   observed curve covers every candidate `(security_id, transaction_type)` key. Missing BUY/SELL
   evidence degrades the method, identifies the exact missing trade sides, and suppresses partial
   aggregates; complete zero-bps evidence remains an explicit zero estimate. Each observed
   `(security_id, transaction_type)` point must be unique: repeated keys, even identical rows or
   different currencies, are refused in caller-supplied context. Duplicate Core source keys
   degrade the mapped context with `TRANSACTION_COST_CURVE_DUPLICATE_POINT` and no numeric estimate.
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
   Stateful Core composition also checks that returned model-target identity and business date
   match the requested selectors. An unrelated model response is a 424 incomplete dependency,
   not an alternative model simulation; mandatory mandate and model readiness is checked before
   fetching dependent portfolio products.
   Core client-restriction profiles must also match the requested portfolio, date, and mandate.
   Scoped rules with blank or absent selectors are rejected before they can become apparent
   client-wide restrictions; intentional `client`/`mandate` rules without selectors remain valid.
   Risk-event waves reject duplicate candidate IDs before Risk evaluation and reject ready Risk
   cohorts with duplicate, contradictory affected/excluded, unknown, wrong-date, or wrong-mandate
   membership before preview or durable wave creation. Manage does not recompute Risk impact scores.
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
18. Book-scale wave simulation uses the durable asynchronous operation routes under
    `/api/v1/rebalance/waves/*/simulation-operations`. Admission binds each selector and nested
    construction portfolio to its immutable tenant-owned wave item before `202`; contradictory or
    foreign inputs are refused without calculation. Horizontally deployed workers use bounded leases
    and fencing, persist each result/failure incrementally, and recover deterministic construction
    artifacts after process replacement. Admitted tenant, effective cash target, and source-backed
    restriction evidence survive that handoff; policy-blocked alternatives cannot be selected.
    Status, stable paged results, retry, and cancellation are supported APIs. The existing
    synchronous `/simulate` route remains a bounded convenience and is not restart-safe book-scale
    orchestration. See
    [issue #715 evidence](docs/evidence/issue-715-wave-simulation/README.md) for the real PostgreSQL
    recovery proof, including physical worker termination after durable financial commit, and
    measured local operating envelope. Synthetic source-ready inputs do not certify live integration
    or production capacity.
    Items may opt into `input_mode=stateful`: Manage derives scope from the checked wave and
    freezes Core inputs, mandate authority and source lineage before durable admission. Exact
    retries and workers do not refetch Core. Review-required health is never promoted; Core's
    unsourced cash-band/turnover controls still prevent source-backed wave qualification. See the
    [source-bound wave evidence](docs/evidence/issue-733-source-bound-waves/README.md).

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
