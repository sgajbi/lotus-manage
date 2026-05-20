from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from threading import Lock

from src.core.pm_quality.models import (
    DpmPmOperatingQualityPolicy,
    DpmPmOperatingQualityScoreRun,
    DpmPmQualityFairnessAnalysis,
    DpmPmQualityReviewAction,
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
)


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
            score_runs = [
                score_run
                for score_run in self._score_runs.values()
                if (pm_id is None or score_run.pm_id == pm_id)
                and (book_id is None or score_run.book_id == book_id)
                and (policy_id is None or score_run.policy_id == policy_id)
                and (as_of_date is None or score_run.as_of_date == as_of_date)
                and (state is None or score_run.state == state)
            ]
            score_runs.sort(
                key=lambda score_run: (score_run.generated_at, score_run.score_run_id),
                reverse=True,
            )
            return deepcopy(score_runs[offset : offset + limit])


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
            analyses = [
                analysis
                for analysis in self._analyses.values()
                if (policy_id is None or analysis.policy_id == policy_id)
                and (policy_version is None or analysis.policy_version == policy_version)
                and (as_of_date is None or analysis.as_of_date == as_of_date)
                and (state is None or analysis.state == state)
            ]
            analyses.sort(
                key=lambda analysis: (analysis.generated_at, analysis.fairness_analysis_id),
                reverse=True,
            )
            return deepcopy(analyses[offset : offset + limit])


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
            actions = [
                action
                for action in self._actions.values()
                if (target_type is None or action.target_type == target_type)
                and (target_id is None or action.target_id == target_id)
                and (policy_id is None or action.policy_id == policy_id)
                and (as_of_date is None or action.as_of_date == as_of_date)
                and (action_state is None or action.action_state == action_state)
            ]
            actions.sort(
                key=lambda action: (action.generated_at, action.review_action_id),
                reverse=True,
            )
            return deepcopy(actions[offset : offset + limit])


def _policy_hash(policy: DpmPmOperatingQualityPolicy) -> str:
    canonical = json.dumps(policy.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
