# Composite Source Authority

Manage owns definitions and membership. Performance owns composite materialization and calculation.
This guide covers the versioned producer schema and controlled tests, **not live provider acceptance**.
Production provider trust and institutional-attestation verification remain unavailable.

## Versions And Ownership

The existing `/api/v1/rebalance/composites` routes carry product versions independently of route
version. Requests without `product_version` retain internal v1 defaults and hashes. v2 requires an
explicit version, strict fields and declared economic authority; unknown versions refuse. Existing
membership, universe-attestation, publication and receipt wires remain v1.

| Contract | Meaning |
| --- | --- |
| INTERNAL | Performance returns and Core assets; internal provider IDs remain literal owners |
| EXTERNAL | Registered external providers supply returns/assets; no fabricated Core or calculation IDs |
| HYBRID | Explicit mixed per-fact sources, never first-response wins or automatic fallback |
| Publisher | Transport/storage ownership, separate from the economic authority |

Every required member/fact/closed business-date interval has exactly one declared source. Overlap,
missing coverage, contradictory mode, unknown member/provider and mismatched method bindings refuse.
Profiles bind provider registrations, source products/revisions/cuts/watermarks/digests and distinct
eligibility-evaluation and return-method references. References alone do not verify those sources.
`ENDING_ASSETS` is optional for return-only profiles. When selected, it requires independent Core or
registered external provenance and complete nonoverlapping member/horizon coverage, just like
beginning assets. The frozen profile remains unchanged and declares no ending assets. Absent that
selection, consumers must return NULL or refuse dependent reporting, never infer ending assets from
beginning values or returns. New ending-assets examples require new profile/source identities and
digests; authority declarations alone do not qualify observations or cash-flow-aware reporting.

## Content And Evidence

| Digest | Exact input |
| --- | --- |
| HP | Economic profile payload P; no approval or self digest |
| HB | Definition business payload B including P/HP; excludes the three envelope fields below |
| HC | B plus `definition_payload_digest` and complete `authority_approval`; excludes only its own top-level `content_hash` |

Canonical JSON uses sorted keys, compact separators, ASCII escapes and UTF-8 SHA-256. v2 admits
closed types, finite values, canonical dates/UTC microsecond instants and stable ordered identities;
duplicate raw JSON keys refuse. No nested digest field is recursively removed. v1's existing hash
and raw timestamp behavior is unchanged.

The immutable `(tenant_id, composite_id, definition_version)` names a revision, not a digest.
Approval claims bind that identity, HP, HB, profile revision and effective interval. They never sign
HC: HC already contains the approval. A content or approval replacement needs a new definition
version; original content remains retrievable.

`authority_approval` is discriminated by `evidence_kind`:

- `SYNTHETIC_UNSIGNED`: explicit test evidence, `synthetic-approval-claims.v1`.
- `INSTITUTIONAL_ATTESTATION_REFERENCE`: `composite-authority-approval-claims.v1`, a bounded
  issuer/attestation/revision/digest reference under `composite-authority-attestation.v1`.
  The referenced signed artifact must bind the exact canonical claims; no algorithm or trusted
  key is inferred from caller text.

Both currently declare `official_activation=UNAVAILABLE`. The institutional reference refuses
persistence with HTTP 503 / `COMPOSITE_AUTHORITY_ATTESTATION_VERIFIER_UNAVAILABLE`, including with
synthetic registration injected. Default v2 registration refuses with HTTP 503 /
`COMPOSITE_PROVIDER_TRUST_UNAVAILABLE`. A test resolver is injected only by owning tests; no request
flag, environment mode or deployed fallback selects it. No affirmative production resolver exists.
Eligibility-policy/evaluation approval (#778) and return-method/calendar approval (#607) remain
separate obligations; an authority-profile attestation cannot substitute for either.

## Client Example And Independent Fixture

The frozen shared fixture at `tests/fixtures/composites/source-authority.v2.json` has three logical
external members with assets 100/300/200 and decimal-fraction returns .10/-.02/.03. Its corrected
version changes the second asset to 310 and pins new source/profile/definition identities. Manage
publishes those identities, not a calculated composite return. All providers, evaluations and
approval references are labelled synthetic; supplied eligibility decisions are not engine proof.

From the repository root, create the exact tested request on stdout (PowerShell or POSIX):

```text
python -c "import json; from tests.composite_authority_helpers import frozen_authority_pack, definition_request; print(json.dumps(definition_request(frozen_authority_pack()['external_versions']['original']['definition'])))"
```

The target is `PUT /api/v1/rebalance/composites/SYNTHETIC_EXTERNAL_MONTHLY_USD/definitions/synthetic.definition.original`.
Tenant and actor come from admitted context, not body overrides. The example needs tenant
`synthetic-tenant-a`, actor `synthetic-maker` and an allowed composite write role from trusted test
ingress. With normal composition, the expected response is the provider-trust 503 above and no row
is written. Caller-asserted headers are not bank IAM. Owning registered-TestClient tests additionally
prove original/corrected exact wires, replay/conflict, tenant isolation and unchanged publication
completeness under constructor-injected synthetic trust.

## Storage And Cutover

Both definition versions use existing immutable JSONB rows and keys. No SQL migration, v1 default
backfill, history rewrite or new publication ledger is introduced. Repository reconstruction
dispatches on product version; unknown versions and invalid v2 raw content fail closed.

Deploy v2-capable consumer readers before enabling v2 writes. Old binaries cannot read v2 rows;
disable new writes and retain compatible readers for rollback rather than downgrading or deleting
history. A populated PostgreSQL upgrade/restart and actual Performance admission still need qualified
evidence before claiming durable cross-service acceptance. Cross-definition correction cannot use
v1 membership supersession; the consumer must retain and reconcile the distinct pinned generations.
`RECEIVED` acknowledges retrieval; publication stays `UNVERIFIED`.

## Validation And Remaining Gates

From the repository root, with the pinned development environment (PowerShell or POSIX):

```text
make test-unit UNIT_TESTS="tests/unit/dpm/composites tests/unit/api/test_composite_membership_routes.py tests/unit/api/test_composite_definition_versions_routes.py"
make typecheck
make openapi-gate domain-product-validate migration-smoke
```

Fixtures bind to the code-owned request helper and registered routes; schema success is not official
approval, financial calculation, production IAM or capacity certification. Protected CI/review,
exact-main validation, real PostgreSQL restart and actual #607 consumer acceptance remain required.
After merge, publish authored wiki and verify strict committed parity.

Review draft disposition: the historical `COMPOSITE-PUBLICATION-QA-20261002.md` distinction between
decision count, distinct members and retrieval acknowledgement is retained here. Its pre-attestation
schema observation is superseded; live population/consumer acceptance remains open. No historical
evidence is promoted into new certification.
