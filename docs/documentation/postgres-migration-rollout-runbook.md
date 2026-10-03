# PostgreSQL Migration Rollout Runbook

## Scope

Runbook for forward-only schema migration rollout for:

- lotus-manage supportability Postgres namespace (`dpm`)

## Preconditions

- PostgreSQL is reachable and healthy.
- Runtime DSNs are configured:
  - `DPM_SUPPORTABILITY_POSTGRES_DSN`
- Runtime Postgres access policy is configured or defaults are accepted:
  - `DPM_POSTGRES_MAX_CONNECTIONS` (`1..100`, default `10`)
  - `DPM_POSTGRES_COORDINATION_MAX_CONNECTIONS` (`1..100`, default `4`)
  - `DPM_POSTGRES_CONNECT_TIMEOUT_SECONDS` (`1..30`, default `3`)
  - `DPM_POSTGRES_STATEMENT_TIMEOUT_MS` (`100..60000`, default `5000`)
  - `DPM_POSTGRES_COORDINATION_WAIT_TIMEOUT_MS` (`1000..300000`, default `60000`)
  - `DPM_POSTGRES_IDLE_IN_TRANSACTION_TIMEOUT_MS` (`1000..120000`, default `10000`)
  - `DPM_POSTGRES_ACQUIRE_TIMEOUT_SECONDS` (`1..30`, default `2`)
- Application image/version to deploy is already tested in non-production.
- Production compose override available:
  - `docker-compose.production.yml`

## Profile Modes

Only `LOCAL` and `PRODUCTION` are accepted (case-insensitive, surrounding whitespace ignored).
Native unset `APP_PERSISTENCE_PROFILE` defaults to `LOCAL`; Compose defaults to `PRODUCTION`
only when unset and preserves explicit blanks. Blank or unknown values raise
`PERSISTENCE_PROFILE_UNSUPPORTED` before migration database access or API startup; readiness
returns HTTP `500`. Correct the profile rather than disabling production checks.

- `APP_PERSISTENCE_PROFILE=LOCAL`:
  - Intended for local development workflows.
  - Postgres-backed runtime is the default local mode.
  - In-memory/SQLite/ENV_JSON runtime backends are deprecated and kept only for transition/testing.
- `APP_PERSISTENCE_PROFILE=PRODUCTION`:
  - Enforces Postgres-only runtime guardrails at startup.
  - Required backend settings:
    - `DPM_SUPPORTABILITY_STORE_BACKEND=POSTGRES`
    - `DPM_POLICY_PACK_CATALOG_BACKEND=POSTGRES` when policy packs/admin APIs are enabled.

## Migration Command

From the `lotus-manage` repository root with the project environment active, use this command
in PowerShell or a POSIX shell before switching traffic:

```bash
python scripts/postgres_migrate.py --target dpm
```

Application startup validates profile configuration. `GET /health/ready` additionally validates
required applied migrations in the production profile; require HTTP `200` before traffic admission.

## Startup Sequencing

1. Configure a supported profile and the required persistence/authorization settings.
2. Start/verify Postgres instance health.
3. Apply migrations (`scripts/postgres_migrate.py --target dpm`).
4. Start API services with Postgres backends enabled and production persistence profile:
   - `APP_PERSISTENCE_PROFILE=PRODUCTION`
   - `DPM_SUPPORTABILITY_STORE_BACKEND=POSTGRES`
   - `DPM_POLICY_PACK_CATALOG_BACKEND=POSTGRES` (when policy packs/admin APIs are enabled)
5. Require `GET /health/ready` HTTP `200`, then run supported API smoke checks.
6. Shift traffic.

Do not admit app replicas before migrations and readiness checks have completed. Compose applies
migrations before Uvicorn; the migration command rejects unsupported profiles before database I/O.

## Safety Controls

- Migrations are forward-only.
- Applied migration checksums are stored in `schema_migrations`.
- Migration execution is wrapped in a namespace-scoped PostgreSQL advisory lock
  to avoid concurrent deploy races.
- If a checked-in migration file is modified after apply, execution fails with:
  - `POSTGRES_MIGRATION_CHECKSUM_MISMATCH:{namespace}:{version}`
- Startup profile guardrails fail-fast in production profile with explicit reason codes:
  - `PERSISTENCE_PROFILE_REQUIRES_DPM_POSTGRES`
  - `PERSISTENCE_PROFILE_REQUIRES_DPM_POSTGRES_DSN`
  - `PERSISTENCE_PROFILE_REQUIRES_ENTERPRISE_AUTHZ`
  - `PERSISTENCE_PROFILE_REQUIRES_ENTERPRISE_PRIMARY_KEY_ID`
  - `PERSISTENCE_PROFILE_REQUIRES_ENTERPRISE_CAPABILITY_RULES`
  - `PERSISTENCE_PROFILE_REQUIRES_POLICY_PACK_POSTGRES`
  - `PERSISTENCE_PROFILE_REQUIRES_POLICY_PACK_POSTGRES_DSN`
  - `POSTGRES_ACCESS_POLICY_INVALID:{env_name}`
  - `POSTGRES_ACCESS_POLICY_OUT_OF_RANGE:{env_name}:{minimum}:{maximum}`
- Runtime repositories use the shared bounded Postgres access policy for connection acquisition,
  connect timeout, statement timeout, and idle-in-transaction timeout. Acquisition and driver
  failures raise stable `POSTGRES_CONNECTION_ACQUIRE_TIMEOUT` or
  `POSTGRES_CONNECTION_UNAVAILABLE` errors, emit bounded `lotus_manage_postgres_access_total`
  metrics, and log sanitized reason/classification fields without DSNs or payload content.
- Application writes are not blindly retried after database errors. Fix database capacity,
  connectivity, timeout, migration, or lock pressure first, then replay only caller-owned
  idempotent requests according to the route contract.

## CI Smoke Checks

The PR and main gates execute `make migration-smoke` for migration/readiness contract tests.
The required PostgreSQL job executes `make test-idea-management-action-postgres-coverage`
against PostgreSQL `17.6`, including real migrations, persistence and recovery tests.
The unit suite also covers profile rejection, startup refusal and registered readiness behavior.
Docker image evidence is a separate required job, not production operation or bank acceptance.

## Rollback Guidance

- Schema migrations are forward-only; do not roll back by editing migration files.
- If rollout fails after migration:
  - keep schema as-is,
  - redeploy previous compatible app version,
  - fix forward in a new migration.
- If startup fails due profile guardrails:
  - correct backend/profile/DSN env configuration,
  - restart services and require `GET /health/ready` HTTP `200` before traffic admission.

## Completion Evidence

Record the exact revision, migration outcome, readiness response, supported API smoke results,
CI run and rollout owner. Use [operations](../../wiki/Operations-Runbook.md) and
[validation](../../wiki/Validation-and-CI.md) for current evidence boundaries.
