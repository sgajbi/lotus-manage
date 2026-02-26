# Project Overview

This document explains the system at a high level for three audiences:
- business stakeholders,
- business analysts (BAs),
- developers.

## What This Platform Does

The platform provides deterministic portfolio decisioning APIs for:
- **DPM rebalancing** (model-driven discretionary portfolio management),
- **Advisory proposals** (advisor-entered cash flows and manual trades).

Architecture authority:
- Platform-wide integration and architecture standards are maintained centrally in `https://github.com/sgajbi/lotus-platform`.
- This repository documents service-local implementation details and service-specific RFCs only.

Both flows produce structured, auditable outputs with:
- before/after portfolio states,
- intent-level actions,
- rules and diagnostics,
- lineage identifiers and deterministic hashes.

## Why It Matters

For business and control functions, the platform is built for:
- reproducibility,
- explainability,
- policy-based controls,
- workflow readiness.

Domain outcomes are returned as:
- `READY`
- `PENDING_REVIEW`
- `BLOCKED`

The API remains deterministic for identical inputs and options.

## Core Business Flows

1. DPM flow
- Input: portfolio snapshot, market snapshot, model targets, shelf, options.
- Output: optimized rebalance intents with controls (tax, turnover, settlement, constraints).

2. Advisory flow
- Input: portfolio snapshot, market snapshot, shelf, advisor cash/trade proposals, options.
- Output: proposal simulation plus optional artifact package for client/reviewer workflow.

3. Workflow semantics (shared)
- Gate decisions provide deterministic next-step semantics:
  - blocked,
  - risk review,
  - compliance review,
  - client consent,
  - execution ready.

## API Surface

- `POST /rebalance/simulate`
- `POST /rebalance/analyze`
- `POST /rebalance/proposals/simulate`
- `POST /rebalance/proposals/artifact`

## Architecture Summary

- `src/api/`: FastAPI contracts and endpoint orchestration.
- `src/core/dpm/`: DPM-specific engine modules.
- `src/core/advisory/`: Advisory-specific modules (artifact, funding, intents, ids).
- `src/core/common/`: Shared logic (simulation primitives, diagnostics, drift, suitability, canonical hashing, workflow gates).
- `src/core/models.py`: shared request/response contracts and options.

## Test Strategy

Tests are organized by responsibility:
- `tests/unit/dpm/`: DPM API, engine, and DPM golden tests.
- `tests/unit/advisory/`: advisory API, engine, contracts, and advisory golden tests.
- `tests/unit/shared/`: shared contracts/compliance/dependencies tests.
- `tests/e2e/`: end-to-end workflow/demo scenario tests.
- `tests/shared/`: shared test helpers (factories/assertions).

Golden fixtures are split by domain:
- `tests/unit/dpm/golden_data/`
- `tests/unit/advisory/golden_data/`

CI test execution model:
- runs `tests/unit`, `tests/integration`, and `tests/e2e` in parallel matrix jobs,
- combines per-suite coverage artifacts,
- enforces a single repository-wide `99%` coverage gate.

## Governance and RFCs

- RFCs under `docs/rfcs/` define scope and acceptance.
- Advisory refinement RFCs are under:
  - `docs/rfcs/advisory pack/refine/`
- Current implementation status is tracked in RFC metadata (`Status`, `Implemented In`).

## Current Delivery Principle

Keep DPM and advisory behavior separated by business logic, while sharing:
- vocabulary,
- control semantics,
- deterministic primitives,
- test and audit standards.

