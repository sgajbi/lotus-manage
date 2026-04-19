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

Local validation:

```powershell
python scripts/validate_domain_data_product_contracts.py
```

Make target:

```powershell
make domain-product-validate
```

Current watchlist:

1. `lotus-manage` currently has no active outbound source-data client to `lotus-core`,
   `lotus-performance`, or `lotus-risk`.
2. `portfolio_id` stateful resolution must add an explicit governed API-read dependency before it
   becomes runtime behavior.
3. Market-data request payloads remain source-data-authority sensitive, but `MarketDataWindow` is not
   currently approved for `lotus-manage` in the upstream producer declaration. Do not declare it here
   until upstream approval and required trust metadata are explicit.
