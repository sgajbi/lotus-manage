# RFC Index

## Platform RFCs that matter most here

- RFC-0066
- RFC-0067
- RFC-0071
- RFC-0072
- RFC-0073
- RFC-0082

## High-value local RFCs

- RFC-0001 to RFC-0013
  core rebalance simulation, controls, optimization, and what-if analysis foundation
- RFC-0002
  implemented enterprise hardening baseline; durable idempotency and persistence are now delivered
  by later supportability RFCs rather than deferred work
- RFC-0007A
  implemented contract-tightening baseline for the canonical rebalance execution surface
- RFC-0016
  idempotency replay contract
- RFC-0017
  run supportability APIs
- RFC-0018
  async operations resource
- RFC-0019
  deterministic run artifact contract
- RFC-0020
  workflow gate API and persistence
- RFC-0021
  OpenAPI hardening, request/response model separation, and current certification evidence
- RFC-0022
  policy-pack configuration model
- RFC-0023
  persistent supportability store and lineage APIs
- RFC-0028
  implemented `GET /api/v1/integration/capabilities` backend-governed capabilities contract

## Active And Recently Completed RFCs

- RFC-0036
  implemented target-state stateful `lotus-core` sourcing and duplicate endpoint consolidation

## Strategic Target-State RFCs

- RFC-0037
  proposed DPM operating-system and mandate-intelligence roadmap intended to make
  `lotus-manage` the management-side crown jewel of the Lotus ecosystem
- RFC-0038
  proposed first implementation foundation for mandate digital twins, mandate health scoring,
  monitoring exceptions, and the DPM command-center API

## Removed local RFC sprawl

- RFC-0030 through RFC-0035 were deleted from the active repository documentation set. They were
  incremental test-pyramid expansion waves whose implemented test coverage is now represented by
  the current test suite and RFC-0036 evidence rather than six separate active RFC records.

## Superseded advisory scope

- Advisor-led proposal simulation, artifacts, consent, and lifecycle RFCs are no longer active
  `lotus-manage` scope. They belong in `lotus-advise`.

## Rebaselined foundation RFCs

- RFC-0002, RFC-0007A, RFC-0021, RFC-0024, RFC-0025, and RFC-0028 were reviewed against current
  implementation evidence on 2026-05-03.
- RFC-0024 and RFC-0025 are complete for current lotus-manage DPM supportability and production
  cutover scope. Historical advisory migration notes remain in the RFC files for audit traceability
  only.

## Full local RFC inventory

- [docs/rfcs/README.md](../docs/rfcs/README.md)
