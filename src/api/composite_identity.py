"""Shared composite transport admission; upstream bank identity verification is separate."""

from dataclasses import dataclass
from fastapi import Depends, HTTPException, Request, status


@dataclass(frozen=True)
class CompositeTrustedIdentity:
    tenant_id: str
    actor_id: str
    role: str


def composite_trusted_identity_required(request: Request) -> CompositeTrustedIdentity:
    for name in ("X-Tenant-Id", "X-Actor-Id", "X-Role"):
        values = request.headers.getlist(name)
        if len(values) != 1 or "," in values[0]:
            raise composite_identity_problem(
                status.HTTP_403_FORBIDDEN, "COMPOSITE_TRUSTED_IDENTITY_REQUIRED"
            )
    identity = CompositeTrustedIdentity(
        tenant_id=request.headers.get("X-Tenant-Id", "").strip(),
        actor_id=request.headers.get("X-Actor-Id", "").strip(),
        role=request.headers.get("X-Role", "").strip(),
    )
    if not all((identity.tenant_id, identity.actor_id, identity.role)):
        raise composite_identity_problem(
            status.HTTP_403_FORBIDDEN, "COMPOSITE_TRUSTED_IDENTITY_REQUIRED"
        )
    return identity


def composite_write_identity_required(
    identity: CompositeTrustedIdentity = Depends(composite_trusted_identity_required),
) -> CompositeTrustedIdentity:
    if identity.role not in {"DPM_COMPOSITE_ADMIN", "DPM_PORTFOLIO_MANAGER"}:
        raise composite_identity_problem(
            status.HTTP_403_FORBIDDEN, "COMPOSITE_WRITE_ROLE_FORBIDDEN"
        )
    return identity


def composite_identity_problem(status_code: int, code: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": code})
