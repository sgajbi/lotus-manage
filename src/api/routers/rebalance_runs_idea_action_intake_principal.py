from __future__ import annotations

from typing import Annotated, NoReturn

from fastapi import Depends, Header, status

from src.api.routers.rebalance_runs_idea_action_intake_http import idea_action_problem

from src.core.rebalance_runs.idea_action_intake_authority import (
    IDEA_ACTION_INTAKE_ACCEPT_CAPABILITY,
    IDEA_ACTION_INTAKE_READ_CAPABILITY,
    IDEA_ACTION_INTAKE_REVIEW_CAPABILITY,
    IdeaActionIntakePrincipal,
)

IDEA_ACTION_INTAKE_PRINCIPAL_REQUIRED = "IDEA_ACTION_INTAKE_PRINCIPAL_REQUIRED"
IDEA_ACTION_INTAKE_PRINCIPAL_INVALID = "IDEA_ACTION_INTAKE_PRINCIPAL_INVALID"
IDEA_ACTION_INTAKE_ROLE_NOT_AUTHORIZED = "IDEA_ACTION_INTAKE_ROLE_NOT_AUTHORIZED"
IDEA_ACTION_INTAKE_CAPABILITY_REQUIRED = "IDEA_ACTION_INTAKE_CAPABILITY_REQUIRED"
IDEA_ACTION_INTAKE_SERVICE_IDENTITY_REQUIRED = "IDEA_ACTION_INTAKE_SERVICE_IDENTITY_REQUIRED"
IDEA_ACTION_INTAKE_PORTFOLIO_SCOPE_REQUIRED = "IDEA_ACTION_INTAKE_PORTFOLIO_SCOPE_REQUIRED"

_ACCEPT_ROLES = frozenset({"SERVICE"})
_READ_ROLES = frozenset({"SERVICE", "PORTFOLIO_MANAGER", "DPM_MANAGER", "INVESTMENT_COUNSELLOR"})
_REVIEW_ROLES = frozenset({"PORTFOLIO_MANAGER", "DPM_MANAGER"})


def resolve_idea_action_principal(
    x_actor_id: Annotated[str, Header(min_length=1)],
    x_role: Annotated[str, Header(min_length=1)],
    x_tenant_id: Annotated[str, Header(min_length=1)],
    x_legal_entity_code: Annotated[str, Header(min_length=1)],
    x_service_identity: Annotated[str, Header(min_length=1)],
    x_capabilities: Annotated[str, Header(min_length=1)],
    x_portfolio_ids: Annotated[str, Header(min_length=1)],
    x_correlation_id: Annotated[str | None, Header()] = None,
    x_principal_status: Annotated[str | None, Header()] = None,
) -> IdeaActionIntakePrincipal:
    if (x_principal_status or "ACTIVE").strip().upper() != "ACTIVE":
        _raise_authn(IDEA_ACTION_INTAKE_PRINCIPAL_INVALID)
    portfolio_ids = _csv_set(x_portfolio_ids)
    if not portfolio_ids:
        _raise_authn(IDEA_ACTION_INTAKE_PORTFOLIO_SCOPE_REQUIRED)
    return IdeaActionIntakePrincipal(
        actor_id=_required_header(x_actor_id),
        role=_required_header(x_role).upper(),
        tenant_id=_required_header(x_tenant_id),
        legal_entity_code=_required_header(x_legal_entity_code).upper(),
        correlation_id=_optional_header(x_correlation_id) or "route-correlation-pending",
        service_identity=_required_header(x_service_identity),
        capabilities=frozenset(_csv_set(x_capabilities)),
        portfolio_ids=frozenset(portfolio_ids),
    )


def require_idea_action_intake_principal(
    principal: IdeaActionIntakePrincipal = Depends(resolve_idea_action_principal),
) -> IdeaActionIntakePrincipal:
    _authorize(
        principal,
        capability=IDEA_ACTION_INTAKE_ACCEPT_CAPABILITY,
        roles=_ACCEPT_ROLES,
    )
    if principal.service_identity != "lotus-idea":
        _raise_authz(IDEA_ACTION_INTAKE_SERVICE_IDENTITY_REQUIRED)
    return principal


def require_idea_action_read_principal(
    principal: IdeaActionIntakePrincipal = Depends(resolve_idea_action_principal),
) -> IdeaActionIntakePrincipal:
    _authorize(
        principal,
        capability=IDEA_ACTION_INTAKE_READ_CAPABILITY,
        roles=_READ_ROLES,
    )
    return principal


def require_idea_action_review_principal(
    principal: IdeaActionIntakePrincipal = Depends(resolve_idea_action_principal),
) -> IdeaActionIntakePrincipal:
    _authorize(
        principal,
        capability=IDEA_ACTION_INTAKE_REVIEW_CAPABILITY,
        roles=_REVIEW_ROLES,
    )
    return principal


def _authorize(
    principal: IdeaActionIntakePrincipal,
    *,
    capability: str,
    roles: frozenset[str],
) -> None:
    if principal.role not in roles:
        _raise_authz(IDEA_ACTION_INTAKE_ROLE_NOT_AUTHORIZED)
    if capability not in principal.capabilities:
        _raise_authz(IDEA_ACTION_INTAKE_CAPABILITY_REQUIRED)


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


def _csv_set(value: str | None) -> set[str]:
    return {part.strip() for part in (value or "").split(",") if part.strip()}


def _raise_authn(detail: str) -> NoReturn:
    raise idea_action_problem(
        status_code=status.HTTP_401_UNAUTHORIZED,
        reason_code=detail,
        detail="Trusted Idea action principal is missing or invalid.",
    )


def _raise_authz(detail: str) -> NoReturn:
    raise idea_action_problem(
        status_code=status.HTTP_403_FORBIDDEN,
        reason_code=detail,
        detail="Trusted Idea action principal is not authorized for this operation.",
    )


__all__ = [
    "IDEA_ACTION_INTAKE_CAPABILITY_REQUIRED",
    "IDEA_ACTION_INTAKE_PORTFOLIO_SCOPE_REQUIRED",
    "IDEA_ACTION_INTAKE_PRINCIPAL_INVALID",
    "IDEA_ACTION_INTAKE_PRINCIPAL_REQUIRED",
    "IDEA_ACTION_INTAKE_ROLE_NOT_AUTHORIZED",
    "IDEA_ACTION_INTAKE_SERVICE_IDENTITY_REQUIRED",
    "require_idea_action_intake_principal",
    "require_idea_action_read_principal",
    "require_idea_action_review_principal",
    "resolve_idea_action_principal",
]
