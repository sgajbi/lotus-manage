# Security and Governance

What protects `lotus-manage`, what is off unless switched on, and what a deployment must supply.
Measured against `main` in
[`src/api/enterprise_readiness.py`](https://github.com/sgajbi/lotus-manage/blob/main/src/api/enterprise_readiness.py).

## How authorization is actually gated

Two mechanisms decide whether a write is authorized, and reading only one of them gives the wrong
answer.

### 1. Startup guardrails bind the production profile

`validate_persistence_profile_guardrails()` runs during application lifespan
([`src/api/main.py`](https://github.com/sgajbi/lotus-manage/blob/main/src/api/main.py)). When
`APP_PERSISTENCE_PROFILE=PRODUCTION` it **raises and the service does not start** unless all of the
following hold:

| requirement | error when missing |
|---|---|
| supportability store is Postgres | `PERSISTENCE_PROFILE_REQUIRES_DPM_POSTGRES` |
| a Postgres DSN is configured | `PERSISTENCE_PROFILE_REQUIRES_DPM_POSTGRES_DSN` |
| the Postgres access policy validates | *(policy-specific)* |
| **`ENTERPRISE_ENFORCE_AUTHZ` is enabled** | `PERSISTENCE_PROFILE_REQUIRES_ENTERPRISE_AUTHZ` |
| `ENTERPRISE_PRIMARY_KEY_ID` is set | `PERSISTENCE_PROFILE_REQUIRES_ENTERPRISE_PRIMARY_KEY_ID` |
| capability rules are loaded | `PERSISTENCE_PROFILE_REQUIRES_ENTERPRISE_CAPABILITY_RULES` |

And conditionally, **when `DPM_POLICY_PACKS_ENABLED` or `DPM_POLICY_PACK_ADMIN_APIS_ENABLED` is
set**, the policy-pack catalog must also be Postgres-backed with an explicit DSN:

| requirement | error when missing |
|---|---|
| policy-pack catalog backend is Postgres | `DPM_POLICY_PACK_CATALOG_BACKEND_UNSUPPORTED` — see below |
| `DPM_POLICY_PACK_POSTGRES_DSN` is set explicitly | `PERSISTENCE_PROFILE_REQUIRES_POLICY_PACK_POSTGRES_DSN` |

On the backend check, the error an operator actually sees is not the guardrail's own code.
`policy_pack_catalog_backend_name()` **raises** `DPM_POLICY_PACK_CATALOG_BACKEND_UNSUPPORTED` for any
value other than `POSTGRES`, before `_policy_pack_catalog_guardrail_error()` can compare and return
`PERSISTENCE_PROFILE_REQUIRES_POLICY_PACK_POSTGRES`. Since a `POSTGRES` value passes the comparison,
that guardrail code is unreachable for this condition. Search for
`DPM_POLICY_PACK_CATALOG_BACKEND_UNSUPPORTED` when troubleshooting.

So a production deployment **cannot run with authorization off**. The checked-in production Compose
configuration selects that profile. This is a fail-closed startup gate, and it is stronger than
forcing the toggle on would be: the deployment stops rather than starting in a posture nobody chose.

### 2. Outside that profile, the toggle governs — and defaults to off

`ENTERPRISE_ENFORCE_AUTHZ` defaults to `"false"`. Under `APP_PERSISTENCE_PROFILE=LOCAL`, which is
the default, the enterprise write-authorization layer is skipped entirely: no identity headers, no
service identity, no capability check.

That is not the same as "unauthenticated" for every route. Some route families guard themselves
regardless of the toggle — see [Route-level trusted identity](#route-level-trusted-identity-independent-of-the-toggle).
The accurate statement is:

> With the toggle off, **any write whose route has no local guard** reaches its handler with no
> identity requirement at all.

Reads are never covered by this layer in any configuration; it applies to `POST`, `PUT`, `PATCH`
and `DELETE` only.

## What a write must carry when enforcement is on

Three checks run in order, and the first failure is the reported reason:

| # | check | failure reason |
|---|---|---|
| 1 | all four identity headers present | `missing_headers:<names>` |
| 2 | a service identity present | `missing_service_identity` |
| 3 | the capability the route requires is among those the caller claims | `missing_capability:<name>` |

**Identity headers** — all four are mandatory:

| header | carries |
|---|---|
| `x-actor-id` | who is acting |
| `x-tenant-id` | which tenant |
| `x-role` | the actor's role |
| `x-correlation-id` | the correlation identifier for the request |

**Service identity** is satisfied by either `x-service-identity` or `authorization` being present.
Note what that is and is not: it is a **presence check**. Neither header's value is verified, so this
establishes that a caller declared an identity, not that the identity is genuine. Authentication is
assumed to happen at platform ingress before the request arrives.

**Capabilities** are read from the caller's own `x-capabilities` header, comma-separated. The
requirement for a route comes from `ENTERPRISE_CAPABILITY_RULES_JSON`, whose keys are
`"<METHOD> /<path-prefix>"` and whose values are capability names; the first rule whose method
matches and whose prefix the path starts with decides. A route with no matching rule requires no
capability.

The same caveat applies as to service identity: the caller states its own capabilities. This bounds
what a **correctly behaving** caller does; it does not resist one that lies. Both properties are
blast-radius controls, not identity checks.

## Route-level trusted identity, independent of the toggle

Three families enforce identity themselves, so they hold whatever the enterprise toggle says. They
are **not** equivalent to each other, and the differences matter:

### Idea-action intake — the fullest local checks, but still not authentication

`POST /api/v1/rebalance/idea-action-intake` always runs `require_idea_action_intake_principal`, the
most complete set of local checks on any route here — and it is still **presence and value checking,
not authentication**. `X-Service-Identity` is only required to be non-empty; actor, tenant, role and
capabilities are taken as the caller states them. No credential, signature or token is validated, so
the route does not resist a caller that misrepresents its principal. As everywhere else in this
service, that trust comes from platform ingress, not from here.

Six headers are declared `Header(min_length=1)` and a request missing any one is rejected before the
handler:

`X-Actor-Id` · `X-Role` · `X-Tenant-Id` · `X-Legal-Entity-Code` · `X-Service-Identity` ·
`X-Capabilities`

Three further checks then run, each with its own reason code:

| check | rejection |
|---|---|
| `X-Principal-Status`, defaulting to `ACTIVE` when absent, must be `ACTIVE` | `IDEA_ACTION_INTAKE_PRINCIPAL_INVALID` |
| the role must be `PORTFOLIO_MANAGER`, `DPM_MANAGER`, `INVESTMENT_COUNSELLOR` or `SERVICE` | `IDEA_ACTION_INTAKE_ROLE_NOT_AUTHORIZED` |
| capabilities must include `manage.idea_action_intake.accept` | `IDEA_ACTION_INTAKE_CAPABILITY_REQUIRED` |

The two layers are **additive, not equivalent** — the route does not behave identically across
toggle states:

- with the toggle **off**, `X-Correlation-Id` is optional here and falls back to a placeholder
- with the toggle **on**, the enterprise middleware requires `X-Correlation-Id` as one of its four
  identity headers and rejects the same request as `missing_headers:x-correlation-id` before the
  handler runs, and any configured capability rule for this path applies on top of the route's own
  capability check

So a caller satisfying the enterprise layer's four identity headers is still rejected here without
service identity and capabilities, and a caller satisfying only the route's local contract can be
rejected once enforcement is on. Treat the two contracts as cumulative and send everything both
require.

### PM operating quality — actor is verified against the header

Every mutation builds a trusted identity from `X-Actor-Id`, `X-Tenant-Id` and `X-Role`. Where the
request body carries an actor field, it is compared against `X-Actor-Id` and a mismatch is rejected.
The field name differs by request, which is a payload-contract detail callers need:

| request | field compared against `X-Actor-Id` |
|---|---|
| score run | `actor_id` |
| fairness analysis | `actor_id` |
| review action | `actor_id` |
| summary invocation | `requested_by` |
| policy version (`PUT .../policies/{id}/versions/{version}`) | *none — the body carries no actor* |

For the four request types with an actor field, a body cannot nominate an actor other than the one
the caller presented. The policy mutation has no such field to spoof: it takes tenant scope from the
trusted identity directly, which is the same protection reached a different way.

### Bulk-review campaigns — only the tenant is trusted

`campaign_trusted_context_required` rejects a request with no `X-Tenant-Id`
(`400 BULK_REVIEW_CAMPAIGN_TRUSTED_TENANT_REQUIRED`), and the same applies when resolving persisted
definitions. But `CampaignTrustedContext` carries **only** `tenant_id`. Create, launch and
assignment mutations take `created_by`, `actor_id` or `recorded_by` **from the request body** and do
not compare them to `X-Actor-Id`.

So with enterprise authorization disabled, the recorded actor on a campaign mutation is
caller-controlled. The tenant is trusted; the actor is asserted. Do not read the PM-quality
invariant as applying here.

**For new routes**, the idea-action-intake and PM-quality shapes are the ones to copy: declare the
identity headers as required, take tenant *and* actor from them, and validate any body-supplied
equivalent against them rather than using it in their place. The safest form is the one with no body
actor at all.

PM operating quality is additionally disabled by default; enabled policies require bank approval and
fairness-review evidence, and HR, compensation, conduct-enforcement and autonomous-ranking uses are
prohibited by the product contract. See
[`docs/methodologies/pm-quality/scoring-and-fairness.md`](https://github.com/sgajbi/lotus-manage/blob/main/docs/methodologies/pm-quality/scoring-and-fairness.md).

## Other enterprise controls

| control | mechanism |
|---|---|
| write payload size | `ENTERPRISE_MAX_WRITE_PAYLOAD_BYTES`, compared against `Content-Length` on write methods |
| runtime configuration validation | `validate_enterprise_runtime_config()` collects issues — policy version, secret rotation, authorization key material — and raises `enterprise_runtime_config_invalid` **only when `ENTERPRISE_ENFORCE_RUNTIME_CONFIG` is enabled**, default `"false"` |
| policy version | `ENTERPRISE_POLICY_VERSION` |
| key material and rotation | `ENTERPRISE_PRIMARY_KEY_ID`, `ENTERPRISE_SECRET_ROTATION_DAYS` |

`ENTERPRISE_FEATURE_FLAGS_JSON` is **not** in this table on purpose. `load_feature_flags()` and
`is_feature_enabled()` have no production callers — only their definitions and unit tests — so
configuring tenant or role flags there restricts nothing today. It is unused infrastructure, not a
control.

Both enforcement toggles default to `false`, and outside the `PRODUCTION` profile that combination
is **silent**: `validate_enterprise_runtime_config()` returns its issue list to `main.py`, which
discards it without logging, and with authorization off the key-material check is skipped anyway. A
`LOCAL` deployment with both toggles unset therefore gets neither enforcement nor a warning. The
`PRODUCTION` profile is what turns that silence into a startup failure.

Sensitive fields — `password`, `secret`, `token` and their siblings — are redacted from audit
records rather than logged.

## Governing RFCs

| RFC | Establishes |
|---|---|
| RFC-0066 | the `lotus-advise` / `lotus-manage` split boundary |
| RFC-0067 | centralized OpenAPI and vocabulary governance |
| RFC-0071 | environment-scoped service addressing and ingress posture |
| RFC-0072 | multi-lane CI and release governance |
| RFC-0073 | ecosystem context and agent guidance system |
| RFC-0082 | upstream authority and analytics serving boundary hardening |

## Repo-native guardrails

These run in CI and fail the build, rather than being conventions:

- the no-alias contract guard
- the OpenAPI quality gate
- API vocabulary inventory validation
- migration smoke, part of the repo-native PR-grade contract
- security audit, part of `make ci`

See [Validation and CI](Validation-and-CI) for the lane each belongs to.

## Operational discipline

- keep management and advisory boundaries explicit — the split is governed by RFC-0066, not by
  convention
- do not let the gateway or UI infer capability truth the backend already publishes
- keep generated artifacts truthful; avoid timestamp-only churn in documentation slices

## Read next

1. [Architecture](Architecture) — where the boundaries sit
2. [API Surface](API-Surface) — the routes these controls apply to
3. [Operations Runbook](Operations-Runbook) — running and supporting the service
