# Overview

## Business role

`lotus-manage` owns discretionary portfolio-management execution and management-side workflow
supportability. It turns governed portfolio inputs into deterministic rebalance decisions,
supportability evidence, and operational workflow state.

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
- remaining advisory/proposal routes treated as compatibility or cleanup surfaces under RFC-0082
