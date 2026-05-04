from src.api import dependencies
from src.infrastructure.construction import InMemoryConstructionRepository
from src.infrastructure.mandates import InMemoryDpmMandateRepository
from src.infrastructure.proof_packs import InMemoryDpmProofPackRepository
from src.infrastructure.risk_authority import LotusRiskAuthorityClient
from src.infrastructure.waves import InMemoryDpmWaveRepository


def test_repository_dependencies_return_default_singletons(monkeypatch) -> None:
    monkeypatch.delenv("DPM_SUPPORTABILITY_POSTGRES_DSN", raising=False)
    monkeypatch.delenv("DPM_MANAGE_POSTGRES_DSN", raising=False)
    assert isinstance(dependencies.get_construction_repository(), InMemoryConstructionRepository)
    assert isinstance(dependencies.get_mandate_repository(), InMemoryDpmMandateRepository)
    assert isinstance(dependencies.get_proof_pack_repository(), InMemoryDpmProofPackRepository)
    assert isinstance(dependencies.get_wave_repository(), InMemoryDpmWaveRepository)


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


def test_risk_authority_dependency_is_configured_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("DPM_RISK_BASE_URL", "http://risk.local")

    client = dependencies.get_risk_authority_client()

    assert isinstance(client, LotusRiskAuthorityClient)
