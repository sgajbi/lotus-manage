"""Read-only monthly assessment over retained definitions and universe evidence."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable

from pydantic import Field

from src.core.composite_authority_models import (
    Digest,
    EvidenceBinding,
    Identity,
    StrictAuthorityModel,
)
from src.core.composite_eligibility.approval import MonthlyPolicyApproval, MonthlyPolicyProposal
from src.core.composite_eligibility.evaluation import (
    MonthlyEligibilityEvaluation,
    evaluate_monthly_eligibility,
)
from src.core.composite_eligibility.diff import MonthlyEligibilityDiff, compare_monthly_evaluations
from src.core.composite_eligibility.policy import (
    MonthlyPolicyLayer,
    MonthlyPolicyScope,
    ResolvedMonthlyPolicy,
    month_window,
    resolve_monthly_policy,
)
from src.core.composite_eligibility.source import (
    MonthlyEligibilitySourcePort,
    MonthlyEligibilitySourceRequest,
    UnavailableMonthlyEligibilitySource,
    admitted_source_snapshot,
)
from src.core.composite_eligibility.observations import MonthlyEligibilityObservations
from src.core.composite_eligibility.source_assembly import VerifiedMonthlySourceAssembly
from src.core.composite_repository import DpmCompositeConflictError, DpmCompositeRepository
from src.core.composite_definition_versions import CompositeDefinition
from src.core.composite_universe import DpmCompositeUniverseAttestation


class MonthlyPolicyValidationRequest(StrictAuthorityModel):
    month: str
    layers: list[MonthlyPolicyLayer] = Field(min_length=1, max_length=5)


class MonthlySimulationRequest(MonthlyPolicyValidationRequest):
    membership_revision: Identity
    attestation_version: Identity
    universe_content_hash: Digest


class MonthlyDiffRequest(MonthlySimulationRequest):
    baseline_layers: list[MonthlyPolicyLayer] = Field(min_length=1, max_length=5)


class MonthlyProposalRequest(StrictAuthorityModel):
    layers: list[MonthlyPolicyLayer] = Field(min_length=1, max_length=5)
    attachments: list[EvidenceBinding] = Field(min_length=1, max_length=20)


class MonthlyApprovalRequest(StrictAuthorityModel):
    expected_proposal_content_hash: Digest


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


@dataclass(frozen=True)
class CompositeMonthlyEligibilityApplicationService:
    repository: DpmCompositeRepository
    source: MonthlyEligibilitySourcePort = field(
        default_factory=UnavailableMonthlyEligibilitySource
    )
    clock: Callable[[], str] = _utc_now

    def get_policy_proposal(
        self,
        *,
        tenant_id: str,
        composite_id: str,
        definition_version: str,
        month: str,
        proposal_revision: str,
    ) -> MonthlyPolicyProposal:
        result = self.repository.get_monthly_policy_proposal(
            tenant_id=tenant_id,
            composite_id=composite_id,
            definition_version=definition_version,
            month=month,
            proposal_revision=proposal_revision,
        )
        if result is None:
            raise ValueError("COMPOSITE_ELIGIBILITY_PROPOSAL_NOT_FOUND")
        return result

    def get_policy_approval(
        self,
        *,
        tenant_id: str,
        composite_id: str,
        definition_version: str,
        month: str,
    ) -> MonthlyPolicyApproval:
        result = self.repository.get_monthly_policy_approval(
            tenant_id=tenant_id,
            composite_id=composite_id,
            definition_version=definition_version,
            month=month,
        )
        if result is None:
            raise ValueError("COMPOSITE_ELIGIBILITY_APPROVAL_NOT_FOUND")
        return result

    def propose_policy(
        self,
        *,
        tenant_id: str,
        composite_id: str,
        definition_version: str,
        month: str,
        proposal_revision: str,
        actor_id: str,
        command: MonthlyProposalRequest,
    ) -> MonthlyPolicyProposal:
        command = MonthlyProposalRequest.model_validate(command.model_dump(mode="json"))
        policy, definition = self._resolved_configuration(
            tenant_id=tenant_id,
            composite_id=composite_id,
            definition_version=definition_version,
            command=MonthlyPolicyValidationRequest(month=month, layers=command.layers),
        )
        retained = self.repository.get_monthly_policy_proposal(
            tenant_id=tenant_id,
            composite_id=composite_id,
            definition_version=definition_version,
            month=month,
            proposal_revision=proposal_revision,
        )
        if retained is not None:
            if (
                retained.policy,
                retained.attachments,
                retained.proposed_by,
                retained.eligibility_policy_version,
            ) != (
                policy,
                command.attachments,
                actor_id,
                definition.eligibility_policy_version,
            ):
                raise ValueError("COMPOSITE_ELIGIBILITY_PROPOSAL_IMMUTABLE_CONFLICT")
            return retained
        proposal = MonthlyPolicyProposal(
            proposal_revision=proposal_revision,
            eligibility_policy_version=definition.eligibility_policy_version,
            policy=policy,
            attachments=command.attachments,
            proposed_by=actor_id,
            proposed_at=self.clock(),
        )
        try:
            self.repository.save_monthly_policy_proposal(proposal=proposal)
        except DpmCompositeConflictError:
            winner = self.repository.get_monthly_policy_proposal(
                tenant_id=tenant_id,
                composite_id=composite_id,
                definition_version=definition_version,
                month=month,
                proposal_revision=proposal_revision,
            )
            if winner is None or (
                winner.policy,
                winner.attachments,
                winner.proposed_by,
                winner.eligibility_policy_version,
            ) != (
                policy,
                command.attachments,
                actor_id,
                definition.eligibility_policy_version,
            ):
                raise
            return winner
        return proposal

    def approve_policy(
        self,
        *,
        tenant_id: str,
        composite_id: str,
        definition_version: str,
        month: str,
        proposal_revision: str,
        actor_id: str,
        command: MonthlyApprovalRequest,
    ) -> MonthlyPolicyApproval:
        command = MonthlyApprovalRequest.model_validate(command.model_dump(mode="json"))
        proposal = self.repository.get_monthly_policy_proposal(
            tenant_id=tenant_id,
            composite_id=composite_id,
            definition_version=definition_version,
            month=month,
            proposal_revision=proposal_revision,
        )
        if proposal is None:
            raise ValueError("COMPOSITE_ELIGIBILITY_PROPOSAL_NOT_FOUND")
        if proposal.content_hash != command.expected_proposal_content_hash:
            raise ValueError("COMPOSITE_ELIGIBILITY_STALE_PROPOSAL")
        if actor_id == proposal.proposed_by:
            raise ValueError("COMPOSITE_ELIGIBILITY_SELF_APPROVAL_FORBIDDEN")
        retained = self.repository.get_monthly_policy_approval(
            tenant_id=tenant_id,
            composite_id=composite_id,
            definition_version=definition_version,
            month=month,
        )
        if retained is not None:
            if (
                retained.proposal.content_hash != proposal.content_hash
                or retained.approved_by != actor_id
            ):
                raise ValueError("COMPOSITE_ELIGIBILITY_ACTIVE_POLICY_CONFLICT")
            return retained
        approval = MonthlyPolicyApproval(
            proposal=proposal, approved_by=actor_id, approved_at=self.clock()
        )
        try:
            self.repository.save_monthly_policy_approval(approval=approval)
        except DpmCompositeConflictError:
            winner = self.repository.get_monthly_policy_approval(
                tenant_id=tenant_id,
                composite_id=composite_id,
                definition_version=definition_version,
                month=month,
            )
            if winner is None or (winner.proposal.content_hash, winner.approved_by) != (
                proposal.content_hash,
                actor_id,
            ):
                raise
            return winner
        return approval

    def validate_policy(
        self,
        *,
        tenant_id: str,
        composite_id: str,
        definition_version: str,
        command: MonthlyPolicyValidationRequest,
    ) -> ResolvedMonthlyPolicy:
        policy, _ = self._resolved_configuration(
            tenant_id=tenant_id,
            composite_id=composite_id,
            definition_version=definition_version,
            command=command,
        )
        return policy

    def _resolved_configuration(
        self,
        *,
        tenant_id: str,
        composite_id: str,
        definition_version: str,
        command: MonthlyPolicyValidationRequest,
    ) -> tuple[ResolvedMonthlyPolicy, CompositeDefinition]:
        command = MonthlyPolicyValidationRequest.model_validate(command.model_dump(mode="json"))
        definition = self.repository.get_definition(
            tenant_id=tenant_id, composite_id=composite_id, definition_version=definition_version
        )
        if definition is None:
            raise ValueError("COMPOSITE_DEFINITION_NOT_FOUND")
        scope = MonthlyPolicyScope(
            tenant_id=tenant_id,
            composite_id=composite_id,
            definition_version=definition_version,
            strategy_code=definition.strategy_code,
        )
        return resolve_monthly_policy(command.layers, month=command.month, scope=scope), definition

    def simulate(
        self,
        *,
        tenant_id: str,
        composite_id: str,
        definition_version: str,
        command: MonthlySimulationRequest,
    ) -> MonthlyEligibilityEvaluation:
        return self._evaluate(
            tenant_id=tenant_id,
            composite_id=composite_id,
            definition_version=definition_version,
            command=command,
            evaluated_at=self.clock(),
        )

    def diff(
        self,
        *,
        tenant_id: str,
        composite_id: str,
        definition_version: str,
        command: MonthlyDiffRequest,
    ) -> MonthlyEligibilityDiff:
        command = MonthlyDiffRequest.model_validate(command.model_dump(mode="json"))
        raw = command.model_dump(mode="json", exclude={"baseline_layers"})
        baseline_command = MonthlySimulationRequest.model_validate(
            raw | {"layers": [layer.model_dump(mode="json") for layer in command.baseline_layers]}
        )
        candidate_command = MonthlySimulationRequest.model_validate(raw)
        evaluated_at = self.clock()
        baseline = self._evaluate(
            tenant_id=tenant_id,
            composite_id=composite_id,
            definition_version=definition_version,
            command=baseline_command,
            evaluated_at=evaluated_at,
        )
        candidate = self._evaluate(
            tenant_id=tenant_id,
            composite_id=composite_id,
            definition_version=definition_version,
            command=candidate_command,
            evaluated_at=evaluated_at,
        )
        return compare_monthly_evaluations(baseline, candidate)

    def _evaluate(
        self,
        *,
        tenant_id: str,
        composite_id: str,
        definition_version: str,
        command: MonthlySimulationRequest,
        evaluated_at: str,
    ) -> MonthlyEligibilityEvaluation:
        command = MonthlySimulationRequest.model_validate(command.model_dump(mode="json"))
        policy, definition = self._resolved_configuration(
            tenant_id=tenant_id,
            composite_id=composite_id,
            definition_version=definition_version,
            command=MonthlyPolicyValidationRequest(month=command.month, layers=command.layers),
        )
        snapshot, attestation = self.resolve_source_inputs(
            policy,
            command,
            reporting_currency=definition.reporting_currency,
        )
        return evaluate_monthly_eligibility(
            policy,
            snapshot,
            evaluated_at=evaluated_at,
            universe_content_hash=attestation.content_hash,
        )

    def resolve_source_inputs(
        self,
        policy: ResolvedMonthlyPolicy,
        command: MonthlySimulationRequest,
        *,
        reporting_currency: str,
    ) -> tuple[MonthlyEligibilityObservations, DpmCompositeUniverseAttestation]:
        snapshot, attestation, _ = self.resolve_source_inputs_with_evidence(
            policy, command, reporting_currency=reporting_currency
        )
        return snapshot, attestation

    def resolve_source_inputs_with_evidence(
        self,
        policy: ResolvedMonthlyPolicy,
        command: MonthlySimulationRequest,
        *,
        reporting_currency: str,
    ) -> tuple[
        MonthlyEligibilityObservations,
        DpmCompositeUniverseAttestation,
        VerifiedMonthlySourceAssembly | None,
    ]:
        """One canonical source admission path for simulation and approved-policy evaluation."""
        attestation = self._retained_universe(policy, command)
        products = [
            product
            for product in attestation.source_products
            if product.product_name == "CompositeMonthlyEligibilityObservations"
            and product.contract_version == "v1"
            and product.authority_scope == "POLICY_INPUT"
        ]
        if len(products) != 1:
            raise ValueError("COMPOSITE_ELIGIBILITY_SOURCE_REFERENCE_UNAVAILABLE")
        product = products[0]
        request = MonthlyEligibilitySourceRequest(
            scope=policy.scope,
            month=command.month,
            source_cut_id=product.source_cut_id,
            owner_service=product.owner_service,
            expected_source_revision=product.source_watermark,
            expected_content_hash=product.content_hash,
            expected_portfolio_ids=tuple(attestation.expected_portfolio_ids),
            reporting_currency=reporting_currency,
        )
        resolution = self.source.resolve(request)
        snapshot = admitted_source_snapshot(request, resolution)
        return snapshot, attestation, resolution.source_assembly_evidence

    def _retained_universe(
        self,
        policy: ResolvedMonthlyPolicy,
        command: MonthlySimulationRequest,
    ) -> DpmCompositeUniverseAttestation:
        scope = policy.scope
        attestation = self.repository.get_universe_attestation(
            tenant_id=scope.tenant_id,
            composite_id=scope.composite_id,
            definition_version=scope.definition_version,
            membership_revision=command.membership_revision,
            attestation_version=command.attestation_version,
        )
        if attestation is None:
            raise ValueError("COMPOSITE_UNIVERSE_ATTESTATION_NOT_FOUND")
        attestation = DpmCompositeUniverseAttestation.model_validate(
            attestation.model_dump(mode="json")
        )
        if attestation.content_hash != command.universe_content_hash:
            raise ValueError("COMPOSITE_ELIGIBILITY_UNIVERSE_CONTENT_MISMATCH")
        first, last = month_window(command.month)
        if attestation.coverage_from > first or attestation.coverage_to < last:
            raise ValueError("COMPOSITE_ELIGIBILITY_UNIVERSE_WINDOW_INCOMPLETE")
        revision = self.repository.get_membership_revision(
            tenant_id=scope.tenant_id,
            composite_id=scope.composite_id,
            definition_version=scope.definition_version,
            membership_revision=command.membership_revision,
        )
        if revision is None or revision.content_hash != attestation.membership_content_hash:
            raise ValueError("COMPOSITE_ELIGIBILITY_UNIVERSE_MEMBERSHIP_MISMATCH")
        return attestation
