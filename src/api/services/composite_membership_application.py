"""Application boundary for Manage-owned composite eligibility source records."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from src.core.composite_membership import (
    DpmCompositeDefinition,
    DpmCompositeMembershipDecision,
    DpmCompositeMembershipRevision,
    DpmCompositeSourceAuthority,
)
from src.core.composite_repository import DpmCompositeRepository


class DpmCompositeNotFoundError(ValueError):
    """Raised when a tenant-scoped composite source record does not exist."""


@dataclass(frozen=True)
class DpmCompositeDefinitionCommand:
    tenant_id: str
    composite_id: str
    definition_version: str
    display_name: str
    strategy_code: str
    reporting_currency: str
    inception_date: str
    termination_date: str | None
    eligibility_policy_version: str
    source_authority: DpmCompositeSourceAuthority
    actor_id: str
    correlation_id: str


@dataclass(frozen=True)
class DpmCompositeMembershipRevisionCommand:
    tenant_id: str
    composite_id: str
    definition_version: str
    membership_revision: str
    policy_version: str
    source_cut_id: str
    decisions: list[DpmCompositeMembershipDecision]
    actor_id: str
    correlation_id: str
    supersedes_membership_revision: str | None
    affected_from: str | None
    affected_to: str | None


@dataclass(frozen=True)
class DpmCompositeMembershipApplicationService:
    repository: DpmCompositeRepository

    def save_definition(self, *, command: DpmCompositeDefinitionCommand) -> DpmCompositeDefinition:
        definition = DpmCompositeDefinition(
            tenant_id=command.tenant_id,
            composite_id=command.composite_id,
            definition_version=command.definition_version,
            display_name=command.display_name,
            strategy_code=command.strategy_code,
            reporting_currency=command.reporting_currency,
            inception_date=command.inception_date,
            termination_date=command.termination_date,
            eligibility_policy_version=command.eligibility_policy_version,
            source_authority=command.source_authority,
            created_by=command.actor_id,
            correlation_id=command.correlation_id,
        )
        self.repository.save_definition(definition=definition)
        return definition

    def get_definition(
        self, *, tenant_id: str, composite_id: str, definition_version: str
    ) -> DpmCompositeDefinition:
        definition = self.repository.get_definition(
            tenant_id=tenant_id,
            composite_id=composite_id,
            definition_version=definition_version,
        )
        if definition is None:
            raise DpmCompositeNotFoundError("COMPOSITE_DEFINITION_NOT_FOUND")
        return definition

    def list_definitions(
        self, *, tenant_id: str, limit: int, offset: int
    ) -> list[DpmCompositeDefinition]:
        return self.repository.list_definitions(tenant_id=tenant_id, limit=limit, offset=offset)

    def save_membership_revision(
        self, *, command: DpmCompositeMembershipRevisionCommand
    ) -> DpmCompositeMembershipRevision:
        revision = DpmCompositeMembershipRevision(
            tenant_id=command.tenant_id,
            composite_id=command.composite_id,
            definition_version=command.definition_version,
            membership_revision=command.membership_revision,
            policy_version=command.policy_version,
            source_cut_id=command.source_cut_id,
            decisions=command.decisions,
            decided_by=command.actor_id,
            correlation_id=command.correlation_id,
            supersedes_membership_revision=command.supersedes_membership_revision,
            affected_from=command.affected_from,
            affected_to=command.affected_to,
        )
        self.repository.save_membership_revision(revision=revision)
        return revision

    def get_membership_revision(
        self,
        *,
        tenant_id: str,
        composite_id: str,
        definition_version: str,
        membership_revision: str,
    ) -> DpmCompositeMembershipRevision:
        revision = self.repository.get_membership_revision(
            tenant_id=tenant_id,
            composite_id=composite_id,
            definition_version=definition_version,
            membership_revision=membership_revision,
        )
        if revision is None:
            raise DpmCompositeNotFoundError("COMPOSITE_MEMBERSHIP_REVISION_NOT_FOUND")
        return revision

    def list_membership_revisions(
        self,
        *,
        tenant_id: str,
        composite_id: str,
        definition_version: str,
        limit: int,
        offset: int,
    ) -> list[DpmCompositeMembershipRevision]:
        return self.repository.list_membership_revisions(
            tenant_id=tenant_id,
            composite_id=composite_id,
            definition_version=definition_version,
            limit=limit,
            offset=offset,
        )

    def membership_as_of(
        self,
        *,
        tenant_id: str,
        composite_id: str,
        definition_version: str,
        membership_revision: str,
        as_of_date: str,
    ) -> list[DpmCompositeMembershipDecision]:
        revision = self.get_membership_revision(
            tenant_id=tenant_id,
            composite_id=composite_id,
            definition_version=definition_version,
            membership_revision=membership_revision,
        )
        requested = date.fromisoformat(as_of_date)
        return [
            decision
            for decision in revision.decisions
            if date.fromisoformat(decision.effective_from) <= requested
            and (
                decision.effective_to is None
                or requested <= date.fromisoformat(decision.effective_to)
            )
        ]
