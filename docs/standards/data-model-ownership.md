# Data Model Ownership

- Service: `lotus-advise`
- Ownership: advisory/discretionary proposal and policy execution domain schema.

## Owned Domains

- DPM policy-pack persistence model.
- Advisory proposal workflow persistence model.
- Schema migration history (`schema_migrations`) for DPM namespaces.

## Service Boundaries

- Core portfolio ledger, valuation, and transaction source data remains PAS-owned.
- Advanced analytics are PA-owned and consumed through APIs where needed.

## Schema Rules

- Namespaces (`dpm`, `proposals`) separate bounded contexts.
- No cross-service shared database access.

