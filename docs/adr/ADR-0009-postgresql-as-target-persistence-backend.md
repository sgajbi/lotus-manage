# ADR-0009: PostgreSQL as Target Persistence Backend for DPM and Advisory

## Status

Accepted

## Context

DPM and advisory workflows require durable, auditable, and scalable persistence for production operations. Current adapters (in-memory and SQLite) are useful for local development and incremental delivery but are not the long-term production target.

## Decision

Set PostgreSQL as the target production persistence backend for both domains:

- DPM supportability and lineage storage
- advisory proposal lifecycle and supportability storage

Keep in-memory (and optionally SQLite) adapters for local and test profiles behind backend configuration flags.

## Consequences

- Unified enterprise persistence strategy across DPM and advisory.
- Better concurrency, indexing, retention operations, and managed backup/HA capabilities.
- Requires migration tooling discipline and staged rollout by environment.
