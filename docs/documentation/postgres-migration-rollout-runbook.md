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
  - `DPM_POSTGRES_CONNECT_TIMEOUT_SECONDS` (`1..30`, default `3`)
  - `DPM_POSTGRES_STATEMENT_TIMEOUT_MS` (`100..60000`, default `5000`)
  - `DPM_POSTGRES_IDLE_IN_TRANSACTION_TIMEOUT_MS` (`1000..120000`, default `10000`)
  - `DPM_POSTGRES_ACQUIRE_TIMEOUT_SECONDS` (`1..30`, default `2`)
- Application image/version to deploy is already tested in non-production.
- Production compose override available:
  - `docker-compose.production.yml`

## Profile Modes

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

Use the shared migration tool before switching traffic:

```bash
python scripts/postgres_migrate.py --target dpm
```

Production contract check (profile/env/migration readiness):

```bash
python scripts/production_cutover_check.py --check-migrations
```

## Startup Sequencing

1. Start/verify Postgres instance health.
2. Apply migrations (`scripts/postgres_migrate.py`).
3. Validate production contract (`scripts/production_cutover_check.py --check-migrations`).
4. Start API services with Postgres backends enabled and production persistence profile:
   - `APP_PERSISTENCE_PROFILE=PRODUCTION`
   - `DPM_SUPPORTABILITY_STORE_BACKEND=POSTGRES`
   - `DPM_POLICY_PACK_CATALOG_BACKEND=POSTGRES` (when policy packs/admin APIs are enabled)
5. Run smoke API checks for lotus-manage.
6. Shift traffic.

Do not start app replicas with Postgres backend enabled before migrations have completed.

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

CI executes:

1. `python scripts/postgres_migrate.py --target dpm`
2. Live Postgres integration tests:
   - `tests/integration/dpm/supportability/test_dpm_postgres_repository_integration.py`
   - `tests/integration/dpm/supportability/test_dpm_policy_pack_postgres_repository_integration.py`
3. Production-profile startup smoke:
   - starts API with `APP_PERSISTENCE_PROFILE=PRODUCTION` and Postgres backends.
4. Production-profile guardrail negatives:
  - validates startup fails with:
    - `PERSISTENCE_PROFILE_REQUIRES_DPM_POSTGRES`
    - `PERSISTENCE_PROFILE_REQUIRES_DPM_POSTGRES_DSN`
    - `PERSISTENCE_PROFILE_REQUIRES_POLICY_PACK_POSTGRES`
    - `PERSISTENCE_PROFILE_REQUIRES_POLICY_PACK_POSTGRES_DSN`
    - `POSTGRES_ACCESS_POLICY_INVALID:{env_name}`
    - `POSTGRES_ACCESS_POLICY_OUT_OF_RANGE:{env_name}:{minimum}:{maximum}`
5. Production cutover contract check:
   - `python scripts/production_cutover_check.py --check-migrations`
6. Optional nightly/manual deep validation:
   - `.github/workflows/nightly-postgres-full.yml`
   - runs integration repositories plus live API demo pack in production profile on Postgres.

This validates both migration application and repository contract parity on real Postgres.

## Rollback Guidance

- Schema migrations are forward-only; do not roll back by editing migration files.
- If rollout fails after migration:
  - keep schema as-is,
  - redeploy previous compatible app version,
  - fix forward in a new migration.
- If startup fails due profile guardrails:
  - correct backend/profile/DSN env configuration,
  - rerun `scripts/production_cutover_check.py --check-migrations`,
  - restart services.

## Completion Evidence

- Cutover acceptance checklist:
  - `docs/demo/postgres-cutover-checklist-2026-02-20.md`
