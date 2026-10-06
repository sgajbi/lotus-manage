"""Registered HTTP v2 behavior with test-owned trust; no live provider certification."""

import json

import pytest
from fastapi.testclient import TestClient

from src.api.dependencies import get_composite_membership_application_service
from src.api.main import app
from src.api.services.composite_membership_application import (
    DpmCompositeMembershipApplicationService,
)
from src.infrastructure.composites.in_memory import InMemoryDpmCompositeRepository
from tests.composite_authority_helpers import (
    SyntheticFixtureProviderTrust,
    definition_request,
    ending_assets_example,
    frozen_authority_pack,
    institutional_reference_wire,
    rebind_definition,
)


@pytest.fixture
def client_and_repository():
    repository = InMemoryDpmCompositeRepository()
    service = DpmCompositeMembershipApplicationService(repository=repository)
    app.dependency_overrides[get_composite_membership_application_service] = lambda: service
    try:
        with TestClient(app) as client:
            yield client, repository, service
    finally:
        app.dependency_overrides.pop(get_composite_membership_application_service, None)


def headers(tenant: str = "synthetic-tenant-a") -> dict[str, str]:
    return {"X-Tenant-Id": tenant, "X-Actor-Id": "synthetic-maker", "X-Role": "DPM_COMPOSITE_ADMIN"}


def definition_url(wire: dict) -> str:
    return f"/api/v1/rebalance/composites/{wire['composite_id']}/definitions/{wire['definition_version']}"


def test_default_trust_refuses_valid_v2_before_any_write(client_and_repository) -> None:
    client, repository, _ = client_and_repository
    wire = frozen_authority_pack()["external_versions"]["original"]["definition"]
    response = client.put(definition_url(wire), json=definition_request(wire), headers=headers())
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "COMPOSITE_PROVIDER_TRUST_UNAVAILABLE"
    assert repository.list_definitions(tenant_id=wire["tenant_id"], limit=10, offset=0).count == 0


@pytest.mark.parametrize("admit_ending_source", [False, True])
def test_ending_source_registration_is_resolved_independently_before_write(
    client_and_repository, admit_ending_source: bool
) -> None:
    client, repository, _ = client_and_repository
    wire, registry = ending_assets_example()
    resolver = SyntheticFixtureProviderTrust(registry)
    resolved_products = []

    class EndingSourceTrust:
        def resolve(self, request):
            resolved_products.append(request.source_product)
            if (
                request.source_product == "SyntheticEndingAssetObservations"
                and not admit_ending_source
            ):
                from src.core.composite_provider_trust import CompositeProviderTrustResolution

                return CompositeProviderTrustResolution("UNAVAILABLE", "ENDING_SOURCE_UNQUALIFIED")
            return resolver.resolve(request)

    service = DpmCompositeMembershipApplicationService(
        repository=repository, provider_trust=EndingSourceTrust()
    )
    app.dependency_overrides[get_composite_membership_application_service] = lambda: service
    response = client.put(definition_url(wire), json=definition_request(wire), headers=headers())
    assert "SyntheticEndingAssetObservations" in resolved_products
    if admit_ending_source:
        assert response.status_code == 200
        assert response.json() == wire
        assert client.get(definition_url(wire), headers=headers()).json() == wire
    else:
        assert response.status_code == 503
        assert response.json()["detail"]["code"] == "COMPOSITE_PROVIDER_TRUST_UNAVAILABLE"
        assert (
            repository.list_definitions(tenant_id=wire["tenant_id"], limit=10, offset=0).count == 0
        )


@pytest.mark.parametrize("inject_synthetic_registration", [False, True])
def test_institutional_reference_never_persists_without_a_qualified_verifier(
    client_and_repository, inject_synthetic_registration: bool
) -> None:
    client, repository, service = client_and_repository
    item = frozen_authority_pack()["external_versions"]["original"]
    if inject_synthetic_registration:
        service = DpmCompositeMembershipApplicationService(
            repository=repository,
            provider_trust=SyntheticFixtureProviderTrust(item["supporting_payloads"]["registry"]),
        )
        app.dependency_overrides[get_composite_membership_application_service] = lambda: service
    wire = institutional_reference_wire(item["definition"])
    response = client.put(definition_url(wire), json=definition_request(wire), headers=headers())
    assert response.status_code == 503
    assert (
        response.json()["detail"]["code"] == "COMPOSITE_AUTHORITY_ATTESTATION_VERIFIER_UNAVAILABLE"
    )
    assert repository.list_definitions(tenant_id=wire["tenant_id"], limit=10, offset=0).count == 0


def test_test_only_provider_original_corrected_retrieval_publication_and_replay(
    client_and_repository,
) -> None:
    client, repository, service = client_and_repository
    pack = frozen_authority_pack()
    registry = pack["external_versions"]["original"]["supporting_payloads"]["registry"]
    service = DpmCompositeMembershipApplicationService(
        repository=repository, provider_trust=SyntheticFixtureProviderTrust(registry)
    )
    app.dependency_overrides[get_composite_membership_application_service] = lambda: service
    for item in pack["external_versions"].values():
        wire, membership = item["definition"], item["membership"]
        url = definition_url(wire)
        request = definition_request(wire)
        assert client.put(url, headers=headers(), json=request).json() == wire
        assert client.put(url, headers=headers(), json=request).json() == wire
        assert client.get(url, headers=headers()).json() == wire
        assert client.get(url, headers=headers("synthetic-tenant-b")).status_code == 404
        member_url = url + "/membership/" + membership["membership_revision"]
        body = {
            k: membership[k]
            for k in [
                "policy_version",
                "source_cut_id",
                "decisions",
                "correlation_id",
                "supersedes_membership_revision",
                "affected_from",
                "affected_to",
            ]
        }
        first = client.put(member_url, headers=headers(), json=body)
        assert first.status_code == 200
        assert client.put(member_url, headers=headers(), json=body).json() == first.json()
        assert first.json()["decisions"] == membership["decisions"]
    page = repository.list_publications(tenant_id=registry["tenant_id"], after_sequence=0, limit=10)
    assert len(page.items) == page.high_watermark == 2
    assert all(p.completeness == "UNVERIFIED" and p.product_version == "v1" for p in page.items)
    assert (
        repository.list_definitions(tenant_id=registry["tenant_id"], limit=10, offset=0).count == 2
    )
    changed = dict(pack["external_versions"]["original"]["definition"], display_name="New content")
    changed = rebind_definition(changed, refresh_approval=True)
    assert (
        client.put(
            definition_url(changed), headers=headers(), json=definition_request(changed)
        ).status_code
        == 409
    )


@pytest.mark.parametrize("case", ["duplicate", "tenant", "caller_trust", "implicit_v2"])
def test_v2_scope_and_raw_body_refusals_do_not_persist(client_and_repository, case: str) -> None:
    client, repository, service = client_and_repository
    pack = frozen_authority_pack()
    wire = pack["external_versions"]["original"]["definition"]
    service = DpmCompositeMembershipApplicationService(
        repository=repository,
        provider_trust=SyntheticFixtureProviderTrust(
            pack["external_versions"]["original"]["supporting_payloads"]["registry"]
        ),
    )
    app.dependency_overrides[get_composite_membership_application_service] = lambda: service
    body = definition_request(wire)
    admitted_headers = headers()
    if case == "duplicate":
        raw = '{"product_version":"v2",' + json.dumps(body)[1:]
    else:
        if case == "tenant":
            admitted_headers = headers("synthetic-tenant-b")
        elif case == "caller_trust":
            body["trusted_provider"] = True
        else:
            body.pop("product_version")
        raw = json.dumps(body)
    response = client.put(
        definition_url(wire),
        content=raw,
        headers={**admitted_headers, "Content-Type": "application/json"},
    )
    assert response.status_code == 422
    assert repository.list_definitions(tenant_id=wire["tenant_id"], limit=10, offset=0).count == 0
