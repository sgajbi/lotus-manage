# Security and Governance

What protects `lotus-manage`, what is off unless switched on, and what a deployment must supply.
Measured against `main` in
[`src/api/enterprise_readiness.py`](https://github.com/sgajbi/lotus-manage/blob/main/src/api/enterprise_readiness.py).

## The controlling fact: write authorization is off by default

`write_authorization_required` returns true only when **`ENTERPRISE_ENFORCE_AUTHZ`** is enabled, and
its default is `"false"`. With the variable unset, **every write reaches its handler unauthorized** —
no headers required, no service identity, no capability check.

Reads are never authorized by this layer at all, in any configuration. The authorization surface
covers `POST`, `PUT`, `PATCH` and `DELETE` only.

There is **no runtime-profile guard**: nothing raises the requirement because the deployment calls
itself production. `lotus-report` does have one — it forces enforcement for `prod`, `production`,
`preprod`, `staging` and `uat` profiles — so a Manage deployment that omits the toggle fails open
where the same omission in Report fails closed. Tracked as
[#649](https://github.com/sgajbi/lotus-manage/issues/649).

Treat enabling `ENTERPRISE_ENFORCE_AUTHZ` as a deployment requirement, not an option.

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

Some route families do **not** rely on `ENTERPRISE_ENFORCE_AUTHZ` and enforce identity themselves.
These are the strongest controls in the service, because they hold whatever the enterprise toggle
says:

| family | control |
|---|---|
| PM operating quality | builds a trusted identity from `X-Actor-Id`, `X-Tenant-Id` and `X-Role`, then asserts the request body's `requested_by` **matches the header actor**. A body cannot nominate a different actor than the caller presented. |
| Bulk-review campaign definitions | `campaign_trusted_context_required` rejects a request with no `X-Tenant-Id`, returning `400 BULK_REVIEW_CAMPAIGN_TRUSTED_TENANT_REQUIRED`, and the same requirement applies when resolving persisted definitions. |

The principle both encode is worth generalising when new routes are added: **the tenant and actor
come from the trusted headers, and the request body may not override them.** Where a route takes a
tenant or actor in its payload, that value is validated against the header rather than used in place
of it.

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
| feature flags | `ENTERPRISE_FEATURE_FLAGS_JSON` |

Two of these enforcement toggles default to `false`, so a deployment that sets neither gets
validation that reports issues without acting on them. That is a deliberate migration affordance;
it is not a posture to run a bank on.

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
