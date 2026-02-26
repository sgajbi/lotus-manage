# RFC Index

Standards for all current and future RFCs:
- `docs/rfcs/RFC-CONVENTIONS.md`

Governance boundary:
- Service-specific implementation RFCs belong in this repository.
- Cross-cutting platform and multi-service RFCs belong in `https://github.com/sgajbi/lotus-platform`.

| RFC | Title | Status | Depends On | File |
| --- | --- | --- | --- | --- |
| RFC-0001 | Enterprise Rebalance Simulation MVP (DPM Platform) | IMPLEMENTED | - | `docs/rfcs/RFC-0001-rebalance-simulation-mvp.md` |
| RFC-0002 | Rebalance Simulation MVP Hardening & Enterprise Completeness | IMPLEMENTED | RFC-0001 | `docs/rfcs/RFC-0002-rebalance-simulation-mvp-hardening-enterprise-completeness.md` |
| RFC-0003 | Rebalance Simulation Contract & Engine Completion (Audit Bundle) | IMPLEMENTED | RFC-0001, RFC-0002 | `docs/rfcs/RFC-0003-contract-engine-completion.md` |
| RFC-0004 | Institutional After-State + Holdings-aware Golden Scenarios (Demo-tight, Pre-Persistence) | IMPLEMENTED | RFC-0003 | `docs/rfcs/RFC-0004-institutional-afterstate-holdings-goldens.md` |
| RFC-0005 | Institutional Tightening (Post-trade Rules, Reconciliation, Demo Pack) | IMPLEMENTED | RFC-0004 | `docs/rfcs/RFC-0005-institutional-tightening-post-trade-rules-reconciliation-demo-pack.md` |
| RFC-0006A | Pre-Persistence Hardening - Safety, After-State Completeness, Contract Consistency | IMPLEMENTED | RFC-0003, RFC-0005 | `docs/rfcs/RFC-0006A-pre-persistence-safety-afterstate.md` |
| RFC-0006B | Pre-Persistence Hardening - Rules Configurability, Dependency Fidelity & Scenario Matrix | IMPLEMENTED | RFC-0006A | `docs/rfcs/RFC-0006B-pre-persistence-rules-scenarios-demo.md` |
| RFC-0007A | Contract Tightening - Canonical Endpoint, Discriminated Intents, Valuation Policy, Universe Locking | IMPLEMENTED | RFC-0006A, RFC-0006B | `docs/rfcs/RFC-0007A-contract-tightening.md` |
| RFC-0008 | Multi-Dimensional Constraints (Attribute Tagging and Group Limits) | IMPLEMENTED | RFC-0007A | `docs/rfcs/RFC-0008-multi-dimensional-constraints-attribute-tagging-group-limits.md` |
| RFC-0009 | Tax-Aware Rebalancing (HIFO and Tax Budget) | IMPLEMENTED | RFC-0008 | `docs/rfcs/RFC-0009-tax-aware-rebalancing-hifo-tax-budget.md` |
| RFC-0010 | Turnover & Transaction Cost Control | IMPLEMENTED | RFC-0007A | `docs/rfcs/RFC-0010-turnover-transaction-cost-control.md` |
| RFC-0011 | Settlement Awareness (Cash Ladder & Overdraft Protection) | IMPLEMENTED | RFC-0007A | `docs/rfcs/RFC-0011-settlement-awareness-cash-ladder-overdraft-protection.md` |
| RFC-0012 | Mathematical Optimization (Solver Integration) | IMPLEMENTED | RFC-0008 | `docs/rfcs/RFC-0012-mathematical-optimization-solver-integration.md` |
| RFC-0013 | "What-If" Analysis Mode (Multi-Scenario Simulation) | IMPLEMENTED | RFC-0003 | `docs/rfcs/RFC-0013-what-if-analysis-mode-multi-scenario-simulation.md` |
| RFC-0014A | Advisory Proposal Simulation MVP (Manual Trades + Cash Flows) | IMPLEMENTED | RFC-0003, RFC-0006A | `docs/rfcs/advisory pack/refine/RFC-0014A-advisory-proposal-simulate-mvp.md` |
| RFC-0014B | Advisory Proposal Auto-Funding (FX Spot Intents + Dependency Graph) | IMPLEMENTED | RFC-0014A, RFC-0006A | `docs/rfcs/advisory pack/refine/RFC-0014B-advisory-proposal-auto-funding.md` |
| RFC-0014C | Drift Analytics for Advisory Proposals (Before vs After vs Reference Model) | IMPLEMENTED | RFC-0014A, RFC-0006A | `docs/rfcs/advisory pack/refine/RFC-0014C-drift-analytics.md` |
| RFC-0014D | Suitability Scanner v1 for Advisory Proposals | IMPLEMENTED | RFC-0014A, RFC-0006A | `docs/rfcs/advisory pack/refine/RFC-0014D-suitability-scanner-v1.md` |
| RFC-0014E | Advisory Proposal Artifact | IMPLEMENTED | RFC-0014A, RFC-0014B, RFC-0014C, RFC-0014D | `docs/rfcs/advisory pack/refine/RFC-0014E-proposal-artifact.md` |
| RFC-0014G | Proposal Persistence and Workflow Lifecycle | IMPLEMENTED (MVP DELIVERED, POSTGRES SLICES COMPLETED VIA RFC-0024) | RFC-0014A, RFC-0014E, RFC-0014F | `docs/rfcs/advisory pack/refine/RFC-0014G-proposal-persistence-workflow-lifecycle.md` |
| RFC-0015 | Deferred Scope Consolidation and Completion Backlog | SUPERSEDED (TRIAGED) | RFC-0001..RFC-0013 | `docs/rfcs/RFC-0015-deferred-scope-consolidation-and-completion-backlog.md` |
| RFC-0016 | DPM Idempotency Replay Contract for `/rebalance/simulate` | IMPLEMENTED | RFC-0001, RFC-0002, RFC-0007A | `docs/rfcs/RFC-0016-dpm-idempotency-replay-contract.md` |
| RFC-0017 | DPM Run Supportability APIs (Run, Correlation, Idempotency Lookup) | IMPLEMENTED | RFC-0001, RFC-0002, RFC-0016 | `docs/rfcs/RFC-0017-dpm-run-supportability-apis.md` |
| RFC-0018 | DPM Async Operations Resource | IMPLEMENTED | RFC-0013, RFC-0016, RFC-0017 | `docs/rfcs/RFC-0018-dpm-async-operations-resource.md` |
| RFC-0019 | DPM Deterministic Run Artifact Contract | IMPLEMENTED (PHASE 1 - DERIVED ARTIFACT) | RFC-0003, RFC-0013, RFC-0017 | `docs/rfcs/RFC-0019-dpm-deterministic-run-artifact-contract.md` |
| RFC-0020 | DPM Workflow Gate API and Persistence | IMPLEMENTED | RFC-0017, RFC-0019 | `docs/rfcs/RFC-0020-dpm-workflow-gate-api-and-persistence.md` |
| RFC-0021 | DPM OpenAPI Contract Hardening and Separation of Request/Response Models | IMPLEMENTED | RFC-0007A, RFC-0016, RFC-0017 | `docs/rfcs/RFC-0021-dpm-openapi-contract-hardening.md` |
| RFC-0022 | DPM Policy Pack Configuration Model | IMPLEMENTED | RFC-0008, RFC-0010, RFC-0011, RFC-0016 | `docs/rfcs/RFC-0022-dpm-policy-pack-configuration-model.md` |
| RFC-0023 | DPM Persistent Supportability Store and Lineage APIs | IMPLEMENTED | RFC-0017, RFC-0018, RFC-0019 | `docs/rfcs/RFC-0023-dpm-persistent-supportability-store-and-lineage-apis.md` |
| RFC-0024 | Unified PostgreSQL Persistence for DPM and Advisory | COMPLETED (SLICE 19) | RFC-0014G, RFC-0017, RFC-0018, RFC-0019, RFC-0020, RFC-0023 | `docs/rfcs/RFC-0024-unified-postgresql-persistence-for-dpm-and-advisory.md` |
| RFC-0025 | PostgreSQL-Only Production Mode Cutover | COMPLETED | RFC-0023, RFC-0024 | `docs/rfcs/RFC-0025-postgres-only-production-mode-cutover.md` |
| RFC-0027 | Advisory Proposal Workflow Coverage Hardening (Approval Chain Paths) | IMPLEMENTED | RFC-0014G, RFC-0024 | `docs/rfcs/RFC-0027-advisory-proposal-workflow-coverage-hardening.md` |
| RFC-0028 | DPM Integration Capabilities Contract | IMPLEMENTED | RFC-0021, RFC-0022, RFC-0027 | `docs/rfcs/RFC-0028-dpm-integration-capabilities-contract.md` |
| RFC-0029 | Iterative Proposal Simulation Workspace Contract for Advisory and DPM Lifecycles | PROPOSED | RFC-0020, RFC-0021, RFC-0028 | `docs/rfcs/RFC-0029-iterative-proposal-simulation-workspace-contract.md` |
| RFC-0030 | DPM Integration Pyramid Rebalance Wave 1 | IMPLEMENTED | RFC-0023, RFC-0024, RFC-0028 | `docs/rfcs/RFC-0030-dpm-integration-pyramid-rebalance-wave-1.md` |
| RFC-0031 | DPM Integration Pyramid Wave 2 (Supportability and Guardrails) | IMPLEMENTED | RFC-0030 | `docs/rfcs/RFC-0031-dpm-integration-pyramid-wave-2-supportability-and-guardrails.md` |
| RFC-0032 | DPM Pyramid Wave 3 (Integration and E2E Workflow Expansion) | IMPLEMENTED | RFC-0031 | `docs/rfcs/RFC-0032-dpm-pyramid-wave-3-integration-and-e2e-workflow-expansion.md` |
| RFC-0033 | DPM Pyramid Wave 4 (Integration and E2E Expansion) | IMPLEMENTED | RFC-0032 | `docs/rfcs/RFC-0033-dpm-pyramid-wave-4-integration-e2e-expansion.md` |
| RFC-0034 | DPM Pyramid Wave 5 (Integration Boundary Expansion) | IMPLEMENTED | RFC-0033 | `docs/rfcs/RFC-0034-dpm-pyramid-wave-5-integration-boundary-expansion.md` |
| RFC-0035 | DPM Pyramid Wave 6 (Repository Integration Depth Expansion) | PROPOSED | RFC-0034 | `docs/rfcs/RFC-0035-dpm-pyramid-wave-6-repository-integration-depth-expansion.md` |
| RFC-0036 | PostgreSQL-Only Runtime Hard Cutover | PROPOSED | RFC-0025, RFC-0024 | `docs/rfcs/RFC-0036-postgres-only-runtime-hard-cutover.md` |

