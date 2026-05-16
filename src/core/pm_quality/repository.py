"""Persistence contracts for PM operating quality policies and score runs."""

from typing import Protocol

from src.core.pm_quality.models import (
    DpmPmOperatingQualityPolicy,
    DpmPmOperatingQualityScoreRun,
    DpmPmQualityFairnessAnalysis,
)


class DpmPmQualityScoreRunConflictError(Exception):
    """Raised when immutable score-run identity conflicts."""


class DpmPmQualityFairnessAnalysisConflictError(Exception):
    """Raised when immutable fairness-analysis identity conflicts."""


class DpmPmQualityPolicyConflictError(Exception):
    """Raised when immutable policy version identity conflicts."""


class DpmPmQualityPolicyRepository(Protocol):
    def save_policy(self, *, policy: DpmPmOperatingQualityPolicy) -> None:
        """Persist an immutable PM operating quality policy version."""

    def get_policy(
        self,
        *,
        policy_id: str,
        policy_version: str,
    ) -> DpmPmOperatingQualityPolicy | None:
        """Return a policy version by id, or None when absent."""

    def list_policies(
        self,
        *,
        policy_id: str | None = None,
        enabled: bool | None = None,
        as_of_date: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[DpmPmOperatingQualityPolicy]:
        """Return a bounded page of policy versions."""


class DpmPmQualityScoreRunRepository(Protocol):
    def save_score_run(self, *, score_run: DpmPmOperatingQualityScoreRun) -> None:
        """Persist an immutable PM operating quality score run."""

    def get_score_run(
        self,
        *,
        score_run_id: str,
    ) -> DpmPmOperatingQualityScoreRun | None:
        """Return a score run by id, or None when absent."""

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
        """Return a bounded page of score runs."""


class DpmPmQualityFairnessAnalysisRepository(Protocol):
    def save_fairness_analysis(self, *, analysis: DpmPmQualityFairnessAnalysis) -> None:
        """Persist an immutable PM operating quality fairness analysis."""

    def get_fairness_analysis(
        self,
        *,
        fairness_analysis_id: str,
    ) -> DpmPmQualityFairnessAnalysis | None:
        """Return a fairness analysis by id, or None when absent."""

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
        """Return a bounded page of persisted fairness analyses."""
