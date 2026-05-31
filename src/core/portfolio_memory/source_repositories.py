"""Repository dependency bundle for portfolio-memory source reads."""

from dataclasses import dataclass

from src.core.construction.repository import ConstructionRepository
from src.core.mandate_repository import DpmMandateRepository
from src.core.pm_quality.repository import (
    DpmPmQualityReviewActionRepository,
    DpmPmQualityScoreRunRepository,
    DpmPmQualitySummaryInvocationRepository,
)
from src.core.outcomes.repository import DpmOutcomeReviewRepository
from src.core.proof_packs.repository import DpmProofPackRepository
from src.core.waves.campaign_repository import DpmBulkReviewCampaignDefinitionRepository
from src.core.waves.repository import DpmWaveRepository


@dataclass(frozen=True)
class PortfolioMemorySourceRepositories:
    proof_pack_repository: DpmProofPackRepository
    wave_repository: DpmWaveRepository
    outcome_review_repository: DpmOutcomeReviewRepository
    mandate_repository: DpmMandateRepository | None = None
    construction_repository: ConstructionRepository | None = None
    pm_quality_score_run_repository: DpmPmQualityScoreRunRepository | None = None
    pm_quality_review_action_repository: DpmPmQualityReviewActionRepository | None = None
    pm_quality_summary_invocation_repository: DpmPmQualitySummaryInvocationRepository | None = None
    campaign_definition_repository: DpmBulkReviewCampaignDefinitionRepository | None = None
