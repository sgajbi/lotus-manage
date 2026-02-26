# RFC-0029: Iterative Proposal Simulation Workspace Contract for Advisory and DPM Lifecycles

- Status: PROPOSED
- Date: 2026-02-24
- Owners: DPM Rebalance Engine

## Problem Statement

Advisors and DPM users need an iterative build-refine-evaluate loop that supports repeated trade/cash adjustments with immediate constraint and portfolio impact feedback. Current workflow APIs are closer to run submission than interactive workspace collaboration.

## Root Cause

- Existing contracts emphasize simulation runs and lifecycle transitions, not iterative workspace state.
- No dedicated delta-based contract for interactive proposal editing.
- Constraint/suitability/SAA feedback is not normalized for per-iteration UI panels.

## Proposed Solution

1. Introduce iterative proposal workspace contracts:
   - draft workspace session
   - add/update/remove delta actions (trades, sells, cash moves)
   - evaluate current draft against policy/suitability/risk constraints
2. Return normalized impact and violation model optimized for UI guidance.
3. Preserve current proposal lifecycle APIs for formal progression to approval/execution.

## Architectural Impact

- DPM supports both interactive iteration and formal lifecycle progression.
- Better alignment with advisory domain behavior expected by private banking users.
- Requires stronger idempotency and deterministic draft-state replay.

## Risks and Trade-offs

- Session/state complexity increases in DPM API model.
- Must carefully distinguish advisory-specific behavior vs DPM automation behavior.
- Additional persistence and audit requirements for draft iteration history.

## High-Level Implementation Approach

1. Define draft session schema and mutation endpoints.
2. Add normalized constraint/impact response contract.
3. Add replay-safe persistence strategy for draft iterations.
4. Add end-to-end tests with BFF and UI iterative loops.

## Dependencies

- Consumed by AEA RFC-0010 and AW RFC-0007.
- Integrates with PAS RFC-046 and PA RFC-032 for data and analytics feedback.
