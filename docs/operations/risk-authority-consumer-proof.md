# Protected Risk consumer pilot

## Scope

Manage binds admitted caller context to concentration, regime-scenario and risk-event-cohort
requests. This is an explicitly enabled local/dev **header-trust pilot**, not verified bank
identity, portfolio authorization or production readiness. Risk owns calculations and source
supportability. Manage does not forward inbound credentials or infer Risk permission from a
Manage capability.

## Admission configuration

Configure both services explicitly. Run commands from their respective repository roots.

| Manage setting | Required value |
|---|---|
| `ENTERPRISE_ENFORCE_AUTHZ` | `true` |
| `PRINCIPAL_RESOLUTION_POSTURE` | `header-trust` |
| `ENVIRONMENT` | `local` or `dev` |
| `APP_PERSISTENCE_PROFILE` | `LOCAL` |
| `ENTERPRISE_POLICY_VERSION` | Explicit deployment policy revision |
| `DPM_RISK_CONSUMER_SERVICE_IDENTITY` | Deployment-owned consumer identity |
| `DPM_RISK_BASE_URL` | Admitted Risk endpoint |
| `DPM_RISK_REQUIRED_CAPABILITIES_JSON` | Exact mapping below |

```json
{
  "concentration": "risk.concentration",
  "regime_scenario": "risk.regime",
  "risk_event_cohort": "risk.cohort"
}
```

These names are synthetic examples, not built-in grants. Match each value to Risk's configured
`ENTERPRISE_CAPABILITY_RULES_JSON` for its corresponding protected POST route. Configure Manage's
own route capability separately. Caller `X-Capabilities` must include the relevant Risk grant;
`manage.write` alone is insufficient. Missing, malformed or incomplete mappings refuse calls.

Only after existing enterprise write admission succeeds does middleware retain typed actor,
tenant, role, correlation and the subset of explicitly mapped caller capabilities. Outbound
headers use that context and the deployment-owned service identity. Shared HTTP-pool headers
remain identity-neutral. `Authorization` is never forwarded or persisted.

## Construction replay

`RISK_AWARE` and `REGIME_STRESS_AWARE` commands bind idempotency to admitted actor, tenant,
role, consumer identity, policy and mapped grants. Diagnostic correlation and grant ordering do
not change business identity. Changed authority under the same key returns `409` before engine
or downstream execution. Historical unbound command hashes conflict; historical GET remains
readable. Non-Risk construction hashes are unchanged. No credentials enter the fingerprint.

Synchronous waves pass admission context to child construction; completed-wave replay reads the
original transition, not a new calculation or renewed grant. Use a new command for changed inputs.
Risk-event creation evaluates the protected producer before persistence or replay.

## Durable operations

Migration `0043` adds nullable context and hash columns without rewriting historical admissions.
New qualified admissions bind context to operation actor, tenant and correlation. Exact replay
requires identical admission context; changed grants or policy conflict. Workers retrieve the
original context by admitted tenant and operation identity. Worker claims cannot replace it.
Recovery checks the retained hash and current deployment-policy fingerprint before a protected
call. Historical operations without context remain readable but cannot acquire Risk authority.
The operation retains original admission correlation; existing item calls use
`<operation-id>:<wave-item-id>` as their diagnostic correlation, not the replacement worker's ID.

Header-trust claims have **no verified issuer, grant-store provenance, expiry or revocation**.
They are not signed delegated principals. `verified`, production and unconfigured postures refuse
protected calls rather than converting credentials to trusted headers. Manage #786 and the
Platform/Risk verified-principal dependencies remain open for that acceptance.

## Evidence boundary

Concentration consumes Risk's exact `ConcentrationRiskReport:v1` metadata and explicit
`source_service=lotus-risk`; missing or incompatible identity fails closed. It does not infer a
methodology version. Missing issuer coverage remains qualified, not a zero-risk assertion.

Unit guards cover pre-transport refusal, immutable admission/replay, policy change and concurrent
tenant isolation. PostgreSQL tests cover repository restart and expired-claim recovery. The
registered HTTP proof exercises all three operations, API-process termination, label-checked
PostgreSQL restart, retained custody and independent numeric controls against an immutable Risk
export. A skipped optional proof is not successful integration evidence.
Neither unit results nor this pilot certify ingress, IAM, live bank integration or capacity.
The separate construction-replay HTTP/PostgreSQL matrix uses an owned unavailable endpoint;
it verifies custody and conflicts across API restarts, not Risk calculation correctness.

### Reproduce the isolated proof

From the Manage repository (PowerShell or Bash), run:

```text
python -m pytest tests/integration/dpm/supportability/test_risk_authority_network.py -q -W error --junitxml=<temp-dir>/risk-proof.xml
```

Supply the prerequisites below explicitly; the test never starts or borrows a Risk runtime.

| Environment input | Requirement |
|---|---|
| `DPM_POSTGRES_INTEGRATION_DSN`, `DPM_POSTGRES_INTEGRATION_REQUIRED=1` | Owned disposable PostgreSQL, not a shared database |
| `DPM_ACTUAL_RISK_REQUIRED=1`, `DPM_ACTUAL_RISK_URL` | Enforced real Risk API, loopback only |
| `DPM_ACTUAL_RISK_SOURCE_DIR`, `DPM_ACTUAL_RISK_ARCHIVE` | Unmodified LF `git archive` of Risk `067df854b05e2ea5e54e8409fa9efde22d9bb7d7` |
| `DPM_ACTUAL_RISK_AUDIT` | Real producer's enterprise audit JSONL sink |
| `DPM_ACTUAL_RISK_RESTART_POSTGRES=1` | Explicit destructive fault-injection consent for the owned database |
| `DPM_ACTUAL_RISK_POSTGRES_CONTAINER`, `DPM_ACTUAL_RISK_POSTGRES_OWNER` | Exact container and matching `lotus.proof.owner` label |

The archive SHA-256 is `6292bf41c23780c8b62d5c6125ab1b5e7645892afff0bc7b3208cefe7fa410de`.
Every exported source byte is checked before and after proof. The PostgreSQL container must also
carry the matching `lotus.proof.risk_revision`, loopback binding and database identity. Use only
synthetic identities and caller-supplied financial/health inputs. JUnit retains source responses
and recovery identities; capture the exact Manage candidate revision alongside it. Remove only
the recorded owned processes/container/volume after proof and verify ports are released.
