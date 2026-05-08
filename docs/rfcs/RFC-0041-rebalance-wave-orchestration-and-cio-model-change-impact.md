# RFC-0041: Rebalance Wave Orchestration and CIO Model Change Impact

| Metadata | Details |
| --- | --- |
| **Status** | DONE |
| **Created** | 2026-05-03 |
| **Last Tightened** | 2026-05-05 |
| **Owner** | `lotus-manage` |
| **Business Sponsor Persona** | CIO desk, DPM head, portfolio manager, investment control, operations, compliance, sales/pre-sales |
| **Depends On** | RFC-0018, RFC-0020, RFC-0023, RFC-0036, RFC-0037, RFC-0038, RFC-0039, RFC-0040, `lotus-core` RFC-0087 |
| **Downstream Realization Depends On** | Gateway wave-composition RFC, Workbench wave-command-center RFC, canonical front-office proof contracts |
| **RFC Tightening Branch** | `feat/rfc0041-gold-standard-tightening` |
| **Implementation Branch** | `feat/rfc0041-implementation` |
| **Slice 0 Evidence** | `docs/rfcs/RFC-0041-source-map-and-gap-analysis.md` |
| **Slice 1 Platform Evidence** | `lotus-platform` PR #296, merge `47d3c7f` |
| **Slice 2 Cleanup Evidence** | `docs/rfcs/RFC-0041-source-map-and-gap-analysis.md#slice-2-cleanup-result` |
| **Slice 3 Domain Evidence** | `src/core/waves/`, `src/infrastructure/waves/`, migration `0007_rebalance_waves.sql`, `tests/unit/dpm/waves/test_wave_domain.py` |
| **Slice 4 API Evidence** | `POST /api/v1/rebalance/waves/preview`, `POST /api/v1/rebalance/waves`, `src/api/services/wave_service.py`, `tests/unit/dpm/api/test_waves_api.py` |
| **Slice 5 Source Check Evidence** | `POST /api/v1/rebalance/waves/{wave_id}/source-check`, `src/core/waves/source_readiness.py`, authoritative mandate twin and health classification, `tests/unit/dpm/api/test_waves_api.py` |
| **Slice 6 Simulation/Selection Evidence** | `POST /api/v1/rebalance/waves/{wave_id}/simulate`, `POST /api/v1/rebalance/waves/{wave_id}/items/{wave_item_id}/select`, RFC-0039 construction delegation, RFC-0040 proof-pack linkage, `tests/unit/dpm/api/test_waves_api.py` |
| **Slice 7 Approval/Handoff Evidence** | `POST /api/v1/rebalance/waves/{wave_id}/approve`, `POST /api/v1/rebalance/waves/{wave_id}/stage`, `POST /api/v1/rebalance/waves/{wave_id}/handoff`, append-only internal handoff refs, no external execution claim, `tests/unit/dpm/api/test_waves_api.py` |
| **Slice 8 Supportability Evidence** | `GET /api/v1/rebalance/waves/{wave_id}/supportability`, product-safe diagnostics, bounded `lotus_manage_wave_supportability_total` metric, observability contract update, `tests/unit/dpm/api/test_waves_api.py`, `tests/unit/dpm/api/test_observability_api.py` |
| **Slice 9 Downstream RFC Evidence** | `lotus-gateway` PR #183 merge `e0e4b1b`, `lotus-workbench` PR #143 merge `c4888d4`, Gateway wiki publish `3fc30e8`, Workbench wiki publish `25566cb` |
| **Slice 10 Live Proof Evidence** | `output/rfc0041-wave-proof/20260504-231914/manifest.json`, `critical-review.json`, `critical-review.md`, live Postgres-backed manage runtime on `http://127.0.0.1:8001` |
| **Slice 11 Hardening Evidence** | RFC/API contract drift removed, source-readiness and selection-conflict tests added, OpenAPI/vocabulary/docs gates passed |
| **Slice 12 Closure Evidence** | Final gold-pass assessment complete, README/RFC index/context/wiki/supported-features aligned, wiki publish required after merge |
| **Doc Location** | `docs/rfcs/RFC-0041-rebalance-wave-orchestration-and-cio-model-change-impact.md` |

---

## 0. Executive Summary

RFC-0041 adds multi-portfolio discretionary portfolio management orchestration to
`lotus-manage`. It turns a CIO model change, tactical house view, PM book review, or explicit
portfolio list into a governed rebalance wave: affected mandates are identified, source readiness
is checked, construction alternatives are generated for ready items, exceptions remain visible,
approvals are actor-attributed, approved actions are staged, and handoff evidence is prepared
without pretending external execution has happened.

This RFC is intentionally a pre-implementation execution guide. It must be strong enough for an
implementer to execute slice by slice with minimal ambiguity. No implementation should begin until
the source map, state machine, API contract, persistence model, evidence requirements, downstream
realization plan, and closure criteria in this document are accepted.

The manage-owned outcome is a durable backend wave authority. The full front-office business
outcome also requires `lotus-gateway` composition and `lotus-workbench` product realization through
paired RFCs. Gateway and Workbench must consume manage truth; they must not reconstruct wave state,
read raw domain services directly, or promote UI support before live proof exists.

---

## 1. Critical Review of the Prior Draft

The first RFC-0041 draft had the right business direction but was not yet an execution-grade plan.
This section records the pre-implementation tightening review so future implementers can understand
the stricter scope.

| Area | Prior weakness | Gold-standard tightening |
| --- | --- | --- |
| Scope | Wave lifecycle was named, but domain ownership and cross-app boundaries were too loose. | Added manage-owned backend authority, explicit downstream Gateway/Workbench realization, and no-local-clone rules for core/risk/performance/report/AI. |
| Sequencing | Feature slices existed but mandatory platform, cleanup, proof, hardening, and closure slices were too compressed. | Rebuilt slice plan with Slice 0 source map, platform scaffolding, cleanup, domain/persistence/API slices, proof, second-last hardening, and final closure. |
| Source data | Affected portfolio selection and model-change impact lacked source authority rules. | Added source map, required source refs, controlled degradation, and explicit gaps that must be implemented in owning apps or deferred without support claims. |
| State machine | States were useful but lacked transition guardrails, idempotency, concurrency, and event lineage. | Added append-only transition contract, command idempotency, optimistic concurrency, actor attribution, and safe partial-completion semantics. |
| API quality | Endpoints were named but lacked Swagger/OpenAPI certification expectations. | Added endpoint certification requirements, attribute examples, error examples, tags, vocabulary, no-alias posture, and API inventory expectations. |
| Evidence | Live proof asked for a wave but did not require critical review or mixed-state proof. | Added machine-readable evidence package, critical review artifacts, mixed ready/pending/blocked live proof, and iteration until gaps are fixed. |
| Supported features | Proposed features were listed but not tied to promotion and wiki truth. | Added implementation-backed supported-feature ledger and explicit prohibition on aspirational wording. |
| Downstream product outcome | Gateway/Workbench were mentioned only indirectly. | Added mandatory slice to create/tighten paired Gateway and Workbench RFCs after manage contracts stabilize. |

---

## 2. Business Outcomes

RFC-0041 must deliver these outcomes.

1. **Scale discretionary portfolio operations**
   Portfolio managers can coordinate action across a PM book instead of running isolated
   single-portfolio analyses.
2. **Improve CIO implementation control**
   CIO and investment-control teams can see how model changes, house views, and campaigns affect
   mandates before trading begins.
3. **Reduce operational bottlenecks**
   Ready, pending-review, blocked, staged, handoff-ready, and failed items are visible in one
   governed workflow.
4. **Improve risk, liquidity, FX, and tax planning**
   Aggregate notional, turnover, cost, FX needs, cash/funding pressure, liquidity warnings,
   concentration warnings, and tax posture are derived from item evidence.
5. **Increase governance quality**
   Every selection, approval, staging, cancellation, retry, and handoff transition is
   actor-attributed and append-only.
6. **Support a premium command-center story**
   Gateway and Workbench can later show CIO/PM wave progress from real backend state, not UI-only
   summaries.

---

## 3. Goals and Non-Goals

### 3.1 Goals

1. Add `DpmRebalanceWave` as the manage-owned durable wave aggregate.
2. Add `DpmRebalanceWaveItem` as the item-level unit of source readiness, simulation, approval,
   staging, proof-pack, and handoff state.
3. Add `DpmCioModelChangeImpact` for source-backed affected-mandate analysis.
4. Identify affected mandates from model, risk profile, region, currency, PM book, trigger event,
   or explicit portfolio list.
5. Evaluate source readiness per wave item using authoritative source products.
6. Generate RFC-0039 construction alternatives for ready items only.
7. Generate or attach RFC-0040 proof packs for selected/approved items where source readiness and
   workflow state allow it.
8. Persist wave state, item state, events, aggregate metrics, lineage, supportability, and retention
   metadata.
9. Expose certified manage APIs for preview, create, source-check, simulate, select, approve,
   stage, handoff, inspect, search, and supportability.
10. Create or tighten Gateway and Workbench realization RFCs after manage contracts and live proof
    are stable.

### 3.2 Non-Goals

1. Actual OMS/EMS order execution.
2. Client consent workflows.
3. Core transaction booking or settlement posting.
4. Replacing `lotus-report` batch scheduling or report materialization.
5. Solving all portfolios as one global optimization problem. First-wave scope is coordinated
   orchestration with item-level construction and aggregate evidence.
6. Recomputing risk, performance, holdings, tax-lot, market-data, or source-readiness methodology
   inside `lotus-manage`.
7. Claiming full front-office product support before Gateway and Workbench RFCs are implemented and
   live-proven.

---

## 4. Architecture Direction

### 4.1 Manage-Owned Backend Authority

`lotus-manage` owns the wave aggregate, wave state machine, item workflow, approvals, staging,
handoff state, wave evidence, and supportability. It may call its own RFC-0038 mandate repository,
RFC-0039 construction alternatives, and RFC-0040 proof-pack authority. It must consume external
domain products only through certified source APIs or explicitly degraded source refs.

```mermaid
flowchart LR
    Trigger[CIO model change / PM campaign / explicit list] --> ManageWave[lotus-manage wave authority]
    Core[lotus-core source readiness and mandate binding] --> ManageWave
    ManageMandate[lotus-manage mandate twin and health] --> ManageWave
    Construction[lotus-manage RFC-0039 alternatives] --> ManageWave
    ProofPack[lotus-manage RFC-0040 proof packs] --> ManageWave
    Risk[lotus-risk risk posture] -. source-backed enrichment .-> ManageWave
    Performance[lotus-performance performance posture] -. source-backed enrichment .-> ManageWave
    ManageWave --> Gateway[lotus-gateway wave composition RFC]
    Gateway --> Workbench[lotus-workbench wave command center RFC]
```

### 4.2 Boundary Rules

1. `lotus-core` remains source authority for portfolio identity, mandate binding, holdings, market
   data coverage, instrument eligibility, tax lots, model binding, and source readiness.
2. `lotus-risk` remains authority for risk calculations and risk supportability.
3. `lotus-performance` remains authority for performance calculations and supportability.
4. `lotus-report`, `lotus-render`, and `lotus-archive` remain authorities for report output,
   rendering, archive metadata, retention, legal hold, and controlled document access.
5. `lotus-ai` remains authority for governed narrative/memo generation. Manage may provide bounded
   wave evidence input but must not generate AI narrative.
6. Gateway composes manage wave state for Workbench; it must not become wave authority.
7. Workbench consumes Gateway only; it must not call manage or raw domain services directly.

### 4.3 Enterprise Data Mesh Posture

Wave evidence must preserve product identity, source owner, source version, freshness, lineage,
supportability, and reason codes. If a required domain product is missing or unsupported, the item
or module must be `DEGRADED`, `BLOCKED`, or `NOT_SUPPORTED`; it must not be silently marked ready.

---

## 5. Source Map and Gap Policy

Implementation must begin with a source map and gap analysis. Each row must be classified as
`proven`, `already sufficient`, `must implement in owner`, `deferred with no support claim`, or
`not applicable`.

| Capability | Expected authority | Required for manage backend support | Missing-data behavior |
| --- | --- | --- | --- |
| Trigger identity and rationale | `lotus-manage` request or upstream CIO event source | yes | reject create if required trigger identity is absent |
| Portfolio identity and book membership | `lotus-core` | yes for source-backed selection | item `SOURCE_BLOCKED` or preview degraded |
| Mandate binding and model id | `lotus-core` + RFC-0038 mandate twin | yes | item `SOURCE_BLOCKED`; no synthetic mandate |
| Model-change affected portfolios | `lotus-core` model binding and/or approved trigger manifest | yes for model-change trigger support | model-change trigger remains `DEGRADED` or not promoted |
| Source readiness | `lotus-core` RFC-0087/source-readiness products | yes | item `SOURCE_BLOCKED` with owner/reason |
| Mandate health/exceptions | `lotus-manage` RFC-0038 | yes | item `REVIEW_REQUIRED` or `SOURCE_BLOCKED` depending on missing evidence |
| Construction alternatives | `lotus-manage` RFC-0039 | yes for simulation support | item `SIMULATION_BLOCKED` |
| Proof pack | `lotus-manage` RFC-0040 | yes before proof-pack handoff claim | item handoff `DEGRADED` or blocked |
| Risk enrichment | `lotus-risk` | required for risk-aware aggregate claim | risk module degraded; wave may continue if non-blocking |
| Performance enrichment | `lotus-performance` | required for performance-impact claim | performance module degraded; wave may continue if non-blocking |
| Report materialization | `lotus-report`/`lotus-render`/`lotus-archive` | not manage backend MVP | no report-output claim |
| AI memo | `lotus-ai` | not manage backend MVP | no AI memo claim |

No source-data gap may be hidden in manage-local placeholders. If the RFC business outcome depends
on a missing source product, the implementation must either add it in the owning app or explicitly
defer that feature from supported status.

---

## 6. Trigger Contract

Supported trigger types:

1. `CIO_MODEL_CHANGE`
2. `TACTICAL_HOUSE_VIEW`
3. `PM_BOOK_REVIEW`
4. `RISK_BREACH_REMEDIATION`
5. `CASH_DRAG_CAMPAIGN`
6. `TAX_YEAR_END_REVIEW`
7. `ESG_RESTRICTION_UPDATE`
8. `EXPLICIT_PORTFOLIO_LIST`

Every trigger must record:

1. `trigger_id`
2. `trigger_type`
3. `source_system`
4. `source_event_id`
5. `effective_date`
6. `as_of_date`
7. `created_by`
8. `rationale`
9. `affected_model_ids`
10. `selection_criteria`
11. `source_refs`
12. `correlation_id`

First implementation supported only `EXPLICIT_PORTFOLIO_LIST`. Later source-owner slices promoted
`PM_BOOK_REVIEW` through lotus-core `PortfolioManagerBookMembership:v1` and `CIO_MODEL_CHANGE`
through lotus-core `CioModelChangeAffectedCohort:v1`. Other trigger types remain unsupported until
an owning source product or approved manifest governance is implemented and proven. Unsupported
trigger types must be rejected or returned as `NOT_SUPPORTED`; they must not appear as supported
features.

Promoted source-owned trigger selectors are intentionally narrow: `PM_BOOK_REVIEW` requires
`portfolio_manager_id`, while `CIO_MODEL_CHANGE` requires `model_portfolio_id`. Both reject
caller-supplied portfolio lists so cohort authority remains in the owning source product.

---

## 7. State Machine

### 7.1 Wave States

1. `DRAFT`
2. `SOURCE_CHECK`
3. `SOURCE_CHECKED`
4. `SIMULATING`
5. `SIMULATED`
6. `REVIEWING`
7. `APPROVED`
8. `STAGED`
9. `HANDOFF_READY`
10. `HANDOFF_SENT`
11. `PARTIALLY_COMPLETED`
12. `COMPLETED`
13. `CANCELLED`
14. `FAILED`

### 7.2 Wave Item States

1. `PENDING_SOURCE_CHECK`
2. `SOURCE_BLOCKED`
3. `READY_TO_SIMULATE`
4. `SIMULATION_BLOCKED`
5. `ALTERNATIVES_READY`
6. `REVIEW_REQUIRED`
7. `SELECTED`
8. `APPROVED`
9. `STAGED`
10. `HANDOFF_READY`
11. `HANDOFF_SENT`
12. `COMPLETED`
13. `CANCELLED`
14. `FAILED`

### 7.3 Transition Rules

1. Every transition is append-only and actor-attributed.
2. Every command uses idempotency and correlation identifiers.
3. Concurrent updates use optimistic versioning or equivalent repository-level guardrails.
4. Blocked, failed, and cancelled items do not fail the whole wave unless all eligible items fail.
5. A wave may be `PARTIALLY_COMPLETED` only when at least one item completed and at least one item
   remains blocked, failed, or cancelled.
6. `HANDOFF_SENT` records handoff evidence only; it does not claim external execution.
7. Item state cannot move from blocked to ready without a new source-check event or explicit
   remediation event.
8. State-machine implementation must be pure and unit-tested independently from API handlers.

---

## 8. Domain Models

### 8.1 `DpmRebalanceWave`

Required fields:

1. `wave_id`
2. `wave_version`
3. `state`
4. `trigger`
5. `as_of_date`
6. `created_at`
7. `created_by`
8. `correlation_id`
9. `version`
10. `items`
11. `aggregate_metrics`
12. `events`
13. `handoff_refs`
14. `retention_policy`

PM-book, portfolio-manager, and CIO model-change cohort fields are intentionally not required wave
aggregate fields in the implemented RFC-0041 manage backend. They remain deferred until the owning
source products and downstream composition routes are implemented and proven.

### 8.2 `DpmRebalanceWaveItem`

Required fields:

1. `wave_item_id`
2. `portfolio_id`
3. `mandate_id`
4. `model_portfolio_id`
5. `state`
6. `reason_codes`
7. `source_refs`
8. `alternative_set_id`
9. `selected_alternative_id`
10. `proof_pack_id`
11. `diagnostics`

### 8.3 `DpmCioModelChangeImpact`

Required fields:

1. `impact_id`
2. `model_change_event_id`
3. `affected_model_ids`
4. `affected_portfolio_count`
5. `affected_mandate_count`
6. `ready_count`
7. `source_blocked_count`
8. `policy_blocked_count`
9. `approval_required_count`
10. `estimated_trade_count`
11. `estimated_turnover_base`
12. `estimated_cost_base`
13. `estimated_fx_by_currency`
14. `top_exposures`
15. `source_refs`
16. `lineage`

### 8.4 `DpmRebalanceWaveEvent`

Every event must include:

1. `event_id`
2. `wave_id`
3. optional `wave_item_id`
4. `event_type`
5. `from_state`
6. `to_state`
7. `actor`
8. `reason_code`
9. `comment`
10. `command_id`
11. `correlation_id`
12. `source_refs`
13. `created_at`

---

## 9. API Surface

All endpoints are under the DPM rebalance wave tag and require full OpenAPI certification.

| Endpoint | Purpose |
| --- | --- |
| `POST /api/v1/rebalance/waves/preview` | Estimate affected portfolios without durable wave creation. |
| `POST /api/v1/rebalance/waves` | Create a durable draft wave from trigger and selection criteria. |
| `GET /api/v1/rebalance/waves` | Search waves by state, trigger type, as-of date, derived supportability, limit, and offset. Book and PM filters are deferred until an owning source product exists. |
| `GET /api/v1/rebalance/waves/{wave_id}` | Retrieve wave detail, summary metrics, items, source refs, and latest supportability. |
| `GET /api/v1/rebalance/waves/{wave_id}/items` | Retrieve item list with state, source readiness, selection, proof-pack, and handoff posture. |
| `POST /api/v1/rebalance/waves/{wave_id}/source-check` | Evaluate source readiness and classify each item. |
| `POST /api/v1/rebalance/waves/{wave_id}/simulate` | Generate alternatives for ready items and preserve blocked/review-required item reasons. |
| `POST /api/v1/rebalance/waves/{wave_id}/items/{wave_item_id}/select` | Select a construction alternative with actor, reason code, and comment. |
| `POST /api/v1/rebalance/waves/{wave_id}/approve` | Approve eligible items or the whole wave without approving blocked items. |
| `POST /api/v1/rebalance/waves/{wave_id}/stage` | Stage approved items for operations handoff. |
| `POST /api/v1/rebalance/waves/{wave_id}/handoff` | Create handoff evidence; do not execute externally. |
| `POST /api/v1/rebalance/waves/{wave_id}/cancel` | Cancel draft/review/staged waves where cancellation is valid. |
| `GET /api/v1/rebalance/waves/{wave_id}/supportability` | Operator supportability, degraded reasons, source owners, and remediation hints. |
| `GET /api/v1/rebalance/waves/{wave_id}/proof-pack` | Wave-level proof-pack/handoff posture and linked item proof-pack refs. |

No alias routes are allowed. If implementation finds duplicate pre-live routes, remove or reject
them before support promotion.

---

## 10. Persistence, Immutability, and Retention

Required tables:

1. `dpm_rebalance_waves`
2. `dpm_rebalance_wave_idempotency`
3. `dpm_rebalance_wave_events`

Wave items, handoff refs, aggregate metrics, and supportability posture are persisted inside the
immutable `wave_json` body for the current manage backend implementation. Automatic CIO
model-change impact persistence is not implemented because automatic CIO model-change cohort
discovery remains deferred with no supported-feature claim.

Required indexes:

1. `(state, created_at desc)`
2. unique `(correlation_id)`
3. idempotency key primary key for command replay/conflict detection
4. `(wave_id, created_at asc)` on wave events

`trigger_type` and `as_of_date` are stored as queryable wave columns and supported by repository
filters. PM-book and portfolio-manager indexes must not be added or documented until the owning
book/cohort source product exists and the API promotes that search posture.

Retention:

1. completed waves: 7 years,
2. cancelled drafts with no approvals: 1 year,
3. failed waves with operational incident refs: 7 years,
4. wave events and handoff refs inherit the parent wave retention.

Repository implementation must support in-memory and PostgreSQL parity with focused tests. Events
and handoff refs are append-only.

---

## 11. Aggregate Metrics

All aggregate metrics must be derived from item evidence and reproducible.

Required first-wave metrics:

1. portfolio count,
2. mandate count,
3. ready count,
4. source-blocked count,
5. simulation-blocked count,
6. review-required count,
7. selected count,
8. approved count,
9. staged count,
10. handoff-ready count,
11. estimated trade count,
12. estimated turnover,
13. estimated cost,
14. estimated realized tax,
15. FX buy/sell by currency,
16. top instruments by notional,
17. liquidity warnings,
18. risk warnings,
19. source readiness coverage,
20. proof-pack coverage.

Metric inputs, item refs, rounding policy, currency, as-of date, and unavailable source reasons must
be visible in evidence.

---

## 12. Implementation Slices

Work strictly slice by slice. Do not move to the next slice until the current slice is implemented,
validated, reviewed, documented, and in a solid state.

### Slice 0 - Critical Source Map and Execution Design

Scope:

1. produce `docs/rfcs/RFC-0041-source-map-and-gap-analysis.md`,
2. verify exact existing source products, manage modules, repositories, migrations, APIs, and tests,
3. classify every source dependency and feature claim,
4. define first-wave trigger subset and unsupported trigger posture,
5. finalize state-machine transition matrix,
6. decide implementation branch naming and evidence-output path.

Acceptance:

1. no source-data dependency is ambiguous,
2. every missing capability is assigned to the owning app or deferred without a supported claim,
3. first implementation scope is small enough to prove end to end,
4. implementation does not begin until this slice is reviewed.

### Slice 1 - Platform Automation and Scaffolding Improvement

Scope:

1. identify gaps in `lotus-platform` automation that RFC-0041 would otherwise solve locally,
2. improve platform automation or app scaffolding where gaps are cross-cutting,
3. cover API certification pattern, Swagger quality, observability, health endpoints, structured
   logging, error handling, test scaffolding, CI defaults, documentation scaffolding, governance
   hooks, evidence manifests, and workflow/state-machine starter patterns where applicable,
4. ensure improvements benefit future Lotus apps, not only `lotus-manage`,
5. record a no-change decision only when the platform baseline is already sufficient.

Acceptance:

1. platform/scaffolding gaps are fixed in `lotus-platform` or explicitly classified,
2. no manage-local platform workaround is introduced,
3. evidence links to platform PRs/commits or a defensible no-change decision.

### Slice 2 - Cleanup and Structure

Scope:

1. remove dead code and stale DPM wave-adjacent docs encountered during source review,
2. keep wave orchestration separate from alternative construction and proof-pack generation,
3. improve repository structure only where it materially improves maintainability,
4. reduce duplicate docs and move long-lived operator/product material to repo-local `wiki/`,
5. preserve concise repo docs and avoid duplicating the full RFC in wiki.

Acceptance:

1. no stale wave/proof/alternative terminology creates wrong ownership,
2. wiki source reflects current truth where implementation changes product/operator material,
3. `Sync-RepoWikis.ps1 -CheckOnly -Repository lotus-manage` is run before merge; after merge wiki
   publication is required if wiki source changes.

### Slice 3 - Wave Domain, State Machine, and Repository

Scope:

1. implement domain models,
2. implement pure transition guards,
3. implement aggregate metric primitives,
4. implement repository contract,
5. implement in-memory and PostgreSQL persistence plus migrations,
6. implement append-only event and handoff-ref persistence.

Acceptance:

1. state machine tests cover every allowed and rejected transition,
2. repository tests prove immutability, idempotency, optimistic concurrency, event ordering, and
   Postgres parity,
3. migrations pass smoke validation.

### Slice 4 - Affected Portfolio Preview and Wave Creation

Scope:

1. implement preview without durable wave creation,
2. implement durable wave creation,
3. support first-wave trigger subset and source-backed candidate selection,
4. return empty, partial-source, and blocked states truthfully,
5. preserve source refs and lineage.

Acceptance:

1. preview and create APIs are certified,
2. explicit list and at least one source-backed selection path are tested,
3. unsupported trigger types cannot be promoted as supported,
4. OpenAPI includes full request/response/error examples.

### Slice 5 - Source Check and Item Classification

Scope:

1. run source readiness per item,
2. attach core, mandate twin, mandate health, and source-readiness refs,
3. classify ready, pending-review, degraded, and blocked item states,
4. update wave-level source summary and supportability.

Acceptance:

1. mixed ready/pending/blocked wave is proven,
2. missing or stale source evidence is visible with source owner and reason code,
3. source-check is idempotent and safe to retry,
4. no item becomes ready from a caller-supplied id alone when required source evidence is missing.

### Slice 6 - Simulation, Alternative Selection, and Proof-Pack Linkage

Scope:

1. call RFC-0039 construction alternatives for ready items,
2. preserve blocked/review-required item reasons,
3. select alternatives at item level with actor/rationale,
4. generate or attach RFC-0040 proof packs when selection and source readiness permit,
5. compute aggregate metrics from item evidence.

Acceptance:

1. alternatives are not generated for source-blocked items,
2. selected alternatives remain linked after reload,
3. proof-pack refs are source-honest and degrade when proof-pack generation is not available,
4. aggregate metric reconciliation is tested.

### Slice 7 - Approval, Staging, and Operations Handoff

Scope:

1. approve wave or selected eligible items,
2. stage approved items,
3. create operations handoff package,
4. preserve no-external-execution boundary,
5. record actor attribution, reason codes, comments, and support refs.

Acceptance:

1. blocked items cannot be approved or staged,
2. repeated commands are idempotent,
3. handoff evidence is durable and append-only,
4. API errors are precise and tested.

### Slice 8 - Supportability, Observability, and Operator Diagnostics

Scope:

1. implement wave supportability endpoint,
2. add bounded structured logs and metrics,
3. expose safe operator diagnostics without raw payloads, portfolio/client identifiers in metric
   labels, secrets, request bodies, response bodies, or trace details,
4. document operational troubleshooting.

Acceptance:

1. degraded states have source owner, reason, remediation route, and support reference,
2. observability tests prove bounded labels and no sensitive content,
3. diagnostics are product-safe and operator-useful.

### Slice 9 - Gateway and Workbench Realization RFC Slice

Scope:

1. after manage contracts and live proof are stable, create or tighten paired RFCs in
   `lotus-gateway` and `lotus-workbench`,
2. if no suitable active RFC exists, add new downstream RFCs rather than hiding product realization
   inside manage; if an active command-center RFC already exists, add an RFC-0041 wave addendum
   with explicit route/state/evidence contracts,
3. define Gateway wave-composition endpoints that consume manage wave APIs without reconstructing
   state,
4. define Workbench wave-command-center surfaces that consume Gateway only,
5. include diagrams, action eligibility, degraded states, proof-pack/report/AI posture, and
   canonical front-office evidence expectations,
6. record downstream supported-feature promotion rules.

Gateway direction:

1. Gateway owns Workbench-facing wave composition, not wave authority.
2. Gateway consumes manage wave preview/detail/item/source-check/simulate/approve/stage/handoff
   posture through typed clients.
3. Gateway composes risk/performance/report/archive/AI posture only from owning services.
4. Gateway returns module-level `ready`, `degraded`, `blocked`, `not_supported`, `unavailable`, and
   `error` states.
5. Gateway must not create aliases, recompute aggregate metrics, or infer item readiness.

Workbench direction:

1. Workbench exposes a wave command center inside the DPM operating cockpit.
2. Workbench uses BFF wrappers over Gateway only.
3. Workbench renders wave list, wave detail, item matrix, mixed-readiness states, approval/staging
   rail, evidence drawer, proof-pack links, and operations handoff posture.
4. Workbench does not calculate readiness, alternatives, proof-pack state, aggregate metrics, or
   report/AI posture.
5. Browser validation, accessibility, visual checks, and canonical `PB_SG_GLOBAL_BAL_001` evidence
   are required before UI support promotion.

Acceptance:

1. Gateway and Workbench RFCs exist or are tightened and reviewed,
2. downstream RFCs agree on route names, state names, action eligibility, supportability taxonomy,
   and proof requirements,
3. manage RFC does not claim full product realization until downstream implementation is proven.

### Slice 10 - Implementation Proof

Scope:

1. prove implementation end to end against this RFC,
2. run live canonical manage runtime with durable persistence,
3. capture machine-readable evidence under `output/rfc0041-wave-proof/<timestamp>/`,
4. critically review evidence for gaps, inconsistencies, weak states, loose ends, and unsupported
   claims,
5. iterate until the implementation is genuinely gold standard.

Required evidence:

1. preview request/response,
2. create wave request/response,
3. source-check request/response with one ready, one pending-review/degraded, and one blocked item,
4. simulate response,
5. alternative selection response,
6. proof-pack linkage evidence,
7. approval response,
8. stage response,
9. handoff response,
10. retrieve/search/supportability responses,
11. aggregate metric reconciliation,
12. OpenAPI/API certification summary,
13. critical-review JSON/Markdown with fixes made.

Slice 10 result:

1. live proof completed under `output/rfc0041-wave-proof/20260504-231914/`,
2. canonical manage runtime was started through `scripts/Start-CanonicalManage.ps1` with
   Postgres-backed manage repositories,
3. proof seeded ready, degraded, pending-review, and blocked mandate postures through the mandate
   health API,
4. proof drove preview, create, source-check, simulate, select/proof-pack, approve, stage, handoff,
   cancel, retrieve, item-list, proof-pack-posture, supportability, and search routes over live
   HTTP,
5. aggregate reconciliation passed with one `HANDOFF_READY`, one `SOURCE_DEGRADED`, one
   `REVIEW_REQUIRED`, and one `SOURCE_BLOCKED` item,
6. OpenAPI certification for 13 RFC-0041 wave operations passed with no missing or weak routes,
7. critical review passed and explicitly preserved the downstream Gateway/Workbench boundary,
8. live validation found and fixed two production-readiness issues:
   - RFC-0039 construction delegation now records method-specific run correlation ids so Postgres
     run supportability does not collide during multi-method alternative generation,
   - mixed waves with simulated eligible items plus degraded/review-required exceptions now roll up
     to `PARTIALLY_SIMULATED`, allowing approval-with-exceptions instead of failing the state
     machine.
9. a stale RFC/API gap was closed by implementing `POST /api/v1/rebalance/waves/{wave_id}/cancel`
   with actor-attributed cancellation evidence and no external execution claim.

The latest live proof result is `passed`. Slice 11 hardening and Slice 12 closure are complete, so
RFC-0041 is `DONE` for the manage-owned explicit portfolio-list wave backend authority.

### Slice 11 - Second-Last Hardening and Review

Scope:

1. perform a proper code review of the full implementation,
2. remove dead code, duplicated transition logic, brittle tests, and stale docs,
3. verify API certification pattern compliance,
4. verify platform governance and enterprise data mesh standards,
5. certify every API endpoint and every returned figure,
6. verify Swagger/OpenAPI quality,
7. verify error handling and degraded-state behavior,
8. verify tests are meaningful and not shallow,
9. make final quality improvements before closure.

Swagger/OpenAPI must include:

1. correct grouping and tags,
2. clear what/when/how endpoint guidance,
3. full request and response examples,
4. full degraded/blocked/error examples,
5. every attribute description,
6. every attribute type,
7. every attribute example value,
8. canonical vocabulary values,
9. no aliases.

Acceptance:

1. local focused and repo-native gates pass,
2. OpenAPI, vocabulary, no-alias, migration, repository, API, integration, and degraded-state tests
   are green,
3. review findings are fixed or explicitly tracked with no unsupported feature claim.

Slice 11 result:

1. hardening review found and fixed RFC/API contract drift: `GET /api/v1/rebalance/waves` is now
   documented as filtering only by implemented fields (`state`, `trigger_type`, `as_of_date`,
   `supportability_state`, `limit`, `offset`), while PM-book and PM filters remain deferred,
2. stale `MANUAL_PORTFOLIO_LIST` first-wave wording was corrected to the implemented
   `EXPLICIT_PORTFOLIO_LIST` trigger contract,
3. the supported-features ledger now distinguishes implementation-backed explicit-list wave
   support from deferred CIO model-change/PM-book discovery and downstream Gateway/Workbench
   product support,
4. source-readiness tests now cover missing twins, missing/stale health, blocked, degraded,
   review-required, ready, and missing-core-lineage-record behavior,
5. selection conflict hardening now verifies optimistic-lock failures are surfaced as
   `DPM_WAVE_VERSION_CONFLICT` during alternative selection,
6. endpoint certification, OpenAPI quality, API vocabulary, documentation guardrails, and the
   repo-native `make check` gate passed after the hardening changes.

No unsupported feature claim was promoted during Slice 11. Slice 12 final closure records the
gold-pass assessment, final docs/wiki/context posture, PR merge requirement, wiki publication
requirement, and branch-hygiene requirement.

### Slice 12 - Final Closure

Scope:

1. update README, RFC index, repo context, supported-features, wiki source, and runbooks,
2. publish wiki after merge when wiki source changes,
3. add final gold-pass assessment to this RFC,
4. record local and GitHub evidence,
5. consciously review whether Lotus skills, guidance, documentation, or agent context should be
   improved for future work,
6. update central or repo-local context only when truth changed,
7. complete PR, merge, branch cleanup, and clean worktree.

Acceptance:

1. supported-features contains only implementation-backed claims,
2. wiki is published and check-only reports zero drift,
3. branch and remote hygiene are clean,
4. final RFC status is updated only after implementation and proof are complete,
5. skills/context decision is explicitly recorded as `updated`, `no change needed`, or
   `follow-up required`.

Slice 12 result:

1. README, RFC index, repository context, supported-features, wiki source, and endpoint
   certification pages reflect the final implementation-backed manage backend posture.
2. The final gold-pass assessment below is complete and evidence-backed.
3. Skills/context/guidance decision: `no change needed`. The existing Lotus backend delivery,
   endpoint certification, README/wiki governance, pre-merge gate, and front-office runtime skills
   were sufficient for RFC-0041. No durable routing change, AGENTS.md update, or central context
   change is required by this RFC because no new platform-wide operating pattern was introduced in
   Slice 12.
4. Final closure does not promote Gateway/Workbench product support, PM-book automatic discovery, or
   CIO model-change cohort discovery. Those remain deferred to the owning downstream/source RFCs.

---

## 13. Testing Requirements

Tests must validate behavior and business risk, not only status codes.

Required coverage:

1. source map and unsupported trigger posture,
2. state-machine allowed/rejected transitions,
3. idempotency and optimistic concurrency,
4. affected portfolio selection,
5. preview empty/partial/blocked states,
6. source-check mixed readiness,
7. item simulation and skip behavior for blocked items,
8. aggregate metric reconciliation from item evidence,
9. alternative selection and persistence,
10. proof-pack linkage and degraded proof-pack posture,
11. approval/staging/handoff guards,
12. event append-only ordering,
13. repository contract and PostgreSQL parity,
14. API success and error paths,
15. OpenAPI examples and field descriptions,
16. no-alias and API vocabulary gates,
17. observability and no-sensitive-label tests,
18. documentation current-state guardrails where applicable,
19. live canonical wave proof.

---

## 14. API Certification and Swagger Standard

Every wave endpoint must satisfy:

1. DPM rebalance wave route grouping,
2. precise summary and description,
3. what/when/how guidance,
4. full request examples,
5. full response examples,
6. mixed-readiness examples,
7. degraded, blocked, not-supported, conflict, and validation-error examples,
8. field-level descriptions and example values,
9. canonical state vocabulary,
10. no aliases,
11. generated API vocabulary inventory validation,
12. endpoint certification matrix inclusion.

---

## 15. Supported-Features Ledger

| Feature | Support state before implementation | Promotion rule |
| --- | --- | --- |
| Wave preview | Supported for `EXPLICIT_PORTFOLIO_LIST` | Implemented and live-proven with source-backed candidates and blocked caller-only portfolio evidence. |
| Durable rebalance wave aggregate | Supported for `EXPLICIT_PORTFOLIO_LIST` | Implemented with persistence, state machine, events, retention policy, repository parity, idempotency, and live retrieval proof. |
| CIO model-change impact | Supported for source-owned affected-cohort discovery | Implemented through lotus-core `CioModelChangeAffectedCohort:v1` and manage `CIO_MODEL_CHANGE` preview/create. Downstream Gateway/Workbench rendering remains a separate support claim. |
| Wave source check | Supported | Implemented with item-level readiness, source refs, blocked/degraded/review reasons, and mixed-readiness proof. |
| Wave simulation | Supported for source-ready items | Implemented through RFC-0039 alternatives for ready items while blocked, degraded, and review-required items remain visible. |
| Alternative selection | Supported | Implemented with actor/rationale selection, proof-pack generation option, durable reload, and optimistic-lock tests. |
| Proof-pack linkage | Supported | Implemented through RFC-0040 proof-pack generation or degraded linkage; no local proof-pack clone exists in wave logic. |
| Wave approval and staging | Supported | Implemented with actor attribution, state guards, idempotency, blocked-item rejection, and no-eligible tests. |
| Operations handoff | Supported as internal pre-execution evidence | Implemented with durable append-only handoff evidence and explicit no-external-execution claims. |
| Wave aggregate metrics | Supported | Implemented from item evidence with live aggregate reconciliation proof. |
| Wave supportability and diagnostics | Supported | Implemented with product-safe diagnostics, bounded metrics/logs, and degraded-state tests. |
| Gateway wave composition | Not supported in manage RFC | Promote only in Gateway RFC after it consumes manage wave APIs without reconstruction and passes Gateway proof. |
| Workbench wave command center | Not supported in manage RFC | Promote only in Workbench RFC after Gateway-backed browser, accessibility, visual, and canonical evidence pass. |

---

## 16. Documentation and Wiki Expectations

Documentation is part of the product output.

Required outputs during implementation:

1. RFC slice evidence docs,
2. README updates for supported wave APIs and run commands,
3. repository context updates when capability truth changes,
4. endpoint certification docs,
5. supported-features updates with implementation-backed wording only,
6. wiki updates with audience-aware wave material,
7. diagrams for wave lifecycle, integration flow, and PM/CIO/operations journey,
8. final gold-pass assessment.

Wiki content should be useful to developers, business users, operations, sales/pre-sales, and
client demos. It should summarize implementation-backed behavior and link to deeper RFC evidence
without duplicating the full RFC.

---

## 17. Risks and Controls

| Risk | Control |
| --- | --- |
| Manage becomes a cross-domain analytics clone | Source map, domain authority rules, and degraded states for missing risk/performance data. |
| Wave state machine becomes brittle | Pure transition model, exhaustive tests, idempotency, optimistic concurrency, append-only events. |
| Blocked items fail the whole wave | Partial-completion semantics and item-level state. |
| Aggregate metrics are non-reproducible | Item-evidence reconciliation and deterministic rounding/currency policy. |
| Gateway or Workbench reconstructs wave truth | Mandatory downstream RFC slice with no-reconstruction and Gateway-only UI rules. |
| Swagger is shallow | Endpoint certification, field examples, degraded/error examples, and API vocabulary gates. |
| Docs overstate support | Supported-feature promotion only after live proof and wiki publication. |
| Platform gaps are fixed locally | Platform automation slice requires platform-level fixes or explicit no-change decision. |
| Sensitive content leaks through diagnostics or metrics | Bounded diagnostics, no raw payloads, no portfolio/client/document/trace labels, tests. |
| CI drifts after local proof | GitHub Feature Lane and PR Merge Gate monitoring before merge. |

---

## 18. Definition of Done

RFC-0041 is complete only when:

1. source map and gap analysis are complete,
2. platform/scaffolding gaps are fixed or consciously classified,
3. wave domain, state machine, persistence, events, and retention are implemented,
4. preview/create/source-check/simulate/select/approve/stage/handoff/search/supportability APIs are
   implemented and certified,
5. every wave item state is source-backed or truthfully degraded/blocked/not-supported,
6. aggregate metrics reconcile to item evidence,
7. proof-pack linkage is source-honest,
8. safe supportability and observability are implemented,
9. Gateway and Workbench realization RFCs are created or tightened after manage contracts stabilize,
10. live evidence exists, has been critically reviewed, and all material gaps are fixed,
11. second-last hardening review is complete,
12. README/wiki/supported-features/context are truthful,
13. local and GitHub checks are green,
14. wiki is published after merge when source changes,
15. final skills/context/guidance decision is recorded,
16. branch and remote hygiene are clean.

---

## 19. Final Gold-Pass Assessment

| Assessment Area | Final Result |
| --- | --- |
| What was truly completed | `lotus-manage` now owns an implementation-backed explicit portfolio-list rebalance-wave backend authority: preview, durable create, source-check, simulate, select, proof-pack linkage, approve, stage, handoff, cancel, search, detail, item list, proof-pack posture, and supportability. |
| Quality improvements made | Slice 10 added live proof and fixed production defects found under Postgres-backed execution. Slice 11 removed RFC/API contract drift, tightened trigger wording, and added source-readiness and selection-conflict hardening tests. |
| Debt removed | Removed misleading RFC claims around unsupported book/PM search filters and stale `MANUAL_PORTFOLIO_LIST` wording. Avoided manage-local clones of RFC-0039 construction and RFC-0040 proof-pack methodology. |
| Platform/scaffold improvements | Slice 1 improved `lotus-platform` RFC evidence scaffolding through PR #296 (`47d3c7f`) so future state-machine/API-heavy RFCs start with stronger evidence manifests. |
| Cross-app changes and evidence | Gateway RFC-0098 and Workbench RFC-0098 received RFC-0041 wave-realization addenda through `lotus-gateway` PR #183 (`e0e4b1b`) and `lotus-workbench` PR #143 (`c4888d4`). Those addenda define downstream integration without promoting product support before implementation. |
| APIs certified | 13 RFC-0041 wave operations are OpenAPI-certified with route grouping, examples, request/response schemas, error posture, and vocabulary inventory validation. |
| Wave states and sections proven | Live proof validated mixed `SOURCE_READY`, `SOURCE_DEGRADED`, `REVIEW_REQUIRED`, `SOURCE_BLOCKED`, `PARTIALLY_SIMULATED`, approval-with-exceptions, `STAGED`, `HANDOFF_READY`, and `CANCELLED` behavior with aggregate reconciliation. |
| Report/AI/proof-pack handoff posture | Wave selection delegates proof-pack generation to RFC-0040 and exposes proof-pack/handoff posture. Report materialization and AI memo generation remain downstream/owning-app concerns with no unsupported claim. |
| Live evidence reviewed | Machine-readable proof exists under `output/rfc0041-wave-proof/20260504-231914/`; `critical-review.json` and `critical-review.md` passed after fixing the live-found gaps. |
| Gateway/Workbench realization RFC result | Downstream realization RFC addenda are complete; implementation and canonical UI proof remain future downstream work and are not claimed as supported by `lotus-manage`. |
| Documentation/wiki result | README, RFC index, repository context, source-map, supported-features, endpoint certification wiki, RFC index wiki, and roadmap wiki are aligned to implementation truth. Wiki publication is required after the Slice 12 PR merges. |
| Skills/context/guidance decision | `no change needed`; current Lotus skills and agent context were sufficient and no new reusable execution rule emerged from final closure. |
| Tests and evidence | Local gates passed: focused hardening tests, OpenAPI certification/docs tests, OpenAPI quality gate, API vocabulary validation, `make check`, and full coverage gate at 99.17%. GitHub PR gates must pass before merge. |
| Gold-standard conclusion | RFC-0041 has reached the expected manage-owned backend gold standard for explicit portfolio-list rebalance waves plus source-owned `PM_BOOK_REVIEW` and `CIO_MODEL_CHANGE` cohort discovery. Tactical house-view, risk-event, campaign discovery, external OMS execution, and downstream UI product rendering remain separate support claims. |
