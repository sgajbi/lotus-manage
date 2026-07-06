# Manage Scripts

Scripts in this folder are repo-native automation entry points used by Make targets, tests, local
runtime validation, and release evidence.

| Script family | Purpose | Common command |
| --- | --- | --- |
| `validate_*_contracts.py` | Domain-product, trust-telemetry, live API, and observability contract validation. | `make mesh-contract-validate` or the focused Make target. |
| `*_gate.py` | API vocabulary, OpenAPI, service-boundary, router, workflow, duplicate, and coverage gates. | `make static-quality-gates` |
| `generate_rfc*_evidence.py` | RFC evidence generation for proof packs, waves, and outcome reviews. | Run only with current RFC/runbook context. |
| `clean_generated_artifacts.py` | Removes ignored generated caches, coverage files, build output, logs, and `output/` evidence. | `make clean` |
| `docker_image_evidence.py` | Writes Docker release manifest, image inspect, SBOM/scan/signature status, and provenance summary evidence. | `make docker-image-evidence` |
| `postgres_migrate.py` | Migration smoke/apply helper. | `make migration-smoke` or `make migration-apply` |
| `Start-CanonicalManage.ps1` | Canonical local Manage service startup helper. | `make run-canonical` |

Prefer the Make target that wraps a script because CI uses those targets as the stable contract.
When changing a script, update the Make target, README/docs/runbook references, and focused tests
that prove its expected output or failure mode.

`make clean` removes untracked generated `output/` evidence and preserves Git-tracked evidence
files. Preserve any issue, PR, or audit evidence by committing the authored source or copying it to
the governed location before cleaning.
