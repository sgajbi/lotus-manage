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
from pydantic import AfterValidator

MANDATE_TENANT_QUERY_DESCRIPTION = (
    "Tenant whose mandate evidence is being read. Required: mandate snapshots and health "
    "snapshots are stored per tenant, and the same mandate id may exist under more than one "
    "tenant. Send it as the canonical snake_case query parameter `tenant_id`."
)


def normalise_mandate_tenant(value: str) -> str:
    """Strip a stated tenant, refusing one that is only whitespace.

    Normalisation belongs to the type rather than to a helper each route must
    remember to call: `tenant_id=%20tenant-a` and `tenant_id=tenant-a` name one
    tenant, and treating them as two silently partitions that tenant's own
    evidence - reads miss rows stored under the unpadded form while writes
    persist into a padded namespace nothing later reads. Every surface that
    accepts a tenant gets this by construction (issue #648).
    """

    stripped = value.strip()
    if not stripped:
        raise ValueError("tenant_id must contain a non-whitespace character")
    return stripped


# The same rule for a tenant arriving in a request body. Query, header and body
# are three doors into the same store, so a tenant that normalises on one and not
# the others still partitions that tenant's evidence.
NormalisedTenantId = Annotated[str, AfterValidator(normalise_mandate_tenant)]

MandateTenantId = Annotated[
    str,
    Query(
        # min_length alone admits "%20": whitespace is a character. This
        # pattern requires the value to CONTAIN a non-whitespace character, so
        # a blank is refused at the boundary rather than becoming a tenant no
        # legitimate caller can ever match again. Padding is normalised by the
        # validator below rather than refused, so a caller that pads is
        # answered from its own tenant instead of a private empty one.
        #
        # Anchored forms are wrong here: `^\s*\S.*$` rejects a trailing newline,
        # because the engine backing this pattern does not match `$` before one.
        # The type would then refuse a value the validator would have normalised,
        # which is the same door-by-door disagreement this module exists to stop.
        pattern=r"\S",
        min_length=1,
        description=MANDATE_TENANT_QUERY_DESCRIPTION,
        examples=["default"],
    ),
    AfterValidator(normalise_mandate_tenant),
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
    # One normaliser, so a surface reached through here and a surface typed as
    # MandateTenantId cannot disagree about what counts as the same tenant.
    return normalise_mandate_tenant(tenant_id)


__all__ = [
    "MANDATE_TENANT_QUERY_DESCRIPTION",
    "MandateTenantId",
    "NormalisedTenantId",
    "normalise_mandate_tenant",
    "DpmMandateTenantRequiredError",
    "require_mandate_tenant",
]
