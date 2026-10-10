# Historical policy admission engineering draft

This directory contains generated schemas and deterministic **controlled test history** examples for the bounded #778 engineering slice. These are draft consumer implementation inputs, not released producer support or genuine institutional acceptance. Production original-format adapters remain **UNAVAILABLE**, consumer release enablement is **NOT_ADMITTED**, completeness is **UNVERIFIED** and official activation is **UNAVAILABLE**. Applied migrations, protected CI, exact-main qualification and consumer compatibility evidence are required before release.

## Versions and immutable boundaries

| Family | New contract | Required nesting |
|---|---|---|
| Monthly policy proposal/approval | v2 | Independent present admission retains the original externally approved history |
| Monthly evaluation proposal/approval/receipt | v3 | Ordinary root, exact policy approval v2, fresh operation verification |
| Monthly evaluation proposal/approval/receipt | v4 | Source correction, identical policy approval v2, fresh operation verification, original root v3 and predecessor v3/v4 |

Frozen ordinary monthly v1, source correction v2 and all existing staged products retain their bytes, hashes and meaning. Explicit null/unknown versions refuse. No old/new chain mixing, staged-root bridge, retrospective policy change, new ledger or implicit institutional profile exists here. Root remains the original v3; every correction binds the selected predecessor's exact approval and receipt, with matching versions and expected publication sequence. Membership and universe remain v1 products with exact references to the actual monthly approval version/digest.

## Original bytes, normalized mapping and current evidence

For a monthly receipt, let `P=/approval/proposal/policy_approval` (the policy approval v2).

| Meaning | JSON pointer in receipt |
|---|---|
| Exact original bytes, base64 | `P/proposal/verification/mapping/raw_original_base64` |
| SHA256 of decoded original bytes | `P/proposal/verification/mapping/reference/raw_digest` |
| Original issuer/artifact/revision/signing contract | `P/proposal/verification/mapping/reference` |
| Original credential in its actual owner format | `P/proposal/verification/mapping/original_credential` |
| Verified normalized policy and original approval instant | `P/proposal/verification/mapping/policy`, `P/proposal/verification/mapping/original_approved_at` |
| Present policy proposal/approval instants | `P/proposal/proposed_at`, `P/approved_at` |
| Current policy proposal/admission approval proofs | `P/proposal/verification`, `P/verification` |
| Current evaluation proposal/approval proofs | `/approval/proposal/operation_verification`, `/approval/operation_verification` |
| Exact correction lineage | `/lineage` and identical `/approval/proposal/amendment` (v4 only) |

`P` is an explanatory prefix: substitute its full pointer when consuming the paths. The original signing contract is **not** a newly invented normalized JWS. The trusted source-format adapter must verify the actual original credential over the actual original bytes according to the source owner's contract and independently attest the normalized mapping. This draft ships no production source-format adapter. Test support verifies a controlled raw-byte Ed25519 format and cannot be selected by production configuration.

The normalized proof has its own independent Ed25519 credential: base64 of the 64-byte signature over the ASCII `sha256:<hex>` canonical digest of the entire typed proof, excluding only root `content_hash` and root `verifier_credential`. Include defaults, every nested hash, original bytes/credential, complete request, trust/configuration/key digests, explicit original-signature/current-revocation statuses and freshness fields. `verifier_public_key_base64` encodes the 32-byte public key, whose raw-byte SHA256 must equal `verifier_key_digest`. Fresh admission also compares server-port trust pins; embedded keys alone are not trust or bank authorization. The retained decoder verifies the normalized credential and its recorded admission interval without pretending historical expiry is current authority.

Each request binds exact scope, original locator/digest/signing contract, current actor/revision/time and `intent_digest`. Policy proposal intent binds reference plus proposal revision; its scope/month/policy/currency are separately explicit and signed. Policy approval intent is the exact policy proposal hash. Evaluation proposal intent hashes its complete typed unsigned proposal excluding root `content_hash` and `operation_verification`; evaluation approval intent is the exact evaluation proposal hash. Every final model's own hash excludes only its root self-hash, retaining all nested hashes and credentials. These acyclic bindings prevent a verifier credential from being reused for another operation or intent after envelope rehashing.

Current writes require fresh verification and exact server pins. Same-intent retained retries and exact historical reads preserve their original evidence without requiring a fresh source. Historical evidence does not become a reusable current grant. A qualified-looking proof does not promote the supported synthetic policy profile, source population/cut compatibility, bank IAM or official activation.

## Digest algorithms and reproducible exports

`manifest.json` explicitly separates:

- `canonical_content_digests`: `sha256:` plus SHA256 of UTF-8 `json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True)` for each JSON value. Pretty file bytes are intentionally different.
- `raw_file_sha256`: SHA256 of the exact exported UTF-8 file bytes, without BOM, with sorted keys, two-space indentation, LF and one final newline. The manifest itself is sealed separately by the handoff's SHA256 to avoid a self-reference cycle.

From the `lotus-manage` checkout, use the repository Python environment:

```powershell
python -m tests.composite_historical_policy_contracts docs/contracts/composite-historical-policy
python -m tests.composite_historical_policy_contracts docs/contracts/composite-historical-policy --check
```

```bash
python -m tests.composite_historical_policy_contracts docs/contracts/composite-historical-policy
python -m tests.composite_historical_policy_contracts docs/contracts/composite-historical-policy --check
```

The check compares actual bytes and both digest inventories. Meaningful tests accept valid exports and refuse CRLF conversion, content tampering, missing/extra JSON files and manifest mutation. CRLF inside the decoded original artifact is intentional controlled source data and remains preserved in its base64 representation.
