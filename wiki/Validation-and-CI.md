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

## Documentation contract proof

When `README.md` changes, run:

```bash
python -m pytest tests/unit/test_local_docker_runtime_contract.py -q
```

That protects the local Docker runtime contract wording.

When DPM supportability or OpenAPI-facing docs change, run:

```bash
python -m pytest tests/unit/dpm/contracts/test_contract_openapi_supportability_docs.py -q
```

If `make check` rewrites `docs/standards/api-vocabulary/lotus-manage-api-vocabulary.v1.json`,
inspect the diff before committing. Timestamp-only `generatedAt` churn is not meaningful docs work.
