# Manage Contracts

This directory contains authored contract truth for `lotus-manage`. Contract changes must stay
aligned with code, tests, OpenAPI/API vocabulary where applicable, and repo-local wiki source.

| Folder | Owns | Validate with |
| --- | --- | --- |
| `domain-data-products/` | Manage producer and consumer data-product declarations. | `make domain-product-validate` |
| `trust-telemetry/` | Repo-native trust telemetry snapshots for every active Manage producer product. | `make trust-telemetry-validate` |
| `observability/` | Monitoring and observability contract descriptors. | `make observability-contract-validate` |
| `idea-action-intake/` | Source-safe Lotus Idea action-intake handoff contract. | Focused contract/API tests plus `make openapi-gate` when routes change. |

Run `make mesh-contract-validate` after changing domain-product, trust-telemetry, or observability
contracts. Do not edit generated platform catalogs here; platform aggregation belongs in
`lotus-platform`.

