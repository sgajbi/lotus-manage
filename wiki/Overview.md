# Overview

## Business role

`lotus-manage` owns discretionary mandate portfolio-management execution, management-side workflow
review, and operational supportability. It turns governed portfolio inputs into deterministic
rebalance decisions, supportability evidence, policy controls, and operational workflow state.

In business terms, `lotus-manage` is the execution-control service for mandate portfolio managers
and operations teams. It answers: "given the governed portfolio context and mandate policy, what
rebalance action is allowed, what evidence supports that decision, and what operational review is
required before execution?"

## Ownership boundaries

This repo owns:

1. rebalance simulation and what-if analysis
2. async operation execution and run lookup
3. policy-pack resolution and workflow-gate supportability
4. run artifacts, lineage, idempotency, and management-side lifecycle support

This repo does not own:

1. advisor-led proposal workflows, which belong to `lotus-advise`
2. canonical portfolio state and source-data truth, which belong to `lotus-core`
3. risk methodology or performance analytics authority, which belong to `lotus-risk` and
   `lotus-performance`

## Current posture

- management-side service after the `lotus-advise` split
- canonical host runtime on port `8001` so both services can coexist locally
- explicit no-alias, OpenAPI, vocabulary, migration, and security governance in CI
- proposal simulation, artifacts, consent, and lifecycle routes are owned by `lotus-advise`
- stateless execution is the default implemented and advertised runtime mode
- stateful `portfolio_id` execution is implemented behind explicit runtime gates and promoted only
  when the canonical core/manage configuration proves RFC-087 source-product readiness

```mermaid
flowchart LR
    PM[Portfolio manager or ops user] --> Gateway[lotus-gateway]
    Gateway --> Manage[lotus-manage]
    Manage --> Decision[Rebalance decision: READY, PENDING_REVIEW, or BLOCKED]
    Manage --> Evidence[Run artifact, lineage, idempotency, workflow, metrics]
    Core[lotus-core] -->|RFC-087 DPM source products| Manage
    Advise[lotus-advise] -. advisor-led proposal workflows .-> Gateway
```

## Target Strategic Role

RFC-0037 through RFC-0043 define the proposed revamp from a certified rebalance/supportability
service into a discretionary mandate portfolio-management operating system.

The target operating model adds mandate digital twins, health scoring, portfolio-manager command
center, advanced construction alternatives, pre-trade proof packs and decision timeline, CIO
model-change and rebalance waves, post-trade outcome feedback, and governed AI PM support.

RFC-0038 has implemented and live-proven the backend mandate digital-twin, health-score,
monitoring, and bounded command-center foundation. Later roadmap features remain proposed until
implementation and live evidence prove them. Target-state work may replace older manage APIs rather
than preserving backward compatibility because there is no assumed production downstream dependency
for the revamp surface.

## Current Proof Posture

Current code has strengthened API, OpenAPI, mesh, observability, mandate health, command-center,
and live core-sourcing validation. The RFC-0036 proof path passed direct canonical-host manage API
proof against `http://manage.dev.lotus`, `http://core-control.dev.lotus`, and
`http://core-query.dev.lotus`. RFC-0038 additionally passed local manage proof and local canonical
manage plus live `lotus-core` proof for the mandate/monitoring/command-center backend foundation.

That proof covers the implemented stateless API surface and the explicitly gated stateful
`portfolio_id` path. Stateful mode composes RFC-087 `lotus-core` source products and publishes
`stateful` capability truth only when the stateful capability flag, stateful core-sourcing flag,
and core base URL are configured.
