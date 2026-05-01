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
- stateless execution is the implemented and advertised runtime mode
- stateful `portfolio_id` execution is modeled behind guardrails, but not promoted until
  `lotus-core` exposes a certified DPM execution-context source-data contract

```mermaid
flowchart LR
    PM[Portfolio manager or ops user] --> Gateway[lotus-gateway]
    Gateway --> Manage[lotus-manage]
    Manage --> Decision[Rebalance decision: READY, PENDING_REVIEW, or BLOCKED]
    Manage --> Evidence[Run artifact, lineage, idempotency, workflow, metrics]
    Core[lotus-core] -. future certified DPM execution context .-> Manage
    Advise[lotus-advise] -. advisor-led proposal workflows .-> Gateway
```

## Current Proof Posture

Current branch code has strengthened API, OpenAPI, mesh, and observability validation. A direct
canonical-host manage API proof on 2026-05-02 showed business execution probes passing, but also
found the running canonical `lotus-manage` container was stale relative to the branch OpenAPI
certification changes. Final proof requires refreshing the running image and rerunning
`scripts/validate_live_api.py --base-url http://manage.dev.lotus` to 0 failures.
