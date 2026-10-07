"""Registered resolver uses admitted scope and exact retained publication, not latest."""

import pytest
from fastapi.testclient import TestClient

from src.api.dependencies import get_composite_subject_service
from src.api.main import app
from src.api.services.composite_subject_application import CompositeSubjectApplicationService
from tests.composite_staged_eligibility_helpers import HEADERS
from tests.unit.dpm.composites.test_composite_staged_custody import retained_graph

RESOLVE = "/api/v1/rebalance/composites/synthetic-composite/definitions/synthetic-definition/eligibility-evidence/resolve"


@pytest.fixture
def resolver_api():
    repository, subject, controls, finalization = retained_graph()
    binding = finalization.definition.source_authority.payload.eligibility_evaluation_binding
    service = CompositeSubjectApplicationService(repository=repository)
    prior = app.dependency_overrides.copy()
    app.dependency_overrides[get_composite_subject_service] = lambda: service
    try:
        with TestClient(app) as client:
            yield client, repository, finalization, binding.model_dump(mode="json")
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(prior)


def test_registered_resolver_returns_exact_finalized_graph_and_preserves_nonproof_labels(
    resolver_api,
):
    client, repository, finalization, binding = resolver_api
    receipt = repository.finalize_eligibility_subject(finalization=finalization)
    response = client.post(RESOLVE, json=binding, headers=HEADERS)
    assert response.status_code == 200, response.text
    assert response.json() == receipt.model_dump(mode="json")
    assert response.json()["completeness"] == "UNVERIFIED"
    assert (
        response.json()["finalization"]["evaluation_approval"]["publication_posture"]
        == "NOT_PUBLISHED"
    )
    assert response.json()["finalization"]["subject"]["subject_revision"] == "synthetic-subject"
    assert client.post(RESOLVE, json=binding, headers=HEADERS).json() == response.json()


@pytest.mark.parametrize(
    "change,status,code",
    [
        ("revision", 404, "COMPOSITE_SUBJECT_FINALIZATION_NOT_FOUND"),
        ("digest", 422, "COMPOSITE_SUBJECT_ELIGIBILITY_BINDING_MISMATCH"),
        ("tenant", 404, "COMPOSITE_SUBJECT_FINALIZATION_NOT_FOUND"),
        ("definition", 404, "COMPOSITE_SUBJECT_FINALIZATION_NOT_FOUND"),
        ("product_name", 422, "COMPOSITE_SUBJECT_ELIGIBILITY_BINDING_MISMATCH"),
        ("publication", 409, "COMPOSITE_SUBJECT_RECEIPT_INTEGRITY_CONFLICT"),
        ("staged_only", 404, "COMPOSITE_SUBJECT_FINALIZATION_NOT_FOUND"),
    ],
)
def test_registered_resolver_refuses_wrong_binding_scope_or_unpublished_graph(
    resolver_api, change, status, code
):
    client, repository, finalization, binding = resolver_api
    if change != "staged_only":
        repository.finalize_eligibility_subject(finalization=finalization)
    headers = dict(HEADERS)
    url = RESOLVE
    if change == "tenant":
        headers["X-Tenant-Id"] = "foreign-tenant"
    elif change == "definition":
        url = url.replace("synthetic-definition", "other-definition")
    elif change == "publication":
        repository._publications.clear()
    elif change == "digest":
        binding[change] = "sha256:" + "0" * 64
    elif change != "staged_only":
        binding[change] = "other"
    response = client.post(url, json=binding, headers=headers)
    assert response.status_code == status, response.text
    assert response.json()["detail"]["code"] == code


def test_registered_resolver_requires_trusted_identity_and_rejects_body_scope_override(
    resolver_api,
):
    client, _, _, binding = resolver_api
    assert client.post(RESOLVE, json=binding).status_code in (401, 403)
    binding["tenant_id"] = "foreign-tenant"
    assert client.post(RESOLVE, json=binding, headers=HEADERS).status_code == 422


def test_registered_resolver_rejects_unsupported_binding_version_at_schema_boundary(resolver_api):
    client, _, _, binding = resolver_api
    binding["product_version"] = "v2"
    response = client.post(RESOLVE, json=binding, headers=HEADERS)
    assert response.status_code == 422
    assert any(error["loc"] == ["body", "product_version"] for error in response.json()["detail"])
