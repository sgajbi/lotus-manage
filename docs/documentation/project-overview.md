# Project Overview

This document explains `lotus-manage` at a high level for:

- business stakeholders,
- business analysts,
- engineers,
- operators.

It is intentionally deeper than the repo `README.md`, but it should still stay summary-oriented.
Detailed engine mechanics, RFC decisions, and operational procedures belong in their own focused
documents.

## What This Service Does

`lotus-manage` provides deterministic management-side portfolio workflow APIs for:

- discretionary rebalance simulation,
- multi-scenario what-if analysis,
- policy-pack-aware workflow gating,
- async execution and polling,
- run supportability, lineage, artifacts, and idempotency lookup.

Platform-wide architecture authority remains in `lotus-platform`. This repository documents
service-local behavior and service-specific RFCs only.

## Why It Matters

For business and control functions, `lotus-manage` is built for:

- reproducibility,
- explainability,
- policy-based controls,
- supportability,
- execution readiness.

Domain outcomes remain explicit rather than inferred:

- `READY`
- `PENDING_REVIEW`
- `BLOCKED`

## Core Business Flows

### 1. Rebalance simulation

Input:

- governed portfolio state,
- market inputs,
- model targets,
- shelf constraints,
- policy options.

Output:

- deterministic rebalance intents,
- diagnostics and workflow posture,
- before and after portfolio states,
- lineage identifiers and supportability evidence.

### 2. What-if and async execution support

Input:

- rebalance scenarios or analysis requests,
- execution mode and correlation context.

Output:

- synchronous analysis or async acceptance,
- durable operation lookup,
- run artifacts and lineage references,
- supportability summaries for investigation workflows.

### 3. Capability and policy supportability

Input:

- tenant or consumer capability queries,
- policy or workflow supportability lookups.

Output:

- backend-owned capability posture,
- policy-pack supportability summaries,
- workflow-gate visibility for downstream consumers.

## Current Boundary Posture

`lotus-manage` is the management-side service after the split from `lotus-advise`.

That means:

- management-side execution and supportability stay here,
- advisor-led proposal ownership stays in `lotus-advise`,
- `lotus-core` remains source-data authority for core-referenced portfolio, market-data, price,
  and FX inputs.

Some advisory proposal routes still remain in this repository as compatibility surfaces during
cleanup. They should not be treated as a mandate to grow new advisory scope here.

For compatibility-surface details, use:

- `docs/documentation/engine-know-how-advisory.md`

## API Surface Summary

Primary management surfaces:

- `POST /rebalance/simulate`
- `POST /rebalance/analyze`
- `POST /rebalance/analyze/async`
- `/rebalance/runs/*`
- `/rebalance/operations/*`
- `/rebalance/lineage/*`
- `/rebalance/idempotency/*`
- `/rebalance/policies/*`
- `/integration/capabilities`
- `/platform/capabilities`

For grouped route documentation, use the repo wiki and router-level docs rather than extending this
overview into an endpoint catalog.

## Architecture Summary

Key module areas:

- `src/api/`
  FastAPI contracts, readiness, observability, and endpoint orchestration
- `src/core/dpm/`
  rebalance engine and management-side simulation logic
- `src/core/dpm_runs/`
  async operation, workflow, artifact, and supportability services
- `src/core/proposals/`
  compatibility proposal-lifecycle modules still present after the split
- `src/infrastructure/`
  PostgreSQL migrations, repository backends, and policy-pack persistence

## Document Map

Use the focused documents for detail:

- management engine detail:
  `docs/documentation/engine-know-how-dpm.md`
- compatibility advisory surface detail:
  `docs/documentation/engine-know-how-advisory.md`
- migration rollout:
  `docs/documentation/postgres-migration-rollout-runbook.md`
- service operations:
  `docs/runbooks/service-operations.md`
- RFC index:
  `docs/rfcs/README.md`
