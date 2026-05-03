# RFC Index

Standards for all current and future RFCs:
- `docs/rfcs/RFC-CONVENTIONS.md`

Governance boundary:
- Service-specific implementation RFCs belong in this repository.
- Cross-cutting platform and multi-service RFCs belong in `https://github.com/sgajbi/lotus-platform`.
- Advisor-led proposal simulation, artifact, consent, and lifecycle RFCs are no longer active
  `lotus-manage` scope after the `lotus-advise` split. Current advisory proposal design belongs
  in `lotus-advise`.

| RFC | Title | Status | Depends On | File |
| --- | --- | --- | --- | --- |
| RFC-0001 | Enterprise Rebalance Simulation MVP (lotus-manage Platform) | IMPLEMENTED | - | `docs/rfcs/RFC-0001-rebalance-simulation-mvp.md` |
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
| RFC-0016 | lotus-manage Idempotency Replay Contract for `/rebalance/simulate` | IMPLEMENTED | RFC-0001, RFC-0002, RFC-0007A | `docs/rfcs/RFC-0016-dpm-idempotency-replay-contract.md` |
| RFC-0017 | lotus-manage Run Supportability APIs (Run, Correlation, Idempotency Lookup) | IMPLEMENTED | RFC-0001, RFC-0002, RFC-0016 | `docs/rfcs/RFC-0017-dpm-run-supportability-apis.md` |
| RFC-0018 | lotus-manage Async Operations Resource | IMPLEMENTED | RFC-0013, RFC-0016, RFC-0017 | `docs/rfcs/RFC-0018-dpm-async-operations-resource.md` |
| RFC-0019 | lotus-manage Deterministic Run Artifact Contract | IMPLEMENTED (PHASE 1 - DERIVED ARTIFACT) | RFC-0003, RFC-0013, RFC-0017 | `docs/rfcs/RFC-0019-dpm-deterministic-run-artifact-contract.md` |
| RFC-0020 | lotus-manage Workflow Gate API and Persistence | IMPLEMENTED | RFC-0017, RFC-0019 | `docs/rfcs/RFC-0020-dpm-workflow-gate-api-and-persistence.md` |
| RFC-0021 | lotus-manage OpenAPI Contract Hardening and Separation of Request/Response Models | IMPLEMENTED | RFC-0007A, RFC-0016, RFC-0017 | `docs/rfcs/RFC-0021-dpm-openapi-contract-hardening.md` |
| RFC-0022 | lotus-manage Policy Pack Configuration Model | IMPLEMENTED | RFC-0008, RFC-0010, RFC-0011, RFC-0016 | `docs/rfcs/RFC-0022-dpm-policy-pack-configuration-model.md` |
| RFC-0023 | lotus-manage Persistent Supportability Store and Lineage APIs | IMPLEMENTED | RFC-0017, RFC-0018, RFC-0019 | `docs/rfcs/RFC-0023-dpm-persistent-supportability-store-and-lineage-apis.md` |
| RFC-0024 | PostgreSQL Persistence for lotus-manage Supportability | COMPLETED, ADVISORY PORTION SUPERSEDED BY SPLIT | RFC-0017, RFC-0018, RFC-0019, RFC-0020, RFC-0023 | `docs/rfcs/RFC-0024-unified-postgresql-persistence-for-dpm-and-advisory.md` |
| RFC-0025 | PostgreSQL-Only Production Mode Cutover | COMPLETED, ADVISORY PORTION SUPERSEDED BY SPLIT | RFC-0023, RFC-0024 | `docs/rfcs/RFC-0025-postgres-only-production-mode-cutover.md` |
| RFC-0028 | lotus-manage Integration Capabilities Contract | IMPLEMENTED | RFC-0021, RFC-0022 | `docs/rfcs/RFC-0028-dpm-integration-capabilities-contract.md` |
| RFC-0036 | lotus-manage Stateful Core Sourcing And Endpoint Consolidation | IMPLEMENTED | RFC-0013, RFC-0016, RFC-0017, RFC-0018, RFC-0021, RFC-0022, RFC-0023, RFC-0028 | `docs/rfcs/RFC-0036-dpm-stateful-core-sourcing-and-endpoint-consolidation.md` |

