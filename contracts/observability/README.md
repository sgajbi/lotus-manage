# Observability Contracts

This folder contains repo-native observability contract truth for Manage monitoring.

| File | Purpose | Validate with |
| --- | --- | --- |
| `lotus-manage-monitoring.v1.json` | Declares supported monitoring signals, dashboards, alerts, and service evidence expected by platform governance. | `make observability-contract-validate` |

Keep this contract synchronized with real metrics, logs, runbooks, dashboards, and alert posture.
Do not add aspirational signals that the service does not emit or that operations cannot validate.

Use `make mesh-contract-validate` when observability changes affect data-product publication or
platform mesh certification evidence.

