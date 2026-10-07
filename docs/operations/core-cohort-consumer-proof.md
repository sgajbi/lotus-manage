# Core Cohort Consumer Proof

## Scope

This opt-in regression exercises actual Core PostgreSQL cohort selection through registered
Manage wave preview/create APIs. Core fixtures use its production DTO and typed upsert service;
this is not proof of the complete upstream ingestion pipeline.

The test covers active MODEL_A → suspended/empty → reassigned MODEL_B, effective-date controls,
tenant refusal, idempotent replay, exactly two persisted waves, and unchanged lineage after an API
restart. It does not certify composite-universe authority, financial simulation, trade release,
booking, enterprise IAM, capacity, or production readiness. The wider integration backlog remains
tracked in [#715](https://github.com/sgajbi/lotus-manage/issues/715).

## Prerequisites

- An approved isolated runtime lease, unused loopback ports, and a unique resource inventory.
  Never use a shared Core database, reserved product runtime, or another agent's checkout.
- Manage's installed development environment and a separate Core interpreter satisfying Core's
  development dependencies. Verify imports below; do not install Core into Manage's environment.
  Fresh-machine dependencies remain governed by the respective repository setup instructions.
- Git, Docker with the pinned PostgreSQL image already available, and PostgreSQL `CREATEDB`
  permission. The existing Manage harness creates and removes its own UUID database.
- `CORE_REPO`: source-object location; `CORE_PYTHON`: absolute Core interpreter path;
  `PROOF_ROOT`: new absolute evidence directory outside all checkouts. No new Git checkout is needed.

| Pin | Required value |
| --- | --- |
| Core revision | `5dc98e084be70821544c4d2d1de2203ddccc4260` |
| Core tree | `b94956cdead24219d267dea3cfaacdbe8bfb4883` |
| Export SHA256 | `edb6296e92b77511918afa21204791affe3cbcf3345de4d4903ff5a28c0af59a` |
| PostgreSQL image | `postgres:17.6@sha256:00bc86618629af00d2937fdc5a5d63db3ff8450acf52f0636ec813c7f4902929` |

The fixture intentionally pins one accepted producer revision. Updating it requires source review
and renewed consumer proof, not substituting mutable `main`. The export uses explicit
`core.autocrlf=true` to reproduce the accepted archive bytes independently of local Git settings.
All 4,974 extracted files must match the archive, with no additional files. Supplementary producer
blob checks compare canonical LF bytes.

## Prepare Source And Resources

Working directory: `lotus-manage`. Set the three caller-resolved prerequisites above before running
the appropriate block. The Windows procedure was exercised; POSIX execution remains an explicit
verification requirement for that environment. Every nonzero command is a setup failure, not proof.

### PowerShell

```powershell
$ErrorActionPreference = 'Stop'
$CoreSha = '5dc98e084be70821544c4d2d1de2203ddccc4260'
$Lease = [guid]::NewGuid().ToString('N')
$Db = "manage_actual_core_715_$Lease"
$Container = "manage-core-cohort-$Lease"
New-Item -ItemType Directory $PROOF_ROOT -ErrorAction Stop | Out-Null
New-Item -ItemType Directory "$PROOF_ROOT/source" -ErrorAction Stop | Out-Null
git -C $CORE_REPO -c core.autocrlf=true archive --format=tar --output="$PROOF_ROOT/core.tar" $CoreSha
if ($LASTEXITCODE) { throw 'Core archive failed' }
python -m tarfile -e "$PROOF_ROOT/core.tar" "$PROOF_ROOT/source"
if ($LASTEXITCODE) { throw 'Unicode-safe archive extraction failed' }
$env:DPM_ACTUAL_CORE_SOURCE_DIR = "$PROOF_ROOT/source"
$env:DPM_ACTUAL_CORE_ARCHIVE = "$PROOF_ROOT/core.tar"
$env:DPM_ACTUAL_CORE_PYTHON = $CORE_PYTHON
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:ENVIRONMENT = 'test'
$env:ENTERPRISE_ENFORCE_AUTHZ = 'false'
```

### POSIX Shell

```bash
set -eu
CoreSha=5dc98e084be70821544c4d2d1de2203ddccc4260
Lease=$(python -c 'import uuid; print(uuid.uuid4().hex)')
Db="manage_actual_core_715_$Lease"
Container="manage-core-cohort-$Lease"
mkdir -p "$PROOF_ROOT"
mkdir "$PROOF_ROOT/source"
git -C "$CORE_REPO" -c core.autocrlf=true archive --format=tar --output="$PROOF_ROOT/core.tar" "$CoreSha"
python -m tarfile -e "$PROOF_ROOT/core.tar" "$PROOF_ROOT/source"
export DPM_ACTUAL_CORE_SOURCE_DIR="$PROOF_ROOT/source"
export DPM_ACTUAL_CORE_ARCHIVE="$PROOF_ROOT/core.tar"
export DPM_ACTUAL_CORE_PYTHON="$CORE_PYTHON"
export PYTHONDONTWRITEBYTECODE=1 ENVIRONMENT=test ENTERPRISE_ENFORCE_AUTHZ=false
```

From Manage, with its environment activated, validate the entire extracted source before starting
anything. This command is identical on both systems:

```text
python -c "import os; from pathlib import Path; from tests.integration.dpm.actual_core_runtime import _verify_source_archive; _verify_source_archive(Path(os.environ['DPM_ACTUAL_CORE_SOURCE_DIR']).resolve(), Path(os.environ['DPM_ACTUAL_CORE_ARCHIVE']).resolve())"
```

Select approved unused `PG_PORT` and `QCP_PORT`; do not evict existing listeners. Record the container
ID, image ID/digest, labels, anonymous volume, process IDs, source cwd, and ports in the evidence
inventory. Start only this PostgreSQL container with `--pull=never`, loopback publication, and owner
and Core-revision labels. Once the lease variables and approved ports are set:

```powershell
docker run -d --pull=never --name $Container --label "lotus.proof.owner=$Lease" --label "lotus.proof.core_revision=$CoreSha" -p "127.0.0.1:${PG_PORT}:5432" -e POSTGRES_USER=cohort -e POSTGRES_PASSWORD=isolated-cohort-proof -e "POSTGRES_DB=$Db" postgres:17.6@sha256:00bc86618629af00d2937fdc5a5d63db3ff8450acf52f0636ec813c7f4902929
if ($LASTEXITCODE) { throw 'Owned PostgreSQL startup failed' }
docker exec $Container pg_isready -U cohort -d $Db
if ($LASTEXITCODE) { throw 'PostgreSQL not ready; do not migrate yet' }
docker exec $Container psql -U cohort -d $Db -v ON_ERROR_STOP=1 -c "COMMENT ON DATABASE $Db IS 'lotus-manage:715:${Db}:$CoreSha';"
if ($LASTEXITCODE) { throw 'Owner marker failed' }
```

```bash
docker run -d --pull=never --name "$Container" --label "lotus.proof.owner=$Lease" --label "lotus.proof.core_revision=$CoreSha" -p "127.0.0.1:${PG_PORT}:5432" -e POSTGRES_USER=cohort -e POSTGRES_PASSWORD=isolated-cohort-proof -e "POSTGRES_DB=$Db" postgres:17.6@sha256:00bc86618629af00d2937fdc5a5d63db3ff8450acf52f0636ec813c7f4902929
docker exec "$Container" pg_isready -U cohort -d "$Db"
docker exec "$Container" psql -U cohort -d "$Db" -v ON_ERROR_STOP=1 -c "COMMENT ON DATABASE $Db IS 'lotus-manage:715:${Db}:$CoreSha';"
```

The password is exclusively for this disposable loopback proof. A failed readiness probe requires
successful readiness verification before proceeding. Use only the generated database identifier;
the fixture verifies its `manage_actual_core_715_[0-9a-f]{32}` shape and source-bound owner comment
before writes. No shared database is eligible.

## Start Core And Run The Test

Set these variables in the proof process; use `$env:NAME = value` in PowerShell or
`export NAME=value` in POSIX shells. Paths are caller-resolved, not repository defaults.

| Variable | Value |
| --- | --- |
| `HOST_DATABASE_URL`, `DATABASE_URL` | `postgresql://cohort:isolated-cohort-proof@127.0.0.1:PG_PORT/DB` |
| `PYTHONPATH` | Extracted `source/src/libs/portfolio-common` |
| `LOTUS_GIT_COMMIT_SHA` | Pinned Core revision |
| `DPM_ACTUAL_CORE_URL` | `http://127.0.0.1:QCP_PORT` |
| `DPM_ACTUAL_CORE_DSN`, `DPM_POSTGRES_INTEGRATION_DSN` | The same isolated database URL |
| `DPM_ACTUAL_CORE_REQUIRED`, `DPM_POSTGRES_INTEGRATION_REQUIRED` | `1` |

Working directory: extracted Core `source`. Using the Core interpreter, first verify that
`portfolio_common`, the reference writer, and QCP `main` module paths resolve inside this directory,
and that `app.dependency_overrides` is empty. With the Core environment activated, the verification
command is identical on both systems:

```text
python -c "from pathlib import Path; import portfolio_common; from src.services.ingestion_service.app.services import reference_data_ingestion_service as writer; from src.services.query_control_plane_service.app import main as qcp; modules=[portfolio_common,writer,qcp]; assert not qcp.app.dependency_overrides; assert all(Path(m.__file__).resolve().is_relative_to(Path.cwd()) for m in modules); [print(m.__name__,m.__file__) for m in modules]"
```

Then migrate and start the registered QCP app:

| Operation | PowerShell | POSIX shell |
| --- | --- | --- |
| Migrate | `& $CORE_PYTHON -m alembic upgrade head` | `"$CORE_PYTHON" -m alembic upgrade head` |
| Serve QCP | `& $CORE_PYTHON -m uvicorn src.services.query_control_plane_service.app.main:app --host 127.0.0.1 --port $QCP_PORT --no-access-log` | `"$CORE_PYTHON" -m uvicorn src.services.query_control_plane_service.app.main:app --host 127.0.0.1 --port "$QCP_PORT" --no-access-log` |

If launched in the background on Windows, use `Start-Process -WindowStyle Hidden -PassThru`, explicit
`-WorkingDirectory`, and separate retained stdout/stderr logs. Retain the launcher PID and verify
its listener descendant. On POSIX, retain the exact background PID and logs. Do not locate a process
for teardown merely by executable name.

Require `/health/ready` 200, the expected revision, and database health before running the test.
The local Core authz setting is not enterprise identity proof. Manage's existing native harness
enables its own authz and uses supported test headers.

Working directory: `lotus-manage`, Manage environment activated. Run the repository-native selected
integration lane, with resource warnings strict and JUnit outside the checkout:

```powershell
make test-integration "INTEGRATION_TESTS=tests/integration/dpm/waves/test_actual_core_cohort_consumption.py -q -W error::ResourceWarning -W error::pytest.PytestUnraisableExceptionWarning --junitxml=`"$PROOF_ROOT/cohort.junit.xml`""
if ($LASTEXITCODE) { throw 'Cohort proof failed; preserve diagnostics before fix-forward' }
```

```bash
make test-integration "INTEGRATION_TESTS=tests/integration/dpm/waves/test_actual_core_cohort_consumption.py -q -W error::ResourceWarning -W error::pytest.PytestUnraisableExceptionWarning --junitxml=\"$PROOF_ROOT/cohort.junit.xml\""
```

Acceptance requires successful exit, one passed test, no skips, and no resource-cleanup warnings.
Missing prerequisite flags must not turn an unexecuted producer proof into acceptance. Both the
direct Core query and Manage selector must use identical tenant, date, model, booking center, and
`include_inactive_mandates=false`. Effective dates govern visibility; `observed_at` is not historical
membership authority. Preserve every failed JUnit separately before any reviewed fix-forward.

## Evidence And Teardown

Retain archive and complete `git ls-tree -r --full-tree` source manifest, digests, source-import
verification, runtime inventory, migration/QCP logs, JUnit, and final test-file hashes. Core's current
cohort has no `source_batch_fingerprint`; the test explicitly preserves that absence. Snapshot and
binding identity assertions are not positive producer content-digest verification.

Verify that the Manage harness removed its generated database, API processes, and listeners. Stop
only the verified QCP launcher/listener process chain. Verify the captured container ID and labels,
then run `docker stop --timeout 10 CONTAINER` and `docker rm -v CONTAINER`. Confirm its exact anonymous
volume, both approved listeners, and owned processes are absent. No broad stack teardown, foreign
port termination, or recursive checkout cleanup is permitted. Retain evidence for review.

This is a local diagnostic acceptance procedure. Governed CI/review/merge, wiki publication, and
exact-main validation remain separate delivery gates.
