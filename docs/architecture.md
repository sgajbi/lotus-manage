# Lotus Manage Architecture

`lotus-manage` is a Domain API in the Lotus stack for discretionary portfolio management execution and
pre-trade operating workflows.

## Primary responsibilities

- Build and persist rebalance construction alternatives and deterministic metadata.
- Run supportability pipelines for async operations, lineage, proof-pack handoff, and idempotent reruns.
- Persist and expose command-center signals used by downstream workflow surfaces.
- Mediate governed source-context intake from `lotus-core`, `lotus-risk`, and `lotus-performance` without
  adopting those domains’ modeling or execution responsibilities.
- Expose bounded governance boundaries for unsupported capabilities such as OMS, client communication,
  and portfolio-level advisory actions.

## Domain and layering

- `src/api` owns router and request/response surfaces.
- `src/core` owns business logic and domain rules.
- `src/api/services` owns orchestration, assembly, and integration use-cases.
- `src/infrastructure` owns concrete adapter implementations and storage/network clients.
- `tests` contains unit, integration, and contract verification aligned to architecture contracts.

## Governance invariants

- Routers do not import concrete infra clients.
- Services do not import router modules.
- Domain and persistence details do not leak into API request contract helpers.
- OpenAPI and API vocabulary checks remain mandatory in every PR lane.

## Current truth pointers

- Ledger: [docs/architecture/CODEBASE-REVIEW-LEDGER.md](architecture/CODEBASE-REVIEW-LEDGER.md)
- Standards: [docs/standards/enterprise-readiness.md](standards/enterprise-readiness.md)
- Standards map: [docs/standards/RFC-0082-upstream-contract-family-map.md](standards/RFC-0082-upstream-contract-family-map.md)
- Open RFC and contract context: [docs/rfcs](rfcs)
