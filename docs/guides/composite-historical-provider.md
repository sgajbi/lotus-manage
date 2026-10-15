# Historical monthly-policy normalized provider

## Native controlled-original admission

The existing `DPM_COMPOSITE_HISTORICAL_POLICY_ADMISSION_JSON` channel also admits an explicit
`adapter: CONTROLLED_SYNTHETIC_POLICY_V1` configuration. Absence remains unavailable; an unknown
adapter or malformed native document refuses. The existing HTTP document has no `adapter` field
and retains its existing strict transport shape. Native admission implements the same
`HistoricalPolicyAdmissionPort` with dedicated request/proof v2; it adds no ledger, API or deployable service.
Candidate/monthly source assembly is separate and remains unavailable without its own admitted
source composition. Core per-fact verification cannot certify that assembly.

Native configuration contains exactly `adapter`, existing `trust`, `source_public_key_base64`,
`source_key_valid_from`, `source_key_valid_to`, `verifier_id`, `verifier_key_file`,
`originals_directory` and `revocation`. Trust is synthetic only, its signing contract matches the
adapter, and source/verifier principals and public-key digests differ. The source key is canonical
standard base64 of the 32-byte Ed25519 public key. The deployment's `configuration_digest` is
`native_configuration_digest(document)` over the complete document excluding only that nested
trust digest. It includes paths, public trust and current revocation, never private key bytes.
The revocation snapshot supplies revision, checked/expiry instants, revoked principals, key
digests and original digests, including explicit empty lists. Its window is at most five minutes
and must cover actual request/admission time; the operator must supply a current reviewed snapshot.

The source-policy author supplies an envelope named `<raw_sha256_hex>.json` in the read-only
originals directory. Its two fields are `raw_original_base64` and `original_credential` (canonical
standard-base64 Ed25519 signature over the exact decoded original bytes). Raw originals are bounded
to 2MB. Duplicate JSON members, malformed signatures, changed digest/identity/purpose/scope or
revoked/expired material refuse. Manage receives only source public keys and signed bytes; source
private keys never enter this process.

The strict signed original contains `format: CONTROLLED_SYNTHETIC_POLICY_V1`,
`posture: SYNTHETIC_NON_CERTIFYING`, purpose `COMPOSITE_CONTROLLED_SCENARIO_POLICY_ADMISSION`,
`signature_semantics: SCENARIO_DECLARATION_AT_ACTUAL_ISSUANCE`, issuer/artifact/revision,
signer principal, `actual_issued_at`, resolved `policy`, policy version, currency, attachments and
`scenario_proposed_by/at` plus `scenario_approved_by/at`. Scenario approval precedes the policy
month and uses a different actor; actual issuance must follow that scenario approval, fall within
the trusted source key window and precede current admission. These are declared synthetic scenario
events, not backdated actual bank approval. The dedicated normalized mapping retains
`actual_issued_at` and the four explicit `scenario_*` fields. It has no original proposal/approval
time or actor aliases. Proof v2 fixes `VERIFIED_AT_ACTUAL_ISSUANCE` and
`SCENARIO_DECLARATION_AT_ACTUAL_ISSUANCE`; it never asserts a physical historical signature.

The independent verifier loads only its separately provisioned 32-byte raw Ed25519 private key,
checks its public digest against verifier trust, and signs the complete new verification
request/mapping/current-revocation proof, excluding only top-level content_hash and verifier_credential.
It cannot reuse the source key or approve an assembler's declaration. Existing HTTP proof v1
and historical graph versions keep their original-approval semantics; scenario proofs refuse there.

The normal unpublished subject lifecycle selects monthly policy proposal/approval v3, subject
policy/evaluation proposal/approval v3, and finalization/receipt v4, with a dedicated evaluation
approval binding v3 and dedicated definition/authority payload v3. Old definition/authority v2
refuse scenario bindings and retain exact exported schemas. Existing route bodies still accept only reference/hash and admitted inputs;
current actor/time come from the existing application. Independent policy/evaluation approval,
all-rule evaluation, final publication and source-off retained replay remain required. Forward
migration0047 preserves0046 predicates and adds only typed STAGED controlled-scenario branches.
The native contract table, exact canonical graph and mixed/tampered vectors live in
[controlled-scenario contracts](../contracts/composite-controlled-scenario/README.md).

### Explicit container custody

`docker-compose.composite-controlled.yml` is an opt-in overlay for the existing `lotus-manage`
service. It mounts `MANAGE_COMPOSITE_ORIGINALS_DIRECTORY` read-only at
`/run/lotus/composite-originals` with automatic host-path creation disabled, and supplies the
operator's `MANAGE_COMPOSITE_VERIFIER_KEY_FILE` as a Compose secret at
`/run/secrets/manage_composite_verifier_key`. Native JSON must explicitly select those container
paths; host paths alone do not configure the application. Neither the overlay nor public variable
names create a key, original, trust, credential or authority. There is no automatic enablement.
Select this tracked overlay only through the existing reviewed canonical Compose/model admission;
preserve project/ports/DB/Core bindings and keep evaluated configuration private.

Custody reads reject links/reparse points, nonregular or multiply linked files, changed file
identity, empty/oversized bytes and missing inputs. Verifier keys additionally require effective
write-open denial (permission or read-only filesystem), without writing the file or assuming host
POSIX ownership/mode survives Docker Desktop. Host ACL confidentiality, access by other principals
and actual secret-mount behavior remain operator/container qualification requirements; the reader
does not claim to certify them. No private key is included in model errors, configuration hashes
or retained evidence. Key/original reads are lazy for new admission: retained policy/approval reads
and exact replay can survive original-source withdrawal without signing new evidence.

Existing native unit and staged-route tests exercise generated independent test authors, actual
bounded file reads and normal production composition. Other candidate/verification sources remain
controlled test inputs in that route proof. This is not Docker, real PostgreSQL, full native Core
population or Performance READY acceptance. Operator-owned originals/trust/principals, current
revocation and actual protected key delivery remain unprovided until Root admits them.

## Existing HTTP provider

Manage supports dedicated HTTPS transport for its existing historical verification port. The
independent provider resolves the immutable original, verifies its actual source-owned signing
format and returns a signed normalized proof. Manage validates the proof and retains exact custody.
This transport does not implement an original-format verifier or certify a provider, source, bank
identity, methodology or official activation.

## Deployment and trust

`DPM_COMPOSITE_HISTORICAL_POLICY_ADMISSION_JSON` contains strict `HistoricalPolicyConfiguration`.
The tracked application Compose environment forwards this operator-supplied JSON with a blank
default. See [configuration delivery](composite-configured-sources.md#tracked-compose-configuration-delivery)
for the three separate channels, credential delivery boundary and deployment evidence requirements.
The documented controlled profile explicitly names `MANAGE_HISTORICAL_PROVIDER_AUTH` as
`credential_env`; tracked Compose forwards that variable with a blank default. An actual
operator-provisioned value and reviewed provider trust remain required; blank refuses before HTTP.
Absent/blank configuration selects the unavailable port; malformed configuration refuses. No test
adapter or fixture key is selected automatically. The [configuration example](../examples/composite-historical-provider-configuration.json)
uses a non-routable endpoint and placeholder pins. Replace these with deployment/provider evidence;
the example is a validated shape, not an executable authority grant.

One tenant and one existing `HistoricalPolicyTrust` tuple bind original signing-contract identity,
independent signer/verifier principals and key digests, approved trust-profile `configuration_digest`
and posture. The configuration digest is a profile pin, not a self-referential configuration hash.
The normalized Ed25519 verifier digest binds its raw 32-byte public key; the original signer digest
follows its source-owned key contract. Changing a label to `QUALIFIED_RECEIPT` supplies no qualification.
Foreign tenants/signing contracts refuse before network access. Requests cannot select trust.

Only pinned HTTPS is supported, including conformance tests. Normal CA/hostname validation applies.
Local HTTP, URL credentials, queries, fragments and redirects refuse. `credential_env` names the
deployment variable holding the provider bearer credential; absent/blank credentials return
unavailable without a call. Keep credentials out of JSON/evidence. Retain the public trust profile
addressed by proof digests for audit.

The existing shared composite client owns bounded connection/pool limits and `DPM_COMPOSITE_HTTP_*`
settings. Request timeout is 0.1–30 seconds and attempts 1–3. The streamed response limit defaults to
8,000,000 bytes, configurable from 1,024–8,000,000. A 2,000,000-byte original expands to 2,666,668
base64 bytes before policy/attachments; ordinary source-channel 2MB limits would be insufficient.
Oversize refuses without truncation. Compression refuses (`Accept-Encoding: identity`). Only
transport errors and HTTP 502/503/504 retry; other 3xx/4xx reject, terminal 5xx/transport fails
unavailable. The shared pool's policy is set by the first composite channel in the process; use
coordinated timeout settings across configured channels. No additional client lifecycle is added.

API refusals use `COMPOSITE_HISTORICAL_POLICY_RESPONSE_INVALID` (422) for malformed/invalid signed
responses, `COMPOSITE_HISTORICAL_POLICY_PROVIDER_REJECTED` (422) for provider 3xx/4xx rejection,
and `COMPOSITE_HISTORICAL_POLICY_ADMISSION_UNAVAILABLE` (503) for missing access/outage.

## Frozen provider protocol

POST exactly `HistoricalPolicyVerificationRequest.model_dump(mode="json")` to the configured URL
with `Authorization: Bearer <deployment credential>`. Accept exactly `HistoricalPolicyVerification/v1`
JSON, without an outer JWS or `owner_service/payload/credential` wrapper. See the
[frozen schemas and examples](../contracts/composite-historical-policy/README.md). Duplicate members
at every object depth, non-object JSON, malformed values, unknown versions and extra fields refuse.
Other source/attestation protocols and global verification purposes remain unchanged.

The proof binds the complete original reference, scope/month/policy/currency, current operation,
revision, actor, server timestamp and intent. Original bytes/digest, opaque credential, signing
contract and event times remain unchanged. The existing Ed25519 normalized credential signs the
canonical unsigned proof hash. `admitted_historical_policy` checks signature, mapping, exact request,
independence, time interval and deployment trust; embedded keys alone are insufficient.

Revocation must be independently observed before the request. The frozen timing rule is
`checked_at <= requested_at <= admitted_at < expires_at <= checked_at + five minutes`.
Use a genuinely current revocation snapshot and admit after receiving the request. Never backdate
`checked_at` to copy `requested_at`. Renew expired snapshots before later operations. Verify original
signatures at the preserved approval instant; apply current revocation clearance to present admission.
Every new proposal/approval needs its own operation-bound proof; a static file cannot supply them.

## API and recovery

The unpublished first-subject lifecycle also consumes this configured channel through
`PUT /api/v1/rebalance/composites/{composite_id}/eligibility-subjects/{definition_version}/{subject_revision}/policies/{proposal_revision}/historical-admission`.
It binds `expected_subject_content_hash` plus the same immutable original `reference` before any
definition is published. Separate current checker/evaluation operations retain fresh operation
proofs; original dates remain in the original mapping. This additive path is synthetic only and
returns staged controls v2 and finalization/receipt v3. See the
[first-month contract](composite-monthly-eligibility.md#historical-first-month-policy).

The caller submits only the original reference to the existing registered operation:

`PUT /api/v1/rebalance/composites/{composite_id}/definitions/{definition_version}/monthly-eligibility/policies/{month}/proposals/{proposal_revision}/historical-admission`

The body is `{"reference": ...}` with exact `issuer_id`, `artifact_id`, `revision`, `raw_digest`
(`sha256:` plus the original-byte SHA256) and `signing_contract`; see the policy v2 example's
`verification.request.reference` in the frozen packet. Current actor/time remain application-owned.
Existing independent approval/evaluation operations select policy v2, ordinary evaluation/receipt
v3 and correction v4 from retained authority. No arbitrary version or retrospective edit is added.

Same-intent retained replay and exact historical resolver reads precede current provider calls.
Provider outages/configuration rotation do not rewrite evidence. Changed intents conflict; fresh
writes require fresh proofs. Disable new writes and keep compatible readers during outage. Original
and corrected receipts remain separately selectable, with original raw custody preserved.

## Conformance and activation

Actual source/provider owners must separately prove immutable lookup, original signing/credential
format, semantic mapping, historical key validity, independent principals, observed revocations,
proof-signing ownership and deployed access before genuine activation. Institutional applicability,
financial inputs, bank IAM and consumer admission remain separate gates. Synthetic conformance or
transport configuration establishes none of these facts.

From the `lotus-manage` checkout, in PowerShell or Bash with its Python environment:

```text
python -m pytest tests/unit/dpm/infrastructure/test_historical_policy_verifier.py tests/unit/dpm/infrastructure/test_authority_http.py -q
python -m pytest tests/integration/dpm/composites/test_historical_provider_http_postgres.py -q
```

The second command requires `DPM_POSTGRES_INTEGRATION_DSN`; set
`DPM_POSTGRES_INTEGRATION_REQUIRED=1` to fail instead of skip when missing. The test uses ephemeral
signer/verifier keys, trusted test TLS and an independently observed synthetic revocation snapshot.
Normal production composition proves registered HTTP → PostgreSQL → restart → exact resolver/replay
with providers unavailable, original v3/correction v4 custody and refusals without writes.
Captured exchanges are synthetic test execution, not genuine historical or institutional acceptance.
