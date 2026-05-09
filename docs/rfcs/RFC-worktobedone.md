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

The WTBD ledger is now used as a product-readiness control surface, not only an engineering
planning artifact. `wiki/Supported-Features.md` is updated in this slice with an
implementation-backed DPM product-readiness view, integration diagram, and next-priority WTBD
sequence suitable for developers, operations, business stakeholders, sales/pre-sales, and client
demo preparation. The wiki remains careful not to promote unfinished WTBDs as supported features.

## Mainline WTBD Control Snapshot

Snapshot basis: the RFC39-WTBD-004 / RFC40-WTBD-008 source-backed restriction and sustainability
slice after the source-owner `lotus-core` `ClientRestrictionProfile:v1` and
`SustainabilityPreferenceProfile:v1` products and the `lotus-manage` consumer are merged,
validated, and wiki-published.
The canonical DPM command-center seed still proves populated source-ready `ready`,
selector-driven `partial`, and empty-date `empty` postures while `lotus-manage` exposes bounded
ready/degraded/blocked source-readiness states for downstream consumers. RFC40-WTBD-007 adds
source-owned observed transaction-cost evidence through `TransactionCostCurve:v1`; RFC39-WTBD-006
adds a bounded `COST_AWARE` construction method that applies observed cost bps to candidate trade
notionals for comparison evidence; and RFC39-WTBD-004/RFC40-WTBD-008 add source-backed
restriction/sustainability profile consumption. Manage can block candidate trades that violate hard
client restrictions and preserve sustainability preference evidence in construction alternatives
and proof packs, while sustainability classification evidence gaps remain pending review. It does
not promote predictive execution-cost quotes, market impact modelling, venue routing, broader
execution methodology, or unsupported ESG approval.

| Control | Count | Meaning |
| --- | ---: | --- |
| Total WTBD items | 59 | RFC-0036 through RFC-0042 follow-up items tracked in this ledger. |
| Done on merged/published truth | 35 | Implementation-backed items merged to owning `main` branches, validated, and published where wiki truth changed. |
| Partial / in progress | 4 | Items with meaningful implementation-backed progress but known source-owner or downstream gaps. |
| Remaining / open | 20 | Items still deferred, proposed, conditional, unsupported, or awaiting ownership. |

Partial / in-progress items:

| ID | Current partial scope | Remaining gap |
| --- | --- | --- |
| RFC37-WTBD-001 | `lotus-manage` RFC-0042 backend authority and first-wave outcome product path are implemented. | Complete richer downstream/source-owner realization across all outcome learning loops. |
| RFC40-WTBD-009 | First-wave regime scenario evidence exists through RFC-0039 selected alternatives. | Direct proof-pack scenario contribution, CIO approval, and richer source-owner proof-pack enrichment remain future work. |
| RFC40-WTBD-010 | `lotus-manage` exposes `/api/v1/rebalance/portfolio-memory/{portfolio_id}` as a deterministic source-backed read model over mandate health snapshots, monitoring exceptions, proof packs, proof-pack timelines, rebalance waves, internal handoffs, and outcome-review events; `lotus-gateway` composes it for the command center; and `lotus-workbench` renders the first-wave portfolio-memory timeline with canonical browser proof. Manage now also emits stable event identity plus retention, redaction, access, and audit policy in the API contract. `lotus-report` PR #92 adds the report-side consumer seam for bounded `portfolio_memory_context` lineage in proof-pack, wave, and outcome report jobs. Manage report-input APIs now attach bounded portfolio-memory context for proof-pack, rebalance-wave, and outcome-review reports without folding that context into recursive report-input hashes. `lotus-ai` PR #62 adds bounded DPM PM memo and outcome-review narrative consumers that validate portfolio identity, capped event refs, `NO_RAW_PAYLOADS`, source content hash, and no-reconstruction source-authority policy before exposing compact lineage summaries. | Future report, AI, OMS, PM-scoring, and client-communication source-event families still need owning-app implementation before the broader portfolio-memory WTBD can be closed. |
| RFC42-WTBD-006 | Selected risk, performance, core tax/cash/FX/cashflow source-family adapters are implemented. `lotus-performance` has now tightened source-owner MWR methodology truth for stateful lotus-core input resolution, carry-forward capital adjustments, fee exclusion, supportability outputs, and downstream no-reconstruction boundaries in methodology docs and wiki source. It has also tightened contribution methodology truth for stateful lotus-core portfolio/position timeseries normalization, total/local/FX contribution ownership, source currency metadata, supportability outputs, and downstream no-reconstruction boundaries. | Aggregated risk/performance, tax, FX, cash movement, liquidity, and execution methodologies remain source-owner work. |

Next bank-buyable product-readiness priorities:

| Priority | WTBD | Why this is next | Promotion bar |
| ---: | --- | --- | --- |
| 1 | RFC40-WTBD-010 - Decision timeline and portfolio memory | Links mandate, exception, wave, proof-pack, handoff, outcome, and report-input lineage into portfolio memory without inventing source truth. First-wave Manage/Gateway/Workbench product realization is merged, live-proven, and wiki-published; manage now emits mandate-health, monitoring-exception, event identity, retention, redaction, access, audit policy, and bounded report-input context; `lotus-report` has the report-side bounded context consumer; and `lotus-ai` has bounded DPM memo/narrative consumers. | Future source-event families are implemented by their owners, tested, and canonically proven without reconstructing source facts. |
| 2 | RFC42-WTBD-006 - Source-owner realized methodology depth | Promotes aggregate risk, performance, tax, FX, cash, liquidity, and execution methodology from selected adapters into auditable source-owned products. Current source-owner slices tighten the `lotus-performance` MWR and contribution methodology/wiki truth so stateful source resolution is auditable and downstream consumers cannot reconstruct cash-flow schedules or position contribution locally. | Owning services provide methodology docs, contracts, degraded-state tests, live proof, and product-surface preservation without manage-local recalculation. |
| 3 | RFC41-WTBD-003 - Tactical house-view, risk-event, and implicit campaign cohorts | Moves the rebalance wave operating model toward bank operating workflows without inventing source-owned cohorts. | Source owners publish governed cohort discovery products; manage consumes them with fail-closed dependency handling, proof-pack/wave preservation, and downstream product evidence. |

Execution rule:

Do not open a new WTBD implementation slice until the current slice has passed local validation,
GitHub required checks, PR merge, wiki publication where needed, final `git fetch origin --prune`
plus `git branch -r --no-merged origin/main`, and clean branch/status hygiene.

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
| RFC36-WTBD-002 | Workbench product surfaces over stateful manage execution | `lotus-workbench` through Gateway/BFF | Completed and merged to `lotus-workbench` `main` in PR #152 (`c83ea7e`) | Workbench now surfaces Gateway-provided manage rebalance action-register supportability without direct manage calls or locally invented source readiness. |
| RFC36-WTBD-003 | Portfolio-level DPM operation dashboards over stateful executions | `lotus-gateway`, `lotus-workbench`, `lotus-manage` | Completed, merged, live-proven, and wiki-published through `lotus-gateway` PR #192/#193 and `lotus-workbench` PR #153 | RFC-0036 certified execution/source posture. This follow-up now promotes recent-run and supportability telemetry into the Gateway BFF and Workbench product surface without making Workbench call manage directly. |
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

Closure status:

Completed on 2026-05-06 through `lotus-workbench` PR #152,
`feat: surface manage rebalance supportability`, merged to `main` at
`c83ea7e136dd00cae1042cb9597fd2c42b634d56`.

What was delivered:

1. Extended the Workbench overview `rebalance_snapshot` type so the UI can consume
   Gateway-provided manage action-register supportability without a direct `lotus-manage` call.
2. Rebuilt the `/workbench/{portfolioId}` rebalance status panel to render manage-owned status,
   source support state, freshness, run count, operation count, workflow decision count,
   last-run identity, and reason posture.
3. Added explicit unknown/N/A handling when Gateway omits action-register supportability so
   missing source context is not misrepresented as verified zero activity.
4. Added focused unit coverage for ready, source-incomplete, and missing-supportability postures.
5. Updated `lotus-workbench` repository context and repo-authored wiki source so product,
   operator, and engineering material reflects the implementation-backed behavior.

Validation evidence:

1. Local targeted proof:
   `npx vitest run tests/unit/rebalance-status.test.tsx` passed with 3 tests.
2. Local type proof: `npm run typecheck` passed.
3. Local repo gate: `make check` passed in `lotus-workbench`, including lint, typecheck,
   156 test files / 707 tests with coverage, and production build.
4. Live canonical proof:
   `powershell -ExecutionPolicy Bypass -File scripts/live/Start-LotusFrontOfficeCanonical.ps1 -LocalApps workbench -RunValidation -ScreenshotDirectory output/playwright/rfc36-wtbd002-rebalance-status`
   passed for `PB_SG_GLOBAL_BAL_001` after the governed seed completed.
5. Targeted live browser assertion against
   `http://workbench.dev.lotus/workbench/PB_SG_GLOBAL_BAL_001` proved the rebalance panel rendered
   status, source support, freshness, evidence counts, and the explicit missing-supportability
   message from the live Gateway payload.
6. GitHub PR #152 checks passed before merge: Feature Lane lint/typecheck/test, Feature Lane
   workflow lint, PR Merge Gate workflow lint, lint/typecheck/coverage/build, Playwright smoke,
   Docker build validation, CI local Docker parity, and queue auto-merge.
7. `lotus-workbench` wiki publication completed after merge; `Sync-RepoWikis.ps1 -CheckOnly
   -Repository lotus-workbench` passed after publishing.

Gold-pass assessment:

This WTBD has reached the expected standard for its stated scope. The Workbench implementation is
merged to `main`, the UI remains Gateway/BFF-only, source-incomplete and missing-supportability
states are explicit, the behavior is protected by unit tests and full local/GitHub gates, canonical
front-office evidence was captured, and repo-local plus published wiki material now reflects the
implementation-backed product behavior.

#### RFC36-WTBD-003 - Portfolio-Level DPM Operation Dashboards

Target business outcome:

Operations and PM users can monitor stateful DPM execution supportability, source readiness,
recent runs, errors, and workflow posture at portfolio/book level.

Closure status:

Completed on 2026-05-06 through the coordinated downstream implementation wave:

1. `lotus-gateway` PR #192, `feat: expose DPM operations dashboard data`, merged to `main` at
   `df428d62e0d54501696afcfd7014b378765e02a9`.
2. `lotus-workbench` PR #153, `feat: render DPM operations dashboard`, merged to `main` at
   `3cbc68895eb098e147d9b0f85a7ceaea5e883fb4`.
3. `lotus-gateway` corrective PR #193,
   `fix: map manage supportability into workbench snapshot`, merged to `main` at
   `8afa4d3e9e58f2d60d9e10a9c7bb92fd8fe18ca9` after canonical evidence exposed that live
   manage supportability came from `/api/v1/rebalance/supportability/summary`, not the rebalance
   run list payload.

What was delivered:

1. `lotus-gateway` now enriches the Workbench overview `rebalance_snapshot` with recent manage
   rebalance runs from `/api/v1/rebalance/runs?portfolio_id=<portfolio>&limit=5`.
2. `lotus-gateway` now fetches live manage action-register supportability from
   `/api/v1/rebalance/supportability/summary` and maps it into the same Gateway-owned
   Workbench BFF snapshot without requiring Workbench to call manage directly.
3. Gateway parsing preserves bounded telemetry: rebalance run id, status, workflow status,
   portfolio id, timestamps, source/error labels, and supportability state/count/freshness posture.
4. `lotus-workbench` extends the rebalance status panel to show operations-facing recent-run
   counts, issue counts, latest run rows, workflow posture, error/source labels, and an explicit
   no-runs state.
5. Product documentation, repository context, and repo-local/published wiki truth were updated in
   the owning Gateway and Workbench repositories. This `lotus-manage` ledger records closure only;
   no additional `lotus-manage` wiki source change is required for this slice.

Validation evidence:

1. Gateway PR #192 local targeted proof passed with 3 tests, and `make check` passed with Ruff
   lint, Ruff format check, monetary-float guard, mypy, Workbench contract smoke, and 423 tests.
2. Gateway PR #193 local targeted proof passed with 2 tests; broader focused regression proof
   passed with 54 tests across Workbench service unit, integration, and contract coverage; final
   `make check` passed with Ruff lint, Ruff format check, monetary-float guard, mypy, Workbench
   contract smoke, and 424 tests.
3. Workbench PR #153 local targeted proof passed with 7 tests; `npm run typecheck` passed; final
   `make check` passed with lint, typecheck, 156 test files / 707 tests, coverage, and production
   build.
4. GitHub CI was green before merge for Gateway PR #192, Workbench PR #153, and Gateway PR #193,
   including Feature Lane checks, PR Merge Gate checks, Docker/parity gates where configured, and
   queue auto-merge.
5. `lotus-gateway` wiki publication completed for PR #192 at wiki commit `778e992` and for PR #193
   at wiki commit `0085441`; post-publish `Sync-RepoWikis.ps1 -CheckOnly -Repository lotus-gateway`
   reported zero drift. `lotus-workbench` wiki publication completed for PR #153 at wiki commit
   `ff0b4ff`.
6. Canonical front-office validation passed after rebuilding impacted images:
   `powershell -ExecutionPolicy Bypass -File scripts/live/Start-LotusFrontOfficeCanonical.ps1 -BuildImages -LocalApps workbench -RunValidation -ScreenshotDirectory output/playwright/rfc36-wtbd003-dpm-operations-dashboard`
   produced `live-validation-summary.json`, `SHOT-INDEX.md`, and
   `dpm-outcome-review-live.png` for `PB_SG_GLOBAL_BAL_001`.
7. A focused live browser/API assertion against
   `http://workbench.dev.lotus/workbench/PB_SG_GLOBAL_BAL_001` and
   `http://gateway.dev.lotus/api/v1/workbench/PB_SG_GLOBAL_BAL_001/overview` passed after PR #193:
   the Workbench dashboard was visible, `recentRunCount` was 5, latest run
   `rr_c09f73d0` had status `PENDING_REVIEW`, `supportabilityStatus` was `ready`,
   `supportabilityRunCount` was 82, `consoleErrorCount` was 0, and `missing` was empty.

Gold-pass assessment:

This WTBD has reached the expected standard for its stated first-wave scope. The product path is
merged to `main` in the owning Gateway and Workbench repositories, the UI remains Gateway/BFF-only,
the Gateway fix was driven by live evidence rather than papering over a missing field, local tests
and GitHub gates passed, canonical Workbench proof passed on the governed stack, and owning
repo-local plus published wiki material reflects the implementation-backed capability. Richer book-
level aggregation, operations drill-down pages, alerting, and report/AI materialization remain
future product depth and should be tracked under later command-center/reporting WTBDs rather than
reopening this first-wave operations dashboard slice.

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
products, and canonical seed automation belonged to downstream or source-owning applications.

| ID | Work item | Owner | Current status | Why it was not done in RFC-0038 |
| --- | --- | --- | --- | --- |
| RFC38-WTBD-001 | Gateway DPM command-center composition | `lotus-gateway` | Completed, merged, CI-proven, and wiki-published through `lotus-gateway` PR #194 | Gateway now composes RFC-0038 mandate command-center, monitoring, exception, and mandate drill-down truth from manage without becoming mandate-health authority. |
| RFC38-WTBD-002 | Workbench DPM cockpit panels | `lotus-workbench` | Completed, merged, CI-proven, live-proven, and wiki-published through `lotus-workbench` PR #154 | Workbench consumes Gateway/BFF command-center contracts only, renders manage-owned supportability/source readiness/health truth without recomputation, and originally recorded the canonical seed gap that RFC38-WTBD-003 later resolved for the populated governed portfolio. |
| RFC38-WTBD-003 | Platform canonical seed automation for populated command-center proof | `lotus-platform` with source-app seeds | Completed, merged, CI-proven, live-proven, wiki-published, and hardened locally for populated ready/partial/empty seed posture checks | Platform canonical automation refreshes the governed DPM mandate from core through manage, runs one monitoring pass for command-center evidence, verifies Manage and Gateway mandate/health/summary reads, and runs canonical Workbench validation with `dpm.command_center` classified from Manage supportability. The current hardening adds platform seed `posture_checks` for populated source-ready `ready`, selector-driven `partial`, and empty-date `empty` command-center states. Degraded and blocked canonical fixtures remain source-owner follow-up rather than demo-ready claims. |
| RFC38-WTBD-004 | PM-book discovery for monitoring and command-center cohorts | `lotus-core` source authority consumed by `lotus-manage`, surfaced through `lotus-gateway` and `lotus-workbench` | Completed in this slice for populated source-owned PM-book monitoring cohorts | Manage monitoring run-once can now resolve PM-book cohorts from `PortfolioManagerBookMembership:v1` when callers omit mandate IDs. Workbench command-center monitoring uses that source-owned path by default. Populated ready/partial/empty seed-posture checks are now covered by RFC38-WTBD-003 hardening; degraded/blocked fixtures remain source-owner follow-up, not a blocker for populated PM-book monitoring support. |
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

Closure status:

Completed on 2026-05-06 through `lotus-gateway` PR #194,
`feat: expose DPM mandate command center`, merged to `main` at
`ee2d80684e9219c1ff42f8660f4a0ff4e97abf08`.

What was delivered:

1. Gateway now exposes a Workbench-facing RFC-0038 route family under
   `/api/v1/dpm/command-center`, `/api/v1/dpm/command-center/monitoring/*`,
   `/api/v1/dpm/command-center/exceptions*`, and
   `/api/v1/dpm/command-center/mandates*`.
2. `lotus-gateway` added typed `DpmClient` methods for manage command-center summary, monitoring
   run/create/search/detail, exception search/resolution, mandate-by-portfolio, mandate detail,
   mandate health, and mandate diff APIs.
3. Gateway wraps manage responses in a product BFF envelope with upstream status, correlation id,
   and manage-derived supportability while preserving the authoritative manage payload.
4. Gateway does not discover PM-book membership, calculate mandate health, reconstruct health
   dimensions, infer source readiness, merge exceptions across monitoring runs, or resolve
   exceptions locally.
5. Gateway repository context, RFC-0098, and repo-authored wiki source were updated. The
   `lotus-gateway` wiki was published after merge at wiki commit `5901cd8` and check-only
   verification reported zero drift.

Validation evidence:

1. Focused local proof passed:
   `python -m pytest tests/contract/test_dpm_command_center_contract.py tests/unit/test_dpm_command_center_service.py tests/integration/test_dpm_command_center_router.py tests/unit/test_upstream_clients.py::test_dpm_client_rfc38_command_center_routes -q`
   with 36 tests.
2. Local repo gate `make check` passed in `lotus-gateway`, including Ruff lint, Ruff format check,
   monetary-float guard, mypy, Workbench contract smoke, and 439 unit/contract tests.
3. GitHub PR #194 checks passed before merge: Feature Lane lint/typecheck/unit, Feature Lane
   workflow lint, PR Merge Gate workflow lint, lint/typecheck/unit, integration tests, coverage
   gate, Docker build validation, CI local Docker parity, and queue auto-merge.
4. `Sync-RepoWikis.ps1 -Publish -Repository lotus-gateway` published the changed API,
   integrations, and supported-feature pages after merge; `Sync-RepoWikis.ps1 -CheckOnly
   -Repository lotus-gateway` then reported diff count 0.

Gold-pass assessment:

This WTBD has reached the expected standard for the Gateway composition slice. The route family is
merged to `main`, pinned by client/service/router/OpenAPI tests, documented in Gateway RFC/wiki
truth, and published to the Gateway wiki. Full Workbench cockpit product support is not claimed
here and remains RFC38-WTBD-002.

#### RFC38-WTBD-002 - Workbench DPM Cockpit Panels

Target business outcome:

PMs and operations users can view mandate health, source readiness, attention queues, recommended
actions, latest monitoring run, and mandate drill-downs through a populated Workbench cockpit.

Closure status:

Completed on 2026-05-06 through `lotus-workbench` PR #154,
`Implement RFC38 DPM command-center cockpit`, merged to `main` at
`2fbfac5dd00104cee2b1da7923efe0c64940a9f5`.

What was delivered:

1. `/workbench/{portfolioId}` now renders an embedded DPM Command Center cockpit for the canonical
   front-office portfolio.
2. Workbench consumes the Gateway command-center route family only:
   `GET /api/v1/dpm/command-center`,
   `POST /api/v1/dpm/command-center/monitoring/run-once`,
   `GET /api/v1/dpm/command-center/exceptions`,
   `GET /api/v1/dpm/command-center/mandates/by-portfolio/{portfolio_id}`, and
   `GET /api/v1/dpm/command-center/mandates/{mandate_id}/health`.
3. The Workbench view model preserves Gateway/manage supportability, source readiness, health
   distribution, attention buckets, recommended actions, active exceptions, latest monitoring-run
   lineage, and mandate-health dimensions without calculating mandate health, supportability, or
   source readiness in browser code.
4. The run-monitoring action calls the Gateway BFF mutation path and sends governed DPM context
   for tenant `default`, PM `PM_SG_DPM_001`, book `BOOK_SG_BALANCED_DPM`, and as-of date
   `2026-05-03`.
5. Bounded observability surfaces were added for command-center summary, monitoring, exception,
   mandate binding, and mandate-health operations without leaking portfolio ids, PM ids, mandate
   ids, run ids, or exception ids into metric labels.
6. `lotus-workbench` repository context, RFC-0098, and repo-authored wiki source were updated.
   The `lotus-workbench` wiki was published after merge at wiki commit `86b6ee7`; check-only
   verification then reported zero drift.

Validation evidence:

1. Focused Workbench proof passed:
   `npx vitest run tests/unit/live-canonical-validation-script.test.ts tests/unit/live-validation-browser-workflows.test.ts tests/unit/dpm-command-center-panel.test.tsx tests/unit/dpm-command-center-view-model.test.ts tests/unit/workbench-api.test.ts`
   with 60 tests.
2. Local repo gate `make check` passed in `lotus-workbench`, including lint, typecheck, coverage
   tests, and production build.
3. Canonical front-office live validation passed:
   `powershell -ExecutionPolicy Bypass -File scripts/live/Start-LotusFrontOfficeCanonical.ps1 -LocalApps workbench,gateway -RunValidation -ScreenshotDirectory output/rfc38-wtbd002-command-center-cockpit-command-center-validated`.
4. Structured live evidence:
   `lotus-workbench/output/rfc38-wtbd002-command-center-cockpit-command-center-validated/live-validation-summary.json`
   proves Gateway command-center summary status 200, active exceptions status 200, and populated UI
   checks for DPM command-center health distribution, attention queue, active exceptions, and
   mandate health dimensions.
5. GitHub PR #154 checks passed before merge: Feature Lane workflow lint, Feature Lane lint/typecheck/test,
   PR Merge Gate workflow lint, lint/typecheck/coverage/build, Playwright smoke, Docker build
   validation, and CI local Docker parity.

Seed gap resolution:

The historical canonical
`GET /api/v1/dpm/command-center/mandates/by-portfolio/PB_SG_GLOBAL_BAL_001` seed gap was resolved
by RFC38-WTBD-003 platform automation on 2026-05-07. Workbench still preserves `seed_gap`
classification for non-populated or incomplete environments, but the governed canonical runtime now
proves the populated command-center path as `ready`.

Gold-pass assessment:

This WTBD has reached the expected standard for the Workbench cockpit slice. The implementation is
merged to `lotus-workbench` `main`, proven by Feature Lane and PR Merge Gate, locally live-proven
through the canonical Workbench runtime, and documented in repo context plus published wiki source.
The Workbench cockpit panel itself is implementation-backed. RFC38-WTBD-003 later resolved the
populated canonical seed gap; later richer product slices still govern PM-book discovery and
partial/empty command-center fixture depth.

#### RFC38-WTBD-003 - Platform Canonical Seed Automation

Target business outcome:

The canonical front-office stack can reliably seed and validate a populated DPM command-center state
for demo, QA, and regression proof.

Closure status:

Completed on 2026-05-07 through coordinated PRs:

1. `lotus-platform` PR #304 merged to `main` as `cdbc489` and published
   `lotus-platform.wiki` commit `fa3216a`,
2. `lotus-workbench` PR #155 merged to `main` as `cad5302`,
3. `lotus-manage` PR #113 merged to `main` as `7579a01` and published
   `lotus-manage.wiki` commit `27b1071`.

What was delivered:

1. `lotus-platform` added canonical DPM command-center seed identity to
   `canonical-front-office-demo-data-contract.json` for `PB_SG_GLOBAL_BAL_001`,
   `MANDATE_PB_SG_GLOBAL_BAL_001`, `PM_SG_DPM_001`, `BOOK_SG_BALANCED_DPM`, tenant `default`,
   booking center `Singapore`, model `MODEL_PB_SG_GLOBAL_BAL_DPM`, policy pack
   `POLICY_DPM_SG_BALANCED_V1`, and as-of date `2026-05-03`.
2. `lotus-platform` added `Invoke-DpmCommandCenterSeed.ps1`, which refreshes the canonical mandate
   from `lotus-core` through `lotus-manage`, verifies manage lookup by portfolio, verifies Gateway
   mandate lookup by portfolio, verifies Gateway mandate health, and verifies the Gateway
   command-center summary.
3. `Invoke-Canonical-FrontOffice-QA.ps1` now runs the DPM command-center seed before Workbench
   validation by default and records DPM seed evidence in the canonical front-office QA summary.
4. The canonical data invariants, Workbench panel registry, analytics UI observability readiness
   contract, and platform automation docs were updated to include `dpm.command_center`.
5. `lotus-workbench` live validation now classifies `dpm.command_center` as a governed ready panel
   and captures the registered DPM command-center screenshot during canonical browser validation.

Validation evidence:

1. Platform focused tests passed:
   `python -m pytest tests/unit/test_analytics_ui_rollout_readiness.py tests/unit/test_rfc_0076_canonical_demo_data_contract.py tests/unit/test_rfc_0077_panel_registry_contract.py tests/unit/test_front_office_runtime_automation_contract.py -q`
   with 15 tests.
2. Workbench focused tests passed:
   `npm test -- --run tests/unit/live-canonical-validation-script.test.ts tests/unit/live-validation-browser-workflows.test.ts`
   with 13 tests.
3. Governed canonical runtime proof passed:
   `powershell -ExecutionPolicy Bypass -File automation\Invoke-Canonical-FrontOffice-QA.ps1 -BringUp -LotusAiEnvFile .env.example -SeedWaitSeconds 1200`.
4. Structured DPM seed evidence:
   `lotus-platform/output/front-office-qa/dpm-command-center-seed-20260507-013324.json` and
   `lotus-platform/output/front-office-qa/dpm-command-center-seed-latest.json` show status `ok`
   for manage refresh, manage lookup, Gateway mandate lookup, Gateway mandate health, and Gateway
   command-center summary.
5. Structured canonical QA evidence:
   `lotus-platform/output/front-office-qa/canonical-front-office-qa-20260507-012800.json` and
   `lotus-workbench/output/playwright/live-canonical/live-validation-summary.json` prove live
   canonical Workbench validation passed for `PB_SG_GLOBAL_BAL_001`, with screenshots under
   `lotus-workbench/output/playwright/live-canonical`.

Remaining governed follow-up:

Populated ready, selector-driven partial, and empty command-center state automation is now claimed
at the platform seed contract layer. The canonical Workbench panel records the current canonical
PM/book/as-of command center as `READY` while preserving degraded and blocked states as explicit
non-ready behavior. Degraded and blocked canonical seed fixtures require source-owner fixture
support before they can be promoted as durable demo or regression scenarios.

#### RFC38-WTBD-004 - PM-Book Discovery For Monitoring And Command-Center Cohorts

Target business outcome:

The DPM command center can populate by PM book or portfolio-manager cohort without requiring
callers to supply every mandate or portfolio id manually.

Current status:

Completed in this slice for populated, source-owned PM-book monitoring cohorts.
`PortfolioManagerBookMembership:v1` already exists in `lotus-core`; `lotus-manage` now consumes it
directly when `/api/v1/dpm/monitoring/run-once` receives no explicit `mandate_ids` and has a
`portfolio_manager_id` selector. The command-center run records the PM, book, tenant, booking
center, core product, core product version, supportability state, snapshot id, and source content
hash in the monitoring-run filters so command-center reads can tie the populated cohort back to
source authority.

What was delivered:

1. Manage preserves the existing explicit mandate-id path for backward-compatible bounded runs.
2. Manage requires either explicit `mandate_ids` or `portfolio_manager_id`, and rejects missing
   selectors with `DPM_MONITORING_SELECTOR_REQUIRED`.
3. Manage resolves source-owned PM-book members through `lotus-core`
   `PortfolioManagerBookMembership:v1` with tenant, booking-center, as-of date, eligible portfolio
   type, and `include_inactive=false` filters.
4. Manage maps source unavailability to dependency errors instead of fabricating a cohort.
5. Manage blocks non-ready PM-book membership, empty PM-book membership, and PM-book members whose
   refreshed RFC-0038 mandate twin is not present.
6. Workbench command-center monitoring no longer sends a single mandate fallback; the embedded
   command-center action lets Gateway/Manage resolve the PM-book cohort from source truth.
7. Gateway remains a pass-through product BFF for the monitoring body and does not become PM-book
   authority.

Validation evidence:

1. Manage focused proof:
   `python -m pytest tests/unit/dpm/api/test_monitoring_api.py -q`.
2. Manage static proof:
   `python -m ruff check src/api/routers/monitoring.py src/api/services/mandate_service.py tests/unit/dpm/api/test_monitoring_api.py`.
3. Workbench focused proof:
   `npm test -- --run tests/unit/workbench-api.test.ts tests/unit/dpm-command-center-panel.test.tsx`.
4. Documentation and API-governance proof are required before merge through the docs current-state
   tests, API vocabulary/no-alias gate, wiki check-only, and PR CI.

Remaining governed follow-up:

This WTBD closes the source-owned populated PM-book monitoring path. The separate command-center
seed hardening now proves populated ready, selector-driven partial, and empty platform seed
postures. It still does not claim degraded, blocked, or permission-denied PM-book fixtures because those require
source-owner fixture support, Workbench browser assertions, and screenshot/evidence registration
beyond the populated command-center path.

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
`CURRENCY_OVERLAY`, `REGIME_STRESS_AWARE`, and source-backed `ESG_AWARE`.

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
| RFC39-WTBD-004 | ESG/restriction-aware construction support | `lotus-core` source authority consumed by manage | Completed for source-backed restriction and sustainability profile consumption | `ClientRestrictionProfile:v1` and `SustainabilityPreferenceProfile:v1` are consumed through stateful core sourcing. Manage degrades when profiles are missing, blocks candidate trades that violate hard client restrictions, preserves sustainability preferences and source lineage, and keeps classification evidence gaps in `PENDING_REVIEW` rather than claiming automatic ESG approval. |
| RFC39-WTBD-005 | Broader risk/performance alternative enrichment | `lotus-risk`, `lotus-performance` | Deferred beyond current seams/authority-backed concentration support | Current `RISK_AWARE` consumes concentration authority; broader tracking error, drawdown, stress contribution, attribution, and benchmark-relative performance need owning-service contracts. |
| RFC39-WTBD-006 | Authoritative transaction-cost and cost-aware alternatives | `lotus-core` source authority consumed by `lotus-manage` | Completed for source-owned observed-cost comparison methods | `TransactionCostCurve:v1` is consumed in stateful construction and proof packs. The `COST_AWARE` method applies observed average cost bps to candidate trade notionals, records an `ESTIMATED_COST` objective/constraint trace, and degrades when source evidence is absent or incomplete. Predictive execution quotes, market-impact modelling, venue routing, and broader execution methodology remain outside this support claim. |
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

Current implementation-backed status:

Completed for manage backend consumption. `lotus-core` publishes source-backed
`ClientRestrictionProfile:v1` and `SustainabilityPreferenceProfile:v1`; `lotus-manage` resolves
both through the stateful core-sourcing client and attaches them to
`ConstructionAuthorityContext`.

Implemented scope:

1. `ESG_AWARE` no longer relies on a blanket deferred method status when the source profiles are
   available,
2. missing client restriction or sustainability profiles degrade explicitly with source-specific
   reason codes,
3. hard client restriction rules block candidate buy/sell intents that match restricted
   instruments, issuers, asset classes, sectors, or regions,
4. sustainability min/max allocation preferences can move the method to `PENDING_REVIEW`,
5. exclusion and positive-tilt sustainability preferences require separate security-level
   classification evidence and therefore remain `PENDING_REVIEW` instead of unsupported ESG
   approval,
6. construction traces include client restriction and sustainability preference source terms,
7. selected-alternative proof packs preserve source refs, hashes, reason codes, restriction rules,
   and sustainability preferences without recomputing client-governance or ESG methodology.

Validation evidence:

1. core-sourcing client tests prove both source-product calls, selector payloads, and attached
   profile state,
2. construction API tests prove source-ready ESG-aware generation and hard-restriction blocking,
3. proof-pack builder tests prove restriction and sustainability source preservation,
4. README, RFC, context, and wiki updates avoid unsupported ESG approval or greenwashing claims.

Remaining boundary:

Gateway/Workbench product presentation for this new profile surface and richer security-level ESG
classification source evidence remain separate downstream/source-owner work. Manage does not infer
issuer sustainability classifications, claim regulatory suitability completion, execute orders, or
turn preferences into automatic client approval.

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

PMs can compare alternatives using source-owned observed transaction-cost evidence rather than
unlabelled local diagnostics, while preserving a clear boundary between observed booked-fee history
and predictive execution quotes.

Current implementation status:

Completed for source-owned observed-cost comparison methods. `lotus-core` owns
`TransactionCostCurve:v1`, `lotus-manage` stateful construction consumes it, and the
`COST_AWARE` construction method applies source-owned observed average cost bps to candidate
security-trade notionals. The method adds an `ESTIMATED_COST` objective term, a transaction-cost
constraint trace, method reason codes, and an `estimated_transaction_cost` comparison metric only
when the source curve covers the candidate trades. Missing, degraded, or inapplicable cost evidence
keeps the method `DEGRADED` with explicit reason codes.

Implemented scope:

1. `COST_AWARE` is a source-aware construction method and is not part of the default stateless
   first-wave method set.
2. `COST_AWARE` requires `TRANSACTION_COST` source-family supportability.
3. Ready source curves produce a bounded comparison estimate by applying observed average bps to
   candidate trade notionals.
4. Missing source curves produce a degraded method with `TRANSACTION_COST_CURVE_UNAVAILABLE` and
   `AUTHORITATIVE_TRANSACTION_COST_UNAVAILABLE`.
5. Missing traded-security coverage produces degraded posture instead of silently treating uncovered
   securities as zero-cost.
6. The method does not claim predictive spread, market impact, venue routing, execution timing, or
   order-placement cost optimization.

Production boundary:

This WTBD is complete for source-owned observed-cost construction comparison. It is not a
predictive transaction-cost model, market-impact model, venue-routing service, or external OMS
execution methodology. Those remain future execution/source-owner work and must not be presented as
supported functionality from this slice.

Implementation proof:

1. `src/core/construction/vocabulary.py` adds `COST_AWARE` and `TRANSACTION_COST` method-family
   linkage.
2. `src/core/construction/method_registry.py` declares the cost-aware method support gate.
3. `src/api/services/construction_service.py` computes source-observed cost comparison metrics and
   degraded-state reason codes.
4. `tests/unit/dpm/api/test_construction_api.py` proves ready and degraded cost-aware behavior.
5. `tests/unit/dpm/construction/test_method_registry.py` and
   `tests/unit/dpm/construction/test_vocabulary.py` preserve method registry and source-family
   governance.

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
| First-wave proof-pack product realization | `lotus-platform/output/front-office-qa/canonical-front-office-qa-20260507-124405.json`, `lotus-workbench/output/playwright/live-canonical/live-validation-summary.json` |

### Remaining Work Summary

These items are deliberately not done in RFC-0040 because proof-pack backend authority is
manage-owned, while full product realization, document materialization, AI narrative generation,
analytics enrichment, and broader source coverage belong to other Lotus apps.

| ID | Work item | Owner | Current status | Why it was not done in RFC-0040 |
| --- | --- | --- | --- | --- |
| RFC40-WTBD-001 | Gateway proof-pack composition | `lotus-gateway` | Completed, merged, CI-proven, and wiki-published through `lotus-gateway` PR #195 | Gateway consumes stable manage proof-pack generate/read/Markdown/report-input/AI-evidence APIs without reconstructing sections, hashes, report refs, or AI refs. Workbench UX and full canonical product proof remain separate WTBDs. |
| RFC40-WTBD-002 | Workbench proof-pack review UX | `lotus-workbench` | Completed, merged, CI-proven, and wiki-published through `lotus-workbench` PR #156 | Workbench now consumes Gateway/BFF proof-pack contracts only, renders proof-pack identity, supportability, sections, source hashes, Markdown/report/AI posture, and action eligibility without reconstructing sections, hashes, report input, or AI evidence. |
| RFC40-WTBD-003 | Full front-office proof-pack product realization | `lotus-gateway`, `lotus-workbench`, with manage as backend authority | Completed, merged, CI-proven, live-proven, and wiki-ready through `lotus-gateway` PR #195, `lotus-workbench` PR #156, `lotus-workbench` PR #164, `lotus-manage` PR #117, and platform canonical QA | The first-wave product path now generates and replays proof-pack evidence through Gateway/BFF, renders Workbench proof-pack review over live manage truth, and passes governed canonical front-office QA with `dpm.proof_pack` classified `ready`. Governed AI memo generation, richer source-owner enrichment, client restrictions, sustainability profiles, and cross-RFC portfolio memory remain separate WTBDs. |
| RFC40-WTBD-004 | Report materialization from `DpmProofPackReportInput` | `lotus-report`, `lotus-render`, `lotus-archive` | Completed, merged, CI-proven, and wiki-published through `lotus-render` PR #11, `lotus-report` PR #90, and `lotus-archive` PR #23 | Manage produces deterministic report input; `lotus-report` consumes it without reconstructing proof-pack evidence, `lotus-render` renders the governed `proof-pack` template, and `lotus-archive` governs the resulting `proof_pack` artifact lifecycle with retention, legal hold, retrieval, purge, and access audit. |
| RFC40-WTBD-005 | AI PM memo generation from `DpmProofPackAiEvidenceInput` | `lotus-ai`, consumed through Gateway/Workbench | Completed, merged, CI-proven, live-proven, and wiki-published through `lotus-ai` PR #61, `lotus-gateway` PR #198, `lotus-workbench` PR #166, and rebuilt platform canonical QA | Manage produces bounded AI evidence with guardrails; `lotus-ai` owns review-gated `dpm_pm_memo.pack@v1` execution, Gateway composes the handoff, and Workbench exposes only a governed request action without prompt construction or autonomous decisioning. |
| RFC40-WTBD-006 | Broader risk and performance proof-pack enrichment | `lotus-risk`, `lotus-performance`, consumed by manage/Gateway | Completed in this slice for manage proof-pack authority | RFC-0040 selected-alternative proof packs now preserve source-owned risk and performance context from construction authority metadata, including supportability state, source refs, source hashes, reason codes, and bounded source-emitted measures. Manage still does not calculate risk or performance methodology locally. |
| RFC40-WTBD-007 | Authoritative transaction-cost curve | `lotus-core` source authority consumed by `lotus-manage` | Completed for proof-pack evidence authority | `lotus-core` publishes `TransactionCostCurve:v1` observed booked-fee evidence and `lotus-manage` consumes it through stateful core sourcing, attaches `AuthoritativeTransactionCostContext` to selected construction alternatives, and preserves source-owned supportability, source refs, content hashes, reason codes, evidence windows, missing securities, and bounded curve points in `turnover_and_cost` proof-pack evidence. Manage still labels local construction estimates separately and does not claim predictive execution quotes or min-cost optimization. |
| RFC40-WTBD-008 | Sustainability preferences and client restriction profiles | `lotus-core` source authority consumed by `lotus-manage` | Completed for manage proof-pack evidence authority | `ClientRestrictionProfile:v1` and `SustainabilityPreferenceProfile:v1` are consumed through stateful core sourcing, attached to selected construction alternatives, and preserved in proof-pack `eligibility_and_restrictions` and `sustainability_controls` sections with source refs, content hashes, reason codes, and review/block posture. Security-level sustainability classification remains a pending-review boundary when source evidence is absent. |
| RFC40-WTBD-009 | Scenario-pack authority beyond supplied context | `lotus-risk` / CIO authority, consumed by `lotus-manage` construction evidence | Partially implemented through selected RFC-0039 alternatives | `RegimeScenarioPackEvaluation:v1` now supplies first-wave scenario-pack evaluation for `REGIME_STRESS_AWARE` alternatives. Proof packs can preserve that selected-alternative context, but richer scenario contribution, CIO approval, and direct proof-pack enrichment remain future source depth. |
| RFC40-WTBD-010 | Decision timeline and portfolio memory across mandate, exception, wave, handoff, and outcome events | `lotus-manage` with downstream/source participants | Partially implemented: manage backend authority plus first-wave Gateway/Workbench product realization are merged, live-proven, and wiki-published; mandate health, monitoring-exception, event identity, retention, redaction, access, and audit policy are implemented in manage; `lotus-report` PR #92 implements the report-side bounded context consumer; `lotus-ai` PR #62 implements bounded DPM memo/narrative consumers | Manage exposes a deterministic source-backed portfolio-memory read model over persisted mandate health snapshots, monitoring exceptions, proof packs, proof-pack-local timeline events, RFC-0041 wave events, internal handoff refs, and RFC-0042 outcome-review events. Gateway composes that read model and Workbench renders the first-wave timeline panel with canonical browser proof. `lotus-report` can carry Manage-owned `portfolio_memory_context` into proof-pack, wave, and outcome report snapshot/render lineage without reconstruction. `lotus-ai` validates that same context for DPM PM memo and outcome-review narrative packs without reconstructing timeline facts. Full WTBD closure still needs future report, AI, OMS, PM-scoring, and client-communication source-event families from their owners. |

### Detailed Follow-Up Items

#### RFC40-WTBD-001 - Gateway Proof-Pack Composition

Target business outcome:

Gateway exposes a Workbench-facing proof-pack contract that preserves manage-owned evidence while
adding experience-layer posture for entitlements, availability, report status, AI status, archive
status, and command-center context.

Current implementation-backed status:

Completed, merged, CI-proven, and wiki-published through `lotus-gateway` PR #195. Gateway now
exposes `/api/v1/dpm/command-center/proof-packs*` routes for generate, read, deterministic
Markdown, report-input, and AI-evidence-input access. The implementation preserves manage-owned
`proof_pack_id`, section states, reason codes, source refs, content/source hashes, report refs, and
AI refs in a Gateway envelope without reconstructing proof-pack evidence.

Implementation evidence:

1. `lotus-gateway` merge commit `f706853`,
2. `src/app/routers/dpm_proof_packs.py`,
3. `src/app/services/dpm_proof_pack_service.py`,
4. `src/app/contracts/dpm_proof_packs.py`,
5. `src/app/clients/dpm_client.py`,
6. `tests/unit/test_dpm_proof_pack_service.py`,
7. `tests/integration/test_dpm_proof_pack_router.py`,
8. `tests/contract/test_dpm_proof_pack_contract.py`,
9. `tests/unit/test_upstream_clients.py`,
10. `lotus-gateway` wiki publication commit `7b97aac`.

Validation evidence:

1. `make check` passed in `lotus-gateway` with lint, format, monetary-float guard, mypy, and `452`
   unit/contract tests,
2. `make test-integration` passed in `lotus-gateway` with `164` integration tests,
3. focused proof-pack and upstream-client checks passed with `110` tests,
4. GitHub Feature Lane and PR Merge Gate passed for `lotus-gateway` PR #195, including coverage,
   integration, Docker build, and Docker parity checks,
5. `Sync-RepoWikis.ps1 -Publish -Repository lotus-gateway` published repo-authored wiki source,
   and post-publish check-only reported zero drift.

Remaining governed follow-up:

Workbench review UX, full canonical front-office proof, report materialization, archive lifecycle,
AI memo generation, and richer source-owner enrichment remain governed by RFC40-WTBD-002 through
RFC40-WTBD-010. This item is a Gateway composition support claim only.

#### RFC40-WTBD-002 - Workbench Proof-Pack Review UX

Target business outcome:

Portfolio managers, reviewers, operations, and client-facing teams can inspect proof packs in
Workbench with section readiness, evidence drawers, Markdown preview, report/AI posture, lineage,
hashes, and action eligibility backed by Gateway truth.

Current implementation-backed status:

Completed, merged, CI-proven, and wiki-published through `lotus-workbench` PR #156. Workbench now
embeds a `Proof-Pack Evidence` panel in `/workbench/{portfolioId}` and uses Gateway/BFF routes under
`/api/v1/dpm/command-center/proof-packs*` for proof-pack generation, detail, Markdown, report-input,
and AI-evidence-input actions. The server prefetch path uses the Gateway server target, while client
actions use the client BFF target. The panel preserves Gateway and manage truth for proof-pack
identity, mandate/run/alternative lineage, supportability, section state counts, source hashes,
Markdown availability, report-input availability, and AI-evidence availability without rebuilding
proof-pack sections, recomputing hashes, or constructing report/AI payloads in browser code.

Implementation evidence:

1. `lotus-workbench` merge commit `8acf276`,
2. `src/features/workbench/api.ts` proof-pack Gateway/BFF wrappers,
3. `src/features/workbench/proof-pack-view-model.ts`,
4. `src/features/workbench/components/proof-pack-panel.tsx`,
5. `src/app/workbench/[portfolioId]/page.tsx`,
6. `scripts/live/validate-canonical-workbench-live.mjs`,
7. `scripts/live/validation/browser-workflows.mjs`,
8. `tests/unit/proof-pack-view-model.test.ts`,
9. `tests/unit/proof-pack-panel.test.tsx`,
10. `tests/unit/workbench-api.test.ts`,
11. `tests/integration/workbench-page.test.tsx`,
12. `lotus-workbench` wiki publication commit `1b4b095`.

Validation evidence:

1. focused Workbench proof-pack, API, metrics, and page tests passed with `70` tests,
2. RFC-0098 documentation regression passed in `lotus-workbench`,
3. `npm run typecheck`, `npm run lint`, and `make check` passed locally in `lotus-workbench`,
   including `725` tests, coverage, and production Next build,
4. GitHub Feature Lane and PR Merge Gate passed for `lotus-workbench` PR #156, including lint,
   typecheck, tests, coverage/build, Playwright smoke, Docker build, and Docker parity,
5. `Sync-RepoWikis.ps1 -Publish -Repository lotus-workbench` published repo-authored wiki source,
   and post-publish check-only reported zero drift.

Remaining governed follow-up:

This closed the Workbench review UX slice only at PR #156 merge time. RFC40-WTBD-003 later closed
the first-wave full product-realization slice after canonical front-office proof across the complete
Gateway/Workbench proof-pack path, audience-ready documentation, and explicit treatment of
report/AI downstream posture. Report
materialization, AI memo generation, richer source-owner enrichment, transaction-cost authority,
client restriction/sustainability profiles, and cross-RFC portfolio memory remain governed by
RFC40-WTBD-004 through RFC40-WTBD-010.

#### RFC40-WTBD-003 - Full Front-Office Proof-Pack Product Realization

Target business outcome:

Proof packs are available as an end-to-end product workflow across manage, Gateway, and Workbench,
with validated backend evidence, composed experience APIs, browser proof, and demo-ready material.

Current implementation-backed status:

Completed for the first-wave full front-office proof-pack product path on 2026-05-07. The proof
pack workflow is now realized across manage backend authority, Gateway/BFF composition, Workbench
review UX, and governed platform canonical QA for `PB_SG_GLOBAL_BAL_001`.

What was delivered:

1. `lotus-gateway` PR #195 exposes Gateway-owned proof-pack routes under
   `/api/v1/dpm/command-center/proof-packs*` without reconstructing manage evidence.
2. `lotus-workbench` PR #156 renders the proof-pack review panel from Gateway/BFF truth and
   preserves proof-pack identity, section states, source hashes, Markdown/report/AI posture, and
   action eligibility.
3. `lotus-workbench` PR #164 aligned live validation proof-pack preflight idempotency with the
   Workbench UI path so canonical browser proof uses the same generated evidence flow.
4. `lotus-manage` PR #117 made proof-pack generation replay deterministic source identities before
   rebuilding a proof pack, preventing immutable-content conflicts when a canonical run already
   exists under a different idempotency key.
5. Platform canonical front-office QA rebuilt the merged images, seeded the canonical portfolio,
   refreshed DPM command-center data, generated proof-pack evidence through Gateway, validated
   Workbench browser panels, captured screenshots, and stopped the governed runtime cleanly.

Validation evidence:

1. `lotus-manage` PR #117 merged to `main` at `78b04eba6c83a35c1ea3f0c89d7740e667bfb576` after
   Feature Lane and PR Merge Gate checks passed.
2. Post-merge manage focused proof passed:
   `python -m pytest tests/unit/dpm/proof_packs/test_proof_pack_service.py tests/unit/dpm/proof_packs/test_proof_pack_repository.py tests/unit/dpm/proof_packs/test_proof_pack_postgres_repository.py tests/unit/dpm/api/test_proof_pack_api.py -q`
   with `29` tests passing.
3. Post-merge governed platform proof passed:
   `powershell -ExecutionPolicy Bypass -File automation\Invoke-Canonical-FrontOffice-QA.ps1 -BringUp -BuildImages -LotusAiEnvFile .env.example -SeedWaitSeconds 1200`.
4. Canonical QA evidence:
   `lotus-platform/output/front-office-qa/canonical-front-office-qa-20260507-124405.json` and
   `lotus-platform/output/front-office-qa/canonical-front-office-qa-20260507-124405.md`.
5. DPM seed evidence:
   `lotus-platform/output/front-office-qa/dpm-command-center-seed-20260507-125141.json` reported
   status `ok` after manage refresh, manage lookup, Gateway mandate lookup, Gateway mandate
   health, and Gateway command-center summary checks.
6. Workbench live evidence:
   `lotus-workbench/output/playwright/live-canonical/live-validation-summary.json` classified
   `dpm.proof_pack` as `ready` with proof pack `dpp_c09f73d0`, business state `PENDING_REVIEW`,
   `27` sections, and `3` source hashes.
7. Browser screenshot evidence:
   `lotus-workbench/output/playwright/live-canonical/dpm-proof-pack-live.png` and
   `lotus-workbench/output/playwright/live-canonical/dpm-command-center-live.png` were captured
   after backend/API/panel validation passed.

Gold-pass assessment:

This WTBD is complete for the stated first-wave product-realization scope. The full path is merged
to owning `main` branches, replay-safe, CI-proven, browser-proven, and supported by canonical
runtime evidence. The closure does not promote report materialization, governed AI memo generation,
richer source-owner enrichment, transaction-cost authority, client restriction/sustainability
profiles, or cross-RFC portfolio memory; those remain RFC40-WTBD-004 through RFC40-WTBD-010.

#### RFC40-WTBD-004 - Report Materialization From `DpmProofPackReportInput`

Target business outcome:

A proof pack can be materialized into a governed report with deterministic rendering, archive
records, retention, legal hold, retrieval, and access audit.

Closure status:

Completed on 2026-05-07 across the owning repositories:

1. `lotus-render` PR #11 added the governed `proof-pack` render template, template manifest,
   deterministic contract tests, and wiki-published render support posture.
2. `lotus-report` PR #90 added `POST /reports/proof-packs`, persisted
   `DpmProofPackReportInput` snapshots, lineage back to `lotus-manage`, render-package handoff to
   `lotus-render`, archive handoff metadata, OpenAPI support posture, and wiki-published
   proof-pack report documentation.
3. `lotus-archive` PR #23 tightened generated-report type validation to include `proof_pack` and
   proved the proof-pack archive lifecycle through create, Gateway download, legal hold,
   blocked-purge response, release, purge, and access-audit events.

Ownership boundary:

`lotus-manage` remains the proof-pack evidence authority and deterministic report-input owner. It
does not generate, render, archive, retain, or retrieve report documents. Report materialization is
owned by `lotus-report`, deterministic rendering by `lotus-render`, and document lifecycle by
`lotus-archive`.

Implementation-backed proof:

1. `lotus-render`: `54 passed` focused render/template tests and wiki check-only drift `0` after
   publication.
2. `lotus-report`: GitHub Feature Lane and PR Merge Gate passed, including unit, integration, e2e,
   combined coverage, Docker build, and wiki publication.
3. `lotus-archive`: GitHub Feature Lane and PR Merge Gate passed, including unit, integration,
   e2e, combined coverage, Docker build, and wiki publication.

Remaining boundaries:

Gateway/Workbench report request UX for pre-trade proof-pack reports is not promoted by this WTBD
unless a separate product-surface slice exposes it. Governed AI PM memo generation is now closed
separately by RFC40-WTBD-005.

#### RFC40-WTBD-005 - AI PM Memo Generation From `DpmProofPackAiEvidenceInput`

Target business outcome:

PMs can request governed AI assistance over proof-pack evidence while preserving provenance,
guardrails, forbidden-field protections, and unsupported-action blocking.

Closure basis:

Completed on 2026-05-07 across the owning repositories:

1. `lotus-ai` PR #61 merged as `942d618a41ae7375fc790995974f8e16db4e2a8b`, adding the
   review-gated `dpm_pm_memo.pack@v1` workflow-pack execution path for manage-owned
   `DpmProofPackAiEvidenceInput`,
2. `lotus-gateway` PR #198 merged as `dc891266ad1dd567f4a0b0d1729d1c60db6cce7a`, adding
   `POST /api/v1/dpm/command-center/proof-packs/{proof_pack_id}/ai-pm-memo` without
   reconstructing proof-pack evidence or generating PM memos locally,
3. `lotus-workbench` PR #166 merged as `243855743380a24e9f7622a1ed7839a50e5604f5`, adding the
   governed proof-pack panel action and live validation for the Gateway memo handoff without
   browser prompt construction,
4. wiki source was synchronized for `lotus-ai`, `lotus-gateway`, and `lotus-workbench`, with
   `lotus-gateway` wiki publication commit `4d5b9d1` and `lotus-workbench` wiki publication
   commit `5d8d763`,
5. rebuilt platform canonical QA passed at
   `lotus-platform/output/front-office-qa/canonical-front-office-qa-20260507-210641.json`.

Runtime proof:

The rebuilt canonical QA run validated the canonical proof pack `dpp_c09f73d0`, classified
`dpm.proof_pack` as `ready`, and called
`POST /api/v1/dpm/command-center/proof-packs/dpp_c09f73d0/ai-pm-memo` through Gateway with HTTP
200. The live Workbench summary recorded `lotus-ai` as source service and workflow-pack run
`packrun_dpm_pm_memo_air_b69bcfd16d7341b889b0037f884839fa` in `AWAITING_REVIEW` /
`ACTION_REQUIRED` posture.

Supported boundaries:

1. `lotus-manage` remains evidence authority only and does not construct AI prompts, generate
   memos, score PMs, approve trades, or issue recommendations,
2. `lotus-gateway` reads manage-owned AI evidence input and invokes `lotus-ai` as the composition
   owner without rebuilding proof-pack sections, hashes, or report refs,
3. `lotus-workbench` exposes a bounded request action and renders workflow-pack posture only,
4. the supported state is review-gated narrative assistance, not autonomous investment advice,
   client contact, order approval, or execution.

#### RFC40-WTBD-006 - Broader Risk And Performance Proof-Pack Enrichment

Target business outcome:

Proof packs include source-backed risk and performance context beyond the first manage-backed
evidence, with clear degraded states when analytics are missing, stale, or partial.

Current implementation-backed status:

Completed in this slice for `lotus-manage` proof-pack authority. Selected-alternative proof packs
now consume source-owned risk and performance authority context already attached to the selected
RFC-0039 construction alternative. The `risk_impact` and `performance_context` sections preserve
the source owner's supportability state, lineage refs, content hashes, reason codes, and bounded
source-emitted measures such as tracking error, concentration posture, benchmark identity, active
return, and underperformance flag. Direct run proof packs and selected alternatives without source
analytics continue to degrade those sections truthfully.

Implemented controls:

1. `src/core/proof_packs/source_analytics.py` isolates risk/performance extraction from the
   proof-pack builder and validates attached contexts against the existing
   `AuthoritativeRiskContext` and `AuthoritativePerformanceContext` models,
2. `src/core/proof_packs/builder.py` uses that module to populate `risk_impact` and
   `performance_context` sections, source refs, and `risk_context` / `performance_context` source
   hashes without adding manage-local analytics methodology,
3. report and AI handoff adapters inherit the enriched sections and sanitized metrics from the
   immutable proof pack without reconstructing analytics,
4. `scripts/generate_rfc0040_proof_pack_evidence.py` now proves a mixed-readiness selected
   alternative where risk is `READY` and performance remains `DEGRADED`,
5. tests pin ready/degraded section states, source hash keys, source refs, JSON-safe source
   measures, AI/report handoff preservation, and evidence-script critical-review checks.

Proof:

1. targeted proof-pack/evidence tests:
   `python -m pytest tests/unit/dpm/proof_packs/test_proof_pack_builder.py tests/unit/dpm/proof_packs/test_proof_pack_handoffs.py tests/unit/dpm/proof_packs/test_proof_pack_markdown.py tests/unit/test_rfc0040_evidence_script.py -q`,
2. live proof is generated by
   `python scripts/generate_rfc0040_proof_pack_evidence.py --base-url http://127.0.0.1:8001`;
   this slice records `output/rfc0040-proof/20260507-230235/manifest.json` with selected
   proof-pack `risk_source_state=READY`, `performance_source_state=DEGRADED`, `risk_context` and
   `performance_context` source hashes, and `critical-review.json` passed,
3. full repository proof remains `make check` before PR publication.

Remaining bounded gaps:

1. Gateway and Workbench may choose to surface the enriched risk/performance posture, but manage
   closure does not claim downstream rendering,
2. richer attribution, contribution, stress, and scenario methodology remains source-owner work in
   `lotus-risk` and `lotus-performance`,
3. transaction-cost authority, client restriction profiles, sustainability preferences, and
   portfolio memory remain separate WTBDs.

#### RFC40-WTBD-007 - Authoritative Transaction-Cost Curve

Target business outcome:

Proof packs can distinguish labelled estimates from source-backed transaction-cost evidence and
show cost supportability clearly.

Implementation-backed status:

Completed for RFC-0040 proof-pack evidence authority. `lotus-core` now owns
`TransactionCostCurve:v1` as observed booked-fee transaction-cost evidence, and `lotus-manage`
consumes that source product through the stateful core-sourcing path. Manage converts the response
into `AuthoritativeTransactionCostContext`, attaches it to construction alternatives, and preserves
the source-owned evidence in the proof-pack `turnover_and_cost` section without blending it into
local construction estimates.

Implemented boundary:

1. source owner: `lotus-core`,
2. source product: `TransactionCostCurve:v1`,
3. route: `/integration/portfolios/{portfolio_id}/transaction-cost-curve`,
4. consumer: `lotus-manage` stateful core-sourcing client,
5. evidence shape: supportability state, reason code, as-of date, transaction-date window,
   missing securities, request fingerprint/source id, source content hash, bounded curve points,
   represented observation count, observed average/min/max bps, total notional, total cost, and
   sample source transaction ids,
6. proof-pack behavior: `turnover_and_cost` carries local estimated cost separately from
   source-owned observed cost evidence.

Production boundary:

This WTBD does not claim predictive transaction-cost quotes, market-impact modeling, venue
selection, spread forecasts, execution-price estimation, or min-cost portfolio construction. Those
remain RFC39-WTBD-006 / broader execution-methodology work. `TransactionCostCurve:v1` is observed
booked-fee evidence suitable for audit, supportability, and proof-pack review.

Implementation evidence:

1. `lotus-core` source-owner implementation and tests for `TransactionCostCurve:v1`,
2. `src/infrastructure/core_sourcing/client.py`,
3. `src/core/dpm_source_context.py`,
4. `src/core/construction/models.py`,
5. `src/api/services/construction_service.py`,
6. `src/core/proof_packs/source_analytics.py`,
7. `src/core/proof_packs/builder.py`,
8. `tests/unit/dpm/infrastructure/test_core_sourcing_client.py`,
9. `tests/unit/dpm/api/test_construction_api.py`,
10. `tests/unit/dpm/proof_packs/test_proof_pack_builder.py`.

#### RFC40-WTBD-008 - Sustainability Preferences And Client Restriction Profiles

Target business outcome:

Proof packs can explain client restrictions, sustainability preferences, and ESG/restriction
controls from source-backed client governance profiles.

Current implementation-backed status:

Completed for manage proof-pack evidence authority. Proof packs can now cite source-backed client
restriction and sustainability preference profiles when the selected construction alternative
carries those profiles through the stateful core-sourcing path.

Implemented scope:

1. `AuthoritativeClientRestrictionContext` and
   `AuthoritativeSustainabilityPreferenceContext` carry source system, product name/version,
   source id, source ref, content hash, supportability status, as-of/effective dates, reason codes,
   and bounded profile entries,
2. the core-sourcing client resolves `ClientRestrictionProfile:v1` and
   `SustainabilityPreferenceProfile:v1` with the same selector payload and correlation posture as
   other DPM source products,
3. `ESG_AWARE` alternatives emit client restriction and sustainability constraint traces and use
   source profile supportability to derive ready/degraded/blocked/pending-review posture,
4. selected-alternative proof packs preserve restriction and sustainability source analytics in
   `eligibility_and_restrictions` and `sustainability_controls`,
5. missing source profiles remain degraded, hard restriction violations remain blocked, and
   sustainability classification evidence gaps remain pending review.

Validation evidence:

1. `tests/unit/dpm/infrastructure/test_core_sourcing_client.py`,
2. `tests/unit/dpm/api/test_construction_api.py`,
3. `tests/unit/dpm/proof_packs/test_proof_pack_builder.py`,
4. docs/wiki/context updates naming the exact source products and avoiding unsupported ESG approval
   claims.

Remaining boundary:

Full front-office presentation of restriction/sustainability profile detail requires Gateway and
Workbench product-surface work. Security-level sustainability classification and regulatory
suitability methodology remain source-owner responsibilities; manage only preserves the source
profiles and blocks or flags the construction evidence it can justify.

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

Current implementation-backed scope:

The completed first-wave scope adds a source-owned portfolio-memory product path without inventing
source truth:

1. `GET /api/v1/rebalance/portfolio-memory/{portfolio_id}` returns a deterministic event timeline
   for one portfolio,
2. source events are composed from persisted RFC-0038 mandate health snapshots, RFC-0038
   monitoring exceptions, RFC-0040 proof packs, proof-pack-local decision timelines, RFC-0041
   rebalance wave events, internal operations handoff refs, and RFC-0042 outcome-review events,
3. proof-pack persistence now supports bounded portfolio/mandate/status search in both in-memory
   and PostgreSQL repository implementations,
4. event nodes preserve source systems, source types, source ids, content hashes, reason codes,
   supportability state, and bounded metadata,
5. the read model does not compute risk, performance, execution, tax, cash, FX, or source-owner
   methodology locally,
6. `lotus-gateway` PR #199 composes the manage read model at
   `/api/v1/dpm/command-center/portfolios/{portfolio_id}/memory` without reconstructing memory
   facts,
7. `lotus-workbench` PR #167 renders the first-wave `Portfolio Memory` panel from Gateway truth,
   including source system, source refs, content hash, supportability, event type counts, and
   timeline order,
8. `lotus-platform` PR #307 registers `dpm.portfolio_memory` in the governed Workbench panel
   registry and analytics observability rollout contract,
9. Workbench wiki publication commit `00c8279` published the repo-authored portfolio-memory
   feature, integration, and observability truth after merge,
10. the mandate-memory event slice adds `MANDATE_HEALTH_SNAPSHOT` and
    `MANDATE_MONITORING_EXCEPTION` event
    nodes from the existing mandate repository, preserving source lineage, supportability state,
    reason codes, monitoring run refs, and deterministic content hashes without recalculating
    mandate health,
11. this manage policy slice adds stable `event_identity` values plus aggregate and event-level
    `DPM_PORTFOLIO_MEMORY_SOURCE_LINEAGE_7Y`, `NO_RAW_PAYLOADS`, `AUDIT_READ_AND_EXPORT`, and
    `CLIENT_CONFIDENTIAL_INTERNAL` policy fields so downstream consumers inherit retention,
    redaction, audit, and access posture from the source-backed API contract,
12. `lotus-report` PR #92 adds the report-side bounded `portfolio_memory_context` consumer for
    proof-pack, rebalance-wave, and outcome-review report jobs, carrying event identity, content
    hash, supportability, retention, redaction, access, and audit posture into immutable snapshot
    lineage and render-package lineage without reconstructing portfolio-memory events,
13. this manage report-input context slice attaches bounded `portfolio_memory_context` to
    proof-pack, rebalance-wave, and outcome-review report inputs while keeping the context hash
    separate from recursive report-input evidence hashes,
14. `lotus-ai` PR #62 adds bounded portfolio-memory consumers for `dpm_pm_memo.pack@v1` and
    `outcome_review_narrative.pack@v1`; those consumers validate matching portfolio identity,
    capped event refs, source content hash, `NO_RAW_PAYLOADS`, and no-reconstruction
    source-authority policy before exposing compact lineage summaries in generated support output.

Remaining dependencies before full support claim:

1. source-owner event families for future report, AI, OMS, PM-scoring, and client-communication
   events when those products are implemented and supportable.

Implementation proof:

1. `tests/unit/dpm/api/test_portfolio_memory_api.py`,
2. `tests/unit/dpm/proof_packs/test_proof_pack_repository.py`,
3. `tests/unit/dpm/proof_packs/test_proof_pack_postgres_repository.py`,
4. `lotus-gateway` PR #199,
5. `lotus-workbench` PR #167,
6. `lotus-platform` PR #307,
7. `lotus-workbench/output/playwright/live-canonical/live-validation-summary.json`,
8. `lotus-workbench/output/playwright/live-canonical/dpm-portfolio-memory-live.png`,
9. `lotus-platform/output/front-office-qa/dpm-command-center-seed-20260508-090145.json`,
10. `tests/unit/dpm/api/test_portfolio_memory_api.py` mandate health and monitoring-exception
    event assertions,
11. `tests/unit/dpm/api/test_portfolio_memory_api.py` event identity, retention, redaction,
    access, and audit policy assertions,
12. `lotus-report` PR #92,
13. `lotus-report` wiki publication commit `c743ba7`,
14. `lotus-report` post-merge focused test proof:
    `python -m pytest tests/unit/reporting_render/test_service.py tests/unit/reporting_lineage/test_capture_service.py tests/unit/report_batch_orchestrator/test_boundary.py -q`,
15. Manage report-input context tests:
    `python -m pytest tests/unit/dpm/proof_packs/test_proof_pack_handoffs.py tests/unit/core/test_outcome_handoffs.py tests/unit/dpm/api/test_proof_pack_api.py tests/unit/dpm/api/test_waves_api.py -q`,
16. `lotus-ai` PR #62,
17. `lotus-ai` wiki publication commit `5267759`,
18. `lotus-ai` post-merge focused test proof:
    `python -m pytest tests/unit/test_outcome_review_narrative_guardrails.py tests/unit/test_proof_pack_pm_memo_guardrails.py tests/unit/test_workflow_pack_execution.py -q`.

Promotion proof still required:

1. README/wiki/supported-feature updates for each newly supported source-event family,
2. source-owner tests and canonical proof for each future report, AI, OMS, PM-scoring, and
   client-communication event family.

### Suggested Sequencing

Recommended order:

1. implement Gateway proof-pack composition,
2. implement Workbench proof-pack review UX,
3. resolve canonical front-office readiness blockers and prove full product realization,
4. implement report materialization in report/render/archive owners,
5. implement AI PM memo generation in `lotus-ai` under RFC-0043 controls,
6. add broader risk/performance enrichment from owning analytics services,
7. add transaction-cost, sustainability/restriction, and scenario-pack source products,
8. extend portfolio memory with future AI/OMS/PM-scoring source events as those owning products
   mature.

Rationale:

Gateway and Workbench can realize the already-supported manage proof-pack backend before broader
source enrichment exists. Report and AI should follow their owning-service controls. Risk,
performance, cost, sustainability, restriction, and scenario enrichment should be promoted only
after source authorities are certified. Portfolio memory now has a manage-owned read model plus
first-wave Gateway/Workbench product realization because mandate health, monitoring exceptions,
proof-pack, wave, handoff, and post-trade outcome events exist. Manage also owns event identity,
retention, redaction, access, and audit policy for the projected timeline. Report now has an
owning-app consumer seam for bounded portfolio-memory context, but Manage must still supply that
context in report inputs before the report path is end-to-end. Broader WTBD closure should wait
until AI/OMS/PM-scoring source events and consumers are implemented by their owners and canonically
proven.

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
| RFC41-WTBD-001 | Automatic PM-book / portfolio-manager cohort discovery | `lotus-core` source authority consumed by `lotus-manage` | Completed, merged, CI-proven, and wiki-published through `lotus-core` PR #339 and `lotus-manage` PR #126 | `lotus-core` now owns `PortfolioManagerBookMembership:v1`; `lotus-manage` consumes it for `PM_BOOK_REVIEW` wave preview/create without caller-supplied portfolio fabrication. |
| RFC41-WTBD-002 | Automatic CIO model-change affected-mandate discovery | `lotus-core` source authority consumed by `lotus-manage` | Completed in this slice for source-owned affected-cohort waves | `lotus-core` now owns `CioModelChangeAffectedCohort:v1`; `lotus-manage` consumes it for `CIO_MODEL_CHANGE` preview/create without caller-supplied portfolio fabrication. |
| RFC41-WTBD-003 | Tactical house-view, risk-event, and implicit bulk-campaign cohorts | CIO/risk/campaign source owners, with likely `lotus-risk` involvement for risk events | Deferred with no support claim | No governed scenario, risk-event, or campaign cohort authority exists for manage to consume. |
| RFC41-WTBD-004 | Risk and performance aggregate enrichment for waves | `lotus-risk`, `lotus-performance`, consumed by `lotus-manage` and later `lotus-gateway` | Completed in this slice for manage aggregate authority | RFC-0041 aggregate impact is carried from source-owned risk/performance authority context into wave aggregate metrics with supportability, lineage refs, source reason codes, and source-emitted scalar values. Manage does not calculate risk or performance methodology locally. |
| RFC41-WTBD-005 | Gateway wave composition | `lotus-gateway` | Completed, merged, CI-proven, and wiki-published through `lotus-gateway` PR #196 | Completed after manage contracts stabilized. Gateway composes manage truth without becoming wave authority or reconstructing state. |
| RFC41-WTBD-006 | Workbench wave command center | `lotus-workbench` with `lotus-gateway`, `lotus-platform`, and `lotus-manage` support | Completed, merged, CI-proven, live-proven, and wiki-published through Manage PR #120, Gateway PR #197, Platform PR #306, and Workbench PR #165 | Workbench now consumes Gateway/BFF routes only and provides the PM operating cockpit over explicit portfolio-list waves. |
| RFC41-WTBD-007 | Full front-office command-center product support | `lotus-gateway`, `lotus-workbench`, with manage as backend authority | Proposed, not supported | The full product outcome requires both downstream implementations and canonical front-office evidence, not manage backend proof alone. |
| RFC41-WTBD-008 | Report materialization from wave/proof-pack evidence | `lotus-manage`, `lotus-report`, `lotus-render`, `lotus-archive` | Completed, merged, CI-proven, and wiki-published through `lotus-manage` PR #124, `lotus-report` PR #91, `lotus-render` PR #12, and `lotus-archive` PR #24 | Manage exposes deterministic wave report input while report/render/archive own generated report, template, and archive lifecycle. |
| RFC41-WTBD-009 | AI PM memo generation from wave evidence | `lotus-ai`, governed by RFC-0043 direction; `lotus-gateway` and `lotus-workbench` as product consumers | Completed, merged, CI-proven, live-proven, and wiki-published where changed through `lotus-ai` PR #63, `lotus-gateway` PR #201, and `lotus-workbench` PR #168 | `lotus-ai` owns `dpm_wave_pm_memo.pack@v1` for bounded `DpmWaveReportInput` memo assistance. Gateway preserves Manage evidence identity and AI guardrails, while Workbench exposes report-input and AI memo request posture without constructing prompts or memo content locally. |
| RFC41-WTBD-010 | External execution integration | Future execution/OMS owner or governed operations integration | Out of RFC-0041 scope | RFC-0041 intentionally stops at internal operations handoff evidence and preserves `external_execution_claimed=false`. |

### Detailed Follow-Up Items

#### RFC41-WTBD-001 - Automatic PM-Book / Portfolio-Manager Cohort Discovery

Target business outcome:

Portfolio managers can start a rebalance wave for their governed book without manually supplying
every portfolio id, and the resulting cohort is source-backed, permission-aware, fresh, and
reconcilable.

Implementation status:

`lotus-core` source ownership is merged through PR #339 with `PortfolioManagerBookMembership:v1`.
`lotus-manage` now consumes that source product for `PM_BOOK_REVIEW` wave preview/create. Callers
supply the portfolio manager selector, as-of date, tenant/booking-center filters, and eligible
portfolio types; manage rejects caller-supplied portfolios for this trigger and builds wave items
only from lotus-core membership evidence. Explicit portfolio-list waves remain supported.

Support boundary:

1. supported: `PM_BOOK_REVIEW` backed by lotus-core `PortfolioManagerBookMembership:v1`,
2. supported: explicit source refs on each resolved item plus trigger-level PM-book snapshot refs,
3. supported: source dependency failures return blocked dependency posture instead of fabricating
   a cohort,
4. supported: `CIO_MODEL_CHANGE` backed by lotus-core `CioModelChangeAffectedCohort:v1`,
5. unsupported: tactical house-view, risk-event, campaign, permission-denied, and stale-book
   cohort semantics until owning source products exist,
6. unsupported: external OMS execution.

Promotion proof:

1. source-owner foundation merged and wiki-published in `lotus-core` PR #339,
2. manage implementation merged in PR #126 and CI-proven by Feature Lane and PR Merge Gate,
3. manage focused tests prove source-product client, PM-book preview/create, invalid selector,
   unavailable/incomplete/empty dependency handling, and source-owned empty-cohort validation,
4. full local coverage proof passed with `make check-all`: 1173 tests passed and coverage reached
   99.02%,
5. repo-local wiki source was published after merge and `Sync-RepoWikis.ps1 -CheckOnly
   -Repository lotus-manage` returned diff count 0,
6. README/wiki/supported-features state the exact promoted trigger path.

#### RFC41-WTBD-002 - Automatic CIO Model-Change Affected-Mandate Discovery

Target business outcome:

A CIO model change can produce a governed wave over the affected mandates without manually
supplying every portfolio id, with clear explanation of why each mandate is in scope.

Implementation status:

`lotus-core` source ownership is implemented in this slice with
`CioModelChangeAffectedCohort:v1`. The source product resolves the approved model definition for
the requested as-of date, emits a deterministic `model_change_event_id`, and returns effective
active discretionary mandate bindings with source lineage, snapshot identity, supportability, and
data-quality posture. `lotus-manage` consumes that product for `CIO_MODEL_CHANGE` wave preview and
create. Callers supply `model_portfolio_id`, as-of date, optional tenant, and booking-center
filters; manage rejects caller-supplied portfolios for this trigger and builds wave items only from
lotus-core affected-mandate evidence.

Support boundary:

1. supported: `CIO_MODEL_CHANGE` backed by lotus-core `CioModelChangeAffectedCohort:v1`,
2. supported: trigger-level source refs for the cohort snapshot and model-change event,
3. supported: item-level source refs for affected mandate binding rows and existing mandate digital
   twin refs,
4. supported: unavailable, incomplete, empty, invalid-selector, and caller-supplied-portfolio
   failures return explicit dependency or validation posture,
5. unsupported: tactical house-view, risk-event, campaign, permission-denied, stale-cohort,
   external OMS execution, and downstream Gateway/Workbench product rendering until owning slices
   implement and prove those paths.

Promotion proof:

1. source-owner route, service, repository, source-catalog, security-profile, route-registry, and
   domain-product tests pass in `lotus-core`,
2. manage source-client and wave API tests prove source-ready preview/create, invalid selector,
   unavailable/incomplete/empty dependency handling, and caller-supplied portfolio rejection,
3. source refs show the model-change event id, cohort snapshot, affected mandate binding, and
   mandate digital-twin lineage,
4. supported-features and wiki truth distinguish source-owned automatic model-change cohorts from
   tactical house-view, risk-event, campaign, and external execution gaps,
5. live Gateway/Workbench product rendering remains a future downstream support claim.

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

Completion result:

Implemented in this slice for manage backend wave aggregate authority. Wave simulation item input
can now carry source-backed `ConstructionAuthorityContext` evidence for `lotus-risk` and
`lotus-performance`; `RISK_AWARE` wave simulation can also use the existing configured
`DPM_RISK_BASE_URL` lotus-risk concentration authority path. `DpmWaveAggregateMetrics` now exposes
`source_analytics` entries for `RISK` and `PERFORMANCE` with supportability state, represented item
counts, source systems, source refs, bounded source-owner reason codes, and source-emitted scalar
values. Manage stores and aggregates those values for command-center lineage and display; it does
not recalculate risk or performance methodology.

Implemented controls:

1. `ConstructionAuthorityContext` now includes optional performance authority context alongside
   risk, liquidity, currency-overlay, and regime-stress context.
2. `AuthoritativeRiskContext` and `AuthoritativePerformanceContext` carry optional source product,
   source version, source id, and content hash fields so wave aggregates can expose lineage without
   raw upstream payloads.
3. Wave simulation accepts per-item authority context and passes it into RFC-0039 construction
   generation.
4. Wave item diagnostics store bounded `source_analytics` evidence derived from construction
   authority context and enrichment supportability.
5. Wave aggregate metrics reconcile source-owned analytics across items without summing or
   recomputing risk/performance values.
6. The RFC-0041 live-evidence script now requires both risk and performance source analytics in its
   aggregate reconciliation and critical-review checks.

Proof:

1. `tests/unit/dpm/api/test_waves_api.py` proves wave simulation aggregates source-owned risk and
   performance context, preserves a `READY` risk state and `DEGRADED` performance state, attaches
   source refs, carries source reason codes, and exposes only source-emitted scalar values.
2. `tests/unit/test_rfc0041_evidence_script.py` proves the live-evidence critical review now fails
   if source-owned analytics are missing from aggregate reconciliation.
3. `scripts/generate_rfc0041_wave_evidence.py` now drives the live proof through `RISK_AWARE` and
   `MIN_TURNOVER` with source-backed risk/performance authority context and records analytics
   posture under `output/rfc0041-wave-proof/<timestamp>/`.
4. Targeted local proof for this slice:
   `python -m pytest tests/unit/test_rfc0041_evidence_script.py tests/unit/dpm/api/test_waves_api.py -q`
   passed with `45 passed`.
5. Broader targeted proof:
   `python -m pytest tests/unit/dpm/api/test_waves_api.py tests/unit/dpm/infrastructure/test_risk_authority_client.py tests/unit/dpm/construction/test_enrichment.py -q`
   passed with `74 passed`.
6. Live manage proof:
   `python scripts/generate_rfc0041_wave_evidence.py --base-url http://127.0.0.1:8001`
   passed against canonical manage runtime and wrote
   `output/rfc0041-wave-proof/20260507-224144/manifest.json`; aggregate reconciliation passed with
   `risk_source_state=READY`, `performance_source_state=DEGRADED`, and critical review
   `passed`.

Remaining downstream/product realization:

1. Gateway must compose `aggregate_metrics.source_analytics` into its wave command-center contract.
2. Workbench must render the risk/performance analytics posture and degraded states in the wave
   command center without flattening source supportability.
3. A future `lotus-performance` dedicated manage client may replace caller-supplied performance
   authority context when a wave-specific performance-impact product is promoted.

#### RFC41-WTBD-005 - Gateway Wave Composition

Target business outcome:

Workbench receives a stable command-center wave contract from Gateway, while manage remains the
wave authority.

Completion result:

Completed, merged, CI-proven, and wiki-published through `lotus-gateway` PR #196. The Gateway
merge commit is `c29d895f08b7316dd363d77559623eabfc3137e8`; the Gateway wiki publication commit is
`fc427a9`. Gateway now exposes implementation-backed `/api/v1/dpm/command-center/waves*` routes
for preview, durable create, search, detail, item list, source-check, simulation, item selection,
approval, staging, internal handoff, cancellation, proof-pack posture, and supportability.

Implemented controls:

1. Gateway RFC-0098 wave addendum was used as the execution guide.
2. Typed Gateway manage client methods cover preview, create, search, detail, items,
   source-check, simulate, select, approve, stage, handoff, cancel, proof-pack posture, and
   supportability routes.
3. Gateway preserves manage `wave_id`, lifecycle state, item states, reason codes, aggregate
   metrics, selected alternative refs, proof-pack refs, handoff refs, supportability issues, and
   `external_execution_claimed=false`.
4. Gateway does not calculate affected portfolios, classify source readiness, generate
   alternatives, select alternatives, approve items, stage items, create handoff evidence, rebuild
   proof packs, cancel external orders, or claim external execution.
5. Risk/performance/report/archive/AI posture remains composed only from owning services and is not
   claimed by this Gateway slice.

Promotion proof:

1. Local focused Gateway proof: `python -m pytest tests/unit/test_dpm_wave_service.py
   tests/integration/test_dpm_wave_router.py tests/contract/test_dpm_wave_contract.py
   tests/unit/test_upstream_clients.py tests/unit/test_rfc0098_documentation.py -q` passed with
   122 tests.
2. Local Gateway `make ci` passed with 168 integration tests, 640-test coverage gate at 88.07%,
   and `pip-audit` with no known vulnerabilities.
3. GitHub PR #196 checks passed: Feature Lane lint/typecheck/unit and workflow lint; PR Merge Gate
   lint/typecheck/unit, workflow lint, integration tests, coverage gate, Docker build, Docker
   parity, and queue auto-merge.
4. Gateway repo-local wiki source was published after merge and `Sync-RepoWikis.ps1 -CheckOnly
   -Repository lotus-gateway` reported diff count 0.

#### RFC41-WTBD-006 - Workbench Wave Command Center

Target business outcome:

Portfolio managers and operations users can review, simulate, approve, stage, hand off, and monitor
rebalance waves through a governed Workbench command-center experience.

Completion result:

Completed on 2026-05-07 and merged to `main` across the owning repositories. The implementation
keeps `lotus-manage` as the wave authority, `lotus-gateway` as the product API/BFF composition
layer, `lotus-platform` as the panel-registry and canonical-validation contract authority, and
`lotus-workbench` as the PM command-center surface.

What was delivered:

1. Manage PR #120 added source-owned wave `supportability` to preview/create/workflow responses
   and regenerated the API vocabulary inventory so downstream callers do not infer readiness.
2. Gateway PR #197 added preservation proof for Manage-provided wave supportability at the
   command-center preview boundary.
3. Platform PR #306 registered `dpm.wave_command_center` in the Workbench panel registry and
   analytics UI observability readiness contract.
4. Workbench PR #165 added the `Rebalance Wave Command Center` panel on `/workbench/{portfolioId}`
   with Gateway-backed list, preview, create, detail, items, source-check, simulate, approve, stage,
   handoff, proof-posture, and supportability actions.
5. Workbench live validation now pre-probes the Gateway wave endpoint, executes the preview action,
   records `dpm.wave_command_center`, and captures `dpm-wave-command-center-live.png` only after
   canonical validation passes.
6. Workbench wiki source now includes current feature coverage, integration posture, roadmap, and
   supported-features material for developers, operations, business users, sales/pre-sales, and
   client-demo preparation.

Promotion proof:

1. Governed canonical live proof passed through platform QA:
   `lotus-platform/output/front-office-qa/canonical-front-office-qa-20260507-142715.json`.
2. DPM seed evidence was captured at
   `lotus-platform/output/front-office-qa/dpm-command-center-seed-20260507-143459.json`.
3. Screenshot evidence was captured at
   `lotus-workbench/output/playwright/live-canonical/dpm-wave-command-center-live.png`.
4. GitHub checks passed for Manage PR #120, Gateway PR #197, Platform PR #306, and Workbench PR
   #165, including feature lanes, PR merge gates, Docker build/parity checks, Workbench Playwright
   smoke, and Manage coverage/API-vocabulary gates.
5. Repo-local wiki source was published after merge for `lotus-manage` (`ed3569b`) and
   `lotus-workbench` (`212f486`). Gateway and Platform required no additional wiki publication for
   this closure slice.
6. Final closure keeps unsupported scope explicit: CIO/risk-event cohort discovery, AI memo
   generation from wave evidence, downstream rendering of the source-owned risk/performance
   analytics posture, and external OMS execution remain separate WTBDs.

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

Status: Completed on merged, validated, and wiki-published owning-repo truth.

Target business outcome:

Wave and proof-pack evidence can be materialized into governed reports and archived artifacts.

Implemented scope:

1. `lotus-manage` PR #124 added deterministic `DpmWaveReportInput` generation and
   `GET /api/v1/rebalance/waves/{wave_id}/report-input`, preserving wave identity, proof-pack
   lineage, supportability posture, selected-item evidence, hashes, actors, and handoff refs without
   generating rendered documents locally.
2. `lotus-report` PR #91 added `POST /reports/rebalance-waves`, wave snapshot lineage capture,
   report-job ledger persistence, and a render package that consumes manage wave report input rather
   than reconstructing wave state.
3. `lotus-render` PR #12 added the `rebalance-wave` v1 Typst template and manifest so generated
   wave reports use a governed template family with registry validation.
4. `lotus-archive` PR #24 added `rebalance_wave` as a governed generated-report type and validated
   archive lifecycle metadata, retention, hash, and retrieval behavior for wave reports.

Promotion proof:

1. `lotus-manage` PR #124 merged to `main` with Feature Lane and PR Merge Gate checks green; local
   `make check` passed with 931 tests passed, 13 skipped, and API vocabulary regenerated.
2. `lotus-report` PR #91 merged to `main` after coverage hardening; CI Feature Lane and PR Merge
   Gate checks passed, including coverage, Docker, unit, integration, and e2e gates.
3. `lotus-render` PR #12 merged to `main`; local `make check` passed with 82 tests and template
   registry validation, and CI passed.
4. `lotus-archive` PR #24 merged to `main`; local `make check` passed with lint, typecheck,
   OpenAPI, migration, and 74 tests, and CI passed.
5. Repo-local wiki source was published after merge for `lotus-manage`, `lotus-report`,
   `lotus-render`, and `lotus-archive`; post-publication wiki check-only drift is clean.

Remaining boundary:

This closure does not make `lotus-manage` a report renderer, archive authority, or document
retention service. It remains the source of wave evidence and deterministic report input. Gateway
and Workbench may surface report availability in a later product slice, but must consume the
owning report/archive posture rather than inferring availability in the browser or BFF.

#### RFC41-WTBD-009 - AI PM Memo Generation From Wave Evidence

Target business outcome:

PMs can request governed AI assistance over wave/proof-pack evidence without exposing forbidden
fields or allowing unsupported action recommendations.

Current implementation-backed state:

`lotus-ai` PR #63 implements the owner-side workflow pack `dpm_wave_pm_memo.pack@v1` on `main`
with CI proof and wiki publication. The pack validates Manage-owned `DpmWaveReportInput` payloads,
blocks forbidden fields, forbidden actions, autonomous requested outputs, raw payload exposure, and
external execution claims, preserves provenance and supportability posture, and returns a
review-required support-only memo payload. Manage remains evidence authority only and must not
create prompts, memos, recommendations, or AI-side workflow state locally.

`lotus-gateway` PR #201 and `lotus-workbench` PR #168 complete the product consumption path.
Gateway requests the AI workflow using Manage-owned wave report input and passes both
`blocked_actions` and `forbidden_actions` supportability controls to `lotus-ai`. Workbench exposes
the governed report-input and AI memo actions from the DPM wave command-center panel, records
observability for `dpm.waves.report-input` and `dpm.waves.ai-pm-memo`, and canonical live
validation proves the full path against the populated front-office runtime before screenshots are
accepted as demo evidence.

Implemented dependencies:

1. RFC-0043 or `lotus-ai` workflow-pack contract defines the memo workflow,
2. forbidden fields and forbidden actions are enforced,
3. provenance, model/prompt identity, input evidence hashes, and fallback states are captured,
4. Gateway/Workbench UI exposes AI posture without bypassing AI service controls,
5. AI unavailable and guardrail-blocked states are tested.

Closure posture:

This WTBD is complete for the first-wave governed product path. Manage remains wave evidence and
report-input authority; Gateway remains the BFF/product API composition layer; Workbench remains
the PM-facing product surface; and `lotus-ai` remains the only memo workflow owner. The closure does
not claim autonomous recommendations, external execution, direct browser-side prompt generation,
or future CIO/risk-event cohort discovery.

Promotion proof:

1. `lotus-ai` PR #63 merge commit `3af5b8f8d6fee96cdc77b8c8c878b4ffdc4b01e3`,
2. `lotus-ai` wiki publication commit `6bed940`,
3. local `lotus-ai` `make check` proof and PR Merge Gate proof for PR #63,
4. AI guardrail and provenance tests,
5. prompt/input-output evidence with sensitive-field protections,
6. unavailable and blocked-state proof,
7. `lotus-gateway` PR #201 merge commit `6171df567010067edcb9fefc7acec92f68f5fde7`,
8. Gateway focused post-merge proof:
   `python -m pytest tests/unit/test_dpm_wave_service.py tests/integration/test_dpm_wave_router.py tests/contract/test_dpm_wave_contract.py -q`, 17 passed,
9. `lotus-workbench` PR #168 merge commit `ed0727a2f3571ec1dcbbab57fe79dc89b81086d9`,
10. `lotus-workbench` wiki publication commit `31ce0bd`,
11. Workbench focused post-merge proof:
    `npm test -- --run tests/unit/dpm-wave-command-center-view-model.test.ts tests/unit/live-canonical-validation-script.test.ts tests/unit/live-validation-browser-workflows.test.ts`, 16 passed,
12. Workbench RFC documentation proof:
    `python -m pytest tests/unit/test_rfc0098_documentation.py -q`, 1 passed,
13. Canonical live product proof:
    `npm run live:validate:ui`, passed with evidence under
    `lotus-workbench/output/playwright/live-canonical/` including the DPM wave command-center
    report-input and AI memo path,
14. supported-feature entries that do not imply autonomous execution authority.

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

1. implement Workbench wave command center,
2. prove full front-office command-center product support,
3. implement source-owned PM-book and CIO model-change cohort products,
4. promote manage automatic discovery triggers from certified source products,
5. add risk/performance aggregate enrichment from owning analytics services,
6. implement report materialization and AI memo generation in their owning apps,
7. evaluate external execution only after the execution owner and RFC-0042 post-trade feedback
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

Latest WTBD-006 performance MWR source-truth proof:

1. `lotus-performance` branch `wtbd-rfc42-performance-mwr-methodology-source-truth` tightens
   `docs/methodologies/metrics/metric-mwr-xirr.md`,
   `docs/methodologies/metrics/metric-mwr-dietz.md`, and
   `docs/methodologies/metrics/master-index.md` so MWR methodology truth covers both stateless
   caller-owned inputs and stateful lotus-core source resolution,
2. the source-owner methodology docs now describe `stateful_input.window_start_date`,
   `CORE_CONTROL_PLANE_BASE_URL`, cross-observation carry-forward capital adjustments, fee-row
   exclusion from investor cash flows, resolved start-date behavior, `cashflows_used`,
   `calculation_supportability`, and downstream no-reconstruction posture,
3. `lotus-performance` wiki source `wiki/Integrations.md` now includes a Mermaid source-flow
   diagram from lotus-core timeseries through performance MWR normalization, engine execution,
   Gateway contract consumption, and Workbench investor capital-timing display,
4. focused documentation proof passed with `43` tests:
   `python -m pytest tests/unit/docs/test_metric_methodology_docs.py tests/unit/docs/test_public_docs_contract.py -q`,
5. implementation-backed proof passed with `41` MWR engine/service/integration tests:
   `python -m pytest tests/unit/engine/test_mwr.py tests/unit/services/test_mwr_mode_service.py tests/unit/services/test_workspace_summary_service.py tests/integration/test_mwr_api.py tests/integration/test_response_attribute_certification.py -q`,
6. `python -m ruff check tests/unit/docs/test_metric_methodology_docs.py tests/unit/docs/test_public_docs_contract.py`
   and `git diff --check` passed; repo-local wiki check-only reports expected drift for
   `API-Surface.md` and `Integrations.md` until the branch is merged and wiki publication is run.

Latest WTBD-006 performance contribution source-truth proof:

1. `lotus-performance` branch `wtbd-rfc42-performance-contribution-methodology-source-truth`
   tightens `docs/methodologies/metrics/metric-contribution-total.md`,
   `metric-contribution-local.md`, `metric-contribution-fx.md`, and
   `docs/methodologies/metrics/master-index.md` so contribution methodology truth covers stateless
   caller-owned inputs and stateful lotus-core portfolio/position timeseries normalization,
2. the source-owner methodology docs now describe `stateful_input.metric_basis`,
   `stateful_input.dimensions`, `stateful_input.include_cash_flows`, source filters,
   portfolio/position retrieval, source currency metadata, FX requirements for mixed-currency
   stateful contribution, `calculation_supportability`, and downstream no-reconstruction posture,
3. `lotus-performance` wiki source `wiki/Integrations.md` now includes a Mermaid source-flow
   diagram from lotus-core portfolio and position timeseries through performance contribution
   normalization, total/local/FX contribution execution, and downstream Gateway, Workbench, risk,
   and reporting consumption,
4. focused documentation proof passed with `44` tests:
   `python -m pytest tests/unit/docs/test_metric_methodology_docs.py tests/unit/docs/test_public_docs_contract.py -q`,
5. implementation-backed proof passed with `48` contribution stateful/service/integration tests:
   `python -m pytest tests/unit/services/test_stateful_contribution_input_service.py tests/integration/test_contribution_api.py -q`,
6. `git diff --check` passed; repo-local wiki publication remains required after merge because
   `API-Surface.md` and `Integrations.md` changed.

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
