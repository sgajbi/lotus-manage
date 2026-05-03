# RFC-0040 Slice 9 Implementation Proof Evidence

This slice proves RFC-0040 manage behavior through a canonical local HTTP runtime backed by
Postgres. It also records the critical review finding and fix-forward work completed before the
slice was accepted.

## Evidence Path

Machine-readable evidence was generated under:

`output/rfc0040-proof/20260503-135112`

The evidence directory is intentionally under ignored `output/` because it is reproducible runtime
evidence rather than source. The committed source of truth is the generator script plus this
evidence summary.

## Runtime

Canonical startup command:

```bash
scripts\Start-CanonicalManage.ps1 -Port 8023 -ListenHost 127.0.0.1 -PostgresContainerName lotus-manage-postgres-rfc0040 -PostgresHostPort 55440
```

Evidence generation command:

```bash
python scripts\generate_rfc0040_proof_pack_evidence.py --base-url http://127.0.0.1:8023
```

The startup path applied DPM Postgres migrations before the service became ready.

## Captured Files

| File | Purpose |
| --- | --- |
| `00-health-ready.json` | live readiness probe |
| `01-direct-run-simulate.json` | source rebalance run response |
| `02-direct-run-proof-pack-generation.json` | direct-run proof-pack generation response |
| `03-direct-run-proof-pack-detail.json` | persisted proof-pack detail lookup |
| `04-direct-run-summary.md` | deterministic Markdown summary |
| `05-direct-run-report-input.json` | report materialization handoff payload |
| `06-direct-run-ai-evidence-input.json` | bounded AI evidence handoff payload |
| `07-selected-alternative-generation.json` | construction alternative set response |
| `08-selected-alternative-selection.json` | selected-alternative audit decision |
| `09-selected-alternative-proof-pack-generation.json` | selected-alternative proof-pack response |
| `10-missing-mandate-proof-pack-generation.json` | blocked missing-mandate proof-pack response |
| `manifest.json` | scenario roll-up, content hashes, and validation results |

## Scenario Results

| Scenario | Proof pack | Status | Key evidence |
| --- | --- | --- | --- |
| Direct rebalance run | `dpp_d1210dac` | `DEGRADED` | JSON/detail/Markdown/report-input/AI-evidence passed; report and AI sections `READY`; missing domain-authority sections are truthfully `DEGRADED`. |
| Selected alternative | `dpp_cas_3258b446f51b_alt_heuristic_explainable` | `DEGRADED` | Selected alternative, before/after state, trade intents, lineage, source readiness, report, and AI sections are `READY`; risk/performance/scenario/tax/sustainability authority sections remain truthfully `DEGRADED`. |
| Missing mandate | `dpp_7142c8e3` | `BLOCKED` | `mandate_context` is `BLOCKED` and reason code `DPM_PROOF_PACK_MANDATE_ID_MISSING` is present while other available evidence remains visible. |

## Critical Review Finding

The first clean canonical proof attempt found that selected-alternative proof packs could prove the
selected-alternative section, but run-derived sections were `BLOCKED`. The root cause was not the
proof-pack builder: construction alternatives carried `rebalance_run_id`, but construction
generation did not record the generated rebalance result in the manage run support repository.

Fix-forward:

1. `src/api/services/construction_service.py` now records construction-generated rebalance runs
   through `DpmRunSupportService` using deterministic construction request hashes.
2. `src/api/routers/construction.py` injects the governed run support service into construction
   generation.
3. `tests/unit/dpm/api/test_proof_pack_api.py` now asserts selected-alternative proof packs carry
   a run id, rebalance-run source hash, and `READY` run-derived evidence.
4. The canonical proof was rerun and selected-alternative proof packs now hydrate run-backed
   sections from persisted manage truth.

## Guardrails Proved

1. Proof-pack content hashes are present and stable in captured responses.
2. Markdown is generated from persisted proof-pack truth.
3. Report input ties back to the source proof-pack content hash.
4. AI evidence ties back to the source proof-pack content hash.
5. AI evidence contains forbidden actions and the generator verifies forbidden field names are
   absent from the emitted evidence payload.
6. Missing mandate identity blocks promotion without hiding available run evidence.

## Validation Commands

```bash
python -m pytest tests\unit\dpm\api\test_proof_pack_api.py tests\unit\test_rfc0040_evidence_script.py -q
python -m mypy src\api\services\construction_service.py src\api\routers\construction.py scripts\generate_rfc0040_proof_pack_evidence.py --config-file mypy.ini
python -m ruff check src\api\services\construction_service.py src\api\routers\construction.py tests\unit\dpm\api\test_proof_pack_api.py scripts\generate_rfc0040_proof_pack_evidence.py tests\unit\test_rfc0040_evidence_script.py
python -m ruff format --check src\api\services\construction_service.py src\api\routers\construction.py tests\unit\dpm\api\test_proof_pack_api.py scripts\generate_rfc0040_proof_pack_evidence.py tests\unit\test_rfc0040_evidence_script.py
```

Results:

1. focused proof-pack and evidence-generator tests passed,
2. mypy passed,
3. ruff passed,
4. format check passed,
5. canonical live evidence generator passed after fix-forward rerun.

## No Supported-Feature Promotion

Slice 9 proves manage-owned backend proof-pack behavior. RFC-0040 remains in progress until final
hardening, full gate review, PR/CI completion, merge, and wiki publication are complete. Gateway
composition, Workbench product UX, report materialization, and AI memo generation are not claimed
as supported by this slice.
