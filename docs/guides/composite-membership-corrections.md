# Composite Membership Corrections

Manage retains immutable membership revisions and publishes each accepted revision atomically.
A correction's `affected_from`/`affected_to` declare the inclusive business-date window for downstream
reconciliation. Every portfolio's decision evidence outside that window must match the superseded
revision. Removed history, changes to status/reason/discretionary facts, and substituted approval or
source references outside the window refuse with HTTP 409,
`COMPOSITE_MEMBERSHIP_CORRECTION_OUTSIDE_WINDOW`. No revision or publication is written on refusal.

## Worked Historical Example

The executable controlled example has three synthetic members:

| Member | Original history | Correction |
| --- | --- | --- |
| A | Included from 1 January 2026 onward | Excluded on 5 January only |
| B | Included through 31 January; excluded prospectively from 1 February | Unchanged |
| C | Included through 15 January; membership ends afterward | Unchanged |

For A, submit three intervals: included 1–4 January, excluded 5 January with the explicit reason,
then included from 6 January. Copy the original evidence on both unaffected intervals. Declare
`supersedes_membership_revision=m1`, `affected_from=2026-01-05`, `affected_to=2026-01-05` and use a
new revision identity `m2`. Excluding A from 1 January onward while declaring 5 January alone is
invalid. Splitting an unchanged interval into adjacent equivalent intervals is permitted; comparison
uses effective decision evidence rather than list position or interval spelling. Gaps outside the
window are changes too. The domain compares interval boundaries without expanding every day.

## Supported API Flow

From the Manage API, let `P=/api/v1/rebalance/composites/{composite_id}/definitions/{definition_version}`.
Use admitted tenant/actor/role headers. These current routing assertions do not establish bank IAM.

1. Read `GET P/membership/m1` and preserve the complete original wire/hash.
2. Submit the new complete decision snapshot to `PUT P/membership/m2`, with its parent and impact
   window. Full request bodies are executable in `tests/composite_correction_helpers.py`.
3. If the response is lost, resend exactly the same request. It returns the retained revision and
   emits no additional publication. Changed content under the same revision conflicts.
4. Read `GET P/membership/m1` and `GET P/membership/m2`; pinned originals remain unchanged.
5. Retrieve `GET /api/v1/rebalance/composites/publications` by cursor. The corrected publication
   carries the exact revision hash, parent and affected window. Completeness remains `UNVERIFIED`.
6. Create a separately pinned universe attestation through the existing universe-attester role.
   An excluded member with complete decision coverage is ordinary business exclusion. A terminated
   member still declared expected in a later window is missing evidence, requiring `INCOMPLETE`;
   do not turn absence into an ordinary exclusion or manufacture a replacement member.

The shared pure domain check is enforced in the memory adapter's lock and PostgreSQL's existing
transaction, before canonical membership/publication writes. Parent evidence is loaded using the
exact tenant/composite/definition/revision key. Existing stored corrections are preserved and remain
readable; this change does not retroactively certify their declared impact windows.

## Pinned Date-Range Reads

`GET P/membership/{membership_revision}/range?effective_from=YYYY-MM-DD&effective_to=YYYY-MM-DD`
pages original decision intervals intersecting the inclusive requested range. Both calendar
dates are required; a reversed window or invalid calendar date returns 422. Missing or foreign
tenant revisions return 404. The same admitted identity required for full-revision and single-date
reads applies here.

For the worked example, request `effective_from=2026-01-05&effective_to=2026-01-05` from `m1` and
`m2`. Each response contains three decision intervals, but A is included in the original and
excluded in the correction. `membership_content_hash` identifies the complete immutable revision,
not a newly hashed projection. The response also retains `tenant_id`, `source_cut_id`, exact revision identity,
requested boundaries, `limit`/`offset` and the total `count` of matching intervals. Intervals and evidence are returned without
clipping; a member with adjacent include/exclude intervals can appear twice in a wider range.
`count` therefore counts intervals, not distinct portfolios or financially included members.

For `2026-01-31` through `2026-02-01`, the original read includes both B's closing included interval
and its prospective excluded interval. C's terminated interval does not overlap this range but
remains retrievable for earlier dates. A requested gap returns no matching intervals for that
member; the API never fills it or turns it into an exclusion. A total `count=0` means there are no
matching stored intervals, not a population-completeness assertion. An empty page beyond the end
can retain a positive total count. Use the separately pinned universe attestation for coverage.
The response explicitly reports `completeness=UNVERIFIED`; selection is not an attestation.

`limit` defaults to 100, accepts 1–1000, and `offset` defaults to zero and must be nonnegative.
For example, append `&limit=2&offset=0` and then `&limit=2&offset=2` to retrieve a three-interval
result in two pages. Each page retains the same total count and membership hash. Pages are stable
even when another revision is published because the requested revision is immutable. There is no
latest lookup or publication-watermark substitution.

Response size is bounded by the page limit. Filtering still loads and scans the complete pinned
revision in O(n) time; existing revision admission has no hard decision-count cap. This is not a
capacity/SLO certification. Full-revision and existing `/as-of` wires remain unchanged. Reads do not publish revisions or advance the
publication cursor. Registered API cases are in
`tests/unit/api/test_composite_membership_range_routes.py`; actual PostgreSQL and application/client
restart proof is in `tests/integration/dpm/composites/test_composite_membership_range_postgres.py`.
These supplied synthetic decisions do not establish authoritative population or financial results.

Exact retries of retained pre-fix revisions return their original content and publication identity;
this is historical replay, not approval of a new correction. New revision identities always pass
the current guard, including when they copy a formerly accepted wrong-window decision.
No migration, new ledger, cross-service transaction, policy approval or financial methodology is introduced.

## Owning Verification

From the `lotus-manage` checkout with the project Python 3.12 environment active (PowerShell or POSIX):

```text
python -m pytest tests/unit/dpm/composites/test_composite_corrections.py -q
python -m pytest tests/integration/dpm/composites/test_composite_correction_network.py -q
```

The network test requires an isolated `DPM_POSTGRES_INTEGRATION_DSN` and
`DPM_POSTGRES_INTEGRATION_REQUIRED=1`. It uses normally spawned APIs with default persistence,
real PostgreSQL, independent process restarts, concurrent exact retry, tenant/read/write refusal,
prospective exclusion, historical termination, original/corrected pins and missing-member evidence.
Inputs are explicitly supplied synthetic decisions and asserted universe evidence. This proof does
not qualify an authoritative population, automatic source evaluation, actual member-return
materialization, provider approval, institutional activation, bank IAM or production capacity.
Performance owns calculation and economic idempotency; retrieval replay is not financial delivery.
