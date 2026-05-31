from __future__ import annotations

from typing import Any


RouteResponses = dict[int | str, dict[str, Any]]

POLICY_RESOLUTION_DESCRIPTION = (
    "Returns the effective discretionary mandate policy-pack resolution using configured "
    "precedence: request-scoped `X-Policy-Pack-Id`, tenant default "
    "`X-Tenant-Policy-Pack-Id` or tenant resolver lookup by `X-Tenant-Id`, then global default. "
    "Use this read-only endpoint for supportability and integration diagnostics before invoking "
    "rebalance execution. Supply resolution context via the documented headers rather than query "
    "parameters; unsupported query parameters are rejected."
)

POLICY_CATALOG_DESCRIPTION = (
    "Returns the configured discretionary mandate policy-pack catalog from the governed "
    "PostgreSQL policy-pack repository plus the effective selection context for optional request "
    "and tenant headers. Use this endpoint when operators or downstream integration checks need "
    "to confirm which policy packs are available and whether the selected policy pack is present. "
    "Supply resolution context via the documented headers rather than query parameters; "
    "unsupported query parameters are rejected."
)

POLICY_CATALOG_ITEM_DESCRIPTION = (
    "Returns one discretionary mandate policy-pack definition from the governed PostgreSQL "
    "policy-pack repository by identifier. Use this read-only route when an operator, Gateway "
    "integration, or certification probe already has a policy-pack id and needs the exact "
    "turnover, tax, settlement, constraint, workflow, and idempotency controls that would be "
    "applied by execution; unsupported query parameters are rejected."
)

POLICY_CATALOG_UPSERT_DESCRIPTION = (
    "Creates or updates one discretionary mandate policy-pack definition in the governed "
    "PostgreSQL policy-pack repository. This is an operator/admin control-plane endpoint and is "
    "available only when `DPM_POLICY_PACK_ADMIN_APIS_ENABLED=true`; keep it disabled in normal "
    "runtime unless policy governance operations are explicitly required. The path identifier is "
    "authoritative; unsupported query parameters are rejected."
)

POLICY_CATALOG_DELETE_DESCRIPTION = (
    "Deletes one discretionary mandate policy-pack definition from the governed PostgreSQL "
    "policy-pack repository. This is an operator/admin control-plane endpoint and is available "
    "only when `DPM_POLICY_PACK_ADMIN_APIS_ENABLED=true`; use it for governed cleanup of obsolete "
    "mandate policy packs, not for advisory proposal lifecycle workflows; unsupported query "
    "parameters are rejected."
)

POLICY_RESOLUTION_RESPONSES: RouteResponses = {
    200: {"description": "Effective policy-pack selection and resolution source."},
    422: {"description": "Unsupported query parameters were supplied."},
}

POLICY_CATALOG_RESPONSES: RouteResponses = {
    200: {"description": "Policy-pack catalog with effective selection context."},
    503: {"description": "Policy-pack repository is unavailable or not configured."},
    422: {"description": "Unsupported query parameters were supplied."},
}

POLICY_CATALOG_ITEM_RESPONSES: RouteResponses = {
    200: {"description": "Requested policy-pack definition."},
    404: {"description": "Policy-pack identifier was not found."},
    422: {"description": "Unsupported query parameters were supplied."},
    503: {"description": "Policy-pack repository is unavailable or not configured."},
}

POLICY_CATALOG_UPSERT_RESPONSES: RouteResponses = {
    200: {"description": "Policy-pack definition created or updated."},
    404: {"description": "Policy-pack admin APIs are disabled for this runtime."},
    422: {
        "description": "Request body validation failed or unsupported query parameters were supplied."
    },
    503: {"description": "Policy-pack repository is unavailable or not configured."},
}

POLICY_CATALOG_DELETE_RESPONSES: RouteResponses = {
    204: {"description": "Policy-pack definition was deleted."},
    404: {"description": "Policy-pack admin APIs are disabled or the policy pack was not found."},
    422: {"description": "Unsupported query parameters were supplied."},
    503: {"description": "Policy-pack repository is unavailable or not configured."},
}
