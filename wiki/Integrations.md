# Integrations

## Upstream and downstream posture

- `lotus-core`
  source-data authority when management flows use core-referenced portfolio or market inputs
- `lotus-gateway`
  primary consumer of management execution, supportability, and capability-discovery contracts
- `lotus-advise`
  owner of advisor-led proposal simulation, proposal artifacts, and proposal lifecycle workflows;
  `lotus-manage` must not reintroduce those concerns

## Boundary rules

1. `lotus-manage` may execute deterministic rebalance decisions from governed inputs
2. inline bundles do not transfer source-data authority to `lotus-manage`
3. `portfolio_id` and future stateful modes must stay grounded in governed `lotus-core` contracts
4. capability consumers should use canonical snake_case query parameters `consumer_system` and
   `tenant_id`
5. advisory proposal workflows should be integrated through `lotus-advise`

## Core Sourcing Target

```mermaid
sequenceDiagram
    participant Gateway as lotus-gateway
    participant Manage as lotus-manage
    participant Core as lotus-core
    Gateway->>Manage: POST /api/v1/rebalance/simulate input_mode=stateful
    Manage->>Manage: Check feature gate and resolver configuration
    alt current guarded state
        Manage-->>Gateway: 409 DPM_STATEFUL_INPUT_DISABLED
    else future certified state
        Manage->>Core: Compose RFC-087 source-data products
        Core-->>Manage: Portfolio, model, mandate, eligibility, tax lots, market data, FX, lineage
        Manage->>Manage: Transform context and run DPM engine
        Manage-->>Gateway: Result with source lineage and supportability
    end
```

Current state:

1. `lotus-manage` has the typed stateful request models, resolver client, transformation helpers,
   and lineage fields.
2. The first RFC-087 source-product integrations exist for `DpmModelPortfolioTarget:v1` through
   `POST /integration/model-portfolios/{model_portfolio_id}/targets` and
   `DiscretionaryMandateBinding:v1` through
   `POST /integration/portfolios/{portfolio_id}/mandate-binding`, and
   `InstrumentEligibilityProfile:v1` through
   `POST /integration/instruments/eligibility-bulk`.
3. `lotus-core` does not yet expose the full RFC-087 composed DPM source-data products required
   for production stateful promotion.
4. Capability discovery does not advertise stateful execution unless the stateful gate,
   `DPM_CORE_BASE_URL`, non-legacy resolver configuration, and capability flag are all enabled.
5. RFC-0036 now tracks the upstream gap through `lotus-core` RFC-087 and updated
   `sgajbi/lotus-core#330`.

Current source-product integration status:

| Source product | lotus-manage posture | Promotion impact |
| --- | --- | --- |
| `DpmModelPortfolioTarget:v1` | Client method and transformer implemented; live proof pending canonical stack refresh. | Required but not sufficient for stateful execution. |
| `DiscretionaryMandateBinding:v1` | Client method and policy-context transformer implemented; live proof pending canonical stack refresh. | Required but not sufficient for stateful execution. |
| `InstrumentEligibilityProfile:v1` | Client method and shelf-entry transformer implemented; live proof pending canonical stack refresh. | Required but not sufficient for stateful execution. |
| Portfolio state, tax lots, market-data coverage, readiness | Awaiting RFC-087 core implementation and certification. | Blocks stateful execution promotion. |

Historical blocked-route proof on 2026-05-02:

1. `POST http://core-control.dev.lotus/integration/portfolios/PB_SG_GLOBAL_BAL_001/dpm-execution-context`
   returned `404`.
2. `POST http://core-query.dev.lotus/integration/portfolios/PB_SG_GLOBAL_BAL_001/dpm-execution-context`
   returned `404`.
3. `POST http://manage.dev.lotus/api/v1/rebalance/simulate` with `input_mode=stateful` returned
   `409 DPM_STATEFUL_INPUT_DISABLED`.
4. The executable proof command now covers both manage behavior and core route posture:

```powershell
make live-api-validate-core
```

The default command expects the current blocked posture. After `lotus-core` exposes the RFC-087
certified source-data products, update the validator to prove composed-source readiness before
promoting stateful capability truth.

Runtime guardrail: `lotus-manage` no longer defaults to the retired monolithic
`/integration/portfolios/{portfolio_id}/dpm-execution-context` route. Stateful sourcing remains
unavailable until all required RFC-087 product-specific core routes are integrated and proven.

This is the correct current behavior: manage is ready for the implemented stateless surface, while
stateful core-sourced execution remains withheld until the upstream source products are certified.

## Manage API Consumers

Strategic downstream consumption should use:

1. `GET /api/v1/integration/capabilities`
2. `POST /api/v1/rebalance/simulate`
3. `POST /api/v1/rebalance/analyze`
4. `POST /api/v1/rebalance/analyze/async`
5. `/api/v1/rebalance/runs/*` supportability and artifact routes
6. `/api/v1/rebalance/operations/*` async-operation routes
7. `/api/v1/rebalance/policies/*` policy-pack supportability routes

Removed or stale consumers should not call unversioned `/rebalance/*` routes, removed
`/api/v1/platform/capabilities`, or proposal/advisory-era DPM endpoints.

## Reference

- [docs/standards/RFC-0082-upstream-contract-family-map.md](../docs/standards/RFC-0082-upstream-contract-family-map.md)
