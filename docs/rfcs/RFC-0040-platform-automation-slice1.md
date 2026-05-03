# RFC-0040 Slice 1 Platform Automation Assessment

This document records the Slice 1 platform automation and scaffolding review for RFC-0040. It is
the manage-side evidence pointer for the reusable platform change made in `lotus-platform`.

## Slice 1 Result

| Area | Classification | Evidence | Decision |
| --- | --- | --- | --- |
| API certification pattern | already covered | `lotus-platform/automation/New-Lotus-Service.ps1`, scaffolded `scripts/openapi_quality_gate.py`, `docs/operations/api-certification.md`, and `lotus-manage/scripts/openapi_quality_gate.py` | Reuse existing gates. Proof-pack endpoints must enter manage OpenAPI certification in Slice 6. |
| Swagger/OpenAPI quality | already covered | Platform scaffold emits summary, description, response examples, product-safe error examples, and OpenAPI tests. Manage already has `scripts/openapi_quality_gate.py`. | No platform change required. |
| Health, liveness, readiness, metadata | already covered | Platform scaffold emits health/readiness/metadata endpoints and tests. | No platform change required. |
| Observability, metrics, structured logging, correlation, trace | already covered | Platform scaffold emits correlation/trace middleware, structured JSON application events, observability docs, and bounded no-sensitive-content guards. | No platform change required for RFC-0040 Slice 1. |
| Problem-details-style error handling | already covered | Platform scaffold emits `ProblemDetails`, validation/unhandled exception handlers, and product-safe error tests. | Reuse in future services; manage proof-pack API errors follow existing manage error patterns in Slice 6. |
| Unit/integration/e2e/coverage/security CI defaults | already covered | Platform scaffold emits Makefile targets, CI templates, coverage gate, security audit, and Docker baseline. | No platform change required. |
| README/wiki/RFC documentation scaffolding | already covered | Platform scaffold emits repo README, wiki home, operations docs, repo context, and `AGENTS.md`. | No platform change required. |
| Supported-feature promotion guard | already covered | Platform scaffold emits `supported-features/supported-features.json` and `scripts/supported_features_gate.py`; manage wiki already separates target-state features from supported features. | Reuse policy. Proof-pack support remains unpromoted until Slice 11. |
| Evidence-output manifest conventions | fixed | `lotus-platform` branch `feat/rfc0040-evidence-manifest-scaffold`, commit `4679b07 feat: scaffold rfc evidence manifests` | Added `evidence/rfc-implementation/evidence-manifest.template.json` to the platform service scaffold and tests/docs so future apps start with comparable RFC evidence manifests. |
| Governance hooks for no-alias, API vocabulary, mesh/trust telemetry, wiki sync | already covered | Manage has no-alias, OpenAPI, API vocabulary, mesh contract validation, and wiki sync expectations; platform owns shared validators and wiki publication automation. | Reuse existing gates; no manage-local replacement. |
| Heartbeat/background-run visibility | already covered for advisory use | `lotus-platform/automation/Run-Heartbeat.ps1`, `Start-Background-Run.ps1`, `Check-Background-Runs.ps1`, and governed ledger docs | Use when long checks, PR monitoring, or cross-repo visibility benefit from advisory evidence. Do not treat heartbeat as source truth. |

## Platform Change

Repository: `lotus-platform`

Branch: `feat/rfc0040-evidence-manifest-scaffold`

Commit: `4679b07 feat: scaffold rfc evidence manifests`

Files changed:

1. `automation/New-Lotus-Service.ps1`
2. `tests/unit/test_repository_hygiene_scaffold_contract.py`
3. `automation/README.md`
4. `platform-standards/README.md`

What changed:

1. New scaffolded services now receive
   `evidence/rfc-implementation/evidence-manifest.template.json`.
2. The manifest template captures repository, RFC id, slice id, generated timestamp, branch,
   commit SHA, PR reference, validation commands, artifacts, cross-app evidence, review notes, and
   sensitive-content policy.
3. The scaffold contract test proves the generated repo includes the template and key fields.
4. Platform automation and standards docs now describe the evidence manifest template.

Validation:

1. `git diff --check`
2. `rg -n "[^\x00-\x7F]" automation/New-Lotus-Service.ps1 tests/unit/test_repository_hygiene_scaffold_contract.py automation/README.md platform-standards/README.md`
3. `python -m pytest tests/unit/test_repository_hygiene_scaffold_contract.py -q`

Result:

1. `git diff --check` passed.
2. Non-ASCII scan found no matches.
3. Scaffold contract test passed: `2 passed in 1.22s`.

## Manage-Side Decision

No manage-local scaffold workaround is introduced in Slice 1.

RFC-0040 implementation evidence under `lotus-manage/output/rfc0040-proof/<timestamp>/` should use
the same manifest shape when proof artifacts are generated in Slice 9. Until then, this slice only
records the reusable platform convention and does not claim proof-pack implementation support.

## Heartbeat Decision

Heartbeat is not required for this completed local Slice 1 proof because the validation was short
and foregrounded. Heartbeat remains appropriate later when:

1. cross-repo PRs are open and checks need advisory visibility,
2. long-running background validation is started through platform automation,
3. wiki publication, PR state, or background-run evidence needs a single attention snapshot.
