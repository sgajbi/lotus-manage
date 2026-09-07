"""Shared tenant query parameter for tenant-scoped mandate endpoints.

Mandate snapshots and health snapshots are stored per tenant, so every read
must state which tenant it is reading. The parameter is required and has no
default: omitting it is refused rather than answered from an assumed tenant,
because a default tenant is what lets one tenant's identifiers resolve against
another tenant's rows.

The value is a caller-asserted scope, not authenticated authority. It narrows
what a caller reads; it does not prove the caller is entitled to that tenant.
Turning this assertion into a verified principal is tracked separately as the
trusted-principal contract dependency (#624), and nothing here should be read
as already providing that guarantee.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Query

MANDATE_TENANT_QUERY_DESCRIPTION = (
    "Tenant whose mandate evidence is being read. Required: mandate snapshots and health "
    "snapshots are stored per tenant, and the same mandate id may exist under more than one "
    "tenant. Send it as the canonical snake_case query parameter `tenant_id`."
)

MandateTenantId = Annotated[
    str,
    Query(
        min_length=1,
        description=MANDATE_TENANT_QUERY_DESCRIPTION,
        examples=["default"],
    ),
]


class DpmMandateTenantRequiredError(Exception):
    """A mandate read or write was attempted without naming a tenant."""


def require_mandate_tenant(tenant_id: str | None) -> str:
    """Return the stated tenant, refusing rather than assuming one.

    Surfaces that carry an optional tenant for other purposes reach mandate
    evidence through here. Refusing keeps an unattributed request from being
    answered out of another tenant's rows, and keeps an unattributable write
    from persisting a row no tenant can later read.
    """

    if tenant_id is None or not tenant_id.strip():
        raise DpmMandateTenantRequiredError("DPM_MANDATE_TENANT_REQUIRED")
    return tenant_id.strip()


__all__ = [
    "MANDATE_TENANT_QUERY_DESCRIPTION",
    "MandateTenantId",
    "DpmMandateTenantRequiredError",
    "require_mandate_tenant",
]
