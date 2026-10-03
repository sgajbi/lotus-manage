# Construction Method Ownership Evidence

Issues #740 and #739 retain broader integration acceptance. This slice extends native HTTP and
PostgreSQL regression proof; it does not change construction economics or production ownership.

## Scope

The complete `ConstructionMethod` vocabulary is exercised in stateless, unrestricted stateful and
restricted stateful modes. The unmodified API creates every financial row in a disposable database.
The controlled Core contract producer supplies an effective instrument-level buy/sell restriction;
no dependency override or direct financial database write is used.

- Same-tenant run, artifact and support-bundle reads succeed; foreign reads return 404.
- Exact replay returns the original set. Changed methods conflict; missing tenant is refused.
- Every trading method retains the shared hard-policy BLOCKED trace and cannot be selected.
  Counterfactual mechanics remain auditable; the no-action comparator has no economic run.
- Forced API-process death and fresh interpreter recovery preserve exact sets, complete artifacts,
  owner/lineage rows and replay identity without additional runs or selections.

The served OpenAPI no-action example has no economic run reference and typed BEFORE evaluation context.
Complete ordered run/artifact/set/lineage rows, including metadata and duplicate multiplicity,
are compared across recovery. Exact method statuses and diagnostic codes distinguish unavailable
cost/Risk/ESG/regime authority from derived liquidity policy and no foreign-currency exposure.

## Independent Calculation

USD 100,000 NAV = 975 shares × USD 100 + USD 2,500 cash. A 2% reserve target yields 980 shares,
USD 2,000 cash and BUY 5. Liquidity's 3% floor yields 970 shares, USD 3,000 cash and SELL 5.
Risk's 30% single-position cap yields 300 shares, USD 70,000 cash and SELL 675.
Each method's actual artifact is checked against these independent quantity/cash/NAV expectations.
Required unavailable authority remains qualified rather than fabricated; local derived policy and
non-applicable foreign-currency exposure are identified separately.

Falsification caught both representative regressions: dropping admitted run ownership fails the
same-tenant HTTP read; bypassing shared hard-policy evaluation fails the restriction trace assertion.
Both temporary mutations were restored before final validation. Initial test-authoring failures
corrected the enabled authorization layer's 403 expectation and decoded stored JSON text for comparison.
Review falsification additionally caught changed lineage metadata with identical run/artifact/set
rows and a removed cost-authority reason despite unchanged DEGRADED status. The stale served
no-action example failed an independent schema assertion before correction. All mutations and
temporary diagnostics were removed before final proof.

## Reproduction And Limits

From this repository root, Windows or POSIX, activate the supported environment; set
`DPM_POSTGRES_INTEGRATION_DSN` to an isolated server whose account has `CREATEDB`, and
`DPM_POSTGRES_INTEGRATION_REQUIRED=1`. Run:

```text
python -m pytest tests/integration/dpm/supportability/test_construction_method_network.py -q
```

The required PostgreSQL CI lane discovers this file through its existing integration-tree target.
The source-installed API, controlled contracts and caller-asserted authorization do not certify
actual Core ingestion, production identity, database-host failover, downstream instruction/package
release, external booking, image-wide method authority or production horizontal capacity.

Review draft `MANAGE-CONSTRUCTION-NETWORK-QA-20261002.md` supplied the bounded acceptance gaps;
its original stateless/heuristic evidence remains historical, not superseded by a broader claim.
Repository context and wiki record the new test scope. Shared skills/AGENTS/routing are unchanged;
no additional deployed context copy exists for this repository-local testing practice.
