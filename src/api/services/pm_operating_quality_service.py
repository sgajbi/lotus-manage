from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from src.core.outcomes import DpmOutcomeSourceRef
from src.core.pm_quality import (
    DpmPmQualityFairnessAnalysis,
    DpmPmQualityFairnessSegmentInput,
    DpmPmQualityScoreRunRepository,
    DpmPmQualityValidationError,
    PmQualityFairnessSegmentType,
    build_pm_operating_quality_fairness_analysis,
)


class DpmPmOperatingQualityServiceError(ValueError):
    """API-service error with a stable PM operating-quality code."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


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
