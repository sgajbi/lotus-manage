from __future__ import annotations

from typing import get_type_hints

from src.api.services import authority_client_service, construction_service


def test_construction_service_exposes_authority_client_aliases() -> None:
    assert construction_service.RiskAuthorityClient is authority_client_service.RiskAuthorityClient
    assert "RiskAuthorityClient" in construction_service.__all__


def test_construction_service_generate_alt_set_signature_uses_alias() -> None:
    annotations = get_type_hints(construction_service.generate_construction_alternative_set)
    risk_client_annotation = annotations["risk_authority_client"]
    assert risk_client_annotation == (construction_service.RiskAuthorityClient | None)
