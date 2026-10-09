# Institutional verification evidence v2

Implementation scope: Manage #779; first delivery uses existing staged finalization only.
This contract was recorded before source changes in
[the governing issue](https://github.com/sgajbi/lotus-manage/issues/779#issuecomment-6089085538).

Existing verification request/receipt v1 and finalization/receipt v1 keep their exact semantics,
serialization and hashes. New institutional authority verification uses an explicit v2 request
binding the full definition, original attestation reference, subject and evaluation approval.
No `claims_digest`, source product or revision field is repurposed. The retained original artifact
binds existing institutional approval claims and exact subject/evaluation approval identities;
its original signature is independent of a fresh configured verifier response. Original approval
time is preserved; it is not today's admission time. New finalization/receipt v2 retains this
evidence through existing atomic publication custody. Synthetic finalization remains v1.

Authority, method and each selected provider require independent scoped verification. A signed
request echo, unknown signer, missing or stale revocation snapshot, invalid original artifact,
foreign scope or unavailable trust refuses. Test signatures prove verification only; official
activation remains unavailable. Source trust creates no tenant membership or caller grants.

Direct institutional definition PUT and external historical monthly-policy admission remain
unavailable. This delivery does not backdate policy, reconstruct R7/797 history, qualify financial
facts or supply the missing actual 797 native amendment packet. Report controlled v6 is independent.

## Deployment configuration and lifecycle

`DPM_COMPOSITE_ATTESTATION_VERIFICATION_JSON` is a deployment-owned JSON object with these fields:

| Field | Required contract |
| --- | --- |
| `verifier` | Existing `SourceBinding`: operation `verification`, HTTPS endpoint without userinfo/fragment, tenant, owner service, issuer URI, receipt issuer, service principal, credential environment variable, pinned Ed25519 public keys, explicit revoked credentials/subjects and posture `QUALIFIED_RECEIPT` |
| `verifier.verification_purposes` | Exactly `COMPOSITE_ECONOMIC_AUTHORITY_PROFILE`, `RETURN_METHOD_CALENDAR`, `PROVIDER_REGISTRATION` |
| `signer` | Tenant, original issuer URI and issuer identity, independent service principal and public keys, explicit revoked credentials/subjects; operation `attestation`, posture `QUALIFIED_RECEIPT` |
| `revocation` | Revision, UTC `checked_at`/`expires_at` and explicit `revoked_artifact_digests` array; empty arrays are explicit status, omitted status refuses |
| `timeout_seconds` | Optional, default 2, bounded 0.1–30 |
| `maximum_response_bytes` | Optional, default 2,000,000, bounded 1,024–8,000,000 |

UTC timestamps use microsecond precision and `Z`. Admission requires
`checked_at <= admitted_at < expires_at <= checked_at + five minutes`, checked before and after
remote verification. Signer and verifier must have distinct principals and non-overlapping keys.
The HTTPS transport uses normal certificate verification; there is no plaintext institutional
test exception. Requests cannot supply a trust configuration or nominate a keyset.

The application parses deployment configuration during service composition. Operators must supply
current authoritative status and refresh configuration before expiry; no revocation feed or key
discovery service is inferred. Absent configuration/transport credentials returns unavailable;
invalid configuration refuses composition; stale status refuses new admission. Retain the exact
public configuration, keysets and revocation snapshot addressed by the receipt digests for audit.
Do not include the transport credential value in that archive. Rotation affects new admissions;
existing immutable receipts remain readable and exact retries return retained evidence without
claiming that its historical trust status is current.

`DPM_COMPOSITE_SOURCES_JSON` continues to admit only synthetic source bindings. Its candidate and
monthly source-cut semantics do not become qualified because the separate verifier is enabled.
Caller authentication, tenant scope, finalizer/maker-checker rules and grants remain separate.

## Signed wire and retained proof

Manage POSTs the complete `CompositeInstitutionalVerificationRequest/v2` to the configured endpoint.
The response envelope is exactly `owner_service`, `payload`, `credential`. `payload` is a strict
`CompositeInstitutionalVerificationResult/v2`; the fresh compact Ed25519 JWS binds the complete
request and payload using the existing platform principal-credential wire. Issuer, audience
`lotus-manage`, tenant, service principal, operation, validity window, credential identity and
posture must match deployment trust.

The result retains `CompositeAuthorityAttestationArtifact/v1` and `original_credential`. The
artifact's self-hash excludes only its `content_hash`; the original signature binds the complete
artifact, including that hash, to `{attestation_id, revision}`. The signature validity window must
contain the preserved approval instant. Current signer/key/credential/artifact revocation still
applies. The original approval time must not be in the future. A fresh signed echo cannot supply
this original signature.

The full definition binds profile digest, approval claims and original reference, including all
selected provider facts, product cuts and method/calendar selection. Separate existing v1 method
and per-selection provider verification requests require qualified responses matching the exact
requested artifact revision and digest. Those related receipts retain their existing wire contract;
this does not claim to archive the provider's underlying financial data or certify its economics.
The v2 retained decoder repeats that exact artifact equality on every related receipt, including
joined reads, resolver reads and replay. Recomputed self-hashes cannot substitute a different
artifact revision or digest for the bound method or provider registration.

The local `CompositeEvidenceVerificationReceipt/v2` retains the original artifact/credential,
fresh verifier credential, configuration/keyset/revocation digests and admission timestamps. It is
the first verification in `CompositeEligibilityFinalization/v2`; remaining related receipts stay v1.
The outer `CompositeEligibilityFinalizationReceipt/v2` keeps the existing product name and custody
fields. Readers dispatch explicitly by `product_version`; absent version retains the existing v1
default, while null/unknown versions refuse. Existing publication locks, transaction rollback,
canonical sequence and exact joined-custody reads apply. The current JSON custody tables need no
new migration or authority ledger. Completeness remains `UNVERIFIED` and activation `UNAVAILABLE`.

## Local verification

From the `lotus-manage` checkout, with its development environment active:

```powershell
python -m pytest tests/unit/dpm/infrastructure/test_composite_institutional_verifier.py tests/unit/dpm/composites/test_institutional_finalization.py -q --no-cov
make static-quality-gates
```

```bash
python -m pytest tests/unit/dpm/infrastructure/test_composite_institutional_verifier.py tests/unit/dpm/composites/test_institutional_finalization.py -q --no-cov
make static-quality-gates
```

Offline controlled keys exercise real signatures over mock HTTP, tampering, revocation, missing
trust, version compatibility, replay and concurrency. They establish verification behavior, not
native HTTPS/PostgreSQL restart evidence or genuine historical institutional/source authority.
