# Validation and CI

## Current scope

Current scope: this page describes the repo-native validation commands, GitHub lane placement, and
evidence expected before `lotus-manage` changes are claimed ready. Branch changes must pass local
repo-native gates first; wiki publication happens only after the corresponding source changes merge
to `main`.

## Evidence map

| Validation question | Primary command or lane | Evidence posture |
| --- | --- | --- |
| Is the branch locally fit for PR? | `make check`, focused tests, targeted contract validators | Blocking local proof before push or PR updates. |
| Is the PR mergeable? | Pull Request Merge Gate | Required GitHub checks must be green; solo development does not require a reviewer when CI and conversations are clean. |
| Is main releasable after merge? | Main Releasability Gate | Post-merge proof must point to the merged `main` SHA when the workflow applies. |
| Did docs or wiki truth change? | Repo docs tests; `Sync-RepoWikis.ps1 -CheckOnly -AllowUnpublishedSourceChanges` before merge when the branch intentionally changes `wiki/`; publish after merge; rerun strict `Sync-RepoWikis.ps1 -CheckOnly` after publication | Repo-local `wiki/` is source truth; GitHub wiki is a publication target. |
| Is live source integration claimed? | `make live-api-validate-core`, `make demo-certify` where applicable | Live proof is required before claiming stateful Core-backed readiness or demo certification. |

## Lane model

`lotus-manage` uses:

1. `Remote Feature Lane`
2. `Pull Request Merge Gate`
3. `Main Releasability Gate`

## Local command mapping

- `make check`
  lint, no-alias, typecheck, OpenAPI, API vocabulary, unit tests
- `make ci`
  migration smoke, full tests with coverage, security audit. Coverage is enforced by the same
  governed two-decimal `scripts/coverage_gate.py` validator as protected combined coverage, so a
  local 98.98% result cannot pass the 99.00% policy through display rounding.
- `make ci-local`
  split local validation across unit, integration, and e2e phases
- `make ci-local-docker`
  Docker parity for the local CI contract
- `make live-api-validate`
  live API evidence against a running `lotus-manage` instance
- `make live-api-validate-core`
  live API evidence against `lotus-manage` plus current `lotus-core` DPM source-product posture.
  The canonical source-ready stack defaults to
  `LOTUS_MANAGE_EXPECT_STATEFUL_CORE_SOURCING=available`; set it to `disabled` only for a
  deliberately non-source-ready local runtime.
- `make demo-certify`
  app-level demo certification against the canonical live stack. The default evidence path is
  `output/live-api/demo-certification/summary.json`.

## Live API evidence

Use this before claiming `lotus-manage` API readiness:

Set `LOTUS_MANAGE_BASE_URL` to the [local manage API](http://127.0.0.1:8001) for local evidence
runs.

```bash
LOTUS_MANAGE_BASE_URL=$LOTUS_MANAGE_BASE_URL make live-api-validate
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
python scripts/validate_live_api.py --base-url "$LOTUS_MANAGE_BASE_URL" --json-output output/live-api/summary.json
```

Use this before claiming manage/core integration readiness with stateful sourcing enabled:

```bash
make live-api-validate-core
```

The validator proves capability truth against the RFC-087 certified composed DPM source-data products,
a live stateful simulate call with READY `lotus-core` lineage, stateful source-backed construction
over `TransactionCostCurve:v1`, `PortfolioCashflowProjection:v1`,
`ClientRestrictionProfile:v1`, and `SustainabilityPreferenceProfile:v1`, duplicate async
correlation handling, supportability persistence, metrics, and continued absence of the retired
monolithic core DPM execution-context route.

Canonical core/manage proof mode must configure both `DPM_CORE_BASE_URL` and
`DPM_CORE_QUERY_BASE_URL` for `lotus-manage`. `DPM_CORE_TRANSACTION_COST_LOOKBACK_DAYS` defaults to
400 days so the observed-cost proof covers low-turnover private-banking portfolios without making
predictive execution-cost or market-impact claims.

For app-level demo certification, run:

```bash
make demo-certify
```

The command uses the same live API validator with canonical defaults for
`PB_SG_GLOBAL_BAL_001` as of `2026-04-10`, writes machine-readable evidence, and exits non-zero if
capability truth, stateful source-backed construction, expected construction figures,
supportability persistence, metrics, or retired-route behavior are weak or failing.

CI posture:

1. the `Demo Certification` GitHub workflow is manual and uploads the evidence artifact for
   caller-supplied reachable canonical URLs,
2. `Quality Baseline` runs deterministic command-contract tests report-only so future agents see
   drift without making environment-dependent live stack proof a noisy blocker,
3. live demo certification should become blocking only after the canonical stack is available in
   the intended CI lane and repeated runs prove baseline stability, false-positive posture, and
   exception handling.

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
