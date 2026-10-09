# Configured Composite eligibility sources

Manage owns immutable candidate selection, monthly assembly identity, eligibility rules and
retained membership evidence. Source services own the supplied facts. Configured adapters reuse
the existing candidate, monthly observation and evidence-verifier ports, existing monthly engine,
existing staged custody and the shared `authority_http` client. They introduce no new ledger.

This path accepts **synthetic, non-certifying evidence only**. Default configuration remains
unavailable. Candidate population stays `UNVERIFIED`, observations stay `SYNTHETIC_UNQUALIFIED`,
evaluation approval stays `SYNTHETIC_UNSIGNED`, and official activation stays `UNAVAILABLE`.
Actual Core unqualified products do not become compatible financial inputs through configuration.
Qualified bank issuer ownership, grants, provider registration, financial applicability and a
qualified complete Core cut remain outstanding under issues #714, #778 and #779.

## Deployment composition and transport

Set `DPM_COMPOSITE_SOURCES_JSON` to a strict `CompositeSourceConfiguration` JSON document. The
normal subject and recurring monthly dependencies use the same deployment-owned bindings; request headers and bodies cannot
select a source, endpoint, issuer, key set, credential or evidence posture. Missing configuration,
tenant binding, credential environment value or permitted verifier purpose fails closed.

Each binding supplies `operation` (`candidates`, `observations`, or `verification`), `tenant_id`,
`owner_service`, `endpoint`, `issuer`, `principal_id`, `credential_env`, pinned `keys`, credential
and subject revocation lists, and `evidence_posture: SYNTHETIC_NON_CERTIFYING`. A verification
binding additionally supplies a `receipt_issuer_id` and nonempty unique `verification_purposes` list using the existing
`VerificationPurpose` vocabulary. A source binding cannot supply verifier purposes. The source
and verifier must have distinct principals and distinct canonical public keys within a tenant.

Keys follow the Platform principal-credential JWKS representation: `kid`, `kty: OKP`,
`crv: Ed25519`, `alg: EdDSA`, canonical unpadded base64url `x`, and optional `revoked`.
The issuer/key set comes from deployment, never a credential-nominated URL. Requests send an
outbound Bearer credential read from `credential_env`; incoming caller credentials are not forwarded.
This artifact boundary does not resolve a bank principal or establish tenant membership/grants.

HTTPS is required except explicitly enabled synthetic loopback IP HTTP (`allow_local_http: true`).
User information, query strings and fragments are rejected. The shared bounded connection pool
uses the `DPM_COMPOSITE_HTTP_*` settings and common `DPM_SOURCE_HTTP_*` defaults. Configuration
bounds timeout to 0.1–30 seconds, attempts to 1–3, and response bytes to 1,024–8,000,000
(default 2,000,000). Responses stream under the byte cap, close on refusal, reject redirects,
request identity content encoding and refuse compressed content before decompression. Only
transport failures and 502/503/504 retry. No credentials enter response errors.
Source HTTP metrics use the bound upstream owner and the existing governed label normalization;
recognized Lotus owners retain their labels, while synthetic/external owners normalize to `unknown`.

## Signed response binding

POST request bodies are the exact existing port request serialized as JSON. Response envelopes
have exactly `owner_service`, `payload` and `credential`. `payload` is the strict existing
candidate or verification receipt contract, or the monthly assembly below. The credential uses
the governed Platform compact JWS Ed25519 format. Only `alg`, known `kid`, and optional `typ`
are accepted in its protected header. Signature verification precedes believing any payload claim.

Required claims retain Platform meanings: pinned `iss`, audience `lotus-manage`, bound service
`sub`, bound `tenant`, `principal_kind: service`, integer `exp`, nonempty `jti`, optional integer
`nbf`, and no delegated `act`. Revoked keys, credential ids and subjects refuse. Additional
Manage artifact claims are `operation`, `request_digest`, `payload_digest` and
`evidence_posture: SYNTHETIC_NON_CERTIFYING`. Both digests use the existing Lotus canonical
JSON SHA-256 function over the complete serialized object. A correctly signed identity credential
without those exact bindings does not approve an artifact. Known issuer/key identity alone does
not confer financial approval or cut compatibility.

For verification, the configured purpose must authorize the requested purpose. The returned
`CompositeEvidenceVerificationReceipt/v1` must match the complete request, configured verifier
principal, configured issuer and synthetic posture. A qualified receipt is refused by this path.
The credential `issuer` is a URI identifying the signing identity authority; `receipt_issuer_id`
is the existing opaque financial receipt authority id. Both are pinned independently in deployment
and checked against their respective signed contracts.
The existing policy, evaluation, economic authority, method calendar and provider purposes and
their required fields remain valid; this slice adds the Manage-local purpose below.

## Complete monthly assembly contract

`CompositeMonthlyEligibilityAssembly/v1` carries:

| Field | Binding |
| --- | --- |
| `observations` | Complete strict `CompositeMonthlyEligibilityObservations/v1`; exact tenant, composite, definition, month, currency, source cut, revision, ordered expected members and full canonical content hash. |
| `inputs` | Exactly one each of `CASH`, `FLOWS`, `MONTH_END_ASSETS`, `PRIOR_ASSETS`, `READINESS`, in that order. Each carries `owner_service`, `source_cut_id` and its product/version/revision/digest `EvidenceBinding`. |
| `compatibility_binding` | `CompositeSourceCutCompatibility/v1` with revision and digest of `{observations, inputs}`. |
| `compatibility_posture` | Existing `SYNTHETIC_UNQUALIFIED`, `SOURCE_UNVERIFIED` or `UNAVAILABLE`; only the synthetic state can proceed. |

Individual cut ids may differ. Matching dates, cut ids or individual digests does not establish
compatibility. Before evaluating, Manage requests independent verification with purpose
`COMPOSITE_MONTHLY_SOURCE_CUT`, exact tenant/composite/definition, the whole calendar-month
effective window, `subject_content_hash` of the complete observations, `claims_digest` of the
complete assembly, the compatibility binding and source product `CompositeMonthlyEligibilityAssembly`.
Absent verification refuses before evaluation persistence. `SOURCE_UNVERIFIED` and `UNAVAILABLE`
refuse before contacting the verifier. This contract describes source-supplied normalized facts;
it does not implement or certify a join of raw Core financial products.

Staged and recurring monthly evaluation custody retain optional `source_assembly_evidence` with the complete assembly and the
independently admitted verification receipt. It revalidates exact observations, manifest and receipt
request on decoding. The field is omitted for legacy evaluations, preserving their canonical hashes;
legacy history is not retroactively certified. Replay uses retained evidence after process restart
without re-resolving changed source facts. The calculation and maker/checker rules remain in their
existing owners.

The recurring simulation, diff and evaluation paths resolve the same signed assembly and whole-cut
verification. The approved evaluation retains it through atomic membership publication and restart.
Each month requires its own prospective policy approval: first-definition authority approval or a
prior month's policy approval does not approve later months. Final definition economic-authority
approval must occur at or after its bound evaluation approval; premature approval refuses before
verification or publication. This chronology differs from monthly policy approval, which must
precede the month being evaluated.
The chronology guard applies to a fresh finalization command, not immutable archival decoding.
Previously sealed synthetic receipts with premature authority timing remain exactly retrievable
and replayable with their original hashes, `UNVERIFIED` completeness and unavailable activation.
Their finalization GET, exact resolver and replay responses include
`X-Composite-Evidence-Diagnostic: HISTORICAL_AUTHORITY_CLOCK_MISMATCH`. Archival retrieval is not
new approval or financial admission; the consumer must still refuse unsuitable authority timing.

## Owning proof

From the `lotus-manage` repository root, run the portable targeted source tests:

```powershell
python -m pytest tests/unit/dpm/infrastructure/test_composite_configured_sources.py tests/unit/dpm/infrastructure/test_composite_monthly_source_assembly.py -q
```

```bash
python -m pytest tests/unit/dpm/infrastructure/test_composite_configured_sources.py tests/unit/dpm/infrastructure/test_composite_monthly_source_assembly.py -q
```

For the native API/PostgreSQL proof, use an owned disposable PostgreSQL server and set
`DPM_POSTGRES_INTEGRATION_DSN` to its admin database and `DPM_POSTGRES_INTEGRATION_REQUIRED=1`.
The test creates and removes only its UUID database and explicitly owned listeners/processes.
Run from the repository root on either shell:

```text
python -m pytest tests/integration/dpm/composites/test_composite_configured_sources_postgres.py tests/integration/dpm/composites/test_composite_recurring_sources_postgres.py -q
```

The fixture generates separate ephemeral source and verifier Ed25519 keys and exact configuration;
it provides a runnable configuration example without committing private keys. No dependency override
is installed in the spawned API. Prospective controls are retained synthetic fixture history;
evaluation and approval use actual runtime time. Proof covers independent refusal before write,
recovery, existing +150/-100 net-flow calculation, maker/checker separation, finalization and
publication of the complete source evidence, exact-digest evidence resolution, changed-digest
refusal, and persisted replay after restart with default unavailable sources. The pytest temporary
directory retains the actual HTTP finalization graph as `configured-source-finalization.json` for
consumer compatibility investigation. It proves executable adapter behavior, not bank IAM,
qualified financial products, official Composite membership or Performance materialization.
`test_composite_historical_finalization_postgres.py` restores the original sealed historical graph,
checks repeated migration initialization and two fresh API processes, exact read/resolution/replay,
changed digest/tenant/approval refusal and unchanged database payload/hash/publication count.

The recurring pack uses registered HTTP and disposable PostgreSQL without dependency overrides.
It covers forged credentials, mixed cuts, stale source revisions, verifier outage, recovery,
checker publication and replay. Its 17-case economic campaign retains all three rule assessments
for thresholds, missing/nonpositive denominators, conflicting/exact duplicates, linked reversals,
late arrivals, missing members and failure precedence over unknown facts. A separate July–September
campaign publishes three independently approved months, retains immutable exclusion history,
refuses prior-month policy inheritance, and proves that cash clearing alone cannot cause re-entry.
`recurring-economic-matrix.json` and `recurring-transition-history.json` are actual HTTP campaign
records in pytest temporary artifacts. Their constituent bindings describe explicit synthetic
normalized snapshots; they do not prove qualification of individual Core financial products.
