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
    DpmPmQualityReviewActionRepository,
    DpmPmQualityScoreRunConflictError,
    DpmPmQualityScoreRunRepository,
    DpmPmQualitySummaryInvocationConflictError,
    DpmPmQualitySummaryInvocationRepository,
)


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
        self._policies: dict[tuple[str, str], DpmPmOperatingQualityPolicy] = {}

    def save_policy(self, *, policy: DpmPmOperatingQualityPolicy) -> None:
        key = (policy.policy_id, policy.policy_version)
        with self._lock:
            existing = self._policies.get(key)
            if existing is not None and _policy_hash(existing) != _policy_hash(policy):
                raise DpmPmQualityPolicyConflictError("PM_QUALITY_POLICY_IMMUTABLE_CONFLICT")
            self._policies[key] = deepcopy(policy)

    def get_policy(
        self,
        *,
        policy_id: str,
        policy_version: str,
    ) -> DpmPmOperatingQualityPolicy | None:
        with self._lock:
            policy = self._policies.get((policy_id, policy_version))
            return deepcopy(policy) if policy is not None else None

    def list_policies(
        self,
        *,
        policy_id: str | None = None,
        enabled: bool | None = None,
        as_of_date: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[DpmPmOperatingQualityPolicy]:
        with self._lock:
            policies = [
                policy
                for policy in self._policies.values()
                if (policy_id is None or policy.policy_id == policy_id)
                and (enabled is None or policy.enabled == enabled)
                and (as_of_date is None or policy.as_of_date == as_of_date)
            ]
            policies.sort(
                key=lambda policy: (policy.as_of_date, policy.policy_id, policy.policy_version),
                reverse=True,
            )
            return deepcopy(policies[offset : offset + limit])


class InMemoryDpmPmQualityScoreRunRepository(DpmPmQualityScoreRunRepository):
    def __init__(self) -> None:
        self._lock = Lock()
        self._score_runs: dict[str, DpmPmOperatingQualityScoreRun] = {}

    def save_score_run(self, *, score_run: DpmPmOperatingQualityScoreRun) -> None:
        with self._lock:
            existing = self._score_runs.get(score_run.score_run_id)
            if existing is not None and existing.content_hash != score_run.content_hash:
                raise DpmPmQualityScoreRunConflictError("PM_QUALITY_SCORE_RUN_IMMUTABLE_CONFLICT")
            self._score_runs[score_run.score_run_id] = deepcopy(score_run)

    def get_score_run(
        self,
        *,
        score_run_id: str,
    ) -> DpmPmOperatingQualityScoreRun | None:
        with self._lock:
            score_run = self._score_runs.get(score_run_id)
            return deepcopy(score_run) if score_run is not None else None

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
        with self._lock:
            page = _list_score_runs(
                score_runs=list(self._score_runs.values()),
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
        self._analyses: dict[str, DpmPmQualityFairnessAnalysis] = {}

    def save_fairness_analysis(self, *, analysis: DpmPmQualityFairnessAnalysis) -> None:
        with self._lock:
            existing = self._analyses.get(analysis.fairness_analysis_id)
            if existing is not None and existing.content_hash != analysis.content_hash:
                raise DpmPmQualityFairnessAnalysisConflictError(
                    "PM_QUALITY_FAIRNESS_ANALYSIS_IMMUTABLE_CONFLICT"
                )
            self._analyses[analysis.fairness_analysis_id] = deepcopy(analysis)

    def get_fairness_analysis(
        self,
        *,
        fairness_analysis_id: str,
    ) -> DpmPmQualityFairnessAnalysis | None:
        with self._lock:
            analysis = self._analyses.get(fairness_analysis_id)
            return deepcopy(analysis) if analysis is not None else None

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
        with self._lock:
            page = _list_fairness_analyses(
                analyses=list(self._analyses.values()),
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
    def __init__(self) -> None:
        self._lock = Lock()
        self._actions: dict[str, DpmPmQualityReviewAction] = {}

    def save_review_action(self, *, action: DpmPmQualityReviewAction) -> None:
        with self._lock:
            existing = self._actions.get(action.review_action_id)
            if existing is not None and existing.content_hash != action.content_hash:
                raise DpmPmQualityReviewActionConflictError(
                    "PM_QUALITY_REVIEW_ACTION_IMMUTABLE_CONFLICT"
                )
            self._actions[action.review_action_id] = deepcopy(action)

    def get_review_action(
        self,
        *,
        review_action_id: str,
    ) -> DpmPmQualityReviewAction | None:
        with self._lock:
            action = self._actions.get(review_action_id)
            return deepcopy(action) if action is not None else None

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
        with self._lock:
            page = _list_review_actions(
                actions=list(self._actions.values()),
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
    def __init__(self) -> None:
        self._lock = Lock()
        self._invocations: dict[str, DpmPmQualitySummaryInvocation] = {}

    def save_summary_invocation(self, *, invocation: DpmPmQualitySummaryInvocation) -> None:
        with self._lock:
            existing = self._invocations.get(invocation.summary_invocation_id)
            if existing is not None and existing.content_hash != invocation.content_hash:
                raise DpmPmQualitySummaryInvocationConflictError(
                    "PM_QUALITY_SUMMARY_INVOCATION_IMMUTABLE_CONFLICT"
                )
            self._invocations[invocation.summary_invocation_id] = deepcopy(invocation)

    def get_summary_invocation(
        self,
        *,
        summary_invocation_id: str,
    ) -> DpmPmQualitySummaryInvocation | None:
        with self._lock:
            invocation = self._invocations.get(summary_invocation_id)
            return deepcopy(invocation) if invocation is not None else None

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
        with self._lock:
            page = _list_summary_invocations(
                invocations=list(self._invocations.values()),
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


def _policy_hash(policy: DpmPmOperatingQualityPolicy) -> str:
    canonical = json.dumps(policy.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
