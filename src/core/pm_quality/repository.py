"""Persistence contracts for PM operating quality score runs."""

from typing import Protocol

from src.core.pm_quality.models import DpmPmOperatingQualityScoreRun


class DpmPmQualityScoreRunConflictError(Exception):
    """Raised when immutable score-run identity conflicts."""


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
