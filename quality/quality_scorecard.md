# lotus-manage Quality Scorecard

- Generated at: `2026-06-02T04:55:04+00:00`

- Current ref: `c65fc5a`

- Purpose: make enterprise-readiness progress measurable without pretending report-only baselines are mature enforcement gates.

| Area | Status | Evidence / next gate |
| --- | --- | --- |
| Lint and formatting | Active gate | `make check` runs Ruff check and format check. |
| Type checking | Active gate | `make check` runs mypy over source files. |
| Unit tests | Active gate | `make check` runs `tests/unit`. |
| OpenAPI governance | Active gate | `scripts/openapi_quality_gate.py`. |
| API vocabulary | Active gate | `scripts/api_vocabulary_inventory.py --validate-only`. |
| Service boundary leakage | Report plus focused scans | Current service boundary findings: 0. |
| Router infrastructure imports | Baseline debt | Current router infra imports: 18. |
| OpenAPI 4xx/5xx response markers | Baseline debt | Current missing markers: 3. |
| Complexity | Report-only baseline | `quality/complexity_report.md`; add thresholds after baseline review. |
| Dead code | Not yet instrumented | Add vulture report-only baseline before thresholds. |
| Dependency architecture | Not yet instrumented | Add import-linter/deptry report-only baseline before thresholds. |
| Security depth | Partially active | Security audit is active; add bandit/pip-audit detail scorecard. |
| Documentation coverage | Partially active | Docs current-state tests exist; add docs-gap scoring later. |
| Observability | Partially active | Observability contract validator exists; add runtime posture scoring later. |

## Progressive Gate Policy

| Phase | Meaning | Current posture |
| --- | --- | --- |
| 1 - baseline/report-only | Measure current posture without failing builds. | Active for refactor health and baseline report. |
| 2 - fail new regressions | Block newly introduced violations once the detector is stable. | Active for existing repo-native gates; planned for richer quality tools. |
| 3 - enforce thresholds | Require agreed numeric thresholds. | Not active for new quality tools yet. |
| 4 - enterprise-readiness gates | Block release on full readiness posture. | Target state, not yet complete. |
