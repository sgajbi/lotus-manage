"""Registered pinned range reads retain PostgreSQL history across application restart."""

from uuid import uuid4

from fastapi.testclient import TestClient

from src.api.dependencies import get_composite_membership_application_service
from src.api.main import app
from src.api.services.composite_membership_application import (
    DpmCompositeMembershipApplicationService,
)
from src.infrastructure.composites.postgres import PostgresDpmCompositeRepository
from tests.composite_correction_helpers import (
    correction_body,
    decision,
    definition_body,
    original_body,
)
from tests.integration.dpm.postgres_prerequisite import postgres_dsn_or_skip


def test_registered_range_retains_original_and_corrected_evidence_after_restart() -> None:
    dsn = postgres_dsn_or_skip("composite membership range durability proof")
    tenant = f"range-{uuid4().hex}"
    base = "/api/v1/rebalance/composites/RANGE_COMPOSITE/definitions/v1"
    headers = {"X-Tenant-Id": tenant, "X-Actor-Id": "range-maker", "X-Role": "DPM_COMPOSITE_ADMIN"}
    retained = {}
    retained_publications = None
    try:
        for restarting in (False, True):
            repository = PostgresDpmCompositeRepository(dsn=dsn)
            app.dependency_overrides[get_composite_membership_application_service] = lambda: (
                DpmCompositeMembershipApplicationService(repository=repository)
            )
            with TestClient(app) as client:
                if not restarting:
                    assert (
                        client.put(base, headers=headers, json=definition_body()).status_code == 200
                    )
                    for revision, body in (("m1", original_body()), ("m2", correction_body())):
                        body["decisions"].extend(
                            [
                                decision("G", first="2026-01-01", last="2026-01-10"),
                                decision("G", first="2026-01-20", last="2026-01-25"),
                            ]
                        )
                        response = client.put(
                            f"{base}/membership/{revision}", headers=headers, json=body
                        )
                        assert response.status_code == 200
                        retained[revision] = response.json()
                    retained_publications = client.get(
                        "/api/v1/rebalance/composites/publications", headers=headers
                    ).json()
                    assert len(retained_publications["items"]) == 2
                for revision, expected_status in (("m1", "INCLUDED"), ("m2", "EXCLUDED")):
                    url = f"{base}/membership/{revision}"
                    response = client.get(
                        f"{url}/range",
                        headers=headers,
                        params={"effective_from": "2026-01-05", "effective_to": "2026-01-05"},
                    )
                    assert response.status_code == 200
                    result = response.json()
                    assert result["tenant_id"] == tenant
                    assert result["completeness"] == "UNVERIFIED"
                    assert result["count"] == 4
                    assert result["decisions"][0]["status"] == expected_status
                    assert result["membership_content_hash"] == retained[revision]["content_hash"]
                    assert result["source_cut_id"] == retained[revision]["source_cut_id"]
                    collected = []
                    for offset in (0, 3, 6):
                        paged = client.get(
                            f"{url}/range",
                            headers=headers,
                            params={
                                "effective_from": "2026-01-05",
                                "effective_to": "2026-01-05",
                                "limit": 3,
                                "offset": offset,
                            },
                        )
                        assert paged.status_code == 200
                        page = paged.json()
                        assert (
                            page["count"] == 4 and page["limit"] == 3 and page["offset"] == offset
                        )
                        assert page["membership_content_hash"] == result["membership_content_hash"]
                        assert page["source_cut_id"] == result["source_cut_id"]
                        assert len(page["decisions"]) <= 3
                        collected.extend(page["decisions"])
                    assert page["decisions"] == []
                    assert collected == result["decisions"]
                    gap = client.get(
                        f"{url}/range",
                        headers=headers,
                        params={
                            "effective_from": "2026-01-16",
                            "effective_to": "2026-01-19",
                            "limit": 1,
                        },
                    )
                    assert gap.status_code == 200 and gap.json()["count"] == 2
                    gap_end = client.get(
                        f"{url}/range",
                        headers=headers,
                        params={
                            "effective_from": "2026-01-16",
                            "effective_to": "2026-01-19",
                            "limit": 1,
                            "offset": 1,
                        },
                    )
                    assert gap_end.status_code == 200 and gap_end.json()["count"] == 2
                    assert [
                        item["portfolio_id"]
                        for item in gap.json()["decisions"] + gap_end.json()["decisions"]
                    ] == ["A", "B"]
                    assert all(
                        item in retained[revision]["decisions"] for item in result["decisions"]
                    )
                    assert client.get(url, headers=headers).json() == retained[revision]
                    assert (
                        client.get(
                            f"{url}/range",
                            headers=headers | {"X-Tenant-Id": f"{tenant}-foreign"},
                            params={"effective_from": "2026-01-01", "effective_to": "2026-01-31"},
                        ).status_code
                        == 404
                    )
                empty = client.get(
                    f"{base}/membership/m2/range",
                    headers=headers,
                    params={"effective_from": "2025-12-01", "effective_to": "2025-12-31"},
                )
                assert empty.status_code == 200
                assert empty.json()["decisions"] == [] and empty.json()["count"] == 0
                publication = client.get(
                    "/api/v1/rebalance/composites/publications", headers=headers
                )
                assert publication.status_code == 200
                assert publication.json() == retained_publications
    finally:
        app.dependency_overrides.clear()
