# Scalability and Availability Standard Alignment

Service: DPM

This repository adopts the platform-wide standard defined in lotus-platform/Scalability and Availability Standard.md.

## Implemented Baseline

- Stateless service behavior with externalized durable state.
- Explicit timeout and bounded retry/backoff for inter-service communication where applicable.
- Health/liveness/readiness endpoints for runtime orchestration.
- Observability instrumentation for latency/error/throughput diagnostics.

## Required Evidence

- Compliance matrix entry in lotus-platform/output/scalability-availability-compliance.md.
- Service-specific tests covering resilience and concurrency-critical paths.

## Database Scalability Fundamentals

- Query plan review is required for proposal retrieval, run supportability, and operation lookup endpoints.
- Index definitions must support correlation-id, workflow status, and time-window query paths.
- Data growth assumptions are tracked for async operation logs and persisted run artifacts.
- Retention and archival controls are mandatory for supportability records and audit-linked payloads.

## Availability Baseline

- Internal SLO baseline: p95 synchronous proposal API latency < 400 ms; error rate < 1%.
- Recovery targets: RTO 30 minutes and RPO 15 minutes for persisted DPM operations.
- Backup and restore validation is required for proposal/run stores in every deployment environment.

## Caching Policy Baseline

- DPM only permits explicit bounded caches for idempotency and workflow supportability lookups.
- Cache use-cases must define TTL and max-size controls with clear invalidation ownership.
- Stale-read behavior is disallowed for correctness-critical rebalance outcomes; stale supportability reads must be explicitly documented.

## Scale Signal Metrics Coverage

- DPM exports `/metrics` for HTTP and workflow instrumentation.
- Platform-shared infrastructure metrics for CPU/memory, DB latency/pool behavior, and queue lag are sourced from:
  - `lotus-platform/platform-stack/prometheus/prometheus.yml`
  - `lotus-platform/platform-stack/docker-compose.yml`
  - `lotus-platform/Platform Observability Standards.md`

## Deviation Rule

Any deviation from this standard requires ADR/RFC with remediation timeline.

