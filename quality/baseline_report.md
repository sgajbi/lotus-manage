# lotus-manage Baseline Quality Report

- Generated at: `2026-06-02T01:04:15+00:00`

- Baseline commit: `c6f49d9`

- Mode: report-only baseline. This records current posture; it does not enforce thresholds by itself.

## Current Code Size

| Metric | Value |
| --- | --- |
| Python files | 769 |
| Total Python LOC | 147699 |
| Test functions | 1900 |
| Service boundary findings | 0 |
| Router infrastructure imports | 18 |

## Current OpenAPI Completeness

| Metric | Value |
| --- | --- |
| Operations | 135 |
| Missing summary | 0 |
| Missing description | 0 |
| Missing tags | 0 |
| Missing 4xx/5xx response | 3 |
| Missing examples marker | 0 |

## Report-Only Coverage Map

| Quality area | Current evidence | Gate phase |
| --- | --- | --- |
| Code size | `scripts/engineering_health_report.py` | 1 - baseline |
| Largest files/functions | `quality/refactor_health_report.md` | 1 - baseline |
| OpenAPI completeness | `scripts/openapi_quality_gate.py` plus this report | 2 - active/new-regression |
| Service boundary leakage | service leakage scan plus this report | 2 - active/new-regression |
| Router infrastructure imports | reported as known baseline debt | 1 - baseline |
| Complexity/maintainability | `quality/complexity_report.md` | 1 - baseline |
| Dead code | not instrumented yet | planned |
| Dependency hygiene | `pip check`/security audit in repo gates; richer deptry planned | 2 - active/new-regression |
| Security | `make security-audit`; richer bandit/pip-audit scorecard planned | 2 - active/new-regression |
| Documentation gaps | current docs tests plus planned docs scorecard | planned |
| Observability gaps | `scripts/validate_observability_contracts.py`; richer runtime gap report planned | 2 - active/new-regression |

## Notes

- Future slices should add optional-tool measurements without converting unstable baselines into blocking gates prematurely.
