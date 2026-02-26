# Data Model Ownership

- Service: `lotus-advise`
- Ownership: advisory/discretionary proposal and policy execution domain schema.

## Owned Domains

- lotus-manage policy-pack persistence model.
- Advisory proposal workflow persistence model.
- Schema migration history (`schema_migrations`) for lotus-manage namespaces.

## Service Boundaries

- Core portfolio ledger, valuation, and transaction source data remains lotus-core-owned.
- Advanced analytics are lotus-performance-owned and consumed through APIs where needed.

## Schema Rules

- Namespaces (`dpm`, `proposals`) separate bounded contexts.
- No cross-service shared database access.

