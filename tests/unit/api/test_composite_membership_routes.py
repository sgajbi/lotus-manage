from __future__ import annotations

from fastapi.testclient import TestClient

from src.api.dependencies import get_composite_membership_application_service
from src.api.main import app
from src.api.services.composite_membership_application import (
    DpmCompositeMembershipApplicationService,
)
from src.infrastructure.composites.in_memory import InMemoryDpmCompositeRepository


def _headers(*, role: str = "DPM_COMPOSITE_ADMIN", tenant: str = "tenant-sg") -> dict[str, str]:
    return {"X-Tenant-Id": tenant, "X-Actor-Id": "pm-ops", "X-Role": role}


def _definition_payload() -> dict[str, object]:
    return {
        "display_name": "Private Banking Global Balanced Composite",
        "strategy_code": "GLOBAL_BALANCED",
        "reporting_currency": "USD",
        "inception_date": "2024-01-01",
        "eligibility_policy_version": "composite-eligibility.v1",
        "source_authority": {"policy_version": "composite-source-authority.v1"},
        "correlation_id": "corr-definition-001",
    }


def _revision_payload() -> dict[str, object]:
    return {
        "policy_version": "composite-eligibility.v1",
        "source_cut_id": "core-cut-2026-10-01",
        "correlation_id": "corr-membership-001",
        "decisions": [
            {
                "portfolio_id": "PB_SG_GLOBAL_BAL_001",
                "effective_from": "2026-01-01",
                "source_snapshot_id": "manage-membership-source-2026-01-01",
            },
            {
                "portfolio_id": "PB_SG_GLOBAL_BAL_002",
                "effective_from": "2026-02-01",
                "effective_to": "2026-02-28",
                "status": "EXCLUDED",
                "reason_code": "MINIMUM_ASSET_NOT_MET",
                "source_snapshot_id": "manage-membership-source-2026-02-01",
            },
        ],
    }


def test_composite_membership_routes_enforce_identity_and_preserve_pinned_history() -> None:
    repository = InMemoryDpmCompositeRepository()
    app.dependency_overrides[get_composite_membership_application_service] = lambda: (
        DpmCompositeMembershipApplicationService(repository=repository)
    )
    base = "/api/v1/rebalance/composites/PB_GLOBAL_BALANCED_USD/definitions/2026.10"
    try:
        with TestClient(app) as client:
            assert client.put(base, json=_definition_payload()).status_code == 403
            assert (
                client.put(
                    base, headers=_headers(role="DPM_VIEWER"), json=_definition_payload()
                ).status_code
                == 403
            )
            saved_definition = client.put(base, headers=_headers(), json=_definition_payload())
            assert saved_definition.status_code == 200
            assert saved_definition.json()["created_by"] == "pm-ops"
            assert client.get(base, headers=_headers()).status_code == 200
            definitions = client.get("/api/v1/rebalance/composites/definitions", headers=_headers())
            assert definitions.status_code == 200
            assert definitions.json()["count"] == 1
            assert client.get(base, headers=_headers(tenant="other-tenant")).status_code == 404

            revision_url = f"{base}/membership/2026.10.1"
            saved_revision = client.put(revision_url, headers=_headers(), json=_revision_payload())
            assert saved_revision.status_code == 200
            assert saved_revision.json()["decided_by"] == "pm-ops"
            as_of = client.get(f"{revision_url}/as-of?as_of_date=2026-02-15", headers=_headers())
            assert as_of.status_code == 200
            assert [item["portfolio_id"] for item in as_of.json()["decisions"]] == [
                "PB_SG_GLOBAL_BAL_001",
                "PB_SG_GLOBAL_BAL_002",
            ]
            assert as_of.json()["content_hash"] == saved_revision.json()["content_hash"]

            correction = _revision_payload() | {
                "correlation_id": "corr-membership-002",
                "supersedes_membership_revision": "2026.10.1",
                "affected_from": "2026-02-01",
                "affected_to": "2026-02-28",
            }
            corrected_url = f"{base}/membership/2026.10.2"
            assert client.put(corrected_url, headers=_headers(), json=correction).status_code == 200
            history = client.get(f"{base}/membership?limit=10&offset=0", headers=_headers())
            assert history.status_code == 200
            assert [item["membership_revision"] for item in history.json()["items"]] == [
                "2026.10.2",
                "2026.10.1",
            ]
    finally:
        app.dependency_overrides.clear()


def test_composite_membership_route_rejects_immutable_conflict_and_invalid_as_of() -> None:
    repository = InMemoryDpmCompositeRepository()
    app.dependency_overrides[get_composite_membership_application_service] = lambda: (
        DpmCompositeMembershipApplicationService(repository=repository)
    )
    base = "/api/v1/rebalance/composites/PB_GLOBAL_BALANCED_USD/definitions/2026.10"
    try:
        with TestClient(app) as client:
            assert (
                client.put(base, headers=_headers(), json=_definition_payload()).status_code == 200
            )
            conflict = client.put(
                base,
                headers=_headers(),
                json=_definition_payload() | {"display_name": "Conflicting composite"},
            )
            assert conflict.status_code == 409
            assert conflict.json()["detail"]["code"] == "COMPOSITE_DEFINITION_IMMUTABLE_CONFLICT"
            assert client.get(f"{base}/membership/missing", headers=_headers()).status_code == 404
            revision_url = f"{base}/membership/2026.10.1"
            assert (
                client.put(revision_url, headers=_headers(), json=_revision_payload()).status_code
                == 200
            )
            membership_conflict = client.put(
                revision_url,
                headers=_headers(),
                json=_revision_payload() | {"policy_version": "composite-eligibility.v2"},
            )
            assert membership_conflict.status_code == 409
            assert (
                membership_conflict.json()["detail"]["code"]
                == "COMPOSITE_MEMBERSHIP_REVISION_IMMUTABLE_CONFLICT"
            )
            invalid_date = client.get(
                f"{revision_url}/as-of?as_of_date=2026-99-99", headers=_headers()
            )
            assert invalid_date.status_code == 422
    finally:
        app.dependency_overrides.clear()
