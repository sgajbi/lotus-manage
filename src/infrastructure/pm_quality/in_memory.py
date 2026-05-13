from __future__ import annotations

from copy import deepcopy
from threading import Lock

from src.core.pm_quality.models import DpmPmOperatingQualityScoreRun
from src.core.pm_quality.repository import (
    DpmPmQualityScoreRunConflictError,
    DpmPmQualityScoreRunRepository,
)


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
