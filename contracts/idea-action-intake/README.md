# Idea Action Intake Contract

This folder defines the `lotus-manage` contract for Lotus Idea conversion-intent handoffs.

| File | Purpose |
| --- | --- |
| `lotus-manage-idea-action-intake.v1.json` | Source-safe request/response contract for the not-certified action-intake route foundation. |

The contract proves route compatibility for `lotus-idea`; it does not create action-register
records, approve rebalances, create orders, contact clients, authorize publication, or promote a
supported feature.

When editing this folder, keep the API route, OpenAPI descriptions, README/wiki boundary language,
and focused route tests aligned. Run `make openapi-gate` when the HTTP surface changes.

