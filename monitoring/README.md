# Manage Monitoring

This directory is reserved for repo-local monitoring source such as dashboard definitions,
Prometheus rules, and alert artifacts when they are authored in this repository.

Current subfolders:

| Folder | Purpose |
| --- | --- |
| `grafana/` | Dashboard source when Manage-owned dashboards are checked in. |
| `prometheus/` | Prometheus rule source when Manage-owned rules are checked in. |

Do not treat generated screenshots, local exports, or ad hoc runtime captures as source truth here.
If monitoring posture changes, update `contracts/observability/lotus-manage-monitoring.v1.json`,
the service runbook, and any wiki operations page that describes the signal.

Validate observability contract changes with `make observability-contract-validate`.

