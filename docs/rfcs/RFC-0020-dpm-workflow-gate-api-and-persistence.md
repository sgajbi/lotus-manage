# RFC-0020: lotus-manage Workflow Gate API and Persistence

| Metadata | Details |
| --- | --- |
| **Status** | IMPLEMENTED |
| **Created** | 2026-02-20 |
| **Completed** | 2026-02-20 |
| **Depends On** | RFC-0017, RFC-0019 |
| **Doc Location** | `docs/rfcs/RFC-0020-dpm-workflow-gate-api-and-persistence.md` |

## 1. Executive Summary

Add workflow gate APIs and persistence for lotus-manage runs to support reviewer-assigned actions (approve, reject, request changes) with full auditability, aligned with advisory workflow lifecycle patterns.

## 2. Problem Statement

lotus-manage exposes run diagnostics but lacks explicit workflow gate state transitions and reviewer decision records. Operations teams currently need external tooling for gating and traceability.

## 3. Goals and Non-Goals

### 3.1 Goals

- Add first-class workflow gate state for runs.
- Persist decisions, timestamps, actor identity, and reason codes.
- Keep gating feature-toggleable for different operating models.

### 3.2 Non-Goals

- Build a full entitlement system in this RFC.
- Couple decision logic to execution scheduling.

## 4. Proposed Design

### 4.1 API Surface

- `GET /rebalance/runs/{run_id}/workflow`
- `GET /rebalance/runs/by-correlation/{correlation_id}/workflow`
- `GET /rebalance/runs/idempotency/{idempotency_key}/workflow`
- `POST /rebalance/runs/{run_id}/workflow/actions`
- `POST /rebalance/runs/by-correlation/{correlation_id}/workflow/actions`
- `POST /rebalance/runs/idempotency/{idempotency_key}/workflow/actions`
  - Action types: `APPROVE`, `REJECT`, `REQUEST_CHANGES`
- `GET /rebalance/runs/{run_id}/workflow/history`
- `GET /rebalance/runs/by-correlation/{correlation_id}/workflow/history`
- `GET /rebalance/runs/idempotency/{idempotency_key}/workflow/history`
- `GET /rebalance/workflow/decisions`
- `GET /rebalance/workflow/decisions/by-correlation/{correlation_id}`
  - filtered supportability listing across runs:
    - `rebalance_run_id`
    - `action`
    - `actor_id`
    - `reason_code`
    - `from`
    - `to`
    - `limit`
    - `cursor`

### 4.2 Domain Model

- `workflow_status`: `NOT_REQUIRED | PENDING_REVIEW | APPROVED | REJECTED`
- Decision record fields:
  - `decision_id`
  - `run_id`
  - `action`
  - `reason_code`
  - `comment`
  - `actor_id`
  - `decided_at`
  - `correlation_id`

### 4.3 Configurability

- `DPM_WORKFLOW_ENABLED` (default `false`)
- `DPM_WORKFLOW_REQUIRES_REVIEW_FOR_STATUSES` (configurable list)

## 5. Test Plan

- Workflow disabled behavior.
- Approve/reject/request-changes happy paths.
- Invalid transitions.
- History retrieval and ordering.

## 6. Rollout/Compatibility

Additive APIs and storage. When disabled, existing run semantics and responses remain unchanged.

## 7. Status and Reason Code Conventions

- Existing run business status remains `READY`, `PENDING_REVIEW`, `BLOCKED`.
- Workflow status is separate and does not replace run status.
- Reason codes use uppercase snake case.

## 8. Implementation Status

- Implemented:
  - `GET /rebalance/runs/{run_id}/workflow`
  - `GET /rebalance/runs/by-correlation/{correlation_id}/workflow`
  - `GET /rebalance/runs/idempotency/{idempotency_key}/workflow`
  - `POST /rebalance/runs/{run_id}/workflow/actions`
  - `POST /rebalance/runs/by-correlation/{correlation_id}/workflow/actions`
  - `POST /rebalance/runs/idempotency/{idempotency_key}/workflow/actions`
  - `GET /rebalance/runs/{run_id}/workflow/history`
  - `GET /rebalance/runs/by-correlation/{correlation_id}/workflow/history`
  - `GET /rebalance/runs/idempotency/{idempotency_key}/workflow/history`
  - `GET /rebalance/workflow/decisions`
  - `GET /rebalance/workflow/decisions/by-correlation/{correlation_id}`
  - Feature flags:
    - `DPM_WORKFLOW_ENABLED` (default `false`)
    - `DPM_WORKFLOW_REQUIRES_REVIEW_FOR_STATUSES` (CSV, default `PENDING_REVIEW`)
  - Persistence backends:
    - in-memory
    - SQLite
- Follow-up Scope (out of RFC-0020):
  - Managed enterprise database profile integration is tracked by RFC-0023 and RFC-0024.
