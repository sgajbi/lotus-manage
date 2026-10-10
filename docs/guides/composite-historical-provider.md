# Historical monthly-policy normalized provider

Manage supports dedicated HTTPS transport for its existing historical verification port. The
independent provider resolves the immutable original, verifies its actual source-owned signing
format and returns a signed normalized proof. Manage validates the proof and retains exact custody.
This transport does not implement an original-format verifier or certify a provider, source, bank
identity, methodology or official activation.

## Deployment and trust

`DPM_COMPOSITE_HISTORICAL_POLICY_ADMISSION_JSON` contains strict `HistoricalPolicyConfiguration`.
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
