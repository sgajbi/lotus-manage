"""Application boundary for Manage-owned composite eligibility source records."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Literal

from src.core.composite_membership import (
    DpmCompositeDefinition,
    DpmCompositeMembershipDecision,
    DpmCompositeMembershipRevision,
    DpmCompositeSourceAuthority,
)
from src.core.composite_definition_versions import (
    CompositeDefinition,
    DpmCompositeDefinitionV2,
)
from src.core.composite_provider_trust import (
    CompositeProviderTrustPort,
    CompositeProviderTrustRequest,
    UnavailableCompositeProviderTrust,
)
from src.core.composite_universe_resolution import reconcile_composite_universe
from src.core.composite_repository import (
    DpmCompositeConflictError,
    DpmCompositeRepository,
    DpmCompositeResultPage,
)
from src.core.composite_publication import (
    DpmCompositeMembershipPublication,
    DpmCompositePublicationPage,
    DpmCompositePublicationReceipt,
    DpmCompositePublicationReconciliation,
)
from src.core.composite_universe import (
    CompositeUniversePosture,
    DpmCompositeUniverseAttestation,
    DpmCompositeUniverseSourceProduct,
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
class DpmCompositeUniverseAttestationCommand:
    tenant_id: str
    composite_id: str
    definition_version: str
    membership_revision: str
    attestation_version: str
    coverage_from: str
    coverage_to: str
    policy_version: str
    source_cut_id: str
    source_products: list[DpmCompositeUniverseSourceProduct]
    posture: CompositeUniversePosture
    expected_portfolio_ids: list[str]
    reason_code: str | None
    actor_id: str
    correlation_id: str


@dataclass(frozen=True)
class DpmCompositeMembershipApplicationService:
    repository: DpmCompositeRepository
    provider_trust: CompositeProviderTrustPort = field(
        default_factory=UnavailableCompositeProviderTrust
    )

    def save_versioned_definition(
        self, *, definition: DpmCompositeDefinitionV2
    ) -> DpmCompositeDefinitionV2:
        """Persist only a scoped profile with an explicitly injected test-only resolver.

        The default remains unavailable. No caller flag or unsigned approval creates
        production trust, and this path never asserts official activation.
        """
        definition = DpmCompositeDefinitionV2.model_validate(definition.model_dump(mode="json"))
        if definition.authority_approval.evidence_kind == "INSTITUTIONAL_ATTESTATION_REFERENCE":
            raise ValueError("COMPOSITE_AUTHORITY_ATTESTATION_VERIFIER_UNAVAILABLE")
        profile = definition.source_authority.payload
        providers = {provider.provider_id: provider for provider in profile.providers}
        for selection in profile.selections:
            provider = providers[selection.provider_id]
            request = CompositeProviderTrustRequest(
                tenant_id=definition.tenant_id,
                provider_id=provider.provider_id,
                registry_revision=provider.registry_revision,
                registry_digest=provider.registry_digest,
                source_product=selection.source_product,
                effective_from=selection.effective_from,
                effective_to=selection.effective_to,
            )
            resolution = self.provider_trust.resolve(request)
            if resolution.posture != "SYNTHETIC_TEST_ONLY":
                raise ValueError("COMPOSITE_PROVIDER_TRUST_UNAVAILABLE")
            if resolution.registration_digest != provider.registry_digest:
                raise ValueError("COMPOSITE_PROVIDER_REGISTRATION_DIGEST_MISMATCH")
        self.repository.save_definition(definition=definition)
        return definition

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
        except DpmCompositeConflictError as exc:
            if str(exc) != "COMPOSITE_DEFINITION_IMMUTABLE_CONFLICT":
                raise
            original = self.repository.get_definition(
                tenant_id=command.tenant_id,
                composite_id=command.composite_id,
                definition_version=command.definition_version,
            )
            if not isinstance(
                original, DpmCompositeDefinition
            ) or not _same_command_except_server_time(
                original, definition, server_time_field="created_at"
            ):
                raise
            return original
        return definition

    def get_definition(
        self, *, tenant_id: str, composite_id: str, definition_version: str
    ) -> CompositeDefinition:
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
    ) -> DpmCompositeResultPage[CompositeDefinition]:
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
        except DpmCompositeConflictError as exc:
            if str(exc) != "COMPOSITE_MEMBERSHIP_REVISION_IMMUTABLE_CONFLICT":
                raise
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
            self.repository.assert_membership_published(revision=original)
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
    ) -> DpmCompositeResultPage[DpmCompositeMembershipRevision]:
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

    def save_universe_attestation(
        self, *, command: DpmCompositeUniverseAttestationCommand
    ) -> DpmCompositeUniverseAttestation:
        attestation = self._prepare_universe_attestation(command=command)
        try:
            self.repository.save_universe_attestation(attestation=attestation)
        except DpmCompositeConflictError as exc:
            if str(exc) != "COMPOSITE_UNIVERSE_ATTESTATION_IMMUTABLE_CONFLICT":
                raise
            original = self.repository.get_universe_attestation(
                tenant_id=command.tenant_id,
                composite_id=command.composite_id,
                definition_version=command.definition_version,
                membership_revision=command.membership_revision,
                attestation_version=command.attestation_version,
            )
            if original is None or not _same_attestation_command(original, attestation):
                raise
            return original
        return attestation

    def _prepare_universe_attestation(
        self, *, command: DpmCompositeUniverseAttestationCommand
    ) -> DpmCompositeUniverseAttestation:
        revision = self.get_membership_revision(
            tenant_id=command.tenant_id,
            composite_id=command.composite_id,
            definition_version=command.definition_version,
            membership_revision=command.membership_revision,
        )
        if command.policy_version != revision.policy_version:
            raise DpmCompositeConflictError("COMPOSITE_UNIVERSE_POLICY_VERSION_MISMATCH")
        if command.source_cut_id != revision.source_cut_id:
            raise DpmCompositeConflictError("COMPOSITE_UNIVERSE_SOURCE_CUT_MISMATCH")
        if len(set(command.expected_portfolio_ids)) != len(command.expected_portfolio_ids):
            raise ValueError("COMPOSITE_UNIVERSE_PORTFOLIO_ID_DUPLICATE")
        expected = sorted(command.expected_portfolio_ids)
        observed, missing, unexpected, gaps = reconcile_composite_universe(
            revision=revision,
            coverage_from=_parse_universe_date(
                command.coverage_from, code="COMPOSITE_UNIVERSE_COVERAGE_FROM_INVALID"
            ),
            coverage_to=_parse_universe_date(
                command.coverage_to, code="COMPOSITE_UNIVERSE_COVERAGE_TO_INVALID"
            ),
            expected_portfolio_ids=expected,
        )
        missing, unexpected, gaps = _validated_discrepancies(
            posture=command.posture,
            missing=missing,
            unexpected=unexpected,
            gaps=gaps,
        )
        return DpmCompositeUniverseAttestation(
            tenant_id=command.tenant_id,
            composite_id=command.composite_id,
            definition_version=command.definition_version,
            membership_revision=command.membership_revision,
            membership_content_hash=revision.content_hash,
            attestation_version=command.attestation_version,
            coverage_from=command.coverage_from,
            coverage_to=command.coverage_to,
            policy_version=command.policy_version,
            source_cut_id=command.source_cut_id,
            source_products=command.source_products,
            posture=command.posture,
            expected_portfolio_ids=expected,
            expected_portfolio_count=len(expected),
            observed_portfolio_count=len(observed),
            missing_portfolio_ids=missing,
            unexpected_portfolio_ids=unexpected,
            coverage_gap_portfolio_ids=gaps,
            reason_code=command.reason_code,
            attested_at=datetime.now(timezone.utc),
            attested_by=command.actor_id,
            correlation_id=command.correlation_id,
        )

    def get_universe_attestation(
        self,
        *,
        tenant_id: str,
        composite_id: str,
        definition_version: str,
        membership_revision: str,
        attestation_version: str,
    ) -> DpmCompositeUniverseAttestation:
        attestation = self.repository.get_universe_attestation(
            tenant_id=tenant_id,
            composite_id=composite_id,
            definition_version=definition_version,
            membership_revision=membership_revision,
            attestation_version=attestation_version,
        )
        if attestation is None:
            raise DpmCompositeNotFoundError("COMPOSITE_UNIVERSE_ATTESTATION_NOT_FOUND")
        return attestation

    def list_universe_attestations(
        self,
        *,
        tenant_id: str,
        composite_id: str,
        definition_version: str,
        membership_revision: str,
        limit: int,
        offset: int,
    ) -> DpmCompositeResultPage[DpmCompositeUniverseAttestation]:
        return self.repository.list_universe_attestations(
            tenant_id=tenant_id,
            composite_id=composite_id,
            definition_version=definition_version,
            membership_revision=membership_revision,
            limit=limit,
            offset=offset,
        )


def _same_command_except_server_time(
    original: DpmCompositeDefinition | DpmCompositeMembershipRevision,
    candidate: DpmCompositeDefinition | DpmCompositeMembershipRevision,
    *,
    server_time_field: str,
) -> bool:
    excluded = {server_time_field, "content_hash"}
    return original.model_dump(exclude=excluded) == candidate.model_dump(exclude=excluded)


def _validated_discrepancies(
    *,
    posture: CompositeUniversePosture,
    missing: list[str],
    unexpected: list[str],
    gaps: list[str],
) -> tuple[list[str], list[str], list[str]]:
    discrepancies = missing or unexpected or gaps
    if posture == "COMPLETE" and discrepancies:
        raise DpmCompositeConflictError("COMPOSITE_UNIVERSE_COMPLETENESS_MISMATCH")
    if posture == "INCOMPLETE" and not discrepancies:
        raise DpmCompositeConflictError("COMPOSITE_UNIVERSE_INCOMPLETE_CONTRADICTED")
    return ([], [], []) if posture == "UNAVAILABLE" else (missing, unexpected, gaps)


def _same_attestation_command(
    original: DpmCompositeUniverseAttestation,
    candidate: DpmCompositeUniverseAttestation,
) -> bool:
    return original.model_dump(exclude={"attested_at", "content_hash"}) == candidate.model_dump(
        exclude={"attested_at", "content_hash"}
    )


def _parse_universe_date(value: str, *, code: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(code) from exc
