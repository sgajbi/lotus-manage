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

Wiki decision for this first ledger slice:

The existing `wiki/Supported-Features.md`, `wiki/RFC-Index.md`, and `wiki/Roadmap.md` already state
the RFC-0041 supported boundary and the major unpromoted capabilities. This ledger is a repo-local
planning/control artifact for follow-up sequencing, so no additional wiki source change is required
for this slice. If this ledger later becomes the public cross-RFC backlog used for product planning
or client roadmap discussion, add a wiki page and sidebar link in the same PR.

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

