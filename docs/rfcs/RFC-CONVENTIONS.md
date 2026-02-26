# RFC Conventions

This document defines the required language and contract conventions for all RFCs in `docs/rfcs`.

## 1. Source of Truth

1. Implemented behavior must match code in `src/`.
2. For implemented RFCs, document current reality first, then pending deltas.
3. Future RFCs must extend existing contracts unless explicitly marked as a breaking change RFC.

## 2. Canonical API Conventions

1. Canonical simulate endpoint is `POST /rebalance/simulate`.
2. Do not introduce `/v1/rebalance/simulate` unless a dedicated versioning RFC is approved and all clients/tests are migrated together.
3. Batch/analysis endpoints should follow the same route family style (`/rebalance/...`).
4. Domain outcomes for valid payloads are represented in response `status`, not as separate HTTP domain error contracts.

## 3. Status Vocabulary

Use only:
1. `READY`
2. `PENDING_REVIEW`
3. `BLOCKED`

Do not invent alternatives like `READY_WITH_WARNINGS` or `PARTIAL_REBALANCE` as top-level run statuses. Use diagnostics warnings/reason codes instead.

## 4. Intent and Model Naming

1. Intent types use discriminated names:
   1. `SECURITY_TRADE`
   2. `FX_SPOT`
2. Rule IDs and reason codes use upper snake case.
3. New models/fields should align naming with existing `src/core/models.py` patterns.
4. If a new RFC proposes field renames, include a migration and compatibility section.

## 5. Safety and Compliance Baseline

All future RFCs must preserve and explicitly acknowledge:
1. No-shorting safeguard (`NO_SHORTING` / `SELL_EXCEEDS_HOLDINGS`).
2. Cash sufficiency safeguard (`INSUFFICIENT_CASH`).
3. Reconciliation block on mismatch.
4. Existing rule engine flow and status escalation semantics.

## 6. File Naming Convention

Use:
1. `RFC-XXXX-topic-in-lowercase-kebab.md`
2. Suffix letters allowed for branch RFCs (for example `RFC-0006A-...`).

Titles can be human-readable; filenames should remain machine-friendly and stable.

## 7. RFC Structure Convention

Each RFC should include:
1. Metadata (`Status`, `Created`, `Depends On`, optional `Doc Location`).
2. Executive Summary.
3. Problem Statement.
4. Goals and Non-Goals.
5. Proposed Design.
6. Test Plan.
7. Rollout/Compatibility.
8. Status/Reason code conventions (if introducing new diagnostics).

## 8. Dependency and Extension Rule

1. New RFCs must state which previous RFCs they extend.
2. If there is pending work in implemented RFCs that is required for correctness, add a carry-forward section.
3. Cross-RFC conflicts must be resolved in the newer RFC text explicitly.
