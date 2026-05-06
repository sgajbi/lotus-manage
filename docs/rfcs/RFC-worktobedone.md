# RFC Work To Be Done Ledger

This ledger records implementation-backed remaining work after an RFC is closed or partially
delivered. It is not an aspirational backlog and it must not be used to claim support for unfinished
features.

Purpose:

1. preserve what remains after an RFC without weakening the RFC closure result,
2. explain why each remaining item was not implemented in the completed wave,
3. assign the owning application or source authority,
4. define the conditions that must be true before implementation starts,
5. define proof and documentation requirements for promoting a feature to supported status.

Governance rules:

1. no item in this ledger is a supported-feature claim,
2. each item must identify the owning repository or explicitly state that ownership is not yet
   established,
3. source-data gaps must be fixed in the source-owning application, not locally cloned in
   `lotus-manage`,
4. Gateway and Workbench items must consume domain-authoritative services through the governed
   product path,
5. promotion requires implementation, tests, OpenAPI/API certification where applicable, live or
   canonical evidence, README/wiki/supported-features updates, PR merge, wiki publication, and branch
   cleanup.

Wiki decision for this ledger update:

The existing `wiki/Supported-Features.md`, `wiki/RFC-Index.md`, and `wiki/Roadmap.md` already state
the RFC-0036 through RFC-0041 supported boundaries and the major unpromoted capabilities. This
ledger is a repo-local planning/control artifact for follow-up sequencing, so no additional wiki
source change is required for this slice. If this ledger later becomes the public cross-RFC backlog
used for product planning or client roadmap discussion, add a wiki page and sidebar link in the
same PR.

## RFC-0036 - DPM Stateful Core Sourcing And Endpoint Consolidation

Current closure status:

RFC-0036 is implemented and gold-pass clean for the `lotus-manage` API surface and stateful
core-sourced execution path. It removed duplicate unversioned routes and advisory/proposal runtime
remnants, made stateless execution explicit, added the gated stateful `portfolio_id` execution
envelope, composed governed `lotus-core` RFC-087 source products, preserved source lineage and
supportability, certified the implemented APIs, proved live `manage.dev.lotus` plus
`core-control.dev.lotus` / `core-query.dev.lotus`, published wiki truth, and kept stateful
capability publication behind explicit runtime gates.

Closure evidence:

| Evidence | Location |
| --- | --- |
| Governing RFC | `docs/rfcs/RFC-0036-dpm-stateful-core-sourcing-and-endpoint-consolidation.md` |
| Supported feature claims | `wiki/Supported-Features.md` stateful execution and core source-sourcing rows |
| Manage/core proof target | `make live-api-validate-core` |
| Manage implementation | `src/core/dpm_source_context.py`, `src/infrastructure/core_sourcing/`, rebalance simulate/analyze/async API paths |
| Source products proven | `DpmModelPortfolioTarget:v1`, `DiscretionaryMandateBinding:v1`, `InstrumentEligibilityProfile:v1`, `PortfolioTaxLotWindow:v1`, `MarketDataCoverageWindow:v1`, `DpmSourceReadiness:v1` |
| Live proof posture | RFC-087 core validation 7/7 and manage/core validation 11/11 with `--expect-stateful-core-sourcing available` |

### Remaining Work Summary

These items are deliberately outside RFC-0036 closure because RFC-0036 certified the service API
surface and stateful source resolver, while product composition, richer upstream source depth, and
mesh/product promotion belong to downstream or platform/source owners.

| ID | Work item | Owner | Current status | Why it was not done in RFC-0036 |
| --- | --- | --- | --- | --- |
| RFC36-WTBD-001 | Gateway integration rebuilt against canonical `/api/v1` manage APIs | `lotus-gateway` | Completed and merged to `lotus-gateway` `main` in PR #191 (`a68181b`) | Endpoint cleanup intentionally accepted breaking stale Gateway assumptions. Gateway now consumes certified manage APIs without reintroducing aliases or monolithic context assumptions. |
| RFC36-WTBD-002 | Workbench product surfaces over stateful manage execution | `lotus-workbench` through Gateway/BFF | Follow-on after Gateway | Workbench must not call manage directly and should only surface stateful behavior once Gateway composition is certified. |
| RFC36-WTBD-003 | Portfolio-level DPM operation dashboards over stateful executions | `lotus-gateway`, `lotus-workbench`, `lotus-manage` | Proposed | RFC-0036 certified execution/source posture, not product dashboards over operations and supportability. |
| RFC36-WTBD-004 | Promote additional stateful DPM source-data products into platform mesh certification | `lotus-platform` with source producers and `lotus-manage` consumer declarations | Deferred until source-data lineage stabilizes | Current source products are live-proven; future stateful products need producer approval, declarations, trust telemetry, SLO/access/evidence policies, and certification. |
| RFC36-WTBD-005 | Additional upstream source-product depth for stateful execution | `lotus-core` and future source owners | Deferred source enrichment | RFC-0036 consumes the certified RFC-087 products. Additional portfolio, market-data, cashflow, benchmark, restriction, or execution-depth sources require explicit retrieval design. |
| RFC36-WTBD-006 | Downstream migration handling if production consumers of removed aliases are discovered | Owning consumer repo, likely `lotus-gateway` | Conditional | RFC-0036 removed stale aliases by design. Permanent compatibility code should not be added unless a real production dependency is proven. |

### Detailed Follow-Up Items

#### RFC36-WTBD-001 - Gateway Integration Rebuilt Against Canonical `/api/v1` Manage APIs

Target business outcome:

Gateway composes the certified manage rebalance, supportability, capability, and stateful-source
posture through clean `/api/v1` contracts without stale aliases or retired monolithic core context.

Closure status:

Completed on 2026-05-06 through `lotus-gateway` PR #191,
`test: guard manage canonical API consumption`, merged to `main` at
`a68181bdd9b8721b5cd613709392ce0e6e89748b`.

What was delivered:

1. `lotus-gateway` already consumed manage through versioned `/api/v1` APIs for rebalance run
   lookup, supportability summary, capability posture, construction alternatives, and
   outcome-review report/AI evidence paths.
2. Added executable regression coverage in
   `lotus-gateway/tests/unit/test_upstream_clients.py::test_dpm_client_uses_only_canonical_manage_api_v1_contracts`
   to exercise every manage-facing `DpmClient` method and reject retired unversioned route
   families, platform capability aliases, and monolithic `dpm-execution-context` assumptions.
3. Tightened `lotus-gateway/docs/standards/RFC-0082-upstream-contract-family-map.md` so the
   manage upstream contract family explicitly records the canonical `/api/v1` route posture and
   boundary rule.

Validation evidence:

1. Local targeted proof:
   `python -m pytest tests/unit/test_upstream_clients.py -k "dpm_client_uses_only_canonical_manage_api_v1_contracts or dpm_client_manage_routes or dpm_client_outcome_review_command_routes or dpm_client_construction_generate_route"`
   passed with 17 selected tests.
2. Local repo gate: `make check` passed in `lotus-gateway`, including Ruff lint, Ruff format
   check, monetary-float guard, mypy, Workbench contract smoke, and 423 unit/contract tests.
3. GitHub PR #191 checks passed before merge: Feature Lane lint/typecheck/unit, Feature Lane
   workflow lint, PR Merge Gate workflow lint, lint/typecheck/unit, integration tests, coverage
   gate, Docker build validation, CI local Docker parity, and queue auto-merge.
4. Wiki synchronization check/publish for `lotus-gateway` completed with diff count 0 because no
   wiki source change was required for this developer-standards/test hardening.

Gold-pass assessment:

This WTBD has reached the expected standard for its stated scope. The owning Gateway implementation
is merged to `main`, the canonical manage route posture is protected by direct regression tests, the
developer contract map is updated, CI has passed, and no unmerged Gateway branch contains additional
durable truth for this item.

#### RFC36-WTBD-002 - Workbench Product Surfaces Over Stateful Manage Execution

Target business outcome:

Workbench can present stateful DPM execution readiness and outcomes to users through Gateway-backed
flows, while hiding the technical source-resolution complexity.

Why it cannot be done now:

Workbench must consume Gateway/BFF only. RFC-0036 did not implement Gateway composition, so a
Workbench product surface would either call manage directly or duplicate capability/source logic.

Dependencies satisfied:

1. RFC36-WTBD-001 complete,
2. Workbench BFF/client modules consume Gateway only,
3. UI clearly distinguishes stateless and stateful availability,
4. source-incomplete states are visible and not treated as generic failures,
5. canonical browser proof covers stateful available and unavailable modes.

Expected implementation wave:

Implement in `lotus-workbench` after Gateway integration is certified.

Promotion proof:

1. Workbench BFF/component/browser tests,
2. accessibility and degraded-state proof,
3. canonical front-office evidence,
4. supported-feature updates that do not imply direct Workbench/manage coupling.

#### RFC36-WTBD-003 - Portfolio-Level DPM Operation Dashboards

Target business outcome:

Operations and PM users can monitor stateful DPM execution supportability, source readiness,
recent runs, errors, and workflow posture at portfolio/book level.

Why it cannot be done now:

RFC-0036 focused on source resolution, endpoint cleanup, execution envelopes, and capability truth.
Dashboards require product composition and durable UX/reporting decisions across Gateway and
Workbench.

Dependencies before implementation:

1. Gateway/Workbench stateful integration complete,
2. dashboard information architecture and supportability taxonomy defined,
3. manage exposes any missing read models through certified APIs instead of UI-side aggregation,
4. no-sensitive telemetry and bounded labels are preserved,
5. canonical proof includes useful populated and degraded cases.

Expected implementation wave:

Implement after the command-center and stateful execution product paths are clear, likely alongside
RFC-0038/RFC-0041 product realization.

Promotion proof:

1. manage read-model tests if new APIs are needed,
2. Gateway/Workbench dashboard tests,
3. live/canonical evidence,
4. operations-facing wiki/runbook updates.

#### RFC36-WTBD-004 - Additional Stateful Source Products In Mesh Certification

Target business outcome:

Every stateful source product used by DPM execution has producer declarations, consumer
declarations, trust telemetry, SLO/access/evidence policies, and platform certification.

Why it cannot be done now:

RFC-0036 validated current RFC-087 source products and existing declarations. Future products must
wait for upstream producer approval and stable lineage/supportability semantics.

Dependencies before implementation:

1. source owner declares the product,
2. `lotus-manage` adds or updates consumer declarations,
3. trust telemetry and SLO/access/evidence policies are available,
4. platform mesh certification includes the product,
5. live proof shows source readiness and degraded behavior.

Expected implementation wave:

Implement product by product as new stateful source dependencies are introduced.

Promotion proof:

1. producer and consumer declarations validate,
2. platform mesh certification passes,
3. manage live proof consumes the product,
4. README/wiki/context updates state the new source dependency.

#### RFC36-WTBD-005 - Additional Upstream Source-Product Depth

Target business outcome:

Stateful DPM execution can consume richer source truth, such as benchmark, cashflow, restriction,
market-data depth, execution cost, or portfolio operations data, without expanding manage into a
source-data owner.

Why it cannot be done now:

RFC-0036 proved the RFC-087 source family and explicitly states that future stateful resolution
must be added only after upstream producer approval and explicit retrieval design.

Dependencies before implementation:

1. source owner and contract for each new source family,
2. source-readiness and lineage semantics,
3. manage resolver and transformer tests,
4. feature-gated capability publication if user-visible,
5. live proof for ready, stale, missing, and incomplete source states.

Expected implementation wave:

Add only when a downstream RFC requires the source and the source owner is ready.

Promotion proof:

1. source-owner certification,
2. manage resolver tests,
3. `make live-api-validate-core` or successor live proof,
4. supported-feature/context updates.

#### RFC36-WTBD-006 - Conditional Downstream Migration Handling

Target business outcome:

If a real production consumer of removed aliases or retired routes appears, it is migrated without
polluting the strategic manage API contract.

Why it cannot be done now:

RFC-0036 found no production dependency that justified permanent compatibility code. Adding aliases
preemptively would reverse the cleanup and weaken the target contract.

Dependencies before implementation:

1. consumer and route/payload dependency are proven,
2. owning consumer repo accepts a migration issue,
3. any temporary adapter has an expiry/removal plan,
4. manage API vocabulary remains clean,
5. no unsupported legacy behavior is advertised.

Expected implementation wave:

Only execute if a real consumer dependency is discovered.

Promotion proof:

1. migration issue and owner,
2. temporary adapter tests if needed,
3. removal evidence,
4. docs explaining the strategic contract remains canonical.

### Suggested Sequencing

Recommended order:

1. rebuild Gateway integration against canonical manage APIs,
2. add Workbench product surfaces through Gateway,
3. implement portfolio-level operation dashboards if needed,
4. add new source products and mesh certification as future RFCs require them,
5. handle legacy-consumer migration only if an actual production dependency is proven.

### RFC-0036 Promotion Checklist For Any Future Item

Before any item above moves from this ledger into a supported-feature claim:

1. canonical `/api/v1` contracts remain the only supported service APIs,
2. stateful capability publication remains gated and truthful,
3. manage does not become a source-data owner,
4. Gateway and Workbench consume through the governed product path,
5. source-ready, stale, missing, unavailable, and disabled-gate states are tested,
6. OpenAPI/Swagger quality is certified for every API added or changed,
7. live or canonical front-office evidence is captured and critically reviewed,
8. README, RFC, wiki, supported-features, endpoint certification, and repository context are
   aligned,
9. PR checks are green, PRs are merged, wiki is published, and branches are cleaned.

## RFC-0037 - DPM Operating System And Mandate Intelligence

Current closure status:

RFC-0037 is a `PROPOSED` strategic parent roadmap, not a single implementation closure. It defines
the target DPM operating-system proposition and the execution contract inherited by RFC-0038
through RFC-0043. Implementation-backed support has advanced through RFC-0038, RFC-0039, RFC-0040,
the manage-owned explicit-list scope of RFC-0041, and the RFC-0042 manage backend outcome-review
authority. RFC-0043 remains proposed, while multiple Gateway, Workbench, report, AI,
source-product, and canonical front-office realization items remain unpromoted.

Closure evidence:

| Evidence | Location |
| --- | --- |
| Strategic RFC | `docs/rfcs/RFC-0037-dpm-operating-system-and-mandate-intelligence.md` |
| RFC family status | `docs/rfcs/README.md` |
| Supported feature truth | `wiki/Supported-Features.md` |
| Repository current-state truth | `REPOSITORY-ENGINEERING-CONTEXT.md` |
| Implementation-backed child RFCs | RFC-0038, RFC-0039, RFC-0040, RFC-0041, RFC-0042 manage backend authority |
| Remaining proposed child RFCs | RFC-0043 |

### Remaining Work Summary

These items remain because RFC-0037 is intentionally a strategic target-state roadmap. The correct
delivery path is to complete and prove the child RFCs and downstream/source-owner implementations,
not to mark RFC-0037 complete from roadmap text alone.

| ID | Work item | Owner | Current status | Why it was not done in RFC-0037 |
| --- | --- | --- | --- | --- |
| RFC37-WTBD-001 | Complete RFC-0042 post-trade outcome feedback loop | `lotus-manage` plus `lotus-core`, `lotus-risk`, `lotus-performance`, `lotus-gateway`, `lotus-workbench` | Manage backend complete; downstream/source-owner realization remains | RFC-0037 identifies outcome learning as target-state. RFC-0042 delivered the manage authority; full product and richer source-owner realization still require owning-app work. |
| RFC37-WTBD-002 | Complete RFC-0043 governed AI PM copilot | `lotus-ai`, consumed by Gateway/Workbench/manage evidence | Proposed | AI must use governed workflow packs, guardrails, provenance, and unavailable fallback; roadmap text is not implementation. |
| RFC37-WTBD-003 | Full front-office DPM product realization across Gateway and Workbench | `lotus-gateway`, `lotus-workbench` | Proposed / downstream addenda exist for several features | Backend child RFCs do not equal product-surface support. Gateway and Workbench must implement and prove the full experience. |
| RFC37-WTBD-004 | Source-product depth for mandate personalization, PM-book discovery, sustainability, restrictions, risk, performance, cost, cashflow, and scenarios | `lotus-core`, `lotus-risk`, `lotus-performance`, future source owners | Deferred source-authority work | RFC-0037 requires rich private-banking source truth that cannot be fabricated in manage. |
| RFC37-WTBD-005 | Report, archive, and client/internal evidence materialization | `lotus-report`, `lotus-render`, `lotus-archive` | Proposed downstream work | RFC-0040 provides proof-pack input; generated documents and archive lifecycle belong to report/render/archive. |
| RFC37-WTBD-006 | Canonical sales/demo story from implementation-backed stack evidence | `lotus-platform`, `lotus-workbench`, `lotus-gateway`, participating domain apps | Proposed | RFC-0037 requires demo-ready story only after backend APIs, Gateway, Workbench, seeds, browser proof, and docs are aligned. |
| RFC37-WTBD-007 | Portfolio memory across mandate, construction, proof-pack, wave, outcome, report, and AI events | Cross-app, with manage as workflow/evidence participant | Proposed strategic extension | Manage outcome-review events now exist from RFC-0042, but full portfolio memory still needs downstream product surfaces and report/AI event sources. |

### Detailed Follow-Up Items

#### RFC37-WTBD-001 - RFC-0042 Post-Trade Outcome Feedback Loop

Target business outcome:

Expected-versus-realized outcome evidence closes the DPM loop so future construction, monitoring,
and governance can learn from actual execution, risk, and performance outcomes.

Current implementation-backed result:

RFC-0042 is done for the `lotus-manage` backend authority. Manage now provides source-backed
outcome-review preview/create/retrieve/search, immutable persistence and append-only events,
source-refresh eventing, supportability diagnostics, certified OpenAPI, and bounded report-input
and AI-evidence input handoffs. It deliberately does not claim Gateway/Workbench product support,
rendered reports, AI narrative, execution/OMS integration, PM scoring, or source-owner
risk/performance/tax/FX/cash methodologies.

Why work remains:

The full RFC-0037 outcome-learning business outcome requires downstream product realization and
source-owner enrichment beyond the manage backend. Gateway and Workbench must implement the
RFC-0098 realization path, and richer realized risk/performance/execution/tax/FX/cash source
methodologies must come from owning apps rather than manage-local approximation.

Dependencies before remaining work:

1. Gateway outcome-review composition over certified manage APIs,
2. Workbench outcome-review UX through Gateway/BFF only,
3. source-owner contracts for any richer realized risk, performance, execution, tax, FX, cash, or
   attribution dimensions,
4. report/render/archive implementation if generated outcome artifacts are required,
5. RFC-0043 or `lotus-ai` workflow-pack implementation for governed AI narrative over outcome
   evidence,
6. canonical front-office proof before any product-surface support claim.

Expected implementation wave:

Use the RFC-0042 manage backend as the authority. Implement remaining work in the owning apps:
Gateway first, Workbench second, then report/render/archive, AI, and source-owner enrichment as
separate governed slices.

Promotion proof:

1. Gateway and Workbench API/BFF/UI tests,
2. source-owner contract and live evidence tests for any new realized dimensions,
3. canonical front-office evidence with populated and degraded outcome-review states,
4. OpenAPI certification and supported-feature updates in every owning app,
5. wiki publication and branch cleanup after merge.

#### RFC37-WTBD-002 - RFC-0043 Governed AI PM Copilot

Target business outcome:

AI assists PMs with summarization, evidence packaging, exception narratives, and review support
without becoming the source of investment truth.

Why it cannot be done now:

RFC-0043 remains proposed and AI behavior belongs to `lotus-ai`. Manage can provide structured
evidence, but AI workflow packs, prompts, guardrails, provenance, and fallback behavior must be
implemented in the owning service.

Dependencies before implementation:

1. RFC-0043 tightened to execution-grade form,
2. `lotus-ai` workflow-pack and guardrail contracts,
3. evidence input contracts from RFC-0040/RFC-0041/RFC-0042,
4. Gateway/Workbench AI posture and unavailable-state rules,
5. sensitive-field and unsupported-action tests.

Expected implementation wave:

Implement in `lotus-ai` and integrate through Gateway/Workbench after evidence contracts are
stable.

Promotion proof:

1. AI guardrail/eval tests,
2. provenance and evidence-hash proof,
3. unavailable/blocked fallback evidence,
4. Gateway/Workbench integration proof if surfaced.

#### RFC37-WTBD-003 - Full Front-Office DPM Product Realization

Target business outcome:

The DPM operating system is visible as a coherent front-office workflow: command center,
construction lab, proof-pack review, rebalance waves, outcome feedback, and AI assistance.

Why it cannot be done now:

Manage child RFCs have delivered backend foundations, but full product realization requires
Gateway composition, Workbench UX, canonical seed data, browser proof, and audience-ready
documentation across apps.

Dependencies before implementation:

1. Gateway compositions for RFC-0038 through RFC-0043 features,
2. Workbench panels and workflows through BFF only,
3. canonical front-office seed and validation automation,
4. backend supportability and degraded states surfaced truthfully,
5. product docs and demos backed by live evidence.

Expected implementation wave:

Execute feature by feature after the owning backend contracts are stable, then close with a
cross-app product-realization proof.

Promotion proof:

1. canonical front-office evidence pack,
2. API/BFF/browser/accessibility/visual checks,
3. demo screenshots only after validation passes,
4. wiki material for developers, business users, operations, sales/pre-sales, and client demos.

#### RFC37-WTBD-004 - Source-Product Depth For Crown-Jewel DPM

Target business outcome:

DPM decisions are based on rich private-banking source truth: mandate objectives, PM books,
benchmarks, risk/performance analytics, client restrictions, sustainability, cashflow, costs,
currency policy, and scenarios.

Why it cannot be done now:

These source products belong to domain owners. RFC-0037 correctly states the ambition but does not
make manage the source authority.

Dependencies before implementation:

1. source-owner contracts and declarations,
2. producer and consumer mesh certification where applicable,
3. manage adapters and degraded-state behavior,
4. Gateway/Workbench posture rules,
5. live proof with missing/stale/partial source states.

Expected implementation wave:

Add source depth as demanded by child RFCs and product-realization slices. Do not bundle unrelated
source families into one large manage change.

Promotion proof:

1. owner API certification,
2. manage consumer tests,
3. live/canonical evidence,
4. supported-feature updates naming the exact source products.

#### RFC37-WTBD-005 - Report, Archive, And Evidence Materialization

Target business outcome:

PM, investment committee, client, compliance, and audit audiences can receive governed documents
and archives generated from DPM evidence.

Why it cannot be done now:

`lotus-report`, `lotus-render`, and `lotus-archive` own generated documents and archive lifecycle.
RFC-0037 cannot claim those outputs until owning apps implement them against manage evidence.

Dependencies before implementation:

1. report-input contracts from proof packs, waves, and outcomes,
2. render templates and deterministic output rules,
3. archive retention/legal-hold/access-audit rules,
4. Gateway/Workbench report posture,
5. live proof that documents reconcile to source evidence.

Expected implementation wave:

Implement through report/render/archive RFCs after evidence contracts stabilize.

Promotion proof:

1. report/render/archive tests,
2. deterministic artifact evidence,
3. archive retrieval and retention proof,
4. docs and supported-feature promotion in owning apps.

#### RFC37-WTBD-006 - Canonical Sales/Demo Story

Target business outcome:

Sales, pre-sales, marketing, client demos, operations, and engineering can show the crown-jewel DPM
story using real canonical stack evidence rather than screenshots disconnected from backend truth.

Why it cannot be done now:

Several product surfaces and source-product depths remain unimplemented. Demo material must wait
until canonical API, calculation, panel, and browser validation pass.

Dependencies before implementation:

1. canonical seed automation,
2. Gateway and Workbench product surfaces,
3. backend live evidence for promoted features,
4. wiki pages with diagrams and audience-aware explanations,
5. demo screenshots labeled and tied to validated evidence.

Expected implementation wave:

Build progressively as each product surface becomes implementation-backed, then package a
cross-app demo/pitch evidence set.

Promotion proof:

1. canonical front-office QA evidence,
2. screenshots after validation only,
3. wiki/demo pages linked to implementation evidence,
4. no unsupported feature claims.

#### RFC37-WTBD-007 - Portfolio Memory Across The DPM Lifecycle

Target business outcome:

Lotus preserves a durable, searchable, governed decision memory across mandate health,
construction, proof packs, rebalance waves, execution outcomes, reports, and AI evidence.

Why it cannot be done now:

RFC-0038 through RFC-0041 provide important event/evidence pieces, but RFC-0042 outcome events,
report/archive materialization, AI provenance, and front-office surfaces are still incomplete.

Dependencies before implementation:

1. event identity and retention policy across child RFCs,
2. RFC-0042 outcome events,
3. report/archive and AI evidence refs,
4. Gateway/Workbench timeline/search UX,
5. access, redaction, and audit policy.

Expected implementation wave:

Treat as a later cross-RFC portfolio-memory RFC or closure slice after RFC-0042/RFC-0043 and
downstream product surfaces are implemented.

Promotion proof:

1. event reconciliation tests,
2. timeline/search API and UI proof,
3. access/redaction tests,
4. canonical evidence and documentation.

### Suggested Sequencing

Recommended order:

1. tighten and implement RFC-0042,
2. tighten and implement RFC-0043 with `lotus-ai`,
3. complete Gateway/Workbench realization for RFC-0038 through RFC-0043,
4. add source-product depth in owning apps as specific product claims require it,
5. implement report/render/archive evidence materialization,
6. package canonical sales/demo story,
7. close portfolio-memory as a cross-RFC product capability.

### RFC-0037 Promotion Checklist For Any Future Item

Before any RFC-0037 target-state item moves into a supported-feature claim:

1. owning child RFC or downstream/source-owner RFC is implementation-backed,
2. source ownership remains explicit,
3. Gateway and Workbench consume through the governed product path,
4. proof exists beyond roadmap language,
5. docs/wiki/supported-features distinguish backend foundation from full product realization,
6. canonical evidence supports demo/pitch material,
7. PR checks are green, PRs are merged, wiki is published, and branches are cleaned.

## RFC-0038 - Mandate Digital Twin, Health Score, And DPM Command Center Foundation

Current closure status:

RFC-0038 delivered the implementation-backed `lotus-manage` backend foundation for mandate digital
twins, deterministic mandate health, monitoring exceptions, monitoring runs, and a bounded DPM
command-center summary. The supported scope is backend/API foundation: source-mapped refresh/read,
version, diff, health read/recalculate, monitoring run, exception, and command-center APIs with
in-memory and PostgreSQL persistence, OpenAPI certification, local live proof, local canonical
manage plus live `lotus-core` proof, README/wiki/supported-feature updates, and published wiki
truth.

Closure evidence:

| Evidence | Location |
| --- | --- |
| Governing RFC | `docs/rfcs/RFC-0038-mandate-digital-twin-health-and-command-center.md` |
| Source-data field map | `docs/rfcs/RFC-0038-source-data-field-map.md` |
| Supported feature claims | `wiki/Supported-Features.md` mandate digital-twin, monitoring, exceptions, and command-center rows |
| Manage live proof | `output/rfc0038-live-proof/20260503T063617Z/summary.json` |
| Manage implementation | `src/core/mandates.py`, `src/core/mandate_repository.py`, `src/api/services/mandate_service.py`, `src/api/routers/mandates.py`, `src/api/routers/monitoring.py`, `src/infrastructure/mandates/` |
| Tests | `tests/unit/dpm/core/test_mandate_health.py`, `tests/unit/dpm/api/test_mandates_api.py`, `tests/unit/dpm/api/test_monitoring_api.py`, `tests/unit/dpm/supportability/test_dpm_mandate_repository.py` |
| Downstream handoff | `docs/architecture/dpm-command-center-gateway-workbench-handoff.md`, `sgajbi/lotus-gateway#180`, `sgajbi/lotus-workbench#140`, `sgajbi/lotus-platform#294` |

### Remaining Work Summary

These items are deliberately not done in RFC-0038 because the RFC delivered manage backend
foundation, while full command-center product realization, PM-book discovery, richer source
products, and canonical seed automation belong to downstream or source-owning applications.

| ID | Work item | Owner | Current status | Why it was not done in RFC-0038 |
| --- | --- | --- | --- | --- |
| RFC38-WTBD-001 | Gateway DPM command-center composition | `lotus-gateway` | Downstream issue opened; implementation not supported yet | Manage contracts had to stabilize first. Gateway must compose manage mandate/health/monitoring truth without becoming mandate-health authority. |
| RFC38-WTBD-002 | Workbench DPM cockpit panels | `lotus-workbench` | Downstream issue opened; implementation not supported yet | Workbench must consume Gateway/BFF only and must not reconstruct health scoring or source readiness in browser code. |
| RFC38-WTBD-003 | Platform canonical seed automation for populated command-center proof | `lotus-platform` with source-app seeds | Downstream issue opened | Manage proof used canonical IDs, but durable cross-app seed automation for populated, partial, and empty command-center states belongs to platform/source owners. |
| RFC38-WTBD-004 | PM-book discovery for monitoring and command-center cohorts | `lotus-core` or future relationship-book authority | Deferred with no support claim | RFC-0038 supports caller-supplied mandate IDs and persisted monitoring runs. No certified PM-book membership source exists yet. |
| RFC38-WTBD-005 | Mandate objective, benchmark, review cadence, and model-change source products | `lotus-core`, `lotus-performance`, CIO/model authority | Deferred source enrichment | MVP fields are source-backed, derived, or gap-coded. Dedicated source products are required before richer personalization can be claimed. |
| RFC38-WTBD-006 | Client restriction, sustainability, and cashflow source products | `lotus-core` or dedicated client-governance/cashflow owners | Deferred source enrichment | Health dimensions preserve gaps rather than inventing restrictions, ESG preferences, or cashflow forecasts. |
| RFC38-WTBD-007 | Broader risk and performance health enrichment | `lotus-risk`, `lotus-performance` | Deferred unless owning-service contracts are consumed | Manage health cannot clone risk or performance methodology. Risk/performance attention must come from certified owners. |
| RFC38-WTBD-008 | Full front-office command-center product support | `lotus-gateway`, `lotus-workbench`, with manage as backend foundation | Proposed, not supported | Full product support requires Gateway composition, Workbench cockpit implementation, canonical runtime proof, and cross-app documentation. |

### Detailed Follow-Up Items

#### RFC38-WTBD-001 - Gateway DPM Command-Center Composition

Target business outcome:

Gateway exposes a product-facing DPM command-center contract that composes mandate digital twins,
health, monitoring runs, active exceptions, supportability, and drill-down links while preserving
`lotus-manage` as the health and monitoring authority.

Why it cannot be done now:

RFC-0038 had to first stabilize manage APIs, monitoring-run scoping, exception filtering, source
readiness, and OpenAPI contracts. Gateway implementation before that proof would have created
speculative composition or duplicated health logic.

Dependencies before implementation:

1. use `docs/architecture/dpm-command-center-gateway-workbench-handoff.md` and
   `sgajbi/lotus-gateway#180` as execution inputs,
2. typed Gateway client consumes manage mandate, health, monitoring, exception, and command-center
   APIs,
3. Gateway preserves manage supportability, reason codes, latest-run identity, and attention
   counts,
4. Gateway does not recompute health scores, source readiness, or exception taxonomy,
5. Gateway OpenAPI and endpoint certification cover degraded, empty, partial, and populated states.

Expected implementation wave:

Implement in `lotus-gateway` before Workbench DPM cockpit panels.

Promotion proof:

1. Gateway unit and contract tests,
2. no-reconstruction tests for health dimensions and exception state,
3. live Gateway proof against manage,
4. OpenAPI quality and vocabulary validation,
5. Gateway README/wiki/supported-features updates.

#### RFC38-WTBD-002 - Workbench DPM Cockpit Panels

Target business outcome:

PMs and operations users can view mandate health, source readiness, attention queues, recommended
actions, latest monitoring run, and mandate drill-downs through a populated Workbench cockpit.

Why it cannot be done now:

Workbench must consume Gateway/BFF contracts only. Implementing panels before Gateway composition
would force direct manage calls or UI-side health reconstruction, both of which RFC-0038 explicitly
forbids.

Dependencies before implementation:

1. RFC38-WTBD-001 complete,
2. Workbench BFF/client modules consume Gateway only,
3. panels cover populated, partial, empty, degraded, and unavailable states,
4. browser code does not calculate health, source readiness, or supportability,
5. canonical runtime proof uses governed front-office validation paths.

Expected implementation wave:

Implement in `lotus-workbench` after Gateway composition. Use `PB_SG_GLOBAL_BAL_001` and governed
canonical runtime proof when producing demo-ready screenshots.

Promotion proof:

1. Workbench component, BFF, and browser tests,
2. accessibility and visual validation,
3. canonical front-office evidence with populated panels,
4. screenshots only after validation passes,
5. Workbench README/wiki/supported-features updates.

#### RFC38-WTBD-003 - Platform Canonical Seed Automation

Target business outcome:

The canonical front-office stack can reliably seed and validate populated, partial, and empty DPM
command-center states for demo, QA, and regression proof.

Why it cannot be done now:

RFC-0038 documented the required canonical identities and opened `sgajbi/lotus-platform#294`, but
seed orchestration across core/manage/Gateway/Workbench belongs to `lotus-platform` and source-app
owners.

Dependencies before implementation:

1. platform seed contract for `PB_SG_GLOBAL_BAL_001`, `MANDATE_PB_SG_GLOBAL_BAL_001`,
   `PM_SG_DPM_001`, `BOOK_SG_BALANCED_DPM`, tenant `default`, and RFC-087 source products,
2. source apps expose or load required seed records,
3. validation covers populated, partial, and empty command-center states,
4. seed automation avoids stale Docker images and propagates stateful manage gates correctly,
5. generated evidence records source lineage and supportability.

Expected implementation wave:

Implement in `lotus-platform` as canonical front-office seed/validation automation, then consume in
Gateway and Workbench proof.

Promotion proof:

1. platform automation tests,
2. canonical runtime validation artifacts,
3. source-product lineage evidence,
4. docs/runbook updates,
5. downstream Gateway/Workbench proof reuse.

#### RFC38-WTBD-004 - PM-Book Discovery For Monitoring And Command-Center Cohorts

Target business outcome:

The DPM command center can populate by PM book or portfolio-manager cohort without requiring
callers to supply every mandate or portfolio id manually.

Why it cannot be done now:

No certified PM-book or portfolio-manager book authority exists. RFC-0038 therefore supports
caller-supplied mandate IDs and persisted monitoring runs while making book discovery gaps explicit.

Dependencies before implementation:

1. PM-book or relationship-book source owner assigned,
2. certified API exposes book identity, mandate/portfolio membership, as-of date, freshness,
   permissions, lineage, and empty/partial semantics,
3. manage consumer contract and degraded-state behavior,
4. Gateway and Workbench product-state expectations updated,
5. live proof covers populated, partial, empty, stale, and permission-denied books.

Expected implementation wave:

Implement after source product proof. This may align with RFC-0041 PM-book discovery work but must
also support monitoring-run and command-center semantics.

Promotion proof:

1. source-owner OpenAPI/tests/live proof,
2. manage monitoring and command-center integration tests,
3. Gateway/Workbench integration proof if surfaced,
4. supported-feature language that names the exact supported book source.

#### RFC38-WTBD-005 - Mandate Objective, Benchmark, Review Cadence, And Model-Change Sources

Target business outcome:

Mandate twins and health scores can use source-backed objective profiles, benchmark bindings,
review cadence, last/next review dates, and CIO model-change lifecycle rather than local defaults or
gap-coded nulls.

Why it cannot be done now:

RFC-0038's MVP correctly used available `lotus-core` mandate binding and model target products,
while recording missing fields as gaps. Inventing objective, benchmark, or model-change facts in
manage would make the twin misleading.

Dependencies before implementation:

1. `MandateObjectiveProfile:v1` or equivalent source product,
2. benchmark binding source from `lotus-core` or `lotus-performance`,
3. review cadence/date source and CIO model-change event source,
4. manage adapter and health-dimension tests,
5. live proof with source-ready and source-gap cases.

Expected implementation wave:

Implement after source products are available. Update health scoring only where source evidence is
clear and backward gap behavior remains explicit.

Promotion proof:

1. source-owner certification,
2. manage twin/health tests,
3. OpenAPI examples and field descriptions,
4. live evidence with changed health outcomes from source-backed fields.

#### RFC38-WTBD-006 - Client Restriction, Sustainability, And Cashflow Source Products

Target business outcome:

Mandate health can assess restriction, sustainability, liquidity, income-need, and cashflow risks
from source-backed client and portfolio profiles.

Why it cannot be done now:

No certified `ClientRestrictionProfile:v1`, `SustainabilityPreferenceProfile:v1`, or
`PortfolioCashflowForecast:v1` source exists for RFC-0038. Manage preserves gaps and does not
fabricate compliance or cashflow facts.

Dependencies before implementation:

1. source-owner products and permission model,
2. effective date, expiry, jurisdiction, client/mandate binding, and lineage semantics,
3. health scoring rules for missing, stale, partial, and blocked profiles,
4. Workbench/Gateway presentation rules if surfaced,
5. documentation that avoids unsupported ESG/compliance claims.

Expected implementation wave:

Implement after source products exist. Coordinate with RFC-0039 ESG/restriction construction and
RFC-0040 proof-pack enrichment so semantics stay consistent.

Promotion proof:

1. source-owner tests and live proof,
2. manage health-dimension tests,
3. canonical evidence with missing and partial profile cases,
4. README/wiki/supported-feature updates.

#### RFC38-WTBD-007 - Broader Risk And Performance Health Enrichment

Target business outcome:

Mandate health can incorporate benchmark-aware risk and performance attention from authoritative
analytics services.

Why it cannot be done now:

Risk and performance methodology belong to `lotus-risk` and `lotus-performance`. RFC-0038 keeps
health dimensions deterministic and source-aware without cloning those analytics.

Dependencies before implementation:

1. risk health/attention contract from `lotus-risk`,
2. performance under-review/benchmark-relative attention contract from `lotus-performance`,
3. benchmark identity and period semantics,
4. manage adapter tests for ready/degraded/stale/partial analytics,
5. Gateway/Workbench supportability presentation rules.

Expected implementation wave:

Implement after analytics contracts exist. Manage should consume supportability and reason codes
from the owners.

Promotion proof:

1. owning-service API certification,
2. manage health and command-center tests,
3. live mixed-readiness proof,
4. supported-feature updates naming supported analytics.

#### RFC38-WTBD-008 - Full Front-Office Command-Center Product Support

Target business outcome:

DPM command-center becomes a complete front-office product surface across manage, Gateway, and
Workbench, backed by canonical data and demo-ready documentation.

Why it cannot be done now:

RFC-0038 closed the backend foundation only. Full product support requires Gateway implementation,
Workbench cockpit panels, canonical seed automation, browser proof, and cross-repo docs.

Dependencies before implementation:

1. RFC38-WTBD-001 complete,
2. RFC38-WTBD-002 complete,
3. RFC38-WTBD-003 complete,
4. canonical front-office validation passes,
5. supported-feature ledgers align across apps.

Expected implementation wave:

Close as a cross-app product-realization slice after Gateway, Workbench, and platform seed
automation are implemented.

Promotion proof:

1. canonical front-office evidence pack,
2. API/BFF/browser/accessibility/visual checks,
3. demo screenshots tied to validated backend proof,
4. wiki material suitable for business, operations, sales/pre-sales, and demos.

### Suggested Sequencing

Recommended order:

1. implement Gateway DPM command-center composition,
2. implement platform canonical seed automation or the minimum needed for populated product proof,
3. implement Workbench DPM cockpit panels,
4. prove full front-office command-center support,
5. add PM-book discovery when a source authority exists,
6. add objective, restriction, sustainability, cashflow, risk, and performance enrichments from
   owning services.

Rationale:

Gateway and Workbench can realize the already-supported backend foundation before every enrichment
source exists. Source enrichments should improve quality later without blocking product visibility,
provided unsupported fields remain explicit and degraded.

### RFC-0038 Promotion Checklist For Any Future Item

Before any item above moves from this ledger into a supported-feature claim:

1. owning repository and source contract are explicit,
2. manage does not invent mandate, book, risk, performance, restriction, sustainability, or
   cashflow facts,
3. Gateway and Workbench consume through the governed product path,
4. degraded, empty, partial, stale, unavailable, and permission-denied states are tested,
5. OpenAPI/Swagger quality is certified for every API added or changed,
6. live or canonical front-office evidence is captured and critically reviewed,
7. README, RFC/source-map, wiki, supported-features, endpoint certification, and repository context
   are aligned,
8. PR checks are green, PRs are merged, wiki is published, and branches are cleaned.

## RFC-0039 - Advanced Portfolio Construction And Rebalance Alternatives

Current closure status:

RFC-0039 delivered the implementation-backed `lotus-manage` backend foundation for construction
alternative generation, comparison, retrieval, persistence, and actor-attributed selection. The
supported manage backend methods are `DO_NOTHING_BASELINE`, `HEURISTIC_EXPLAINABLE`,
`MIN_TURNOVER`, `TAX_AWARE`, `SOLVER_CONSTRAINED`, `RISK_AWARE`, `LIQUIDITY_AWARE`,
`CURRENCY_OVERLAY`, and `REGIME_STRESS_AWARE`. `ESG_AWARE` remains deliberately degraded with
`ESG_RESTRICTION_AWARE_CONSTRUCTION_DEFERRED`.

Closure evidence:

| Evidence | Location |
| --- | --- |
| Governing RFC | `docs/rfcs/RFC-0039-advanced-portfolio-construction-and-rebalance-alternatives.md` |
| Source-data and method map | `docs/rfcs/RFC-0039-source-data-and-method-map.md` |
| Supported feature claim | `wiki/Supported-Features.md` construction rows |
| Live proof | `output/rfc0039-proof/20260503-193842-authority-backed-canonical/summary.json` |
| Manage implementation | `src/core/construction/`, `src/api/services/construction_service.py`, `src/api/routers/construction.py`, `src/infrastructure/construction/`, `src/infrastructure/risk_authority/` |
| Tests | `tests/unit/dpm/api/test_construction_api.py`, `tests/unit/dpm/infrastructure/test_risk_authority_client.py` |
| Downstream handoff | `docs/architecture/dpm-construction-alternatives-gateway-workbench-handoff.md`, Gateway/Workbench RFC-0098 construction addenda |

### Remaining Work Summary

These items are deliberately not done in RFC-0039 because manage owns construction-alternative
truth, while product realization and several richer source authorities belong outside manage.

| ID | Work item | Owner | Current status | Why it was not done in RFC-0039 |
| --- | --- | --- | --- | --- |
| RFC39-WTBD-001 | Gateway construction-alternatives composition | `lotus-gateway` | Implemented, merged, CI-proven, and wiki-published through `lotus-gateway` PR #190 | Gateway consumes manage alternatives without recomputing construction truth or choosing alternatives. Product support still requires Workbench implementation and canonical front-office proof. |
| RFC39-WTBD-002 | Workbench construction lab / alternatives comparison UX | `lotus-workbench` | Implemented, merged, CI-proven, live-proven, and wiki-published through `lotus-workbench` PR #150 and PR #151 | Workbench consumes Gateway/BFF construction contracts only, sends governed DPM context, renders manage-owned alternatives and traces without browser optimization, and is proven by focused canonical Workbench live evidence. |
| RFC39-WTBD-003 | Full front-office construction-lab product realization | `lotus-gateway`, `lotus-workbench`, with manage as backend authority | First-wave Gateway/Workbench realization implemented and wiki-published through `lotus-gateway` PR #190 plus `lotus-workbench` PR #150/#151 | The current PM-facing path is implementation-backed for generated alternatives, supportability, comparison, and selection controls. Richer lifecycle depth across proof packs, waves, reports, AI, approval staging, and demos remains RFC39-WTBD-010 / later command-center work. |
| RFC39-WTBD-004 | ESG/restriction-aware construction support | `lotus-core` or dedicated client-governance/sustainability source, consumed by manage | Deferred with explicit degraded posture | No certified restriction and sustainability profile products exist. Full ESG support would be a false compliance claim. |
| RFC39-WTBD-005 | Broader risk/performance alternative enrichment | `lotus-risk`, `lotus-performance` | Deferred beyond current seams/authority-backed concentration support | Current `RISK_AWARE` consumes concentration authority; broader tracking error, drawdown, stress contribution, attribution, and benchmark-relative performance need owning-service contracts. |
| RFC39-WTBD-006 | Authoritative transaction-cost and cost-aware alternatives | Future cost/execution source | Deferred with labelled local estimates only | No authoritative `TransactionCostCurve:v1` source exists. |
| RFC39-WTBD-007 | Cashflow/income-need aware liquidity construction | `lotus-core` plus future income-need source | First wave implemented for source-backed cashflow projection; income-need planning remains deferred | `LIQUIDITY_AWARE` now accepts `lotus-core` `PortfolioCashflowProjection:v1` total net cashflow evidence and evaluates projected cash pressure against minimum cash policy. Client income-needs/forecast methodology remains unsupported until a source owner publishes a governed product. |
| RFC39-WTBD-008 | Treasury-depth currency overlay | `lotus-core` / treasury policy / execution source | Deferred source depth beyond current policy-backed overlay | Current support uses FX readiness and bounded currency-overlay context; forward curves, hedge instruments, and treasury execution readiness are not source-backed. |
| RFC39-WTBD-009 | First-class regime scenario-pack source | `lotus-risk` / CIO scenario authority, consumed by `lotus-manage` | First-wave implemented for `RegimeScenarioPackEvaluation:v1`; product UX remains downstream | `lotus-risk` now owns a certified scenario-pack evaluation source product, and manage consumes it for `REGIME_STRESS_AWARE` when `DPM_RISK_BASE_URL` is configured. Broader scenario contribution rows, approvals workflow, Gateway composition, and Workbench UX remain downstream/future depth. |
| RFC39-WTBD-010 | Construction alternative lifecycle across proof packs, waves, reports, and AI | `lotus-manage`, `lotus-report`, `lotus-ai`, `lotus-gateway`, `lotus-workbench` | Proposed strategic extension | RFC-0039 selects alternatives; cross-RFC lifecycle needs RFC-0040 proof packs, RFC-0041 waves, report/AI owners, and product surfaces. |

### Detailed Follow-Up Items

#### RFC39-WTBD-001 - Gateway Construction-Alternatives Composition

Target business outcome:

Gateway exposes construction-alternative sets, comparison metrics, selected-alternative state,
supportability, and action posture to Workbench while preserving manage as construction authority.

Why it cannot be done now:

Completed on 2026-05-06 through `lotus-gateway` PR #190 after RFC-0039 stabilized manage
alternative contracts, selection events, source-supportability posture, and live evidence.

Implemented scope:

1. Gateway RFC-0098 construction addendum is used as execution guide.
2. typed Gateway client consumes manage generate/read/select APIs:
   `POST /api/v1/construction/alternative-sets/generate`,
   `GET /api/v1/construction/alternative-sets/{alternative_set_id}`, and
   `POST /api/v1/construction/alternative-sets/{alternative_set_id}/selections`.
3. Gateway exposes Workbench-facing BFF routes:
   `POST /api/v1/dpm/command-center/construction/alternative-sets/generate`,
   `GET /api/v1/dpm/command-center/construction/alternative-sets/{alternative_set_id}`, and
   `POST /api/v1/dpm/command-center/construction/alternative-sets/{alternative_set_id}/selections`.
4. Gateway preserves alternative IDs, method statuses, objective terms, constraint traces,
   comparison metrics, source supportability, and selected state,
5. Gateway does not run optimizer, recompute metrics, infer source readiness, execute orders, or
   choose alternatives,
6. Gateway documents construction composition as an implementation-backed feature in README, RFC,
   repo context, and published wiki.

Validation and merge evidence:

1. `lotus-gateway` PR #190 merged to `main`.
2. PR checks passed: Feature Lane lint/typecheck/unit and workflow lint; PR Merge Gate
   lint/typecheck/unit, integration, coverage, Docker build, Docker parity, workflow lint, and queue
   checks.
3. Post-merge local validation passed on `main`:
   `python -m pytest tests\unit\test_dpm_construction_service.py tests\integration\test_dpm_construction_router.py tests\contract\test_dpm_construction_contract.py -q`
   with 10 tests passed.
4. Gateway wiki published from repo source with zero drift after publication.
5. Gateway branch cleaned after merge.

Remaining dependency:

Workbench construction lab and canonical front-office proof were completed afterward through
`lotus-workbench` PR #150 and PR #151. Gateway remains the composition boundary and does not
convert construction support into order execution, proof-pack lifecycle, or AI/report lifecycle
claims.

#### RFC39-WTBD-002 - Workbench Construction Lab / Alternatives Comparison UX

Target business outcome:

PMs can compare construction alternatives, inspect objective/constraint traces, understand degraded
source posture, and select an alternative through a governed Workbench journey.

Completion status:

Complete for the current Workbench construction-lab scope on 2026-05-06. `lotus-workbench`
PR #150 merged the Gateway-backed construction alternatives panel and PR #151 merged the
follow-up live-proof hardening that remained on the feature branch after PR #150 auto-merged.

Implemented scope:

1. `/workbench/{portfolioId}` renders a Construction Alternatives panel for the canonical DPM
   workflow,
2. Workbench uses the BFF/Gateway route family only:
   `POST /api/v1/dpm/command-center/construction/alternative-sets/generate`,
   `GET /api/v1/dpm/command-center/construction/alternative-sets/{alternative_set_id}`, and
   `POST /api/v1/dpm/command-center/construction/alternative-sets/{alternative_set_id}/selections`,
3. Workbench sends governed DPM source context instead of relying on page-level reporting dates:
   `MANDATE_PB_SG_GLOBAL_BAL_001`, `MODEL_PB_SG_GLOBAL_BAL_DPM`, `booking_center_code=Singapore`,
   and canonical construction source date `2026-04-10`,
4. generated alternatives, method status, drift/turnover metrics, objective trace count,
   constraint trace count, reason codes, correlation id, selected alternative state, and manage
   authority are rendered from Gateway/manage truth,
5. the panel keeps Gateway mediation visible after generation while showing `lotus-manage` as the
   data authority,
6. browser code does not optimize, auto-select, recompute construction metrics, infer source
   supportability, or clone manage methodology,
7. a focused live Playwright proof was added as `npm run live:validate:construction`,
8. README and wiki validation material now document the live proof command and evidence path.

Validation and merge evidence:

1. `lotus-workbench` PR #150 merged to `main` as merge commit
   `d96bc0eada11e8ecb5ac224cc04d9c9a155935ac`,
2. follow-up `lotus-workbench` PR #151 merged to `main` as
   `ac951d5` after the unmerged live-proof commit was found on the feature branch,
3. PR #150 checks passed: Feature Lane, PR Merge Gate lint/typecheck/coverage/build, Playwright
   smoke, Docker build, Docker parity, workflow lint, and queue checks,
4. PR #151 checks passed: Feature Lane and PR Merge Gate including Docker parity, Playwright
   smoke, Docker build, coverage/build, and workflow lint,
5. local targeted tests passed:
   `npx vitest run tests/unit/workbench-api.test.ts tests/unit/domain-product-discovery-client.test.tsx tests/unit/construction-alternatives-panel.test.tsx`
   with 46 tests passed,
6. local full Workbench gate passed before merge:
   `make check` with lint, typecheck, coverage 155 files / 704 tests, and Next production build,
7. focused live proof passed:
   `npm run live:validate:construction` against canonical `PB_SG_GLOBAL_BAL_001`,
8. live proof generated `output/rfc39-wtbd002-construction-lab/construction-live/construction-alternatives-live-summary.json`
   with response status `200`, source service `lotus-manage`, authority `lotus-manage:RFC-0039`,
   correlation `corr-workbench-construction-PB_SG_GLOBAL_BAL_001-2026-04-10`, three alternatives,
   visible Gateway mediation, and no local optimizer/methodology claim,
9. Workbench wiki was published from repo source after merge as `lotus-workbench.wiki` commit
   `a908bab`, and `Sync-RepoWikis.ps1 -CheckOnly -Repository lotus-workbench` returned clean.

Quality improvements made during closure:

1. fixed the Workbench construction request context after live proof exposed a real
   `DPM_CORE_CONTEXT_INCOMPLETE` failure caused by missing mandate/model context and a mismatched
   booking-center/source-date posture,
2. aligned construction idempotency and correlation keys with the governed construction source date
   rather than the page/reporting as-of date,
3. made Gateway mediation persistent in the panel after successful generation,
4. hardened a flaky domain-product discovery test by waiting on loaded catalog data instead of a
   static page heading,
5. added a repeatable live proof command so future verification is not a one-off manual browser
   exercise.

Remaining dependency:

Richer construction lifecycle depth remains outside RFC39-WTBD-002: proof-pack linkage, wave
orchestration, report/AI narrative lifecycle, approval staging, OMS handoff, and broader
command-center product choreography stay tracked under RFC39-WTBD-010 and later RFC-0098
command-center work.

#### RFC39-WTBD-003 - Full Front-Office Construction-Lab Product Realization

Target business outcome:

Construction alternatives become a complete front-office PM workflow across manage, Gateway, and
Workbench, suitable for demos and real operating use.

Completion status:

Complete for first-wave product realization on 2026-05-06. Manage owns construction authority,
Gateway composes it, and Workbench renders a canonical PM-facing construction-lab path with live
proof. This does not close the later lifecycle expansion tracked in RFC39-WTBD-010.

Implemented scope:

1. `lotus-manage` owns alternative generation, comparison metrics, source supportability, method
   posture, and selection state,
2. `lotus-gateway` PR #190 exposes Workbench-facing construction BFF routes without recomputing
   construction truth,
3. `lotus-workbench` PR #150/#151 renders the PM construction alternatives panel, generation
   action, comparison table, reason codes, traces, and selection controls,
4. README/wiki material in Gateway and Workbench describes the current implementation-backed
   product path,
5. canonical live proof shows a real `PB_SG_GLOBAL_BAL_001` construction alternative set generated
   through the Workbench/Gateway/manage path.

Not included in this first wave:

1. proof-pack attachment for each construction choice,
2. wave-orchestration promotion from selected alternative to rebalance wave,
3. rendered report and archive lifecycle for construction decisions,
4. governed AI narrative over construction choices,
5. OMS or order-staging handoff,
6. richer command-center drawers and demo choreography beyond the embedded Workbench panel.

Those items require cross-RFC lifecycle work and remain tracked under RFC39-WTBD-010 or later
RFC-0098 command-center realization.

#### RFC39-WTBD-004 - ESG/Restriction-Aware Construction Support

Target business outcome:

Construction alternatives can enforce client restrictions, sustainability preferences, product
eligibility, and ESG exclusions from source-backed profiles.

Why it cannot be done now:

No certified `ClientRestrictionProfile:v1` or `SustainabilityPreferenceProfile:v1` exists. RFC-0039
therefore keeps `ESG_AWARE` degraded and prevents client/sales material from claiming full ESG or
restriction-aware construction.

Dependencies before implementation:

1. restriction and sustainability source products,
2. source-owner permission, effective-date, expiry, jurisdiction, client/mandate binding, and
   lineage semantics,
3. manage method eligibility and constraint tests,
4. proof-pack and health semantics aligned with RFC-0038/RFC-0040,
5. Workbench presentation rules if surfaced.

Expected implementation wave:

Implement only after source authorities exist. Coordinate with RFC-0038 health enrichment and
RFC-0040 proof-pack enrichment.

Promotion proof:

1. source-owner certification,
2. manage construction tests for ready/degraded/blocked profile states,
3. live evidence with compliant and blocked portfolios,
4. README/wiki/supported-feature updates that avoid unsupported ESG claims.

#### RFC39-WTBD-005 - Broader Risk/Performance Alternative Enrichment

Target business outcome:

Alternative comparisons include source-backed tracking error, volatility, drawdown, stress
contribution, attribution, and benchmark-relative performance context where available.

Why it cannot be done now:

Current support consumes `lotus-risk` concentration authority for `RISK_AWARE`, but broader risk
and performance analytics need certified owner contracts. Manage must not recalculate risk or
performance methodology.

Dependencies before implementation:

1. `RiskAlternativeEnrichment:v1` or equivalent from `lotus-risk`,
2. `PerformanceBenchmarkContext:v1` or equivalent from `lotus-performance`,
3. benchmark identity, as-of date, period vocabulary, freshness, and supportability semantics,
4. manage adapter tests,
5. Gateway/Workbench posture if displayed.

Expected implementation wave:

Implement after analytics source products exist. Preserve degraded supportability when unavailable.

Promotion proof:

1. owning-service API certification,
2. manage alternative-enrichment tests,
3. live proof with ready and degraded analytics,
4. OpenAPI/endpoint-certification updates,
5. supported-feature wording naming the exact analytics supported.

#### RFC39-WTBD-006 - Authoritative Transaction-Cost And Cost-Aware Alternatives

Target business outcome:

PMs can compare alternatives using source-backed spread, commission, and market-impact estimates
rather than local labelled diagnostics.

Why it cannot be done now:

No authoritative cost curve or execution-cost source exists. RFC-0039 allows only clearly labelled
estimated cost diagnostics.

Dependencies before implementation:

1. `TransactionCostCurve:v1` or equivalent owner,
2. instrument/venue/currency applicability and freshness semantics,
3. manage cost-aware objective and constraint tests,
4. degraded behavior for stale/missing/inapplicable curves,
5. documentation distinguishing estimates from authoritative costs.

Expected implementation wave:

Implement after the cost/execution source is certified.

Promotion proof:

1. source-owner tests,
2. manage method tests and live proof,
3. OpenAPI/supportability updates,
4. supported-feature promotion only for source-backed cost contexts.

#### RFC39-WTBD-007 - Cashflow/Income-Need Aware Liquidity Construction

Current implementation status:

First-wave implementation is complete for source-backed cashflow projection liquidity posture.
`lotus-core` now owns `PortfolioCashflowProjection:v1`, and `lotus-manage` `LIQUIDITY_AWARE`
construction accepts that source product through `AuthoritativeLiquidityContext.cashflow_projection`.
Manage uses the source-owned `total_net_cashflow`, currency, projection window, projected-row
posture, source fingerprint, data-quality status, latest evidence timestamp, and bounded reason
codes to evaluate projected cash pressure against the liquidity policy. If the projected net
cashflow would reduce adjusted post-trade cash below the minimum cash weight, the method moves to
`PENDING_REVIEW` with `CASHFLOW_PROJECTION_ADJUSTED_CASH_BELOW_POLICY`. If the projection is stale,
wrong-currency, lacks projected rows, or otherwise degraded by the source, the method degrades
truthfully and preserves source reason codes.

Target business outcome:

Liquidity-aware alternatives can account for client income needs, expected cashflows, and future
liquidity events rather than only current cash, settlement, and minimum cash policy.

What remains deferred:

Client income-need planning and forecast methodology remain unsupported. `PortfolioCashflowProjection:v1`
is a source-owned projection of portfolio cashflows; it is not a client income-need profile, spending
plan, liability ladder, or wealth-planning forecast. Manage must not fabricate income needs or
liability timing from current cash, transactions, or projection totals.

Dependencies before implementation:

Completed first-wave dependencies:

1. `lotus-core` certified `PortfolioCashflowProjection:v1`,
2. source-owned currency, projection-window, projected-row, freshness, fingerprint, and reason-code
   posture,
3. manage liquidity objective tests for ready, degraded, currency-mismatch, no-projected-row, and
   below-policy cash pressure cases.

Remaining dependencies before full income-need support:

1. client income-need or liability-planning source product,
2. income need and forecast horizon semantics distinct from portfolio cashflow projection,
3. confidence/freshness posture for client planning inputs,
4. proof-pack and Workbench presentation alignment if surfaced as client income-need support.

Expected implementation wave:

The source-backed cashflow projection wave is implemented in manage after core source proof. The
income-need planning wave must wait for an owning source product.

Promotion proof:

1. source-owner certification for `PortfolioCashflowProjection:v1`,
2. manage liquidity/cashflow tests,
3. local and PR-gate evidence for ready, pending-review, degraded, and unsupported client-income
   posture,
4. supported-feature update.

#### RFC39-WTBD-008 - Treasury-Depth Currency Overlay

Target business outcome:

Currency-overlay construction can use treasury policy, forward curves, hedge instruments, and
execution readiness rather than FX spot readiness and bounded policy context alone.

Why it cannot be done now:

RFC-0039 supports policy-backed overlay posture, but no treasury-depth source products exist for
forward curves, hedge instruments, or execution readiness.

Dependencies before implementation:

1. `CurrencyExposurePolicy:v1` or treasury policy source,
2. forward curves and hedge instrument eligibility,
3. settlement/execution readiness for hedge actions,
4. manage overlay tests for ready/degraded/blocked states,
5. Gateway/Workbench display rules if surfaced.

Expected implementation wave:

Implement after treasury/source products are certified.

Promotion proof:

1. source-owner tests,
2. manage overlay tests and live proof,
3. documentation distinguishing policy-backed from treasury-backed overlay support.

#### RFC39-WTBD-009 - First-Class Regime Scenario-Pack Source

Target business outcome:

Regime-stress-aware alternatives can consume governed scenario packs from risk/CIO authority with
explicit assumptions, approvals, applicability, and stress result lineage.

Current implementation status:

First-wave implementation is complete for source-backed regime scenario evaluation.
`lotus-risk` owns `RegimeScenarioPackEvaluation:v1` and exposes
`POST /analytics/risk/regime-scenario-pack/evaluate`. `lotus-manage` consumes that source product
through the bounded `LotusRiskAuthorityClient` when `DPM_RISK_BASE_URL` is configured and
`REGIME_STRESS_AWARE` is requested without caller-supplied scenario context. Manage sends
post-construction asset-class exposure weights, portfolio id, business as-of date, governed
scenario pack id, and policy maximum loss threshold to `lotus-risk`; it uses only the returned
supportability, source service, scenario pack id, worst-case loss, policy threshold, and reason
codes to govern method posture. Excess loss remains `PENDING_REVIEW`; unavailable or invalid risk
responses fail closed into degraded manage supportability rather than locally calculating stress
methodology.

What remains deferred:

Broader scenario-pack maturity remains future depth. The first-wave source product evaluates a
governed pack against exposure weights; it does not yet expose per-security stress contribution,
CIO approval workflow evidence, portfolio applicability exceptions beyond bounded reason codes, or
Gateway/Workbench product surfaces.

Completed first-wave dependencies:

1. `lotus-risk` source product and API for `RegimeScenarioPackEvaluation:v1`,
2. platform domain-data-product mirror for `RegimeScenarioPackEvaluation:v1`,
3. manage risk-authority adapter tests for request shape, supportability, breach posture, invalid
   responses, and retries,
4. manage construction API tests proving automatic source-backed `REGIME_STRESS_AWARE` resolution,
5. README, RFC source map, wiki, supported-features, and repository context alignment.

Remaining dependencies before full product realization:

1. Gateway construction-alternatives composition,
2. Workbench construction lab UX,
3. scenario contribution or CIO-approval source fields if future product claims require them,
4. canonical browser proof after Gateway/Workbench support exists.

Expected implementation wave:

The source-product and manage-consumer wave is implemented. Product realization follows
RFC39-WTBD-001 through RFC39-WTBD-003.

Promotion proof:

1. source-owner certification in `lotus-risk`,
2. platform mirror PR for `RegimeScenarioPackEvaluation:v1`,
3. manage scenario method tests and proof,
4. supported-feature update distinguishing backend support from downstream product support.

#### RFC39-WTBD-010 - Construction Lifecycle Across Proof Packs, Waves, Reports, And AI

Target business outcome:

A selected construction alternative flows coherently into proof packs, rebalance waves, reports,
and governed AI evidence without any app reconstructing construction truth.

Why it cannot be done now:

RFC-0039 stops at construction alternatives and selection. Cross-RFC lifecycle depends on RFC-0040
proof packs, RFC-0041 waves, report/AI owning services, and Gateway/Workbench product surfaces.

Dependencies before implementation:

1. RFC-0040 proof-pack consumption of selected alternatives,
2. RFC-0041 wave linkage and selected-alternative refs,
3. report and AI owner contracts,
4. Gateway/Workbench product surfaces,
5. event and lineage reconciliation across artifacts.

Expected implementation wave:

Treat as a later cross-RFC closure/product-memory slice after downstream product surfaces and
report/AI owners are implemented.

Promotion proof:

1. lineage tests across alternative, proof pack, wave, report, and AI evidence,
2. live/canonical proof,
3. no-reconstruction tests in Gateway/Workbench/report/AI,
4. README/wiki/supported-feature updates.

### Suggested Sequencing

Recommended order:

1. implement Gateway construction composition,
2. implement Workbench construction lab,
3. prove full front-office construction-lab product support,
4. implement ESG/restriction source products and promote `ESG_AWARE`,
5. add broader risk/performance, cost, cashflow, currency, and scenario source depth,
6. close cross-RFC construction lifecycle after proof packs, waves, reports, AI, Gateway, and
   Workbench are live.

Rationale:

Gateway and Workbench can expose the supported manage backend methods immediately once downstream
composition exists. Enrichment items should be promoted later from source-authoritative contracts
instead of blocking the product surface or creating manage-local methodology clones.

### RFC-0039 Promotion Checklist For Any Future Item

Before any item above moves from this ledger into a supported-feature claim:

1. owning repository and source contract are explicit,
2. manage does not clone risk, performance, cost, sustainability, restriction, cashflow, treasury,
   scenario, report, AI, Gateway, or Workbench behavior,
3. method status remains truthful: `READY`, `PENDING_REVIEW`, `BLOCKED`, or `DEGRADED`,
4. Gateway and Workbench consume through the governed product path,
5. degraded, blocked, stale, partial, unavailable, inapplicable, and solver-fallback states are
   tested where applicable,
6. OpenAPI/Swagger quality is certified for every API added or changed,
7. live or canonical front-office evidence is captured and critically reviewed,
8. README, RFC/source-map, wiki, supported-features, endpoint certification, and repository context
   are aligned,
9. PR checks are green, PRs are merged, wiki is published, and branches are cleaned.

## RFC-0040 - Pre-Trade Proof Pack And Evidence Fabric

Current closure status:

RFC-0040 is `DONE` for the `lotus-manage` owned backend proof-pack authority. The delivered scope
includes `DpmPreTradeProofPack` generation from direct rebalance runs and selected construction
alternatives, immutable JSON persistence, deterministic Markdown, section states, section and
content hashes, lineage, retention metadata, append-only report/AI handoff refs, certified APIs,
bounded report-input and AI-evidence-input adapters, forbidden-field/action guardrails, and
source-backed RFC-0038 mandate-context attachment when mandate evidence exists.

Closure evidence:

| Evidence | Location |
| --- | --- |
| Governing RFC | `docs/rfcs/RFC-0040-pre-trade-proof-pack-and-evidence-fabric.md` |
| Source-map and gap analysis | `docs/rfcs/RFC-0040-source-map-and-gap-analysis.md` |
| Supported feature claim | `wiki/Supported-Features.md` |
| Live proof | `output/rfc0040-proof/20260503-145818/manifest.json` and `critical-review.json` |
| Manage implementation | `src/core/proof_packs/`, `src/api/routers/proof_packs.py`, `src/infrastructure/proof_packs/` |
| Tests | `tests/unit/dpm/proof_packs/`, `tests/unit/dpm/api/test_proof_pack_api.py` |
| Downstream RFC alignment | `lotus-gateway` PR #181 merge `b2c3734`, `lotus-workbench` PR #142 merge `b63981b` |
| Canonical front-office readiness boundary | `lotus-platform/output/front-office-qa/canonical-front-office-qa-20260503-222559.json`, `sgajbi/lotus-gateway#182` |

### Remaining Work Summary

These items are deliberately not done in RFC-0040 because proof-pack backend authority is
manage-owned, while full product realization, document materialization, AI narrative generation,
analytics enrichment, and broader source coverage belong to other Lotus apps.

| ID | Work item | Owner | Current status | Why it was not done in RFC-0040 |
| --- | --- | --- | --- | --- |
| RFC40-WTBD-001 | Gateway proof-pack composition | `lotus-gateway` | Downstream RFC direction aligned; implementation not supported yet | Gateway must consume stable manage proof-pack APIs without reconstructing sections, hashes, report refs, or AI refs. Manage implementation and proof had to stabilize first. |
| RFC40-WTBD-002 | Workbench proof-pack review UX | `lotus-workbench` | Downstream RFC direction aligned; implementation not supported yet | Workbench must consume Gateway/BFF only. Implementing before Gateway composition would force direct manage calls or speculative UI state. |
| RFC40-WTBD-003 | Full front-office proof-pack product realization | `lotus-gateway`, `lotus-workbench`, with manage as backend authority | Proposed, not supported | Manage backend proof is necessary but not sufficient. Canonical front-office QA exposed a downstream Gateway risk-drawdown `partial` boundary tracked in `sgajbi/lotus-gateway#182`. |
| RFC40-WTBD-004 | Report materialization from `DpmProofPackReportInput` | `lotus-report`, `lotus-render`, `lotus-archive` | Deferred to owning services | Manage produces deterministic report input; it does not generate, render, archive, retain, or retrieve report documents. |
| RFC40-WTBD-005 | AI PM memo generation from `DpmProofPackAiEvidenceInput` | `lotus-ai`, later consumed through Gateway/Workbench | Deferred to RFC-0043 / AI owner | Manage produces bounded AI evidence with guardrails; it must not generate AI narrative, prompts, recommendations, or autonomous decisioning. |
| RFC40-WTBD-006 | Broader risk and performance proof-pack enrichment | `lotus-risk`, `lotus-performance`, consumed by manage/Gateway | Deferred unless owning-service contracts are consumed | RFC-0040 preserves degraded sections where source-backed risk/performance context is missing. Manage must not clone analytics methodology. |
| RFC40-WTBD-007 | Authoritative transaction-cost curve | Future cost/execution source, likely execution/platform domain | Deferred with no support claim | Manage may expose labelled estimated cost, but no authoritative `TransactionCostCurve:v1` source exists. |
| RFC40-WTBD-008 | Sustainability preferences and client restriction profiles | `lotus-core` or dedicated client-governance source | Deferred with no support claim | No source-backed `ClientRestrictionProfile:v1` or `SustainabilityPreferenceProfile:v1` is available for proof-pack-ready claims. |
| RFC40-WTBD-009 | Scenario-pack authority beyond supplied context | `lotus-risk` / CIO authority, consumed by `lotus-manage` construction evidence | Partially implemented through selected RFC-0039 alternatives | `RegimeScenarioPackEvaluation:v1` now supplies first-wave scenario-pack evaluation for `REGIME_STRESS_AWARE` alternatives. Proof packs can preserve that selected-alternative context, but richer scenario contribution, CIO approval, and direct proof-pack enrichment remain future source depth. |
| RFC40-WTBD-010 | Decision timeline and portfolio memory across mandate, exception, wave, handoff, and outcome events | `lotus-manage` with downstream/source participants | Proposed strategic extension | RFC-0040 creates proof-pack-local timeline/lineage. Cross-RFC portfolio memory needs RFC-0041 wave links, RFC-0042 outcome events, and product-surface realization before support can be claimed. |

### Detailed Follow-Up Items

#### RFC40-WTBD-001 - Gateway Proof-Pack Composition

Target business outcome:

Gateway exposes a Workbench-facing proof-pack contract that preserves manage-owned evidence while
adding experience-layer posture for entitlements, availability, report status, AI status, archive
status, and command-center context.

Why it cannot be done now:

RFC-0040 stabilized the manage proof-pack artifact, hashes, refs, and API shape. Gateway
composition before that proof would have required speculative contracts or duplicated proof-pack
logic. Slice 8 corrected the downstream RFC ownership language, but it did not implement runtime
Gateway composition.

Dependencies before implementation:

1. Gateway RFC-0098 proof-pack addendum is used as execution guide,
2. typed manage client consumes proof-pack generate/read/Markdown/report-input/AI-evidence routes,
3. Gateway preserves manage `proof_pack_id`, section states, reason codes, source refs, hashes,
   report refs, and AI refs,
4. Gateway composes report/archive/AI posture only from owning services,
5. Gateway does not calculate proof-pack section state or modify persisted evidence.

Expected implementation wave:

Implement in `lotus-gateway` before Workbench proof-pack UX. This should be a Gateway-owned RFC
implementation slice with OpenAPI certification, no-reconstruction tests, and live Gateway proof
against manage.

Promotion proof:

1. Gateway unit, contract, and OpenAPI tests,
2. no-reconstruction tests for section states, hashes, refs, and reason codes,
3. degraded/unavailable manage posture tests,
4. live Gateway proof against manage proof-pack APIs,
5. Gateway README/wiki/supported-features/endpoint-certification updates.

#### RFC40-WTBD-002 - Workbench Proof-Pack Review UX

Target business outcome:

Portfolio managers, reviewers, operations, and client-facing teams can inspect proof packs in
Workbench with section readiness, evidence drawers, Markdown preview, report/AI posture, lineage,
hashes, and action eligibility backed by Gateway truth.

Why it cannot be done now:

Workbench must consume Gateway/BFF contracts only. Without Gateway proof-pack composition,
Workbench would either call manage directly or recreate proof-pack posture in browser code. Both
would violate the governed front-office architecture.

Dependencies before implementation:

1. RFC40-WTBD-001 complete,
2. Workbench BFF/client modules consume Gateway only,
3. UX covers section matrix, degraded/blocked/pending-review states, evidence detail, lineage,
   Markdown preview, report/AI readiness, and supportability,
4. no browser-side fact generation, hashing, report input generation, or AI evidence generation,
5. canonical front-office validation path is available for proof.

Expected implementation wave:

Implement in `lotus-workbench` after Gateway composition. Use the canonical front-office runtime
when producing demo-ready screenshots or proof.

Promotion proof:

1. Workbench component and BFF contract tests,
2. browser validation for ready/degraded/blocked proof packs,
3. accessibility and responsive layout checks,
4. canonical front-office evidence with backend validation passed,
5. Workbench README/wiki/supported-features updates.

#### RFC40-WTBD-003 - Full Front-Office Proof-Pack Product Realization

Target business outcome:

Proof packs are available as an end-to-end product workflow across manage, Gateway, and Workbench,
with validated backend evidence, composed experience APIs, browser proof, and demo-ready material.

Why it cannot be done now:

Manage proof-pack backend passed. Full product support also requires Gateway runtime composition,
Workbench UX, and canonical front-office QA. The post-merge canonical QA run
`canonical-front-office-qa-20260503-222559.json` failed at Workbench browser validation because
Gateway risk drawdown returned `partial`; that boundary is tracked as `sgajbi/lotus-gateway#182`.

Dependencies before implementation:

1. RFC40-WTBD-001 complete,
2. RFC40-WTBD-002 complete,
3. `sgajbi/lotus-gateway#182` or equivalent front-office readiness blocker resolved or explicitly
   reclassified,
4. canonical front-office validation passes before screenshots are promoted as demo evidence,
5. supported-feature ledgers across manage, Gateway, and Workbench are aligned.

Expected implementation wave:

Treat this as a cross-app closure/proof slice after Gateway and Workbench implementation. Do not
claim full product support from manage evidence alone.

Promotion proof:

1. canonical front-office QA evidence pack,
2. API, BFF, browser, accessibility, and visual validation pass,
3. screenshots tied to validated backend evidence,
4. no unresolved blocking downstream issue,
5. public docs are suitable for developers, operations, business users, sales/pre-sales, and demos.

#### RFC40-WTBD-004 - Report Materialization From `DpmProofPackReportInput`

Target business outcome:

A proof pack can be materialized into a governed report with deterministic rendering, archive
records, retention, legal hold, retrieval, and access audit.

Why it cannot be done now:

`lotus-manage` owns proof-pack evidence and typed report input. It does not own document
generation, rendering, archive lifecycle, or retrieval governance. Implementing those locally would
duplicate `lotus-report`, `lotus-render`, and `lotus-archive` responsibilities.

Dependencies before implementation:

1. `lotus-report` consumer contract for `DpmProofPackReportInput`,
2. render template and deterministic output contract in `lotus-render`,
3. archive retention, legal hold, retrieval, and access-audit contract in `lotus-archive`,
4. source-hash reconciliation from generated report back to manage proof-pack input,
5. Gateway/Workbench report posture if surfaced.

Expected implementation wave:

Implement in report/render/archive owning RFCs after document output scope and audience rules are
clear.

Promotion proof:

1. report/render/archive tests,
2. deterministic report artifact and archive evidence,
3. retention/retrieval/access-audit proof,
4. Gateway/Workbench posture tests if exposed,
5. supported-feature updates in owning apps.

#### RFC40-WTBD-005 - AI PM Memo Generation From `DpmProofPackAiEvidenceInput`

Target business outcome:

PMs can request governed AI assistance over proof-pack evidence while preserving provenance,
guardrails, forbidden-field protections, and unsupported-action blocking.

Why it cannot be done now:

RFC-0040 correctly stopped at bounded AI evidence input. AI prompts, memos, model invocation,
guardrail evaluation, and provenance belong to `lotus-ai` and RFC-0043, not manage.

Dependencies before implementation:

1. RFC-0043 or `lotus-ai` workflow-pack contract,
2. prompt/model provenance and evidence-hash lineage,
3. forbidden-field and forbidden-action guardrails enforced in AI service,
4. unavailable, blocked, redacted, and human-review states,
5. Gateway/Workbench consumption rules if surfaced.

Expected implementation wave:

Implement in `lotus-ai` after RFC-0043 is tightened or executed. Manage remains the evidence
source and should not become an AI generation surface.

Promotion proof:

1. AI guardrail/eval tests,
2. provenance and evidence-hash proof,
3. unavailable/blocked-state tests,
4. Gateway/Workbench integration proof if exposed,
5. supported-feature language that does not imply autonomous trading or approval authority.

#### RFC40-WTBD-006 - Broader Risk And Performance Proof-Pack Enrichment

Target business outcome:

Proof packs include source-backed risk and performance context beyond the first manage-backed
evidence, with clear degraded states when analytics are missing, stale, or partial.

Why it cannot be done now:

Risk and performance analytics are not manage-owned methodology. RFC-0040 can carry degraded
sections and consume source-backed context, but it must not clone risk or performance calculations.

Dependencies before implementation:

1. `lotus-risk` proof-pack-compatible risk enrichment contract,
2. `lotus-performance` benchmark/return/attention context contract,
3. source refs, as-of semantics, benchmark identity, freshness, and supportability states,
4. manage adapter tests for ready/degraded/stale/partial analytics,
5. Gateway posture if analytics are surfaced in the product UI.

Expected implementation wave:

Implement after risk/performance contracts exist. Manage should consume and attach owning-service
lineage, not calculate the analytics.

Promotion proof:

1. owning-service API certification,
2. manage adapter and proof-pack section tests,
3. live mixed-readiness proof,
4. OpenAPI and endpoint-certification updates,
5. supported-feature updates naming exactly which analytics are supported.

#### RFC40-WTBD-007 - Authoritative Transaction-Cost Curve

Target business outcome:

Proof packs can distinguish labelled estimates from source-backed transaction-cost evidence and
show cost supportability clearly.

Why it cannot be done now:

No authoritative transaction-cost source exists. RFC-0040 can preserve labelled estimated cost from
manage diagnostics, but it cannot promote authoritative transaction-cost support.

Dependencies before implementation:

1. source owner assigned for `TransactionCostCurve:v1` or equivalent,
2. curve identity, venue/asset/currency applicability, as-of timestamp, freshness, and lineage,
3. manage adapter rules for missing/stale/inapplicable curves,
4. tests for estimate versus authoritative-cost labeling,
5. documentation warning against unsupported cost precision.

Expected implementation wave:

Implement after the cost/execution source is established and certified.

Promotion proof:

1. source-owner contract tests,
2. manage proof-pack cost-section tests,
3. live evidence for ready and degraded cost posture,
4. OpenAPI/supportability documentation updates,
5. supported-feature promotion only for source-backed cost contexts.

#### RFC40-WTBD-008 - Sustainability Preferences And Client Restriction Profiles

Target business outcome:

Proof packs can explain client restrictions, sustainability preferences, and ESG/restriction
controls from source-backed client governance profiles.

Why it cannot be done now:

No source-backed client restriction or sustainability preference profile is available to manage.
Promoting ESG/restriction-ready proof packs without that source would create a false compliance
claim.

Dependencies before implementation:

1. `ClientRestrictionProfile:v1` and `SustainabilityPreferenceProfile:v1` or equivalent source
   products,
2. source-owner OpenAPI certification and permission model,
3. effective date, expiry, jurisdiction, client/mandate binding, and lineage semantics,
4. manage section-state tests for ready/degraded/blocked/pending-review posture,
5. Workbench presentation rules if surfaced.

Expected implementation wave:

Implement only after the source authority exists. This may align with future core/client-governance
or sustainability RFCs.

Promotion proof:

1. source-owner tests and live proof,
2. manage proof-pack section tests,
3. no unsupported ESG/restriction wording in README/wiki,
4. canonical evidence with at least one missing or partial profile case,
5. supported-feature entry that names the exact profile products consumed.

#### RFC40-WTBD-009 - Scenario-Pack Authority Beyond Supplied Context

Target business outcome:

Proof packs can cite governed CIO/risk scenario packs and regime stress context without relying on
caller-supplied metadata alone.

Current implementation status:

First-wave scenario-pack authority exists through `lotus-risk`
`RegimeScenarioPackEvaluation:v1`, and manage can consume it through RFC-0039
`REGIME_STRESS_AWARE` alternatives. RFC-0040 proof packs preserve selected alternative diagnostics
and scenario context when the selected construction alternative carries it.

What remains deferred:

RFC-0040 does not yet call `lotus-risk` directly to enrich proof packs that lack selected
construction scenario evidence. It also does not yet receive source-owned per-security scenario
contribution rows, CIO approval workflow evidence, effective-period exception posture, or
portfolio/mandate applicability evidence beyond the first-wave evaluation reason codes.

Remaining dependencies before full proof-pack enrichment:

1. scenario contribution and approval evidence from `lotus-risk` / CIO authority if product claims
   require it,
2. manage proof-pack adapter tests for direct enrichment when no selected alternative carries
   scenario evidence,
3. proof-pack section-state behavior for stale, missing, inapplicable, and contribution-partial
   scenario evidence,
4. Gateway/Workbench posture if displayed,
5. methodology and business documentation for any richer scenario meaning.

Expected implementation wave:

The first-wave source and selected-alternative preservation path is implemented. Direct proof-pack
enrichment and richer scenario evidence should be handled only if a future proof-pack/product RFC
requires those fields.

Promotion proof:

1. source-owner API and methodology tests,
2. manage proof-pack scenario-section tests if direct proof-pack enrichment is added,
3. live proof with ready and degraded scenario posture,
4. documentation and supported-feature updates that distinguish supplied from certified context.

#### RFC40-WTBD-010 - Decision Timeline And Portfolio Memory

Target business outcome:

Lotus can show a durable portfolio-management memory across mandate health, monitoring exceptions,
construction alternatives, proof packs, rebalance waves, approvals, operations handoff, and
post-trade outcomes.

Why it cannot be done now:

RFC-0040 builds proof-pack-local lineage and decision timeline, but the cross-RFC memory requires
RFC-0041 wave linkage, RFC-0042 outcome feedback, downstream product surfaces, and careful
event-retention semantics. Promoting it from proof-pack evidence alone would overstate the current
system.

Dependencies before implementation:

1. RFC-0041 wave events consumed as source-backed timeline nodes,
2. RFC-0042 post-trade outcome events defined and implemented,
3. event identity, retention, redaction, and audit policy across apps,
4. Gateway/Workbench timeline views consume authoritative events only,
5. report/AI consumers use timeline evidence without reconstructing facts.

Expected implementation wave:

Treat this as a later cross-RFC portfolio-memory slice after RFC-0042 is implemented and downstream
product surfaces exist.

Promotion proof:

1. event contract and retention tests,
2. manage/Gateway/Workbench integration tests,
3. proof that timeline nodes reconcile to source artifacts,
4. canonical front-office evidence,
5. README/wiki/supported-feature updates explaining audience and retention boundaries.

### Suggested Sequencing

Recommended order:

1. implement Gateway proof-pack composition,
2. implement Workbench proof-pack review UX,
3. resolve canonical front-office readiness blockers and prove full product realization,
4. implement report materialization in report/render/archive owners,
5. implement AI PM memo generation in `lotus-ai` under RFC-0043 controls,
6. add broader risk/performance enrichment from owning analytics services,
7. add transaction-cost, sustainability/restriction, and scenario-pack source products,
8. revisit decision timeline and portfolio memory after RFC-0041 and RFC-0042 event sources are
   fully available.

Rationale:

Gateway and Workbench can realize the already-supported manage proof-pack backend before broader
source enrichment exists. Report and AI should follow their owning-service controls. Risk,
performance, cost, sustainability, restriction, and scenario enrichment should be promoted only
after source authorities are certified. Portfolio memory should wait until wave and post-trade
outcome events exist.

### RFC-0040 Promotion Checklist For Any Future Item

Before any item above moves from this ledger into a supported-feature claim:

1. owning repository and API/source contract are explicit,
2. manage remains proof-pack authority and does not clone report, AI, Gateway, Workbench, risk,
   performance, cost, sustainability, restriction, or scenario behavior,
3. Gateway and Workbench consume through the governed product path,
4. report/AI/archive products preserve proof-pack hashes and lineage,
5. degraded, blocked, stale, partial, unavailable, permission-denied, redacted, and
   human-review-required states are tested where applicable,
6. OpenAPI/Swagger quality is certified for every API added or changed,
7. live or canonical front-office evidence is captured and critically reviewed,
8. README, RFC/source-map, wiki, supported-features, endpoint certification, and repository context
   are aligned,
9. PR checks are green, PRs are merged, wiki is published, and branches are cleaned.

## RFC-0041 - Rebalance Wave Orchestration And CIO Model Change Impact

Current closure status:

RFC-0041 is `DONE` for the `lotus-manage` owned backend authority over explicit portfolio-list
rebalance waves. The delivered scope includes durable preview/create, source-check,
RFC-0039-backed ready-item simulation, item selection, RFC-0040 proof-pack linkage,
approval-with-exceptions, staging, internal operations handoff evidence with
`external_execution_claimed=false`, pre-execution cancellation, wave search/detail/item/proof-pack
posture/supportability read models, OpenAPI certification, Postgres-backed persistence, live proof,
hardening, documentation, wiki publication, and supported-feature promotion.

Closure evidence:

| Evidence | Location |
| --- | --- |
| Governing RFC | `docs/rfcs/RFC-0041-rebalance-wave-orchestration-and-cio-model-change-impact.md` |
| Source-map and gap analysis | `docs/rfcs/RFC-0041-source-map-and-gap-analysis.md` |
| Supported feature claim | `wiki/Supported-Features.md` |
| Live proof | `output/rfc0041-wave-proof/20260504-231914/manifest.json` and `critical-review.json` |
| Manage implementation | `src/core/waves/`, `src/api/services/wave_service.py`, `src/api/routers/waves.py`, `src/infrastructure/waves/` |
| Tests | `tests/unit/dpm/api/test_waves_api.py`, `tests/unit/dpm/waves/test_wave_domain.py`, `tests/unit/dpm/waves/test_source_readiness.py` |

### Remaining Work Summary

These items are deliberately not done in RFC-0041 because they require source-owned data products,
downstream product-surface implementation, or owning-service materialization outside
`lotus-manage`.

| ID | Work item | Owner | Current status | Why it was not done in RFC-0041 |
| --- | --- | --- | --- | --- |
| RFC41-WTBD-001 | Automatic PM-book / portfolio-manager cohort discovery | `lotus-core` or future relationship-book authority | Deferred with no support claim | No certified PM-book membership or portfolio-manager book source product was available to `lotus-manage`. Implementing this locally would fabricate source authority. |
| RFC41-WTBD-002 | Automatic CIO model-change affected-mandate discovery | `lotus-core` or CIO model-event authority | Deferred with no support claim | Model targets and mandate bindings exist, but no certified source product returns all portfolios affected by a model-change event with lineage and reconciliation proof. |
| RFC41-WTBD-003 | Tactical house-view, risk-event, and implicit bulk-campaign cohorts | CIO/risk/campaign source owners, with likely `lotus-risk` involvement for risk events | Deferred with no support claim | No governed scenario, risk-event, or campaign cohort authority exists for manage to consume. |
| RFC41-WTBD-004 | Risk and performance aggregate enrichment for waves | `lotus-risk`, `lotus-performance`, consumed by `lotus-manage` and later `lotus-gateway` | Deferred unless owning-service contracts are consumed | RFC-0041 aggregate impact must not be calculated from manage-local approximations. Risk and performance figures need owning-service certified contracts. |
| RFC41-WTBD-005 | Gateway wave composition | `lotus-gateway` | Downstream RFC direction created; implementation not supported yet | Manage contracts had to stabilize first. Gateway must compose manage truth without becoming wave authority or reconstructing state. |
| RFC41-WTBD-006 | Workbench wave command center | `lotus-workbench` | Downstream RFC direction created; implementation not supported yet | Workbench must consume Gateway/BFF routes only and needs Gateway implementation plus browser, accessibility, visual, and canonical runtime proof. |
| RFC41-WTBD-007 | Full front-office command-center product support | `lotus-gateway`, `lotus-workbench`, with manage as backend authority | Proposed, not supported | The full product outcome requires both downstream implementations and canonical front-office evidence, not manage backend proof alone. |
| RFC41-WTBD-008 | Report materialization from wave/proof-pack evidence | `lotus-report`, `lotus-render`, `lotus-archive` | Deferred to owning services | Manage exposes proof-pack and handoff posture. It does not generate governed report output or archive records. |
| RFC41-WTBD-009 | AI PM memo generation from wave evidence | `lotus-ai`, governed by RFC-0043 direction | Deferred to owning service | Manage can expose bounded evidence posture but must not generate AI narrative or prompts locally. |
| RFC41-WTBD-010 | External execution integration | Future execution/OMS owner or governed operations integration | Out of RFC-0041 scope | RFC-0041 intentionally stops at internal operations handoff evidence and preserves `external_execution_claimed=false`. |

### Detailed Follow-Up Items

#### RFC41-WTBD-001 - Automatic PM-Book / Portfolio-Manager Cohort Discovery

Target business outcome:

Portfolio managers can start a rebalance wave for their governed book without manually supplying
every portfolio id, and the resulting cohort is source-backed, permission-aware, fresh, and
reconcilable.

Why it cannot be done now:

`lotus-manage` has no certified PM-book or portfolio-manager cohort source. RFC-0041 found core
portfolio and mandate source products, but not an authority that can answer "which portfolios are
in this PM's book for this as-of date and caller context?" A manage-local query would create a
shadow book model and break domain ownership.

Dependencies before implementation:

1. owning repository declares the PM-book or relationship-book authority,
2. certified API exposes book identity, portfolio membership, as-of date, freshness, permissions,
   source refs, and lineage,
3. OpenAPI examples and field descriptions are complete,
4. manage consumer declaration is added if the source is a governed domain data product,
5. mixed live proof covers included, excluded, stale, permission-denied, and empty-book cases.

Expected implementation wave:

Implement after the source product is live-proven. Add a manage slice that enables
`PM_BOOK_REVIEW` from a certified source ref, keeps explicit supplied manifests supported, and
preserves `NOT_SUPPORTED_TRIGGER` for missing or uncertified discovery.

Promotion proof:

1. source-owner PR and live proof,
2. manage integration tests for discovery success and degraded/blocked states,
3. OpenAPI certification for the promoted trigger path,
4. live evidence with at least one mixed-readiness book,
5. README/wiki/supported-features update stating exactly which PM-book path is supported.

#### RFC41-WTBD-002 - Automatic CIO Model-Change Affected-Mandate Discovery

Target business outcome:

A CIO model change can produce a governed wave over the affected mandates without manually
supplying every portfolio id, with clear explanation of why each mandate is in scope.

Why it cannot be done now:

RFC-0041 could consume model targets and mandate bindings, but no source authority exists for the
model-change event itself and its affected portfolio or mandate cohort. Inferring the cohort inside
manage from model id alone would be brittle and would hide missing event lineage.

Dependencies before implementation:

1. source-owned model-change event product with event id, model id/version, approval state, effective
   date, affected mandate or portfolio ids, exclusion rationale, freshness, and lineage,
2. certified affected-cohort API with explicit reconciliation semantics,
3. clear ownership for CIO approval metadata and model-version lifecycle,
4. manage consumer contract and permission checks,
5. live proof reconciling source cohort to manage wave items.

Expected implementation wave:

Implement after the model-change source product exists. Promote `CIO_MODEL_CHANGE` only for
certified event-backed cohorts; keep supplied affected-portfolio manifests as the first-wave
fallback posture.

Promotion proof:

1. source-owner tests and OpenAPI certification,
2. manage tests for source-ready, degraded, blocked, stale, and partial-cohort cases,
3. proof-pack linkage showing model-change event lineage,
4. live evidence proving automatic cohort discovery and reconciliation,
5. supported-features update that distinguishes automatic event-backed cohorts from supplied
   manifests.

#### RFC41-WTBD-003 - Tactical House-View, Risk-Event, And Implicit Campaign Cohorts

Target business outcome:

CIO, risk, or operations teams can launch governed waves for tactical house views, market/risk
events, or bulk review campaigns from source-owned campaign definitions rather than raw portfolio
lists.

Why it cannot be done now:

There is no certified source authority for tactical house-view cohorts, risk-event impact cohorts,
or implicit bulk-campaign membership. RFC-0041 therefore correctly keeps these trigger types
unpromoted or limited to explicit supplied manifests.

Dependencies before implementation:

1. owner for each cohort family is assigned,
2. cohort source APIs expose membership, rationale, source refs, freshness, permissions, and
   exclusion rules,
3. risk-event cohorts come from `lotus-risk` or a certified risk-event product,
4. campaign cohorts define reviewer, approval, and expiry governance,
5. manage validates supportability without calculating source membership locally.

Expected implementation wave:

Treat each trigger family as a separate RFC or explicit slice after owner contracts exist. Do not
bundle them into manage until source behavior and business controls are stable.

Promotion proof:

1. owning-service API certification,
2. manage trigger-specific integration tests,
3. degraded-state and permission tests,
4. live evidence with at least one partial/degraded cohort,
5. wiki and supported-feature language that names the supported trigger family precisely.

#### RFC41-WTBD-004 - Risk And Performance Aggregate Enrichment

Target business outcome:

Wave previews and simulations can show governed risk and performance impact using authoritative
analytics rather than manage-local estimates.

Why it cannot be done now:

Risk and performance impact are not manage-owned calculations. RFC-0041 can preserve posture and
supportability, but it must not fabricate risk or performance figures from construction inputs.

Dependencies before implementation:

1. `lotus-risk` exposes certified wave-compatible risk impact contracts,
2. `lotus-performance` exposes certified wave-compatible performance impact contracts,
3. request identity, as-of date, benchmark, and method semantics align with manage wave items,
4. unavailable, degraded, stale, and partial analytics states are contractually represented,
5. Gateway composition preserves owning-service supportability rather than flattening it.

Expected implementation wave:

Implement after risk/performance contracts exist. The manage slice should consume owning-service
results, attach lineage/supportability to wave aggregates, and keep unsupported states explicit.

Promotion proof:

1. risk/performance owner tests and OpenAPI certification,
2. manage integration tests covering successful and degraded analytics,
3. aggregate reconciliation evidence,
4. live proof with mixed analytics availability,
5. endpoint certification and supported-feature updates.

#### RFC41-WTBD-005 - Gateway Wave Composition

Target business outcome:

Workbench receives a stable command-center wave contract from Gateway, while manage remains the
wave authority.

Why it cannot be done now:

RFC-0041's manage contracts had to be implemented and proven before Gateway could safely build a
composition layer. Slice 9 created/tightened downstream RFC direction but did not implement
Gateway behavior.

Dependencies before implementation:

1. Gateway RFC-0098 wave addendum is used as the execution guide,
2. typed manage client covers preview, create, source-check, simulate, select, approve, stage,
   handoff, cancel, detail, item, proof-pack, and supportability routes,
3. Gateway preserves manage `wave_id`, state, item states, reason codes, aggregate metrics,
   proof-pack refs, and supportability,
4. risk/performance/report/archive/AI posture is composed only from owning services,
5. no aliases or duplicated state-machine logic are introduced.

Expected implementation wave:

Implement in `lotus-gateway` before Workbench wave-command-center implementation.

Promotion proof:

1. Gateway unit and contract tests,
2. no-reconstruction tests proving Gateway does not recompute manage truth,
3. OpenAPI certification and examples,
4. live Gateway proof against manage,
5. Gateway wiki, README, supported-features, and endpoint-certification updates.

#### RFC41-WTBD-006 - Workbench Wave Command Center

Target business outcome:

Portfolio managers and operations users can review, simulate, approve, stage, hand off, and monitor
rebalance waves through a governed Workbench command-center experience.

Why it cannot be done now:

Workbench must consume Gateway/BFF contracts only. Implementing the UI before Gateway composition
would either force direct manage calls or speculative UI contracts. That would violate Lotus
front-office ownership rules.

Dependencies before implementation:

1. Gateway wave composition is implemented and certified,
2. Workbench BFF/client modules consume Gateway only,
3. UX covers wave list, wave detail, item matrix, mixed readiness, action eligibility, proof-pack
   posture, report/AI posture, supportability, and operator diagnostics,
4. UI states are backed by backend truth and do not invent calculations,
5. accessibility, visual, browser, and canonical front-office validation are in place.

Expected implementation wave:

Implement in `lotus-workbench` after Gateway wave composition passes. Use the canonical
front-office runtime and `PB_SG_GLOBAL_BAL_001` evidence path when demo-ready proof is required.

Promotion proof:

1. Workbench unit/component tests and BFF contract tests,
2. browser validation across core wave workflows,
3. accessibility and responsive layout proof,
4. canonical front-office validation evidence,
5. screenshots only after API/calculation/panel validation passes,
6. Workbench README/wiki/supported-features updates.

#### RFC41-WTBD-007 - Full Front-Office Command-Center Product Support

Target business outcome:

The RFC-0041 wave capability is visible as an end-to-end front-office product workflow, not only as
manage backend APIs.

Why it cannot be done now:

Manage backend completion is necessary but not sufficient. Full product support requires Gateway
composition, Workbench implementation, canonical runtime validation, and product documentation
across the downstream apps.

Dependencies before implementation:

1. RFC41-WTBD-005 complete,
2. RFC41-WTBD-006 complete,
3. canonical front-office QA passes with populated panels,
4. supported-feature ledgers in all participating apps are aligned,
5. wiki material is suitable for developers, operations, business users, sales/pre-sales, and demos.

Expected implementation wave:

Close only after Gateway and Workbench PRs merge and publish wiki updates. Treat this as a final
cross-app proof and documentation slice, not as a manage-only change.

Promotion proof:

1. canonical front-office evidence pack,
2. API, BFF, and UI tests green,
3. demo screenshots clearly tied to validated backend evidence,
4. cross-repo supported-feature entries aligned,
5. no unresolved blocking downstream issue.

#### RFC41-WTBD-008 - Report Materialization From Wave / Proof-Pack Evidence

Target business outcome:

Wave and proof-pack evidence can be materialized into governed reports and archived artifacts.

Why it cannot be done now:

`lotus-manage` owns wave state and proof-pack linkage, not report rendering or archive lifecycle.
RFC-0040 and RFC-0041 provide report-input posture, but generated output belongs to
`lotus-report`, `lotus-render`, and `lotus-archive`.

Dependencies before implementation:

1. report service contract for consuming wave/proof-pack input,
2. render/archive lifecycle contracts for generated artifacts,
3. retention, legal hold, access audit, and redaction rules,
4. Gateway/Workbench posture for report availability,
5. live proof that generated artifacts reconcile to manage evidence.

Expected implementation wave:

Implement through a reporting RFC after report service ownership and document output scope are
clear.

Promotion proof:

1. report/render/archive tests,
2. deterministic artifact evidence,
3. archive retrieval and retention proof,
4. Gateway/Workbench posture tests if surfaced,
5. supported-feature updates in owning apps.

#### RFC41-WTBD-009 - AI PM Memo Generation From Wave Evidence

Target business outcome:

PMs can request governed AI assistance over wave/proof-pack evidence without exposing forbidden
fields or allowing unsupported action recommendations.

Why it cannot be done now:

AI narrative generation belongs to `lotus-ai`, not manage. RFC-0040 and RFC-0041 provide bounded
evidence posture, but manage must not create AI prompts, memos, or recommendations locally.

Dependencies before implementation:

1. RFC-0043 or `lotus-ai` workflow-pack contract defines the memo workflow,
2. forbidden fields and forbidden actions are enforced,
3. provenance, model/prompt identity, input evidence hashes, and fallback states are captured,
4. Gateway/Workbench UI exposes AI posture without bypassing AI service controls,
5. AI unavailable and guardrail-blocked states are tested.

Expected implementation wave:

Implement in `lotus-ai` and consume through Gateway/Workbench after the AI contract is stable.

Promotion proof:

1. AI guardrail and provenance tests,
2. prompt/input-output evidence with sensitive-field protections,
3. unavailable and blocked-state proof,
4. Gateway/Workbench integration tests if surfaced,
5. supported-feature entries that do not imply autonomous execution authority.

#### RFC41-WTBD-010 - External Execution Integration

Target business outcome:

Approved and staged waves can hand off to a governed execution/OMS integration with auditability,
permissions, acknowledgements, and reconciliation.

Why it cannot be done now:

RFC-0041 intentionally ends at internal operations handoff evidence. No external execution owner or
OMS contract is established, and claiming execution would overstate manage's current business
capability.

Dependencies before implementation:

1. execution/OMS owner and contract,
2. order-generation, acknowledgement, rejection, cancellation, and reconciliation semantics,
3. maker-checker and entitlement controls,
4. failure/retry and compensation model,
5. post-trade feedback handoff into RFC-0042 scope where appropriate.

Expected implementation wave:

Do not start until the execution owner, control model, and post-trade feedback boundary are clear.
This may belong after RFC-0042 depending on whether outcome feedback requires execution status as a
source.

Promotion proof:

1. execution-owner API certification,
2. manage handoff integration tests,
3. failure and reconciliation proof,
4. operational runbook and supportability evidence,
5. explicit supported-feature promotion that names the execution boundary.

### Suggested Sequencing

Recommended order:

1. implement Gateway wave composition,
2. implement Workbench wave command center,
3. prove full front-office command-center product support,
4. implement source-owned PM-book and CIO model-change cohort products,
5. promote manage automatic discovery triggers from certified source products,
6. add risk/performance aggregate enrichment from owning analytics services,
7. implement report materialization and AI memo generation in their owning apps,
8. evaluate external execution only after the execution owner and RFC-0042 post-trade feedback
   boundary are clear.

Rationale:

Gateway and Workbench can realize the already-supported explicit-list manage backend without
waiting for automatic cohort discovery. Source-owned discovery should then improve trigger quality
without blocking the product surface. Report, AI, and execution materialization should follow the
owning-service contracts because they introduce additional control, audit, and supportability
requirements.

### RFC-0041 Promotion Checklist For Any Future Item

Before any item above moves from this ledger into a supported-feature claim:

1. owning repository and API/source contract are explicit,
2. implementation is complete in the owning app,
3. `lotus-manage` consumes only certified source truth where it is not the owner,
4. Gateway and Workbench consume through the governed product path,
5. degraded, stale, missing, permission-denied, partial, and unavailable states are tested where
   applicable,
6. OpenAPI/Swagger quality is certified for every API added or changed,
7. live or canonical front-office evidence is captured and critically reviewed,
8. README, RFC, source-map, wiki, supported-features, and repository context are aligned,
9. PR checks are green, PRs are merged, wiki is published, and branches are cleaned.

## RFC-0042 - Post-Trade Outcome Feedback Loop

Current closure status:

RFC-0042 is `DONE - MANAGE BACKEND COMPLETE; FIRST-WAVE PRODUCT REALIZATION COMPLETE; SOURCE-OWNER
ENRICHMENT REMAINS`. `lotus-manage` owns the implementation-backed outcome-review authority:
source-backed preview/create/retrieve/search, immutable persistence and append-only events,
source-refresh eventing, supportability diagnostics, deterministic report-input and AI-evidence
input handoff contracts, certified OpenAPI, and live manage proof under
`output/rfc0042-outcome-proof/20260505-024352/` plus hardening proof under
`output/rfc0042-outcome-proof/20260505-025613/`. Gateway, Workbench, report/render/archive, and
AI first-wave realization is now implemented and merged in the owning repositories. Remaining
ledger work is limited to source-owner methodology enrichment, external execution/OMS ownership,
and any future PM quality-scoring RFC.

Closure evidence:

| Evidence | Location |
| --- | --- |
| Governing RFC | `docs/rfcs/RFC-0042-post-trade-outcome-feedback-loop.md` |
| Source map | `docs/rfcs/RFC-0042-source-map-and-gap-analysis.md` |
| Slice evidence | `docs/rfcs/RFC-0042-*-slice*.md` |
| Certified API family | `wiki/Endpoint-Certification.md` post-trade outcome review API foundation |
| Supported feature claim | `wiki/Supported-Features.md` post-trade outcome feedback row |
| Live proof | `output/rfc0042-outcome-proof/20260505-024352/critical-review.json` |
| Hardening proof | `output/rfc0042-outcome-proof/20260505-025613/critical-review.json` |
| Post-merge audit rerun | `output/rfc0042-outcome-proof/20260505-040212/critical-review.json` |
| WTBD audit outcome proof | `output/rfc0042-wtbd-audit-outcome-proof/20260505-211611/critical-review.json` |
| WTBD canonical Workbench proof | `lotus-workbench/output/playwright/rfc42-wtbd-audit-20260506-fixed/live-validation-summary.json` |

Audit refresh on 2026-05-05:

1. `lotus-manage` mainline truth was reconciled with `git fetch origin --prune` and
   `git branch -r --no-merged origin/main`; no unmerged remote branch carried RFC-0042 durable
   truth.
2. `lotus-gateway` commit `38d46f9` and `lotus-workbench` commit `3b5182f`, referenced by Slice
   10, are present on `origin/main` in their owning repositories; the realization RFC addenda are
   not stranded on side branches.
3. The RFC-0042 manage implementation evidence remains consistent with the support claim:
   backend authority is implemented and proven; downstream product, report, AI narrative,
   execution/OMS, PM scoring, and richer source-owner methodology work remains unpromoted.
4. RFC42-WTBD-002 and RFC42-WTBD-003 were completed after the audit through the downstream owning
   repositories: `lotus-workbench` PR #146, `lotus-gateway` PR #187, `lotus-platform` PR #300, and
   `lotus-core` PR #336 are merged, Workbench wiki publication completed, and canonical
   front-office evidence is captured under
   `lotus-workbench/output/playwright/live-canonical-rfc42-outcome-review/`.

WTBD audit refresh on 2026-05-06:

1. Rebuilt stale local `lotus-gateway`, `lotus-manage`, and `lotus-workbench` Docker images before
   accepting live evidence; stale images initially hid merged route/UI truth and caused false live
   failures.
2. Generated a durable live manage-backed outcome review with
   `python scripts/generate_rfc0042_outcome_evidence.py --base-url http://127.0.0.1:8001
   --output-root C:\Users\Sandeep\projects\lotus-manage\output\rfc0042-wtbd-audit-outcome-proof`.
   The accepted critical review is
   `output/rfc0042-wtbd-audit-outcome-proof/20260505-211611/critical-review.json` and it passed
   review creation, idempotency replay/conflict, source lineage, supportability, report input, AI
   guardrails, degraded-source posture, refresh eventing, OpenAPI certification, and variance
   worked-example checks.
3. Fixed the `lotus-workbench` outcome-review view model after screenshot review found manage-owned
   `source_system`, `source_id`, and `content_hash` lineage rendered as `N/A`. The corrected panel
   now shows `lotus-manage` and `lotus-core` source refs and hashes from the Gateway contract.
4. Fixed the manage RFC-0042 evidence generator so relative `--output-root` paths resolve under the
   repository root instead of failing before manifest publication.
5. Reran canonical front-office validation after the fixes. Accepted evidence is
   `lotus-workbench/output/playwright/rfc42-wtbd-audit-20260506-fixed/live-validation-summary.json`,
   `SHOT-INDEX.md`, and `dpm-outcome-review-live.png`; the DPM outcome-review panel is
   `demo_ready`, contains one manage-backed review, one dimension row, and two source-lineage rows.
6. Residual non-RFC42 findings remain bounded: the Workbench page still includes separate
   non-outcome sections showing unavailable reporting/analytics placeholders and existing build
   warnings for CSS autoprefixer/dependency audit posture. These are not outcome-review contract
   failures and should be handled by their owning Workbench/platform hygiene items rather than
   weakening RFC42-WTBD closure.

### Remaining Work Summary

These items are outside the RFC-0042 manage closure because outcome review backend authority is
necessary but not sufficient for the full front-office learning loop. Source calculations belong
to source-owning services, product composition belongs to Gateway and Workbench, generated
artifacts belong to report/render/archive services, and AI narrative execution belongs to
`lotus-ai`.

| ID | Work item | Owner | Current status | Why it was not done in RFC-0042 |
| --- | --- | --- | --- | --- |
| RFC42-WTBD-001 | Gateway outcome-review composition and BFF contract | `lotus-gateway` | Implemented, merged, CI-proven, and wiki-published through `lotus-gateway` PR #186; live canonical product proof remains part of RFC42-WTBD-003 | Manage APIs were stabilized first. Gateway now composes the BFF route family without recomputing outcome truth. Product support still requires Workbench implementation and canonical front-office proof. |
| RFC42-WTBD-002 | Workbench post-trade outcome review UX | `lotus-workbench` through Gateway/BFF | Implemented, merged, CI-proven, live-proven, and wiki-published through `lotus-workbench` PR #146 | Workbench now consumes Gateway/BFF outcome-review contracts only, presents manage-owned outcome truth without recomputation, and is proven by canonical Workbench validation. |
| RFC42-WTBD-003 | Full front-office post-trade outcome feedback product support | `lotus-gateway`, `lotus-workbench`, `lotus-manage` | Implemented and canonically proven for current Gateway/Workbench outcome-review product scope through `lotus-gateway` PR #186, `lotus-gateway` PR #187, `lotus-workbench` PR #146, `lotus-platform` PR #300, and `lotus-core` PR #336 | The full first-wave product path is now implementation-backed: manage owns authority, Gateway composes it, Workbench renders it, panel governance certifies it, and live canonical evidence proves it. Reporting, AI, OMS, source-owner methodology, and PM-scoring scope remain separate ledger items. |
| RFC42-WTBD-004 | Rendered outcome reports and archive lifecycle | `lotus-report`, `lotus-render`, `lotus-archive`, `lotus-gateway`, `lotus-workbench` | Implemented, merged, CI-proven, and wiki-published through `lotus-render` PR #9, `lotus-archive` PR #21, `lotus-report` PR #88, `lotus-gateway` PR #188, and `lotus-workbench` PR #147 | Manage emits bounded report input only; downstream services now consume it to create deterministic outcome-review report artifacts, preserve archive posture, expose Gateway submission, and add the Workbench report request action without recomputing outcome truth. |
| RFC42-WTBD-005 | Governed AI narrative/copilot over outcome evidence | `lotus-ai`, Gateway, Workbench, with manage as evidence authority | Implemented, merged, CI-proven, and wiki-published through `lotus-ai` PR #59/#60, `lotus-gateway` PR #189, and `lotus-workbench` PR #148 | Manage emits AI evidence input only; `lotus-ai` now owns guarded workflow-pack narrative execution, Gateway composes the evidence/narrative BFF, and Workbench exposes only a governed request action without prompt construction or autonomous decisioning. |
| RFC42-WTBD-006 | Source-owned realized risk/performance/tax/FX/cash outcome methodologies | `lotus-risk`, `lotus-performance`, `lotus-core`, future source owners | In progress source-family by source-family | RiskMetricsReport, drawdown response max drawdown, concentration response selected measures, rolling metric summaries, historical attribution selected measures, performance workspace-summary TWR, active return, MWR output, contribution selected measures, attribution selected measures, core HoldingsAsOf cash totals, core TransactionLedgerWindow explicit transaction-row measures, and core PortfolioCashflowProjection total net cashflow now have manage adapters; aggregated risk/performance, tax, FX, cash movements beyond source-emitted totals, liquidity ladders, and execution methodologies stay source-owner follow-on work. |
| RFC42-WTBD-007 | External execution/OMS integration and acknowledgements | Execution/OMS owner, `lotus-manage` consumer | Ownership not established | RFC-0042 can compare expected and realized evidence, but OMS integration needs a separate owner, controls, acknowledgements, and reconciliation contract. |
| RFC42-WTBD-008 | PM quality scoring or behavioral analytics | Business owner, methodology owner, `lotus-ai` only if approved | Not supported | RFC-0042 intentionally avoids scoring PMs. Any future scoring requires business approval, auditable methodology, bias controls, and governance. |

### Detailed Follow-Up Items

#### RFC42-WTBD-001 - Gateway Outcome-Review Composition And BFF Contract

Target business outcome:

Gateway exposes a product-facing outcome-review contract for command-center and portfolio workspace
consumers while preserving manage-owned source lineage, state, reason codes, supportability,
report-input refs, and AI-evidence refs.

Current implementation-backed result:

`lotus-gateway` branch `feat/rfc42-outcome-review-gateway` implements the first RFC-0042
realization slice. Gateway now has typed manage client methods, DPM command-center outcome-review
BFF contracts, a service layer, and route handlers for preview, create, search, detail,
source-refresh, supportability, report-input, AI-evidence input, run lookup, and wave lookup.
Gateway preserves manage-owned payloads and supportability and does not recompute expected values,
realized values, variance, tolerance, hashes, lineage, freshness, or review state. Gateway PR #186
merged to `main` as `a71275d` after local `make ci` and GitHub PR Merge Gate passed. Gateway wiki
publication completed with zero drift. End-to-end product proof remains under RFC42-WTBD-003
because it requires Workbench UX implementation and canonical front-office validation.

Why it was not done in RFC-0042:

RFC-0042 intentionally stabilized the manage API surface first. Gateway composition had to consume
the certified surface after manage closure and remain in the Gateway owning repository.

Dependencies before implementation:

1. typed Gateway manage client for all RFC-0042 outcome-review endpoints,
2. Gateway route design aligned with RFC-0098,
3. no direct Workbench-to-manage calls,
4. no recomputation of outcome dimensions in Gateway,
5. unavailable/degraded source posture preserved for UI consumers.

Expected implementation wave:

This item is complete enough to unblock Workbench outcome-review UX work. The next implementation
wave is RFC42-WTBD-002 in `lotus-workbench`, followed by RFC42-WTBD-003 for full canonical
front-office product proof.

Promotion proof:

1. Gateway unit and contract tests: focused tests added in
   `tests/unit/test_dpm_command_center_service.py`,
   `tests/unit/test_upstream_clients.py`,
   `tests/integration/test_dpm_command_center_router.py`, and
   `tests/contract/test_dpm_command_center_contract.py`,
2. Gateway OpenAPI/Swagger certification: route family registered with What/When/How descriptions
   and response schema descriptions; local `make check` and `make ci` passed,
3. live canonical front-office proof remains required before full product-support promotion under
   RFC42-WTBD-003,
4. degraded, blocked, unsupported, unavailable, and upstream-error coverage has been added at the
   Gateway service/router layer; live degraded proof remains required,
5. Gateway README/wiki/context updates are merged and wiki source was published.

#### RFC42-WTBD-002 - Workbench Post-Trade Outcome Review UX

Target business outcome:

PMs, CIO, compliance, and operations can review expected-versus-realized outcomes in Workbench with
clear state, variance, source lineage, supportability, report/AI handoff posture, and next-action
guidance.

Current implementation-backed result:

`lotus-workbench` PR #146 implements the RFC-0042 post-trade outcome-review UX on
`/workbench/{portfolioId}`. The panel consumes Gateway/BFF contracts only through the shared
Workbench API layer, normalizes manage-owned outcome-review payloads in a deterministic view-model,
and renders review state, expected-versus-realized dimensions, variance/tolerance posture, source
lineage, hashes, supportability, report-input refs, AI-evidence refs, and next-action posture
without client-side outcome calculation. Server-side Workbench Gateway reads now share governed
caller-context propagation with the BFF route. The canonical live validator certifies
`dpm.outcome_review` as a governed panel and captures machine-readable API/panel proof plus the
`dpm-outcome-review-live.png` screenshot.

Cross-repo hardening completed during live proof:

1. `lotus-gateway` PR #187 fixed platform-capabilities live fanout and the manage capability
   contract route so Workbench no longer sees false platform degradation.
2. `lotus-platform` PR #300 registered `dpm.outcome_review` in the governed Workbench panel
   registry and analytics UI observability readiness contracts.
3. `lotus-core` PR #336 passed governed caller-context headers during canonical front-office seed
   validation and added unit coverage for that contract.

Why it was not done in RFC-0042:

Workbench had to wait until manage and Gateway contracts stabilized. Implementing earlier would
have forced direct manage calls, duplicated outcome logic, or speculative UI behavior.

Dependencies before implementation:

1. RFC42-WTBD-001 complete,
2. Workbench must consume Gateway/BFF only,
3. Workbench BFF/client modules consume Gateway only,
4. outcome-review list and detail information architecture,
5. UI states for ready, degraded, blocked, unsupported, stale, malformed, conflicting, and empty,
6. canonical browser validation with populated and degraded evidence cases.

Expected implementation wave:

Complete. This item merged through `lotus-workbench` PR #146 after Gateway, platform governance,
and core caller-context dependencies were raised, fixed, green, and merged.

Promotion proof:

1. Workbench unit/component/BFF/browser tests:
   `tests/unit/outcome-review-view-model.test.ts`, `tests/unit/outcome-review-panel.test.tsx`,
   `tests/unit/workbench-api.test.ts`, `tests/unit/live-validation-probes.test.ts`,
   `tests/unit/live-validation-browser-workflows.test.ts`, and
   `tests/integration/workbench-page.test.tsx`,
2. local gates: `npm run typecheck`, `npm run lint`, `npm run build`, `make check`, and
   `git diff --check`,
3. GitHub checks: `lotus-workbench` PR #146 Feature Lane and PR Merge Gate green,
4. canonical proof:
   `lotus-workbench/output/playwright/live-canonical-rfc42-outcome-review/live-validation-summary.json`
   shows `DPM outcome reviews` API status 200 and `dpm.outcome_review` panel state `ready`,
5. screenshot index:
   `lotus-workbench/output/playwright/live-canonical-rfc42-outcome-review/SHOT-INDEX.md` lists
   `dpm-outcome-review-live.png` as `demo_ready`,
6. Workbench README/wiki/context updates merged, and Workbench wiki source was published with
   commit `650f698` to `lotus-workbench.wiki`.

#### RFC42-WTBD-003 - Full Front-Office Post-Trade Outcome Feedback Product Support

Target business outcome:

The RFC-0042 capability becomes an end-to-end product workflow: manage creates durable outcome
reviews, Gateway composes them, Workbench presents them, and documentation supports business,
operations, sales/pre-sales, client demos, and engineering.

Current implementation-backed result:

The first-wave front-office product path is complete for RFC-0042 outcome review. Manage remains
the backend authority, Gateway composes the outcome-review contract, Workbench presents the
post-trade outcome-review panel through Gateway/BFF only, platform governance registers the panel,
and canonical Workbench validation proves the populated panel on `PB_SG_GLOBAL_BAL_001` with
machine-readable API, panel, and screenshot evidence.

Why it was not done in RFC-0042:

The original RFC-0042 closure was intentionally limited to manage backend authority. Gateway,
Workbench, platform panel governance, and core seed-validation hardening had to be implemented in
their owning repositories after manage contracts and live proof stabilized.

Dependencies before implementation:

1. RFC42-WTBD-001 complete,
2. RFC42-WTBD-002 complete,
3. canonical front-office QA passes with populated outcome-review panels,
4. supported-feature ledgers align across participating apps,
5. unresolved downstream issues are closed or explicitly bounded.

Expected implementation wave:

Complete for current Gateway/Workbench product realization. Remaining reporting, AI, OMS,
source-owner methodology, and PM-scoring work stays in RFC42-WTBD-004 through RFC42-WTBD-008.

Promotion proof:

1. manage backend authority: RFC-0042 proof under
   `lotus-manage/output/rfc0042-outcome-proof/20260505-024352/`,
   `20260505-025613/`, and post-merge audit `20260505-040212/`,
2. Gateway composition: `lotus-gateway` PR #186 merged as `a71275d`; Gateway wiki publication was
   completed with zero drift,
3. Gateway live-proof hardening: `lotus-gateway` PR #187 merged and all GitHub Feature Lane /
   PR Merge Gate checks passed,
4. platform panel governance: `lotus-platform` PR #300 merged and all platform contract/vocabulary
   checks passed,
5. core caller-context validation: `lotus-core` PR #336 merged after local targeted proof,
   `make warning-gate`, and full GitHub Feature Lane / PR Merge Gate including Docker, E2E,
   latency, fast load, and coverage gates,
6. Workbench UX: `lotus-workbench` PR #146 merged after Feature Lane and PR Merge Gate passed,
7. canonical evidence:
   `lotus-workbench/output/playwright/live-canonical-rfc42-outcome-review/live-validation-summary.json`,
   `SHOT-INDEX.md`, and `dpm-outcome-review-live.png`,
8. Workbench wiki was published from repo source after merge.

#### RFC42-WTBD-004 - Rendered Outcome Reports And Archive Lifecycle

Target business outcome:

Outcome reviews can be turned into governed report artifacts with deterministic rendering,
retention, archive retrieval, legal hold posture, and access audit.

Current implementation-backed result:

Complete for the first-wave generated outcome-review report artifact path. `lotus-report` now
accepts manage-owned `DpmOutcomeReportInput` through `POST /reports/outcome-reviews`, persists the
handoff as the immutable report snapshot, records lineage back to `lotus-manage`, builds the
`dpm_outcome_report_input.v1` render package, submits the `outcome-review` template to
`lotus-render` when PDF is requested, and hands rendered artifacts to the existing
`lotus-archive` generated-document lifecycle. `lotus-render` now owns the deterministic
`outcome-review/v1` Typst template and registry manifest. `lotus-archive` documentation confirms
that outcome-review generated documents inherit the existing archive, retrieval, retention,
legal-hold, access-audit, purge, and lifecycle posture when supplied by `lotus-report`.

Gateway and Workbench realization is complete for report-request submission: `lotus-gateway`
exposes `POST /api/v1/reports/outcome-reviews` as a pass-through Experience API route to
`lotus-report`, preserving caller context and idempotency without recomputing outcome truth.
`lotus-workbench` adds a governed outcome-review report request action in the DPM outcome panel,
calling Gateway/BFF only and recording the `dpm.outcome-review.report-job.submit` observability
surface.

Why it was not done in the original RFC-0042 manage closure:

`lotus-manage` correctly emits bounded `DpmOutcomeReportInput`; report generation, rendering,
archive persistence, retrieval, and retention lifecycle are owned by downstream reporting services.
The work had to land in the owning repositories after manage report-input contracts stabilized.

Dependencies before implementation:

1. `lotus-report` contract for consuming outcome-review report input - complete in PR #88,
2. `lotus-render` deterministic rendering contract - complete in PR #9,
3. `lotus-archive` retention, legal hold, access-audit, and retrieval posture - documented and
   merged in PR #21,
4. Gateway/Workbench posture for report availability and submission - complete in Gateway PR #188
   and Workbench PR #147,
5. reconciliation from generated artifact back to manage evidence hashes - complete through
   `lotus-report` snapshot lineage, render package hashes, and archive metadata handoff.

Expected implementation wave:

Complete for first-wave outcome-review generated reports. A future enhancement may add direct
Workbench retrieval/download affordances once the broader generated-document discovery UX is
standardized, but report request, render, archive handoff, and lifecycle posture are now
implementation-backed and must not remain listed as deferred.

Promotion proof:

1. `lotus-render` PR #9 merged after Feature Lane and PR Merge Gate passed, including lint,
   unit/integration/e2e tests, coverage, Docker build validation, and template-registry gate;
   wiki published from repo source as `lotus-render.wiki` commit `e09f36e`,
2. `lotus-archive` PR #21 merged after Feature Lane and PR Merge Gate passed, including lint,
   unit/integration/e2e tests, coverage, Docker build validation, and documentation posture tests;
   wiki published from repo source as `lotus-archive.wiki` commit `47b59e0`,
3. `lotus-report` PR #88 merged after Feature Lane and PR Merge Gate passed, including lint,
   unit/integration/e2e tests, 99 percent coverage gate, Docker build validation, OpenAPI wording
   guardrails, immutable snapshot capture, report render package tests, idempotency guardrails,
   degraded validation coverage, and supported-features/wiki updates; wiki published from repo
   source as `lotus-report.wiki` commit `aa6d487`,
4. `lotus-gateway` PR #188 merged after Feature Lane and PR Merge Gate passed, including lint,
   typecheck, unit/contract/integration tests, coverage, Docker parity, Docker build validation,
   caller-context/idempotency forwarding tests, OpenAPI route registration, README, and wiki
   updates; wiki published from repo source as `lotus-gateway.wiki` commit `483f627`,
5. `lotus-workbench` PR #147 merged after Feature Lane and PR Merge Gate passed, including lint,
   typecheck, focused unit/component tests, coverage/build, Docker parity, Playwright smoke,
   Docker build validation, BFF/API tests, component action tests, observability registry tests,
   and wiki updates; wiki published from repo source as `lotus-workbench.wiki` commit `6db1daa`.

#### RFC42-WTBD-005 - Governed AI Narrative/Copilot Over Outcome Evidence

Target business outcome:

PMs and CIO users can request governed AI support over outcome-review evidence without inventing
missing facts, scoring PMs, contacting clients, approving trades, or bypassing controls.

Current implementation-backed result:

Complete for first-wave governed outcome-review narrative support. `lotus-ai` now owns
`outcome_review_narrative.pack@v1`, including supported caller governance, narrative guardrails,
stub-provider execution, workflow-pack registry exposure, queue policy, and supportability
metadata. `lotus-gateway` composes the product route
`POST /api/v1/dpm/command-center/outcome-reviews/{outcome_review_id}/ai-narrative` by fetching
manage-owned `DpmOutcomeAiEvidenceInput`, forwarding a bounded request to `lotus-ai`, preserving
manage as evidence/workflow authority, and returning explicit manage/AI upstream posture.
`lotus-workbench` exposes the governed action on the RFC-0042 outcome-review panel through the
Gateway BFF only, records bounded observability for `dpm.outcome-review.ai-narrative`, and displays
workflow-pack run posture without constructing prompts, scoring PMs, approving trades, or calling
raw manage/AI services.

Why it was not done in the original RFC-0042 manage closure:

`lotus-manage` correctly emitted bounded AI evidence input but was not the AI workflow owner.
Prompt execution, model posture, guardrails, narrative execution, and unavailable/blocked AI states
belong in `lotus-ai`; product composition belongs in Gateway; user realization belongs in
Workbench. The item could only close after all three owning repositories implemented and proved
their contracts.

Dependencies satisfied:

1. `lotus-ai` workflow-pack contract and registry entry for `outcome_review_narrative.pack@v1`,
2. guardrails that block forbidden actions, forbidden fields, unsupported/degraded evidence,
   empty review evidence, and missing required evidence hashes,
3. caller governance for both `lotus-manage` and `lotus-gateway`,
4. Gateway route and service composition that calls manage and AI through typed owning-service
   contracts without recomputing outcome truth,
5. Workbench BFF/API/component realization through Gateway only, with bounded metric labels that
   exclude outcome review ids, workflow-pack run ids, request bodies, response bodies, hashes, and
   lineage references.

Expected implementation wave:

Complete for first-wave governed AI narrative support over RFC-0042 outcome evidence. Future
enhancements, such as non-stub model providers, richer narrative templates, or additional PM/CIO
workflow outputs, must remain in `lotus-ai` and preserve the same evidence, guardrail, provenance,
Gateway-only, and Workbench-no-autonomy boundaries.

Promotion proof:

1. `lotus-ai` PR #59 merged as `6e547866e0e7254a4d03bc8cf94101d70eaef221` after Feature Lane and
   PR Merge Gate passed; post-merge validation
   `python -m pytest tests/unit/test_outcome_review_narrative_guardrails.py tests/unit/test_workflow_pack_execution.py tests/integration/test_workflow_pack_run_api_contract.py -q`
   passed `49` tests; wiki published from repo source as `lotus-ai.wiki` commit `89b873b`,
2. `lotus-ai` PR #60 merged as `d1df451` after Feature Lane and PR Merge Gate passed, adding
   `lotus-gateway` as an explicit supported caller and proving Gateway caller execution through
   targeted integration/registry tests,
3. `lotus-gateway` PR #189 merged as `9d1d04794ea7ee0a733a76e671fd927a3a2d862c` after Feature
   Lane and PR Merge Gate passed, including service/router/contract tests, OpenAPI route
   registration, local `make ci`, and post-merge targeted validation
   `python -m pytest tests/unit/test_dpm_command_center_service.py tests/integration/test_dpm_command_center_router.py tests/contract/test_dpm_command_center_contract.py -q`
   with `17` passing tests; wiki published from repo source as `lotus-gateway.wiki` commit
   `e4dbdd0`,
4. `lotus-workbench` PR #148 merged as `46fe13ad3dd43f3a3150f6c2966c59e88a8a3e95` after Feature
   Lane and PR Merge Gate passed, including lint, typecheck, coverage/build, Playwright smoke,
   Docker build, Docker parity, focused API/component/observability tests, and local
   `make test-coverage` with `695` passing tests and `91.06%` statement coverage; post-merge
   targeted validation
   `npm test -- --run tests/unit/outcome-review-panel.test.tsx tests/unit/workbench-api.test.ts tests/unit/analytics-observability-metrics.test.ts`
   passed `58` tests,
5. `lotus-workbench` wiki was published from repo source as `lotus-workbench.wiki` commit
   `e223851` and `Sync-RepoWikis.ps1 -CheckOnly -Repository lotus-workbench` returned clean
   synchronization.

#### RFC42-WTBD-006 - Source-Owned Realized Outcome Methodologies

Target business outcome:

Outcome reviews can compare richer realized evidence across risk, performance, tax, FX, cash,
liquidity, and execution dimensions using source-owner methodologies and certified contracts.

Implementation-backed progress:

1. `src/core/outcomes/performance_sources.py` adds WTBD-006 source-family adapters for
   `lotus-performance` workspace-summary TWR return, active return, MWR return, contribution
   selected-measure evidence, and attribution reconciliation/level/currency selected-measure
   evidence,
2. `src/core/outcomes/risk_sources.py` adds WTBD-006 source-family adapters for
   `lotus-risk` `RiskMetricsReport:v1`, drawdown response evidence, concentration response
   selected-measure evidence, rolling metrics selected metric/statistic/window evidence, and
   historical attribution selected set/contributor evidence,
3. `src/core/outcomes/core_sources.py` adds WTBD-006 `lotus-core` source-family adapters for
   `HoldingsAsOf:v1` cash-total evidence, `TransactionLedgerWindow:v1` explicit transaction-row
   scalar evidence, and `PortfolioCashflowProjection:v1` total net cashflow evidence,
4. the performance adapters consume source-owned `WORKSPACE_SUMMARY_TWR_RETURN`,
   `WORKSPACE_SUMMARY_ACTIVE_RETURN`, `WORKSPACE_SUMMARY_MWR_RETURN`, and
   `PERFORMANCE_CONTRIBUTION`, and `PERFORMANCE_ATTRIBUTION` output and convert percentage-point
   source units to RFC-0042 ratio units without calculating performance, contribution, or
   attribution locally,
5. the risk adapters consume source-owned `RISK_METRICS_REPORT`, `DRAWDOWN_RESPONSE`,
   `CONCENTRATION_RESPONSE`, `ROLLING_RISK_METRICS_REPORT`, and
   `HISTORICAL_RISK_ATTRIBUTION` output and preserve selected source metric, absolute
   max-drawdown, benchmark-relative max-drawdown, HHI, single-position concentration, issuer
   concentration, issuer-coverage, rolling metric, rolling statistic, rolling window, attribution
   type, attribution metric, grouping dimension, set-level measure, and explicit contributor values
   without calculating risk locally,
6. the core adapters consume source-owned `HOLDINGS_AS_OF_CASH_BALANCE` totals,
   `TRANSACTION_LEDGER_WINDOW` explicit transaction-row trade-fee, withholding-tax, realized-FX-P&L,
   linked-cashflow measures, and `PORTFOLIO_CASHFLOW_PROJECTION` total net cashflow without
   aggregating cash accounts, aggregating transaction rows, projecting/forecasting cashflows,
   deriving tax, calculating FX, inferring execution quality, or converting currency locally,
7. performance source lineage is preserved through calculation id, calculation hash, selected
   period, selected basis or MWR method where applicable, selected return, contribution, or
   attribution measure, attribution model, linking method, benchmark context where available,
   source supportability where applicable, source owner, source type, and reason codes,
8. risk source lineage is preserved through request fingerprint, selected period where applicable,
   selected risk metric, drawdown measure, concentration measure, rolling metric, rolling
   statistic, rolling window length, attribution type, attribution metric, grouping dimension,
   attribution measure, contributor group key where applicable, source supportability state,
   source supportability reason, issuer coverage posture where applicable, benchmark/risk-free
   context where applicable, attribution quality flags and stateful active-risk support metadata,
   latest observation date, period end date, as-of date, source owner, source type, and reason codes,
9. core source lineage is preserved through product identity, portfolio id, as-of date,
   generated/evidence timestamp, data-quality posture, source fingerprint, source owner, source type,
   transaction id/type, selected transaction measure where applicable, selected source field,
   projection range/include-projected posture where applicable, source units, and reason codes,
10. focused tests prove ready, missing, degraded/unavailable, permission-blocked, explicit metric,
   source supportability, source-owned active return, source-owned MWR return, source-owned
   absolute and relative max drawdown, relative-drawdown unavailable posture, rolling metric
   summaries, benchmark/risk-free rolling degraded posture, historical attribution set and
   contributor measures, historical attribution quality-flag and period-error posture, contribution
   selected measures, attribution reconciliation/level/currency selected measures, stale
   contribution and attribution posture, errored contribution and attribution blocking posture, core
   cash totals, explicit transaction-row trade-fee, withholding-tax, realized-FX-P&L,
   linked-cashflow measures, core cashflow projection total net cashflow, projection
   degraded/unavailable posture, required currency/total/projection guardrails, and malformed
   payload behavior,
11. no broader methodology is claimed yet: aggregated tax, aggregated FX, aggregated
   transaction-cost, execution, cash movements beyond source-emitted totals, liquidity ladders,
   risk attribution outside
   source-emitted historical attribution scalars,
   broader benchmark-relative performance analysis outside source-emitted attribution scalars, and
   full review-window source contracts remain source-owner follow-on scope.

Why it cannot be done now:

RFC-0042 intentionally avoided local calculation clones. The first risk, performance, and core cash
adapters are possible because `lotus-risk` publishes `RiskMetricsReport:v1`, drawdown response
output, concentration response output, rolling metrics response output, and historical attribution
response output, `lotus-performance` publishes workspace-summary TWR, active return, MWR output,
contribution output, and attribution output, and `lotus-core` publishes `HoldingsAsOf:v1` cash
totals, `TransactionLedgerWindow:v1` explicit transaction-row scalar evidence, and
`PortfolioCashflowProjection:v1` total net cashflow with explicit portfolio currency.
Remaining source-owner methods are surfaced as degraded, unsupported, unavailable, malformed,
conflicting, or blocked states until their owning applications publish certified contracts.

Dependencies before implementation:

1. source-owner methodology and API contract,
2. source lineage, freshness, and content hashes,
3. validation of missing, partial, stale, conflicting, and permission-denied behavior,
4. manage adapter consumes source truth without becoming the source owner,
5. OpenAPI and evidence documentation in source-owning apps.

Expected implementation wave:

Implement source family by source family as source owners publish certified contracts.

Promotion proof:

1. source-owner unit/integration/live tests,
2. manage adapter tests,
3. live evidence with ready and degraded examples,
4. README/wiki/context updates in both source and manage repositories.

Latest WTBD-006 tightening proof:

1. local critical review evidence:
   `output/rfc0042-wtbd006-source-methodology-proof/20260506-060312/critical-review.json`,
2. repo-native `make check` passed with `874` unit tests, lint, typecheck, OpenAPI quality,
   API vocabulary, no-alias, mesh contracts, and monetary-float guard,
3. focused source-adapter/doc proof passed with `52` tests across documentation current-state,
   performance, risk, core cash, and realized-source assembly behavior.

Latest WTBD-006 risk-drawdown tightening proof:

1. local critical review evidence:
   `output/rfc0042-wtbd006-risk-drawdown-proof/20260506-061850/critical-review.json`,
2. `tests/unit/core/test_risk_realized_outcome_sources.py` passed with `16` tests,
3. tests cover source-owned absolute max drawdown, benchmark-relative max drawdown, ready snapshot
   assembly, stale source posture, unavailable benchmark-relative posture, missing fingerprint, and
   missing ready-value guardrails,
4. repo-native `make check` passed with `881` unit tests, lint, typecheck, OpenAPI quality,
   API vocabulary, no-alias, mesh contracts, and monetary-float guard,
5. manage preserves `lotus-risk` request fingerprint and supportability truth and performs no
   drawdown path, episode, or benchmark-relative calculation locally.

Latest WTBD-006 risk-concentration tightening proof:

1. local critical review evidence:
   `output/rfc0042-wtbd006-risk-concentration-proof/20260506-064212/critical-review.json`,
2. `tests/unit/core/test_risk_realized_outcome_sources.py` passed with `24` tests,
3. tests cover source-owned HHI, top-position weight, issuer HHI, issuer partial-coverage degraded
   posture, issuer missing-coverage degraded posture, ready snapshot assembly, missing fingerprint,
   and missing ready-value guardrails,
4. repo-native `make check` passed with `889` unit tests, lint, format, mypy, OpenAPI quality,
   API vocabulary, no-alias, domain-data-product, trust telemetry, observability, and
   monetary-float guardrails before PR #96 merge,
5. manage preserves `lotus-risk` request fingerprint, supportability truth, issuer coverage
   posture, and concentration source units, and performs no HHI, top-position, issuer, or coverage
   calculation locally.

Latest WTBD-006 risk-rolling tightening proof:

1. local critical review evidence:
   `output/rfc0042-wtbd006-risk-rolling-proof/20260506-081336/critical-review.json`,
2. `tests/unit/core/test_risk_realized_outcome_sources.py` passed with `33` tests,
3. tests cover source-owned latest rolling volatility, beta percentile, ready snapshot assembly,
   benchmark-unavailable degraded posture, risk-free-unavailable degraded posture, stale source
   posture, permission-blocked posture, missing fingerprint, and missing ready-value guardrails,
4. repo-native `make check` passed with `912` unit tests, lint, format, mypy, OpenAPI quality,
   API vocabulary, domain-data-product, trust telemetry, and observability contract gates,
5. manage preserves `lotus-risk` request fingerprint, supportability truth, selected period,
   selected metric, selected statistic, selected window length, benchmark/risk-free context,
   latest observation date, and source units, and performs no rolling-window, volatility, Sharpe,
   beta, tracking-error, information-ratio, drawdown, percentile, benchmark-alignment, or
   risk-free-alignment calculation locally.

Latest WTBD-006 risk-attribution tightening proof:

1. local critical review evidence:
   `output/rfc0042-wtbd006-risk-attribution-proof/20260506-083000/critical-review.json`,
2. `tests/unit/core/test_risk_realized_outcome_sources.py` passed with `41` tests,
3. tests cover source-owned historical attribution total value, explicit contributor component
   contribution, ready snapshot assembly, source quality-flag degraded posture, period-error
   blocked posture, missing fingerprint, missing ready-value guardrails, and contributor-group-key
   guardrails,
4. repo-native `make check` passed with `920` unit tests, lint, format, mypy, OpenAPI quality,
   API vocabulary, domain-data-product, trust telemetry, and observability contract gates,
5. manage preserves `lotus-risk` request fingerprint, supportability truth, selected period,
   attribution type, metric, grouping dimension, selected measure, contributor group key where
   applicable, stateful active-risk support metadata, quality-flag posture, period-error posture,
   period end date, as-of date, and source units, and performs no covariance, contribution,
   residual, grouping, top-contributor, or support-matrix calculation locally.

Latest WTBD-006 core-transaction-ledger tightening proof:

1. local critical review evidence:
   `output/rfc0042-wtbd006-core-transaction-ledger-proof/20260506-085229/critical-review.json`,
2. `tests/unit/core/test_core_realized_outcome_sources.py` passed with `15` tests,
3. tests cover source-owned trade fee, withholding tax, realized FX P&L, linked cashflow amount,
   ready tax-dimension snapshot assembly, degraded source-owner posture, missing transaction-row
   guardrails, and missing selected source-value guardrails,
4. repo-native `make check` passed with `928` unit tests, lint, format, mypy, OpenAPI quality,
   API vocabulary, no-alias, domain-data-product, trust-telemetry, observability, and
   monetary-float guardrails,
5. manage preserves `lotus-core` product identity, portfolio id, as-of date, generated/evidence
   timestamp, data-quality posture, source fingerprint, transaction id/type, selected measure,
   selected source field, and source units, and performs no transaction aggregation, tax
   calculation, FX calculation, cash movement aggregation, currency conversion, or
   execution-quality inference locally.

Latest WTBD-006 core-cashflow-projection tightening proof:

1. local critical review evidence:
   `output/rfc0042-wtbd006-core-cashflow-projection-proof/20260506-101500/critical-review.json`,
2. source-owner hardening was completed, merged, CI-proven, and wiki-published in `lotus-core`
   PR #338 as merge commit `1ab53453198bede79b1d8ec7326120f27adc9ba5`; the core source product
   now exposes `PortfolioCashflowProjection:v1` product metadata, latest evidence timestamp,
   deterministic source fingerprint, and explicit `portfolio_currency`,
3. local manage adapter proof passed with `33` focused core/realized-source tests,
4. tests cover source-owned total net cashflow, ready cash-dimension snapshot assembly, degraded
   source-owner posture, unavailable source-owner posture, missing portfolio currency, missing
   total net cashflow, and missing include-projected posture,
5. manage preserves `lotus-core` product identity, portfolio id, as-of date, generated/evidence
   timestamp, data-quality posture, source fingerprint, projection range, include-projected
   posture, selected measure, and portfolio currency, and performs no cashflow forecasting,
   cashflow aggregation, liquidity-ladder calculation, currency conversion, or execution-quality
   inference locally.

Latest WTBD-006 performance-contribution tightening proof:

1. local critical review evidence:
   `output/rfc0042-wtbd006-performance-contribution-proof/20260506-074309/critical-review.json`,
2. `tests/unit/core/test_performance_realized_outcome_sources.py` passed with `19` tests,
3. tests cover source-owned total contribution, total portfolio return, summary FX contribution,
   ready snapshot assembly, stale/degraded source-owner posture, errored source blocking posture,
   and missing ready-value guardrails,
4. repo-native `make check` passed with `896` unit tests, lint, format, mypy, OpenAPI quality,
   API vocabulary, no-alias, domain-data-product, trust telemetry, observability, and
   monetary-float guardrails before PR #97 merge,
5. manage preserves `lotus-performance` calculation id, calculation hash, supportability truth,
   input mode, selected contribution measure, and percentage-point to ratio unit conversion, and
   performs no position, daily, hierarchy, local/FX, benchmark-relative, or attribution calculation
   locally.

Latest WTBD-006 performance-attribution tightening proof:

1. local critical review evidence:
   `output/rfc0042-wtbd006-performance-attribution-proof/20260506-075838/critical-review.json`,
2. `tests/unit/core/test_performance_realized_outcome_sources.py` passed with `26` tests,
3. tests cover source-owned active-return reconciliation, level total effect, currency total
   effect, ready snapshot assembly, stale/degraded source-owner posture, errored source blocking
   posture, and missing ready-value guardrails,
4. repo-native `make check` passed with `903` unit tests, lint, format, mypy, OpenAPI quality,
   API vocabulary, no-alias, domain-data-product, trust-telemetry, observability, and
   monetary-float guardrails,
5. manage preserves `lotus-performance` calculation id, calculation hash, supportability truth,
   input mode, attribution model, linking method, benchmark context, selected attribution measure,
   and percentage-point to ratio unit conversion, and performs no group-row summing, active-return,
   allocation, selection, interaction, residual, currency-effect, benchmark-selection, or
   attribution calculation locally.

#### RFC42-WTBD-007 - External Execution / OMS Integration And Acknowledgements

Target business outcome:

Outcome reviews can include governed execution status, acknowledgement, rejection, cancellation,
settlement, and reconciliation facts from an execution/OMS owner.

Why it cannot be done now:

No execution/OMS owner or contract is established. RFC-0041 deliberately stopped at internal
operations handoff evidence, and RFC-0042 must not invent execution truth.

Dependencies before implementation:

1. execution/OMS owner and API contract,
2. order, acknowledgement, rejection, cancellation, settlement, and reconciliation semantics,
3. maker-checker and entitlement controls,
4. failure/retry/compensation model,
5. manage outcome-review adapter that treats execution as source truth.

Expected implementation wave:

Do not start until the execution owner and control model are explicit.

Promotion proof:

1. execution-owner API certification,
2. manage integration tests,
3. failure, rejection, cancellation, and reconciliation proof,
4. operational runbook and supportability evidence,
5. supported-feature promotion that names the execution boundary.

#### RFC42-WTBD-008 - PM Quality Scoring Or Behavioral Analytics

Target business outcome:

If the business later approves it, outcome evidence could support governed learning analytics over
process quality without becoming opaque, punitive, or biased.

Why it cannot be done now:

RFC-0042 explicitly supports outcome review, not PM scoring. Scoring requires business ownership,
methodology, controls, explainability, fairness review, and governance that do not exist in this
RFC.

Dependencies before implementation:

1. named business owner,
2. approved auditable methodology,
3. bias, explainability, and appropriate-use controls,
4. source and outcome evidence boundaries,
5. AI/product/legal/compliance sign-off if AI is involved.

Expected implementation wave:

Treat as a separate governed RFC only if the business explicitly wants this capability.

Promotion proof:

1. methodology document and worked examples,
2. tests for explainability, constraints, and inappropriate-use blocks,
3. governance approval evidence,
4. README/wiki/supported-feature updates with strict wording,
5. client-facing material reviewed for appropriate claims.

### Suggested Sequencing

Recommended order:

1. maintain the implemented Gateway/Workbench outcome-review composition as contracts evolve,
2. maintain generated report/render/archive materialization and retrieval posture,
3. maintain governed AI narrative support only through `lotus-ai`, Gateway, and Workbench,
4. add source-owned risk/performance/tax/FX/cash/execution methodologies as source owners publish
   certified contracts,
5. evaluate PM quality scoring only as a separate governance-heavy RFC.

Rationale:

Gateway, Workbench, report/render/archive, and governed AI narrative now realize the supported
manage backend for the first-wave RFC-0042 product path without waiting for every future source
methodology. Execution/OMS integration, richer source-owned outcome methodologies, and PM scoring
still introduce separate ownership, control, audit, and regulatory considerations and must not be
folded back into manage.

### RFC-0042 Promotion Checklist For Any Future Item

Before any item above moves from this ledger into a supported-feature claim:

1. owning repository and API/source contract are explicit,
2. implementation is complete in the owning app,
3. `lotus-manage` consumes only certified source truth where it is not the owner,
4. Gateway and Workbench consume through the governed product path,
5. degraded, stale, missing, permission-denied, partial, unsupported, malformed, conflicting, and
   unavailable states are tested where applicable,
6. OpenAPI/Swagger quality is certified for every API added or changed,
7. live or canonical front-office evidence is captured and critically reviewed,
8. README, RFC, source-map, wiki, supported-features, and repository context are aligned,
9. PR checks are green, PRs are merged, wiki is published, and branches are cleaned.
