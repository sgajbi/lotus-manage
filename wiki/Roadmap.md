# Roadmap

## Direction

`lotus-manage` is being rebuilt as the discretionary mandate portfolio-management operating system
for Lotus. The goal is not to preserve the old API shape. The goal is a clean, certified,
enterprise-grade DPM service that can support portfolio managers, CIO offices, compliance,
operations, sales, and client-demo teams with implementation-backed evidence.

Current implementation-backed posture:

1. management-side rebalance execution and what-if analysis are supported,
2. run supportability, artifacts, lineage, idempotency, workflow gates, policy packs, and
   PostgreSQL-backed operational evidence are supported or feature-gated as documented in
   [Supported Features](Supported-Features),
3. stateful `portfolio_id` execution is implemented behind explicit runtime gates and composes
   governed `lotus-core` RFC-087 source products when the canonical core/manage stack is configured,
4. advisory proposal workflows remain outside this repository and belong to `lotus-advise`.
5. RFC-0038 has delivered the first implementation-backed DPM operating-system foundation:
   mandate digital-twin, health-engine, repository, migration, mandate refresh/read/version/diff
   APIs, standalone health APIs, bounded monitoring/exception APIs, and a bounded command-center
   summary API with local manage and live core/manage proof.
6. RFC-0039 has delivered the manage-side construction-alternative foundation with first-wave
   generate/read/select APIs, Postgres-backed proof, and Gateway/Workbench realization requirements
   for the later product-surface journey.

Strategic posture:

1. no production downstream dependency is assumed for the target RFC-0037 through RFC-0043 surfaces,
2. duplicate, advisory-era, poorly named, or misleading manage endpoints may be deleted rather than
   kept for backward compatibility,
3. future gateway and Workbench integration should be rebuilt against the certified target contract,
4. every feature must improve enterprise posture through better source authority, auditability,
   observability, supportability, tests, and documentation.

## Strategic Roadmap

```mermaid
flowchart TD
    Foundation[RFC-0038<br/>Mandate digital twin, health score, command center]
    Construction[RFC-0039<br/>Advanced construction and rebalance alternatives]
    Evidence[RFC-0040<br/>Pre-trade proof pack and decision timeline]
    Waves[RFC-0041<br/>CIO model-change impact and rebalance waves]
    Feedback[RFC-0042<br/>Post-trade outcome feedback]
    Copilot[RFC-0043<br/>Governed AI PM copilot]
    Crown[RFC-0037<br/>DPM operating system]

    Foundation --> Construction
    Construction --> Evidence
    Evidence --> Waves
    Waves --> Feedback
    Evidence --> Copilot
    Feedback --> Crown
    Copilot --> Crown
```

| RFC | Business outcome | Enterprise posture raised by |
| --- | --- | --- |
| RFC-0038 | PMs see mandate state, health, exceptions, and book attention queues. | Source-lineage-backed mandate twin, deterministic scoring, certified command-center APIs. |
| RFC-0039 | PMs compare construction alternatives with visible risk, tax, liquidity, FX, regime-stress, and cost trade-offs. | Manage backend foundation is implementation-backed for first-wave methods, mandatory authority-backed advanced methods, objective/constraint traces, solver/fallback supportability posture, `lotus-risk` concentration authority integration, certified alternative APIs, Postgres proof, explicit ESG/restriction deferral, and downstream Gateway/Workbench realization requirements. Full product-outcome claims wait for downstream implementation and live proof. |
| RFC-0040 | PMs, compliance, operations, CIO, and audit can inspect one pre-trade evidence artifact. | Manage-owned durable proof-pack JSON, Markdown summary, report-input and AI-evidence input contracts, lineage and retention posture, Gateway/Workbench realization RFC alignment, and canonical Postgres-backed live proof. Full front-office product support waits for downstream Gateway/Workbench/report/AI implementation. |
| RFC-0041 | CIO and PM teams can orchestrate book-level model-change and rebalance waves. | Implementation is complete through Slice 9: source-map, platform scaffold evidence improvement, cleanup review, wave domain contracts, persistence foundation, explicit affected-portfolio preview, idempotent durable create, durable source-check classification, RFC-0039-backed simulation for ready items with real construction inputs, item-level alternative selection, RFC-0040 proof-pack linkage, approval, staging, internal operations handoff evidence with no external execution claim, product-safe wave supportability/observability diagnostics, and downstream Gateway/Workbench RFC-0098 wave realization addenda. First-wave scope remains explicit portfolio-list waves; automatic PM-book and CIO model-change cohort discovery remain deferred until source-owning products are proven. Support remains proposed until live proof and supported-feature promotion are complete. |
| RFC-0042 | PMs learn from expected-versus-realized outcomes after execution. | Source-authoritative realized evidence, variance decomposition, searchable outcome memory. |
| RFC-0043 | AI assists PM productivity without owning investment truth. | Structured evidence input, forbidden-action guardrails, no-sensitive telemetry, AI-unavailable fallback. |

## Business Value Themes

1. scale PM capacity through exception-based monitoring and wave orchestration,
2. improve investment discipline through mandate, policy, CIO, risk, tax, liquidity, currency, and
   ESG controls,
3. improve trust through proof packs, lineage, decision timelines, and outcome reviews,
4. strengthen sales and demo material through implementation-backed DPM stories,
5. raise Lotus ecosystem value by orchestrating `lotus-core`, `lotus-risk`, `lotus-performance`,
   `lotus-report`, `lotus-ai`, `lotus-gateway`, and `lotus-workbench`.

## Non-Negotiable Delivery Rules

1. target-state features remain `Proposed` until live evidence proves them,
2. OpenAPI must explain what each endpoint is for, when to use it, how to call it, and every
   request/response/error field,
3. every endpoint must expose source-readiness and degraded states rather than hiding missing data,
4. every implementation must satisfy data-mesh, structured logging, metrics, health, readiness,
   audit, and supportability standards,
5. documentation is part of the product and must serve business, engineering, sales, marketing,
   operations, and client-demo preparation.

## RFC-0038 Current Implementation Progress

```mermaid
flowchart LR
    FieldMap[Source-data field map] --> Twin[Pure mandate digital twin]
    Twin --> Health[Pure mandate health engine]
    Health --> Exceptions[Derived monitoring exceptions]
    Exceptions --> Persistence[Repository and Postgres migration foundation]
    Persistence --> APIs[Mandate refresh, read, version, diff APIs]
    APIs --> HealthApis[Standalone health and monitoring APIs]
    HealthApis --> Command[DPM command center]
```

The first RFC-0038 implementation wave establishes source-mapped domain primitives, a deterministic
health engine, repository contracts, in-memory persistence, a Postgres repository foundation, and a
Postgres migration. Slice 3 adds the first certified mandate API foundation for refreshing a twin
from product-specific `lotus-core` source products and reading versioned mandate state. Slice 4
adds standalone health read/recalculate plus bounded monitoring run and exception APIs. Slice 5 adds
bounded command-center aggregation over persisted monitoring runs and active exceptions. Local
manage proof and local canonical manage plus live `lotus-core` proof passed; Gateway/Workbench
product-surface integration remains downstream handoff work.
