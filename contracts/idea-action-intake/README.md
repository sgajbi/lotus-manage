# Idea Action Intake Contract

This folder defines the `lotus-manage` contract for Lotus Idea conversion-intent handoffs.

| File | Purpose |
| --- | --- |
| `lotus-manage-idea-action-intake.v1.json` | Source-safe intake and owner-outcome contract for not-certified management review realization. |

An accepted `REVIEW_FOR_REBALANCE` intent creates exactly one durable, portfolio-scoped
`PENDING_REVIEW` management action. Manage owns its append-only review history; portfolio-manager
decisions require the current `source_event_version`, so concurrent stale decisions fail closed.

```mermaid
sequenceDiagram
    participant Idea as lotus-idea
    participant Manage as lotus-manage
    participant PM as Portfolio manager
    Idea->>Manage: Conversion intent + portfolio scope + idempotency key
    Manage->>Manage: Persist PENDING_REVIEW action and event v1
    Manage-->>Idea: Receipt + management_action_id + outcome route
    PM->>Manage: APPROVE/REJECT + expected source_event_version
    Manage->>Manage: Fence stale writer; append owner event v2
    Idea->>Manage: Read owner outcome history
    Manage-->>Idea: Source-owned status and event chain
```

`APPROVED` means management review approval only. It is not rebalance execution, an order or OMS
instruction, suitability proof, or client publication. Production IdP claim binding and live
cross-repository consumer certification remain outstanding, so the surface is not promoted as a
supported feature.

When editing this folder, keep the API route, OpenAPI descriptions, README/wiki boundary language,
and focused route tests aligned. Run `make openapi-gate` when the HTTP surface changes.

