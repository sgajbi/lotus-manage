"""Application boundary for Manage-owned composite eligibility source records."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Literal

from src.core.composite_membership import (
    DpmCompositeDefinition,
    DpmCompositeMembershipDecision,
    DpmCompositeMembershipRevision,
    DpmCompositeSourceAuthority,
)
from src.core.composite_repository import DpmCompositeConflictError, DpmCompositeRepository
from src.core.composite_publication import (
    DpmCompositeMembershipPublication,
    DpmCompositePublicationPage,
    DpmCompositePublicationReceipt,
    DpmCompositePublicationReconciliation,
)


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
class DpmCompositeReceiptCommand:
    tenant_id: str
    publication_sequence: int
    membership_content_hash: str
    consumer_id: str
    receipt_evidence_hash: str
    disposition: Literal["RECEIVED", "REJECTED"]
    reason_code: str | None
    correlation_id: str


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
        try:
            self.repository.save_definition(definition=definition)
        except DpmCompositeConflictError:
            original = self.repository.get_definition(
                tenant_id=command.tenant_id,
                composite_id=command.composite_id,
                definition_version=command.definition_version,
            )
            if original is None or not _same_command_except_server_time(
                original, definition, server_time_field="created_at"
            ):
                raise
            return original
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
        try:
            self.repository.save_membership_revision(revision=revision)
        except DpmCompositeConflictError:
            original = self.repository.get_membership_revision(
                tenant_id=command.tenant_id,
                composite_id=command.composite_id,
                definition_version=command.definition_version,
                membership_revision=command.membership_revision,
            )
            if original is None or not _same_command_except_server_time(
                original, revision, server_time_field="decided_at"
            ):
                raise
            return original
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

    def get_publication(
        self, *, tenant_id: str, sequence: int
    ) -> DpmCompositeMembershipPublication:
        publication = self.repository.get_publication(tenant_id=tenant_id, sequence=sequence)
        if publication is None:
            raise DpmCompositeNotFoundError("COMPOSITE_PUBLICATION_NOT_FOUND")
        return publication

    def list_publications(
        self, *, tenant_id: str, after_sequence: int, limit: int
    ) -> DpmCompositePublicationPage:
        return self.repository.list_publications(
            tenant_id=tenant_id, after_sequence=after_sequence, limit=limit
        )

    def acknowledge_receipt(
        self, *, command: DpmCompositeReceiptCommand
    ) -> tuple[DpmCompositePublicationReceipt, bool]:
        receipt = DpmCompositePublicationReceipt(
            tenant_id=command.tenant_id,
            publication_sequence=command.publication_sequence,
            membership_content_hash=command.membership_content_hash,
            consumer_id=command.consumer_id,
            receipt_evidence_hash=command.receipt_evidence_hash,
            disposition=command.disposition,
            reason_code=command.reason_code,
            correlation_id=command.correlation_id,
            received_at=datetime.now(timezone.utc),
        )
        created = self.repository.save_receipt(receipt=receipt)
        if created:
            return receipt, True
        existing = next(
            (
                item
                for item in self.repository.list_receipts(
                    tenant_id=command.tenant_id,
                    publication_sequence=command.publication_sequence,
                )
                if item.consumer_id == command.consumer_id
            ),
            None,
        )
        if existing is None:
            raise DpmCompositeConflictError("COMPOSITE_RECEIPT_STORE_INCONSISTENT")
        return existing, False

    def publication_reconciliation(
        self, *, tenant_id: str, sequence: int
    ) -> DpmCompositePublicationReconciliation:
        publication = self.get_publication(tenant_id=tenant_id, sequence=sequence)
        receipts = self.repository.list_receipts(tenant_id=tenant_id, publication_sequence=sequence)
        required = next(
            (receipt for receipt in receipts if receipt.consumer_id == "lotus-performance"), None
        )
        return DpmCompositePublicationReconciliation(
            publication=publication,
            receipts=receipts,
            consumer_posture=(required.disposition if required else "UNACKNOWLEDGED"),
        )


def _same_command_except_server_time(
    original: DpmCompositeDefinition | DpmCompositeMembershipRevision,
    candidate: DpmCompositeDefinition | DpmCompositeMembershipRevision,
    *,
    server_time_field: str,
) -> bool:
    excluded = {server_time_field, "content_hash"}
    return original.model_dump(exclude=excluded) == candidate.model_dump(exclude=excluded)
