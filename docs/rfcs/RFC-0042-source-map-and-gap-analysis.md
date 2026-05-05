# RFC-0042 Source Map and Gap Analysis

| Metadata | Details |
| --- | --- |
| **Status** | IN IMPLEMENTATION - SLICES 0-11 COMPLETE; NO FULL PRODUCT SUPPORT CLAIM |
| **Created** | 2026-05-05 |
| **RFC** | `docs/rfcs/RFC-0042-post-trade-outcome-feedback-loop.md` |
| **Tightening Branch** | `docs/rfc0042-gold-standard-tightening` |
| **Future Implementation Branch** | `feat/rfc0042-implementation` unless an active RFC-0042 implementation branch exists |
| **Evidence Root For Future Implementation** | `output/rfc0042-outcome-proof/<timestamp>/` |

---

## Purpose

This source map is the Slice 0 control artifact for RFC-0042. It prevents the implementation from
turning post-trade outcome feedback into a manage-local approximation of execution, risk,
performance, tax, holdings, cash, or report/AI truth.

Implementation must not start until this document is reviewed and the first-wave source boundary is
accepted. No supported-feature promotion is made by this document.

---

## Slice 0 Result

Slice 0 result:

1. RFC-0042 has been tightened into an execution-grade guide.
2. First-wave support is bounded to manage-owned outcome review authority.
3. Realized source truth remains owned by `lotus-core`, `lotus-risk`, `lotus-performance`, or a
   future execution/OMS owner.
4. Gateway and Workbench realization must be RFC-led downstream work after manage contracts and live
   proof are stable.
5. Report and AI behavior is limited to bounded evidence inputs from manage.
6. Work-to-be-done ledger items have been classified as included, partially included, downstream, or
   outside the first wave.

No route, persistence table, runtime capability, Gateway behavior, Workbench behavior, report
artifact, AI narrative, or supported-feature claim is added by Slice 0.

---

## Slice 1 Platform Result

Slice 1 platform evidence is recorded in
`docs/rfcs/RFC-0042-platform-automation-slice1.md`.

The cross-cutting platform gap was source-degraded and reconciliation endpoint guidance in the
backend service scaffold. `sgajbi/lotus-platform#297`, merged as `1b9671e`, updates
`automation/New-Lotus-Service.ps1` so new backend services start with source-owner, freshness,
lineage, supportability, degraded-state, no-local-clone, and documentation-promotion expectations
in generated API certification guidance.

Slice 1 is `DONE`; no manage runtime code or supported-feature claim was added in this slice.

---

## Slice 2 Cleanup and Structure Result

Slice 2 completed a cleanup and structure review before runtime implementation. Evidence lives in
`docs/rfcs/RFC-0042-cleanup-and-structure-slice2.md`.

The review found no existing runtime outcome authority to refactor or remove. The key cleanup was
documentation truth: `wiki/Supported-Features.md` no longer implies that outcome events are already
part of supported decision-timeline memory. Outcome events remain RFC-0042 proposed work until
source-backed runtime implementation, proof, downstream realization where surfaced, and wiki
publication are complete.

The implementation boundary is now explicit: RFC-0042 should introduce a dedicated outcome domain,
repository, service, router, source-adapter, and handoff structure instead of adding outcome
behavior to the wave router or cloning source-owner methodology.

No supported feature is promoted by Slice 2.

---

## Slice 3 Domain Model and Pure Comparison Result

Slice 3 evidence is recorded in `docs/rfcs/RFC-0042-domain-model-slice3.md`.

`src/core/outcomes/` now contains typed outcome-review domain primitives and a deterministic
comparison engine over supplied expected and realized snapshots. The implementation deliberately
does not call source-owner apps, persist reviews, expose APIs, produce reports, produce AI evidence,
or claim product support.

Tests prove lower-is-better, higher-is-better, soft tolerance, hard tolerance, missing source values,
degraded source values, `NOT_SUPPORTED` source posture, execution-evidence blocking, roll-up
precedence, and invalid tolerance rejection.

No supported feature is promoted by Slice 3.

---

## Slice 4 Expected Snapshot Assembly Result

Slice 4 evidence is recorded in `docs/rfcs/RFC-0042-expected-snapshot-slice4.md`.

`src/core/outcomes/snapshots.py` now assembles expected outcome snapshots from RFC-0039 selected
alternatives, RFC-0040 proof packs, and optional RFC-0041 wave item and internal operations handoff
refs. The assembly rejects mismatched portfolio, mandate, run, alternative, proof-pack, wave, and
handoff linkages and preserves source refs, source hashes, section hashes, and supportability.

The expected snapshot only includes values that exist in the selected alternative. It does not default
risk, performance, tax, FX, or execution-quality values.

No supported feature is promoted by Slice 4.

---

## Slice 5 Realized Source Adapter Result

Slice 5 evidence is recorded in `docs/rfcs/RFC-0042-realized-source-adapters-slice5.md`.

`src/core/outcomes/realized_sources.py` now translates explicit source-owner realized snapshots into
comparable outcome metrics while preserving source refs, source hashes, freshness, quality posture,
and supportability. It handles ready, missing, stale, unavailable, partial, malformed, conflicting,
blocked, and not-supported source evidence without calculating source-owner truth locally.

The implementation records the first-wave boundary: missing execution evidence emits
`EXECUTION_EVIDENCE_BLOCKED`, missing risk evidence emits `RISK_OUTCOME_NOT_SUPPORTED`, and missing
performance evidence emits `PERFORMANCE_OUTCOME_NOT_SUPPORTED` until certified review-window
contracts exist.

No supported feature is promoted by Slice 5.

---

## Slice 6 Persistence, Repository, Events, and Retention Result

Slice 6 evidence is recorded in `docs/rfcs/RFC-0042-persistence-events-slice6.md`.

`DpmPostTradeOutcomeReview`, `DpmOutcomeReviewRepository`,
`InMemoryDpmOutcomeReviewRepository`, `PostgresDpmOutcomeReviewRepository`, and migration
`0008_post_trade_outcome_reviews.sql` now provide immutable review persistence, idempotency
protection, filtered search, retention metadata, and append-only outcome events.

No supported feature is promoted by Slice 6.

---

## Slice 7 Certified Manage APIs and OpenAPI Quality Result

Slice 7 evidence is recorded in `docs/rfcs/RFC-0042-api-openapi-slice7.md`.

`src/api/routers/outcome_reviews.py` and `src/api/services/outcome_review_service.py` now expose
the manage-owned RFC-0042 outcome-review API foundation:

1. preview expected-versus-realized comparison without persistence,
2. idempotent immutable review creation,
3. bounded review search,
4. review lookup,
5. source-refresh re-evaluation with append-only event evidence,
6. operator-safe supportability lookup,
7. run and wave read-side lookup routes.

OpenAPI paths are grouped under `lotus-manage Outcome Reviews`, and tests pin the route presence,
request/response body presence, and What/When/How guidance for preview and refresh.

No full RFC-0042 supported feature is promoted by Slice 7. Report input, AI evidence input,
supportability/observability hardening, live canonical proof, Gateway/Workbench realization RFCs,
final hardening, PR merge, and wiki publication remain pending.

---

## Slice 8 Report Input and AI Evidence Input Handoffs Result

Slice 8 evidence is recorded in `docs/rfcs/RFC-0042-report-ai-handoffs-slice8.md`.

`src/core/outcomes/handoffs.py` now builds deterministic `DpmOutcomeReportInput` and
`DpmOutcomeAiEvidenceInput` contracts from the persisted immutable outcome review. The report input
is report-ready but does not render a report or create an archive record. The AI evidence input is
bounded, hash-linked, source-ref-backed, and includes explicit forbidden actions for order
placement, approval, control override, invented evidence, PM scoring, and client contact.

`src/api/routers/outcome_reviews.py` exposes:

1. `GET /api/v1/rebalance/outcome-reviews/{outcome_review_id}/report-input`,
2. `GET /api/v1/rebalance/outcome-reviews/{outcome_review_id}/ai-evidence-input`.

No downstream product claim is promoted by Slice 8. `lotus-report`, `lotus-render`,
`lotus-archive`, and `lotus-ai` own artifact generation, archive lifecycle, workflow packs,
prompts, generated narrative, and AI execution guardrails.

---

## Slice 9 Supportability, Observability, and Operator Diagnostics Result

Slice 9 evidence is recorded in
`docs/rfcs/RFC-0042-supportability-observability-slice9.md`.

`lotus_manage_outcome_review_supportability_total` now records bounded create, source-refresh, and
supportability-read posture for outcome reviews. The monitoring contract defines allowlisted
`surface`, `supportability_state`, and `reason` labels, adds an outcome-review supportability panel,
and adds a blocked-state alert linked to the RFC-0042 runbook.

`GET /api/v1/rebalance/outcome-reviews/{outcome_review_id}/supportability` now returns
operator-safe source-owner, source-ref count, dimension-state count, freshness-state count, and
remediation-route diagnostics. The router emits safe supportability inspection logs with counts and
bounded state only.

No full RFC-0042 product support is promoted by Slice 9. Live source-backed proof,
Gateway/Workbench realization RFCs, final hardening, PR merge, and wiki publication remain pending.

---

## Slice 10 Gateway and Workbench Realization RFC Result

Slice 10 evidence is recorded in
`docs/rfcs/RFC-0042-gateway-workbench-realization-slice10.md`.

`lotus-gateway` RFC-0098 was tightened on branch `feat/rfc0042-outcome-realization` and pushed at
commit `38d46f9`. It now defines strategic Gateway routes under
`/api/v1/dpm/command-center/outcome-reviews*`, typed manage upstream consumption, required
outcome-review modules, supportability preservation, no-recompute rules, and live proof
expectations.

`lotus-workbench` RFC-0098 was tightened on branch `feat/rfc0042-outcome-realization` and pushed at
commit `3b5182f`. It now defines the future post-trade outcome-review workspace, required panels,
required UI states, Gateway-only route consumption, no client-side calculation posture, and
promotion gates for canonical browser proof.

No Gateway or Workbench supported-feature claim is promoted by Slice 10. Downstream implementation,
canonical product proof, PR merge, and wiki publication remain required before product realization
can be claimed.

---

## Current Foundation Evidence

| Foundation | Current evidence | RFC-0042 implication |
| --- | --- | --- |
| Stateful DPM source posture | RFC-0036 sourceful execution path and core source readiness | Outcome reviews can reuse source-readiness conventions but must not assume every post-trade source exists. |
| Mandate and command-center foundation | RFC-0038 mandate twin, health, monitoring, command-center summary | Outcome reviews can attach mandate/portfolio context when implementation-backed. |
| Construction alternatives | RFC-0039 selected alternatives and method supportability | Expected construction snapshot must come from selected alternatives, not recomputed choices. |
| Proof packs | RFC-0040 proof-pack JSON, Markdown summary, report input, AI evidence input, lineage and retention | Outcome reviews must link to proof-pack refs and section/source hashes where available. |
| Rebalance waves | RFC-0041 explicit portfolio-list waves, source-check, simulation, selection, proof-pack linkage, approval, staging, internal handoff | Outcome reviews can link to wave item and internal handoff evidence; external execution remains unclaimed. |
| Work-to-be-done ledger | `docs/rfcs/RFC-worktobedone.md` | RFC-0042 pulls in outcome-loop work and leaves downstream/product/source-owner items bounded. |

---

## Work-To-Be-Done Intake Classification

| Ledger item | Classification | RFC-0042 handling |
| --- | --- | --- |
| `RFC37-WTBD-001` Complete RFC-0042 post-trade outcome feedback loop | Included | Governing feature scope for manage plus source-owner dependencies. |
| `RFC37-WTBD-007` Portfolio memory across mandate, construction, proof-pack, wave, outcome, report, AI events | Partially included | RFC-0042 emits outcome events and review refs; full portfolio memory remains cross-app future work. |
| `RFC40-WTBD-010` Decision timeline and portfolio memory | Partially included | Outcome reviews attach to proof-pack and decision refs where available; no full timeline UI claim. |
| `RFC41-WTBD-004` Risk and performance aggregate enrichment | Source-owner included | Risk/performance evidence must come from owner contracts; missing owner capability blocks the dimension. |
| `RFC41-WTBD-005` Gateway wave composition | Downstream | RFC-0042 must create/tighten Gateway outcome realization RFC direction; manage implementation does not satisfy product support. |
| `RFC41-WTBD-006` Workbench wave command center | Downstream | RFC-0042 must create/tighten Workbench outcome review RFC direction; Workbench must consume Gateway only. |
| `RFC41-WTBD-008` Report materialization | Downstream | Manage emits report input only; rendering/archive belongs to owning apps. |
| `RFC41-WTBD-009` AI PM memo generation | Downstream | Manage emits AI evidence input only; RFC-0043/`lotus-ai` owns prompts, guardrails, and output. |
| `RFC41-WTBD-010` External execution integration | Outside first-wave support unless owner exists | Execution quality requires certified fill/order evidence; otherwise emit `EXECUTION_EVIDENCE_BLOCKED`. |

---

## Source Dependency Classification

| Source or contract | Owner | Required for | First-wave posture | Required implementation action |
| --- | --- | --- | --- | --- |
| Selected construction alternative | `lotus-manage` RFC-0039 | Expected snapshot | Required | Consume existing selected-alternative record and method supportability. |
| Proof-pack evidence | `lotus-manage` RFC-0040 | Expected snapshot, lineage, report/AI handoff | Required for proof-pack outcome claim | Link proof-pack id, hashes, Markdown/report/AI evidence refs. |
| Wave item and internal handoff | `lotus-manage` RFC-0041 | Wave outcome review | Required for wave-linked reviews | Validate wave item, selection, approval/staging/handoff refs. |
| Booked transactions | `lotus-core` | Turnover, cost, cash, tax, execution reconciliation | Source-owner required | Consume certified product if available; otherwise block affected dimensions. |
| Fill/order/execution detail | `lotus-core` or future execution/OMS owner | `EXECUTION_QUALITY` | Blocked until certified | Do not infer partial fills or slippage from manage intent. |
| Post-trade holdings and positions | `lotus-core` | Drift, rule, cash/security residuals | Source-owner required | Consume source product with as-of date and lineage. |
| Cash movements | `lotus-core` | `CASH_OUTCOME` and MWR-related context | Source-owner required | Consume source product; missing source blocks cash outcome. |
| FX executions and currency exposures | `lotus-core` or treasury source owner | `FX_OUTCOME` | Source-owner required | Consume source product; no local treasury-depth reconstruction. |
| Tax lots and realized tax | `lotus-core` or tax source owner | `TAX_OUTCOME` | Source-owner required | Consume source product; no manage-local tax-lot authority. |
| Risk after execution | `lotus-risk` | `RISK_OUTCOME` | Supported only if endpoint supports review window and portfolio context | Consume risk owner output and supportability; otherwise mark not supported/degraded. |
| Returns series/TWR/MWR/contribution/attribution | `lotus-performance` | `PERFORMANCE_OUTCOME` | Supported only if endpoint supports review window and benchmark context | Consume performance owner output and supportability; otherwise mark not supported/degraded. |
| Report artifact | `lotus-report`, `lotus-render`, `lotus-archive` | Reports and archive | Downstream only | Manage emits `DpmOutcomeReportInput`; no artifact claim. |
| AI memo/copilot output | `lotus-ai` | AI assistance | Downstream only | Manage emits `DpmOutcomeAiEvidenceInput`; no narrative claim. |
| Product composition | `lotus-gateway` | Product API | Downstream RFC required | Gateway must preserve manage truth and source supportability. |
| Product surface | `lotus-workbench` | UI/demos | Downstream RFC required | Workbench must consume Gateway/BFF only and prove canonical runtime. |

---

## First-Wave Outcome Dimension Posture

| Dimension | First-wave support condition | Blocked/not-supported posture |
| --- | --- | --- |
| `DRIFT_OUTCOME` | Expected target/current state plus post-trade holdings are source-backed. | `DRIFT_SOURCE_INCOMPLETE` if holdings or expected target is missing. |
| `RISK_OUTCOME` | `lotus-risk` provides post-trade risk for the review window with supportability. | `RISK_OUTCOME_NOT_SUPPORTED` or `RISK_SOURCE_UNAVAILABLE`. |
| `PERFORMANCE_OUTCOME` | `lotus-performance` provides returns/contribution/attribution for the review window. | `PERFORMANCE_OUTCOME_NOT_SUPPORTED` or `PERFORMANCE_SOURCE_UNAVAILABLE`. |
| `TURNOVER_OUTCOME` | Booked transaction window is source-backed. | `TRANSACTION_SOURCE_INCOMPLETE`. |
| `TRANSACTION_COST_OUTCOME` | Realized cost source is available and comparable to estimated cost basis. | `COST_SOURCE_INCOMPLETE`. |
| `TAX_OUTCOME` | Realized tax/tax-lot evidence is source-backed. | `TAX_SOURCE_INCOMPLETE`. |
| `FX_OUTCOME` | FX executions/currency exposures are source-backed. | `FX_SOURCE_INCOMPLETE`. |
| `CASH_OUTCOME` | Post-trade cash movements and balances are source-backed. | `CASH_SOURCE_INCOMPLETE`. |
| `EXECUTION_QUALITY` | Fill/order/execution source exists with partial, cancelled, unfilled, slippage, and timing evidence. | `EXECUTION_EVIDENCE_BLOCKED`. |
| `RULE_OUTCOME` | Rule source and post-trade state source both exist. | `RULE_SOURCE_INCOMPLETE`. |
| `SOURCE_DATA_OUTCOME` | Manage can classify completeness and supportability of all requested source families. | Always available as a classification, but never converts blocked dimensions to ready. |

---

## Review Window Semantics

The implementation must define review-window semantics before durable create:

1. `review_window_start` must be anchored to the selected alternative, proof pack, wave item,
   internal handoff, or execution source event.
2. `review_window_end` must be explicit and must not default to current time without caller intent.
3. risk and performance windows must align with owner-service conventions.
4. transaction/fill windows must state inclusion/exclusion rules for partial fills, cancellations,
   late bookings, and corporate-action adjustments.
5. refresh must append a new event and source hash; it must not mutate prior review evidence
   without audit trace.

---

## Degraded and Blocked Behavior Rules

1. Missing mandatory expected evidence blocks durable creation.
2. Missing mandatory realized evidence blocks the affected dimension.
3. Optional source evidence may degrade the review only if the API response names the missing source
   and its business effect.
4. Source staleness must preserve source timestamp and freshness policy.
5. Source conflicts must be visible and must not be overwritten by later source order.
6. `SOURCE_DATA_OUTCOME` may be ready while other dimensions are blocked, but it must clearly state
   that it is only a source completeness assessment.
7. Unsupported dimensions must not appear as successful, estimated, or assumed.

---

## Gateway and Workbench Realization Boundary

RFC-0042 manage implementation must create or tighten downstream realization RFCs near the end of
manage implementation, after manage contracts and live proof are stable.

Gateway RFC/addendum must specify:

1. typed manage client and route strategy for outcome reviews,
2. payload preservation for source lineage, supportability, hashes, dimensions, and links,
3. no recomputation of manage outcome state,
4. no direct composition of risk/performance/core values that bypasses manage review authority,
5. OpenAPI examples and degraded-state responses.

Workbench RFC/addendum must specify:

1. outcome review list and detail surfaces,
2. proof-pack, wave, and construction links,
3. source-degraded and blocked-state presentation,
4. PM explanation workflow if implemented,
5. report/AI posture without unsupported generation claims,
6. canonical front-office proof through Gateway/BFF only.

No Gateway or Workbench supported-feature claim may be made from manage-only evidence.

---

## Slice 11 Live Implementation Proof Result

Slice 11 evidence is recorded in `docs/rfcs/RFC-0042-implementation-proof-slice11.md`.

Live accepted output:

`output/rfc0042-outcome-proof/20260505-024352/`

Critical review result:

`output/rfc0042-outcome-proof/20260505-024352/critical-review.json` => `passed`.

The live proof exercised the canonical manage runtime and verified:

1. health readiness,
2. preview and durable create for a source-backed `PB_SG_GLOBAL_BAL_001` outcome review,
3. retrieve, search, supportability, report-input, and AI-evidence endpoints,
4. source lineage and SHA-256 content hashes across `lotus-manage` expected evidence and
   `lotus-core` realized evidence refs,
5. worked variance example for `DRIFT_REDUCTION`,
6. degraded realized source behavior,
7. append-only source refresh event behavior,
8. run and wave lookup routes,
9. live OpenAPI certification for all RFC-0042 outcome-review paths.

The proof found real quality gaps and they were fixed before the slice was accepted:

1. stale canonical runtime restart handling caused an old OpenAPI document to remain live on
   `8001`; `scripts/Start-CanonicalManage.ps1` now avoids the reserved PowerShell `$PID` variable
   when stopping an existing listener.
2. five GET endpoints lacked explicit What/When/How OpenAPI guidance; the router descriptions and
   API contract test now guard that standard.
3. generated proof payloads now use proper SHA-256 source and section hashes and keep refreshed
   realized source refs consistent across lineage, source hashes, and dimension refs.

No full RFC-0042 product support is promoted by Slice 11. Manage backend behavior is live-proven;
hardening, final closure, PR/CI, merge, wiki publication, and downstream product realization where
surfaced remain required.

---

## Evidence Convention

Future implementation evidence must be captured under:

`output/rfc0042-outcome-proof/<timestamp>/`

Minimum evidence:

1. `manifest.json`
2. `source-map-review.json`
3. `create-request.json`
4. `create-response.json`
5. `retrieved-review.json`
6. `search-response.json`
7. `supportability-response.json`
8. `report-input.json`
9. `ai-evidence-input.json`
10. `source-lineage.json`
11. `variance-worked-example.json`
12. `degraded-source-example.json`
13. `openapi-certification.json`
14. `critical-review.json`
15. `test-summary.json`

When front-office proof is required, use the governed canonical runtime and `PB_SG_GLOBAL_BAL_001`
unless a later RFC explicitly selects another dataset. Screenshots must not be captured as
demo-ready material before API, calculation, and panel validation pass.

---

## Supported-Features Decision

No supported feature is promoted by RFC-0042 tightening.

The current documentation update may state that RFC-0042 is tightened and implementation-ready, but
must not state that post-trade outcome feedback is supported. Promotion requires implementation,
tests, live evidence, OpenAPI certification, README/wiki/supported-feature updates, PR merge, wiki
publication, and branch cleanup.

---

## Open Questions for Implementation Slice 0 Review

1. Which `lotus-core` source product should be the first certified transaction/fill window for
   outcome reviews?
2. Can `lotus-risk` provide post-trade risk for the exact review window, or is a risk-owner RFC
   required first?
3. Can `lotus-performance` provide the required window return/contribution/attribution contract, or
   is a performance-owner RFC required first?
4. Should first-wave live proof block on `EXECUTION_QUALITY`, or should execution quality remain
   `NOT_SUPPORTED` while drift/source/risk/performance dimensions proceed?
5. Which downstream Gateway and Workbench RFC identifiers will own outcome-feedback realization?
