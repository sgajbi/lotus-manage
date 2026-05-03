from src.api import dependencies
from src.infrastructure.construction import InMemoryConstructionRepository
from src.infrastructure.proof_packs import InMemoryDpmProofPackRepository
from src.infrastructure.risk_authority import LotusRiskAuthorityClient


def test_repository_dependencies_return_default_singletons() -> None:
    assert isinstance(dependencies.get_construction_repository(), InMemoryConstructionRepository)
    assert isinstance(dependencies.get_proof_pack_repository(), InMemoryDpmProofPackRepository)


def test_risk_authority_dependency_is_configured_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("DPM_RISK_BASE_URL", "http://risk.local")

    client = dependencies.get_risk_authority_client()

    assert isinstance(client, LotusRiskAuthorityClient)
