# Durable Construction Restriction Evidence

Issue #739 remains open for broader actual-source, downstream and production-principal acceptance.

## Correction

Construction alternatives already enforce shared restrictions, but their persisted run artifacts
omitted `client_restriction_policy`. The native regression failed on a tenant-owned artifact with
missing evidence while direct simulation retained it. Execution now reuses the shared evaluator
before run persistence. Source-backed decisions preserve scope, business date, hashes, versioned
applicable/violated rule references and explicit no-override authority.

Comparison mechanics and no-action semantics remain unchanged. Stateless artifacts are explicitly
`NOT_ASSESSED`; unavailable or unclassifiable authority is review-required. Legacy rows are not
rewritten. Policy qualification is necessary, not sufficient, for approval or instruction release.

## Native Matrix

Supported HTTP APIs create all financial records in disposable PostgreSQL. Eighteen controlled
source profiles exercise direct simulation and every trading construction method:

- Verified empty and unavailable profiles remain distinct.
- Buy-only, sell-only, inclusive start/end, future, expired and inactive rules retain exact decisions.
- Instrument, unrelated instrument, asset, issuer, country and intentional global scopes are checked.
- Missing issuer/country/asset classification remains explicitly qualified, never inferred permission.
- Independent USD100,000 controls: BUY5 to980shares/USD2,000 cash; liquidity SELL5 to970/USD3,000;
  risk-cap SELL675 to300/USD70,000. Restrictions qualify these counterfactuals without altering them.
- Changed source material conflicts with the original idempotency keys. Exact retries do not add rows.
- Forced API death/fresh interpreter retains complete run/artifact/set/lineage rows and decisions;
  artifact reads need no producer calls and remain tenant-fenced. Blocked selections write no rows.

## Reproduction And Limits

From the repository root on Windows or POSIX, activate the supported environment and set
`DPM_POSTGRES_INTEGRATION_DSN` to an isolated server with `CREATEDB`;
set `DPM_POSTGRES_INTEGRATION_REQUIRED=1`. Run:

```text
python -m pytest tests/integration/dpm/supportability/test_construction_method_network.py -q
```

The existing required PostgreSQL CI lane discovers the test. Controlled contract fixtures and
caller-asserted identity are not actual Core delivery, bank IAM, downstream approval/package/booking,
database-host failover or capacity evidence. Shared skills/AGENTS/routing need no change; repository
testing context is updated. Existing construction QA informed the scope; historical receipts remain.
