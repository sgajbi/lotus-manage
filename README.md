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
   configured, and the retired monolithic core route is not configured. `DPM_CORE_QUERY_BASE_URL`
   is also required when stateful construction consumes query-plane source products such as
   `PortfolioCashflowProjection:v1`.
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
command-center backend foundation, including first-wave mandate-health consumption of
`ClientRestrictionProfile:v1`, `SustainabilityPreferenceProfile:v1`, and
`PortfolioCashflowProjection:v1` with source lineage, bounded review/block posture, and explicit
gap codes when optional source products are unavailable. RFC-0039 is implementation-backed for the manage-side
construction-alternative foundation: first-wave and authority-backed generate/read/select APIs,
do-nothing baseline, explainable heuristic, minimum-turnover, tax-aware, solver-constrained,
risk-aware, liquidity-aware with optional `lotus-core` `PortfolioCashflowProjection:v1` projected
cash-pressure evidence, currency-overlay, and regime-stress-aware construction through `lotus-risk`
`RegimeScenarioPackEvaluation:v1`. ESG/restriction-aware construction now consumes `lotus-core`
`ClientRestrictionProfile:v1` and `SustainabilityPreferenceProfile:v1` when stateful core sourcing
is enabled: hard client restrictions can block candidate trades, sustainability allocation
preferences can trigger pending review, and profile source lineage is preserved for proof packs.
Construction alternatives also carry bounded `proposed_changes` diagnostics from generated
security trade intents so wave simulation can show PM-reviewable proposed changes without claiming
order execution, venue routing, execution price, or OMS handoff. Stateful core sourcing now also
preserves optional `ClientIncomeNeedsSchedule:v1`, `LiquidityReserveRequirement:v1`, and
`PlannedWithdrawalSchedule:v1` evidence in liquidity-aware construction diagnostics and
mandate-health lineage. Security-level sustainability classification evidence remains an explicit
pending-review boundary; Manage does not turn income needs, reserve requirements, or withdrawals
into financial-planning advice, funding recommendations, client liability planning, OMS
instructions, or treasury actions. `lotus-core` PR #365 (`c7fa07b0`, wiki `067f919`) now defines
external treasury source-product contract boundaries for currency exposure, hedge policy, FX
forward curves, and eligible hedge instruments. `lotus-core` PR #366 (`9e86df3b`, wiki `617e4e6`)
exposes `ExternalHedgeExecutionReadiness:v1` as an active fail-closed `UNAVAILABLE` route.
`lotus-core` PR #367 (`3d0a7bbd`, wiki `d719c74`) now also exposes
`ExternalCurrencyExposure:v1` as an active fail-closed `UNAVAILABLE` route and `lotus-core` PR
#368 (`763db4c1`, wiki `50fff30`) exposes `ExternalHedgePolicy:v1` as an active fail-closed
`UNAVAILABLE` route. `lotus-core` PR #369 (`89225766`, wiki `72dc91d`) exposes
`ExternalFXForwardCurve:v1` as an active fail-closed `UNAVAILABLE` route, and `lotus-core` PR #370
(`bacad356`, wiki `6e7c706`) exposes `ExternalEligibleHedgeInstrument:v1` as an active
fail-closed `UNAVAILABLE` route. `lotus-core` PR #371 (`9774bc40`, wiki published) exposes
`ExternalOrderExecutionAcknowledgement:v1` as an active fail-closed `UNAVAILABLE` route for external
OMS acknowledgement posture. `lotus-platform` PR #333 (`c46d581`), PR #334 (`ae4f707`), and
PR #335 (`72be854`) mirror the first active treasury source-product postures. Manage now consumes
the readiness, currency-exposure, hedge-policy, eligible-hedge-instrument, and FX forward-curve
postures through stateful core sourcing and preserves them in currency-overlay construction
diagnostics as blocked external treasury evidence, including empty exposure/policy/
eligible-instrument/forward-curve rows, exposure/policy-rule/eligible-instrument/curve-point
counts, missing data families, blocked capabilities, lineage, and source hashes. Manage also
preserves Core's external order-execution acknowledgement posture in construction authority
diagnostics as fail-closed execution-boundary evidence, including acknowledgement counts, empty
acknowledgement rows, missing data families, blocked capabilities, lineage, and source hashes.
Manage still makes
no FX-attribution, hedge-policy approval, eligible-instrument selection, suitability approval,
product-recommendation, hedge advice, forward-pricing, FX valuation-methodology,
counterparty-selection, treasury-instruction, best-execution, OMS, fill, or settlement claim.
Postgres
persistence, live proof, and downstream Gateway/Workbench realization requirements are documented,
but full product-surface support still requires Gateway and Workbench implementation and proof.
RFC-0040 is now implementation-backed for manage-owned pre-trade proof packs: durable
JSON, deterministic Markdown, report-input handoff, AI-evidence handoff, hashes, lineage, retention
metadata, immutable persistence, certified APIs, source-backed mandate-context attachment from
RFC-0038 mandate evidence, and canonical Postgres-backed live proof. Gateway
composition and Workbench review UX are implemented in their owning apps; report materialization is
implemented in `lotus-render`, `lotus-report`, and `lotus-archive`; and governed AI PM memo support
is implemented in `lotus-ai`, `lotus-gateway`, and `lotus-workbench`. The post-merge gold-pass audit
also records a canonical front-office risk-drawdown `partial` boundary tracked as
`sgajbi/lotus-gateway#182`, so no unsupported proof-pack source enrichment is claimed here.
The portfolio-memory API now publishes source-event family posture for supported manage, report,
AI, and archive families, explicitly marks OMS execution as deferred, and points PM scoring to the
separate Manage-owned PM operating quality score-run lifecycle product. Persisted PM quality score
runs with source-owned Core PM-book membership now project bounded portfolio-memory lineage events
for matching portfolios without copying raw score payloads or creating portfolio-level rankings. The
portfolio-memory API also exposes `GET /api/v1/rebalance/portfolio-memory/search` as a bounded
Manage-local index over persisted proof-pack, wave, monitoring-exception, campaign-definition,
outcome-review, and explicit caller-supplied portfolio identifiers; it is not global
portfolio-universe discovery and does not project OMS acknowledgement, fill, settlement, or
execution-status events. Persisted bulk-review campaign definitions now project bounded portfolio
memory events for definition, approval-decision, assignment-action, assignment-task, and
maker-checker control evidence without copying raw campaign payloads, recalculating membership,
or claiming external workflow orchestration, client contact, order routing, or OMS execution. The
portfolio-memory response also carries structured
`DPM_PORTFOLIO_MEMORY_EXTERNAL_EXECUTION_BOUNDARY` evidence naming blocked OMS capabilities, the
required future execution/OMS owner, and `ExternalOrderExecutionAcknowledgement:v1` as the required
future source product before acknowledgement, fill, settlement, or execution-status events can be
projected.
RFC-0041 is implementation-backed and closed as `DONE`
for manage-owned explicit portfolio-list rebalance waves: durable preview/create/source-check,
RFC-0039-backed ready-item simulation, RFC-0040 proof-pack linkage, approval-with-exceptions,
internal handoff evidence, retrieve/search/item/proof-pack/report-input/supportability read models, and
Postgres-backed evidence under `output/rfc0041-wave-proof/20260504-231914`. Gateway composition,
Workbench first-wave command-center UX, and wave report materialization in `lotus-report`,
`lotus-render`, and `lotus-archive` are implementation-backed, merged, validated, and
wiki-published. PM-book cohort discovery is implemented for `PM_BOOK_REVIEW` through the
source-owned lotus-core `PortfolioManagerBookMembership:v1` product; CIO model-change discovery is
implemented through `CioModelChangeAffectedCohort:v1`; and bounded risk-event discovery is
implemented for `RISK_EVENT` through lotus-risk `RiskEventAffectedCohort:v1` over caller-supplied
candidate portfolios with source-supplied exposure weights. Bounded bulk-review campaign
membership is implemented for `BULK_REVIEW_CAMPAIGN` through Manage-owned
`BulkReviewCampaignMembership:v1` over source-backed candidate portfolios with source-owned
portfolio type, DPM portfolio-type filtering, deterministic membership refs, optional
approval/expiry/actor-entitlement governance evidence, immutable
`BulkReviewCampaignDefinition:v1` definitions over source-backed candidate sets, and fail-closed
validation. Tactical house-view wave discovery is implemented for `TACTICAL_HOUSE_VIEW` through
lotus-advise `TacticalHouseViewAffectedCohort:v1` over caller-supplied source-backed candidate
portfolios; Manage preserves Advise cohort refs and fails closed without recomputing house-view,
holdings, exposure, alignment, or mandate facts. Workbench now renders the first-wave active
campaign-definition list through Gateway/BFF without recalculating campaign membership. Manage now
also exposes persisted campaign discovery at
`GET /api/v1/rebalance/waves/campaign-discovery`, summarizing `BulkReviewCampaignDefinition:v1`
identity, governance posture, expiry posture, source-ref count, and source-backed candidate counts
without discovering the global portfolio universe or recalculating membership. Manage also supports
an operating queue at `GET /api/v1/rebalance/waves/campaign-operating-queue`, classifying persisted
definitions as ready to launch, attention required, or closed from existing discovery,
preview-readiness, lifecycle, and launch-history posture without creating maker-checker or OMS
claims. Manage also supports
an approval attention inbox at `GET /api/v1/rebalance/waves/campaign-approval-inbox`, classifying
persisted definitions as approval complete, approval required, approval incomplete, expiry
attention, entitlement attention, or closed from existing governance evidence and readiness posture
without mutating approval state, creating maker-checker workflow, approving trades, generating
orders, or claiming OMS execution. Manage also supports a read-only cross-actor workflow board at
`GET /api/v1/rebalance/waves/campaign-workflow-board`, composing the operating queue and approval
inbox into actor-aware next-action rows for launch, approval-decision capture, approval evidence
remediation, expiry refresh, entitlement review, or closed posture without discovering the global
portfolio universe, mutating approval state, creating maker-checker workflow, approving trades,
generating orders, or claiming OMS execution. Manage also supports a read-only assignment and
escalation plan at `GET /api/v1/rebalance/waves/campaign-assignment-plan`, deriving actor routing,
escalation tier, SLA posture, and reason codes from the workflow board without mutating assignment
state, creating escalation tasks, creating maker-checker workflow, approving trades, generating
orders, or claiming OMS execution. Manage also supports read-only workflow automation readiness at
`GET /api/v1/rebalance/waves/campaign-workflow-automation`, composing assignment-plan posture and
existing controlled assignment-task state into deterministic candidates for opening, monitoring, or
escalating Manage-owned assignment tasks without mutating tasks, orchestrating external workflow,
contacting clients, mutating maker-checker control state, approving trades, generating orders, or
claiming OMS execution. Manage also supports append-only assignment and escalation
actions at
`POST /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/assignment-actions`
plus listing them at the same route with `GET`, mutating assignment posture evidence only with
assigned actors, escalation tier, SLA posture, correlation id, source refs, deterministic action ids,
and conflict-safe action refs; it does not mutate approval state, create maker-checker workflow,
approve trades, generate or route orders, contact clients, or claim OMS execution. Manage also supports
controlled assignment and escalation tasks at
`POST /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/assignment-tasks`,
task transitions at
`POST /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/assignment-tasks/{task_ref}/transitions`,
and task listing at
`GET /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/assignment-tasks`,
mutating only Manage-side assignment task state with append-only transition evidence, current
status, assignees, escalation tier, SLA posture, due-date posture, deterministic task/transition
ids, and conflict-safe refs; it does not mutate approval state, create maker-checker workflow,
approve trades, generate or route orders, contact clients, orchestrate external workflow systems,
or claim OMS execution. Manage also supports
append-only maker-checker control evidence at
`POST /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/maker-checker-controls`
plus listing it at the same route with `GET`, requiring distinct submitter and reviewer actors for
completed reviews while avoiding trade approval, order generation/routing, client contact,
external workflow orchestration, or OMS claims. Manage also supports
retiring persisted campaign definitions at
`POST /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/retire`;
and superseding older definitions with active replacement versions at
`POST /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/supersede`;
and projecting lifecycle events at
`GET /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/lifecycle-events`;
and composing a bounded workflow overview at
`GET /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/workflow-overview`
with discovery, fail-closed readiness, lifecycle events, launch history, and optional launch
package guidance;
and recording append-only approval decisions at
`POST /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/approval-decisions`
plus listing them at the same route with `GET`, mutating campaign approval posture evidence only
without trade approval, order generation/routing, client contact, maker-checker workflow, or OMS
execution claims;
and checking fail-closed preview readiness at
`GET /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/preview-readiness`
before new wave use;
and building bounded launch packages at
`GET /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/launch-package`
with preview/create request drafts and idempotency headers; and launching a durable wave from a
ready persisted definition at
`POST /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/launch`
using deterministic launch idempotency; and listing append-only launch history at
`GET /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/launch-history`
with wave id, actor, requested as-of date, correlation id, idempotency key, pagination, and
explicit no-order/no-OMS operating boundaries;
retired and superseded definitions stay auditable in list/get/discovery/lifecycle-event results but
fail closed for new preview/create requests. Global portfolio-universe campaign discovery, external
workflow orchestration beyond Manage-side task readiness and append-only evidence ledgers,
richer owning-service risk/performance
aggregate enrichment, and external OMS execution remain unpromoted.
`lotus-ai` now owns the first-wave `dpm_pm_memo.pack@v1`, `dpm_wave_pm_memo.pack@v1`,
`outcome_review_narrative.pack@v1`, `dpm_operations_handoff_summary.pack@v1`,
`dpm_exception_summary.pack@v1`, and `pm_quality_summary.pack@v1` workflows over Manage-owned
proof-pack, wave, outcome, operations handoff, monitoring-exception, and PM quality score-run
evidence with review-required guardrails. RFC-0042 is
`DONE` for manage backend
authority:
source-backed outcome-review preview/create/retrieve/search, immutable persistence and events,
source-refresh eventing, report-input and AI-evidence handoff contracts, supportability telemetry,
and live canonical manage proof under `output/rfc0042-outcome-proof/20260505-024352`; Slice 12
hardening proof under `output/rfc0042-outcome-proof/20260505-025613` adds idempotency conflict and
state-filter validation evidence. Full post-trade outcome product support remains downstream until
Gateway/Workbench implementation where surfaced is complete and canonically proven. RFC-0043 is
partially implemented for the bounded DPM workflow-pack product path: owner-side packs, default
workflow-pack resolution, and first-wave Gateway/Workbench operations-handoff plus
exception-summary invocation are merged, validated, and wiki-published. Full copilot workspace UX,
additional future product surfaces, and unsupported autonomous advice remain future owner work.
RFC42-WTBD-008 now has a bounded Manage-owned PM operating quality backend foundation:
`POST /api/v1/rebalance/pm-operating-quality/score-runs/preview` previews
`PmOperatingQualityScoreRun:v1`, while `PUT /policies/{policy_id}/versions/{policy_version}`,
`GET /policies`, and `GET /policies/{policy_id}/versions/{policy_version}` administer immutable
bank policy versions for reuse. `POST /score-runs`, `GET /score-runs`, and
`GET /score-runs/{score_run_id}` persist and retrieve immutable score-run evidence. Scoring is
disabled by default, enabled policies require bank approval and fairness-review evidence, fail
closed for missing required evidence, invalid or expired governance approval, and unauthorized
actors, and prohibited HR, compensation, conduct-enforcement, and autonomous-ranking uses remain
outside the product contract.
Policies may also carry bank-defined `peer_group_policy` and `lookback_window_policy` evidence.
Score runs materialize that context into `scope_evidence`, include the peer-group and lookback refs
in the content hash, and fail closed when dated source evidence falls outside the approved lookback
window. Manage records this comparison context only; it does not discover peers, rank PMs, or own
source methodology.
When `pm_book_scope` is supplied, score-run preview/create materializes source-owned lotus-core
`PortfolioManagerBookMembership:v1` evidence, records `book_scope_evidence` including bounded
member portfolio ids, and fails closed for unavailable, incomplete, degraded, or empty PM-book
membership. Persisted source-backed score runs are visible in portfolio memory as
`PM_QUALITY_SCORE_RUN` lineage events. Review actions over those score runs are visible as bounded
`PM_QUALITY_REVIEW_ACTION` supervisory events that preserve target identity, hashes, states, source
refs, actor, and action posture without projecting raw rationale, score values, PM rankings,
client-contact, trade, order, OMS, or execution claims. The fairness-analysis route family now
supports preview and immutable create/read/list lifecycle at
`POST /api/v1/rebalance/pm-operating-quality/fairness-analyses/preview`,
`POST /api/v1/rebalance/pm-operating-quality/fairness-analyses`,
`GET /api/v1/rebalance/pm-operating-quality/fairness-analyses`, and
`GET /api/v1/rebalance/pm-operating-quality/fairness-analyses/{fairness_analysis_id}`. It emits
bounded `PmOperatingQualityFairnessAnalysis:v1` posture over persisted score runs and
source-defined segments such as mandate type, region, book profile, client constraint profile, or
market regime. It validates common policy/as-of scope, requires minimum scorable segment counts,
compares segment average scores against a governed spread threshold, persists content-addressed
evidence immutably, and returns stored evidence without recomputing score runs. It does not infer
protected classes, rank PMs, or create HR, compensation, conduct, approval, client-contact,
execution, or OMS decisions. Downstream UI remains future expansion.
The review-action route family now supports preview and immutable create/read/list lifecycle at
`POST /api/v1/rebalance/pm-operating-quality/review-actions/preview`,
`POST /api/v1/rebalance/pm-operating-quality/review-actions`,
`GET /api/v1/rebalance/pm-operating-quality/review-actions`, and
`GET /api/v1/rebalance/pm-operating-quality/review-actions/{review_action_id}`. It emits
bounded `PmOperatingQualityReviewAction:v1` ledger rows over existing score-run or
fairness-analysis evidence, preserving target content hashes and bank review references without
mutating score runs, recomputing fairness posture, ranking PMs, creating HR/compensation/conduct
decisions, contacting clients, approving trades, routing orders, or claiming OMS execution.
`lotus-gateway` PR #213 (`62ce4c4`) now exposes the bounded PM operating quality BFF route family at
`/api/v1/dpm/command-center/pm-operating-quality/*`, forwarding Manage policy and score-run
payloads without calculating scores, ranking PMs, administering policy locally, or creating HR,
compensation, conduct, approval, client-contact, execution, or OMS decisions. Workbench PM-quality
UI remains future owner scope and must consume Gateway only.
`lotus-ai` PR #70 (`1951f62`) adds `pm_quality_summary.pack@v1` for review-gated support-only
summaries over Manage-owned `PmOperatingQualityScoreRun` evidence. The pack validates score-run
identity, source refs, supportability posture, optional bounded portfolio-memory context, and
forbidden-use controls, and it must not calculate scores, rank PMs, generate HR/compensation/
conduct decisions, contact clients, approve trades, route orders, claim execution, or invent
missing source facts. Gateway/Workbench product invocation remains future owner scope.
Target-state features are not support claims until the owning RFC is implemented, certified,
live-proven, and reflected in
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
  the canonical source-ready stack defaults to `LOTUS_MANAGE_EXPECT_STATEFUL_CORE_SOURCING=available`
  because RFC-087 source products and stateful manage gates are active. Set
  `LOTUS_MANAGE_EXPECT_STATEFUL_CORE_SOURCING=disabled` only when deliberately validating a
  non-source-ready local runtime.
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
   `LOTUS_MANAGE_EXPECT_STATEFUL_CORE_SOURCING=available`, which is the repo-native default for the
   canonical source-ready stack after `lotus-core` exposes the RFC-087 certified source-data
   products and canonical data is seeded. The live proof now includes
   stateful source-backed construction over `TransactionCostCurve:v1`,
   `PortfolioCashflowProjection:v1`, `ClientRestrictionProfile:v1`, and
   `SustainabilityPreferenceProfile:v1`, not only stateful simulate lineage.
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
7. wave simulation item diagnostics can expose bounded `proposed_changes` from selected
   construction alternatives. These rows are pre-trade review evidence only and are not orders,
   executions, fills, or OMS instructions.
8. source-owned cash methodology depth is consumed as evidence from `lotus-core`. Current Core
   products include `PortfolioCashflowProjection:v1`, `PortfolioLiquidityLadder:v1`, and
   `PortfolioCashMovementSummary:v1`; Manage does not forecast cashflows, issue funding or
   treasury instructions, or acknowledge OMS execution.
9. source-owned external OMS acknowledgement posture is consumed as fail-closed evidence from
   `lotus-core` `ExternalOrderExecutionAcknowledgement:v1`; Manage records blocked diagnostics
   and exposes structured `DPM_OUTCOME_EXTERNAL_EXECUTION_BOUNDARY` evidence on supportability,
   report-input, and AI-evidence handoffs only.
   Manage does not generate orders, route venues, certify best execution, ingest OMS
   acknowledgements, confirm fills, project settlement, or reconcile execution status.
10. outcome-review supportability, report-input, and AI-evidence handoffs also expose structured
    `DPM_OUTCOME_CLIENT_COMMUNICATION_BOUNDARY` evidence. Manage may support internal PM, CIO,
    compliance, operations, report, and AI review workflows, but it does not contact clients,
    generate client-ready messages, collect client approval, confirm delivery, or certify client
    communication audit truth.

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
