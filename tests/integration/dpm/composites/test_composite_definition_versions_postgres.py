"""Real JSONB and fresh-process producer proof; no actual consumer/trust certification."""

from __future__ import annotations

import multiprocessing
from datetime import datetime, timezone

import psycopg
import pytest
from fastapi.testclient import TestClient

from src.api.dependencies import get_composite_membership_application_service
from src.api.main import app
from src.api.services.composite_membership_application import (
    DpmCompositeMembershipApplicationService,
)
from src.core.composite_definition_versions import decode_composite_definition
from src.core.composite_membership import DpmCompositeMembershipRevision
from src.infrastructure.composites.postgres import PostgresDpmCompositeRepository
from tests.composite_authority_helpers import (
    SyntheticFixtureProviderTrust,
    definition_request,
    frozen_authority_pack,
    independent_digest,
    institutional_reference_wire,
    rebind_definition,
)
from tests.integration.dpm.network_runtime import disposable_database


def _headers(tenant: str = "synthetic-tenant-a") -> dict[str, str]:
    return {"X-Tenant-Id": tenant, "X-Actor-Id": "synthetic-maker", "X-Role": "DPM_COMPOSITE_ADMIN"}


def _url(wire: dict) -> str:
    return f"/api/v1/rebalance/composites/{wire['composite_id']}/definitions/{wire['definition_version']}"


def _membership_request(wire: dict) -> dict:
    return {
        key: wire[key]
        for key in (
            "policy_version",
            "source_cut_id",
            "decisions",
            "correlation_id",
            "supersedes_membership_revision",
            "affected_from",
            "affected_to",
        )
    }


def _read_in_fresh_process(dsn: str, tenant: str, pipe) -> None:
    """Spawned interpreter reconstructs only retained database content, without overrides."""
    try:
        assert not app.dependency_overrides
        repository = PostgresDpmCompositeRepository(dsn=dsn)
        definitions = repository.list_definitions(tenant_id=tenant, limit=10, offset=0)
        publications = repository.list_publications(tenant_id=tenant, after_sequence=0, limit=10)
        memberships = [
            repository.get_membership_revision(
                tenant_id=tenant,
                composite_id=p.composite_id,
                definition_version=p.definition_version,
                membership_revision=p.membership_revision,
            )
            for p in publications.items
        ]
        assert all(m is not None for m in memberships)
        pipe.send(
            {
                "definitions": [d.model_dump(mode="json") for d in definitions.items],
                "count": definitions.count,
                "publications": [p.model_dump(mode="json") for p in publications.items],
                "high_watermark": publications.high_watermark,
                "memberships": [m.model_dump(mode="json") for m in memberships if m is not None],
            }
        )
    finally:
        pipe.close()


def _fresh_snapshot(dsn: str, tenant: str) -> dict:
    context = multiprocessing.get_context("spawn")
    parent, child = context.Pipe(duplex=False)
    reader = context.Process(target=_read_in_fresh_process, args=(dsn, tenant, child))
    reader.start()
    child.close()
    try:
        assert parent.poll(30), "Fresh PostgreSQL reader did not return its retained snapshot"
        snapshot = parent.recv()
        reader.join(15)
        assert reader.exitcode == 0
        return snapshot
    finally:
        parent.close()
        if reader.is_alive():
            reader.terminate()
            reader.join(15)
        assert not reader.is_alive()


def test_registered_v1_v2_generations_publication_and_fresh_reader_preserve_originals() -> None:
    pack = frozen_authority_pack()
    v1 = pack["v1_compatibility"]["raw_definition"]
    originals = [v1] + [item["definition"] for item in pack["external_versions"].values()]
    with disposable_database() as dsn:
        repository = PostgresDpmCompositeRepository(dsn=dsn)
        repository.save_definition(definition=decode_composite_definition(v1))
        registry = pack["external_versions"]["original"]["supporting_payloads"]["registry"]
        service = DpmCompositeMembershipApplicationService(
            repository=repository, provider_trust=SyntheticFixtureProviderTrust(registry)
        )
        app.dependency_overrides[get_composite_membership_application_service] = lambda: service
        try:
            with TestClient(app) as client:
                for item in pack["external_versions"].values():
                    wire, membership = item["definition"], item["membership"]
                    url = _url(wire)
                    for _ in range(2):
                        response = client.put(
                            url, headers=_headers(), json=definition_request(wire)
                        )
                        assert response.status_code == 200
                        assert response.json() == wire
                    assert client.get(url, headers=_headers()).json() == wire
                    assert (
                        client.get(url, headers=_headers("synthetic-tenant-b")).status_code == 404
                    )
                    # Seed the exact immutable shared generation, then prove registered replay/read.
                    repository.save_membership_revision(
                        revision=DpmCompositeMembershipRevision.model_validate(membership)
                    )
                    member_url = url + "/membership/" + membership["membership_revision"]
                    member_request = _membership_request(membership)
                    for _ in range(2):
                        response = client.put(member_url, headers=_headers(), json=member_request)
                        assert response.status_code == 200
                        assert response.json() == membership
                    assert client.get(member_url, headers=_headers()).json() == membership
                    changed = rebind_definition(
                        dict(wire, display_name="Unapproved replacement"), refresh_approval=True
                    )
                    assert (
                        client.put(
                            url, headers=_headers(), json=definition_request(changed)
                        ).status_code
                        == 409
                    )
                first = originals[1]
                mutated = decode_composite_definition(first)
                mutated.source_authority.payload.selections[0].member_ids.pop()
                with pytest.raises(ValueError):
                    repository.save_definition(definition=mutated)
                with psycopg.connect(dsn) as connection:
                    for wire in originals:
                        row = connection.execute(
                            "SELECT payload_json FROM dpm_composite_definitions WHERE tenant_id=%s AND composite_id=%s AND definition_version=%s",
                            (wire["tenant_id"], wire["composite_id"], wire["definition_version"]),
                        ).fetchone()
                        assert row is not None and row[0] == wire
                tenant = registry["tenant_id"]
                publications = repository.list_publications(
                    tenant_id=tenant, after_sequence=0, limit=10
                )
                assert len(publications.items) == 2
                # PostgreSQL identity allocation can leave gaps after ON CONFLICT replay.
                assert publications.high_watermark == max(p.sequence for p in publications.items)
                assert all(
                    p.completeness == "UNVERIFIED" and p.product_version == "v1"
                    for p in publications.items
                )
                publication_url = "/api/v1/rebalance/composites/publications"
                published = client.get(publication_url, headers=_headers())
                assert published.status_code == 200
                assert published.json() == publications.model_dump(mode="json")
                second = client.get(
                    publication_url,
                    headers=_headers(),
                    params={"after_sequence": publications.items[0].sequence, "limit": 1},
                )
                assert second.status_code == 200
                assert second.json()["items"] == [publications.items[1].model_dump(mode="json")]
                for publication in publications.items:
                    item_url = publication_url + f"/{publication.sequence}"
                    assert client.get(
                        item_url, headers=_headers()
                    ).json() == publication.model_dump(mode="json")
                    assert (
                        client.get(item_url, headers=_headers("synthetic-tenant-b")).status_code
                        == 404
                    )
                assert (
                    repository.list_publications(
                        tenant_id="synthetic-tenant-b", after_sequence=0, limit=10
                    ).items
                    == []
                )
                snapshot = _fresh_snapshot(dsn, tenant)
                # The v1 compatibility fixture may have a different tenant; independently read it too.
                expected = [w for w in originals if w["tenant_id"] == tenant]
                assert snapshot["count"] == len(expected)
                assert {d["definition_version"]: d for d in snapshot["definitions"]} == {
                    d["definition_version"]: d for d in expected
                }
                assert snapshot["publications"] == [
                    p.model_dump(mode="json") for p in publications.items
                ]
                assert snapshot["high_watermark"] == publications.high_watermark
                legacy = _fresh_snapshot(dsn, v1["tenant_id"])
                assert v1 in legacy["definitions"]
                assert _fresh_snapshot(dsn, "synthetic-tenant-b")["definitions"] == []
        finally:
            app.dependency_overrides.pop(get_composite_membership_application_service, None)


def test_registered_membership_first_create_publishes_real_server_generations() -> None:
    pack = frozen_authority_pack()
    registry = pack["external_versions"]["original"]["supporting_payloads"]["registry"]
    with disposable_database() as dsn:
        repository = PostgresDpmCompositeRepository(dsn=dsn)
        service = DpmCompositeMembershipApplicationService(
            repository=repository, provider_trust=SyntheticFixtureProviderTrust(registry)
        )
        app.dependency_overrides[get_composite_membership_application_service] = lambda: service
        created_memberships = {}
        try:
            with TestClient(app) as client:
                for item in pack["external_versions"].values():
                    wire, declared_membership = item["definition"], item["membership"]
                    url = _url(wire)
                    response = client.put(url, headers=_headers(), json=definition_request(wire))
                    assert response.status_code == 200 and response.json() == wire
                    member_url = url + "/membership/" + declared_membership["membership_revision"]
                    body = _membership_request(declared_membership)
                    started = datetime.now(timezone.utc)
                    response = client.put(member_url, headers=_headers(), json=body)
                    assert response.status_code == 200
                    actual = response.json()
                    assert actual["decided_by"] == _headers()["X-Actor-Id"]
                    assert (
                        started
                        <= datetime.fromisoformat(actual["decided_at"])
                        <= datetime.now(timezone.utc)
                    )
                    for key, value in body.items():
                        assert actual[key] == value
                    assert actual["definition_version"] == wire["definition_version"]
                    assert actual["content_hash"] == independent_digest(
                        {k: v for k, v in actual.items() if k != "content_hash"}
                    )
                    assert client.put(member_url, headers=_headers(), json=body).json() == actual
                    assert client.get(member_url, headers=_headers()).json() == actual
                    created_memberships[wire["definition_version"]] = actual
                published = client.get(
                    "/api/v1/rebalance/composites/publications", headers=_headers()
                )
                assert published.status_code == 200
                assert len(published.json()["items"]) == 2
                for publication in published.json()["items"]:
                    actual = created_memberships[publication["definition_version"]]
                    assert publication["membership_content_hash"] == actual["content_hash"]
                    assert publication["source_cut_id"] == actual["source_cut_id"]
                    assert publication["membership_revision"] == actual["membership_revision"]
                    assert publication["completeness"] == "UNVERIFIED"
                snapshot = _fresh_snapshot(dsn, registry["tenant_id"])
                assert {
                    m["definition_version"]: m for m in snapshot["memberships"]
                } == created_memberships
                assert snapshot["publications"] == published.json()["items"]
                with psycopg.connect(dsn) as connection:
                    assert connection.execute(
                        "SELECT COUNT(*) FROM dpm_composite_membership_revisions"
                    ).fetchone() == (2,)
                    assert connection.execute(
                        "SELECT COUNT(*) FROM dpm_composite_membership_publications"
                    ).fetchone() == (2,)
        finally:
            app.dependency_overrides.pop(get_composite_membership_application_service, None)


@pytest.mark.parametrize("institutional", [False, True])
def test_postgres_registration_and_institutional_refusal_leave_no_rows(institutional: bool) -> None:
    pack = frozen_authority_pack()
    item = pack["external_versions"]["original"]
    wire = institutional_reference_wire(item["definition"]) if institutional else item["definition"]
    with disposable_database() as dsn:
        repository = PostgresDpmCompositeRepository(dsn=dsn)
        service = (
            DpmCompositeMembershipApplicationService(
                repository=repository,
                provider_trust=SyntheticFixtureProviderTrust(
                    item["supporting_payloads"]["registry"]
                ),
            )
            if institutional
            else DpmCompositeMembershipApplicationService(repository=repository)
        )
        app.dependency_overrides[get_composite_membership_application_service] = lambda: service
        try:
            with TestClient(app) as client:
                response = client.put(_url(wire), headers=_headers(), json=definition_request(wire))
                assert response.status_code == 503
                code = (
                    "COMPOSITE_AUTHORITY_ATTESTATION_VERIFIER_UNAVAILABLE"
                    if institutional
                    else "COMPOSITE_PROVIDER_TRUST_UNAVAILABLE"
                )
                assert response.json()["detail"]["code"] == code
            with psycopg.connect(dsn) as connection:
                assert connection.execute(
                    "SELECT COUNT(*) FROM dpm_composite_definitions"
                ).fetchone() == (0,)
                assert connection.execute(
                    "SELECT COUNT(*) FROM dpm_composite_membership_publications"
                ).fetchone() == (0,)
        finally:
            app.dependency_overrides.pop(get_composite_membership_application_service, None)
