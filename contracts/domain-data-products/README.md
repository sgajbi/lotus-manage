# Lotus Manage Domain Data Product Declarations

This directory stores `lotus-manage` repo-native declarations for governed Lotus domain data
products.

`lotus-manage` owns discretionary portfolio-management execution and supportability. It does not
own canonical portfolio ledger state, market-data source truth, performance analytics, risk
analytics, advisory-only workflows, reporting, or UI composition.

Current declarations:

1. `lotus-manage-consumers.v1.json`
   Consumer declaration for the governed `lotus-core` portfolio-state product used by management
   execution workflows through the current request-payload contract.
2. `lotus-manage-products.v1.json`
   Producer declaration for `lotus-manage:PortfolioActionRegister:v1`, surfaced through the
   implemented rebalance supportability, artifact, and workflow route families.

Local validation:

```powershell
python scripts/validate_domain_data_product_contracts.py
```

Make target:

```powershell
make domain-product-validate
```

Trust telemetry validation:

```powershell
make trust-telemetry-validate
```

Full mesh contract validation:

```powershell
make mesh-contract-validate
```

Current watchlist:

1. `lotus-manage` has a modeled, feature-gated `lotus-core` resolver client for future stateful
   `portfolio_id` execution, but it must not be advertised as supported or declared as a live
   source-data API-read dependency until the governed core execution-context product is available
   and live proof is captured.
2. `portfolio_id` stateful resolution must add an explicit governed API-read dependency before it
   becomes promoted runtime behavior. The upstream blocker is `sgajbi/lotus-core#330`.
3. Market-data request payloads remain source-data-authority sensitive, but `MarketDataWindow` is not
   currently approved for `lotus-manage` in the upstream producer declaration. Do not declare it here
   until upstream approval and required trust metadata are explicit.
