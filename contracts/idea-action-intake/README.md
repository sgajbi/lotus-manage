# Idea Action Intake Contract

This folder defines the `lotus-manage` contract for Lotus Idea conversion-intent handoffs.

| File | Purpose |
| --- | --- |
| `lotus-manage-idea-action-intake.v1.json` | Source-safe request/response contract for the not-certified action-intake receipt. |

The contract proves executable receipt compatibility for `lotus-idea`, including trusted local/dev
caller scope, idempotency conflict detection, replay, and accepted/rejected outcomes; it does not
create action-register records, approve rebalances, create orders, bind production IdP claims,
contact clients, authorize publication, or promote a supported feature.

When editing this folder, keep the API route, OpenAPI descriptions, README/wiki boundary language,
and focused route tests aligned. Run `make openapi-gate` when the HTTP surface changes.

