# ADR-0009: PostgreSQL as Target Persistence Backend for lotus-manage

## Status

Accepted, narrowed after the `lotus-advise` split.

## Context

lotus-manage workflows require durable, auditable, and scalable persistence for production
operations. Current adapters are useful for local development and incremental delivery but are not
the long-term production target.

## Decision

Set PostgreSQL as the target production persistence backend for lotus-manage domains:

- lotus-manage supportability and lineage storage
- lotus-manage workflow, idempotency, operation, artifact, and policy-pack storage

Keep in-memory (and optionally SQLite) adapters for local and test profiles behind backend configuration flags.

## Consequences

- Unified enterprise persistence strategy across lotus-manage supportability surfaces.
- Better concurrency, indexing, retention operations, and managed backup/HA capabilities.
- Requires migration tooling discipline and staged rollout by environment.
