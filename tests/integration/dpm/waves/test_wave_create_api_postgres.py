"""Registered wave-create API semantics proven against PostgreSQL (#724)."""

from __future__ import annotations

import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from src.api.dependencies import (
    get_campaign_definition_repository,
    get_mandate_repository,
    get_wave_repository,
)
from src.api.main import app
from src.infrastructure.mandates import InMemoryDpmMandateRepository
from src.infrastructure.waves import InMemoryDpmBulkReviewCampaignDefinitionRepository
from src.infrastructure.waves.postgres import PostgresDpmWaveRepository
from tests.integration.dpm.postgres_prerequisite import postgres_dsn_or_skip

_PROOF = "registered wave-create correlation and idempotency proof"


@pytest.fixture
def repository() -> PostgresDpmWaveRepository:
    return PostgresDpmWaveRepository(dsn=postgres_dsn_or_skip(_PROOF))


@pytest.fixture(autouse=True)
def restore_app_dependencies():
    original = dict(app.dependency_overrides)
    yield
    app.dependency_overrides = original
    app.openapi_schema = None


def _request(*, rationale: str = "Create a source-backed portfolio review wave.") -> dict:
    return {
        "trigger_type": "EXPLICIT_PORTFOLIO_LIST",
        "trigger_id": "same-business-trigger",
        "rationale": rationale,
        "as_of_date": "2026-10-01",
        "actor_id": "pm-integration",
        "portfolios": [
            {
                "portfolio_id": "PB_SG_WAVE_CREATE_001",
                "source_refs": [
                    {
                        "source_system": "bank-core-adapter",
                        "source_type": "AFFECTED_PORTFOLIO_MANIFEST",
                        "source_id": "manifest-wave-create-001",
                        "source_version": "1.0.0",
                        "supportability_state": "READY",
                    }
                ],
            }
        ],
    }


def _client(repository: PostgresDpmWaveRepository) -> TestClient:
    app.dependency_overrides[get_mandate_repository] = InMemoryDpmMandateRepository
    app.dependency_overrides[get_campaign_definition_repository] = (
        InMemoryDpmBulkReviewCampaignDefinitionRepository
    )
    app.dependency_overrides[get_wave_repository] = lambda: repository
    return TestClient(app)


def _headers(*, tenant: str, key: str, correlation: str | None = None) -> dict[str, str]:
    headers = {"X-Tenant-Id": tenant, "Idempotency-Key": key}
    if correlation is not None:
        headers["X-Correlation-Id"] = correlation
    return headers


def test_registered_create_api_enforces_command_and_correlation_identity(
    repository: PostgresDpmWaveRepository,
) -> None:
    run = uuid.uuid4().hex[:12]
    tenant_a = f"tenant-wave-create-a-{run}"
    tenant_b = f"tenant-wave-create-b-{run}"
    explicit_correlation = f"corr-wave-create-{run}"

    with _client(repository) as client:
        first = client.post(
            "/api/v1/rebalance/waves",
            json=_request(),
            headers=_headers(tenant=tenant_a, key=f"idem-a-{run}"),
        )
        exact_replay = client.post(
            "/api/v1/rebalance/waves",
            json=_request(),
            headers=_headers(tenant=tenant_a, key=f"idem-a-{run}"),
        )
        changed_request = client.post(
            "/api/v1/rebalance/waves",
            json=_request(rationale="A different economic create instruction."),
            headers=_headers(tenant=tenant_a, key=f"idem-a-{run}"),
        )
        distinct_command = client.post(
            "/api/v1/rebalance/waves",
            json=_request(),
            headers=_headers(tenant=tenant_a, key=f"idem-b-{run}"),
        )
        explicit_first = client.post(
            "/api/v1/rebalance/waves",
            json=_request(),
            headers=_headers(
                tenant=tenant_a,
                key=f"idem-explicit-a-{run}",
                correlation=explicit_correlation,
            ),
        )
        explicit_collision = client.post(
            "/api/v1/rebalance/waves",
            json=_request(),
            headers=_headers(
                tenant=tenant_a,
                key=f"idem-explicit-b-{run}",
                correlation=explicit_correlation,
            ),
        )
        other_tenant = client.post(
            "/api/v1/rebalance/waves",
            json=_request(),
            headers=_headers(
                tenant=tenant_b,
                key=f"idem-explicit-b-{run}",
                correlation=explicit_correlation,
            ),
        )

    assert first.status_code == exact_replay.status_code == 201
    assert exact_replay.json()["idempotent_replay"] is True
    assert exact_replay.json()["wave"]["wave_id"] == first.json()["wave"]["wave_id"]
    assert changed_request.status_code == 409
    assert changed_request.json()["detail"]["message"] == "DPM_WAVE_IDEMPOTENCY_CONFLICT"

    assert distinct_command.status_code == 201
    assert distinct_command.json()["wave"]["wave_id"] != first.json()["wave"]["wave_id"]
    assert (
        distinct_command.json()["wave"]["correlation_id"] != first.json()["wave"]["correlation_id"]
    )

    assert explicit_first.status_code == 201
    assert explicit_collision.status_code == 409
    assert explicit_collision.json()["detail"]["message"] == "DPM_WAVE_CORRELATION_CONFLICT"
    assert (
        repository.get_wave_idempotency_record(
            idempotency_key=f"idem-explicit-b-{run}", tenant_id=tenant_a
        )
        is None
    )
    assert len(repository.list_waves(tenant_id=tenant_a)) == 3

    assert other_tenant.status_code == 201
    assert other_tenant.json()["wave"]["tenant_id"] == tenant_b
    tenant_b_waves = repository.list_waves(tenant_id=tenant_b)
    assert [wave.wave_id for wave in tenant_b_waves] == [other_tenant.json()["wave"]["wave_id"]]
    assert tenant_b_waves[0].tenant_id == tenant_b


def test_competing_registered_creates_converge_and_survive_repository_restart(
    repository: PostgresDpmWaveRepository,
) -> None:
    run = uuid.uuid4().hex[:12]
    tenant = f"tenant-wave-race-{run}"
    key = f"idem-wave-race-{run}"

    with _client(repository) as client:

        def create() -> object:
            return client.post(
                "/api/v1/rebalance/waves",
                json=_request(),
                headers=_headers(tenant=tenant, key=key),
            )

        with ThreadPoolExecutor(max_workers=2) as executor:
            responses = list(executor.map(lambda _index: create(), range(2)))

    assert [response.status_code for response in responses] == [201, 201]
    wave_ids = {response.json()["wave"]["wave_id"] for response in responses}
    assert len(wave_ids) == 1
    assert sorted(response.json()["idempotent_replay"] for response in responses) == [False, True]
    wave_id = wave_ids.pop()
    assert [wave.wave_id for wave in repository.list_waves(tenant_id=tenant)] == [wave_id]

    restarted = PostgresDpmWaveRepository(dsn=postgres_dsn_or_skip(_PROOF))
    record = restarted.get_wave_idempotency_record(idempotency_key=key, tenant_id=tenant)
    assert record is not None
    assert record.wave.wave_id == wave_id
    assert [event.reason_code for event in record.wave.events] == ["WAVE_PREVIEWED", "WAVE_CREATED"]
