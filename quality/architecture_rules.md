# lotus-manage Architecture Rules

These rules define the report-only architecture baseline for the enterprise-readiness refactor.
They are explicit so later validators can enforce them without changing their meaning.

## Layering

1. Routers call application services or use-case functions only.
2. Routers must not call repositories, database clients, HTTP clients, Kafka, Redis, or downstream adapters directly.
3. Middleware stays thin, cross-cutting, and business-logic-free.
4. Domain and application code must not depend on FastAPI, framework objects, infrastructure clients, or persistence models.
5. Infrastructure sits behind explicit ports/adapters.
6. DTOs and persistence models must not leak into domain logic.

## Reliability And Auditability

1. Downstream failures map to consistent platform errors.
2. Every request must support and propagate a correlation identifier.
3. Relevant mutations must be auditable.
4. Idempotent operations must define replay/conflict behavior.
5. Logs must be structured and must not leak sensitive data.

## Current Gate Phase

These rules are in phase 1/report-only except for checks already covered by repo-native gates.
