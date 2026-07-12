from __future__ import annotations

from fastapi import APIRouter

from src.api.routers.pm_operating_quality_fairness_routes import router as fairness_router
from src.api.routers.pm_operating_quality_models import (
    DpmPmOperatingQualityPmBookScopeRequest,
    DpmPmOperatingQualityScorePreviewRequest,
    DpmPmQualityFairnessPreviewRequest,
    DpmPmQualityFairnessSegmentRequest,
    DpmPmQualityReviewActionRequest,
    DpmPmQualitySummaryInvocationRequest,
)
from src.api.routers.pm_operating_quality_policy_routes import router as policy_router
from src.api.routers.pm_operating_quality_review_action_routes import (
    register_pm_quality_review_action_routes,
)
from src.api.routers.pm_operating_quality_score_run_routes import (
    register_pm_quality_score_run_command_routes,
    register_pm_quality_score_run_read_routes,
)
from src.api.routers.pm_operating_quality_summary_routes import router as summary_router


__all__ = [
    "DpmPmOperatingQualityPmBookScopeRequest",
    "DpmPmOperatingQualityScorePreviewRequest",
    "DpmPmQualityFairnessPreviewRequest",
    "DpmPmQualityFairnessSegmentRequest",
    "DpmPmQualityReviewActionRequest",
    "DpmPmQualitySummaryInvocationRequest",
]


router = APIRouter(
    prefix="/rebalance/pm-operating-quality",
    tags=["lotus-manage PM Operating Quality"],
)


register_pm_quality_score_run_command_routes(router)


router.include_router(fairness_router)


register_pm_quality_review_action_routes(router)


router.include_router(summary_router)


router.include_router(policy_router)


register_pm_quality_score_run_read_routes(router)
