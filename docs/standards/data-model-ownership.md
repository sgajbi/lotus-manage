# Data Model Ownership

- Service: `lotus-manage`
- Ownership: discretionary portfolio-management execution, supportability, policy-pack, and manage-local workflow persistence schema.

## Owned Domains

- lotus-manage policy-pack persistence model.
- lotus-manage run, supportability, lineage, and workflow persistence model.
- Any remaining manage-local proposal workflow persistence while split-governance cleanup is in progress.
- Schema migration history (`schema_migrations`) for lotus-manage namespaces.

## Service Boundaries

- Core portfolio ledger, valuation, and transaction source data remains lotus-core-owned.
- Advanced analytics are lotus-performance-owned and consumed through APIs where needed.
- Advisor-led proposal workflow ownership belongs to lotus-advise.

## Schema Rules

- Namespaces (`dpm`, `proposals`) separate bounded contexts.
- No cross-service shared database access.

