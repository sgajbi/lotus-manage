# lotus-manage Baseline Quality Report

- Generated at: `2026-06-04T06:45:02+00:00`

- Baseline commit: `68e0309`

- Mode: report-only baseline. This records current posture; it does not enforce thresholds by itself.

## Current Code Size

| Metric | Value |
| --- | --- |
| Python files | 783 |
| Total Python LOC | 150279 |
| Test functions | 1978 |
| Service boundary findings | 0 |
| Router infrastructure imports | 0 |

## Current OpenAPI Completeness

| Metric | Value |
| --- | --- |
| Operations | 135 |
| Missing summary | 0 |
| Missing description | 0 |
| Missing tags | 0 |
| Missing 4xx/5xx response | 0 |
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
| Dead code | vulture baseline capture via `quality-baseline.yml` | 1 - report-only baseline |
| Dependency hygiene | `deptry` + `pip check` via `quality-baseline.yml` and `make security-audit` | 2 - active/new-regression |
| Security | `bandit` + `pip-audit` via `quality-baseline.yml` and `make security-audit` | 2 - active/new-regression |
| Documentation gaps | current docs tests plus planned docs scorecard | planned |
| Observability gaps | `scripts/validate_observability_contracts.py`; richer runtime gap report planned | 2 - active/new-regression |

## Notes

- Future slices should add optional-tool measurements without converting unstable baselines into blocking gates prematurely.
