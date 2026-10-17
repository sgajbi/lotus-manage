# Configured Composite eligibility sources

Historical monthly-policy verification uses its own
[normalized provider configuration and protocol](composite-historical-provider.md).
That channel can explicitly select the native controlled-original adapter and opt-in read-only
custody overlay described there. It supplies independent historical admission only; it does not
enable the separate native candidate/monthly adapter below or upgrade per-fact authority.
It does not widen the source operations or verification purposes described here.

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

### Tracked Compose configuration delivery

The `lotus-manage` application environment in `docker-compose.yml` and its
`docker-compose.production.yml` overlay passes through these operator-supplied settings:
`DPM_COMPOSITE_SOURCES_JSON`, `DPM_COMPOSITE_HISTORICAL_POLICY_ADMISSION_JSON` and
`DPM_COMPOSITE_ATTESTATION_VERIFICATION_JSON`. The isolated `ci-local` service in
`docker-compose.ci-local.yml` exposes the same settings for its owning test process.
Unset or blank values remain blank; the existing loaders keep the corresponding channel
unavailable. No fixture, issuer, key, tenant or approval is selected by default. Malformed or
unsupported configuration still refuses during composition.

The same JSON channel also admits the explicit controlled native v2 document described below.
It does not enable the unrelated stateful Core rebalance resolver or replace historical admission.

Supply the reviewed JSON through the operator's existing Compose interpolation environment
before the admitted deployment. The same tracked service environments also pass through these
controlled-profile credential variables with blank defaults:

| JSON channel | Explicit `credential_env` in the reviewed profile |
| --- | --- |
| Source-provider binding | `MANAGE_COMPOSITE_SOURCE_AUTH` |
| Historical admission | `MANAGE_HISTORICAL_PROVIDER_AUTH` |
| Attestation verifier, when applicable | `MANAGE_COMPOSITE_ATTESTATION_AUTH` |
| Native assembler reader A | `MANAGE_COMPOSITE_CORE_ASSEMBLY_AUTH` |
| Independent native verifier reader C | `MANAGE_COMPOSITE_CORE_VERIFIER_AUTH` |

The loader does not select these names automatically: each controlled JSON binding must name
its matching variable explicitly. The operator separately provisions its actual credential value;
no secret, provider, principal, trust or approval is supplied by this wiring. Missing or blank
credentials remain unavailable before transport. Other arbitrary host credential names are not
automatically forwarded by Compose. Do not publish evaluated environment JSON or credentials.
The reader grant remains separate and does not authorize writing or approval.

For canonical deployment, follow Platform's reviewed incremental-refresh runbook and existing
reservation; preserve port 8001, Core source bindings and migration-first startup. Configuration
delivery is not provider/trust/principal qualification or live financial acceptance. The static
Compose and loader contracts can be checked from the repository root in PowerShell or Bash
using the project Python environment:

```text
make test-unit UNIT_TESTS=tests/unit/test_local_docker_runtime_contract.py
```

These checks parse the tracked application models and exercise loader admission/refusal without
Docker. Actual evaluated Compose, immutable image, PostgreSQL startup and native workflow proof
remain the deployment owner's responsibility.

### Native deployment document

Use `adapter: CONTROLLED_SYNTHETIC_NATIVE_ASSEMBLY_V2` in the existing
`DPM_COMPOSITE_SOURCES_JSON`. The closed model is
[`NativeAssemblyConfiguration`](../../src/infrastructure/composites/native_assembly_configuration.py).
The ordinary subject and recurring monthly factories select it; no request can select configuration
or trust. Legacy `CompositeSourceConfiguration` documents without `adapter` remain supported by
their signed provider protocol below. Blank JSON keeps both native candidate and monthly ports
unavailable. Duplicate members, unknown fields/discriminators and malformed policy refuse.

| Field | Deployment responsibility |
| --- | --- |
| `adapter` | Exactly `CONTROLLED_SYNTHETIC_NATIVE_ASSEMBLY_V2`. |
| `financial` | Exact tenant/composite/definition/strategy/month/currency, registry cut and ordered explicit member→provider/financial-cut mappings; pins come from the admitted producer. |
| `reader` | Reader A's origin, tenant, real credential reference, `authentication_mode: core_enterprise_hmac_v1`, bounded page/attempt/byte settings and explicit local HTTP admission only for synthetic loopback IPs. |
| `verification` | Independently supplied C2 `financial`, `reader`, `expected_observations_digest`, `trust` and `revocation`; never derive the expected digest from A's output or a caller. |
| `assembly_authorization` | Reader A's public Core context policy, with matching origin/tenant/credential reference, service identity `lotus-manage`, actor, role, key ID and both fixed native capabilities. |
| `verification_authorization` | Reader C's separately configured context policy with the same per-reader agreement; it authenticates the Core consumer, not the monthly verifier principal. |
| `verifier_key_file` | Absolute runtime path to a separately provisioned, effectively read-only, exact 32-byte Ed25519 monthly signer matching C2's public verifier key. |
| `timeout_seconds` | Bounded0.1–30 second request timeout; existing `DPM_COMPOSITE_HTTP_*`/`DPM_SOURCE_HTTP_*` connection and pool limits still apply. |
| `policy_verification` | Optional separate legacy synthetic verification-only bindings for generic policy purposes; no monthly purpose and no shared enrolled source/monthly principal or public key. |

A and C must pin identical financial documents. Each reader and auth policy must agree on tenant,
origin, credential reference and local HTTP admission. Both real credentials and the matching
monthly signer are required before native candidate admission can reserve a subject; absence or
blank credentials/missing custody stays unavailable before network or reservation. Unsafe writable,
linked, oversize or mismatched signer custody refuses. An OS chmod alone under a privileged user
does not establish effective read-only custody. No key is generated or replaced by composition.

C2 trust explicitly supplies tenant, issuer, receipt issuer, monthly verifier principal, audience
`lotus-manage`, purpose `COMPOSITE_MONTHLY_SOURCE_CUT`, operation `verification`, synthetic posture,
verifier public key/key-validity interval and actual source principal/key inventories. The current
unsigned native artifact catalog permits explicit `source_keys: []`; omission/null is invalid and
does not enroll an artifact signer. Source principals remain required and distinct from the monthly
verifier. Revocation has a named revision, checked/expiry instants within at most five minutes and
explicit credential/subject/key-digest inventories. Current admission checks use server time.
Deployment must retain these public pins and snapshots for provenance; no request/proof key enrolls
fresh trust. C2 independently refetches/rebuilds the entire source cut for each fresh monthly request.

### Native Core transport and monthly proof

Reader A and reader C use separately partitioned managed clients, no shared reader/result/proof
cache, explicit `follow_redirects=False`, `trust_env=False` and TLS verification. Existing bounded
timeouts/limits and application shutdown own both clients. Credentials resolve freshly on each
request; rotation/withdrawal has no last-success fallback. Native HTTPS origins have no user info,
query, fragment or path prefix. Private CA/routing admission is an operator prerequisite; disabling
TLS or inheriting a proxy is not a supported workaround.

The current network consumer remains `lotus-manage`. Both readers use Core's existing context
HMAC-v1 on exactly these POSTs, with both capabilities:

| Native path | Required capability |
| --- | --- |
| `/integration/portfolio-historical-registries/query` | `source_data.portfolio_historical_registry.read` |
| `/integration/financial-source-cuts/query` | `source_data.portfolio_financial_source_cut.read` |

`CoreRetainedReadAuth` supplies fresh timestamp/correlation and the exact governed nine-line UTF-8
context signature. It sends no `Authorization` header; do not fabricate a bearer credential or put
an HMAC/private key into that header. Core separately admits signature, service/tenant, capabilities,
feature flags and exact source-read grants. HMAC signs context, not route/body/replay protection or
financial approval. The independent monthly Ed25519 signer never travels to Core. An arbitrary
injected Auth/client is not an IAM claim; owning no-follow clients are required because Auth alone
cannot constrain an arbitrary client's internal redirect behavior.

Native `CompositeMonthlyEligibilityAssembly/v2` adds complete retained registry/member/raw capture,
typed financial input, role/root and compatibility custody to the five-role assembly. C2 returns one
immutable receipt/proof pair; `source_assembly_evidence.native_proof` carries the independently
admitted `CompositeMonthlySourceAdmissionProof/v1` and its signed result/current admission pins.
It is monthly-only. Generic policy, historical original and institutional verification keep separate
authorities. Native proof is required for assemblyv2 and forbidden on assemblyv1. Existing v1
assembly/evaluation/hash semantics and legacy omission behavior remain unchanged; no historical
credential or receipt is reissued. All native results remain synthetic/non-certifying and official
activation unavailable; native custody does not qualify Core facts or a bank population.

Monthly native admission requires a complete consumed financial-input population for every exact
pinned manifest. Manage groups retained declarations by tenant, product/version and full source
address/revision/batch hash, then checks that each group's unique, canonically ordered portfolio
inputs reproduce both the manifest's `selection_count` and `PortfolioFinancialSourceCutInputs:v1`
ordered root. Observation envelopes and flow cuts must also use the selected graph's definition.
Complete single-input cuts, complete shared batches and disjoint complete multi-cut groups are
supported. A complete monthly registry alone does not prove a financial batch's membership.

Core's selected INPUTS view is valid selected-read evidence; its one-input root is not the full
batch root. A larger/superset batch, incomplete overlapping groups, or a rehashed substituted input
refuses before monthly assembly or independent proof signing. Manage does not infer missing IDs,
fetch mutable/latest cuts, or duplicate full witnesses per portfolio. General selected-subset proof
support requires an agreed producer evidence contract through Core #1227 and Manage #778; it is
not supplied by this bounded consumer validation. Individual selected reads remain intermediate
evidence and do not establish signed monthly acceptance.

### Opt-in monthly signer overlay

Base, production and CI environments forward the two named A/C credential references with blank
defaults. They never mount or select a native signer automatically. The operator provisions actual
credential values through the admitted secret mechanism and explicitly names the corresponding
variables in both reader/auth documents. Arbitrary host variables are not forwarded.

Add `docker-compose.composite-native.yml` only for a reviewed native deployment. It requires a
nonblank `DPM_COMPOSITE_SOURCES_JSON` and host file reference
`MANAGE_COMPOSITE_MONTHLY_VERIFIER_KEY_FILE`; the latter is Compose interpolation only, not a new
application setting. It mounts only the application's `manage_composite_monthly_verifier_key` secret
at `/run/secrets/manage_composite_monthly_verifier_key` with mode0400. Set the JSON `verifier_key_file`
to that container path. The historical overlay's `manage_composite_verifier_key` and originals
directory are separate custody. No credentials or signer are forwarded to PostgreSQL. Compose
configuration validation checks interpolation/model shape; the loader/current custody checks own
JSON, effective permissions, key match and live authority admission.

From the `lotus-manage` root, use an existing project environment and separately reviewed public JSON
file/private-key **file reference**. These commands only evaluate configuration and print no
expanded credentials. Provision the two A/C environment credentials separately before runtime use.

```powershell
Set-Location "$env:LOTUS_WORKSPACE_ROOT/lotus-manage"
$nativeConfigFile = Read-Host "Absolute reviewed public configuration file"
$env:DPM_COMPOSITE_SOURCES_JSON = Get-Content -LiteralPath $nativeConfigFile -Raw
$env:MANAGE_COMPOSITE_MONTHLY_VERIFIER_KEY_FILE = Read-Host "Absolute monthly signer file"
docker compose -f docker-compose.yml -f docker-compose.composite-native.yml config --quiet
```

```bash
cd "$LOTUS_WORKSPACE_ROOT/lotus-manage"
read -r -p "Absolute reviewed public configuration file: " native_config_file
export DPM_COMPOSITE_SOURCES_JSON="$(cat "$native_config_file")"
read -r -p "Absolute monthly signer file: " MANAGE_COMPOSITE_MONTHLY_VERIFIER_KEY_FILE
export MANAGE_COMPOSITE_MONTHLY_VERIFIER_KEY_FILE
docker compose -f docker-compose.yml -f docker-compose.composite-native.yml config --quiet
```

For the production model insert `-f docker-compose.production.yml` between base and native overlay.
The overlay targets `lotus-manage`; it is not a `ci-local` signer mount. CI credential forwarding is
only process environment delivery; the owning isolated test runtime must supply its own explicit
read-only synthetic custody. Do not dump evaluated Compose environments, print signer bytes, create
fallback keys, or deploy before the existing runtime reservation/refresh and trust admission.

### Native evidence and release boundaries

[`test_core_financial_sources_postgres.py`](../../tests/integration/dpm/composites/test_core_financial_sources_postgres.py)
uses separate UUID databases for staged admission and published recurring history. Retained
controlled Docker/HTTP/PostgreSQL evidence proves clean staged default-off refusal/no reservation,
identical configured candidate admission and exact source-off/default-off restart replay. The owning
recurring-only Docker/HTTP/PostgreSQL campaign also passed with zero skips: seeded membership
already has publication sequence1, and C2 denial preserved that exact baseline and absent proposal.
Recovery retained independent refetch/native proof, exact economics, checker publication/resolution
and replay without fresh source calls. Test existence or source/mock receipts do not establish
that campaign's live result; its [retained owner evidence](https://github.com/sgajbi/lotus-manage/issues/778#issuecomment-6220647430)
records the actual synthetic consumer pass. This uses a synthetic retained provider, not the actual
Core service or bank authority.

With an admitted isolated PostgreSQL DSN, effective read-only synthetic custody and owning runtime
approval, the existing native target can execute that file. Working directory is `lotus-manage`;
the command is the same in PowerShell and POSIX shells:

```text
make test-integration INTEGRATION_TESTS=tests/integration/dpm/composites/test_core_financial_sources_postgres.py
```

Actual Core IAM/native financial acceptance, producer protocol/vector and contract promotion,
Manage consumer/schema/vocabulary release closure, Performance source admission/calculation and
merged-main qualification remain separate gates. This guide changes no producer, consumer, issued
proof, financial methodology or supported-readiness claim.

### Read-only Report service

The existing published-evidence resolver uses POST to carry an exact immutable binding; it is a
read, not an approval. With `ENTERPRISE_ENFORCE_AUTHZ=true`, deployment-owned
`DPM_COMPOSITE_READ_SERVICE_GRANTS_JSON` enrolls a dedicated reader. The default `[]` grants
nothing. A controlled example is:

```json
[{"service_identity":"synthetic-report-read-service","actor_id":"synthetic-report-read-actor","tenant_id":"synthetic-tenant"}]
```

Each entry has exactly these three nonblank single-assertion strings; service identities must be
unique. Invalid JSON, extra fields, malformed values or duplicate identities refuse the entire
read enrollment. Provision a separate service identity for each admitted tenant/actor tuple.
This is a trusted-ingress header assertion boundary, **not cryptographic service authentication
or bank IAM certification**. The ingress must strip caller-controlled authority headers and admit
the configured service independently. Merely possessing these example strings is not bank authority.

Report supplies exactly one of each header: `X-Service-Identity`, `X-Actor-Id`, `X-Tenant-Id`,
`X-Role: REPORT_COMPOSITE_READER`, `X-Capabilities: manage.read`, and `X-Correlation-Id`.
The configured actor/service and admitted tenant must match the enrollment. Do not propagate caller
roles/capabilities, reuse writer credentials, or grant `manage.write`. Duplicate or comma-joined
identity headers refuse. The dedicated read rule precedes legacy prefix rules independently of JSON
insertion order. Ordinary writers retain existing authorization requirements.

Let `D=/api/v1/rebalance/composites/{composite_id}/definitions/{definition_version}`. The service
may call only the following exact paths, with conservative identifier segments of 1–256 ASCII
letters/digits/dots/underscores/hyphens beginning with a letter or digit:

| Method | Path | Meaning |
| --- | --- | --- |
| GET | `D` | Pinned immutable definition for Report source context |
| GET | `D/membership/{membership_revision}` | Pinned membership or its full parent |
| GET | `D/membership/{membership_revision}/universe-attestations/{attestation_version}` | Published universe |
| GET | `D/monthly-eligibility/evaluations/{evaluation_revision}` | Exact retained evaluated-only proposal |
| POST | `D/eligibility-evidence/resolve` | Exact-binding published receipt |
| GET | `/api/v1/rebalance/composites/publications/{sequence}` | Positive integer publication cursor |

Extra segments, trailing slashes and percent-encoded paths refuse. The same enrolled identity
cannot mutate any record or use other protected operations, even if it asserts a writer role or
capability. GET and POST outcomes use the existing enterprise audit envelope. Custody still verifies
the exact tenant, product, revision, digest, membership, universe and publication binding; reader
enrollment does not change source qualification or grant approval authority.

`tests/unit/api/test_composite_read_authority.py` covers valid and adversarial admission. The existing
three-month v1/v2 native PostgreSQL history test also performs all six reads, foreign/missing
assertion refusals, same-reader mutation denials and publication equality before/after reads and
refusals. The native economic matrix also checks exact evaluated-only proposal reads and refuses
approval/suffix and mutation paths for the same service. Those direct HTTP tests prove Manage behavior; actual configured Report-client transport
is a separately recorded joined acceptance requirement under #795 and Report #417.

For the legacy signed-provider path, set `DPM_COMPOSITE_SOURCES_JSON` to a strict
`CompositeSourceConfiguration` JSON document without `adapter`. The
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

## Legacy signed response binding

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

## Legacy complete monthly assembly contract

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
