from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Protocol, TypeVar

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
    DpmPmQualitySummaryInvocationRepository,
)
from src.core.pm_quality.book_scope_refs import pm_book_member_source_refs


RepositoryT = TypeVar("RepositoryT")


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
class DpmPmOperatingQualityApplicationService:
    """PM operating-quality use cases over repository ports."""

    outcome_review_repository: DpmOutcomeReviewRepository | None = None
    policy_repository: DpmPmQualityPolicyRepository | None = None
    score_run_repository: DpmPmQualityScoreRunRepository | None = None
    fairness_repository: DpmPmQualityFairnessAnalysisRepository | None = None
    review_action_repository: DpmPmQualityReviewActionRepository | None = None
    summary_invocation_repository: DpmPmQualitySummaryInvocationRepository | None = None
    core_resolver_factory: Callable[[], CoreResolverProtocol] = build_core_resolver_client
    review_action_builder: Callable[..., DpmPmQualityReviewAction] = build_pm_quality_review_action

    def save_policy(
        self,
        *,
        policy_id: str,
        policy_version: str,
        policy: DpmPmOperatingQualityPolicy,
    ) -> DpmPmOperatingQualityPolicy:
        if policy.policy_id != policy_id or policy.policy_version != policy_version:
            raise DpmPmOperatingQualityServiceError("PM_QUALITY_POLICY_PATH_BODY_MISMATCH")
        _required_repository(
            self.policy_repository,
            "PM_QUALITY_POLICY_REPOSITORY_NOT_CONFIGURED",
        ).save_policy(policy=policy)
        return policy

    def list_policies(
        self,
        *,
        policy_id: str | None = None,
        enabled: bool | None = None,
        as_of_date: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[DpmPmOperatingQualityPolicy]:
        return _required_repository(
            self.policy_repository,
            "PM_QUALITY_POLICY_REPOSITORY_NOT_CONFIGURED",
        ).list_policies(
            policy_id=policy_id,
            enabled=enabled,
            as_of_date=as_of_date,
            limit=limit,
            offset=offset,
        )

    def get_policy(
        self,
        *,
        policy_id: str,
        policy_version: str,
    ) -> DpmPmOperatingQualityPolicy:
        policy = _required_repository(
            self.policy_repository,
            "PM_QUALITY_POLICY_REPOSITORY_NOT_CONFIGURED",
        ).get_policy(policy_id=policy_id, policy_version=policy_version)
        if policy is None:
            raise DpmPmOperatingQualityServiceError(
                f"PM_QUALITY_POLICY_NOT_FOUND:{policy_id}:{policy_version}"
            )
        return policy

    def preview_score_run(
        self,
        command: DpmPmQualityScoreRunCommand,
    ) -> DpmPmOperatingQualityScoreRun:
        return build_pm_quality_score_run_from_command(
            command=command,
            outcome_review_repository=_required_repository(
                self.outcome_review_repository,
                "PM_QUALITY_OUTCOME_REPOSITORY_NOT_CONFIGURED",
            ),
            policy_repository=_required_repository(
                self.policy_repository,
                "PM_QUALITY_POLICY_REPOSITORY_NOT_CONFIGURED",
            ),
            core_resolver_factory=self.core_resolver_factory,
        )

    def create_score_run(
        self,
        command: DpmPmQualityScoreRunCommand,
    ) -> DpmPmOperatingQualityScoreRun:
        score_run = self.preview_score_run(command)
        _required_repository(
            self.score_run_repository,
            "PM_QUALITY_SCORE_RUN_REPOSITORY_NOT_CONFIGURED",
        ).save_score_run(score_run=score_run)
        return score_run

    def list_score_runs(
        self,
        *,
        pm_id: str | None = None,
        book_id: str | None = None,
        policy_id: str | None = None,
        as_of_date: str | None = None,
        state: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[DpmPmOperatingQualityScoreRun]:
        return _required_repository(
            self.score_run_repository,
            "PM_QUALITY_SCORE_RUN_REPOSITORY_NOT_CONFIGURED",
        ).list_score_runs(
            pm_id=pm_id,
            book_id=book_id,
            policy_id=policy_id,
            as_of_date=as_of_date,
            state=state,
            limit=limit,
            offset=offset,
        )

    def get_score_run(self, *, score_run_id: str) -> DpmPmOperatingQualityScoreRun:
        score_run = _required_repository(
            self.score_run_repository,
            "PM_QUALITY_SCORE_RUN_REPOSITORY_NOT_CONFIGURED",
        ).get_score_run(score_run_id=score_run_id)
        if score_run is None:
            raise DpmPmOperatingQualityServiceError(
                f"PM_QUALITY_SCORE_RUN_NOT_FOUND:{score_run_id}"
            )
        return score_run

    def preview_fairness_analysis(
        self,
        command: DpmPmQualityFairnessAnalysisCommand,
    ) -> DpmPmQualityFairnessAnalysis:
        return build_pm_quality_fairness_analysis_from_command(
            command=command,
            score_run_repository=_required_repository(
                self.score_run_repository,
                "PM_QUALITY_SCORE_RUN_REPOSITORY_NOT_CONFIGURED",
            ),
        )

    def create_fairness_analysis(
        self,
        command: DpmPmQualityFairnessAnalysisCommand,
    ) -> DpmPmQualityFairnessAnalysis:
        fairness_analysis = self.preview_fairness_analysis(command)
        _required_repository(
            self.fairness_repository,
            "PM_QUALITY_FAIRNESS_REPOSITORY_NOT_CONFIGURED",
        ).save_fairness_analysis(analysis=fairness_analysis)
        return fairness_analysis

    def list_fairness_analyses(
        self,
        *,
        policy_id: str | None = None,
        policy_version: str | None = None,
        as_of_date: str | None = None,
        state: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[DpmPmQualityFairnessAnalysis]:
        return _required_repository(
            self.fairness_repository,
            "PM_QUALITY_FAIRNESS_REPOSITORY_NOT_CONFIGURED",
        ).list_fairness_analyses(
            policy_id=policy_id,
            policy_version=policy_version,
            as_of_date=as_of_date,
            state=state,
            limit=limit,
            offset=offset,
        )

    def get_fairness_analysis(
        self,
        *,
        fairness_analysis_id: str,
    ) -> DpmPmQualityFairnessAnalysis:
        fairness_analysis = _required_repository(
            self.fairness_repository,
            "PM_QUALITY_FAIRNESS_REPOSITORY_NOT_CONFIGURED",
        ).get_fairness_analysis(fairness_analysis_id=fairness_analysis_id)
        if fairness_analysis is None:
            raise DpmPmOperatingQualityServiceError(
                f"PM_QUALITY_FAIRNESS_ANALYSIS_NOT_FOUND:{fairness_analysis_id}"
            )
        return fairness_analysis

    def preview_review_action(
        self,
        command: DpmPmQualityReviewActionCommand,
    ) -> DpmPmQualityReviewAction:
        return build_pm_quality_review_action_from_command(
            command=command,
            score_run_repository=_required_repository(
                self.score_run_repository,
                "PM_QUALITY_SCORE_RUN_REPOSITORY_NOT_CONFIGURED",
            ),
            fairness_repository=_required_repository(
                self.fairness_repository,
                "PM_QUALITY_FAIRNESS_REPOSITORY_NOT_CONFIGURED",
            ),
            review_action_builder=self.review_action_builder,
        )

    def create_review_action(
        self,
        command: DpmPmQualityReviewActionCommand,
    ) -> DpmPmQualityReviewAction:
        review_action = self.preview_review_action(command)
        _required_repository(
            self.review_action_repository,
            "PM_QUALITY_REVIEW_ACTION_REPOSITORY_NOT_CONFIGURED",
        ).save_review_action(action=review_action)
        return review_action

    def list_review_actions(
        self,
        *,
        target_type: str | None = None,
        target_id: str | None = None,
        policy_id: str | None = None,
        as_of_date: str | None = None,
        action_state: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[DpmPmQualityReviewAction]:
        return _required_repository(
            self.review_action_repository,
            "PM_QUALITY_REVIEW_ACTION_REPOSITORY_NOT_CONFIGURED",
        ).list_review_actions(
            target_type=target_type,
            target_id=target_id,
            policy_id=policy_id,
            as_of_date=as_of_date,
            action_state=action_state,
            limit=limit,
            offset=offset,
        )

    def get_review_action(self, *, review_action_id: str) -> DpmPmQualityReviewAction:
        review_action = _required_repository(
            self.review_action_repository,
            "PM_QUALITY_REVIEW_ACTION_REPOSITORY_NOT_CONFIGURED",
        ).get_review_action(review_action_id=review_action_id)
        if review_action is None:
            raise DpmPmOperatingQualityServiceError(
                f"PM_QUALITY_REVIEW_ACTION_NOT_FOUND:{review_action_id}"
            )
        return review_action

    def preview_summary_invocation(
        self,
        command: DpmPmQualitySummaryInvocationCommand,
    ) -> DpmPmQualitySummaryInvocation:
        return build_pm_quality_summary_invocation_from_command(
            command=command,
            score_run_repository=_required_repository(
                self.score_run_repository,
                "PM_QUALITY_SCORE_RUN_REPOSITORY_NOT_CONFIGURED",
            ),
            review_action_repository=_required_repository(
                self.review_action_repository,
                "PM_QUALITY_REVIEW_ACTION_REPOSITORY_NOT_CONFIGURED",
            ),
        )

    def create_summary_invocation(
        self,
        command: DpmPmQualitySummaryInvocationCommand,
    ) -> DpmPmQualitySummaryInvocation:
        summary_invocation = self.preview_summary_invocation(command)
        _required_repository(
            self.summary_invocation_repository,
            "PM_QUALITY_SUMMARY_REPOSITORY_NOT_CONFIGURED",
        ).save_summary_invocation(invocation=summary_invocation)
        return summary_invocation

    def list_summary_invocations(
        self,
        *,
        score_run_id: str | None = None,
        review_action_id: str | None = None,
        policy_id: str | None = None,
        as_of_date: str | None = None,
        invocation_state: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[DpmPmQualitySummaryInvocation]:
        return _required_repository(
            self.summary_invocation_repository,
            "PM_QUALITY_SUMMARY_REPOSITORY_NOT_CONFIGURED",
        ).list_summary_invocations(
            score_run_id=score_run_id,
            review_action_id=review_action_id,
            policy_id=policy_id,
            as_of_date=as_of_date,
            invocation_state=invocation_state,
            limit=limit,
            offset=offset,
        )

    def get_summary_invocation(
        self,
        *,
        summary_invocation_id: str,
    ) -> DpmPmQualitySummaryInvocation:
        summary_invocation = _required_repository(
            self.summary_invocation_repository,
            "PM_QUALITY_SUMMARY_REPOSITORY_NOT_CONFIGURED",
        ).get_summary_invocation(summary_invocation_id=summary_invocation_id)
        if summary_invocation is None:
            raise DpmPmOperatingQualityServiceError(
                f"PM_QUALITY_SUMMARY_INVOCATION_NOT_FOUND:{summary_invocation_id}"
            )
        return summary_invocation


def _required_repository(repository: RepositoryT | None, code: str) -> RepositoryT:
    if repository is None:
        raise DpmPmOperatingQualityServiceError(code)
    return repository


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
    return pm_book_member_source_refs(membership)


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
