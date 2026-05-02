# Data Model Ownership

- Service: `lotus-manage`
- Ownership: discretionary portfolio-management execution, supportability, policy-pack, and manage-local workflow persistence schema.

## Owned Domains

- lotus-manage policy-pack persistence model.
- lotus-manage run, supportability, lineage, and workflow persistence model.
- Schema migration history (`schema_migrations`) for lotus-manage namespaces.

## Service Boundaries

- Core portfolio ledger, valuation, and transaction source data remains lotus-core-owned.
- Advanced analytics are lotus-performance-owned and consumed through APIs where needed.
- Advisor-led proposal workflow ownership belongs to lotus-advise.

## Schema Rules

- Namespace `dpm` stores lotus-manage supportability, workflow, and policy-pack schema history.
- No cross-service shared database access.

