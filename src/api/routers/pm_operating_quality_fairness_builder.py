from __future__ import annotations

from src.api.routers.pm_operating_quality_http import (
    pm_quality_not_found_http_exception,
    pm_quality_validation_http_exception,
)
from src.api.routers.pm_operating_quality_models import DpmPmQualityFairnessPreviewRequest
from src.api.services.pm_operating_quality_service import (
    DpmPmOperatingQualityServiceError,
    DpmPmQualityFairnessAnalysisCommand,
    DpmPmQualityFairnessSegmentCommand,
    build_pm_quality_fairness_analysis_from_command,
)
from src.core.pm_quality import (
    DpmPmQualityFairnessAnalysis,
    DpmPmQualityScoreRunRepository,
)


def build_fairness_analysis_response_model(
    *,
    request: DpmPmQualityFairnessPreviewRequest,
    x_correlation_id: str | None,
    repository: DpmPmQualityScoreRunRepository,
) -> DpmPmQualityFairnessAnalysis:
    command = DpmPmQualityFairnessAnalysisCommand(
        policy_id=request.policy_id,
        policy_version=request.policy_version,
        as_of_date=request.as_of_date,
        segments=[
            DpmPmQualityFairnessSegmentCommand(
                segment_id=segment.segment_id,
                segment_type=segment.segment_type,
                display_name=segment.display_name,
                score_run_ids=segment.score_run_ids,
                source_refs=segment.source_refs,
            )
            for segment in request.segments
        ],
        minimum_segment_score_run_count=request.minimum_segment_score_run_count,
        maximum_average_score_spread=request.maximum_average_score_spread,
        actor_id=request.actor_id,
        correlation_id=x_correlation_id or request.actor_id,
    )
    try:
        return build_pm_quality_fairness_analysis_from_command(
            command=command,
            score_run_repository=repository,
        )
    except DpmPmOperatingQualityServiceError as exc:
        not_found_prefix = "PM_QUALITY_SCORE_RUN_NOT_FOUND:"
        if exc.code.startswith(not_found_prefix):
            raise pm_quality_not_found_http_exception(
                code="PM_QUALITY_SCORE_RUN_NOT_FOUND",
                identifier=exc.code.removeprefix(not_found_prefix),
            ) from exc
        raise pm_quality_validation_http_exception(exc.code) from exc
