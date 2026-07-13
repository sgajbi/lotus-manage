"""Persistence contracts for PM operating quality policies and score runs."""

from typing import Protocol

from src.core.pm_quality.models import (
    DpmPmOperatingQualityPolicy,
    DpmPmOperatingQualityScoreRun,
    DpmPmQualityFairnessAnalysis,
    DpmPmQualityReviewAction,
    DpmPmQualitySummaryInvocation,
)


class DpmPmQualityScoreRunConflictError(Exception):
    """Raised when immutable score-run identity conflicts."""


class DpmPmQualityFairnessAnalysisConflictError(Exception):
    """Raised when immutable fairness-analysis identity conflicts."""


class DpmPmQualityReviewActionConflictError(Exception):
    """Raised when immutable review-action identity conflicts."""


class DpmPmQualityReviewActionIntegrityError(Exception):
    """Raised when review-action target lineage is not persisted or coherent."""


class DpmPmQualitySummaryInvocationConflictError(Exception):
    """Raised when immutable summary-invocation identity conflicts."""


class DpmPmQualitySummaryInvocationIntegrityError(Exception):
    """Raised when summary-invocation parent lineage is not persisted or coherent."""


class DpmPmQualityPolicyConflictError(Exception):
    """Raised when immutable policy version identity conflicts."""


class DpmPmQualityPolicyRepository(Protocol):
    def save_policy(self, *, tenant_id: str, policy: DpmPmOperatingQualityPolicy) -> None:
        """Persist an immutable PM operating quality policy version."""

    def get_policy(
        self,
        *,
        tenant_id: str,
        policy_id: str,
        policy_version: str,
    ) -> DpmPmOperatingQualityPolicy | None:
        """Return a policy version by id, or None when absent."""

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
        """Return a bounded page of policy versions."""


class DpmPmQualityScoreRunRepository(Protocol):
    def save_score_run(self, *, tenant_id: str, score_run: DpmPmOperatingQualityScoreRun) -> None:
        """Persist an immutable PM operating quality score run."""

    def get_score_run(
        self,
        *,
        tenant_id: str,
        score_run_id: str,
    ) -> DpmPmOperatingQualityScoreRun | None:
        """Return a score run by id, or None when absent."""

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
        """Return a bounded page of score runs."""


class DpmPmQualityFairnessAnalysisRepository(Protocol):
    def save_fairness_analysis(
        self, *, tenant_id: str, analysis: DpmPmQualityFairnessAnalysis
    ) -> None:
        """Persist an immutable PM operating quality fairness analysis."""

    def get_fairness_analysis(
        self,
        *,
        tenant_id: str,
        fairness_analysis_id: str,
    ) -> DpmPmQualityFairnessAnalysis | None:
        """Return a fairness analysis by id, or None when absent."""

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
        """Return a bounded page of persisted fairness analyses."""


class DpmPmQualityReviewActionRepository(Protocol):
    def save_review_action(self, *, tenant_id: str, action: DpmPmQualityReviewAction) -> None:
        """Persist an immutable PM operating-quality review action."""

    def get_review_action(
        self,
        *,
        tenant_id: str,
        review_action_id: str,
    ) -> DpmPmQualityReviewAction | None:
        """Return a review action by id, or None when absent."""

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
        """Return a bounded page of persisted review actions."""


class DpmPmQualitySummaryInvocationRepository(Protocol):
    def save_summary_invocation(
        self, *, tenant_id: str, invocation: DpmPmQualitySummaryInvocation
    ) -> None:
        """Persist an immutable PM-quality support-summary invocation record."""

    def get_summary_invocation(
        self,
        *,
        tenant_id: str,
        summary_invocation_id: str,
    ) -> DpmPmQualitySummaryInvocation | None:
        """Return a summary invocation by id, or None when absent."""

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
        """Return a bounded page of persisted summary invocations."""
