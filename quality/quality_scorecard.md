# lotus-manage Quality Scorecard

- Generated at: `2026-06-13T05:00:35+00:00`

- Current ref: `3f1a3509`

- Purpose: make enterprise-readiness progress measurable without pretending report-only baselines are mature enforcement gates.

| Area | Status | Evidence / next gate |
| --- | --- | --- |
| Lint and formatting | Active gate | `make check` runs Ruff check and format check. |
| Type checking | Active gate | `make check` runs mypy over source files. |
| Unit tests | Active gate | `make check` runs `tests/unit`. |
| OpenAPI governance | Active gate | `scripts/openapi_quality_gate.py`. |
| API vocabulary | Active gate | `scripts/api_vocabulary_inventory.py --validate-only`. |
| Service boundary | Active gate | `scripts/service_boundary_gate.py`. |
| Router infrastructure imports | Baseline debt | Current router infra imports: 0. |
| OpenAPI 4xx/5xx response markers | Baseline debt | Current missing markers: 0. |
| Complexity | Report-only baseline | `quality/complexity_report.md`; add thresholds after baseline review. |
| Dead code | Report-only baseline | `quality-baseline.yml` captures `vulture` output; add thresholds after baseline review. |
| Dependency architecture | Report-only baseline | `quality-baseline.yml` captures `importlinter` and `deptry`; add thresholds after baseline review. |
| Security depth | Partially active | `make security-audit` is active; `bandit` and `pip-audit` are report-only in `quality-baseline.yml`. |
| Documentation coverage | Partially active | Docs current-state tests exist; add docs-gap scoring later. |
| Observability | Partially active | Observability contract validator exists; add runtime posture scoring later. |

## Progressive Gate Policy

| Phase | Meaning | Current posture |
| --- | --- | --- |
| 1 - baseline/report-only | Measure current posture without failing builds. | Active for refactor health and baseline report. |
| 2 - fail new regressions | Block newly introduced violations once the detector is stable. | Active for existing repo-native gates; planned for richer quality tools. |
| 3 - enforce thresholds | Require agreed numeric thresholds. | Not active for new quality tools yet. |
| 4 - enterprise-readiness gates | Block release on full readiness posture. | Target state, not yet complete. |
