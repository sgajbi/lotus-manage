"""Real PostgreSQL refusal and authorized-replay proof for issue #756."""

from __future__ import annotations

import json
import uuid

from fastapi.testclient import TestClient
import pytest

from src.api.dependencies import get_composite_membership_application_service
from src.api.main import app
from src.api.services.composite_membership_application import (
    DpmCompositeMembershipApplicationService,
)
from src.infrastructure.composites.postgres import PostgresDpmCompositeRepository
from tests.integration.dpm.postgres_prerequisite import postgres_dsn_or_skip

_PROOF = "enterprise refusal no-mutation and authorized replay PostgreSQL proof"


def test_refusal_does_not_mutate_postgres_and_authorized_replay_remains_idempotent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    suffix = uuid.uuid4().hex[:12]
    tenant_id = f"tenant-refusal-{suffix}"
    composite_id = f"PB_GLOBAL_BALANCED_{suffix}"
    path = f"/api/v1/rebalance/composites/{composite_id}/definitions/2026.10"
    correlation_id = f"corr-refusal-{suffix}"
    repository = PostgresDpmCompositeRepository(dsn=postgres_dsn_or_skip(_PROOF))
    app.dependency_overrides[get_composite_membership_application_service] = lambda: (
        DpmCompositeMembershipApplicationService(repository=repository)
    )
    monkeypatch.setenv("ENTERPRISE_ENFORCE_AUTHZ", "true")
    monkeypatch.setenv("ENTERPRISE_POLICY_VERSION", "test-policy-v1")
    monkeypatch.setenv(
        "ENTERPRISE_CAPABILITY_RULES_JSON",
        json.dumps({"PUT /api/v1/rebalance/composites": "composites:write"}),
    )
    headers = {
        "X-Tenant-Id": tenant_id,
        "X-Actor-Id": "pm-ops",
        "X-Role": "DPM_COMPOSITE_ADMIN",
        "X-Service-Identity": "lotus-gateway",
        "X-Capabilities": "composites:write",
        "X-Correlation-Id": correlation_id,
    }
    payload = {
        "display_name": "Private Banking Global Balanced Composite",
        "strategy_code": "GLOBAL_BALANCED",
        "reporting_currency": "USD",
        "inception_date": "2024-01-01",
        "eligibility_policy_version": "composite-eligibility.v1",
        "source_authority": {"policy_version": "composite-source-authority.v1"},
        "correlation_id": correlation_id,
    }

    try:
        with TestClient(app) as client:
            refusal_headers = dict(headers)
            refusal_headers.pop("X-Role")
            refused = client.put(path, headers=refusal_headers, json=payload)

            assert refused.status_code == 403
            assert refused.headers["X-Correlation-Id"] == correlation_id
            assert refused.headers["X-Enterprise-Policy-Version"] == "test-policy-v1"
            assert refused.json()["correlationId"] == correlation_id
            assert repository.list_definitions(tenant_id=tenant_id, limit=10, offset=0).count == 0

            accepted = client.put(path, headers=headers, json=payload)
            replayed = client.put(path, headers=headers, json=payload)

            assert accepted.status_code == 200
            assert replayed.status_code == 200
            page = repository.list_definitions(tenant_id=tenant_id, limit=10, offset=0)
            assert page.count == 1
            assert page.items[0].composite_id == composite_id
    finally:
        app.dependency_overrides.clear()
