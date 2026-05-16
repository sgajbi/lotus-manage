from src.api import dependencies
from src.infrastructure.construction import InMemoryConstructionRepository
from src.infrastructure.mandates import InMemoryDpmMandateRepository
from src.infrastructure.outcomes import InMemoryDpmOutcomeReviewRepository
from src.infrastructure.pm_quality import (
    InMemoryDpmPmQualityFairnessAnalysisRepository,
    InMemoryDpmPmQualityPolicyRepository,
    InMemoryDpmPmQualityScoreRunRepository,
)
from src.infrastructure.proof_packs import InMemoryDpmProofPackRepository
from src.infrastructure.risk_authority import LotusRiskAuthorityClient
from src.infrastructure.waves import InMemoryDpmWaveRepository
from src.infrastructure.waves.campaign_definitions import (
    InMemoryDpmBulkReviewCampaignDefinitionRepository,
)


def test_repository_dependencies_return_default_singletons(monkeypatch) -> None:
    monkeypatch.delenv("DPM_SUPPORTABILITY_POSTGRES_DSN", raising=False)
    monkeypatch.delenv("DPM_MANAGE_POSTGRES_DSN", raising=False)
    assert isinstance(dependencies.get_construction_repository(), InMemoryConstructionRepository)
    assert isinstance(dependencies.get_mandate_repository(), InMemoryDpmMandateRepository)
    assert isinstance(dependencies.get_proof_pack_repository(), InMemoryDpmProofPackRepository)
    assert isinstance(dependencies.get_wave_repository(), InMemoryDpmWaveRepository)
    assert isinstance(
        dependencies.get_outcome_review_repository(),
        InMemoryDpmOutcomeReviewRepository,
    )
    assert isinstance(
        dependencies.get_pm_quality_score_run_repository(),
        InMemoryDpmPmQualityScoreRunRepository,
    )
    assert isinstance(
        dependencies.get_pm_quality_policy_repository(),
        InMemoryDpmPmQualityPolicyRepository,
    )
    assert isinstance(
        dependencies.get_pm_quality_fairness_analysis_repository(),
        InMemoryDpmPmQualityFairnessAnalysisRepository,
    )
    assert isinstance(
        dependencies.get_campaign_definition_repository(),
        InMemoryDpmBulkReviewCampaignDefinitionRepository,
    )


def test_repository_dependencies_use_canonical_postgres_dsn_when_configured(
    monkeypatch,
) -> None:
    created: list[tuple[str, str]] = []

    class FakeMandateRepository:
        def __init__(self, *, dsn: str) -> None:
            created.append(("mandate", dsn))

    class FakeConstructionRepository:
        def __init__(self, *, dsn: str) -> None:
            created.append(("construction", dsn))

    class FakeProofPackRepository:
        def __init__(self, *, dsn: str) -> None:
            created.append(("proof_pack", dsn))

    class FakeWaveRepository:
        def __init__(self, *, dsn: str) -> None:
            created.append(("wave", dsn))

    monkeypatch.setenv("DPM_MANAGE_POSTGRES_DSN", "postgresql://manage")
    monkeypatch.setattr(dependencies, "_POSTGRES_MANDATE_REPOSITORY", None)
    monkeypatch.setattr(dependencies, "_POSTGRES_CONSTRUCTION_REPOSITORY", None)
    monkeypatch.setattr(dependencies, "_POSTGRES_PROOF_PACK_REPOSITORY", None)
    monkeypatch.setattr(dependencies, "_POSTGRES_WAVE_REPOSITORY", None)
    monkeypatch.setattr(dependencies, "PostgresDpmMandateRepository", FakeMandateRepository)
    monkeypatch.setattr(dependencies, "PostgresConstructionRepository", FakeConstructionRepository)
    monkeypatch.setattr(dependencies, "PostgresDpmProofPackRepository", FakeProofPackRepository)
    monkeypatch.setattr(dependencies, "PostgresDpmWaveRepository", FakeWaveRepository)

    assert isinstance(dependencies.get_mandate_repository(), FakeMandateRepository)
    assert isinstance(dependencies.get_construction_repository(), FakeConstructionRepository)
    assert isinstance(dependencies.get_proof_pack_repository(), FakeProofPackRepository)
    assert isinstance(dependencies.get_wave_repository(), FakeWaveRepository)
    assert created == [
        ("mandate", "postgresql://manage"),
        ("construction", "postgresql://manage"),
        ("proof_pack", "postgresql://manage"),
        ("wave", "postgresql://manage"),
    ]


def test_extended_repository_dependencies_use_specific_and_fallback_postgres_dsns(
    monkeypatch,
) -> None:
    created: list[tuple[str, str]] = []

    class FakeOutcomeReviewRepository:
        def __init__(self, *, dsn: str) -> None:
            created.append(("outcome_review", dsn))

    class FakePmQualityScoreRunRepository:
        def __init__(self, *, dsn: str) -> None:
            created.append(("pm_quality_score_run", dsn))

    class FakePmQualityPolicyRepository:
        def __init__(self, *, dsn: str) -> None:
            created.append(("pm_quality_policy", dsn))

    class FakePmQualityFairnessAnalysisRepository:
        def __init__(self, *, dsn: str) -> None:
            created.append(("pm_quality_fairness_analysis", dsn))

    class FakeCampaignDefinitionRepository:
        def __init__(self, *, dsn: str) -> None:
            created.append(("campaign_definition", dsn))

    monkeypatch.delenv("DPM_MANAGE_POSTGRES_DSN", raising=False)
    monkeypatch.setenv("DPM_SUPPORTABILITY_POSTGRES_DSN", "postgresql://supportability")
    monkeypatch.setenv("DPM_OUTCOME_REVIEW_POSTGRES_DSN", "postgresql://outcomes")
    monkeypatch.setenv("DPM_PM_QUALITY_POSTGRES_DSN", "postgresql://pm-quality")
    monkeypatch.setattr(dependencies, "_POSTGRES_OUTCOME_REVIEW_REPOSITORY", None)
    monkeypatch.setattr(dependencies, "_POSTGRES_PM_QUALITY_SCORE_RUN_REPOSITORY", None)
    monkeypatch.setattr(dependencies, "_POSTGRES_PM_QUALITY_POLICY_REPOSITORY", None)
    monkeypatch.setattr(dependencies, "_POSTGRES_PM_QUALITY_FAIRNESS_ANALYSIS_REPOSITORY", None)
    monkeypatch.setattr(dependencies, "_POSTGRES_CAMPAIGN_DEFINITION_REPOSITORY", None)
    monkeypatch.setattr(
        dependencies,
        "PostgresDpmOutcomeReviewRepository",
        FakeOutcomeReviewRepository,
    )
    monkeypatch.setattr(
        dependencies,
        "PostgresDpmPmQualityScoreRunRepository",
        FakePmQualityScoreRunRepository,
    )
    monkeypatch.setattr(
        dependencies,
        "PostgresDpmPmQualityPolicyRepository",
        FakePmQualityPolicyRepository,
    )
    monkeypatch.setattr(
        dependencies,
        "PostgresDpmPmQualityFairnessAnalysisRepository",
        FakePmQualityFairnessAnalysisRepository,
    )
    monkeypatch.setattr(
        dependencies,
        "PostgresDpmBulkReviewCampaignDefinitionRepository",
        FakeCampaignDefinitionRepository,
    )

    assert isinstance(
        dependencies.get_outcome_review_repository(),
        FakeOutcomeReviewRepository,
    )
    assert isinstance(
        dependencies.get_pm_quality_score_run_repository(),
        FakePmQualityScoreRunRepository,
    )
    assert isinstance(
        dependencies.get_pm_quality_policy_repository(),
        FakePmQualityPolicyRepository,
    )
    assert isinstance(
        dependencies.get_pm_quality_fairness_analysis_repository(),
        FakePmQualityFairnessAnalysisRepository,
    )
    assert isinstance(
        dependencies.get_campaign_definition_repository(),
        FakeCampaignDefinitionRepository,
    )
    assert isinstance(
        dependencies.get_outcome_review_repository(),
        FakeOutcomeReviewRepository,
    )
    assert isinstance(
        dependencies.get_pm_quality_score_run_repository(),
        FakePmQualityScoreRunRepository,
    )
    assert isinstance(
        dependencies.get_pm_quality_policy_repository(),
        FakePmQualityPolicyRepository,
    )
    assert isinstance(
        dependencies.get_pm_quality_fairness_analysis_repository(),
        FakePmQualityFairnessAnalysisRepository,
    )
    assert isinstance(
        dependencies.get_campaign_definition_repository(),
        FakeCampaignDefinitionRepository,
    )
    assert created == [
        ("outcome_review", "postgresql://outcomes"),
        ("pm_quality_score_run", "postgresql://pm-quality"),
        ("pm_quality_policy", "postgresql://pm-quality"),
        ("pm_quality_fairness_analysis", "postgresql://pm-quality"),
        ("campaign_definition", "postgresql://supportability"),
    ]


def test_risk_authority_dependency_is_configured_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("DPM_RISK_BASE_URL", "http://risk.local")

    client = dependencies.get_risk_authority_client()

    assert isinstance(client, LotusRiskAuthorityClient)


def test_advise_authority_dependency_is_configured_from_environment(monkeypatch) -> None:
    monkeypatch.delenv("DPM_ADVISE_BASE_URL", raising=False)
    assert dependencies.get_advise_authority_client() is None

    monkeypatch.setenv("DPM_ADVISE_BASE_URL", "http://advise.local")

    client = dependencies.get_advise_authority_client()

    assert client is not None
    assert client._config.base_url == "http://advise.local"
