"""Pinned interval reads preserve decision evidence without inferring eligibility."""

from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from src.api.dependencies import get_composite_membership_application_service
from src.api.main import app
from src.api.services.composite_membership_application import (
    DpmCompositeMembershipApplicationService,
)
from src.infrastructure.composites.in_memory import InMemoryDpmCompositeRepository
from tests.composite_correction_helpers import correction_body, definition_body, original_body


@pytest.fixture
def range_api():
    repository = InMemoryDpmCompositeRepository()
    app.dependency_overrides[get_composite_membership_application_service] = lambda: (
        DpmCompositeMembershipApplicationService(repository=repository)
    )
    headers = {
        "X-Tenant-Id": "range-tenant",
        "X-Actor-Id": "range-maker",
        "X-Role": "DPM_COMPOSITE_ADMIN",
    }
    base = "/api/v1/rebalance/composites/RANGE_COMPOSITE/definitions/v1"
    try:
        with TestClient(app) as client:
            assert client.put(base, headers=headers, json=definition_body()).status_code == 200
            body = deepcopy(original_body())
            body["decisions"].append(
                body["decisions"][0]
                | {
                    "portfolio_id": "D",
                    "effective_from": "2026-03-01",
                    "status": "PENDING_REVIEW",
                    "reason_code": "SYNTHETIC_REVIEW",
                }
            )
            gap_decisions = [
                body["decisions"][0]
                | {"portfolio_id": "G", "effective_from": first, "effective_to": last}
                for first, last in (("2026-01-01", "2026-01-10"), ("2026-01-20", "2026-01-25"))
            ]
            body["decisions"].extend(gap_decisions)
            original = client.put(f"{base}/membership/m1", headers=headers, json=body)
            assert original.status_code == 200
            corrected_body = correction_body()
            corrected_body["decisions"].extend(body["decisions"][4:])
            corrected = client.put(f"{base}/membership/m2", headers=headers, json=corrected_body)
            assert corrected.status_code == 200
            yield client, base, headers, original.json(), corrected.json()
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize(
    "first,last,expected",
    [
        ("2026-01-15", "2026-01-15", [("A", "INCLUDED"), ("B", "INCLUDED"), ("C", "INCLUDED")]),
        ("2026-01-16", "2026-01-31", [("A", "INCLUDED"), ("B", "INCLUDED"), ("G", "INCLUDED")]),
        ("2026-01-31", "2026-02-01", [("A", "INCLUDED"), ("B", "INCLUDED"), ("B", "EXCLUDED")]),
        (
            "2026-03-01",
            "9999-12-31",
            [("A", "INCLUDED"), ("B", "EXCLUDED"), ("D", "PENDING_REVIEW")],
        ),
        ("2025-12-01", "2025-12-31", []),
    ],
)
def test_range_selects_inclusive_intersections_and_preserves_original_evidence(
    range_api, first, last, expected
):
    client, base, headers, original, _ = range_api
    response = client.get(
        f"{base}/membership/m1/range",
        headers=headers,
        params={"effective_from": first, "effective_to": last},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["tenant_id"] == headers["X-Tenant-Id"]
    assert result["completeness"] == "UNVERIFIED"
    assert [(item["portfolio_id"], item["status"]) for item in result["decisions"]] == expected
    assert result["count"] == len(expected)
    assert result["membership_content_hash"] == original["content_hash"]
    assert result["source_cut_id"] == original["source_cut_id"]
    assert result["membership_revision"] == "m1"
    assert result["effective_from"] == first and result["effective_to"] == last
    assert all(item in original["decisions"] for item in result["decisions"])
    assert client.get(f"{base}/membership/m1", headers=headers).json() == original


def test_range_preserves_gaps_and_original_intervals_at_both_edges(range_api):
    client, base, headers, original, _ = range_api
    url = f"{base}/membership/m1/range"
    gap = client.get(
        url, headers=headers, params={"effective_from": "2026-01-11", "effective_to": "2026-01-19"}
    )
    assert gap.status_code == 200
    assert "G" not in [item["portfolio_id"] for item in gap.json()["decisions"]]
    spanning = client.get(
        url, headers=headers, params={"effective_from": "2026-01-10", "effective_to": "2026-01-20"}
    )
    assert spanning.status_code == 200
    decisions = spanning.json()["decisions"]
    assert [item for item in decisions if item["portfolio_id"] == "G"] == [
        item for item in original["decisions"] if item["portfolio_id"] == "G"
    ]
    assert spanning.json()["count"] == 5
    assert len({item["portfolio_id"] for item in decisions}) == 4


def test_range_preserves_corrected_and_original_pins_and_single_date_equivalence(range_api):
    client, base, headers, original, corrected = range_api
    for revision, wire, expected_status in [
        ("m1", original, "INCLUDED"),
        ("m2", corrected, "EXCLUDED"),
    ]:
        url = f"{base}/membership/{revision}"
        ranged = client.get(
            f"{url}/range",
            headers=headers,
            params={"effective_from": "2026-01-05", "effective_to": "2026-01-05"},
        )
        assert ranged.status_code == 200
        point = client.get(f"{url}/as-of", headers=headers, params={"as_of_date": "2026-01-05"})
        assert point.status_code == 200
        assert ranged.json()["decisions"] == point.json()["decisions"]
        assert ranged.json()["decisions"][0]["status"] == expected_status
        assert ranged.json()["membership_content_hash"] == wire["content_hash"]
        assert client.get(url, headers=headers).json() == wire
    assert (
        client.get("/api/v1/rebalance/composites/publications", headers=headers).json()[
            "high_watermark"
        ]
        == 2
    )


@pytest.mark.parametrize(
    "first,last",
    [
        ("2026-02-01", "2026-01-31"),
        ("2026-02-29", "2026-03-01"),
        ("2026-01-01", "2026-99-99"),
        ("20260101", "2026-01-31"),
    ],
)
def test_range_refuses_invalid_calendar_and_reversed_windows(range_api, first, last):
    client, base, headers, _, _ = range_api
    assert (
        client.get(
            f"{base}/membership/m1/range",
            headers=headers,
            params={"effective_from": first, "effective_to": last},
        ).status_code
        == 422
    )


def test_range_requires_both_dates_and_tenant_scoped_pinned_revision(range_api):
    client, base, headers, _, _ = range_api
    params = {"effective_from": "2026-01-01", "effective_to": "2026-01-31"}
    url = f"{base}/membership/m1/range"
    assert client.get(url, params=params).status_code == 403
    assert (
        client.get(url, headers=headers | {"X-Tenant-Id": "foreign"}, params=params).status_code
        == 404
    )
    assert (
        client.get(f"{base}/membership/missing/range", headers=headers, params=params).status_code
        == 404
    )
    for missing in params:
        assert (
            client.get(
                url,
                headers=headers,
                params={key: value for key, value in params.items() if key != missing},
            ).status_code
            == 422
        )
