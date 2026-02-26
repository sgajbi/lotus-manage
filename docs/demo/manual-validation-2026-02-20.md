# Demo Pack Manual Validation - 2026-02-20

## Scope

Validated the end-to-end demo pack scenarios through live API calls in both runtime modes:

- `uvicorn` local process on `http://127.0.0.1:8001`
- Docker Compose service on `http://127.0.0.1:8000`

Coverage includes:

- lotus-manage simulate demos (`01`-`08`)
- lotus-manage batch analyze demo (`09`)
- lotus-manage async batch analyze demo (`26`)
- lotus-manage supportability + deterministic artifact flow demo (`27`)
- lotus-manage async manual-execute guard demo (`28`)
- lotus-manage workflow gate default-disabled contract demo (`29`)
- lotus-manage policy-pack supportability diagnostics demo (`31`)
- lotus-manage supportability summary metrics demo (`32`)
- Advisory simulate demos (`10`-`18`)
- Advisory artifact demo (`19`)
- Advisory lifecycle flow demos (`20`-`25`)
- Proposal list support endpoint validation

## Commands Executed

### 1) Start uvicorn (local runtime)

```powershell
Start-Process -FilePath ".venv\Scripts\python.exe" -ArgumentList "-m","uvicorn","src.api.main:app","--host","127.0.0.1","--port","8001" -PassThru
```

### 2) Validate demo pack against uvicorn

```powershell
.venv\Scripts\python scripts/run_demo_pack_live.py --base-url http://127.0.0.1:8001
```

Observed result:

```text
Demo pack validation passed for http://127.0.0.1:8001
```

### 3) Build and run Docker runtime

```powershell
docker-compose up -d --build
```

### 4) Validate demo pack against Docker

```powershell
.venv\Scripts\python scripts/run_demo_pack_live.py --base-url http://127.0.0.1:8000
```

Observed result:

```text
Demo pack validation passed for http://127.0.0.1:8000
```

## Validation Notes

- Async scenario `26_dpm_async_batch_analysis.json` validated:
  - `POST /rebalance/analyze/async` returns `202 Accepted`.
  - `GET /rebalance/operations/{operation_id}` returns terminal `SUCCEEDED`.
  - Result payload contains expected partial-batch warning and failed scenario diagnostics:
    - `warnings = ["PARTIAL_BATCH_FAILURE"]`
    - `failed_scenarios = {"invalid_options": "..."}`
  - No contract or runtime mismatches observed between uvicorn and Docker paths.
  - Async operation listing validation:
    - `GET /rebalance/operations?status=SUCCEEDED&operation_type=ANALYZE_SCENARIOS&limit=...`
      returns filtered operation rows.
    - Cursor pagination check:
      - `GET /rebalance/operations?limit=1` returns `next_cursor`.
      - `GET /rebalance/operations?limit=1&cursor={next_cursor}` returns next row.
  - Additional manual listing checks:
    - Uvicorn (`DPM_ASYNC_EXECUTION_MODE=ACCEPT_ONLY`, `http://127.0.0.1:8017`):
      - `GET /rebalance/operations?operation_type=ANALYZE_SCENARIOS&status=PENDING&limit=10`
        returns expected pending operations.
      - cursor pagination over operations returns deterministic next row.
    - Container (`DPM_ASYNC_EXECUTION_MODE=ACCEPT_ONLY`, `http://127.0.0.1:8018`):
      - filtered listing and cursor pagination produce expected operation rows.
- Policy-pack supportability diagnostics scenario `31_dpm_policy_pack_supportability_diagnostics.json` validated:
  - Uvicorn runtime (`http://127.0.0.1:8001`):
    - `POST /rebalance/simulate` with policy headers returns `200`.
    - `GET /rebalance/policies/effective` returns `200` with:
      - `enabled`
      - `selected_policy_pack_id`
      - `source`
    - `GET /rebalance/policies/catalog` returns `200` with:
      - `enabled`
      - `total`
      - `selected_policy_pack_id`
      - `selected_policy_pack_present`
      - `selected_policy_pack_source`
      - `items`
  - Docker runtime (`http://127.0.0.1:8000`):
    - Same request sequence returns `200` with expected diagnostics keys.
- Supportability summary metrics scenario `32_dpm_supportability_summary_metrics.json` validated:
  - Uvicorn runtime (`http://127.0.0.1:8001`):
    - `POST /rebalance/simulate` returns `200`.
    - `GET /rebalance/supportability/summary` returns `200` with expected aggregate fields:
      - `store_backend`
      - `retention_days`
      - `run_count`
      - `operation_count`
      - `operation_status_counts`
      - `run_status_counts`
      - `workflow_decision_count`
      - `workflow_action_counts`
      - `workflow_reason_code_counts`
      - `lineage_edge_count`
  - Docker runtime (`http://127.0.0.1:8000`):
    - Same request sequence returns `200` with expected aggregate fields.
- Supportability summary API validation:
  - Uvicorn runtime (`http://127.0.0.1:8019`):
    - `POST /rebalance/simulate` returns `status=READY`.
    - `GET /rebalance/supportability/summary` returns `200` with:
      - `store_backend=IN_MEMORY`
      - `run_count=1`
      - `operation_count=0`
      - `run_status_counts={"READY":1}`
      - `workflow_decision_count=0`
      - `lineage_edge_count=2`
  - Docker runtime (`http://127.0.0.1:8000`):
    - `POST /rebalance/simulate` returns `status=READY`.
    - `GET /rebalance/supportability/summary` returns `200` with:
      - `store_backend=IN_MEMORY`
      - `run_count=1`
      - `operation_count=0`
      - `run_status_counts={"READY":1}`
      - `workflow_decision_count=0`
      - `lineage_edge_count=2`
  - Uvicorn runtime (`DPM_WORKFLOW_ENABLED=true`, `http://127.0.0.1:8035`):
    - `POST /rebalance/simulate` with pending-review candidate payload and one workflow `APPROVE` action.
    - `GET /rebalance/supportability/summary` returns:
      - `workflow_action_counts={"APPROVE":1}`
      - `workflow_reason_code_counts={"REVIEW_APPROVED":1}`
  - Container runtime (`DPM_WORKFLOW_ENABLED=true`, `http://127.0.0.1:8036`):
    - `POST /rebalance/simulate` with pending-review candidate payload and one workflow `APPROVE` action.
    - `GET /rebalance/supportability/summary` returns:
      - `workflow_action_counts={"APPROVE":1}`
      - `workflow_reason_code_counts={"REVIEW_APPROVED":1}`
- Run support bundle API validation:
  - Uvicorn runtime (`http://127.0.0.1:8022`):
    - `POST /rebalance/simulate` returns `status=READY`.
    - `GET /rebalance/runs/{rebalance_run_id}/support-bundle` returns `200` with:
      - `run.rebalance_run_id` matching created run id
      - `artifact` populated
      - `lineage.edges` count = `2`
      - `workflow_history.decisions` count = `0`
    - Correlation/idempotency variants:
      - `GET /rebalance/runs/by-correlation/{correlation_id}/support-bundle` returns `200`
        with run id matching simulate response.
      - `GET /rebalance/runs/idempotency/{idempotency_key}/support-bundle` returns `200`
        with run id matching simulate response.
      - `GET /rebalance/runs/by-operation/{operation_id}/support-bundle` returns `200`
        with run id matching simulate response after async operation creation.
  - Docker runtime (`http://127.0.0.1:8000`):
    - `POST /rebalance/simulate` returns `status=READY`.
    - `GET /rebalance/runs/{rebalance_run_id}/support-bundle` returns `200` with:
      - `run.rebalance_run_id` matching created run id
      - `artifact` populated
      - `lineage.edges` count = `2`
      - `workflow_history.decisions` count = `0`
    - Correlation/idempotency variants:
      - `GET /rebalance/runs/by-correlation/{correlation_id}/support-bundle` returns `200`
        with run id matching simulate response.
      - `GET /rebalance/runs/idempotency/{idempotency_key}/support-bundle` returns `200`
        with run id matching simulate response.
      - `GET /rebalance/runs/by-operation/{operation_id}/support-bundle` returns `200`
        with run id matching simulate response after async operation creation.
- SQLite supportability backend validation:
  - Uvicorn run (`DPM_SUPPORTABILITY_STORE_BACKEND=SQLITE`) on `http://127.0.0.1:8001`:
    - `POST /rebalance/simulate` succeeded (`200`).
    - `GET /rebalance/runs/{rebalance_run_id}` succeeded (`200`).
    - `GET /rebalance/runs/by-correlation/{correlation_id}` succeeded (`200`).
    - `GET /rebalance/runs/idempotency/{idempotency_key}` succeeded (`200`).
- Lineage API validation:
  - Uvicorn run (`DPM_LINEAGE_APIS_ENABLED=true`) on `http://127.0.0.1:8001`:
    - `GET /rebalance/lineage/{correlation_id}` returns `200` with `CORRELATION_TO_RUN`.
    - `GET /rebalance/lineage/{idempotency_key}` returns `200` with `IDEMPOTENCY_TO_RUN`.
    - `GET /rebalance/lineage/{operation_id}` returns `200` with `OPERATION_TO_CORRELATION`.
- Idempotency history API validation:
  - Uvicorn run (`DPM_IDEMPOTENCY_REPLAY_ENABLED=false`, `DPM_IDEMPOTENCY_HISTORY_APIS_ENABLED=true`)
    on `http://127.0.0.1:8011`:
    - Two `POST /rebalance/simulate` calls with same idempotency key and different payload hash
      both return `200`.
    - `GET /rebalance/idempotency/{idempotency_key}/history` returns `200` with two entries
      preserving run ids, correlation ids, and request hashes.
  - Container run (`lotus-advise:latest`, `DPM_IDEMPOTENCY_REPLAY_ENABLED=false`,
    `DPM_IDEMPOTENCY_HISTORY_APIS_ENABLED=true`, `DPM_SUPPORTABILITY_STORE_BACKEND=SQLITE`)
    on `http://127.0.0.1:8012`:
    - Two `POST /rebalance/simulate` calls with same idempotency key and different payload hash
      both return `200`.
    - `GET /rebalance/idempotency/{idempotency_key}/history` returns `200` with two entries.
  - Container run (`DPM_LINEAGE_APIS_ENABLED=true`, `DPM_SUPPORTABILITY_STORE_BACKEND=SQLITE`)
    on `http://127.0.0.1:8002`:
    - `GET /rebalance/lineage/{correlation_id}` returns `200` with `CORRELATION_TO_RUN`.
    - `GET /rebalance/lineage/{idempotency_key}` returns `200` with `IDEMPOTENCY_TO_RUN`.
    - `GET /rebalance/lineage/{operation_id}` returns `200` with `OPERATION_TO_CORRELATION`.
  - Container run (`lotus-advise:latest` with `DPM_SUPPORTABILITY_STORE_BACKEND=SQLITE`)
    on `http://127.0.0.1:8002`:
    - `POST /rebalance/simulate` succeeded (`200`).
    - `GET /rebalance/runs/{rebalance_run_id}` succeeded (`200`).
    - `GET /rebalance/runs/by-correlation/{correlation_id}` succeeded (`200`).
    - `GET /rebalance/runs/idempotency/{idempotency_key}` succeeded (`200`).
- Supportability and artifact scenario `27_dpm_supportability_artifact_flow.json` validated:
  - `POST /rebalance/simulate` with idempotency + correlation headers succeeds.
  - `GET /rebalance/runs/{rebalance_run_id}` returns run payload and metadata.
  - `GET /rebalance/runs/by-correlation/{correlation_id}` returns mapped run.
  - `GET /rebalance/runs/idempotency/{idempotency_key}` returns mapped run id.
  - `GET /rebalance/runs?status=READY&portfolio_id={portfolio_id}&limit=...` returns filtered rows.
  - Cursor pagination check:
    - `GET /rebalance/runs?limit=1` returns `next_cursor`.
    - `GET /rebalance/runs?limit=1&cursor={next_cursor}` returns next row.
  - `GET /rebalance/runs/{rebalance_run_id}/artifact` returns deterministic artifact payload.
  - Repeated artifact retrieval returns identical `evidence.hashes.artifact_hash`.
- Supportability run-list and retention validation:
  - Uvicorn (`DPM_SUPPORTABILITY_STORE_BACKEND=SQLITE`,
    `DPM_SUPPORTABILITY_RETENTION_DAYS=1`, `http://127.0.0.1:8015`):
    - `POST /rebalance/simulate` succeeds and appears in `GET /rebalance/runs`.
    - After setting persisted run timestamp older than retention window in SQLite,
      `GET /rebalance/runs` returns empty list (expired run purged).
  - Container (`DPM_SUPPORTABILITY_STORE_BACKEND=SQLITE`,
    `DPM_SUPPORTABILITY_RETENTION_DAYS=1`, `http://127.0.0.1:8016`):
    - `POST /rebalance/simulate` succeeds and appears in `GET /rebalance/runs`.
    - After setting persisted run timestamp older than retention window in SQLite,
      `GET /rebalance/runs` returns empty list (expired run purged).
- Request-hash run-list filtering validation:
  - Uvicorn runtime (`http://127.0.0.1:8025`):
    - `POST /rebalance/simulate` succeeds.
    - `GET /rebalance/runs/{rebalance_run_id}` returns persisted `request_hash`.
    - `GET /rebalance/runs?request_hash={request_hash}&limit=20` returns one matching run.
    - `GET /rebalance/runs/by-request-hash/{url_encoded_request_hash}` returns matching run.
  - Docker runtime (`http://127.0.0.1:8000`):
    - `POST /rebalance/simulate` succeeds.
    - `GET /rebalance/runs/{rebalance_run_id}` returns persisted `request_hash`.
    - `GET /rebalance/runs?request_hash={request_hash}&limit=20` returns one matching run.
    - `GET /rebalance/runs/by-request-hash/{url_encoded_request_hash}` returns matching run.
- Async manual execute guard scenario `28_dpm_async_manual_execute_guard.json` validated:
  - `POST /rebalance/analyze/async` in default inline mode succeeds and completes operation.
  - `POST /rebalance/operations/{operation_id}/execute` returns `409` with
    `DPM_ASYNC_OPERATION_NOT_EXECUTABLE` when operation is already non-pending.
- Workflow gate contract scenario `29_dpm_workflow_gate_disabled_contract.json` validated:
  - `POST /rebalance/simulate` creates a pending-review candidate run.
  - `GET /rebalance/runs/{rebalance_run_id}/workflow` returns `404` with
    `DPM_WORKFLOW_DISABLED` under default config.
  - `GET /rebalance/runs/{rebalance_run_id}/workflow/history` returns `404` with
    `DPM_WORKFLOW_DISABLED` under default config.
- Additional workflow-enabled supportability checks validated:
  - Uvicorn runtime (`DPM_WORKFLOW_ENABLED=true`, `http://127.0.0.1:8032`):
    - `POST /rebalance/simulate` returns `200` for workflow-review candidate payload.
    - `POST /rebalance/runs/{rebalance_run_id}/workflow/actions` with `APPROVE` returns `200`.
    - `GET /rebalance/workflow/decisions?actor_id=reviewer_manual_uvicorn&action=APPROVE&limit=10`
      returns `200` with one matching decision.
    - `GET /rebalance/workflow/decisions/by-correlation/corr-manual-wf-uvicorn`
      returns `200` with decision history for the resolved run.
  - Uvicorn runtime (`DPM_WORKFLOW_ENABLED=true`, `http://127.0.0.1:8033`):
    - `POST /rebalance/simulate` + one workflow `APPROVE` action succeeded.
    - `GET /rebalance/workflow/decisions/by-correlation/corr-manual-wf-corr-uvicorn`
      returns `200` with `run_id=rr_b5a85230` and one decision.
  - Uvicorn (`DPM_WORKFLOW_ENABLED=true`, `http://127.0.0.1:8001`):
    - `GET /rebalance/runs/by-correlation/{correlation_id}/workflow` returns `200`.
    - `GET /rebalance/runs/idempotency/{idempotency_key}/workflow` returns `200`.
    - `GET /rebalance/runs/by-correlation/{correlation_id}/workflow/history` returns `200`.
    - `GET /rebalance/runs/idempotency/{idempotency_key}/workflow/history` returns `200`.
    - `POST /rebalance/runs/by-correlation/{correlation_id}/workflow/actions` returns `200`.
    - `POST /rebalance/runs/idempotency/{idempotency_key}/workflow/actions` returns `200`.
    - Sequential action check:
      - correlation-based `REQUEST_CHANGES` keeps workflow in `PENDING_REVIEW`
      - idempotency-based `APPROVE` transitions workflow to `APPROVED`
    - Workflow action and history are consistent between run-id and correlation-id endpoints.
    - Idempotency-key workflow retrieval without prior action returns:
      - `workflow_status=PENDING_REVIEW`
      - history `decisions=[]`
    - `GET /rebalance/workflow/decisions?limit=20` returns workflow decisions across runs.
    - `GET /rebalance/workflow/decisions?actor_id=...&action=...&limit=...` returns filtered rows.
  - Container runtime (`lotus-advise:latest` with `-e DPM_WORKFLOW_ENABLED=true`,
    published on `http://127.0.0.1:8002`):
    - `GET /rebalance/runs/by-correlation/{correlation_id}/workflow` returns `200`.
    - `GET /rebalance/runs/idempotency/{idempotency_key}/workflow` returns `200`.
    - `GET /rebalance/runs/by-correlation/{correlation_id}/workflow/history` returns `200`.
    - `GET /rebalance/runs/idempotency/{idempotency_key}/workflow/history` returns `200`.
    - `POST /rebalance/runs/by-correlation/{correlation_id}/workflow/actions` returns `200`.
    - `POST /rebalance/runs/idempotency/{idempotency_key}/workflow/actions` returns `200`.
    - Sequential action check:
      - correlation-based `REQUEST_CHANGES` keeps workflow in `PENDING_REVIEW`
      - idempotency-based `APPROVE` transitions workflow to `APPROVED`
    - Idempotency-key workflow retrieval without prior action returns:
      - `workflow_status=PENDING_REVIEW`
      - history `decisions=[]`
  - Container runtime (`lotus-advise:latest` with `-e DPM_WORKFLOW_ENABLED=true`,
    published on `http://127.0.0.1:8031`):
    - `POST /rebalance/simulate` returns `200`.
    - `POST /rebalance/runs/{rebalance_run_id}/workflow/actions` with `APPROVE` returns `200`.
    - `GET /rebalance/workflow/decisions?actor_id=reviewer_manual_docker&action=APPROVE&limit=10`
      returns `200` with one matching decision.
    - `GET /rebalance/workflow/decisions/by-correlation/corr-manual-wf-docker`
      returns `200` with decision history for the resolved run.
  - Container runtime (`lotus-advise:latest` with `-e DPM_WORKFLOW_ENABLED=true`,
    published on `http://127.0.0.1:8034`):
    - `POST /rebalance/simulate` + one workflow `APPROVE` action succeeded.
    - `GET /rebalance/workflow/decisions/by-correlation/corr-manual-wf-corr-docker`
      returns `200` with `run_id=rr_7d3afe35` and one decision.
- Policy-pack scaffold validation (RFC-0022 slice 1):
  - Uvicorn runtime (`DPM_POLICY_PACKS_ENABLED=true`, `DPM_DEFAULT_POLICY_PACK_ID=dpm_default_pack`,
    `http://127.0.0.1:8037`):
    - `POST /rebalance/simulate` with `X-Policy-Pack-Id=dpm_request_pack` returns `200`
      and unchanged simulation behavior (`status=READY` observed).
  - Container runtime (`DPM_POLICY_PACKS_ENABLED=true`, `DPM_DEFAULT_POLICY_PACK_ID=dpm_default_pack`,
    `http://127.0.0.1:8038`):
    - `POST /rebalance/simulate` with `X-Policy-Pack-Id=dpm_request_pack` returns `200`
      and unchanged simulation behavior (`status=READY` observed).
- Policy-pack supportability endpoint validation (RFC-0022 slice 2):
  - Uvicorn runtime (`DPM_POLICY_PACKS_ENABLED=true`, `DPM_DEFAULT_POLICY_PACK_ID=dpm_default_pack`):
    - `GET /rebalance/policies/effective` with:
      - `X-Policy-Pack-Id=req_pack`

## RFC-0024 Postgres Backend Validation

- Uvicorn runtime (`http://127.0.0.1:8041`) with:
  - `PROPOSAL_STORE_BACKEND=POSTGRES`
  - `PROPOSAL_POSTGRES_DSN=postgresql://dpm:dpm@127.0.0.1:5432/dpm_supportability`
  - Command:
    - `.venv\Scripts\python scripts/run_demo_pack_live.py --base-url http://127.0.0.1:8041`
  - Observed result:
    - `Demo pack validation passed for http://127.0.0.1:8041`

- Docker runtime (`http://127.0.0.1:8000`) with profile `postgres` and:
  - `PROPOSAL_STORE_BACKEND=POSTGRES`
  - `PROPOSAL_POSTGRES_DSN=postgresql://dpm:dpm@postgres:5432/dpm_supportability`
  - `DPM_SUPPORTABILITY_STORE_BACKEND=POSTGRES`
  - `DPM_SUPPORTABILITY_POSTGRES_DSN=postgresql://dpm:dpm@postgres:5432/dpm_supportability`
  - Commands:
    - `docker-compose --profile postgres up -d --build lotus-advise`
    - `.venv\Scripts\python scripts/run_demo_pack_live.py --base-url http://127.0.0.1:8000`
  - Observed result:
    - `Demo pack validation passed for http://127.0.0.1:8000`
      - `X-Tenant-Policy-Pack-Id=tenant_pack`
      returns `200` with:
      - `enabled=true`
      - `selected_policy_pack_id=req_pack`
      - `source=REQUEST`
  - Container runtime (`DPM_POLICY_PACKS_ENABLED=true`, `DPM_DEFAULT_POLICY_PACK_ID=dpm_default_pack`):
    - same call and response semantics verified.
    - `GET /rebalance/workflow/decisions?limit=20` returns workflow decisions across runs.
    - `GET /rebalance/workflow/decisions?actor_id=...&action=...&limit=...` returns filtered rows.
- Live Postgres repository contract validation (RFC-0024 slice 8):
  - Precondition:
    - `docker-compose --profile postgres up -d postgres`
    - `DPM_POSTGRES_INTEGRATION_DSN=postgresql://dpm:dpm@127.0.0.1:5432/dpm_supportability`
  - Executed:
    - `uv run pytest tests/integration/dpm/supportability/test_dpm_postgres_repository_integration.py -q`
  - Observed:
    - `3 passed in 4.75s`
    - run persistence/lookup/filter/cursor behavior matched repository contract
    - artifact persistence/retrieval remained deterministic
    - idempotency/workflow/lineage summary counters persisted and were queryable
    - async TTL purge and run retention cascade purge semantics were enforced
- Live Postgres API validation for supportability flow (RFC-0024 slice 8):
  - Uvicorn runtime (`http://127.0.0.1:8041`) with:
    - `DPM_SUPPORTABILITY_STORE_BACKEND=POSTGRES`
    - `DPM_SUPPORTABILITY_POSTGRES_DSN=postgresql://dpm:dpm@127.0.0.1:5432/dpm_supportability`
    validated:
    - `POST /rebalance/simulate` returns `status=READY`
    - `GET /rebalance/runs/by-correlation/{correlation_id}` returns the same `rebalance_run_id`
    - `GET /rebalance/supportability/summary` returns:
      - `store_backend=POSTGRES`
      - `run_count=1`
  - Docker runtime (`http://127.0.0.1:8003`) with:
    - `docker run ... -e DPM_SUPPORTABILITY_STORE_BACKEND=POSTGRES -e DPM_SUPPORTABILITY_POSTGRES_DSN=...`
    validated:
    - `POST /rebalance/simulate` returns `status=READY`
    - `GET /rebalance/runs/by-correlation/{correlation_id}` returns the same `rebalance_run_id`
    - `GET /rebalance/supportability/summary` returns:
      - `store_backend=POSTGRES`
      - `run_count=2` (includes previously persisted uvicorn validation run)
- Policy-pack catalog supportability endpoint validation (RFC-0022 slice 4):
  - Docker runtime (`http://127.0.0.1:8000`):
    - `GET /rebalance/policies/catalog` with:
      - `X-Policy-Pack-Id=dpm_standard_v1`
      - `X-Tenant-Policy-Pack-Id=dpm_tenant_default_v1`
      returns `200` with:
      - `enabled=false`
      - `total=0`
      - `selected_policy_pack_source=DISABLED`
  - Uvicorn runtime (`http://127.0.0.1:8002`):
    - same call and response semantics verified.
- Policy-pack tax/turnover application path validation (RFC-0022 slice 5):
  - Docker runtime (`http://127.0.0.1:8000`):
    - `POST /rebalance/simulate` with:
      - `Idempotency-Key=manual-policy-tax-8000`
      - `X-Policy-Pack-Id=dpm_standard_v1`
      returns `200` with `status=READY`.
  - Uvicorn runtime (`http://127.0.0.1:8002`):
    - same call and response semantics verified (`status=READY`).
- Tenant policy-pack resolver validation (RFC-0022 slice 6):
  - Docker runtime (`http://127.0.0.1:8000`, default config):
    - `GET /rebalance/policies/effective` with `X-Tenant-Id=tenant_001` returns:
      - `enabled=false`
      - `source=DISABLED`
    - `POST /rebalance/simulate` with `X-Tenant-Id=tenant_001` returns `200` with `status=READY`.
  - Uvicorn runtime (`http://127.0.0.1:8003`) with:
    - `DPM_POLICY_PACKS_ENABLED=true`
    - `DPM_DEFAULT_POLICY_PACK_ID=global_pack`
    - `DPM_POLICY_PACK_CATALOG_JSON={"tenant_pack":{"version":"1","turnover_policy":{"max_turnover_pct":"0.02"}}}`
    - `DPM_TENANT_POLICY_PACK_RESOLUTION_ENABLED=true`
    - `DPM_TENANT_POLICY_PACK_MAP_JSON={"tenant_001":"tenant_pack"}`
    validated:
    - `GET /rebalance/policies/effective` with `X-Tenant-Id=tenant_001` returns:
      - `enabled=true`
      - `selected_policy_pack_id=tenant_pack`
      - `source=TENANT_DEFAULT`
    - `GET /rebalance/policies/catalog` with `X-Tenant-Id=tenant_001` returns:
      - `total=1`
      - `selected_policy_pack_id=tenant_pack`
      - `selected_policy_pack_present=true`
    - `POST /rebalance/simulate` with `X-Tenant-Id=tenant_001` returns `200` with `status=READY`.
- Settlement policy-pack override validation (RFC-0022 slice 7):
  - Docker runtime (`http://127.0.0.1:8000`, default config):
    - `GET /rebalance/policies/catalog` with `X-Policy-Pack-Id=dpm_standard_v1` returns:
      - `total=0`
    - `POST /rebalance/simulate` with:
      - `Idempotency-Key=manual-settlement-policy-docker`
      - `X-Policy-Pack-Id=dpm_standard_v1`
      - payload: `docs/demo/07_settlement_overdraft_block.json`
      returns `200` with `status=BLOCKED`.
  - Uvicorn runtime (`http://127.0.0.1:8004`) with:
    - `DPM_POLICY_PACKS_ENABLED=true`
    - `DPM_POLICY_PACK_CATALOG_JSON={"dpm_standard_v1":{"version":"1","settlement_policy":{"enable_settlement_awareness":true,"settlement_horizon_days":3}}}`
    validated:
    - `GET /rebalance/policies/catalog` with `X-Policy-Pack-Id=dpm_standard_v1` returns:
      - `total=1`
      - `selected_policy_pack_id=dpm_standard_v1`
      - `items[0].settlement_policy.enable_settlement_awareness=true`
      - `items[0].settlement_policy.settlement_horizon_days=3`
    - `POST /rebalance/simulate` with:
      - `Idempotency-Key=manual-settlement-policy-uvicorn`
      - `X-Policy-Pack-Id=dpm_standard_v1`
      - payload: `docs/demo/07_settlement_overdraft_block.json`
      returns `200` with `status=BLOCKED`.
- Constraint policy-pack override validation (RFC-0022 slice 8):
  - Docker runtime (`http://127.0.0.1:8000`, default config):
    - `GET /rebalance/policies/catalog` with `X-Policy-Pack-Id=dpm_standard_v1` returns:
      - `total=0`
    - `POST /rebalance/simulate` with:
      - `Idempotency-Key=manual-constraint-policy-docker`
      - `X-Policy-Pack-Id=dpm_standard_v1`
      - payload: `docs/demo/01_standard_drift.json`
      returns `200` with `status=READY`.
  - Uvicorn runtime (`http://127.0.0.1:8005`) with:
    - `DPM_POLICY_PACKS_ENABLED=true`
    - `DPM_POLICY_PACK_CATALOG_JSON={"dpm_standard_v1":{"version":"1","constraint_policy":{"single_position_max_weight":"0.25","group_constraints":{"sector:TECH":{"max_weight":"0.20"}}}}}`
    validated:
    - `GET /rebalance/policies/catalog` with `X-Policy-Pack-Id=dpm_standard_v1` returns:
      - `total=1`
      - `selected_policy_pack_id=dpm_standard_v1`
      - `items[0].constraint_policy.single_position_max_weight=0.25`
      - `items[0].constraint_policy.group_constraints["sector:TECH"].max_weight=0.20`
    - `POST /rebalance/simulate` with:
      - `Idempotency-Key=manual-constraint-policy-uvicorn`
      - `X-Policy-Pack-Id=dpm_standard_v1`
      - payload: `docs/demo/01_standard_drift.json`
      returns `200` with `status=READY`.
- Workflow policy-pack override validation (RFC-0022 slice 9):
  - Docker runtime (`http://127.0.0.1:8000`, default config):
    - `GET /rebalance/policies/catalog` with `X-Policy-Pack-Id=dpm_standard_v1` returns:
      - `total=0`
    - `POST /rebalance/simulate` with:
      - `Idempotency-Key=manual-workflow-policy-docker`
      - `X-Policy-Pack-Id=dpm_standard_v1`
      - payload: `docs/demo/01_standard_drift.json`
      returns `200` with `status=READY`.
  - Uvicorn runtime (`http://127.0.0.1:8006`) with:
    - `DPM_POLICY_PACKS_ENABLED=true`
    - `DPM_POLICY_PACK_CATALOG_JSON={"dpm_standard_v1":{"version":"1","workflow_policy":{"enable_workflow_gates":false,"workflow_requires_client_consent":true,"client_consent_already_obtained":true}}}`
    validated:
    - `GET /rebalance/policies/catalog` with `X-Policy-Pack-Id=dpm_standard_v1` returns:
      - `total=1`
      - `selected_policy_pack_id=dpm_standard_v1`
      - `items[0].workflow_policy.enable_workflow_gates=false`
      - `items[0].workflow_policy.workflow_requires_client_consent=true`
      - `items[0].workflow_policy.client_consent_already_obtained=true`
    - `POST /rebalance/simulate` with:
      - `Idempotency-Key=manual-workflow-policy-uvicorn`
      - `X-Policy-Pack-Id=dpm_standard_v1`
      - payload: `docs/demo/01_standard_drift.json`
      returns `200` with `status=READY`.
- Idempotency policy-pack override validation (RFC-0022 slice 10):
  - Docker runtime (`http://127.0.0.1:8000`, default config):
    - `POST /rebalance/simulate` repeated twice with:
      - `Idempotency-Key=manual-idem-policy-docker`
      - `X-Policy-Pack-Id=dpm_standard_v1`
      - payload: `docs/demo/01_standard_drift.json`
      returns replayed same run id:
      - `run1=rr_7f8351fa`
      - `run2=rr_7f8351fa`
  - Uvicorn runtime (`http://127.0.0.1:8007`) with:
    - `DPM_POLICY_PACKS_ENABLED=true`
    - `DPM_IDEMPOTENCY_REPLAY_ENABLED=true`
    - `DPM_POLICY_PACK_CATALOG_JSON={"dpm_standard_v1":{"version":"1","idempotency_policy":{"replay_enabled":false}}}`
    validated:
    - `POST /rebalance/simulate` repeated twice with:
      - `Idempotency-Key=manual-idem-policy-uvicorn`
      - `X-Policy-Pack-Id=dpm_standard_v1`
      - payload: `docs/demo/01_standard_drift.json`
      returns different run ids:
      - `run1=rr_ff9f058f`
      - `run2=rr_2e3b31d8`

## RFC-0025 Slice 1 Production Profile Guardrails

- Uvicorn startup validation (expected fail-fast):
  - Command:
    - `APP_PERSISTENCE_PROFILE=PRODUCTION`
    - `DPM_SUPPORTABILITY_STORE_BACKEND=IN_MEMORY`
    - `PROPOSAL_STORE_BACKEND=POSTGRES`
    - `python -m uvicorn src.api.main:app --host 127.0.0.1 --port 8050`
  - Observed:
    - startup fails with `PERSISTENCE_PROFILE_REQUIRES_DPM_POSTGRES`.

- Uvicorn startup validation (expected pass):
  - Command:
    - `APP_PERSISTENCE_PROFILE=PRODUCTION`
    - `DPM_SUPPORTABILITY_STORE_BACKEND=POSTGRES`
    - `PROPOSAL_STORE_BACKEND=POSTGRES`
    - `DPM_POLICY_PACK_CATALOG_BACKEND=POSTGRES`
    - `python -m uvicorn src.api.main:app --host 127.0.0.1 --port 8051`
  - Observed:
    - app starts normally and `/docs` responds `200`.

- Docker startup validation (expected fail-fast):
  - Command:
    - `docker run --rm -e APP_PERSISTENCE_PROFILE=PRODUCTION -e DPM_SUPPORTABILITY_STORE_BACKEND=IN_MEMORY -e PROPOSAL_STORE_BACKEND=POSTGRES lotus-advise:latest`
  - Observed:
    - container exits at startup with `PERSISTENCE_PROFILE_REQUIRES_DPM_POSTGRES`.

## RFC-0025 Slice 2 CI and Production Profile Smoke

- CI workflow adds production-profile smoke job with:
  - `APP_PERSISTENCE_PROFILE=PRODUCTION`
  - Postgres-backed lotus-manage/advisory/policy-pack configuration
  - migration application via `python scripts/postgres_migrate.py --target all`
  - startup verification of `/docs`, `/rebalance/policies/effective`, and `/rebalance/proposals?limit=1`

- Local equivalent smoke command sequence:
  - `python scripts/postgres_migrate.py --target all`
  - `APP_PERSISTENCE_PROFILE=PRODUCTION DPM_SUPPORTABILITY_STORE_BACKEND=POSTGRES PROPOSAL_STORE_BACKEND=POSTGRES DPM_POLICY_PACKS_ENABLED=true DPM_POLICY_PACK_CATALOG_BACKEND=POSTGRES python -m uvicorn src.api.main:app --host 127.0.0.1 --port 8052`
  - `curl http://127.0.0.1:8052/docs`
  - `curl http://127.0.0.1:8052/rebalance/policies/effective`
  - `curl "http://127.0.0.1:8052/rebalance/proposals?limit=1"`

## RFC-0025 Slice 3 Negative Guardrail Validation

- Production-profile negative startup checks validated by CI job `production-profile-guardrail-negatives`:
  - lotus-manage backend mismatch (`DPM_SUPPORTABILITY_STORE_BACKEND=IN_MEMORY`) fails startup with:
    - `PERSISTENCE_PROFILE_REQUIRES_DPM_POSTGRES`
  - Advisory backend mismatch (`PROPOSAL_STORE_BACKEND=IN_MEMORY`) fails startup with:
    - `PERSISTENCE_PROFILE_REQUIRES_ADVISORY_POSTGRES`
  - Policy-pack backend mismatch (`DPM_POLICY_PACKS_ENABLED=true`, `DPM_POLICY_PACK_CATALOG_BACKEND=ENV_JSON`) fails startup with:
    - `PERSISTENCE_PROFILE_REQUIRES_POLICY_PACK_POSTGRES`

## RFC-0025 Slice 4 Cutover Contract and Closure

- Production cutover contract CLI added:
  - `python scripts/production_cutover_check.py --check-migrations`
  - validates:
    - `APP_PERSISTENCE_PROFILE=PRODUCTION`
    - production backend/DSN guardrails
    - `schema_migrations` contains all checked-in `dpm` and `proposals` migration versions.

- Production compose override added:
  - `docker-compose --profile postgres -f docker-compose.yml -f docker-compose.production.yml up -d --build`
  - enforces production profile and postgres-only persistence env defaults.

- RFC-0025 DSN guardrail negatives are now validated in CI (`production-profile-guardrail-negatives`):
  - missing lotus-manage Postgres DSN -> `PERSISTENCE_PROFILE_REQUIRES_DPM_POSTGRES_DSN`
  - missing advisory Postgres DSN -> `PERSISTENCE_PROFILE_REQUIRES_ADVISORY_POSTGRES_DSN`
  - missing policy-pack Postgres DSN with policy packs enabled -> `PERSISTENCE_PROFILE_REQUIRES_POLICY_PACK_POSTGRES_DSN`

- Nightly/full Postgres suite added (`.github/workflows/nightly-postgres-full.yml`):
  - scheduled/manual workflow with production profile + Postgres service,
  - applies migrations,
  - validates production cutover contract,
  - runs Postgres integration tests,
  - runs live demo pack against Postgres-backed API.

- RFC-0025 local-default continuation:
  - `docker-compose.yml` defaults now start Postgres-backed runtime (no profile required).
  - legacy runtime backends remain available for transition/testing but emit `DeprecationWarning`.

