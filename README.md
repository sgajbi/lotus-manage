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
Construction alternatives also preserve supplied source-owned risk/performance analytics context
for tracking error, drawdown, stress contribution, historical risk attribution, benchmark,
contribution, attribution, benchmark-relative performance, and currency attribution. The
`source_analytics_posture` names implemented source products from `lotus-risk` and
`lotus-performance`, while wave and proof-pack source analytics carry the supplied fields without
Manage calculating risk, performance, attribution, contribution, FX, predictive execution, or OMS
methodology locally.
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
the readiness, currency-exposure, hedge-policy, eligible-hedge-instrument, and market-data-scoped
FX forward-curve postures through stateful core sourcing and preserves them in currency-overlay construction
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
is implemented in `lotus-ai`, `lotus-gateway`, and `lotus-workbench`. Proof-pack report-input and
AI-evidence handoffs carry structured `DPM_PROOF_PACK_CLIENT_COMMUNICATION_BOUNDARY` evidence so
downstream consumers can see that proof packs support internal review only, not client contact,
client-ready message generation, client approval, delivery confirmation, or communication audit
truth. The post-merge gold-pass audit
also records a canonical front-office risk-drawdown `partial` boundary tracked as
`sgajbi/lotus-gateway#182`, so no unsupported proof-pack source enrichment is claimed here.
The portfolio-memory API now publishes source-event family posture for supported manage, report,
AI, and archive families, explicitly marks OMS execution as deferred, and points PM scoring to the
separate Manage-owned PM operating quality score-run lifecycle product. Persisted PM quality score
runs with source-owned Core PM-book membership now project bounded portfolio-memory lineage events,
review actions over those runs project bounded supervisory events, and support-summary invocations
over those runs project bounded workflow-lineage events for matching portfolios without copying raw
score payloads, raw review rationale, generated summary text, prompt bodies, model responses, or
creating portfolio-level rankings or downstream summary UX. The
portfolio-memory API also exposes `GET /api/v1/rebalance/portfolio-memory/search` as a bounded
Manage-local index over persisted proof-pack, wave, monitoring-exception, campaign-definition,
outcome-review, PM-quality, and explicit caller-supplied portfolio identifiers. Search responses
include pre-pagination facet counts for portfolio aggregate supportability state, matched event
type, matched-event supportability state, matched-event source systems, matched-event source
types, and represented source system plus matching-event context and stable matching-event
identity/source coordinates so
consumers can distinguish the latest overall memory event, aggregate portfolio posture, and
portfolio-level source-system coverage from the specific event that satisfied an event/source
filter without loading every portfolio timeline. The optional `supportability_state` query filter
is aggregate-only and does not filter matching-event metadata or matching-event facet counts. The
optional `source_type` query filter searches the same Manage-local matching-event source type,
source refs, and artifact refs used for those facets; it is not a global cross-app source-event
search.
Gateway PR #242 and Workbench PR #350 realize these bounded source-lineage filters and facets
downstream through Gateway-only portfolio-memory search consumption without broadening Manage into
global portfolio-universe discovery or cross-app source-event search.
Portfolio-level source-system coverage includes event owners, source refs, and artifact refs so
report, AI, and archive handoff evidence is not hidden from audit search facets. Search scans each
supported Manage-local source family once per bounded request, groups projected events by candidate
portfolio, and reports exact `total_count` and facet counts over that bounded source-family scan;
those counts are not a claim over a global portfolio universe. Pagination metadata also returns
`has_more`, `next_offset`, the normalized `applied_filters` echo, and the `source_scan_limit` used
for each Manage-local evidence repository so consumers can continue bounded searches without
reconstructing continuation logic, filter posture, or scan-cap posture from counts. Search pages
validate returned-count, total-count, has-more, next-offset, supportability-count,
source-system-count, and matching-event-count posture against the returned rows. Each
portfolio-memory view and search page carries a deterministic `content_hash`
that excludes `generated_at` so audit review can reconcile equivalent source-backed views and
result pages without timestamp churn. Portfolio-memory aggregate event count, event-type counts,
source-system coverage, reason-code rollups, supportability state, and governance posture are
validated against returned event rows so audit consumers do not receive inconsistent summary truth.
Proof-pack and outcome-review report and AI evidence
handoff contexts preserve the source memory view hash, expose an explicit no-claim
`support_boundary`, and also expose a bounded `context_content_hash` over the report-safe event
refs with Manage lookup `event_id`, source-backed `event_identity`, event timestamps, and selection
ranks plus explicit event-ref limit, selection policy, returned-count, omitted-count, and
truncation posture. `event_id` addresses
`GET /api/v1/rebalance/portfolio-memory/{portfolio_id}/events/{event_id}` for exact Manage
drilldown; `event_identity` remains the cross-app lineage identity. Those bounded counters are
non-negative, selection ranks are contiguous and one-based, and the governance policy must carry
identity-scheme, retention, redaction, audit, access, and source-authority posture. Per-event
retention, redaction, audit, and access fields must match that governance envelope, so downstream consumers can reconcile
lineage context without loading the full memory view or inferring raw source, OMS, client
communication, global-discovery, or source-methodology support.
Portfolio-memory text filters are trimmed before validation and matching, and blank text filters
are treated as absent, so audit consumers can rely on the echoed filter posture rather than raw
query-string formatting.
`GET /api/v1/rebalance/portfolio-memory/{portfolio_id}/events/{event_id}` provides the bounded
drilldown counterpart for those search hits: it returns the exact source-backed memory event,
event identity, memory content hash, replay-stable lookup envelope hash, and no-claim boundary
without querying external source-owner event stores or projecting OMS, client communication, risk,
performance, report, archive, or AI truth.
Unsupported event-type filters are rejected at the API boundary instead of being interpreted as an
empty source result. Empty supportability summaries are returned only for explicit caller-supplied
portfolio identifiers when `supportability_state=EMPTY` is requested; the search route is not
global portfolio-universe discovery and does not project OMS acknowledgement, fill, settlement, or
execution-status events. Persisted bulk-review campaign definitions now project
bounded portfolio memory events for definition, approval-decision, assignment-action,
assignment-task, and maker-checker control evidence without copying raw campaign payloads,
recalculating membership, or claiming external workflow orchestration, client contact, order
routing, or OMS execution. The
portfolio-memory response also carries structured
`DPM_PORTFOLIO_MEMORY_EXTERNAL_EXECUTION_BOUNDARY` evidence naming blocked OMS capabilities, the
required future execution/OMS owner, and `ExternalOrderExecutionAcknowledgement:v1` as the required
future source product before acknowledgement, fill, settlement, or execution-status events can be
projected; it also lists promotion requirements for certified OMS source ownership,
source-product contracts, lineage/freshness, acknowledgement/fill/settlement reconciliation,
Manage consumer declaration, Gateway/Workbench realization, and operations audit evidence. It also carries structured
`DPM_PORTFOLIO_MEMORY_CLIENT_COMMUNICATION_BOUNDARY` evidence naming blocked client-contact,
message-generation, delivery-confirmation, client-approval, and communication-audit capabilities,
the required future client-communication owner, and `ClientCommunicationRecord:v1` as the required
future source product before any client communication events can be projected; it lists promotion
requirements for certified communication source ownership, source-product contracts,
lineage/freshness, delivery/approval/audit reconciliation, Manage consumer declaration,
Gateway/Workbench realization, and consent/evidence controls.
RFC-0041 is implementation-backed and closed as `DONE`
for manage-owned explicit portfolio-list rebalance waves: durable preview/create/source-check,
RFC-0039-backed ready-item simulation, RFC-0040 proof-pack linkage, approval-with-exceptions,
internal handoff evidence, retrieve/search/item/proof-pack/report-input/supportability read models, and
Postgres-backed evidence under `output/rfc0041-wave-proof/20260504-231914`. Gateway composition,
Workbench first-wave command-center UX, and wave report materialization in `lotus-report`,
`lotus-render`, and `lotus-archive` are implementation-backed, merged, validated, and
wiki-published. Wave proof-pack posture and report-input contracts now also carry
`DPM_WAVE_CLIENT_COMMUNICATION_BOUNDARY` evidence, with promotion requirements for a future
`ClientCommunicationRecord:v1` owner, delivery/approval/audit reconciliation, consent/evidence
controls, and downstream realization before any client-contact, client-message, client-approval,
delivery-confirmation, or communication-audit capability can be promoted. `BULK_REVIEW_CAMPAIGN`
wave report inputs now also carry nullable `DPM_WAVE_CAMPAIGN_UNIVERSE_BOUNDARY` evidence when
applicable, making persisted-definition-only discovery, deferred global-universe source ownership,
required `GlobalPortfolioUniverseCampaignCandidateSet:v1`, blocked bank-wide scan/candidate
discovery/source-fact recalculation/membership recomputation capabilities, and no-order/no-OMS
operating boundaries machine-readable for report, archive, and AI consumers. PM-book cohort discovery
is implemented for `PM_BOOK_REVIEW` through the
source-owned lotus-core `PortfolioManagerBookMembership:v1` product; CIO model-change discovery is
implemented through `CioModelChangeAffectedCohort:v1`; and bounded risk-event discovery is
implemented for `RISK_EVENT` through lotus-risk `RiskEventAffectedCohort:v1` over caller-supplied
candidate portfolios with source-supplied exposure weights. Bounded bulk-review campaign
membership is implemented for `BULK_REVIEW_CAMPAIGN` through Manage-owned
`BulkReviewCampaignMembership:v1` over source-backed candidate portfolios with source-owned
portfolio type, DPM portfolio-type filtering, deterministic membership refs, optional
approval/expiry/actor-entitlement governance evidence, immutable
`BulkReviewCampaignDefinition:v1` definitions over source-backed candidate sets, and fail-closed
validation. `BULK_REVIEW_CAMPAIGN` preview/create can also resolve its candidate set from
lotus-core `DpmPortfolioUniverseCandidate:v1` by setting
`campaign_candidate_source=CORE_DPM_PORTFOLIO_UNIVERSE`; Manage preserves Core candidate lineage,
rejects caller-supplied portfolios for that mode, walks bounded continuation pages to terminal
exhaustion, and fails closed on unavailable, incomplete, degraded, empty, duplicate,
non-terminating, or still-truncated Core pages without claiming relationship householding, global
portfolio-universe ownership, PM ranking, external workflow orchestration, OMS execution, or client
communication workflow. Tactical house-view wave discovery is implemented for `TACTICAL_HOUSE_VIEW` through
lotus-advise `TacticalHouseViewAffectedCohort:v1` over caller-supplied source-backed candidate
portfolios; Manage preserves Advise cohort refs and fails closed without recomputing house-view,
holdings, exposure, alignment, or mandate facts. Workbench now renders the first-wave active
campaign-definition list through Gateway/BFF without recalculating campaign membership. Manage now
also exposes persisted campaign discovery at
`GET /api/v1/rebalance/waves/campaign-discovery`, summarizing `BulkReviewCampaignDefinition:v1`
identity, governance posture, expiry posture, source-ref count, and source-backed candidate counts
without discovering the global portfolio universe or recalculating membership. Each row carries
hashed `BulkReviewCampaignUniversePosture:v1` evidence naming `PERSISTED_DEFINITION_ONLY`
discovery mode, deferred source ownership, required future
`GlobalPortfolioUniverseCampaignCandidateSet:v1`, blocked bank-wide candidate-discovery
capabilities, and promotion requirements for any future global-universe support. Manage also supports
an operating queue at `GET /api/v1/rebalance/waves/campaign-operating-queue`, classifying persisted
definitions as ready to launch, attention required, or closed from existing discovery,
preview-readiness, lifecycle, and launch-history posture without creating maker-checker or OMS
claims. Manage also supports
an approval attention inbox at `GET /api/v1/rebalance/waves/campaign-approval-inbox`, classifying
persisted definitions as approval complete, approval required, approval incomplete, expiry
attention, entitlement attention, or closed from existing governance evidence and readiness posture
without mutating approval state, mutating maker-checker control state, approving trades, generating
orders, or claiming OMS execution. Manage also supports a read-only cross-actor workflow board at
`GET /api/v1/rebalance/waves/campaign-workflow-board`, composing the operating queue and approval
inbox into actor-aware next-action rows for launch, approval-decision capture, approval evidence
remediation, expiry refresh, entitlement review, or closed posture without discovering the global
portfolio universe, mutating approval state, mutating maker-checker control state, approving trades,
generating orders, or claiming OMS execution. Manage also supports a read-only assignment and
escalation plan at `GET /api/v1/rebalance/waves/campaign-assignment-plan`, deriving actor routing,
escalation tier, SLA posture, and reason codes from the workflow board without mutating assignment
state, creating escalation tasks, mutating maker-checker control state, approving trades, generating
orders, or claiming OMS execution. Manage also supports read-only workflow automation readiness at
`GET /api/v1/rebalance/waves/campaign-workflow-automation`, composing assignment-plan posture and
existing controlled assignment-task state into deterministic candidates for opening, monitoring, or
escalating Manage-owned assignment tasks without mutating tasks, orchestrating external workflow,
contacting clients, mutating maker-checker control state, approving trades, generating orders, or
claiming OMS execution. The response includes machine-readable `capability_posture` so consumers
can distinguish supported Manage assignment-task readiness and controlled endpoint-only task
mutation from unsupported external workflow orchestration; the posture names blocked external
workflow task creation, assignment, synchronization, escalation, and completion capabilities,
requires future `ExternalWorkflowOrchestrationRecord:v1` source ownership, lists the promotion
requirements for certified source ownership, source-product contracts, lineage/freshness,
consumer declaration, Gateway/Workbench realization, and external workflow audit/reconciliation
evidence, and carries a deterministic content hash. Campaign operating queue, approval inbox,
workflow board, assignment plan, and workflow automation pages validate returned row count, page
limit/offset, and posture/action count maps against the returned rows so audit summaries cannot
drift from the page payload. Append-only approval-decision, assignment-action, assignment-task,
maker-checker-control, and launch-history pages also validate returned row count, page
limit/offset, assignment-task count-map coverage, open-task coverage, and launch-history total-count
window posture so audit evidence cannot carry internally inconsistent summaries. Campaign workflow
evidence persistence uses the caller's base campaign-definition content hash as an optimistic
compare-and-set guard; same-ref replay remains idempotent, while independently stale appends return
HTTP 409 with `BULK_REVIEW_CAMPAIGN_DEFINITION_STALE_WRITE` rather than overwriting newer audit
evidence. PostgreSQL also maintains the derived
`dpm_bulk_review_campaign_workflow_read_model` projection from the durable campaign definition
payload. The projection materializes board status, next action, assignment escalation tier, SLA
posture, assigned actors, assignment task statuses, maker-checker outcomes, evidence counts, and
lineage hashes for indexed operator filtering. `payload_json` plus `content_hash` remains the
durable evidence source; the projection is rebuildable from the parent definition and does not
authorize edits, create external workflow tasks, approve trades, route orders, contact clients, or
claim OMS execution. Manage also supports append-only
assignment and escalation actions at
`POST /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/assignment-actions`
plus listing them at the same route with `GET`, mutating assignment posture evidence only with
assigned actors, escalation tier, SLA posture, correlation id, source refs, deterministic action ids,
conflict-safe action refs, and the campaign actor allow-list when supplied; it does not mutate approval state, mutate maker-checker control state,
approve trades, generate or route orders, contact clients, or claim OMS execution. Manage also supports
controlled assignment and escalation tasks at
`POST /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/assignment-tasks`,
task transitions at
`POST /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/assignment-tasks/{task_ref}/transitions`,
and task listing at
`GET /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/assignment-tasks`,
mutating only Manage-side assignment task state with append-only transition evidence, current
status, assignees, escalation tier, SLA posture, due-date posture, deterministic task/transition
ids, conflict-safe refs, and command-actor allow-list enforcement when supplied; it does not mutate approval state, mutate maker-checker control state,
approve trades, generate or route orders, contact clients, orchestrate external workflow systems,
or claim OMS execution. Manage also supports
append-only maker-checker control evidence at
`POST /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/maker-checker-controls`
plus listing it at the same route with `GET`, requiring distinct submitter and reviewer actors for
completed reviews, enforcing fail-closed submission/reviewer/completion and open-exception
sequencing, and enforcing the command actor allow-list when supplied while avoiding trade
approval, order generation/routing, client contact, external workflow orchestration, or OMS claims.
Manage also supports
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
without trade approval, order generation/routing, client contact, maker-checker control-state mutation, or OMS
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
if durable wave creation succeeds but launch-history persistence returns a 409 stale-write
conflict, retrying the same launch request reuses the existing wave through the deterministic
idempotency key and repairs the missing launch audit without creating another wave;
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
source-lineage source-owner/source-type filters and facets over persisted review lineage,
source-refresh eventing, report-input and AI-evidence handoff contracts, supportability telemetry,
deduplicated AI-evidence source lineage across review, snapshot, dimension-result, and metric-level
refs, and live canonical manage proof under `output/rfc0042-outcome-proof/20260505-024352`; Slice 12
hardening proof under `output/rfc0042-outcome-proof/20260505-025613` adds idempotency conflict and
state-filter validation evidence. The Lotus-owned RFC37-WTBD-001 outcome-feedback loop is now
closed for the first-wave product path: Gateway/Workbench realization, report/render/archive
materialization, governed AI narrative support, PM operating quality linkage, and bounded
source-lineage filters/facets are merged in their owning repositories. Richer realized methodology
depth remains RFC42-WTBD-006, and external OMS/client-communication runtime promotion remains an
unsupported external-owner dependency. Gateway PR #242 and Workbench PR #350 realize the
already-supported bounded outcome-review source-lineage filters and facets through Gateway-only
downstream consumption. RFC-0043 is
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
client-contact, trade, order, OMS, or execution claims. Support-summary invocations over those
score runs are visible as bounded `PM_QUALITY_SUMMARY_INVOCATION` lineage events that preserve
score-run and review-action identity, state-specific workflow, artifact, hash, or bounded failure
evidence, and the summary-text boundary posture without storing or exposing generated summary
text, reconstructing prompts or model responses, projecting downstream summary UX, ranking PMs,
contacting clients, approving trades, routing orders, or claiming OMS execution. The
fairness-analysis route family now
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
execution, or OMS decisions. Gateway/Workbench downstream PM-quality realization is implemented
through bounded Gateway BFF composition and Gateway-only Workbench policy, score-run,
fairness-analysis, support-summary, review-action ledger/detail, and preview-before-create
supervisory review-action UX.
The review-action route family now supports preview and immutable create/read/list lifecycle at
`POST /api/v1/rebalance/pm-operating-quality/review-actions/preview`,
`POST /api/v1/rebalance/pm-operating-quality/review-actions`,
`GET /api/v1/rebalance/pm-operating-quality/review-actions`, and
`GET /api/v1/rebalance/pm-operating-quality/review-actions/{review_action_id}`. It emits
bounded `PmOperatingQualityReviewAction:v1` ledger rows over existing score-run or
fairness-analysis evidence, preserving target content hashes and bank review references without
mutating score runs, recomputing fairness posture, ranking PMs, creating HR/compensation/conduct
decisions, contacting clients, approving trades, routing orders, or claiming OMS execution. Each
row carries structured `PM_QUALITY_APPROVAL_WORKFLOW_BOUNDARY` evidence with a deterministic
content hash, proving that immutable review-action evidence is not a CIO approval workflow,
policy approval, client approval, trade approval, HR/conduct decision, order route, or OMS
execution claim.
The support-summary history route family now supports review-gated preview and immutable
create/read/list lifecycle at
`POST /api/v1/rebalance/pm-operating-quality/summary-invocations/preview`,
`POST /api/v1/rebalance/pm-operating-quality/summary-invocations`,
`GET /api/v1/rebalance/pm-operating-quality/summary-invocations`, and
`GET /api/v1/rebalance/pm-operating-quality/summary-invocations/{summary_invocation_id}`. It emits
bounded `PmOperatingQualitySummaryInvocation:v1` rows over persisted score-run and review-action
evidence. `REQUESTED` rows may carry downstream workflow-run handoff identity but no result or
failure evidence; `COMPLETED` rows require workflow run, artifact reference, and `sha256:` content
hash; `FAILED` rows require workflow run plus a non-sensitive `failure_reason_code` and reject
completed artifact evidence. Manage records append-only invocation state without storing generated
AI narrative text, exposing raw review rationale, recalculating scores, recomputing fairness,
ranking PMs, creating HR/compensation/conduct decisions, contacting clients, approving trades,
routing orders, or claiming OMS execution. Each row carries structured
`PM_QUALITY_SUMMARY_TEXT_BOUNDARY` evidence with a deterministic content hash, proving Manage
records invocation history only and does not store or expose generated summary text, project
downstream summary UX, reconstruct prompts or model responses, generate client messages, approve
trades, route orders, or claim OMS execution.
`lotus-gateway` PR #213 (`62ce4c4`) now exposes the bounded PM operating quality BFF route family at
`/api/v1/dpm/command-center/pm-operating-quality/*`, forwarding Manage policy and score-run
payloads without calculating scores, ranking PMs, administering policy locally, or creating HR,
compensation, conduct, approval, client-contact, execution, or OMS decisions. `lotus-gateway`
PR #234 (`c74b3e1514e8875d1cf7a479280e9deddd51a8db`, Main Releasability Gate `26163382026`)
adds bounded PM-quality review-action preview/create/list/get BFF routes, and Gateway PR #239
(`c4f007d`) adds bounded PM-quality summary-invocation preview/create/list/get BFF routes.
`lotus-workbench`
PR #245 (`2af063b`) implements the Gateway-only policy, score-run, fairness-analysis, and
support-summary surface, and Workbench PR #302 (`8052d92`) plus PR #303 (`3581b04`) implement
read-only PM-quality review-action ledger/detail rendering. Workbench PR #314 (`6bd43c8`) adds
Gateway-only PM-quality review-action preview-before-create command UX, PR #315 (`806193f`)
extracts the bounded command-control component, PR #316 (`fdc37b5`) extracts the PM-quality API
module, Workbench PR #341 (`667d18c`) renders persisted summary-invocation list/detail evidence,
PR #342 (`565a555`) adds the Gateway-only summary-invocation command path, PR #343 (`d0e1464`)
adds source-backed command target selectors, and PR #344 (`39993d4`) adds focused test hardening
for the summary-invocation control rather than a new product capability.
`lotus-ai` PR #70 (`1951f62`) adds `pm_quality_summary.pack@v1` for review-gated support-only
summaries over Manage-owned `PmOperatingQualityScoreRun` evidence. The pack validates score-run
identity, source refs, supportability posture, optional bounded portfolio-memory context, and
forbidden-use controls, and it must not calculate scores, rank PMs, generate HR/compensation/
conduct decisions, contact clients, approve trades, route orders, claim execution, or invent
missing source facts. Gateway/Workbench support-summary product invocation, summary-invocation
list/detail/command realization, and Workbench review-action preview-before-create command UX are
implemented through the Gateway and Workbench PM-quality realization path above.
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
- idea action-intake route foundation
  `/api/v1/rebalance/idea-action-intake` accepts source-safe `lotus-idea`
  conversion-intent handoff evidence and returns a not-certified acknowledgement. It does not
  create action-register records, approve rebalances, create orders, route OMS instructions,
  contact clients, authorize publication, or promote a supported feature.
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
   report-input, and AI-evidence handoffs only, including promotion requirements for certified
   OMS source ownership, reconciliation controls, consumer declaration, and downstream realization.
   Manage does not generate orders, route venues, certify best execution, ingest OMS
   acknowledgements, confirm fills, project settlement, or reconcile execution status.
10. outcome-review search exposes bounded source-owner and source-type filters plus facets over
    persisted review lineage only. It does not query source-owner stores, recalculate realized
    source truth, project OMS execution events, or create client-communication workflow evidence.
11. outcome-review supportability, report-input, and AI-evidence handoffs also expose structured
    `DPM_OUTCOME_CLIENT_COMMUNICATION_BOUNDARY` evidence. Manage may support internal PM, CIO,
    compliance, operations, report, and AI review workflows, but it does not contact clients,
    generate client-ready messages, collect client approval, confirm delivery, or certify client
    communication audit truth; the boundary lists the source-owner, delivery/audit, consent, and
    downstream realization requirements before promotion. AI-evidence handoff source refs are bounded to persisted
    outcome-review lineage and deduplicated review, snapshot, dimension-result, and metric-level
    evidence refs.
12. wave proof-pack posture and report-input handoffs expose structured
    `DPM_WAVE_CLIENT_COMMUNICATION_BOUNDARY` evidence. Manage wave evidence stops at internal
    operations handoff and does not contact clients, generate client-ready wave messages, collect
    client approval, confirm delivery, or certify communication audit truth.
13. proof-pack report-input and AI-evidence handoffs expose structured
    `DPM_PROOF_PACK_CLIENT_COMMUNICATION_BOUNDARY` evidence with the same source-owner,
    delivery/audit, consent, and downstream-realization promotion bar.
14. bulk-review campaign wave report-input handoffs expose structured
    `DPM_WAVE_CAMPAIGN_UNIVERSE_BOUNDARY` evidence when the trigger is
    `BULK_REVIEW_CAMPAIGN`. Manage preserves persisted source-backed campaign-definition
    candidates only and does not discover the global portfolio universe, recalculate source facts,
    recompute membership, generate orders, or claim OMS execution.
15. PM operating-quality review actions expose structured
    `PM_QUALITY_APPROVAL_WORKFLOW_BOUNDARY` evidence. Manage records immutable review-action
    ledger rows over existing score-run or fairness-analysis evidence only; it does not mutate
    approval workflow state, approve policies or trades, contact clients, create HR or conduct
    decisions, route orders, or claim OMS execution.
16. PM operating-quality summary invocations expose structured
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
