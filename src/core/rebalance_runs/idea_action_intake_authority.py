from __future__ import annotations

from dataclasses import dataclass
from typing import Any

IDEA_ACTION_INTAKE_ACCEPT_CAPABILITY = "manage.idea_action_intake.accept"
IDEA_ACTION_INTAKE_READ_CAPABILITY = "manage.idea_action_intake.read"
IDEA_ACTION_INTAKE_REVIEW_CAPABILITY = "manage.idea_action_intake.review"
IDEA_ACTION_INTAKE_AUTHORIZED_ROLES = frozenset(
    {"PORTFOLIO_MANAGER", "DPM_MANAGER", "INVESTMENT_COUNSELLOR", "SERVICE"}
)


@dataclass(frozen=True)
class IdeaActionIntakePrincipal:
    actor_id: str
    role: str
    tenant_id: str
    legal_entity_code: str
    correlation_id: str
    service_identity: str
    capabilities: frozenset[str]
    portfolio_ids: frozenset[str]

    def audit_metadata(self, *, capability: str) -> dict[str, Any]:
        return {
            "subject": self.actor_id,
            "role": self.role,
            "tenant_id": self.tenant_id,
            "legal_entity_code": self.legal_entity_code,
            "correlation_id": self.correlation_id,
            "service_identity": self.service_identity,
            "capability": capability,
            "portfolio_ids": sorted(self.portfolio_ids),
        }

    def can_access_portfolio(self, portfolio_id: str) -> bool:
        return portfolio_id in self.portfolio_ids


__all__ = [
    "IDEA_ACTION_INTAKE_ACCEPT_CAPABILITY",
    "IDEA_ACTION_INTAKE_AUTHORIZED_ROLES",
    "IDEA_ACTION_INTAKE_READ_CAPABILITY",
    "IDEA_ACTION_INTAKE_REVIEW_CAPABILITY",
    "IdeaActionIntakePrincipal",
]
