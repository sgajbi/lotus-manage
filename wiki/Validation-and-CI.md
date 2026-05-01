# Validation and CI

## Lane model

`lotus-manage` uses:

1. `Remote Feature Lane`
2. `Pull Request Merge Gate`
3. `Main Releasability Gate`

## Local command mapping

- `make check`
  lint, no-alias, typecheck, OpenAPI, API vocabulary, unit tests
- `make ci`
  migration smoke, full tests with coverage, security audit
- `make ci-local`
  split local validation across unit, integration, and e2e phases
- `make ci-local-docker`
  Docker parity for the local CI contract
- `make live-api-validate`
  live API evidence against a running `lotus-manage` instance

## Live API evidence

Use this before claiming `lotus-manage` API readiness:

```bash
LOTUS_MANAGE_BASE_URL=http://127.0.0.1:8001 make live-api-validate
```

The validator runs the live demo pack and focused production-readiness probes:

1. readiness,
2. backend-owned capability truth,
3. OpenAPI advisory/proposal boundary cleanliness,
4. removed proposal route behavior,
5. duplicate async correlation conflict handling,
6. PostgreSQL-backed supportability summary,
7. bounded supportability metrics.

For reusable evidence, write the JSON summary directly:

```bash
python scripts/validate_live_api.py --base-url http://127.0.0.1:8001 --json-output output/live-api/summary.json
```

## Documentation contract proof

When `README.md` changes, run:

```bash
python -m pytest tests/unit/test_local_docker_runtime_contract.py -q
```

That protects the local Docker runtime contract wording.

When Docker readiness, migration startup, or supportability health behavior changes, include:

```bash
python -m pytest tests/unit/test_local_docker_runtime_contract.py tests/unit/dpm/api/test_observability_api.py tests/unit/shared/dependencies/test_production_cutover_contract.py -q
docker compose config
```

Gateway and Workbench proof should be treated as downstream integration validation. `lotus-manage`
API certification should first pass `make check` and `make live-api-validate`.

When DPM supportability or OpenAPI-facing docs change, run:

```bash
python -m pytest tests/unit/dpm/contracts/test_contract_openapi_supportability_docs.py -q
```

If `make check` rewrites `docs/standards/api-vocabulary/lotus-manage-api-vocabulary.v1.json`,
inspect the diff before committing. Timestamp-only `generatedAt` churn is not meaningful docs work.
