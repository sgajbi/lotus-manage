# lotus-manage Quality Scorecard

- Generated at: `2026-08-20T17:55:26+00:00`

- Baseline source snapshot: `58cf058954a35c1e73450aabe5d7ae095a20d497`

- Report source snapshot: `7bd5e1d4+worktree`

- Purpose: make enterprise-readiness progress measurable without pretending report-only baselines are mature enforcement gates.

| Area | Status | Evidence / next gate |
| --- | --- | --- |
| Lint and formatting | Active gate | `make check` runs Ruff check and format check. |
| Type checking | Active gate | `make check` runs mypy over source files. |
| Unit tests | Active gate | `make check` runs `tests/unit`. |
| OpenAPI governance | Active gate | `scripts/openapi_quality_gate.py`. |
| API vocabulary | Active gate | `scripts/api_vocabulary_inventory.py --validate-only`. |
| Service boundary | Active gate | `scripts/service_boundary_gate.py`. |
| Router infrastructure imports | Active gate | `scripts/router_infrastructure_gate.py`. |
| OpenAPI 4xx/5xx response markers | Baseline debt | Current missing markers: 1. |
| Complexity | Active source C gate | `make complexity-gate` blocks Radon C-or-worse source functions; `quality/complexity_report.md` keeps broader source/test metrics report-only. |
| Duplicate implementation hotspots | Active exact-duplicate non-regression gate | `make duplicate-implementation-gate` blocks newly introduced exact non-trivial Python function-body duplicates; `quality/duplicate_implementation_baseline.json` governs current accepted groups. |
| Quality report freshness | Active gate | `make quality-report-gate` blocks stale checked-in quality reports while ignoring volatile report provenance. |
| Workflow policy | Active gate | `make workflow-policy-gate` blocks unpinned action refs, permission creep, blocking quality-report drift, raw blocking-workflow pytest shortcuts, coverage-gate drift, and PR evidence drift. |
| Local CI parity | Active gate | `make check`, `make ci`, and `make ci-local` share `make static-quality-gates` so local proof cannot omit active static gates. |
| Coverage gate parity | Active gate | `scripts/coverage_gate.py` is the shared local and GitHub combined coverage gate. |
| Test-family proof breadth | Active gate | `make test-family-inventory` checks `quality/test_family_inventory_baseline.json` and blocks loss of API/runtime, contract/governance, observability/security, domain/lifecycle/methodology, and integration/runtime proof-family file counts. |
| Dead code | Active gate | `make dead-code-gate` runs vulture over `src` and `tests`; baseline workflow still captures expanded output. |
| Dependency architecture | Active gate | `make architecture-gate` and `make dependency-hygiene-gate` run import-linter and deptry. |
| Security depth | Active project dependency gate | `make security-audit` runs high-severity Bandit over `src` plus project-scoped `python -m pip_audit .`; `quality-baseline.yml` captures the same scanner family as report-only evidence. |
| Documentation coverage | Partially active | Docs current-state tests exist; add docs-gap scoring later. |
| Observability | Partially active | Observability contract validator exists; add runtime posture scoring later. |
| Demo certification | Manual/report-only live evidence | `make demo-certify` certifies canonical live API demo proof and writes JSON evidence; `demo-certification.yml` is manual, while `quality-baseline.yml` keeps deterministic command-contract tests report-only until CI has a stable canonical stack lane. |

## Progressive Gate Policy

| Phase | Meaning | Current posture |
| --- | --- | --- |
| 1 - baseline/report-only | Measure current posture without failing builds. | Active for refactor health and baseline report. |
| 2 - fail new regressions | Block newly introduced violations once the detector is stable. | Active for existing repo-native gates; planned for richer quality tools. |
| 3 - enforce thresholds | Require agreed numeric thresholds. | Not active for new quality tools yet. |
| 4 - enterprise-readiness gates | Block release on full readiness posture. | Target state, not yet complete. |
