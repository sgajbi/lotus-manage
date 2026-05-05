# RFC-0042 Source Map and Gap Analysis

| Metadata | Details |
| --- | --- |
| **Status** | DRAFT - GOLD-STANDARD TIGHTENING COMPLETE; IMPLEMENTATION NOT STARTED |
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
