# Repository Engineering Context

This file provides repository-local engineering context for `lotus-manage`.

For platform-wide truth, read:

1. `../lotus-platform/context/LOTUS-QUICKSTART-CONTEXT.md`
2. `../lotus-platform/context/LOTUS-ENGINEERING-CONTEXT.md`
3. `../lotus-platform/context/CONTEXT-REFERENCE-MAP.md`

## Repository Role

`lotus-manage` is the discretionary mandate portfolio-management execution and operational
supportability service.

It owns management-side rebalance execution, what-if orchestration, run supportability, policy-pack
controls, and mandate workflow review for discretionary portfolio management.

## Business And Domain Responsibility

This repository owns:

1. discretionary mandate rebalance simulation and what-if workflow APIs,
2. management-side lifecycle, workflow review, and execution support,
3. operational supportability, deterministic artifacts, lineage, idempotency, and policy-pack
   contracts.

Advisor-led proposal simulation, artifacts, consent, and lifecycle workflows are intentionally
owned by `lotus-advise`.

## Current-State Summary

Current repository posture:

1. `lotus-manage` is the management-side service after the split from `lotus-advise`,
2. canonical local host runtime uses port `8001` so it can coexist with `lotus-advise`,
3. local CI and Docker parity are already standardized under the RFC-0072 lane model,
4. upstream and source-data authority posture is classified under RFC-0082 in `docs/standards/RFC-0082-upstream-contract-family-map.md`,
5. it carries repo-native RFC-0084 consumer declarations for the governed core portfolio-state
   product used by management execution request contracts,
6. it carries the RFC-0091 repo-native producer declaration and telemetry fixture for
   `PortfolioActionRegister`,
7. the service remains part of the canonical front-office validation path through `lotus-gateway`,
8. current execution APIs support explicit `input_mode=stateless` caller-supplied portfolio,
   market-data, model, shelf, and option bundles,
9. stateful `portfolio_id` execution has typed selector/context models, a bounded `lotus-core`
   resolver client, transformation helpers, and lineage fields; it is disabled by default but
   live-proven when explicit stateful gates and `DPM_CORE_BASE_URL` are configured,
10. RFC-087 composed source-product integrations are implemented and live-proven for
    `DpmModelPortfolioTarget:v1` through
    `/integration/model-portfolios/{model_portfolio_id}/targets` and
    `DiscretionaryMandateBinding:v1` through
    `/integration/portfolios/{portfolio_id}/mandate-binding`, and
    `InstrumentEligibilityProfile:v1` through `/integration/instruments/eligibility-bulk`, and
    `PortfolioTaxLotWindow:v1` through `/integration/portfolios/{portfolio_id}/tax-lots`,
    `MarketDataCoverageWindow:v1` through `/integration/market-data/coverage`, and
    `DpmSourceReadiness:v1` through `/integration/portfolios/{portfolio_id}/dpm-source-readiness`.
11. RFC-0037 through RFC-0043 define the strategic revamp into a DPM operating system.
    RFC-0038, RFC-0039, RFC-0040, and the manage-owned explicit portfolio-list wave scope of
    RFC-0041 are now implementation-backed. Remaining roadmap scope stays target-state planning
    material until implementation-backed support, live proof, and supported-feature promotion are
    completed.
12. RFC-0038 has delivered the first implementation-backed DPM operating-system foundation with a
    source-mapped `DpmMandateDigitalTwin`, deterministic ten-dimension mandate health engine,
    derived monitoring-exception taxonomy, repository contract, in-memory and PostgreSQL
    persistence, mandate migrations, certified mandate refresh/read/version/diff APIs, standalone
    health APIs, bounded monitoring/exception APIs, and a bounded command-center summary API.
    Local manage proof, local canonical manage plus live `lotus-core` proof, supported-feature
    promotion, and wiki publication have passed. Gateway composition, Workbench cockpit panels, and
    populated platform canonical seed automation are now implementation-backed and live-proven in
    their owning repositories; partial/empty command-center seed fixtures and PM-book discovery
    remain governed downstream follow-up.
13. RFC-0039 has delivered the implementation-backed construction-alternative backend foundation:
    bounded construction vocabulary, pure alternative models, method registry, enrichment posture,
    risk/performance seams, repository contract, in-memory and PostgreSQL persistence foundation,
    migration `0005_construction_alternatives.sql`, and certified APIs for generating, retrieving,
    and selecting persisted alternative sets. First-wave and mandatory authority-backed methods are
    supported as manage backend capabilities: solver-constrained, risk-aware through `lotus-risk`
    concentration authority, liquidity-aware with optional `lotus-core`
    `PortfolioCashflowProjection:v1` projected cash-pressure evidence, currency-overlay, and
    regime-stress-aware through `lotus-risk` `RegimeScenarioPackEvaluation:v1` when
    `DPM_RISK_BASE_URL` is configured. Client income-need planning is not supported by cashflow
    projection totals and remains deferred until an owning source product exists.
    ESG/restriction-aware construction is explicitly deferred until restriction and sustainability
    source products exist. Gateway and Workbench are not yet integrated with this surface; paired
    realization RFCs have been created and must be implemented/proven downstream before a full
    front-office product outcome is claimed.
14. RFC-0040 has delivered the implementation-backed manage pre-trade proof-pack backend
    foundation: durable `DpmPreTradeProofPack` JSON, deterministic Markdown summary, report-input
    handoff, AI-evidence handoff with forbidden-action/field guardrails, immutable in-memory and
    PostgreSQL persistence, append-only refs, retention metadata, section/content hashes, source
    lineage, source-backed mandate-context attachment from persisted RFC-0038 mandate twin and
    health evidence when available, certified `/api/v1/rebalance/proof-packs/*` APIs, and
    canonical Postgres-backed live proof under `output/rfc0040-proof/20260503-135112`,
    post-merge audit rerun `output/rfc0040-proof/20260503-142438`, and mandate-context hardening
    rerun `output/rfc0040-proof/20260503-145818`. `lotus-gateway` and `lotus-workbench` RFC-0098
    documents have been aligned to consume manage truth without reconstruction. Gateway
    composition, Workbench proof-pack review UX, report materialization, AI memo generation, and
    full front-office product-outcome support remain downstream work in the owning repositories;
    the post-merge canonical front-office QA run exposed a downstream risk-drawdown `partial`
    boundary tracked as `sgajbi/lotus-gateway#182`, and therefore no full product UX support claim
    is made here.
15. RFC-0041 is `DONE` for implementation-backed manage backend authority over explicit
    portfolio-list rebalance waves: durable preview/create,
    source-check, RFC-0039-backed ready-item simulation, item-level selection, RFC-0040 proof-pack
    linkage, approval-with-exceptions, staging, internal operations handoff evidence with
    `external_execution_claimed=false`, actor-attributed pre-execution cancellation,
    repository-backed wave search/detail/item/proof-pack posture/supportability read models,
    OpenAPI certification, and aggregate reconciliation under
    `output/rfc0041-wave-proof/20260504-231914`. The canonical proof used Postgres-backed manage
    repositories via `DPM_MANAGE_POSTGRES_DSN`. Automatic PM-book and CIO model-change cohort
    discovery, Gateway composition, Workbench UX, and full front-office product support remain
    unpromoted until owning source products and downstream implementations are live-proven.
16. RFC-0042 is `DONE` for manage backend authority:
    source-backed outcome-review preview/create/retrieve/search, immutable persistence and
    append-only events, source-refresh eventing, report-input and AI-evidence handoff contracts,
    supportability diagnostics, bounded metrics/logging, source-owned realized adapters for
    `lotus-risk` `RiskMetricsReport:v1`, drawdown response max drawdown, concentration
    response selected measures, rolling metrics selected metric/statistic/window measures, and
    historical attribution selected set/contributor measures,
    `lotus-performance` workspace-summary TWR/active/MWR returns,
    contribution selected measures, and attribution reconciliation/level/currency selected
    measures, and `lotus-core` `HoldingsAsOf:v1` cash totals plus
    `TransactionLedgerWindow:v1` explicit transaction-row trade-fee, withholding-tax,
    realized-FX-P&L, linked-cashflow measures, and `PortfolioCashflowProjection:v1` total net
    cashflow, live
    canonical manage proof under `output/rfc0042-outcome-proof/20260505-024352`, and Slice 12 hardening proof under
    `output/rfc0042-outcome-proof/20260505-025613`. The proof found and fixed stale listener
    restart handling in `scripts/Start-CanonicalManage.ps1`, OpenAPI What/When/How gaps on
    outcome-review GET routes, same-key changed-evidence idempotency conflict handling, and invalid
    search-state filter validation. Full product support remains downstream until Gateway/Workbench
    implementation where surfaced is complete and canonically proven.

## Architecture And Module Map

Primary areas:

1. `src/`
   management APIs, workflow logic, and supporting modules.
   RFC-0038 mandate digital-twin and health-scoring domain primitives live in
   `src/core/mandates.py`; repository and persistence primitives live in
   `src/core/mandate_repository.py` and `src/infrastructure/mandates/`; mandate API orchestration
   lives in `src/api/services/mandate_service.py`, `src/api/routers/mandates.py`, and
   `src/api/routers/monitoring.py`, including the bounded command-center summary endpoint.
   RFC-0039 construction-alternative domain primitives live in `src/core/construction/`;
   construction persistence lives in `src/core/construction/repository.py` and
   `src/infrastructure/construction/`; construction API orchestration lives in
   `src/api/services/construction_service.py` and `src/api/routers/construction.py`.
   RFC-0042 outcome-review authority lives in `src/core/outcomes/`; outcome persistence lives in
   `src/infrastructure/outcomes/`; API orchestration lives in
   `src/api/services/outcome_review_service.py` and `src/api/routers/outcome_reviews.py`.
2. `scripts/`
   OpenAPI, vocabulary, migration, and governance scripts.
3. `docs/`
   project overview, runbooks, standards, demo evidence, and RFC documentation.
4. `wiki/`
   canonical authored source for repository wiki publication and operator onboarding summaries.
5. `tests/`
   unit, integration, and e2e validation.
6. `contracts/domain-data-products/`
   repo-native producer and consumer declarations for governed upstream domain data products and
   management workflow products.
7. `contracts/trust-telemetry/`
   repo-native RFC-0087/RFC-0091 trust telemetry snapshots for governed management products.

## Runtime And Integration Boundaries

Runtime model:

1. FastAPI service,
2. depends on `lotus-core` as source-data authority for governed stateful source-data resolution,
   while default execution consumes explicit stateless request bundles,
3. primarily consumed through `lotus-gateway`,
4. canonical host runtime is exposed through `manage.dev.lotus`.

Boundary rules:

1. management workflows belong here,
2. proposal and advisor-led flows belong in `lotus-advise` and should not be reintroduced here,
3. host runtime identity and coexistence with `lotus-advise` are part of the operational contract,
4. management capabilities should remain aligned with gateway-facing product expectations,
5. `lotus-core` remains the source-data authority for core-referenced portfolio, market-data, price, and FX inputs,
6. REST/OpenAPI remains the canonical integration contract; gRPC is not justified for current management workflows.

## Repo-Native Commands

Use these commands as the primary local contract:

1. install
   `make install`
2. fast local gate
   `make check`
3. PR-grade local gate
   `make ci`
4. feature-lane local gate
   `make ci-local`
5. Docker parity
   `make ci-local-docker`
6. canonical host runtime
   `make run-canonical`
7. domain-data-product contract validation
   `make domain-product-validate`

## Validation And CI Expectations

`lotus-manage` uses explicit CI lanes:

1. `Remote Feature Lane`
2. `Pull Request Merge Gate`
3. `Main Releasability Gate`

Important validation expectations:

1. no-alias, OpenAPI, API vocabulary, migration smoke, and security audit are active,
2. PR-grade validation includes coverage-backed full test execution,
3. host/runtime coexistence assumptions matter for canonical front-office startup,
4. README changes should preserve the local Docker runtime contract language enforced by
   `tests/unit/test_local_docker_runtime_contract.py`,
5. DPM supportability and OpenAPI-facing docs changes should respect the targeted contract tests in
   `tests/unit/dpm/contracts/test_contract_openapi_supportability_docs.py`,
6. current operational evidence docs under `docs/demo/` and runbooks should preserve canonical
   `lotus-manage` service, image, and ingress identity while clearly labeling historical local-only
   debug paths.
7. RFC/docs/wiki/context work must include stranded-truth reconciliation before RFC start, final
   closure, post-merge audit, and move-on to the next RFC. Run `git fetch origin --prune` and
   `git branch -r --no-merged origin/main`, inspect unmerged branches touching `docs/rfcs/`,
   `wiki/`, `README.md`, `REPOSITORY-ENGINEERING-CONTEXT.md`, `AGENTS.md`, contracts, standards,
   OpenAPI/vocabulary, migrations, CI workflows, or supported-features material, and classify each
   branch as `must-merge`, `cherry-pick`, `superseded`, `delete`, or `active`. This is mandatory
   because RFC-0036 through RFC-0042 work previously exposed a failure mode where
   `docs/rfcs/RFC-worktobedone.md` and an RFC-0041 post-closure documentation correction were
   stranded on unmerged side branches instead of reaching `main`.

## Standards And RFCs That Govern This Repository

Most relevant current governance:

1. `../lotus-platform/rfcs/RFC-0066-lotus-advise-to-lotus-advise-and-lotus-manage-split.md`
2. `../lotus-platform/rfcs/RFC-0067-centralized-api-vocabulary-inventory-and-openapi-documentation-governance.md`
3. `../lotus-platform/rfcs/RFC-0071-centralized-environment-scoped-service-addressing-and-ingress-governance.md`
4. `../lotus-platform/rfcs/RFC-0072-platform-wide-multi-lane-ci-validation-and-release-governance.md`
5. `../lotus-platform/rfcs/RFC-0073-lotus-ecosystem-engineering-context-and-agent-guidance-system.md`
6. `../lotus-platform/rfcs/RFC-0082-lotus-core-domain-authority-and-analytics-serving-boundary-hardening.md`
7. `docs/standards/RFC-0082-upstream-contract-family-map.md`

## Known Constraints And Implementation Notes

1. management/advisory boundary clarity remains a real quality concern after the split,
2. canonical local host runtime matters because port coexistence with `lotus-advise` is intentional,
3. local `pip check` and project-scoped security posture still matter for repo truth here,
4. stateful `portfolio_id` mode is disabled by default through
   `DPM_STATEFUL_CORE_SOURCING_ENABLED=false`; integration capabilities must not publish
   `stateful` unless `DPM_CAP_INPUT_MODE_PORTFOLIO_ID_ENABLED=true`,
   `DPM_STATEFUL_CORE_SOURCING_ENABLED=true`, `DPM_CORE_BASE_URL` is configured, and any configured
   core resolver path is not the retired monolithic `dpm-execution-context` route,
5. `DpmModelPortfolioTarget:v1`, `DiscretionaryMandateBinding:v1`,
   `InstrumentEligibilityProfile:v1`, `PortfolioTaxLotWindow:v1`,
   `MarketDataCoverageWindow:v1`, and `DpmSourceReadiness:v1` are the core source products used to
   prove stateful manage execution against the canonical mandate portfolio,
6. this repo should stay operationally aligned with gateway and platform startup sequences,
7. repo-local `wiki/` content should stay concise, operator-focused, and derived from repo truth
   rather than duplicating the full `docs/` tree,
8. enterprise audit and readiness surfaces must emit `lotus-manage` service identity rather than
   stale split-era names,
9. `make check` may refresh generated API vocabulary output; docs-only slices should inspect that
   diff and avoid committing timestamp-only churn when the semantic inventory is unchanged,
10. the current repo-native domain-data-product declaration intentionally records only governed
    `PortfolioStateSnapshot` input consumption through caller-supplied management request payloads;
    market-data and future stateful `portfolio_id` resolution must be added only after upstream
    producer approval and an explicit source-data retrieval design.
11. target-state RFC-0037 through RFC-0043 work may redesign or remove stale manage APIs because
    no production downstream dependency is assumed for the revamp surface. Any downstream usage
    discovered during implementation should be documented and migrated to the certified target
    contract rather than preserved through permanent compatibility aliases.
12. durable RFC control artifacts such as `docs/rfcs/RFC-worktobedone.md`, source maps, proof
    indexes, and supported-feature ledgers must be referenced from stable navigation docs and pinned
    by `tests/unit/test_documentation_current_state.py` or an equivalent docs/current-state test
    whenever practical.

## Context Maintenance Rule

Update this document when:

1. management workflow ownership changes,
2. runtime or coexistence assumptions with `lotus-advise` change,
3. repo-native commands or CI expectations change,
4. upstream or downstream integration posture changes materially,
5. RFC-0082 contract-family classification changes,
6. current-state rollout posture changes,
7. README or `wiki/` structure changes the repository-local onboarding or operator navigation model.

## Cross-Links

1. `../lotus-platform/context/LOTUS-QUICKSTART-CONTEXT.md`
2. `../lotus-platform/context/LOTUS-ENGINEERING-CONTEXT.md`
3. `../lotus-platform/context/CONTEXT-REFERENCE-MAP.md`
4. `../lotus-platform/context/Repository-Engineering-Context-Contract.md`
5. [Lotus Developer Onboarding](../lotus-platform/docs/onboarding/LOTUS-DEVELOPER-ONBOARDING.md)
6. [Lotus Agent Ramp-Up](../lotus-platform/docs/onboarding/LOTUS-AGENT-RAMP-UP.md)
