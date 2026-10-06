# Monthly Composite Eligibility

Manage evaluates a bounded monthly synthetic profile and publishes independently approved results
through its existing immutable membership ledger. It does not calculate composite returns.
Official activation remains `UNAVAILABLE`: the default source adapter is unavailable, population
qualification and bank IAM are not established, and institutional policy applicability requires approval.

## Rule And Source Dictionary

All money is bounded decimal text in the definition's reporting currency. No FX conversion,
customer code or arbitrary SQL is accepted. Limits are 1,000 expected portfolios, 250 flow events
per portfolio and five ordered policy layers.

| Rule | Inputs And Interval | Comparator | Missing Or Ambiguous Inputs |
| --- | --- | --- | --- |
| Significant flow | Absolute net posted external cash over UTC calendar month M / assets at prior month-end | `ABS_NET >= flow_threshold` fails; synthetic example 10% | Unknown; missing/nonpositive denominator is not zero |
| Cash | Settled, unencumbered cash / assets, both at month-end M | `cash_ratio > cash_threshold` fails; synthetic example 5% | Unknown; no inference from booked or projected balances |
| Readiness | Discretionary, funded and invested facts at month-end M | Every required fact must be true | False fails; absent fact remains unknown |

Every rule is assessed. Any known failure produces `EXCLUDED`; otherwise any required unknown
produces `PENDING_REVIEW`; otherwise the portfolio is `INCLUDED`. All failure/unknown reasons are
retained in the evaluation, including when another rule already failed. Counts use unique portfolio
identities. Missing expected members remain pending and make the evaluation universe incomplete;
they are not normal business exclusions.

The source-owned `CompositeMonthlyEligibilityObservations:v1` includes month, tenant/definition,
currency, source cut/revision, generation time, expected IDs and dated observations. Admission pins
the product's owner/cut/revision/content digest against retained universe evidence. The Manage
universe cut and monthly observation cut are distinct. A consumer timestamp cannot manufacture a cut.
Historical mandate bindings, current portfolio state, booked cash and projected liquidity do not
individually establish the complete monthly product.

Identical event IDs are deduplicated; conflicting duplicates are unknown. Posted external cash
is netted, internal transfers and cancelled events are excluded. Reversals require one retained
original, matching currency and the exact opposite amount. In-kind, unresolved reversal, late
receipt and incomplete flow coverage remain unknown rather than receiving an invented policy.
Threshold decisions use exact cross-products, not rounded displayed ratios.

## Configuration, Approval And Time

Layers resolve in order `PLATFORM → TENANT → STRATEGY → COMPOSITE → RUN`. Each binds scope,
revision, whole-month effective dates and permitted overrides. Economic equality does not require
override permission, but lexical decimal changes still change the content digest.

```text
Before M: resolved policy + attachments → maker proposal → independent checker approval
After M closes: pinned source + universe + current parent → reproducible evaluation proposal
Independent checker: exact proposal digest → one atomic transaction
                      [approval + membership revision + universe attestation + publication]
Consumer: exact published hashes → retained receipt / separate Performance admission
```

Policy proposal revision identifies configuration custody; `eligibility_policy_version` comes from
the immutable definition and remains the membership/universe/consumer policy identity. They are
not interchangeable. Approval binds exact policy, attachments, inputs, all-rule results, parent,
target revision and month. Maker/time and checker/time are server-admitted, not body fields.
Self-approval, changed material, stale parent/content and competing active month approvals refuse.
Configuration must be proposed and approved before M starts; retrospective policy improvement is
not permitted. Publication requires a finalized source generated after M ends; draft evaluation
retains unresolved timing as unknown rather than certifying a complete month.

Publication replaces only M's decision interval. Earlier/later intervals and the immutable parent
remain available. Each later month's re-entry assesses all rules again: clearing cash does not
clear a funding failure. A known discretionary fact plus another unknown can publish pending;
unknown discretionary status refuses publication because the legacy membership wire requires a
boolean. No fabricated boolean or v1 wire change is used.

## API Tutorial

Prefix `P = /api/v1/rebalance/composites/{composite_id}/definitions/{definition_version}/monthly-eligibility`.
All calls require unambiguous `X-Tenant-Id`, `X-Actor-Id` and `X-Role`. Administrators or portfolio
managers propose; only an independent `DPM_COMPOSITE_ADMIN` checks. These headers require trusted
ingress and are not authenticated bank-principal evidence.

| Step | Operation | Required Evidence |
| --- | --- | --- |
| Resolve | `POST P/validate` | `month`, ordered `layers` |
| Inspect | `POST P/simulate` or `POST P/diff` | Pinned membership, attestation/hash, layers; diff also `baseline_layers` |
| Propose policy | `PUT P/policies/{month}/proposals/{proposal_revision}` | `layers`, exact named attachment bindings |
| Check policy | `PUT P/policies/{month}/proposals/{proposal_revision}/approval` | `expected_proposal_content_hash` |
| Propose evaluation | `PUT P/evaluations/{evaluation_revision}` | Approved policy hash, month, pinned parent/universe and new target revision |
| Check evaluation | `PUT P/evaluations/{evaluation_revision}/approval` | `expected_proposal_content_hash` |
| Replay/read | Corresponding `GET` operations; policy approval is `GET P/policies/{month}/approval` | Exact identifiers and tenant scope |

Example evaluation request, with hashes obtained from retained APIs rather than invented values:

```json
{
  "month": "2026-09",
  "policy_approval_content_hash": "<retained-policy-approval-sha256>",
  "parent_membership_revision": "membership-r1",
  "parent_membership_content_hash": "<retained-membership-sha256>",
  "attestation_version": "universe-r1",
  "universe_content_hash": "<retained-universe-sha256>",
  "target_membership_revision": "membership-r2",
  "correlation_id": "monthly-evaluation-2026-09"
}
```

Replace hash placeholders with exact `sha256:` digests. Never send source observations, actor,
tenant, evaluation time or activation fields in the body. The registered-route tests below are
executable complete request/response examples, including configuration attachments and re-entry.

## Independent Examples And Regression

| Case | Independent Result |
| --- | --- |
| `(+150 - 100) / 1,000` | Absolute net 5%; passes synthetic 10% flow threshold |
| `abs(-100) / 1,000` | 10%; fails at equality |
| Cash `50 / 1,000` | 5%; passes cash equality |
| Cash `51 / 1,000` | 5.1%; fails cash rule |
| Missing/nonpositive denominator | Unknown, never implicit zero |
| Cash clears; funding remains false | Remains excluded; re-entry requires all rules |

From the `lotus-manage` root, using the project Python 3.12 environment (PowerShell or POSIX):

```text
python -m pytest tests/unit/dpm/composites/test_composite_monthly_eligibility.py tests/unit/api/test_composite_monthly_eligibility_routes.py tests/unit/api/test_composite_monthly_evaluation_routes.py -q
python -m pytest tests/integration/dpm/composites/test_composite_monthly_policy_postgres.py tests/integration/dpm/composites/test_composite_monthly_evaluation_postgres.py -q
```

The database command requires an approved isolated `DPM_POSTGRES_INTEGRATION_DSN` and
`DPM_POSTGRES_INTEGRATION_REQUIRED=1`; missing prerequisites fail rather than silently skip.
The proofs cover real PostgreSQL, fresh-process default read/check/replay, post-write rollback
and observed conflicting writer locks. Synthetic source injection is explicit and does not
certify a live supplier, capacity or institutional approval.

## Operations And Remaining Boundaries

| Condition | Operator Action |
| --- | --- |
| Source unavailable or owner/cut/content mismatch | Obtain qualified owner evidence; never replace pins with latest facts |
| Missing members or unknown discretionary status | Repair source evidence and retain a new proposal; do not force publication |
| Stale published parent | Reconcile the latest publication and create a new explicitly pinned evaluation |
| Lost acknowledgement | Retry the exact command; retained approval/publication replay is idempotent |
| Write failure | Verify no partial publication; retry exact retained proposal after recovery |
| New source correction | Retain a separately governed revision; do not mutate approved monthly truth |

Migrations `0040`/`0041` add immutable policy/evaluation custody; membership authority stays in the
existing ledger. Manage does not mark receipt as materialization, fills or authoritative Core booking.
Performance owns return-fact admission and calculation. Existing v2 definitions independently bind
eligibility approval digests: publishing monthly v1 wires alone does not create or reapprove a v2
definition, provider registration or institutional approval.

Drift threshold alternatives, accreditation, additional institutional rules, qualified historical
Core readiness/cash and bank IAM remain separate, unapproved scope. No GIPS compliance, live
capacity or production-readiness claim follows from this synthetic profile.
