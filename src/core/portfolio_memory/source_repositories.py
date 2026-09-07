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


def pm_quality_sources_present(repositories: PortfolioMemorySourceRepositories) -> bool:
    return (
        repositories.pm_quality_score_run_repository is not None
        or repositories.pm_quality_review_action_repository is not None
        or repositories.pm_quality_summary_invocation_repository is not None
    )


def campaign_definition_sources_present(repositories: PortfolioMemorySourceRepositories) -> bool:
    return repositories.campaign_definition_repository is not None


def require_pm_quality_tenant_id(
    *,
    tenant_id: str | None,
    repositories: PortfolioMemorySourceRepositories,
) -> str | None:
    if not pm_quality_sources_present(repositories):
        return None
    if tenant_id is None or not tenant_id.strip():
        raise ValueError("tenant_id is required when portfolio memory includes PM-quality sources")
    return tenant_id.strip()


def require_campaign_definition_tenant_id(
    *,
    tenant_id: str | None,
    repositories: PortfolioMemorySourceRepositories,
) -> str | None:
    if not campaign_definition_sources_present(repositories):
        return None
    if tenant_id is None or not tenant_id.strip():
        raise ValueError(
            "tenant_id is required when portfolio memory includes campaign-definition sources"
        )
    return tenant_id.strip()


def require_mandate_tenant_id(
    *,
    tenant_id: str | None,
    repositories: PortfolioMemorySourceRepositories,
) -> str | None:
    if repositories.mandate_repository is None:
        return None
    if tenant_id is None or not tenant_id.strip():
        raise ValueError("tenant_id is required when portfolio memory includes mandate sources")
    return tenant_id.strip()


def build_portfolio_memory_source_repositories(
    *,
    proof_pack_repository: DpmProofPackRepository,
    wave_repository: DpmWaveRepository,
    outcome_review_repository: DpmOutcomeReviewRepository,
    mandate_repository: DpmMandateRepository | None = None,
    construction_repository: ConstructionRepository | None = None,
    pm_quality_score_run_repository: DpmPmQualityScoreRunRepository | None = None,
    pm_quality_review_action_repository: DpmPmQualityReviewActionRepository | None = None,
    pm_quality_summary_invocation_repository: DpmPmQualitySummaryInvocationRepository | None = None,
    campaign_definition_repository: DpmBulkReviewCampaignDefinitionRepository | None = None,
) -> PortfolioMemorySourceRepositories:
    return PortfolioMemorySourceRepositories(
        proof_pack_repository=proof_pack_repository,
        wave_repository=wave_repository,
        outcome_review_repository=outcome_review_repository,
        mandate_repository=mandate_repository,
        construction_repository=construction_repository,
        pm_quality_score_run_repository=pm_quality_score_run_repository,
        pm_quality_review_action_repository=pm_quality_review_action_repository,
        pm_quality_summary_invocation_repository=pm_quality_summary_invocation_repository,
        campaign_definition_repository=campaign_definition_repository,
    )
