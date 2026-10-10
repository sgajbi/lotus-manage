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

Monthly arithmetic uses a fresh decimal context with 80 significant digits, `ROUND_HALF_EVEN`,
exponent bounds -999999 to 999999, no clamping and only invalid-operation, division-by-zero and
overflow traps. This preserves the default ratio wire while isolating evaluation/approval hashes
from caller precision, rounding, exponent limits, traps, flags and mutable decimal defaults.
Repeating ratios are deterministic evidence; they do not replace exact threshold cross-products.
The owning monthly eligibility tests pin the default `1/300` wire/hash and replay it under hostile
contexts; the registered proposal/approval test also verifies immutable replay and publication count.

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
Self-approval, changed material, stale parent/content and competing ordinary month approvals refuse.
Configuration must be proposed and approved before M starts; retrospective policy improvement is
not permitted. Publication requires a finalized source generated after M ends; draft evaluation
retains unresolved timing as unknown rather than certifying a complete month.

Publication replaces only M's decision interval. Earlier/later intervals and the immutable parent
remain available. Each later month's re-entry assesses all rules again: clearing cash does not
clear a funding failure. A known discretionary fact plus another unknown can publish pending;
unknown discretionary status refuses publication because the legacy membership wire requires a
boolean. No fabricated boolean or v1 wire change is used.

## API Tutorial

### First Definition: Staged V2 Lifecycle

For a new definition, `S = /api/v1/rebalance/composites/{composite_id}/eligibility-subjects/{definition_version}/{subject_revision}`.
This is an unpublished reservation, not a provisional definition or invented parent membership.

| Phase | Operation | Exact Material |
| --- | --- | --- |
| Before M | `PUT S` | Business fields, month and source-owned candidate registry binding; server supplies scope, actor and time |
| Before M | `PUT S/policies/{proposal_revision}` then `/approval` | Subject hash, ordered layers, attachments; independent checker and retained verification |
| After M closes | `PUT S/evaluations/{evaluation_revision}` then `/approval` | Approved policy hash, actual observation cut/revision/hash, target first membership revision |
| Finalize | `PUT S/finalization` | Evaluation revision/hash and existing v2 definition request, exact authority/method/provider receipts |
| Retrieve | Corresponding exact `GET` operations | Retained subject and controls; final receipt joins canonical publication |

The prospective candidate registry does not embed future month-end observations. Evaluation freezes
the separately admitted owner/cut/revision/content, currency, complete logical member population
and all-rule results. The approval digest is retained before the final economic-authority profile
and definition hashes; no hash depends on its own future definition. Authority, eligibility,
method/calendar and provider-registration verification are distinct purposes.
Economic-authority approval must occur at or after the bound evaluation approval. Premature
approval refuses before final verification or publication. This does not change the prospective
monthly policy requirement: policy approval must precede its month, and each month needs a new approval.

Finalization atomically retains the v2 definition, first membership, universe, existing publication
cursor and final receipt. Identical retry returns the original graph; changed content conflicts.
The approval remains `NOT_PUBLISHED` as immutable historical evidence. The final receipt remains
`UNVERIFIED`; it is not financial-fact admission, institutional activation or authoritative booking.

Consumers submit the existing strict `EvidenceBinding` to
`POST /api/v1/rebalance/composites/{composite_id}/definitions/{definition_version}/eligibility-evidence/resolve`:
product `CompositeSubjectEvaluationApproval`, version `v1`, exact evaluation revision and approval
digest. Tenant is admitted transport scope. The response contains the exact subject locator and
final receipt only after joining retained definition, approval, membership, universe and publication
hashes/sequence. No latest or correlation lookup exists. Staged-only/missing scope returns 404;
wrong product/digest refuses with 422; missing publication refuses with 409. Unsupported versions
are rejected by the existing binding schema.

Default candidate, observation and independent-verifier adapters are unavailable. A typed qualified
receipt is not qualification by itself: only an independently configured verifier can establish its
issuer/artifact/purpose authority. Test fixtures are explicitly synthetic; their assets/returns
labels do not supply actual financial products. Performance owns downstream admission/calculation.
The [configured source guide](composite-configured-sources.md) describes the normal deployment
factory for synthetic signed candidate, complete monthly assembly and purpose-bound independent
verification, including retained manifest/receipt custody and native HTTP/PostgreSQL proof.

### Existing Published Definition

Prefix `P = /api/v1/rebalance/composites/{composite_id}/definitions/{definition_version}/monthly-eligibility`.
All calls require unambiguous `X-Tenant-Id`, `X-Actor-Id` and `X-Role`. Administrators or portfolio
managers propose; only an independent `DPM_COMPOSITE_ADMIN` checks. These headers require trusted
ingress and are not authenticated bank-principal evidence.

Deployment-configured recurring simulation, diff and evaluation use the same signed monthly
assembly and independent whole-cut verifier as staged evaluation. Configured proposals retain
optional `source_assembly_evidence`; legacy proposals omit the field and retain their hashes.
Approval and membership publication preserve this graph without querying sources during replay.
First-definition approval and earlier monthly approvals do not authorize future months.

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

## Approved-Month Source Corrections

An ordinary monthly approval remains the unique root for its composite/month. A source correction
retains a new `CompositeMonthlyEvaluationProposal/v2` and independent
`CompositeMonthlyEvaluationApproval/v2`; it never edits or replaces the original retained products.
This version is independent of the embedded definition's product version: either definition v1
or v2 can appear in an ordinary receipt v1 or an amendment receipt v2.

Use `PUT E/source-amendment`, where
`E = /api/v1/rebalance/composites/{composite_id}/definitions/{definition_version}/monthly-eligibility/evaluations/{new_evaluation_revision}`.
The body contains the ordinary evaluation command's month, approved-policy hash, exact parent
membership/hash, input universe revision/hash, new target revision and correlation ID, plus
`amendment` with these claims:

| Claim | Required binding |
| --- | --- |
| `correction_kind` | Exactly `SOURCE_CORRECTION` |
| `predecessor_approval_binding` and `expected_authority_binding` | Identical product/version/revision/digest for the selected chain tip |
| `predecessor_receipt_binding` | Exact monthly receipt product/version/revision/digest for that predecessor |
| `original_approval_binding` | Exact ordinary v1 root approval, retained through every later correction |
| `projection_parent_membership_binding` | Current canonical membership revision/hash, separately from the selected monthly authority |
| `expected_current_publication_sequence` | Positive sequence of that current parent publication |
| `affected_from`, `affected_to` | The complete evaluated calendar month |
| `reason_code`, `reason`, `evidence_bindings` | Explicit reason code, nonblank reason up to 2,048 characters, and 1–32 distinct versioned evidence bindings |

The server obtains observations and complete verified assembly from the configured source ports;
the command cannot supply financial facts, actors or clocks. Proposal time must follow both the
selected predecessor approval and current projection decision. The approved policy and expected
population must match the predecessor exactly. A changed generation clock alone is insufficient.
Propose against the selected authority and independently approve the exact proposal hash with
`PUT E/approval`. GET evaluation and approval operations discriminate the product version.

The existing publication lock protects authority selection, current parent and sequence checks,
and the owning approval/membership/universe/publication transaction. There is one immutable chain,
one child per predecessor, and at most 64 approvals including the original. Selection follows exact
links rather than timestamps. Stale authority or projection, forks, a full history, or any later
approved month refuse; the latter requires a governed cascade that this profile does not support.
Policy changes, population changes and staged-finalization root amendments remain unsupported.
An ordinary second approval still refuses. Exact retries remain readable and idempotent after
subsequent publications, and retain the original publication sequence.

The published universe locates the amendment approval as v2. POST its exact binding to the existing
eligibility evidence resolver to obtain `CompositeMonthlyEligibilityPublicationReceipt/v2`, with
the complete new graph and `lineage` equal to the approved amendment claims. Resolution verifies
every predecessor receipt, original root, parent publication sequence and full projected objects
under one read snapshot. Original receipt v1 lookup remains unchanged. Global authority
`EvidenceBinding` remains v1; only the monthly resolver binding admits monthly approval v2.
Consumers must explicitly support these v2 products; an existing v1-only dataset is not silently
upgraded. Report selection and financial admission remain independently governed.

Migration `0044` preserves existing payloads and staged foreign keys, replaces the monthly approval
primary key with revision identity, and adds monthly-root uniqueness, predecessor/original custody
foreign keys and successor uniqueness in the existing tables. Deploy compatible readers before
admitting amendment traffic. Keep issued v2 products and their schema during recovery; do not
downgrade or delete the chain to make an older reader accept it.

From the `lotus-manage` root, using the project Python environment, these commands work in
PowerShell and POSIX shells:

```text
python -m pytest tests/unit/dpm/composites/test_monthly_amendment_controls.py tests/unit/dpm/composites/test_monthly_amendment_custody.py -q
python -m pytest tests/integration/dpm/composites/test_composite_monthly_amendment_upgrade_postgres.py tests/integration/dpm/composites/test_composite_monthly_amendment_postgres.py tests/integration/dpm/composites/test_composite_monthly_amendment_http_postgres.py -q
```

The second command requires an owned isolated `DPM_POSTGRES_INTEGRATION_DSN` and
`DPM_POSTGRES_INTEGRATION_REQUIRED=1`. Its native proof retains explicitly synthetic initial
history, then runs configured signed HTTP sources, registered correction/approval/resolver routes,
PostgreSQL custody and a new API process. These products remain `UNVERIFIED`; source correction
does not qualify financial facts, establish bank IAM, extend economic authority dates or activate
official eligibility. Broader eligibility and historical-cascade acceptance remain open.

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
python -m pytest tests/unit/dpm/composites/test_composite_staged_bindings.py tests/unit/dpm/composites/test_composite_staged_custody.py tests/unit/dpm/composites/test_composite_staged_postgres_queries.py tests/unit/api/test_composite_subject_lifecycle_routes.py tests/unit/api/test_composite_subject_resolver_routes.py -q
python -m pytest tests/integration/dpm/composites/test_composite_staged_postgres.py tests/integration/dpm/composites/test_composite_staged_upgrade_postgres.py -q
```

The database command requires an approved isolated `DPM_POSTGRES_INTEGRATION_DSN` and
`DPM_POSTGRES_INTEGRATION_REQUIRED=1`; missing prerequisites fail rather than silently skip.
The proofs cover real PostgreSQL, fresh-process default read/check/replay, post-write rollback
and observed conflicting writer locks. Synthetic source injection is explicit and does not
certify a live supplier, capacity or institutional approval.
The staged pack additionally checks populated `0041`→`0042` replay, cross-mode foreign-key
refusals, atomic first publication and an authenticated resolver in a fresh API process.

## Operations And Remaining Boundaries

### Historical original policy admission

The additive `PUT policies/{month}/proposals/{proposal_revision}/historical-admission`
operation is relative to the registered monthly-eligibility base above. Its command contains only
`reference`: `issuer_id`, `artifact_id`, `revision`, `raw_digest` and `signing_contract`. Tenant,
actor, current operation time and normalized mapping come from admitted server dependencies.
Callers cannot submit historical event times, raw artifacts, credentials or trust configuration.
Existing policy checking and evaluation operations then select the explicit product families:

| Policy proposal/approval | Evaluation proposal/approval/receipt | Purpose |
| --- | --- | --- |
| v1 | v1 | Existing prospective ordinary evaluation |
| v1 | v2 | Existing source correction |
| v2 | v3 | Admitted historical policy, ordinary evaluation |
| v2 | v4 | Source correction of a v3 root or v4 predecessor |

Existing wires remain frozen. Explicit unknown/null versions and mixed families refuse; missing
versions retain only the existing v1 interpretation. A staged root remains unsupported for ordinary
source correction. Definition product versions are independent of this table.

`historical_policy.py` separates exact original raw bytes and their digest/opaque original
credential from normalized policy fields and present-operation verification. The trusted admission
port must verify the authentic artifact using its actual original signing format, original signer
authority and historical approval time. It must also prove current revocation clearance and fresh
independent admission for each policy/evaluation proposal and approval. Original maker/checker times
remain original; current maker/checker times remain current. The normalized proof carries separate
Ed25519 verifier credentials, exact operation/scope/revision/actor/intent binding, server-pinned
keys/configuration, independent principals and a maximum five-minute admission interval.

Production composition supports a dedicated configured normalized-provider HTTPS adapter through
`DPM_COMPOSITE_HISTORICAL_POLICY_ADMISSION_JSON`; blank configuration remains unavailable.
The independent provider owns actual original-format verification and fresh revocation evidence.
Manage admits only the frozen signed response against deployment trust. See
[provider protocol, configuration and activation conditions](composite-historical-provider.md).
Controlled test keys/formats never auto-enable a provider. Genuine original-format/provider
conformance, trust ownership and institutional acceptance remain separate activation gates.
This transport implements no original-format verifier inside Manage.

Exact replay returns retained custody before consulting current sources. Read-only receipt resolution
validates the recorded admission interval and all immutable bindings without renewing authority,
rechecking today's revocation or changing original evidence. A fresh write requires fresh admission;
unavailable, changed mapping/trust, stale projection and changed command refuse atomically.
The existing monthly UOW, locks, one-root/one-successor constraints and publication ledger apply.
Forward migration `0045` admits the explicit wire families without rewriting old rows or migration
checksums; apply it before enabling new writers. No separate runtime or authority ledger is introduced.

Actual schemas and controlled examples live in
[`docs/contracts/composite-historical-policy`](../contracts/composite-historical-policy/README.md).
From the `lotus-manage` root, verify their exact bytes and canonical content on either OS:

```text
python -m tests.composite_historical_policy_contracts docs/contracts/composite-historical-policy --check
python -m tests.composite_historical_policy_graph tests/fixtures/composite_historical_policy_graph --check
python -m pytest tests/unit/dpm/composites/test_historical_policy_admission.py tests/unit/dpm/composites/test_historical_monthly_custody.py tests/unit/api/test_historical_policy_routes.py -q
```

The owning PostgreSQL lane runs `test_composite_historical_policy_postgres.py` and
`test_composite_historical_policy_upgrade_postgres.py` in `tests/integration/dpm/composites`.
Local runs without an isolated DSN explicitly skip those proofs; skips are not storage qualification.
These contracts do not admit downstream Report/Render/Archive consumers, genuine institutional
authority, production sources, bank IAM, methodology or official activation. Those acceptance gates
remain separate and open.

### Exact monthly published evidence

Fresh monthly proposals carry the server-owned `publication_evidence_version: "v1"` marker.
Commands cannot supply or downgrade it. Missing markers preserve legacy custody; explicit null
or unknown versions are refused. No migration rewrites an earlier proposal, approval or universe.

A marked checker publication adds exactly one current `lotus-manage` source product named
`CompositeMonthlyEvaluationApproval/v1` to its published universe, with `POLICY_INPUT` scope,
the exact source cut, evaluation revision as watermark and full approval content hash. A previous
monthly locator is replaced only in the new projected universe; retained inputs remain immutable.

POST the locator as an `EvidenceBinding` to the existing
`/api/v1/rebalance/composites/{composite_id}/definitions/{definition_version}/eligibility-evidence/resolve`
operation. For this product it returns `CompositeMonthlyEligibilityPublicationReceipt/v1`:
the full definition and approval (including complete source assembly), membership/universe
bindings, source cut, positive canonical publication sequence, `UNVERIFIED` completeness and
content hash. The receipt hash excludes only its own root hash and retains every nested hash.
The staged product continues to return its existing subject finalization receipt.

Resolution joins independently retained definition, policy proposal/approval, evaluation
proposal/approval, parent, input universe, published membership/universe and canonical publication
under one memory lock or PostgreSQL repeatable-read snapshot. Full reprojection rejects a changed
nested locator even when the legacy universe self-hash is unchanged. Missing custody, incorrect
pins or rehashed disagreement fail closed; no source call, new approval or publication is made.
Unmarked legacy monthly approvals remain readable and replayable but cannot be resolved as this
new proof. A marked proposal without retained complete source evidence returns unavailable.

Each month's checker evidence is separate from prospective policy approval, Core per-fact
qualification and whole-cut verification. It does not extend a v2 definition's economic authority
dates, method/provider registration, institutional approval or official activation.

An internal client must derive the binding from the exact published universe, rather than copy
the evaluation claims digest or select the latest approval. With an authenticated HTTP client,
the definition's base URL and that universe already pinned:

```python
locator, = (
    product for product in published_universe["source_products"]
    if product["owner_service"] == "lotus-manage"
    and product["product_name"] == "CompositeMonthlyEvaluationApproval"
)
response = client.post(
    definition_base_url + "/eligibility-evidence/resolve",
    json={
        "product_name": locator["product_name"],
        "product_version": locator["contract_version"],
        "revision": locator["source_watermark"],
        "digest": locator["content_hash"],
    },
)
response.raise_for_status()
receipt = response.json()
```

Legacy v1 retrieval remains supported. A consumer requiring a v2 economic profile must additionally
admit that full profile, its unchanged effective dates, provider/method registration and separately
qualified financial facts. The native three-month v2 campaign defines a distinct initial synthetic
profile for July–September; it does not promote fixture authority into financial qualification.

| Condition | Operator Action |
| --- | --- |
| Source unavailable or owner/cut/content mismatch | Obtain qualified owner evidence; never replace pins with latest facts |
| Missing members or unknown discretionary status | Repair source evidence and retain a new proposal; do not force publication |
| Stale published parent | Reconcile the latest publication and create a new explicitly pinned evaluation |
| Lost acknowledgement | Retry the exact command; retained approval/publication replay is idempotent |
| Write failure | Verify no partial publication; retry exact retained proposal after recovery |
| New source correction | Use the explicit source-amendment operation with exact authority, receipt, parent and sequence pins |

Migrations `0040`/`0041` add immutable policy/evaluation custody; membership authority stays in the
existing ledger. Manage does not mark receipt as materialization, fills or authoritative Core booking.
Forward migration `0042` preserves legacy payloads and historical migration checksums. Apply before
switching traffic; existing writers retain their original definition/parent/membership requirements.
Staged branches use strict subject/hash custody and non-null legacy/staged discriminator FKs.
Do not downgrade readers, delete approvals or hand-create a reserved definition for rollback.
Performance owns return-fact admission and calculation. Existing v2 definitions independently bind
eligibility approval digests: publishing monthly v1 wires alone does not create or reapprove a v2
definition, provider registration or institutional approval.

Drift threshold alternatives, accreditation, additional institutional rules, qualified historical
Core readiness/cash and bank IAM remain separate, unapproved scope. No GIPS compliance, live
capacity or production-readiness claim follows from this synthetic profile.

Review disposition: the reviewed `V2-LIFECYCLE-DESIGN-20261007.md` and staged-custody addendum are
adopted for the first-definition lifecycle. The Performance staged consumer plan's missing exact
lookup is addressed by the resolver above; its independent publication/financial qualification
requirements remain acceptance dependencies. Earlier source-preparation drafts are superseded only
where the implemented lifecycle differs; no historical evidence is promoted into certification.
