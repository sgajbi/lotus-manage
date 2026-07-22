from __future__ import annotations

from typing import Annotated, NoReturn

from fastapi import Header, HTTPException, status

from src.core.rebalance_runs.idea_action_intake_authority import (
    IDEA_ACTION_INTAKE_ACCEPT_CAPABILITY,
    IDEA_ACTION_INTAKE_AUTHORIZED_ROLES,
    IdeaActionIntakePrincipal,
)

IDEA_ACTION_INTAKE_PRINCIPAL_REQUIRED = "IDEA_ACTION_INTAKE_PRINCIPAL_REQUIRED"
IDEA_ACTION_INTAKE_PRINCIPAL_INVALID = "IDEA_ACTION_INTAKE_PRINCIPAL_INVALID"
IDEA_ACTION_INTAKE_ROLE_NOT_AUTHORIZED = "IDEA_ACTION_INTAKE_ROLE_NOT_AUTHORIZED"
IDEA_ACTION_INTAKE_CAPABILITY_REQUIRED = "IDEA_ACTION_INTAKE_CAPABILITY_REQUIRED"


def require_idea_action_intake_principal(
    x_actor_id: Annotated[str, Header(min_length=1)],
    x_role: Annotated[str, Header(min_length=1)],
    x_tenant_id: Annotated[str, Header(min_length=1)],
    x_legal_entity_code: Annotated[str, Header(min_length=1)],
    x_service_identity: Annotated[str, Header(min_length=1)],
    x_capabilities: Annotated[str, Header(min_length=1)],
    x_correlation_id: Annotated[str | None, Header()] = None,
    x_principal_status: Annotated[str | None, Header()] = None,
) -> IdeaActionIntakePrincipal:
    actor_id = _required_header(x_actor_id)
    role = _required_header(x_role).upper()
    tenant_id = _required_header(x_tenant_id)
    legal_entity_code = _required_header(x_legal_entity_code).upper()
    correlation_id = _optional_header(x_correlation_id) or "route-correlation-pending"
    service_identity = _required_header(x_service_identity)
    capabilities = _capability_set(x_capabilities)

    if (x_principal_status or "ACTIVE").strip().upper() != "ACTIVE":
        _raise_authn(IDEA_ACTION_INTAKE_PRINCIPAL_INVALID)
    if role not in IDEA_ACTION_INTAKE_AUTHORIZED_ROLES:
        _raise_authz(IDEA_ACTION_INTAKE_ROLE_NOT_AUTHORIZED)
    if IDEA_ACTION_INTAKE_ACCEPT_CAPABILITY not in capabilities:
        _raise_authz(IDEA_ACTION_INTAKE_CAPABILITY_REQUIRED)

    return IdeaActionIntakePrincipal(
        actor_id=actor_id,
        role=role,
        tenant_id=tenant_id,
        legal_entity_code=legal_entity_code,
        correlation_id=correlation_id,
        service_identity=service_identity,
        capabilities=frozenset(capabilities),
    )


def _required_header(value: str | None) -> str:
    normalized = _optional_header(value)
    if normalized is None:
        _raise_authn(IDEA_ACTION_INTAKE_PRINCIPAL_REQUIRED)
    return normalized


def _optional_header(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _capability_set(value: str | None) -> set[str]:
    return {part.strip() for part in (value or "").split(",") if part.strip()}


def _raise_authn(detail: str) -> NoReturn:
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


def _raise_authz(detail: str) -> NoReturn:
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


__all__ = [
    "IDEA_ACTION_INTAKE_CAPABILITY_REQUIRED",
    "IDEA_ACTION_INTAKE_PRINCIPAL_INVALID",
    "IDEA_ACTION_INTAKE_PRINCIPAL_REQUIRED",
    "IDEA_ACTION_INTAKE_ROLE_NOT_AUTHORIZED",
    "require_idea_action_intake_principal",
]
