# Ordinary Core request context

Ordinary stateful Core reads can opt into Core's existing enterprise HMAC-v1 context. Defaults
remain unsigned. Core owns route capabilities and admission; this configuration does not qualify
financial sources, Composite custody, bank IAM or institutional authority.

## Deployment enrollment

| Setting | Default / enabled requirement |
| --- | --- |
| `CORE_EXECUTION_ENABLED` | `false`; only true/1 or false/0, case-insensitive and trimmed |
| `CORE_EXECUTION_KEY_ID` | Blank; exact Core-enrolled key ID |
| `CORE_EXECUTION_SECRET` | Blank; separately provisioned secret, never committed or printed |
| `CORE_EXECUTION_SERVICE_IDENTITY` | Blank; exact source-admitted service, ordinarily `lotus-manage` |
| `CORE_EXECUTION_ACTOR_ID` | Blank; server-owned actor |
| `CORE_EXECUTION_ROLE` | Blank; server-owned role |
| `CORE_EXECUTION_ALLOWED_TENANTS` | Blank; nonempty exact unique JSON string array |
| `CORE_EXECUTION_CAPABILITIES` | Blank; nonempty exact unique JSON string array of Core-owned capabilities |

All three tracked Compose files forward these settings with false/blank defaults. Blank enabled
fields, malformed arrays, duplicates, wildcards and unsafe identities refuse locally. Disabled
mode does not parse unused authority fields. Operator enrollment must include the actual canonical
tenant alongside isolated synthetic tenants; never derive tenant from a portfolio ID. Ask Core's
owner for effective route capabilities and strictness; Manage does not maintain a parallel catalog.

Enabled mode requires explicit distinct `DPM_CORE_BASE_URL` (QCP origin) and
`DPM_CORE_QUERY_BASE_URL` (unsigned query origin), with HTTP/HTTPS origins only and no userinfo,
path, query or fragment. HTTPS verifies TLS; private-network HTTP deployment remains an explicit
operator trust decision. No query-to-QCP fallback is admitted in enabled configuration. The
cashflow projection remains on the query plane. Preserve the existing stateful-source flags and
selectors; query authentication tenant does not change global fact ownership.

Only admitted tenant and validated correlation reach execution authority. Actor, service, role and
capabilities come from server configuration; merged caller/default authority headers refuse.
No pooled authority mutation occurs. Ordinary policy partitions reuse managed shutdown, disable
environment proxies and redirects, and verify TLS. Injected transports are trusted application
dependencies and must preserve TLS verification; environment-proxy clients refuse and redirects
are disabled per request. The direct fallback has identical signing and safe HTTP configuration.

Every wire attempt resolves the current secret and signs a current timestamp. Missing/blank or
removed secret refuses locally; a well-formed wrong secret, stale signature or revoked remote key
requires Core verifier refusal. Authentication failures and redirects never retry or downgrade.
Read retries retain transport/502/503/504 semantics, with enabled attempts restricted to1..3 and
finite per-stage timeout in(0,60] seconds. A290-second monotonic budget refuses additional attempts
and late responses; HTTPX synchronous per-stage timeouts bound network waits, rather than a
preemptive cancellation of an arbitrary injected transport. Context HMAC does not bind route/body
or establish replay prevention; Core independently enforces tenant, product and capability rules.

Native Composite A/C keeps separate credentials, retained-read policy, two exact POST targets and
capabilities. Only the HMAC wire primitive is shared. Monthly verification keys never travel to Core.

## Verification and rollout

From the `lotus-manage` repository root, PowerShell or Bash:

```text
make test-unit UNIT_TESTS=tests/unit/dpm/infrastructure/test_core_request_context.py
make lint
make typecheck
```

Focused tests use synthetic in-process transport and `docker compose config` only; no daemon or
business HTTP is contacted. Do not print evaluated Compose with real credentials. Root alone owns
deployment activation/rollback and the live canonical stateful source flow under enforcing Core,
with exact resource preservation. Protected PR/Main CI, actual deployment and independent retained
A/C proof remain required before issue closure; source/mock tests cannot establish live readiness.
