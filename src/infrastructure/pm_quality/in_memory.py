from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import dataclass
from threading import Lock

from src.core.pm_quality.models import (
    DpmPmOperatingQualityPolicy,
    DpmPmOperatingQualityScoreRun,
    DpmPmQualityFairnessAnalysis,
    DpmPmQualityReviewAction,
    DpmPmQualitySummaryInvocation,
)
from src.core.pm_quality.repository import (
    DpmPmQualityFairnessAnalysisConflictError,
    DpmPmQualityFairnessAnalysisRepository,
    DpmPmQualityPolicyConflictError,
    DpmPmQualityPolicyRepository,
    DpmPmQualityReviewActionConflictError,
    DpmPmQualityReviewActionIntegrityError,
    DpmPmQualityReviewActionRepository,
    DpmPmQualityScoreRunConflictError,
    DpmPmQualityScoreRunRepository,
    DpmPmQualitySummaryInvocationConflictError,
    DpmPmQualitySummaryInvocationIntegrityError,
    DpmPmQualitySummaryInvocationRepository,
)


@dataclass(frozen=True)
class _PolicyFilters:
    policy_id: str | None
    enabled: bool | None
    as_of_date: str | None


@dataclass(frozen=True)
class _ScoreRunFilters:
    pm_id: str | None
    book_id: str | None
    policy_id: str | None
    as_of_date: str | None
    state: str | None


@dataclass(frozen=True)
class _FairnessAnalysisFilters:
    policy_id: str | None
    policy_version: str | None
    as_of_date: str | None
    state: str | None


@dataclass(frozen=True)
class _ReviewActionFilters:
    target_type: str | None
    target_id: str | None
    policy_id: str | None
    as_of_date: str | None
    action_state: str | None


@dataclass(frozen=True)
class _SummaryInvocationFilters:
    score_run_id: str | None
    review_action_id: str | None
    policy_id: str | None
    as_of_date: str | None
    invocation_state: str | None


class InMemoryDpmPmQualityPolicyRepository(DpmPmQualityPolicyRepository):
    def __init__(self) -> None:
        self._lock = Lock()
        self._policies: dict[tuple[str, str, str], DpmPmOperatingQualityPolicy] = {}

    def save_policy(self, *, tenant_id: str, policy: DpmPmOperatingQualityPolicy) -> None:
        _ensure_record_tenant(tenant_id=tenant_id, record_tenant_id=policy.tenant_id)
        key = (tenant_id, policy.policy_id, policy.policy_version)
        with self._lock:
            existing = self._policies.get(key)
            if existing is not None and _policy_hash(existing) != _policy_hash(policy):
                raise DpmPmQualityPolicyConflictError("PM_QUALITY_POLICY_IMMUTABLE_CONFLICT")
            self._policies[key] = deepcopy(policy)

    def get_policy(
        self,
        *,
        tenant_id: str,
        policy_id: str,
        policy_version: str,
    ) -> DpmPmOperatingQualityPolicy | None:
        with self._lock:
            policy = self._policies.get((tenant_id, policy_id, policy_version))
            return deepcopy(policy) if policy is not None else None

    def list_policies(
        self,
        *,
        tenant_id: str,
        policy_id: str | None = None,
        enabled: bool | None = None,
        as_of_date: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[DpmPmOperatingQualityPolicy]:
        with self._lock:
            page = _list_policies(
                policies=[
                    policy for policy in self._policies.values() if policy.tenant_id == tenant_id
                ],
                filters=_PolicyFilters(
                    policy_id=policy_id,
                    enabled=enabled,
                    as_of_date=as_of_date,
                ),
                limit=limit,
                offset=offset,
            )
            return deepcopy(page)


class InMemoryDpmPmQualityScoreRunRepository(DpmPmQualityScoreRunRepository):
    def __init__(self) -> None:
        self._lock = Lock()
        self._score_runs: dict[tuple[str, str], DpmPmOperatingQualityScoreRun] = {}

    def save_score_run(self, *, tenant_id: str, score_run: DpmPmOperatingQualityScoreRun) -> None:
        _ensure_record_tenant(tenant_id=tenant_id, record_tenant_id=score_run.tenant_id)
        with self._lock:
            existing = self._score_runs.get((tenant_id, score_run.score_run_id))
            if existing is not None and existing.content_hash != score_run.content_hash:
                raise DpmPmQualityScoreRunConflictError("PM_QUALITY_SCORE_RUN_IMMUTABLE_CONFLICT")
            self._score_runs[(tenant_id, score_run.score_run_id)] = deepcopy(score_run)

    def get_score_run(
        self,
        *,
        tenant_id: str,
        score_run_id: str,
    ) -> DpmPmOperatingQualityScoreRun | None:
        with self._lock:
            score_run = self._score_runs.get((tenant_id, score_run_id))
            return deepcopy(score_run) if score_run is not None else None

    def list_score_runs(
        self,
        *,
        tenant_id: str,
        pm_id: str | None = None,
        book_id: str | None = None,
        policy_id: str | None = None,
        as_of_date: str | None = None,
        state: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[DpmPmOperatingQualityScoreRun]:
        with self._lock:
            page = _list_score_runs(
                score_runs=[
                    score_run
                    for score_run in self._score_runs.values()
                    if score_run.tenant_id == tenant_id
                ],
                filters=_ScoreRunFilters(
                    pm_id=pm_id,
                    book_id=book_id,
                    policy_id=policy_id,
                    as_of_date=as_of_date,
                    state=state,
                ),
                limit=limit,
                offset=offset,
            )
            return deepcopy(page)


class InMemoryDpmPmQualityFairnessAnalysisRepository(DpmPmQualityFairnessAnalysisRepository):
    def __init__(self) -> None:
        self._lock = Lock()
        self._analyses: dict[tuple[str, str], DpmPmQualityFairnessAnalysis] = {}

    def save_fairness_analysis(
        self, *, tenant_id: str, analysis: DpmPmQualityFairnessAnalysis
    ) -> None:
        _ensure_record_tenant(tenant_id=tenant_id, record_tenant_id=analysis.tenant_id)
        with self._lock:
            existing = self._analyses.get((tenant_id, analysis.fairness_analysis_id))
            if existing is not None and existing.content_hash != analysis.content_hash:
                raise DpmPmQualityFairnessAnalysisConflictError(
                    "PM_QUALITY_FAIRNESS_ANALYSIS_IMMUTABLE_CONFLICT"
                )
            self._analyses[(tenant_id, analysis.fairness_analysis_id)] = deepcopy(analysis)

    def get_fairness_analysis(
        self,
        *,
        tenant_id: str,
        fairness_analysis_id: str,
    ) -> DpmPmQualityFairnessAnalysis | None:
        with self._lock:
            analysis = self._analyses.get((tenant_id, fairness_analysis_id))
            return deepcopy(analysis) if analysis is not None else None

    def list_fairness_analyses(
        self,
        *,
        tenant_id: str,
        policy_id: str | None = None,
        policy_version: str | None = None,
        as_of_date: str | None = None,
        state: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[DpmPmQualityFairnessAnalysis]:
        with self._lock:
            page = _list_fairness_analyses(
                analyses=[
                    analysis
                    for analysis in self._analyses.values()
                    if analysis.tenant_id == tenant_id
                ],
                filters=_FairnessAnalysisFilters(
                    policy_id=policy_id,
                    policy_version=policy_version,
                    as_of_date=as_of_date,
                    state=state,
                ),
                limit=limit,
                offset=offset,
            )
            return deepcopy(page)


class InMemoryDpmPmQualityReviewActionRepository(DpmPmQualityReviewActionRepository):
    def __init__(
        self,
        *,
        score_run_repository: DpmPmQualityScoreRunRepository | None = None,
        fairness_analysis_repository: DpmPmQualityFairnessAnalysisRepository | None = None,
    ) -> None:
        self._lock = Lock()
        self._actions: dict[tuple[str, str], DpmPmQualityReviewAction] = {}
        self._score_run_repository = score_run_repository
        self._fairness_analysis_repository = fairness_analysis_repository

    def save_review_action(self, *, tenant_id: str, action: DpmPmQualityReviewAction) -> None:
        _ensure_record_tenant(tenant_id=tenant_id, record_tenant_id=action.tenant_id)
        _validate_review_action_parent(
            tenant_id=tenant_id,
            action=action,
            score_run_repository=self._score_run_repository,
            fairness_analysis_repository=self._fairness_analysis_repository,
        )
        with self._lock:
            existing = self._actions.get((tenant_id, action.review_action_id))
            if existing is not None and existing.content_hash != action.content_hash:
                raise DpmPmQualityReviewActionConflictError(
                    "PM_QUALITY_REVIEW_ACTION_IMMUTABLE_CONFLICT"
                )
            self._actions[(tenant_id, action.review_action_id)] = deepcopy(action)

    def get_review_action(
        self,
        *,
        tenant_id: str,
        review_action_id: str,
    ) -> DpmPmQualityReviewAction | None:
        with self._lock:
            action = self._actions.get((tenant_id, review_action_id))
            return deepcopy(action) if action is not None else None

    def list_review_actions(
        self,
        *,
        tenant_id: str,
        target_type: str | None = None,
        target_id: str | None = None,
        policy_id: str | None = None,
        as_of_date: str | None = None,
        action_state: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[DpmPmQualityReviewAction]:
        with self._lock:
            page = _list_review_actions(
                actions=[
                    action for action in self._actions.values() if action.tenant_id == tenant_id
                ],
                filters=_ReviewActionFilters(
                    target_type=target_type,
                    target_id=target_id,
                    policy_id=policy_id,
                    as_of_date=as_of_date,
                    action_state=action_state,
                ),
                limit=limit,
                offset=offset,
            )
            return deepcopy(page)


class InMemoryDpmPmQualitySummaryInvocationRepository(DpmPmQualitySummaryInvocationRepository):
    def __init__(
        self,
        *,
        score_run_repository: DpmPmQualityScoreRunRepository | None = None,
        review_action_repository: DpmPmQualityReviewActionRepository | None = None,
    ) -> None:
        self._lock = Lock()
        self._invocations: dict[tuple[str, str], DpmPmQualitySummaryInvocation] = {}
        self._score_run_repository = score_run_repository
        self._review_action_repository = review_action_repository

    def save_summary_invocation(
        self, *, tenant_id: str, invocation: DpmPmQualitySummaryInvocation
    ) -> None:
        _ensure_record_tenant(tenant_id=tenant_id, record_tenant_id=invocation.tenant_id)
        _validate_summary_invocation_parents(
            tenant_id=tenant_id,
            invocation=invocation,
            score_run_repository=self._score_run_repository,
            review_action_repository=self._review_action_repository,
        )
        with self._lock:
            existing = self._invocations.get((tenant_id, invocation.summary_invocation_id))
            if existing is not None and existing.content_hash != invocation.content_hash:
                raise DpmPmQualitySummaryInvocationConflictError(
                    "PM_QUALITY_SUMMARY_INVOCATION_IMMUTABLE_CONFLICT"
                )
            self._invocations[(tenant_id, invocation.summary_invocation_id)] = deepcopy(invocation)

    def get_summary_invocation(
        self,
        *,
        tenant_id: str,
        summary_invocation_id: str,
    ) -> DpmPmQualitySummaryInvocation | None:
        with self._lock:
            invocation = self._invocations.get((tenant_id, summary_invocation_id))
            return deepcopy(invocation) if invocation is not None else None

    def list_summary_invocations(
        self,
        *,
        tenant_id: str,
        score_run_id: str | None = None,
        review_action_id: str | None = None,
        policy_id: str | None = None,
        as_of_date: str | None = None,
        invocation_state: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[DpmPmQualitySummaryInvocation]:
        with self._lock:
            page = _list_summary_invocations(
                invocations=[
                    invocation
                    for invocation in self._invocations.values()
                    if invocation.tenant_id == tenant_id
                ],
                filters=_SummaryInvocationFilters(
                    score_run_id=score_run_id,
                    review_action_id=review_action_id,
                    policy_id=policy_id,
                    as_of_date=as_of_date,
                    invocation_state=invocation_state,
                ),
                limit=limit,
                offset=offset,
            )
            return deepcopy(page)


def _policy_matches_filters(
    policy: DpmPmOperatingQualityPolicy,
    filters: _PolicyFilters,
) -> bool:
    return all(
        (
            _optional_value_matches(policy.policy_id, filters.policy_id),
            _optional_bool_matches(policy.enabled, filters.enabled),
            _optional_value_matches(policy.as_of_date, filters.as_of_date),
        )
    )


def _sort_policies(
    policies: list[DpmPmOperatingQualityPolicy],
) -> list[DpmPmOperatingQualityPolicy]:
    return sorted(
        policies,
        key=lambda policy: (policy.as_of_date, policy.policy_id, policy.policy_version),
        reverse=True,
    )


def _list_policies(
    *,
    policies: list[DpmPmOperatingQualityPolicy],
    filters: _PolicyFilters,
    limit: int,
    offset: int,
) -> list[DpmPmOperatingQualityPolicy]:
    filtered = [policy for policy in policies if _policy_matches_filters(policy, filters)]
    return _sort_policies(filtered)[offset : offset + limit]


def _score_run_matches_filters(
    score_run: DpmPmOperatingQualityScoreRun,
    filters: _ScoreRunFilters,
) -> bool:
    return all(
        (
            _optional_value_matches(score_run.pm_id, filters.pm_id),
            _optional_value_matches(score_run.book_id, filters.book_id),
            _optional_value_matches(score_run.policy_id, filters.policy_id),
            _optional_value_matches(score_run.as_of_date, filters.as_of_date),
            _optional_value_matches(score_run.state, filters.state),
        )
    )


def _sort_score_runs(
    score_runs: list[DpmPmOperatingQualityScoreRun],
) -> list[DpmPmOperatingQualityScoreRun]:
    return sorted(
        score_runs,
        key=lambda score_run: (score_run.generated_at, score_run.score_run_id),
        reverse=True,
    )


def _list_score_runs(
    *,
    score_runs: list[DpmPmOperatingQualityScoreRun],
    filters: _ScoreRunFilters,
    limit: int,
    offset: int,
) -> list[DpmPmOperatingQualityScoreRun]:
    filtered = [
        score_run for score_run in score_runs if _score_run_matches_filters(score_run, filters)
    ]
    return _sort_score_runs(filtered)[offset : offset + limit]


def _fairness_analysis_matches_filters(
    analysis: DpmPmQualityFairnessAnalysis,
    filters: _FairnessAnalysisFilters,
) -> bool:
    return all(
        (
            _optional_value_matches(analysis.policy_id, filters.policy_id),
            _optional_value_matches(analysis.policy_version, filters.policy_version),
            _optional_value_matches(analysis.as_of_date, filters.as_of_date),
            _optional_value_matches(analysis.state, filters.state),
        )
    )


def _sort_fairness_analyses(
    analyses: list[DpmPmQualityFairnessAnalysis],
) -> list[DpmPmQualityFairnessAnalysis]:
    return sorted(
        analyses,
        key=lambda analysis: (analysis.generated_at, analysis.fairness_analysis_id),
        reverse=True,
    )


def _list_fairness_analyses(
    *,
    analyses: list[DpmPmQualityFairnessAnalysis],
    filters: _FairnessAnalysisFilters,
    limit: int,
    offset: int,
) -> list[DpmPmQualityFairnessAnalysis]:
    filtered = [
        analysis for analysis in analyses if _fairness_analysis_matches_filters(analysis, filters)
    ]
    return _sort_fairness_analyses(filtered)[offset : offset + limit]


def _review_action_matches_filters(
    action: DpmPmQualityReviewAction,
    filters: _ReviewActionFilters,
) -> bool:
    return all(
        (
            _optional_value_matches(action.target_type, filters.target_type),
            _optional_value_matches(action.target_id, filters.target_id),
            _optional_value_matches(action.policy_id, filters.policy_id),
            _optional_value_matches(action.as_of_date, filters.as_of_date),
            _optional_value_matches(action.action_state, filters.action_state),
        )
    )


def _sort_review_actions(
    actions: list[DpmPmQualityReviewAction],
) -> list[DpmPmQualityReviewAction]:
    return sorted(
        actions,
        key=lambda action: (action.generated_at, action.review_action_id),
        reverse=True,
    )


def _list_review_actions(
    *,
    actions: list[DpmPmQualityReviewAction],
    filters: _ReviewActionFilters,
    limit: int,
    offset: int,
) -> list[DpmPmQualityReviewAction]:
    filtered = [action for action in actions if _review_action_matches_filters(action, filters)]
    return _sort_review_actions(filtered)[offset : offset + limit]


def _summary_invocation_matches_filters(
    invocation: DpmPmQualitySummaryInvocation,
    filters: _SummaryInvocationFilters,
) -> bool:
    return all(
        (
            _optional_value_matches(invocation.score_run_id, filters.score_run_id),
            _optional_value_matches(invocation.review_action_id, filters.review_action_id),
            _optional_value_matches(invocation.policy_id, filters.policy_id),
            _optional_value_matches(invocation.as_of_date, filters.as_of_date),
            _optional_value_matches(invocation.invocation_state, filters.invocation_state),
        )
    )


def _optional_value_matches(actual: str | None, expected: str | None) -> bool:
    return expected is None or actual == expected


def _optional_bool_matches(actual: bool, expected: bool | None) -> bool:
    return expected is None or actual == expected


def _sort_summary_invocations(
    invocations: list[DpmPmQualitySummaryInvocation],
) -> list[DpmPmQualitySummaryInvocation]:
    return sorted(
        invocations,
        key=lambda invocation: (invocation.generated_at, invocation.summary_invocation_id),
        reverse=True,
    )


def _list_summary_invocations(
    *,
    invocations: list[DpmPmQualitySummaryInvocation],
    filters: _SummaryInvocationFilters,
    limit: int,
    offset: int,
) -> list[DpmPmQualitySummaryInvocation]:
    filtered = [
        invocation
        for invocation in invocations
        if _summary_invocation_matches_filters(invocation, filters)
    ]
    return _sort_summary_invocations(filtered)[offset : offset + limit]


def _validate_review_action_parent(
    *,
    tenant_id: str,
    action: DpmPmQualityReviewAction,
    score_run_repository: DpmPmQualityScoreRunRepository | None,
    fairness_analysis_repository: DpmPmQualityFairnessAnalysisRepository | None,
) -> None:
    target: DpmPmOperatingQualityScoreRun | DpmPmQualityFairnessAnalysis | None
    if action.target_type == "SCORE_RUN":
        if score_run_repository is None:
            return
        target = score_run_repository.get_score_run(
            tenant_id=tenant_id,
            score_run_id=action.target_id,
        )
    elif action.target_type == "FAIRNESS_ANALYSIS":
        if fairness_analysis_repository is None:
            return
        target = fairness_analysis_repository.get_fairness_analysis(
            tenant_id=tenant_id, fairness_analysis_id=action.target_id
        )
    else:
        raise DpmPmQualityReviewActionIntegrityError(
            "PM_QUALITY_REVIEW_ACTION_TARGET_TYPE_UNSUPPORTED"
        )
    if target is None:
        raise DpmPmQualityReviewActionIntegrityError("PM_QUALITY_REVIEW_ACTION_TARGET_NOT_FOUND")
    if (
        target.content_hash != action.target_content_hash
        or target.policy_id != action.policy_id
        or target.policy_version != action.policy_version
        or target.as_of_date != action.as_of_date
        or target.state != action.target_state
    ):
        raise DpmPmQualityReviewActionIntegrityError("PM_QUALITY_REVIEW_ACTION_TARGET_MISMATCH")


def _validate_summary_invocation_parents(
    *,
    tenant_id: str,
    invocation: DpmPmQualitySummaryInvocation,
    score_run_repository: DpmPmQualityScoreRunRepository | None,
    review_action_repository: DpmPmQualityReviewActionRepository | None,
) -> None:
    score_run = (
        None
        if score_run_repository is None
        else score_run_repository.get_score_run(
            tenant_id=tenant_id,
            score_run_id=invocation.score_run_id,
        )
    )
    if score_run_repository is not None and score_run is None:
        raise DpmPmQualitySummaryInvocationIntegrityError(
            "PM_QUALITY_SUMMARY_INVOCATION_SCORE_RUN_NOT_FOUND"
        )
    if score_run is not None and (
        score_run.content_hash != invocation.score_run_content_hash
        or score_run.policy_id != invocation.policy_id
        or score_run.policy_version != invocation.policy_version
        or score_run.as_of_date != invocation.as_of_date
    ):
        raise DpmPmQualitySummaryInvocationIntegrityError(
            "PM_QUALITY_SUMMARY_INVOCATION_SCORE_RUN_MISMATCH"
        )
    review_action = (
        None
        if review_action_repository is None
        else review_action_repository.get_review_action(
            tenant_id=tenant_id, review_action_id=invocation.review_action_id
        )
    )
    if review_action_repository is not None and review_action is None:
        raise DpmPmQualitySummaryInvocationIntegrityError(
            "PM_QUALITY_SUMMARY_INVOCATION_REVIEW_ACTION_NOT_FOUND"
        )
    if review_action is not None and (
        review_action.content_hash != invocation.review_action_content_hash
        or review_action.target_type != "SCORE_RUN"
        or review_action.target_id != invocation.score_run_id
        or review_action.policy_id != invocation.policy_id
        or review_action.policy_version != invocation.policy_version
        or review_action.as_of_date != invocation.as_of_date
    ):
        raise DpmPmQualitySummaryInvocationIntegrityError(
            "PM_QUALITY_SUMMARY_INVOCATION_REVIEW_ACTION_MISMATCH"
        )


def _ensure_record_tenant(*, tenant_id: str, record_tenant_id: str) -> None:
    if not tenant_id.strip():
        raise ValueError("PM_QUALITY_TENANT_REQUIRED")
    if record_tenant_id != tenant_id:
        raise ValueError("PM_QUALITY_TENANT_MISMATCH")


def _policy_hash(policy: DpmPmOperatingQualityPolicy) -> str:
    canonical = json.dumps(policy.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
