# Lotus Manage Domain Data Product Declarations

This directory stores `lotus-manage` repo-native declarations for governed Lotus domain data
products.

`lotus-manage` owns discretionary portfolio-management execution and supportability. It does not
own canonical portfolio ledger state, market-data source truth, performance analytics, risk
analytics, advisory-only workflows, reporting, or UI composition.

Current declarations:

1. `lotus-manage-consumers.v1.json`
   Consumer declaration for governed `lotus-core` products used by management execution workflows.
   It includes the request-payload `PortfolioStateSnapshot:v1` dependency and stateful
   `ClientRestrictionProfile:v1` / `SustainabilityPreferenceProfile:v1` dependencies used by
   ESG/restriction-aware construction and proof-pack source preservation.
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

1. `lotus-manage` stateful source consumption must stay aligned with certified producer
   declarations. New core products should be added here only after source-owner approval,
   trust metadata, tests, and live proof exist.
2. Market-data request payloads remain source-data-authority sensitive, but `MarketDataWindow` is not
   currently approved for `lotus-manage` in the upstream producer declaration. Do not declare it here
   until upstream approval and required trust metadata are explicit.
