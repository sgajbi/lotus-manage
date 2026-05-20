"""Infrastructure adapters for PM operating quality policies and score runs."""

from src.infrastructure.pm_quality.in_memory import (
    InMemoryDpmPmQualityFairnessAnalysisRepository,
    InMemoryDpmPmQualityPolicyRepository,
    InMemoryDpmPmQualityReviewActionRepository,
    InMemoryDpmPmQualityScoreRunRepository,
    InMemoryDpmPmQualitySummaryInvocationRepository,
)
from src.infrastructure.pm_quality.postgres import (
    PostgresDpmPmQualityFairnessAnalysisRepository,
    PostgresDpmPmQualityPolicyRepository,
    PostgresDpmPmQualityReviewActionRepository,
    PostgresDpmPmQualityScoreRunRepository,
    PostgresDpmPmQualitySummaryInvocationRepository,
)

__all__ = [
    "InMemoryDpmPmQualityFairnessAnalysisRepository",
    "InMemoryDpmPmQualityPolicyRepository",
    "InMemoryDpmPmQualityReviewActionRepository",
    "InMemoryDpmPmQualityScoreRunRepository",
    "InMemoryDpmPmQualitySummaryInvocationRepository",
    "PostgresDpmPmQualityFairnessAnalysisRepository",
    "PostgresDpmPmQualityPolicyRepository",
    "PostgresDpmPmQualityReviewActionRepository",
    "PostgresDpmPmQualityScoreRunRepository",
    "PostgresDpmPmQualitySummaryInvocationRepository",
]
