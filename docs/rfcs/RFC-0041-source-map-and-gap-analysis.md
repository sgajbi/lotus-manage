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
| First-wave trigger subset defined | First implementation scope began with explicit portfolio-list waves. Source-owned `PM_BOOK_REVIEW` and `CIO_MODEL_CHANGE` cohort discovery are now implementation-backed through lotus-core source products. Bounded `RISK_EVENT` and `TACTICAL_HOUSE_VIEW` cohorts are now consumed from their owning source products, and bounded `BULK_REVIEW_CAMPAIGN` membership is implemented in Manage over source-backed candidates. |
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
| PM-book portfolio membership | `lotus-core` | `PortfolioManagerBookMembership:v1` is implemented, validated, and consumed by manage for `PM_BOOK_REVIEW` preview/create. | Proven for source-owned PM-book discovery. | Support `PM_BOOK_REVIEW` only through lotus-core source evidence; reject caller-supplied portfolios for that trigger. |
| CIO model-change affected portfolios | `lotus-core` model binding/event source | `CioModelChangeAffectedCohort:v1` is implemented, validated, and consumed by manage for `CIO_MODEL_CHANGE` preview/create. It returns approved model-version identity, deterministic model-change event id, affected mandate bindings, supportability, and lineage. | Proven for source-owned first-wave CIO model-change affected-mandate discovery. | Support `CIO_MODEL_CHANGE` only through lotus-core affected-cohort evidence; reject caller-supplied portfolios for that trigger. |
| Risk-event affected portfolios | `lotus-risk` risk-event cohort source product | `RiskEventAffectedCohort:v1` is implemented in `lotus-risk`, mirrored in platform mesh governance, and consumed by manage for bounded `RISK_EVENT` preview/create over caller-supplied candidate portfolios with source-supplied exposure weights. | Proven for bounded source-owned risk-event affected-cohort discovery. | Support `RISK_EVENT` only through lotus-risk affected-cohort evidence; require caller-supplied candidates and exposure weights; fail closed when source authority is unavailable, rejected, incomplete, or empty. |
| Tactical house-view affected portfolios | `lotus-advise` tactical house-view cohort source product | `TacticalHouseViewAffectedCohort:v1` is implemented in `lotus-advise` and consumed by manage for bounded `TACTICAL_HOUSE_VIEW` preview/create over caller-supplied source-backed candidate portfolios. | Proven for bounded source-owned tactical house-view affected-cohort consumption. | Support `TACTICAL_HOUSE_VIEW` only through lotus-advise affected-cohort evidence; require bank-authored tactical view refs, candidate source refs, source-owned portfolio type and discretionary mandate posture, eligible DPM portfolio types, and fail-closed source dependency handling. |
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
| `PM_BOOK_REVIEW` | Supported for source-owned PM-book discovery | `portfolio_manager_id`, as-of date, optional tenant/booking-center filters, and eligible portfolio types. | Reject caller-supplied portfolios; return dependency failures for unavailable, incomplete, or empty source cohorts. | Promote only while lotus-core `PortfolioManagerBookMembership:v1` remains the source authority. |
| `CIO_MODEL_CHANGE` | Supported for source-owned model-change affected-mandate discovery | `model_portfolio_id`, as-of date, optional tenant and booking-center filters. | Reject caller-supplied portfolios; return dependency failures for unavailable, incomplete, or empty source cohorts. | Promote only while lotus-core `CioModelChangeAffectedCohort:v1` remains the source authority. |
| `TACTICAL_HOUSE_VIEW` | Supported for bounded source-owned tactical house-view affected-cohort consumption | Bank-authored tactical house-view payload with source refs, as-of date, candidate portfolios, source-owned `portfolio_type`, source-owned `discretionary_mandate`, candidate source refs, eligible portfolio types, and optional minimum tactical exposure weight. | Reject missing source evidence; return dependency failures for unavailable, rejected, incomplete, or empty source cohorts. | Promote only while lotus-advise `TacticalHouseViewAffectedCohort:v1` remains the source authority; manage must not compute house-view, holdings, exposure, alignment, or mandate facts locally. |
| `RISK_EVENT` | Supported for bounded source-owned risk-event affected-cohort discovery | `risk_event_id`, as-of date, candidate portfolios, and source-supplied `exposure_weights`. | Reject missing selector/candidates/exposure weights; return dependency failures for unavailable, rejected, incomplete, or empty source cohorts. | Promote only while lotus-risk `RiskEventAffectedCohort:v1` remains the source authority; manage must not compute risk-event impact locally. |
| `BULK_REVIEW_CAMPAIGN` | Supported for bounded Manage-owned campaign membership, persisted campaign discovery, and campaign-definition retirement over supplied source-backed candidates | Source-backed candidate portfolios, source-owned `portfolio_type`, source refs, as-of date, eligible portfolio types, optional governance evidence, persisted campaign definitions, `BulkReviewCampaignDiscovery:v1` summaries, and retirement metadata for definitions closed to new wave use. | Reject missing candidate/source/governance evidence or empty eligible membership; retired definitions fail closed for preview/create; campaign discovery must not discover the global portfolio universe or recompute membership. | Promote only for the bounded membership envelope, persisted campaign-definition discovery, retirement lifecycle control, and Workbench active campaign-definition list; broader campaign workflow surfaces remain future work. |

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
| Certified affected-portfolio discovery by PM book or portfolio manager | `lotus-core` | Implemented for first-wave PM-book discovery through `PortfolioManagerBookMembership:v1`; richer relationship-householding and entitlement hierarchy remain future source products. | Keep source-product tests, manage consumer tests, and supported-feature truth current. |
| Certified affected-mandate discovery by model-change event | `lotus-core` | Implemented for first-wave CIO model-change discovery through `CioModelChangeAffectedCohort:v1`; risk-event and tactical house-view cohorts are implemented through their owning source products; global campaign discovery remains future source/product depth. | Keep source-product tests, manage consumer tests, and supported-feature truth current. |
| Wave domain-data product declaration | `lotus-manage` | Implement after wave API and persistence are stable. | Repo-native producer declaration, telemetry fixture, platform catalog regeneration, consumer dependencies. |
| Wave trust telemetry | `lotus-manage` | Implement after producer declaration exists. | Validated telemetry snapshot and live evidence path. |
| Gateway wave composition | `lotus-gateway` | Tighten or add downstream RFC in Slice 9 after manage API shape stabilizes. | Gateway RFC, typed client, OpenAPI tests, no-reconstruction tests, live gateway proof. |
| Workbench wave command center | `lotus-workbench` | Tighten or add downstream RFC in Slice 9 after manage/Gateway contracts stabilize. | Workbench RFC, BFF-only consumption, browser/accessibility/visual proof, canonical runtime evidence. |
| Platform scaffold for state-machine/evidence-heavy services | `lotus-platform` | Evaluate and improve in Slice 1 only where reusable gaps are proven. | Platform automation change, tests, docs, and evidence that future apps benefit. |

## Slice 1 Platform Result

Slice 1 found that the platform scaffold already covered the baseline API certification pattern,
Swagger/OpenAPI gate, health/readiness endpoints, structured logging, product-safe problem-details
errors, test scaffolding, CI defaults, supported-features placeholder, wiki source posture, and
basic RFC evidence manifest. The reusable gap was narrower: state-machine and API-heavy RFC slices
needed a stronger machine-readable evidence template so future services do not invent local closure
formats.

`lotus-platform` PR #296 fixed that at the platform layer and was merged as
`47d3c7fcd9142e383592bc9bd2e770c647966efb`. The scaffold now emits RFC evidence manifest
sections for:

1. slice closure,
2. API certification,
3. state-machine review,
4. supported-feature review,
5. wiki-publication posture,
6. downstream realization.

Validation:

1. `python -m pytest tests\unit\test_repository_hygiene_scaffold_contract.py -q`,
2. `python -m ruff check tests\unit\test_repository_hygiene_scaffold_contract.py`,
3. `python -m ruff format --check tests\unit\test_repository_hygiene_scaffold_contract.py`,
4. `git diff --check`,
5. GitHub Feature Lane and PR Merge Gate passed on `sgajbi/lotus-platform#296`.

No manage-local evidence convention is introduced for RFC-0041.

## Slice 2 Cleanup Result

Slice 2 reviewed wave-adjacent structure before product implementation. The current RFC-0038,
RFC-0039, and RFC-0040 modules are already split into domain, repository, infrastructure, service,
router, and tests. No dead proof-pack, construction, mandate, or supportability module was removed
because the reviewed candidates are still referenced by tests or runtime paths.

Material cleanup completed in this slice:

1. the misleading RFC-0041 documentation guardrail name was changed from "before implementation"
   to a Slice 0 source-map guardrail,
2. the RFC status and index now reflect that platform scaffolding and cleanup are complete,
3. long-lived cleanup evidence stays in this source-map document instead of adding another
   redundant RFC-sidecar document.

Slice 3 may now add wave domain modules without needing to preserve stale or speculative
compatibility aliases.

## Slice 3 Domain Foundation Result

Slice 3 adds the manage-owned wave foundation without adding API behavior yet:

1. `src/core/waves/models.py` defines the durable `DpmRebalanceWave`,
   `DpmRebalanceWaveItem`, trigger, source-ref, aggregate-metric, and event contracts,
2. `src/core/waves/state_machine.py` implements the RFC transition matrix as pure validation and
   transition functions,
3. `src/core/waves/repository.py` defines the wave repository protocol, version-conflict error, and
   idempotency-conflict error,
4. `src/infrastructure/waves/in_memory.py` provides a defensive-copy in-memory repository with
   idempotency and optimistic-concurrency guards,
5. `src/infrastructure/waves/postgres.py` provides the PostgreSQL repository adapter and migration
   initialization path,
6. `src/infrastructure/postgres_migrations/dpm/0007_rebalance_waves.sql` adds wave, idempotency,
   and append-only event tables.

Validation:

1. `python -m pytest tests\unit\dpm\waves\test_wave_domain.py -q`,
2. `python -m ruff check src\core\waves src\infrastructure\waves tests\unit\dpm\waves\test_wave_domain.py`,
3. `python -m mypy --config-file mypy.ini src\core\waves src\infrastructure\waves tests\unit\dpm\waves\test_wave_domain.py`,
4. `python -m pytest tests\unit\shared\dependencies\test_production_cutover_contract.py::test_expected_migration_versions_for_namespaces tests\unit\shared\dependencies\test_postgres_migrations.py::test_apply_postgres_migrations_is_forward_only_and_idempotent -q`.

No route, capability, or supported-feature claim is added in Slice 3. Slice 4 must build preview and
create behavior on top of these domain contracts.

## Slice 4 Preview/Create Result

Slice 4 adds the first certified manage API surface for explicit affected-portfolio waves:

1. `POST /api/v1/rebalance/waves/preview` builds a non-durable wave preview,
2. `POST /api/v1/rebalance/waves` creates a durable wave with `Idempotency-Key`,
3. only `EXPLICIT_PORTFOLIO_LIST` is supported; unsupported triggers return
   `NOT_SUPPORTED_TRIGGER`,
4. source-backed candidates are built from caller-supplied affected-portfolio source refs or
   existing RFC-0038 mandate digital twins,
5. missing affected-portfolio evidence is returned as `SOURCE_BLOCKED` rather than promoted to
   readiness,
6. OpenAPI quality and endpoint-certification source are updated.

Validation:

1. `python -m pytest tests\unit\dpm\api\test_waves_api.py tests\unit\dpm\waves\test_wave_domain.py -q`,
2. `python scripts\openapi_quality_gate.py`,
3. `python -m pytest tests\unit\dpm\contracts\test_contract_openapi_supportability_docs.py tests\integration\test_openapi_certification_matrix.py tests\unit\test_documentation_current_state.py -q`.

No Gateway, Workbench, simulation, approval, staging, operations handoff, PM-book discovery, or
automatic CIO model-change cohort discovery claim is added in Slice 4.

## Slice 5 Source Check Result

Slice 5 adds the durable source-check operation for existing waves:

1. `POST /api/v1/rebalance/waves/{wave_id}/source-check` loads a persisted wave and evaluates
   each item against authoritative manage-owned mandate digital twins and mandate health snapshots,
2. ready promotion requires both mandate twin evidence and a ready mandate health/source-readiness
   snapshot; caller portfolio ids or caller source refs alone are never sufficient,
3. `src/core/waves/source_readiness.py` keeps pure item-classification logic out of the API
   orchestration service,
4. item classification now supports `SOURCE_READY`, `SOURCE_DEGRADED`, `REVIEW_REQUIRED`, and
   `SOURCE_BLOCKED` with bounded reason codes such as `MANDATE_HEALTH_MISSING` and
   source-owner diagnostics,
5. source refs are attached for `MANDATE_DIGITAL_TWIN`, `DPM_MANDATE_HEALTH_SNAPSHOT`,
   `DPM_SOURCE_READINESS`, and available `lotus-core` lineage products from the mandate twin,
6. aggregate metrics are recomputed from item state after classification,
7. the wave transitions from `CREATED` to `SOURCE_CHECKED` with an event carrying state counts, and
   repeat calls against an already source-checked wave return the persisted wave as idempotent
   replay without appending duplicate events,
8. missing waves return `DPM_WAVE_NOT_FOUND`; invalid state and version conflicts are explicit
   error contracts.

Validation:

1. `python -m pytest tests\unit\dpm\api\test_waves_api.py tests\unit\dpm\waves\test_wave_domain.py -q`,
2. `python -m ruff check src\api\services\wave_service.py src\api\routers\waves.py tests\unit\dpm\api\test_waves_api.py`,
3. `python -m mypy --config-file mypy.ini src\api\services\wave_service.py src\api\routers\waves.py tests\unit\dpm\api\test_waves_api.py`,
4. `python scripts\openapi_quality_gate.py`,
5. `python scripts\api_vocabulary_inventory.py --output docs\standards\api-vocabulary\lotus-manage-api-vocabulary.v1.json`.

No simulation, selection, approval, staging, handoff, Gateway, Workbench, PM-book discovery, or
automatic CIO model-change cohort discovery claim is added in Slice 5.

## Slice 6 Simulation, Selection, and Proof-Pack Linkage Result

Slice 6 adds construction and proof-pack orchestration without duplicating RFC-0039 or RFC-0040
authority:

1. `POST /api/v1/rebalance/waves/{wave_id}/simulate` calls
   `construction_service.generate_construction_alternative_set` for `SOURCE_READY` items only,
2. callers must provide a real RFC-0039 `RebalanceRequest` per ready item; wave simulation does
   not synthesize holdings, market data, model targets, or shelf data from mandate identifiers,
3. ready items without construction input become `SIMULATION_BLOCKED` with
   `CONSTRUCTION_INPUT_MISSING`, while source-blocked/degraded/review-required items preserve their
   existing source-check reasons,
4. wave simulation records `SIMULATING` and terminal `SIMULATED`, `PARTIALLY_SIMULATED`, or
   `SIMULATION_FAILED` events and recomputes aggregate metrics from item evidence,
5. `POST /api/v1/rebalance/waves/{wave_id}/items/{wave_item_id}/select` delegates selection to
   `construction_service.select_construction_alternative`,
6. selected alternatives persist on the wave item after repository reload,
7. when requested, item selection generates RFC-0040 proof packs through
   `proof_pack_service.generate_proof_pack_from_selected_alternative`,
8. proof-pack generation failures or explicitly skipped generation degrade the item as `SELECTED`
   with proof-pack diagnostics instead of fabricating proof-pack readiness,
9. no approval, staging, handoff, Gateway, Workbench, PM-book discovery, or automatic CIO
   model-change cohort discovery claim is added in Slice 6.

Validation:

1. `python -m pytest tests\unit\dpm\api\test_waves_api.py -q`,
2. `python -m ruff check src\api\services\wave_service.py src\api\routers\waves.py tests\unit\dpm\api\test_waves_api.py`,
3. `python -m mypy --config-file mypy.ini src\api\services\wave_service.py src\api\routers\waves.py tests\unit\dpm\api\test_waves_api.py`,
4. `python scripts\openapi_quality_gate.py`,
5. `python scripts\api_vocabulary_inventory.py --output docs\standards\api-vocabulary\lotus-manage-api-vocabulary.v1.json`.

## Slice 7 Approval, Staging, and Operations Handoff Result

Slice 7 adds manage-owned workflow commands after construction selection and proof-pack linkage.
The implementation stays inside `lotus-manage`; it does not send orders, client communications, or
external execution instructions.

Implemented truth:

1. `POST /api/v1/rebalance/waves/{wave_id}/approve` approves only `SELECTED` or
   `PROOF_PACK_READY` items.
2. Blocked, simulation-blocked, degraded, review-required, unselected, failed, and cancelled items
   are never promoted to approved by the approval command.
3. Mixed waves with at least one approved item and at least one exception item move to
   `APPROVED_WITH_EXCEPTIONS`; fully eligible waves move to `APPROVED`.
4. `POST /api/v1/rebalance/waves/{wave_id}/stage` stages only approved items and records
   `external_execution_claimed=false` in item diagnostics.
5. `POST /api/v1/rebalance/waves/{wave_id}/handoff` creates append-only internal operations
   handoff refs on the wave JSON contract, including stable handoff id, item ids, actor, reason,
   correlation id, content hash, and `external_execution_claimed=false`.
6. Repeated approve, stage, and handoff commands are idempotent and do not append duplicate
   evidence after the terminal command state has already been reached.
7. API errors are precise: invalid state, no eligible approval items, no eligible staging items,
   no staged handoff items, missing wave, and optimistic version conflicts all use bounded error
   codes.
8. Tests prove end-to-end approval/stage/handoff persistence, blocked-item exclusion, handoff ref
   append-only persistence, idempotent replay, and invalid-state behavior.

Production boundary:

1. Manage handoff evidence is an internal operations readiness package only.
2. It is not an order execution API, OMS handoff, client communication, or trading instruction.
3. Gateway and Workbench must consume this manage truth later; they must not reconstruct approval,
   staging, handoff readiness, or aggregate state.
4. No supported feature claim is promoted yet because supportability, live proof, downstream
   realization RFCs, and final closure are still pending.

Evidence:

1. `src/api/services/wave_service.py`
2. `src/api/routers/waves.py`
3. `src/core/waves/models.py`
4. `tests/unit/dpm/api/test_waves_api.py`
5. `docs/standards/api-vocabulary/lotus-manage-api-vocabulary.v1.json`

## Slice 8 Supportability, Observability, and Operator Diagnostics Result

Slice 8 adds a product-safe supportability surface for operators and bounded telemetry for wave
supportability posture.

Implemented truth:

1. `GET /api/v1/rebalance/waves/{wave_id}/supportability` returns wave-level readiness posture,
   issue counts, bounded item-state issues, source owners, reason codes, remediation routes, and
   support refs.
2. The response deliberately excludes portfolio identifiers, client identifiers, raw request
   bodies, raw response bodies, source-ref payloads, secrets, and trace details.
3. Blocked source or simulation states produce `blocked` supportability with critical issues.
4. Degraded/review/selected-but-not-proof-ready states produce `degraded` supportability with
   warning issues.
5. Ready workflow states return `ready` supportability and a bounded continue-workflow operator
   action.
6. The endpoint emits safe structured logs with only wave state, supportability state, bounded
   reason, and issue count.
7. `lotus_manage_wave_supportability_total` records bounded metric labels:
   `surface`, `supportability_state`, and `reason`.
8. The observability monitoring contract and validator now include the wave supportability metric.
9. Tests prove product-safe responses, missing-wave behavior, bounded metric labels, contract
   alignment, and no portfolio/client identifier leakage in the wave supportability endpoint or
   metric labels.

Production boundary:

1. The endpoint is operator diagnostics, not a business workflow command.
2. It does not expose raw upstream evidence; users should follow the remediation route and source
   owner to repair the owning source product.
3. Gateway and Workbench may later compose this endpoint, but they must keep the same no-sensitive
   telemetry and no-reconstruction posture.

Evidence:

1. `src/api/services/wave_service.py`
2. `src/api/routers/waves.py`
3. `src/api/observability.py`
4. `contracts/observability/lotus-manage-monitoring.v1.json`
5. `tests/unit/dpm/api/test_waves_api.py`
6. `tests/unit/dpm/api/test_observability_api.py`
7. `tests/unit/test_observability_contracts.py`

## Slice 9 Gateway and Workbench Realization RFC Result

Slice 9 tightened the downstream realization RFCs now that manage wave contracts are stable through
supportability and observability. No manage product behavior was moved downstream, and no Gateway
or Workbench feature was promoted as supported.

Gateway result:

1. `lotus-gateway` RFC-0098 now includes an RFC-0041 rebalance-wave addendum.
2. Gateway target routes are under `/api/v1/dpm/command-center/waves*`.
3. Gateway must consume manage preview, create, source-check, simulate, select, approve, stage,
   handoff, and supportability APIs through typed clients.
4. Gateway must preserve manage `wave_id`, state, item states, reason codes, aggregate metrics,
   selected alternative refs, proof-pack refs, handoff refs, supportability refs, retention policy,
   and event refs.
5. Gateway must not calculate affected portfolios, source readiness, aggregate metrics,
   construction alternatives, proof-pack state, or execution posture.
6. Gateway must compose risk, performance, report, archive, and AI posture only from owning
   services.

Workbench result:

1. `lotus-workbench` RFC-0098 now includes an RFC-0041 rebalance-wave command-center workspace
   addendum.
2. Workbench must consume Gateway wave routes only through the Workbench BFF.
3. Workbench target panels cover wave header, item matrix, action rail, construction drawer,
   proof-pack evidence drawer, supportability drawer, and internal operations handoff rail.
4. Workbench must not call `lotus-manage` directly, calculate readiness, override action
   eligibility, or imply external execution from manage internal handoff refs.
5. Workbench promotion requires Gateway implementation, Workbench BFF/browser implementation,
   canonical `PB_SG_GLOBAL_BAL_001` live validation, visual and accessibility evidence, reviewed
   screenshots, wiki updates, and implementation-backed support wording.

Evidence:

1. `lotus-gateway` PR #183, merge `e0e4b1b`, wiki publish `3fc30e8`
2. `lotus-workbench` PR #143, merge `c4888d4`, wiki publish `25566cb`
3. Gateway RFC: `lotus-gateway/docs/rfcs/RFC-0098-dpm-command-center-composition-contract.md`
4. Workbench RFC: `lotus-workbench/docs/rfcs/RFC-0098-dpm-mandate-command-center-experience.md`

Production boundary:

1. Manage remains the RFC-0041 wave authority.
2. Gateway remains the future composition boundary.
3. Workbench remains the future product experience boundary.
4. Full front-office support remains unpromoted until downstream implementation and live proof are
   complete.

## Slice 10 Live Implementation Proof Result

Slice 10 generated live, machine-readable implementation proof against the canonical manage runtime
with Postgres-backed repositories. The evidence pack is
`output/rfc0041-wave-proof/20260504-231914/`.

Validated flow:

1. `POST /api/v1/mandates/{mandate_id}/health/recalculate` seeded source-backed ready,
   degraded, and pending-review mandate health states.
2. `POST /api/v1/rebalance/waves/preview` proved non-durable mixed candidate and blocked
   affected-portfolio posture.
3. `POST /api/v1/rebalance/waves` proved durable wave creation and idempotency-key posture.
4. `POST /api/v1/rebalance/waves/{wave_id}/source-check` proved one `SOURCE_READY`, one
   `SOURCE_DEGRADED`, one `REVIEW_REQUIRED`, and one `SOURCE_BLOCKED` item.
5. `POST /api/v1/rebalance/waves/{wave_id}/simulate` delegated to RFC-0039 construction for the
   ready item only.
6. `POST /api/v1/rebalance/waves/{wave_id}/items/{wave_item_id}/select` generated RFC-0040
   proof-pack linkage for the selected alternative.
7. `POST /api/v1/rebalance/waves/{wave_id}/approve`, `stage`, and `handoff` proved
   approval-with-exceptions, approved-item-only staging, append-only internal handoff refs, and
   `external_execution_claimed=false`.
8. `POST /api/v1/rebalance/waves/{wave_id}/cancel` proved actor-attributed cancellation on a
   separate durable wave before downstream work, with no external execution claim.
9. `GET /api/v1/rebalance/waves`, `GET /api/v1/rebalance/waves/{wave_id}`,
   `GET /api/v1/rebalance/waves/{wave_id}/items`,
   `GET /api/v1/rebalance/waves/{wave_id}/proof-pack`, and
   `GET /api/v1/rebalance/waves/{wave_id}/supportability` proved retrieve, search, item,
   proof-pack posture, and product-safe supportability read models.
10. OpenAPI certification checked 13 wave operations and found no missing or weak route contracts.
11. Aggregate reconciliation passed with one handoff-ready item and three visible exceptions.

Issues found and fixed during live proof:

1. RFC-0039 construction delegation reused one wave simulation correlation id for multiple method
   runs, which collided with Postgres run-supportability uniqueness. The fix records
   method-specific run correlation ids while preserving the parent wave correlation in wave events.
2. Mixed waves with a simulated eligible item plus degraded or review-required exceptions rolled up
   to `SIMULATED`, which made approval-with-exceptions invalid. The fix classifies any simulated
   wave with remaining non-simulated exceptions as `PARTIALLY_SIMULATED`.
3. RFC-0041 read-side gaps were closed with repository-backed wave search/detail/item/proof-pack
   posture APIs before live proof was accepted.
4. Canonical startup now exports `DPM_MANAGE_POSTGRES_DSN` so wave, mandate, construction, and
   proof-pack repositories can use the same durable Postgres backing during live proof.
5. The RFC-listed cancel command was implemented instead of leaving cancellation as a state-machine
   only concept.

Evidence:

1. `scripts/generate_rfc0041_wave_evidence.py`
2. `output/rfc0041-wave-proof/20260504-231914/manifest.json`
3. `output/rfc0041-wave-proof/20260504-231914/critical-review.json`
4. `output/rfc0041-wave-proof/20260504-231914/critical-review.md`
5. `output/rfc0041-wave-proof/20260504-231914/17-openapi-certification.json`
6. `output/rfc0041-wave-proof/20260504-231914/18-aggregate-reconciliation.json`
7. `tests/unit/test_rfc0041_evidence_script.py`
8. `tests/unit/dpm/api/test_waves_api.py`
9. `tests/unit/dpm/construction/test_enrichment.py`
10. `tests/unit/api/test_dependencies.py`

Production boundary:

1. Slice 10 proves the manage backend authority, not the full front-office product experience.
2. Gateway and Workbench remained unpromoted until their implementation RFCs were executed and
   proven; first-wave command-center support is now implementation-backed in owning repos.
3. Automatic PM-book and CIO model-change cohort discovery are now source-backed through lotus-core
   products.
4. RFC-0041 proceeded to Slice 11 hardening and Slice 12 final closure after live proof passed.

## Slice 11 Hardening Review Result

Slice 11 performed the second-last production-readiness review across the manage wave authority,
endpoint contracts, documentation claims, tests, and proof posture.

Review findings fixed:

1. The RFC endpoint table overstated `GET /api/v1/rebalance/waves` filtering by mentioning book and
   PM filters. The implemented API is intentionally narrower and certified for `state`,
   `trigger_type`, `as_of_date`, derived `supportability_state`, `limit`, and `offset`. The RFC now
   states that book/PM filters remain deferred until an owning source product exists.
2. The trigger contract still used stale `MANUAL_PORTFOLIO_LIST` wording from the pre-hardening
   draft. It now matches the implemented `EXPLICIT_PORTFOLIO_LIST` contract.
3. The RFC supported-features ledger still read as pre-implementation promotion rules. It now records
   which explicit-list wave capabilities are implementation-backed and which CIO/PM/Gateway/
   Workbench capabilities remain unpromoted.

Hardening tests added:

1. `tests/unit/dpm/waves/test_source_readiness.py` covers missing mandate twins, missing/stale health,
   blocked source readiness, degraded readiness, pending-review health, ready health, and lineage
   filtering when a source lineage record id is absent.
2. `tests/unit/dpm/api/test_waves_api.py` now covers alternative-selection optimistic-lock conflict
   mapping to `DPM_WAVE_VERSION_CONFLICT`.

Validation:

1. `python -m pytest tests/unit/dpm/api/test_waves_api.py::test_wave_selection_translates_durable_write_conflict_to_governed_error tests/unit/dpm/waves/test_source_readiness.py -q`
2. `python -m pytest tests/integration/test_openapi_certification_matrix.py tests/unit/dpm/contracts/test_contract_openapi_supportability_docs.py tests/unit/test_documentation_current_state.py -q`
3. `python scripts/openapi_quality_gate.py`
4. `python scripts/api_vocabulary_inventory.py --validate-only`
5. `make check`

Slice 11 did not add new product claims. It tightened implementation-backed truth before Slice 12
final closure, wiki-publication governance, and gold-pass assessment marked RFC-0041 `DONE`.

## Post-Closure Audit Result - 2026-05-05

The post-closure slice-by-slice audit found one documentation-quality gap and no manage backend
implementation gap.

What was tightened:

1. The RFC aggregate, item, persistence, and index sections still carried pre-implementation field
   names for PM-book and CIO-model-change discovery that were intentionally deferred. The RFC now
   matches the implemented `DpmRebalanceWave`, `DpmRebalanceWaveItem`, and durable persistence
   contract in `src/infrastructure/postgres_migrations/dpm/0007_rebalance_waves.sql`.
2. The final gold-pass heading no longer reads as a template. It is the completed assessment for
   the delivered manage-owned explicit portfolio-list wave authority.
3. Documentation guardrail tests now fail if the RFC reintroduces unsupported
   `portfolio_manager_id` or `dpm_cio_model_change_impacts` claims before owning source products
   and downstream routes are implemented and proven.

Validation rerun:

1. `python -m pytest tests/unit/test_documentation_current_state.py tests/unit/dpm/api/test_waves_api.py tests/unit/dpm/waves/test_wave_domain.py tests/unit/dpm/waves/test_source_readiness.py -q`
2. `python -m pytest tests/integration/test_openapi_certification_matrix.py tests/unit/dpm/contracts/test_contract_openapi_supportability_docs.py -q`
3. `python scripts/openapi_quality_gate.py`
4. `python scripts/api_vocabulary_inventory.py --validate-only`

Front-office audit boundary:

1. Canonical front-office validation was attempted through
   `lotus-platform/automation/Invoke-Canonical-FrontOffice-QA.ps1` against
   `PB_SG_GLOBAL_BAL_001`.
2. The 2026-05-05 run reached canonical seed readiness, verified DNS, Gateway readiness, Workbench
   portfolio/performance routes, `lotus-manage` readiness, `lotus-manage` supportability summary,
   report integration capabilities, and Gateway workspace/performance/risk/advisor probes before
   failing browser validation with `Canonical Workbench browser validation failed with exit code 1`.
   Evidence is in
   `../lotus-platform/output/front-office-qa/canonical-front-office-qa-20260505-084445.json`,
   `../lotus-platform/output/front-office-qa/canonical-front-office-qa-20260505-084445.md`, and
   `../lotus-platform/output/front-office-qa/canonical-front-office-qa-20260505-084445.log`.
3. The failed live front-office result is not a manage RFC-0041 implementation failure: the manage
   readiness and supportability probes passed, and the failure occurred in downstream canonical
   Workbench browser validation outside the manage-owned wave authority.
4. RFC-0041 still does not claim Workbench wave command-center support because the downstream
   Gateway and Workbench realization RFCs are not implemented as runtime product surfaces.
5. Any canonical Workbench evidence captured during this audit is treated as stack/boundary
   evidence only, not as proof of a supported RFC-0041 wave UI.

Wiki decision:

1. No wiki source change is required for this post-closure audit. The wiki already states the
   implementation-backed manage boundary and keeps Gateway/Workbench wave product support
   unpromoted.

## Slice 12 Final Closure Result

Slice 12 closed RFC-0041 after implementation, live proof, hardening, documentation alignment, and
PR/wiki governance were complete.

Closure result:

1. RFC-0041 status is `DONE` for the manage-owned explicit portfolio-list wave backend authority.
2. The final gold-pass assessment in the RFC is complete and records completed scope, quality
   improvements, removed debt, platform/scaffold impact, cross-app evidence, certified APIs, live
   proof, documentation/wiki result, and residual deferred boundaries.
3. README, RFC index, repository engineering context, supported-features, wiki source, and endpoint
   certification pages are aligned to final implementation truth.
4. Skills/context/guidance decision is `no change needed`: existing Lotus backend delivery,
   endpoint certification, README/wiki governance, pre-merge gate, and front-office runtime skills
   were sufficient. No central context or AGENTS.md operating-contract update is required by this
   final closure slice.
5. Remaining unpromoted capabilities are explicit: broader campaign workflow surfaces beyond
   bounded campaign-definition retirement, global portfolio-universe campaign discovery, richer
   source-owner depth, and external execution.

Validation:

1. `python -m pytest tests/unit/test_documentation_current_state.py -q`
2. `python scripts/openapi_quality_gate.py`
3. `python scripts/api_vocabulary_inventory.py --validate-only`
4. `make check`

Wiki publication is required after the Slice 12 PR merges.

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

