from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Protocol

from src.api.services.core_resolver_service import CoreResolverError, CoreResolverUnavailableError
from src.api.services.core_resolver_service import build_core_resolver_client
from src.core.dpm_source_context import DpmCorePortfolioManagerBookMembershipResponse
from src.core.outcomes import DpmOutcomeSourceRef
from src.core.outcomes.repository import DpmOutcomeReviewRepository
from src.core.pm_quality import (
    DpmPmOperatingQualityPolicy,
    DpmPmOperatingQualityScoreRun,
    DpmPmQualityBookScopeEvidence,
    DpmPmQualityFairnessAnalysis,
    DpmPmQualityEvidenceItem,
    DpmPmQualityFairnessSegmentInput,
    DpmPmQualityPolicyRepository,
    DpmPmQualityReviewAction,
    DpmPmQualityScoreRunRepository,
    DpmPmQualitySummaryInvocation,
    DpmPmQualityValidationError,
    PmQualityReviewActionTargetType,
    PmQualityReviewActionType,
    PmQualitySummaryInvocationState,
    build_pm_operating_quality_score_run,
    build_pm_quality_review_action,
    build_pm_quality_summary_invocation,
    PmQualityFairnessSegmentType,
    build_pm_operating_quality_fairness_analysis,
    DpmPmQualityFairnessAnalysisRepository,
    DpmPmQualityReviewActionRepository,
)


class CoreResolverProtocol(Protocol):
    def resolve_portfolio_manager_book_membership(
        self,
        *,
        portfolio_manager_id: str,
        as_of_date: date,
        tenant_id: str | None,
        booking_center_code: str | None,
        portfolio_types: list[str],
        include_inactive: bool,
        correlation_id: str,
    ) -> DpmCorePortfolioManagerBookMembershipResponse: ...


class DpmPmOperatingQualityServiceError(ValueError):
    """API-service error with a stable PM operating-quality code."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class DpmPmQualityBookScopeCommand:
    tenant_id: str | None
    booking_center_code: str | None
    portfolio_types: list[str]
    include_inactive: bool


@dataclass(frozen=True)
class DpmPmQualityScoreRunCommand:
    pm_id: str
    book_id: str | None
    as_of_date: str
    policy: DpmPmOperatingQualityPolicy | None
    policy_id: str | None
    policy_version: str | None
    evidence_items: list[DpmPmQualityEvidenceItem]
    outcome_review_ids: list[str]
    actor_id: str
    correlation_id: str
    book_scope: DpmPmQualityBookScopeCommand | None = None


@dataclass(frozen=True)
class DpmPmQualityFairnessSegmentCommand:
    segment_id: str
    segment_type: PmQualityFairnessSegmentType
    display_name: str
    score_run_ids: list[str]
    source_refs: list[DpmOutcomeSourceRef] = field(default_factory=list)


@dataclass(frozen=True)
class DpmPmQualityFairnessAnalysisCommand:
    policy_id: str
    policy_version: str
    as_of_date: str
    segments: list[DpmPmQualityFairnessSegmentCommand]
    minimum_segment_score_run_count: int
    maximum_average_score_spread: Decimal
    actor_id: str
    correlation_id: str


@dataclass(frozen=True)
class DpmPmQualityReviewActionCommand:
    target_type: PmQualityReviewActionTargetType
    target_id: str
    action_type: PmQualityReviewActionType
    review_action_ref: str
    review_reason: str
    actor_id: str
    remediation_due_date: str | None
    source_refs: list[DpmOutcomeSourceRef]
    correlation_id: str


@dataclass(frozen=True)
class DpmPmQualitySummaryInvocationCommand:
    score_run_id: str
    review_action_id: str
    invocation_state: PmQualitySummaryInvocationState
    summary_ref: str
    workflow_pack_name: str
    workflow_pack_version: str
    requested_by: str
    workflow_run_id: str | None
    summary_artifact_ref: str | None
    summary_content_hash: str | None
    source_refs: list[DpmOutcomeSourceRef]
    correlation_id: str


def resolve_pm_quality_policy_from_command(
    *,
    policy: DpmPmOperatingQualityPolicy | None,
    policy_id: str | None,
    policy_version: str | None,
    repository: DpmPmQualityPolicyRepository,
) -> DpmPmOperatingQualityPolicy:
    if policy is not None:
        return policy
    if policy_id is None or policy_version is None:
        raise DpmPmOperatingQualityServiceError("PM_QUALITY_POLICY_REFERENCE_REQUIRED")
    stored_policy = repository.get_policy(policy_id=policy_id, policy_version=policy_version)
    if stored_policy is None:
        raise DpmPmOperatingQualityServiceError(
            f"PM_QUALITY_POLICY_NOT_FOUND:{policy_id}:{policy_version}"
        )
    return stored_policy


def resolve_pm_quality_book_scope_evidence(
    *,
    pm_id: str,
    as_of_date: str,
    command: DpmPmQualityBookScopeCommand,
    correlation_id: str,
    core_resolver_factory: Callable[[], CoreResolverProtocol],
) -> DpmPmQualityBookScopeEvidence:
    as_of_date_obj = _parse_pm_book_scope_as_of_date(as_of_date)
    membership = _resolve_pm_book_membership(
        pm_id=pm_id,
        as_of_date=as_of_date_obj,
        command=command,
        correlation_id=correlation_id,
        core_resolver_factory=core_resolver_factory,
    )
    _validate_pm_book_membership(membership)
    return _pm_book_scope_evidence_from_membership(membership)


def _parse_pm_book_scope_as_of_date(as_of_date: str) -> date:
    try:
        return date.fromisoformat(as_of_date)
    except ValueError as exc:
        raise DpmPmOperatingQualityServiceError("INVALID_AS_OF_DATE") from exc


def _resolve_pm_book_membership(
    *,
    pm_id: str,
    as_of_date: date,
    command: DpmPmQualityBookScopeCommand,
    correlation_id: str,
    core_resolver_factory: Callable[[], CoreResolverProtocol],
) -> DpmCorePortfolioManagerBookMembershipResponse:
    try:
        resolver = core_resolver_factory()
        return resolver.resolve_portfolio_manager_book_membership(
            portfolio_manager_id=pm_id,
            as_of_date=as_of_date,
            tenant_id=command.tenant_id,
            booking_center_code=command.booking_center_code,
            portfolio_types=command.portfolio_types,
            include_inactive=command.include_inactive,
            correlation_id=correlation_id,
        )
    except CoreResolverUnavailableError as exc:
        raise DpmPmOperatingQualityServiceError("DPM_CORE_PM_BOOK_MEMBERSHIP_UNAVAILABLE") from exc
    except CoreResolverError as exc:
        raise DpmPmOperatingQualityServiceError(str(exc)) from exc


def _validate_pm_book_membership(
    membership: DpmCorePortfolioManagerBookMembershipResponse,
) -> None:
    if membership.supportability.state != "READY":
        raise DpmPmOperatingQualityServiceError(membership.supportability.reason)
    if not membership.members:
        raise DpmPmOperatingQualityServiceError("DPM_CORE_PM_BOOK_MEMBERSHIP_EMPTY")


def _pm_book_scope_source_id(
    membership: DpmCorePortfolioManagerBookMembershipResponse,
) -> str:
    return (
        membership.snapshot_id
        or membership.source_batch_fingerprint
        or f"pm-book:{membership.portfolio_manager_id}:{membership.as_of_date.isoformat()}"
    )


def _pm_book_member_source_refs(
    membership: DpmCorePortfolioManagerBookMembershipResponse,
) -> list[DpmOutcomeSourceRef]:
    return [
        DpmOutcomeSourceRef(
            source_system="lotus-core",
            source_type="PORTFOLIO_MANAGER_BOOK_MEMBER",
            source_id=member.source_record_id or member.portfolio_id,
            source_version=membership.as_of_date.isoformat(),
        )
        for member in membership.members[:100]
    ]


def _pm_book_scope_evidence_from_membership(
    membership: DpmCorePortfolioManagerBookMembershipResponse,
) -> DpmPmQualityBookScopeEvidence:
    source_id = _pm_book_scope_source_id(membership)
    return DpmPmQualityBookScopeEvidence(
        source_id=source_id,
        product_version=membership.product_version,
        supportability_state=membership.supportability.state,
        returned_portfolio_count=len(membership.members),
        member_portfolio_ids=[member.portfolio_id for member in membership.members[:100]],
        filters_applied=membership.supportability.filters_applied,
        reason_codes=[
            "PM_BOOK_SCOPE_MATERIALIZED",
            membership.supportability.reason,
        ],
        source_refs=[
            DpmOutcomeSourceRef(
                source_system="lotus-core",
                source_type="PortfolioManagerBookMembership",
                source_id=source_id,
                source_version=membership.product_version,
                content_hash=membership.source_batch_fingerprint,
            ),
            *_pm_book_member_source_refs(membership),
        ],
    )


def build_pm_quality_book_scope_signal(
    *,
    book_scope_evidence: DpmPmQualityBookScopeEvidence,
) -> DpmPmQualityEvidenceItem:
    return DpmPmQualityEvidenceItem(
        indicator="SOURCE_QUALITY",
        evidence_state="READY",
        score=None,
        source_system=book_scope_evidence.source_system,
        source_type=book_scope_evidence.source_type,
        source_id=book_scope_evidence.source_id,
        reason_codes=book_scope_evidence.reason_codes,
        source_refs=book_scope_evidence.source_refs,
    )


def build_pm_quality_score_run_from_command(
    *,
    command: DpmPmQualityScoreRunCommand,
    outcome_review_repository: DpmOutcomeReviewRepository,
    policy_repository: DpmPmQualityPolicyRepository,
    core_resolver_factory: Callable[[], CoreResolverProtocol] = build_core_resolver_client,
) -> DpmPmOperatingQualityScoreRun:
    policy = resolve_pm_quality_policy_from_command(
        policy=command.policy,
        policy_id=command.policy_id,
        policy_version=command.policy_version,
        repository=policy_repository,
    )

    evidence_items = list(command.evidence_items)
    book_scope_evidence = None
    if command.book_scope is not None:
        book_scope_evidence = resolve_pm_quality_book_scope_evidence(
            pm_id=command.pm_id,
            as_of_date=command.as_of_date,
            command=command.book_scope,
            correlation_id=command.correlation_id,
            core_resolver_factory=core_resolver_factory,
        )
        evidence_items.append(
            build_pm_quality_book_scope_signal(book_scope_evidence=book_scope_evidence)
        )

    outcome_reviews = []
    for outcome_review_id in command.outcome_review_ids:
        outcome_review = outcome_review_repository.get_outcome_review(
            outcome_review_id=outcome_review_id
        )
        if outcome_review is None:
            raise DpmPmOperatingQualityServiceError(f"OUTCOME_REVIEW_NOT_FOUND:{outcome_review_id}")
        outcome_reviews.append(outcome_review)

    try:
        return build_pm_operating_quality_score_run(
            pm_id=command.pm_id,
            book_id=command.book_id,
            as_of_date=command.as_of_date,
            policy=policy,
            evidence_items=evidence_items,
            outcome_reviews=outcome_reviews,
            book_scope_evidence=book_scope_evidence,
            generated_by=command.actor_id,
            correlation_id=command.correlation_id,
        )
    except DpmPmQualityValidationError as exc:
        raise DpmPmOperatingQualityServiceError(str(exc)) from exc


def build_pm_quality_fairness_analysis_from_command(
    *,
    command: DpmPmQualityFairnessAnalysisCommand,
    score_run_repository: DpmPmQualityScoreRunRepository,
) -> DpmPmQualityFairnessAnalysis:
    segment_inputs = []
    for segment in command.segments:
        score_runs = []
        for score_run_id in segment.score_run_ids:
            score_run = score_run_repository.get_score_run(score_run_id=score_run_id)
            if score_run is None:
                raise DpmPmOperatingQualityServiceError(
                    f"PM_QUALITY_SCORE_RUN_NOT_FOUND:{score_run_id}"
                )
            score_runs.append(score_run)
        segment_inputs.append(
            DpmPmQualityFairnessSegmentInput(
                segment_id=segment.segment_id,
                segment_type=segment.segment_type,
                display_name=segment.display_name,
                score_runs=score_runs,
                source_refs=segment.source_refs,
            )
        )
    try:
        return build_pm_operating_quality_fairness_analysis(
            policy_id=command.policy_id,
            policy_version=command.policy_version,
            as_of_date=command.as_of_date,
            segments=segment_inputs,
            minimum_segment_score_run_count=command.minimum_segment_score_run_count,
            maximum_average_score_spread=command.maximum_average_score_spread,
            generated_by=command.actor_id,
            correlation_id=command.correlation_id,
        )
    except DpmPmQualityValidationError as exc:
        raise DpmPmOperatingQualityServiceError(str(exc)) from exc


def build_pm_quality_review_action_from_command(
    *,
    command: DpmPmQualityReviewActionCommand,
    score_run_repository: DpmPmQualityScoreRunRepository,
    fairness_repository: DpmPmQualityFairnessAnalysisRepository,
    review_action_builder: Callable[..., DpmPmQualityReviewAction] = build_pm_quality_review_action,
) -> DpmPmQualityReviewAction:
    target: DpmPmOperatingQualityScoreRun | DpmPmQualityFairnessAnalysis | None = None
    if command.target_type == "SCORE_RUN":
        target = score_run_repository.get_score_run(score_run_id=command.target_id)
        if target is None:
            raise DpmPmOperatingQualityServiceError(
                f"PM_QUALITY_SCORE_RUN_NOT_FOUND:{command.target_id}"
            )
    else:
        target = fairness_repository.get_fairness_analysis(fairness_analysis_id=command.target_id)
        if target is None:
            raise DpmPmOperatingQualityServiceError(
                f"PM_QUALITY_FAIRNESS_ANALYSIS_NOT_FOUND:{command.target_id}"
            )
    try:
        return review_action_builder(
            target=target,
            target_type=command.target_type,
            action_type=command.action_type,
            review_action_ref=command.review_action_ref,
            review_reason=command.review_reason,
            actor_id=command.actor_id,
            source_refs=command.source_refs,
            remediation_due_date=command.remediation_due_date,
            correlation_id=command.correlation_id,
        )
    except ValueError as exc:
        raise DpmPmOperatingQualityServiceError(str(exc)) from exc


def build_pm_quality_summary_invocation_from_command(
    *,
    command: DpmPmQualitySummaryInvocationCommand,
    score_run_repository: DpmPmQualityScoreRunRepository,
    review_action_repository: DpmPmQualityReviewActionRepository,
) -> DpmPmQualitySummaryInvocation:
    score_run = score_run_repository.get_score_run(score_run_id=command.score_run_id)
    if score_run is None:
        raise DpmPmOperatingQualityServiceError(
            f"PM_QUALITY_SCORE_RUN_NOT_FOUND:{command.score_run_id}"
        )
    review_action = review_action_repository.get_review_action(
        review_action_id=command.review_action_id
    )
    if review_action is None:
        raise DpmPmOperatingQualityServiceError(
            f"PM_QUALITY_REVIEW_ACTION_NOT_FOUND:{command.review_action_id}"
        )
    try:
        return build_pm_quality_summary_invocation(
            score_run=score_run,
            review_action=review_action,
            invocation_state=command.invocation_state,
            summary_ref=command.summary_ref,
            workflow_pack_name=command.workflow_pack_name,
            workflow_pack_version=command.workflow_pack_version,
            workflow_run_id=command.workflow_run_id,
            summary_artifact_ref=command.summary_artifact_ref,
            summary_content_hash=command.summary_content_hash,
            requested_by=command.requested_by,
            source_refs=command.source_refs,
            correlation_id=command.correlation_id,
        )
    except ValueError as exc:
        raise DpmPmOperatingQualityServiceError(str(exc)) from exc
