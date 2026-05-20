import os
from typing import AsyncIterator

from src.infrastructure.advise_authority import (
    LotusAdviseAuthorityClient,
    LotusAdviseAuthorityConfig,
)
from src.core.construction.repository import ConstructionRepository
from src.core.mandate_repository import DpmMandateRepository
from src.core.proof_packs.repository import DpmProofPackRepository
from src.core.outcomes.repository import DpmOutcomeReviewRepository
from src.core.pm_quality.repository import (
    DpmPmQualityFairnessAnalysisRepository,
    DpmPmQualityPolicyRepository,
    DpmPmQualityReviewActionRepository,
    DpmPmQualityScoreRunRepository,
)
from src.core.waves.repository import DpmWaveRepository
from src.core.waves.campaign_repository import DpmBulkReviewCampaignDefinitionRepository
from src.infrastructure.construction import InMemoryConstructionRepository
from src.infrastructure.construction import PostgresConstructionRepository
from src.infrastructure.mandates import InMemoryDpmMandateRepository, PostgresDpmMandateRepository
from src.infrastructure.proof_packs import (
    InMemoryDpmProofPackRepository,
    PostgresDpmProofPackRepository,
)
from src.infrastructure.outcomes import (
    InMemoryDpmOutcomeReviewRepository,
    PostgresDpmOutcomeReviewRepository,
)
from src.infrastructure.pm_quality import (
    InMemoryDpmPmQualityFairnessAnalysisRepository,
    InMemoryDpmPmQualityPolicyRepository,
    InMemoryDpmPmQualityReviewActionRepository,
    InMemoryDpmPmQualityScoreRunRepository,
    PostgresDpmPmQualityFairnessAnalysisRepository,
    PostgresDpmPmQualityPolicyRepository,
    PostgresDpmPmQualityReviewActionRepository,
    PostgresDpmPmQualityScoreRunRepository,
)
from src.infrastructure.risk_authority import LotusRiskAuthorityClient, LotusRiskAuthorityConfig
from src.infrastructure.waves import (
    InMemoryDpmBulkReviewCampaignDefinitionRepository,
    InMemoryDpmWaveRepository,
    PostgresDpmBulkReviewCampaignDefinitionRepository,
    PostgresDpmWaveRepository,
)


_MANDATE_REPOSITORY = InMemoryDpmMandateRepository()
_CONSTRUCTION_REPOSITORY = InMemoryConstructionRepository()
_PROOF_PACK_REPOSITORY = InMemoryDpmProofPackRepository()
_OUTCOME_REVIEW_REPOSITORY = InMemoryDpmOutcomeReviewRepository()
_PM_QUALITY_POLICY_REPOSITORY = InMemoryDpmPmQualityPolicyRepository()
_PM_QUALITY_SCORE_RUN_REPOSITORY = InMemoryDpmPmQualityScoreRunRepository()
_PM_QUALITY_FAIRNESS_ANALYSIS_REPOSITORY = InMemoryDpmPmQualityFairnessAnalysisRepository()
_PM_QUALITY_REVIEW_ACTION_REPOSITORY = InMemoryDpmPmQualityReviewActionRepository()
_WAVE_REPOSITORY = InMemoryDpmWaveRepository()
_CAMPAIGN_DEFINITION_REPOSITORY = InMemoryDpmBulkReviewCampaignDefinitionRepository()
_POSTGRES_MANDATE_REPOSITORY: PostgresDpmMandateRepository | None = None
_POSTGRES_CONSTRUCTION_REPOSITORY: PostgresConstructionRepository | None = None
_POSTGRES_PROOF_PACK_REPOSITORY: PostgresDpmProofPackRepository | None = None
_POSTGRES_OUTCOME_REVIEW_REPOSITORY: PostgresDpmOutcomeReviewRepository | None = None
_POSTGRES_PM_QUALITY_POLICY_REPOSITORY: PostgresDpmPmQualityPolicyRepository | None = None
_POSTGRES_PM_QUALITY_SCORE_RUN_REPOSITORY: PostgresDpmPmQualityScoreRunRepository | None = None
_POSTGRES_PM_QUALITY_FAIRNESS_ANALYSIS_REPOSITORY: (
    PostgresDpmPmQualityFairnessAnalysisRepository | None
) = None
_POSTGRES_PM_QUALITY_REVIEW_ACTION_REPOSITORY: PostgresDpmPmQualityReviewActionRepository | None = (
    None
)
_POSTGRES_WAVE_REPOSITORY: PostgresDpmWaveRepository | None = None
_POSTGRES_CAMPAIGN_DEFINITION_REPOSITORY: (
    PostgresDpmBulkReviewCampaignDefinitionRepository | None
) = None


async def get_db_session() -> AsyncIterator[None]:
    """Stub for Database Session (RFC-0005). To be replaced with actual AsyncPG session."""
    yield None


def get_mandate_repository() -> DpmMandateRepository:
    """Return the mandate repository used by RFC-0038 APIs.

    The default local profile is in-memory so the API remains usable in developer and test
    runtimes. Production wiring can replace this dependency with the Postgres-backed repository
    once the deployment profile injects a managed connection provider.
    """

    dsn = _repository_dsn("DPM_MANDATE_POSTGRES_DSN")
    if dsn:
        global _POSTGRES_MANDATE_REPOSITORY
        if _POSTGRES_MANDATE_REPOSITORY is None:
            _POSTGRES_MANDATE_REPOSITORY = PostgresDpmMandateRepository(dsn=dsn)
        return _POSTGRES_MANDATE_REPOSITORY
    return _MANDATE_REPOSITORY


def get_construction_repository() -> ConstructionRepository:
    """Return the RFC-0039 construction repository for local and test runtimes."""

    dsn = _repository_dsn("DPM_CONSTRUCTION_POSTGRES_DSN")
    if dsn:
        global _POSTGRES_CONSTRUCTION_REPOSITORY
        if _POSTGRES_CONSTRUCTION_REPOSITORY is None:
            _POSTGRES_CONSTRUCTION_REPOSITORY = PostgresConstructionRepository(dsn=dsn)
        return _POSTGRES_CONSTRUCTION_REPOSITORY
    return _CONSTRUCTION_REPOSITORY


def get_proof_pack_repository() -> DpmProofPackRepository:
    """Return the RFC-0040 proof-pack repository for local and test runtimes."""

    dsn = _repository_dsn("DPM_PROOF_PACK_POSTGRES_DSN")
    if dsn:
        global _POSTGRES_PROOF_PACK_REPOSITORY
        if _POSTGRES_PROOF_PACK_REPOSITORY is None:
            _POSTGRES_PROOF_PACK_REPOSITORY = PostgresDpmProofPackRepository(dsn=dsn)
        return _POSTGRES_PROOF_PACK_REPOSITORY
    return _PROOF_PACK_REPOSITORY


def get_outcome_review_repository() -> DpmOutcomeReviewRepository:
    """Return the RFC-0042 outcome-review repository for local and test runtimes."""

    dsn = _repository_dsn("DPM_OUTCOME_REVIEW_POSTGRES_DSN")
    if dsn:
        global _POSTGRES_OUTCOME_REVIEW_REPOSITORY
        if _POSTGRES_OUTCOME_REVIEW_REPOSITORY is None:
            _POSTGRES_OUTCOME_REVIEW_REPOSITORY = PostgresDpmOutcomeReviewRepository(dsn=dsn)
        return _POSTGRES_OUTCOME_REVIEW_REPOSITORY
    return _OUTCOME_REVIEW_REPOSITORY


def get_pm_quality_score_run_repository() -> DpmPmQualityScoreRunRepository:
    """Return the PM operating quality score-run repository for local and test runtimes."""

    dsn = _repository_dsn("DPM_PM_QUALITY_POSTGRES_DSN")
    if dsn:
        global _POSTGRES_PM_QUALITY_SCORE_RUN_REPOSITORY
        if _POSTGRES_PM_QUALITY_SCORE_RUN_REPOSITORY is None:
            _POSTGRES_PM_QUALITY_SCORE_RUN_REPOSITORY = PostgresDpmPmQualityScoreRunRepository(
                dsn=dsn
            )
        return _POSTGRES_PM_QUALITY_SCORE_RUN_REPOSITORY
    return _PM_QUALITY_SCORE_RUN_REPOSITORY


def get_pm_quality_policy_repository() -> DpmPmQualityPolicyRepository:
    """Return the PM operating quality policy repository for local and test runtimes."""

    dsn = _repository_dsn("DPM_PM_QUALITY_POSTGRES_DSN")
    if dsn:
        global _POSTGRES_PM_QUALITY_POLICY_REPOSITORY
        if _POSTGRES_PM_QUALITY_POLICY_REPOSITORY is None:
            _POSTGRES_PM_QUALITY_POLICY_REPOSITORY = PostgresDpmPmQualityPolicyRepository(dsn=dsn)
        return _POSTGRES_PM_QUALITY_POLICY_REPOSITORY
    return _PM_QUALITY_POLICY_REPOSITORY


def get_pm_quality_fairness_analysis_repository() -> DpmPmQualityFairnessAnalysisRepository:
    """Return the PM operating quality fairness-analysis repository for local and test runtimes."""

    dsn = _repository_dsn("DPM_PM_QUALITY_POSTGRES_DSN")
    if dsn:
        global _POSTGRES_PM_QUALITY_FAIRNESS_ANALYSIS_REPOSITORY
        if _POSTGRES_PM_QUALITY_FAIRNESS_ANALYSIS_REPOSITORY is None:
            _POSTGRES_PM_QUALITY_FAIRNESS_ANALYSIS_REPOSITORY = (
                PostgresDpmPmQualityFairnessAnalysisRepository(dsn=dsn)
            )
        return _POSTGRES_PM_QUALITY_FAIRNESS_ANALYSIS_REPOSITORY
    return _PM_QUALITY_FAIRNESS_ANALYSIS_REPOSITORY


def get_pm_quality_review_action_repository() -> DpmPmQualityReviewActionRepository:
    """Return the PM operating quality review-action repository for local and test runtimes."""

    dsn = _repository_dsn("DPM_PM_QUALITY_POSTGRES_DSN")
    if dsn:
        global _POSTGRES_PM_QUALITY_REVIEW_ACTION_REPOSITORY
        if _POSTGRES_PM_QUALITY_REVIEW_ACTION_REPOSITORY is None:
            _POSTGRES_PM_QUALITY_REVIEW_ACTION_REPOSITORY = (
                PostgresDpmPmQualityReviewActionRepository(dsn=dsn)
            )
        return _POSTGRES_PM_QUALITY_REVIEW_ACTION_REPOSITORY
    return _PM_QUALITY_REVIEW_ACTION_REPOSITORY


def get_wave_repository() -> DpmWaveRepository:
    """Return the RFC-0041 rebalance-wave repository for local and test runtimes."""

    dsn = _repository_dsn("DPM_WAVE_POSTGRES_DSN")
    if dsn:
        global _POSTGRES_WAVE_REPOSITORY
        if _POSTGRES_WAVE_REPOSITORY is None:
            _POSTGRES_WAVE_REPOSITORY = PostgresDpmWaveRepository(dsn=dsn)
        return _POSTGRES_WAVE_REPOSITORY
    return _WAVE_REPOSITORY


def get_campaign_definition_repository() -> DpmBulkReviewCampaignDefinitionRepository:
    """Return the Manage-owned bulk-review campaign definition repository."""

    dsn = _repository_dsn("DPM_CAMPAIGN_DEFINITION_POSTGRES_DSN")
    if dsn:
        global _POSTGRES_CAMPAIGN_DEFINITION_REPOSITORY
        if _POSTGRES_CAMPAIGN_DEFINITION_REPOSITORY is None:
            _POSTGRES_CAMPAIGN_DEFINITION_REPOSITORY = (
                PostgresDpmBulkReviewCampaignDefinitionRepository(dsn=dsn)
            )
        return _POSTGRES_CAMPAIGN_DEFINITION_REPOSITORY
    return _CAMPAIGN_DEFINITION_REPOSITORY


def get_risk_authority_client() -> LotusRiskAuthorityClient | None:
    """Return a lotus-risk authority client when risk integration is configured."""

    base_url = os.getenv("DPM_RISK_BASE_URL", "").strip()
    if not base_url:
        return None
    return LotusRiskAuthorityClient(config=LotusRiskAuthorityConfig(base_url=base_url))


def get_advise_authority_client() -> LotusAdviseAuthorityClient | None:
    """Return a lotus-advise authority client when advisory source integration is configured."""

    base_url = os.getenv("DPM_ADVISE_BASE_URL", "").strip()
    if not base_url:
        return None
    return LotusAdviseAuthorityClient(config=LotusAdviseAuthorityConfig(base_url=base_url))


def _repository_dsn(primary_env_name: str) -> str:
    return (
        os.getenv(primary_env_name, "").strip()
        or os.getenv("DPM_MANAGE_POSTGRES_DSN", "").strip()
        or os.getenv("DPM_SUPPORTABILITY_POSTGRES_DSN", "").strip()
    )
