# RFC-0041 Source Map And Gap Analysis

This document is the Slice 0 evidence map for RFC-0041. It records the current
implementation foundations, source-data dependencies, trigger support posture, state-machine
decision, cross-app gaps, branch/evidence conventions, and review gate that must be true before
rebalance-wave implementation begins.

The governing rule is strict: no wave item, aggregate metric, trigger cohort, readiness state,
approval, staging action, handoff, Gateway surface, or Workbench claim may be marked supported
unless it is backed by owning-service truth or deterministic `lotus-manage` state. Missing source
truth must remain visible as `DEGRADED`, `BLOCKED`, `NOT_SUPPORTED`, or `PENDING_REVIEW` with
owner and reason codes.

## Slice 0 Result

| Slice 0 requirement | Result |
| --- | --- |
| Existing source products, manage modules, repositories, migrations, APIs, and tests reviewed | Reviewed current `lotus-manage` RFC-0038 mandate, RFC-0039 construction, RFC-0040 proof-pack, run-support, workflow, source-sourcing, domain-data-product, telemetry, migration, RFC, and wiki surfaces. Reviewed relevant `lotus-core` RFC-0087 source products and portfolio query evidence. |
| Every source dependency and feature claim classified | Classified below as `already sufficient`, `proven`, `must implement in owner`, `deferred with no support claim`, or `not applicable`. |
| First-wave trigger subset defined | First implementation scope is explicit portfolio-list waves only, with optional supplied affected-portfolio manifests for CIO/PM campaigns. Full PM-book discovery and full CIO model-change impact discovery are deferred until an owning source product or certified cohort query exists. |
| Unsupported trigger posture defined | Unsupported triggers must reject create/preview with `NOT_SUPPORTED_TRIGGER` or produce a degraded preview with no supported-feature claim, depending on endpoint semantics. They must not silently fall back to all portfolios, sample data, local hardcoded lists, or UI-only filters. |
| State-machine transition matrix finalized | The Slice 0 transition matrix below is the implementation contract for Slice 3 and later API guards. |
| Branch and evidence-output path decided | Implementation branch is `feat/rfc0041-implementation`; live evidence will be written under `output/rfc0041-wave-proof/<timestamp>/`. |
| Implementation review gate recorded | Product implementation must not begin until this source map, RFC metadata, RFC index, and guardrail tests are committed and green. |

## Reviewed Current Manage Foundations

| Foundation | Current implementation evidence | RFC-0041 reuse posture |
| --- | --- | --- |
| Stateful core sourcing | `src/infrastructure/core_sourcing/client.py`, `src/core/dpm_source_context.py` | Reuse per-portfolio source-product client and typed DTOs for mandate binding, model targets, eligibility, tax lots, market coverage, and portfolio snapshot. Add wave-specific source readiness only where contracts are already certified. |
| RFC-0038 mandate twin and health | `src/core/mandates.py`, `src/core/mandate_repository.py`, `src/api/services/mandate_service.py`, `src/api/routers/mandates.py`, `src/api/routers/monitoring.py` | Reuse mandate identity, health, exceptions, review posture, source gaps, and command-center summary evidence for item readiness and pending-review decisions. |
| RFC-0039 construction alternatives | `src/core/construction/`, `src/api/services/construction_service.py`, `src/api/routers/construction.py`, migration `0005_construction_alternatives.sql` | Reuse generation, persistence, method status, selection, idempotency, and run-support recording. Wave simulation must call this authority for ready items rather than cloning construction logic. |
| RFC-0040 proof-pack authority | `src/api/services/proof_pack_service.py`, `src/api/routers/proof_packs.py`, migration `0006_pre_trade_proof_packs.sql` | Reuse immutable proof-pack generation, section states, hashes, lineage, Markdown, report input, and AI evidence input. Wave proof-pack linkage must attach or generate proof packs through this authority. |
| Workflow and run supportability | `src/core/common/workflow_gates.py`, `src/core/rebalance_runs/`, `src/api/routers/rebalance_runs.py` | Reuse actor-attributed review decisions, lineage, run artifacts, and supportability concepts where appropriate; add wave-specific events because wave state is a new aggregate. |
| Existing API composition | `src/api/main.py`, `src/api/routers/integration_capabilities.py` | Add wave router only after domain, repository, and service contracts are stable. Capability publication must remain disabled until implementation-backed support exists. |
| Persistence baseline | `src/infrastructure/postgres_migrations/dpm/0001_baseline.sql` through `0006_pre_trade_proof_packs.sql` | Add a new wave migration later, expected as `0007_rebalance_waves.sql`, with repository parity and migration smoke tests. |
| Domain-product declarations | `contracts/domain-data-products/lotus-manage-products.v1.json`, `contracts/domain-data-products/lotus-manage-consumers.v1.json` | Existing producer declaration covers `PortfolioActionRegister:v1`, not waves. Existing consumer declaration covers caller-supplied `PortfolioStateSnapshot:v1`, not the direct RFC-0087 source products needed for wave source checks. Update only when the wave contract is implementation-backed. |
| Trust telemetry | `contracts/trust-telemetry/portfolio-action-register.telemetry.v1.json` | Current telemetry is action-register specific. Add wave telemetry only after an implementation-backed product declaration exists. |
| Documentation guardrails | `tests/unit/test_documentation_current_state.py`, `docs/rfcs/README.md`, `wiki/Supported-Features.md` | Extend guardrails to protect Slice 0 decisions and prevent premature supported-feature promotion. |

## Reviewed Source Authorities

| Capability | Authority | Current evidence | Slice 0 classification | First implementation decision |
| --- | --- | --- | --- | --- |
| Portfolio identity by explicit id list | `lotus-core` operational portfolio query plus per-portfolio source products | `lotus-core` query service supports `/portfolios` filters including explicit `portfolio_ids`; manage has per-portfolio source resolvers. | Already sufficient for explicit-list selection when each item is source-checked. | Support first. Wave preview/create accepts explicit portfolio ids and checks each item independently. |
| PM-book portfolio membership | `lotus-core` | Current query evidence shows booking-center and client filters, but no proven PM-book/portfolio-manager book product exposed to manage. | Deferred with no support claim. | Do not support full PM-book trigger until core owns a certified PM-book/cohort product or the caller supplies an explicit reviewed manifest. |
| CIO model-change affected portfolios | `lotus-core` model binding/event source or approved trigger manifest | `DpmModelPortfolioTarget:v1` and mandate binding exist, but no proven source product returns all portfolios affected by a model-change event. | Deferred with no support claim for automatic impact discovery. | Allow only explicit affected-portfolio manifest posture in first wave; do not promote automatic CIO model-change impact. |
| Mandate binding and model id per item | `lotus-core` and `lotus-manage` mandate twin | RFC-0087 mandate-binding product and RFC-0038 mandate twin exist. | Proven for per-portfolio checks. | Required for `READY`; missing or mismatched evidence blocks the item. |
| Source readiness per item | `lotus-core` RFC-0087 source-readiness products | `DpmSourceReadiness:v1` is declared and implemented in `lotus-core`; manage currently has stateful source context but no wave source-check service. | Must implement in manage using existing owner product. | Slice 5 adds item source checks and preserves source refs, owner, product version, freshness, and reason codes. |
| Mandate health and exceptions | `lotus-manage` RFC-0038 | Mandate health snapshots and monitoring exceptions exist. | Already sufficient. | Missing health degrades or blocks according to item policy; unresolved exceptions may make item `REVIEW_REQUIRED`. |
| Construction alternatives | `lotus-manage` RFC-0039 | Persisted alternative generation and selection APIs exist. | Already sufficient as owning authority. | Wave simulation delegates to construction service for ready items only. |
| Proof-pack linkage | `lotus-manage` RFC-0040 | Immutable proof-pack authority exists. | Already sufficient as owning authority. | Wave items link to generated or attached proof packs only through proof-pack service contracts. |
| Aggregate wave metrics | `lotus-manage` from item evidence | No wave aggregate exists today. | Must implement in manage. | Compute only from item evidence and expose reconciliation refs; no cross-domain calculation cloning. |
| Risk enrichment | `lotus-risk` | Manage construction has a risk-authority seam, but RFC-0041 aggregate risk impact needs risk-owned support. | Deferred unless a risk-owned contract is consumed. | First wave may show risk module `DEGRADED`/`NOT_SUPPORTED`; no risk-aware aggregate support claim. |
| Performance enrichment | `lotus-performance` | No RFC-0041 manage integration exists. | Deferred with no support claim. | First wave may show performance module `DEGRADED`/`NOT_SUPPORTED`; no performance-impact support claim. |
| Report materialization | `lotus-report`/`lotus-render`/`lotus-archive` | RFC-0040 manage report input exists; report/render/archive product realization is downstream. | Not applicable to manage backend MVP. | Wave can provide evidence refs only; no generated-report claim. |
| AI memo generation | `lotus-ai` | RFC-0040 manage AI evidence input exists; AI memo generation belongs to AI/RFC-0043. | Not applicable to manage backend MVP. | Wave can provide bounded AI evidence refs only; no AI memo claim. |
| Gateway composition | `lotus-gateway` | Existing Gateway RFC-0098 covers DPM command-center direction and proof-pack alignment. | Must tighten later. | Slice 9 adds RFC-0041 wave composition direction after manage contracts stabilize. |
| Workbench command center | `lotus-workbench` | Existing Workbench RFC-0098 covers command-center direction and proof-pack alignment. | Must tighten later. | Slice 9 adds RFC-0041 wave UI realization direction after manage contracts stabilize. |

## First-Wave Trigger Scope

| Trigger | First-wave support posture | Required input | Missing-source behavior | Promotion rule |
| --- | --- | --- | --- | --- |
| `EXPLICIT_PORTFOLIO_LIST` | Supported first | Non-empty portfolio id list, trigger rationale, as-of date, actor/correlation context. | Reject empty or malformed list; source-check each item and preserve partial readiness. | Promote only after preview/create/source-check/simulate/approve/stage/handoff live proof with mixed item states. |
| `PM_BOOK_REVIEW` | Deferred, except supplied manifest posture | Caller-supplied affected portfolio manifest with reviewer/source metadata. | Return `NOT_SUPPORTED_TRIGGER` for implicit PM-book discovery; degraded preview if manifest metadata is insufficient. | Promote only after core or another owner exposes certified PM-book membership or manifest governance is formalized and proven. |
| `CIO_MODEL_CHANGE` | Deferred for automatic discovery, allowed only as supplied affected-portfolio manifest posture | Model-change event id/rationale plus explicit affected portfolio ids and source metadata. | Return `NOT_SUPPORTED_TRIGGER` for automatic impact discovery; no synthetic portfolio cohort from model id alone. | Promote automatic impact only after owning source product returns affected mandates and live proof reconciles the cohort. |
| `TACTICAL_HOUSE_VIEW` | Deferred with no support claim | Future CIO/risk scenario or approved portfolio manifest. | `NOT_SUPPORTED_TRIGGER`. | Promote only after scenario/house-view authority exists or approved manifest rules are implemented. |
| `RISK_EVENT` | Deferred with no support claim | Future `lotus-risk` event/cohort product. | `NOT_SUPPORTED_TRIGGER`. | Promote only after risk owner exposes certified cohort/impact source. |
| `BULK_REVIEW_CAMPAIGN` | Deferred, except supplied manifest posture | Explicit portfolio ids and campaign rationale. | `NOT_SUPPORTED_TRIGGER` for implicit campaign discovery. | Promote only after campaign source and permissions are governed. |

## State-Machine Transition Matrix

Wave and item states must be append-only event driven. Commands must carry actor, rationale,
correlation id, idempotency key where applicable, expected version, and generated timestamp.

| Current state | Allowed next states | Guard |
| --- | --- | --- |
| `DRAFT` | `PREVIEWED`, `CANCELLED` | Trigger payload is valid; no persisted wave actions have run. |
| `PREVIEWED` | `CREATED`, `CANCELLED` | Candidate list and source posture are persisted with source refs. |
| `CREATED` | `SOURCE_CHECKED`, `CANCELLED` | Wave aggregate exists and item list is immutable except governed retry/re-source events. |
| `SOURCE_CHECKED` | `SIMULATING`, `REVIEW_REQUIRED`, `BLOCKED`, `CANCELLED` | At least one item has source-check evidence; blocked items remain visible. |
| `SIMULATING` | `SIMULATED`, `PARTIALLY_SIMULATED`, `SIMULATION_FAILED` | Only ready items may be simulated; blocked/pending items are skipped with reason codes. |
| `SIMULATED` | `REVIEW_REQUIRED`, `APPROVED`, `CANCELLED` | Required alternatives and aggregate reconciliation are available. |
| `PARTIALLY_SIMULATED` | `REVIEW_REQUIRED`, `APPROVED_WITH_EXCEPTIONS`, `CANCELLED` | Partial completion is explicit and exception approval is required. |
| `REVIEW_REQUIRED` | `APPROVED`, `APPROVED_WITH_EXCEPTIONS`, `REJECTED`, `CANCELLED` | Actor has approval authority and rationale is present. |
| `APPROVED` | `STAGED`, `CANCELLED` | All mandatory item approvals and proof-pack prerequisites pass. |
| `APPROVED_WITH_EXCEPTIONS` | `STAGED`, `CANCELLED` | Exception approvals are actor-attributed and blocked items are excluded. |
| `STAGED` | `HANDOFF_READY`, `HANDOFF_BLOCKED`, `CANCELLED` | Staging evidence exists; no external execution claim is made. |
| `HANDOFF_READY` | `HANDOFF_ACKNOWLEDGED`, `CLOSED` | Operations handoff evidence is generated and immutable. |
| `HANDOFF_BLOCKED` | `SOURCE_CHECKED`, `CANCELLED` | Retry is allowed only after new source/staging evidence and version guard. |
| `SIMULATION_FAILED` | `SOURCE_CHECKED`, `CANCELLED` | Retry must preserve failed event and add new reason/source refs. |
| `BLOCKED` | `SOURCE_CHECKED`, `CANCELLED` | Retry must cite changed source evidence. |
| `REJECTED` | `CLOSED` | No further execution actions. |
| `CANCELLED` | `CLOSED` | No further execution actions. |
| `HANDOFF_ACKNOWLEDGED` | `CLOSED` | Acknowledgement does not imply OMS/EMS execution. |
| `CLOSED` | none | Terminal. |

## Item Readiness Rules

| Item state | Meaning | Allowed behavior |
| --- | --- | --- |
| `CANDIDATE` | Portfolio is in the candidate set but not yet source-checked. | Can be persisted from preview/create; cannot simulate. |
| `SOURCE_READY` | Required source products are current, complete, and reconciled. | Can simulate. |
| `SOURCE_DEGRADED` | Non-blocking source families are stale, partial, or unavailable. | Can simulate only when policy permits and degradation is visible. |
| `REVIEW_REQUIRED` | Mandate health, exception, or policy state requires approval. | Cannot stage without approval. |
| `SOURCE_BLOCKED` | Required source product or identity evidence is missing or inconsistent. | Cannot simulate or stage. |
| `SIMULATED` | Construction alternatives exist for the item. | Can select alternative and generate proof-pack linkage. |
| `SIMULATION_BLOCKED` | Simulation failed or prerequisites did not pass. | Can retry after source or configuration change. |
| `SELECTED` | An alternative is actor-selected with rationale. | Can request proof-pack/approval. |
| `PROOF_PACK_READY` | RFC-0040 proof-pack is attached or generated. | Can approve when other guards pass. |
| `APPROVED` | Actor-approved for staging. | Can stage. |
| `STAGED` | Operations handoff package is prepared. | Can enter handoff. |
| `HANDOFF_READY` | Handoff package is immutable and retrievable. | Can close after acknowledgement. |
| `EXCLUDED` | Item was explicitly excluded from the wave. | Cannot be staged; remains visible in aggregate. |

## Cross-App Gap Decisions

| Gap | Owner | Decision | Required future proof |
| --- | --- | --- | --- |
| Certified affected-portfolio discovery by PM book or portfolio manager | `lotus-core` or future relationship-book authority | Deferred; first wave requires explicit portfolio ids or supplied manifest. | Owner route/product declaration, OpenAPI certification, manage consumer declaration, mixed live proof. |
| Certified affected-mandate discovery by model-change event | `lotus-core` or CIO model-event authority | Deferred; automatic CIO model-change impact cannot be promoted. | Source product with event id, model id/version, affected portfolio ids, lineage, freshness, and reconciliation proof. |
| Wave domain-data product declaration | `lotus-manage` | Implement after wave API and persistence are stable. | Repo-native producer declaration, telemetry fixture, platform catalog regeneration, consumer dependencies. |
| Wave trust telemetry | `lotus-manage` | Implement after producer declaration exists. | Validated telemetry snapshot and live evidence path. |
| Gateway wave composition | `lotus-gateway` | Tighten or add downstream RFC in Slice 9 after manage API shape stabilizes. | Gateway RFC, typed client, OpenAPI tests, no-reconstruction tests, live gateway proof. |
| Workbench wave command center | `lotus-workbench` | Tighten or add downstream RFC in Slice 9 after manage/Gateway contracts stabilize. | Workbench RFC, BFF-only consumption, browser/accessibility/visual proof, canonical runtime evidence. |
| Platform scaffold for state-machine/evidence-heavy services | `lotus-platform` | Evaluate and improve in Slice 1 only where reusable gaps are proven. | Platform automation change, tests, docs, and evidence that future apps benefit. |

## Implementation Order Confirmation

RFC-0041 should proceed in the RFC-defined order:

1. Slice 1: evaluate and fix reusable platform/scaffold gaps before inventing local wave-only
   conventions.
2. Slice 2: clean wave-adjacent structure and docs only where it materially reduces duplication,
   dead code, or future implementation risk.
3. Slice 3: implement pure wave domain, state machine, events, repository contract, and persistence.
4. Slice 4: implement preview/create using only supported first-wave triggers.
5. Slice 5: implement source check against owning source products and mandate health.
6. Slice 6: implement simulation, alternative selection, aggregate metrics, and proof-pack linkage.
7. Slice 7: implement approval, staging, and handoff without external execution claims.
8. Slice 8: implement supportability, observability, and diagnostics.
9. Slice 9: tighten Gateway and Workbench realization RFCs from stable manage contracts.
10. Slice 10 through Slice 12: live proof, hardening, docs/wiki/context, PR merge, wiki publish,
    branch cleanup, and final gold-pass assessment.

Do not start product implementation before this Slice 0 artifact is reviewed and validated.

## Evidence And Branch Conventions

| Convention | Value |
| --- | --- |
| Implementation branch | `feat/rfc0041-implementation` |
| Live evidence root | `output/rfc0041-wave-proof/<timestamp>/` |
| Preferred canonical portfolio for live proof | `PB_SG_GLOBAL_BAL_001` where front-office evidence requires the canonical seeded portfolio |
| Required mixed-state proof | At least one `SOURCE_READY`, one `REVIEW_REQUIRED` or `SOURCE_DEGRADED`, and one `SOURCE_BLOCKED` item before support promotion |
| Downstream RFC timing | Slice 9, after manage API contracts and live manage proof are stable enough to avoid speculative Gateway/Workbench contracts |
| Wiki posture during Slice 0 | Wiki may state implementation has started and source-map decisions are complete, but all wave features remain proposed only |

