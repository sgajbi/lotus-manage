import pytest
from fastapi.testclient import TestClient

from src.api.dependencies import (
    get_construction_repository,
    get_db_session,
    get_proof_pack_repository,
)
from src.api.main import app
from src.api.routers.rebalance_runs import reset_dpm_run_support_service_for_tests
from src.api.services.rebalance_simulation_service import DPM_IDEMPOTENCY_CACHE
from src.infrastructure.construction import InMemoryConstructionRepository
from src.infrastructure.proof_packs import InMemoryDpmProofPackRepository
from tests.shared.factories import valid_api_payload


async def override_get_db_session():
    yield None


@pytest.fixture(autouse=True)
def override_dependencies():
    original_overrides = dict(app.dependency_overrides)
    construction_repository = InMemoryConstructionRepository()
    proof_pack_repository = InMemoryDpmProofPackRepository()
    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_construction_repository] = lambda: construction_repository
    app.dependency_overrides[get_proof_pack_repository] = lambda: proof_pack_repository
    DPM_IDEMPOTENCY_CACHE.clear()
    reset_dpm_run_support_service_for_tests()
    yield
    DPM_IDEMPOTENCY_CACHE.clear()
    reset_dpm_run_support_service_for_tests()
    app.dependency_overrides = original_overrides


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def _simulate_run(client: TestClient) -> str:
    response = client.post(
        "/api/v1/rebalance/simulate",
        json={"input_mode": "stateless", "stateless_input": valid_api_payload()},
        headers={"Idempotency-Key": "proof-pack-source-run", "X-Correlation-Id": "corr-proof-api"},
    )
    assert response.status_code == 200
    return str(response.json()["rebalance_run_id"])


def _generate_selected_alternative(client: TestClient) -> tuple[str, str]:
    response = client.post(
        "/api/v1/construction/alternative-sets/generate",
        json={
            "input_mode": "stateless",
            "stateless_input": valid_api_payload(),
            "methods": ["DO_NOTHING_BASELINE", "HEURISTIC_EXPLAINABLE"],
        },
        headers={
            "Idempotency-Key": "proof-pack-source-alternatives",
            "X-Correlation-Id": "corr-proof-pack-alternatives",
        },
    )
    assert response.status_code == 200
    alternative_set = response.json()
    selected_alternative_id = alternative_set["alternatives"][1]["alternative_id"]

    selection = client.post(
        f"/api/v1/construction/alternative-sets/{alternative_set['alternative_set_id']}/selections",
        json={
            "alternative_id": selected_alternative_id,
            "actor_id": "pm_api",
            "reason_code": "LOWER_DRIFT_WITH_SOURCE_TRACE",
            "comment": "Selected for proof-pack API coverage.",
        },
        headers={"X-Correlation-Id": "corr-proof-pack-selection"},
    )
    assert selection.status_code == 200
    return str(alternative_set["alternative_set_id"]), str(selected_alternative_id)


def test_generate_get_and_render_direct_run_proof_pack(client: TestClient) -> None:
    run_id = _simulate_run(client)

    generated = client.post(
        "/api/v1/rebalance/proof-packs",
        json={
            "source_type": "REBALANCE_RUN",
            "rebalance_run_id": run_id,
            "include_markdown": True,
            "include_report_input": True,
            "include_ai_evidence_input": True,
            "actor_id": "pm_api",
            "reason": "Rebalance back to model after drift review.",
            "mandate_id": "mandate_api_001",
        },
        headers={
            "Idempotency-Key": "proof-pack-api-001",
            "X-Correlation-Id": "corr-proof-pack-api",
        },
    )

    assert generated.status_code == 200
    body = generated.json()
    proof_pack = body["proof_pack"]
    assert proof_pack["source_type"] == "REBALANCE_RUN"
    assert proof_pack["rebalance_run_id"] == run_id
    assert proof_pack["content_hash"].startswith("sha256:")
    assert body["markdown_url"].endswith("/summary.md")
    assert body["report_input_url"].endswith("/report-input")
    assert body["ai_evidence_input_url"].endswith("/ai-evidence-input")

    replay = client.post(
        "/api/v1/rebalance/proof-packs",
        json={
            "source_type": "REBALANCE_RUN",
            "rebalance_run_id": run_id,
            "actor_id": "pm_api",
            "reason": "Changed replay reason should not mutate persisted proof.",
            "mandate_id": "mandate_api_001",
        },
        headers={"Idempotency-Key": "proof-pack-api-001"},
    )
    assert replay.status_code == 200
    assert replay.json()["proof_pack"]["content_hash"] == proof_pack["content_hash"]

    fetched = client.get(f"/api/v1/rebalance/proof-packs/{proof_pack['proof_pack_id']}")
    assert fetched.status_code == 200
    fetched_proof_pack = fetched.json()["proof_pack"]
    assert fetched_proof_pack["proof_pack_id"] == proof_pack["proof_pack_id"]
    assert fetched_proof_pack["report_input_ref"]["ref_type"] == "DPM_PROOF_PACK_REPORT_INPUT"
    assert fetched_proof_pack["ai_evidence_ref"]["ref_type"] == "DPM_PROOF_PACK_AI_EVIDENCE_INPUT"

    markdown = client.get(f"/api/v1/rebalance/proof-packs/{proof_pack['proof_pack_id']}/summary.md")
    assert markdown.status_code == 200
    assert "# Pre-Trade Proof Pack" in markdown.text
    assert "| `reporting_refs` | `READY` |" in markdown.text
    assert "| `ai_refs` | `READY` |" in markdown.text

    report = client.get(f"/api/v1/rebalance/proof-packs/{proof_pack['proof_pack_id']}/report-input")
    assert report.status_code == 200
    report_input = report.json()
    assert report_input["proof_pack_id"] == proof_pack["proof_pack_id"]
    assert report_input["proof_pack_content_hash"] == proof_pack["content_hash"]
    assert report_input["content_hash"].startswith("sha256:")
    assert report_input["evidence_ref"]["ref_type"] == "DPM_PROOF_PACK_REPORT_INPUT"

    ai = client.get(
        f"/api/v1/rebalance/proof-packs/{proof_pack['proof_pack_id']}/ai-evidence-input"
    )
    assert ai.status_code == 200
    ai_input = ai.json()
    assert ai_input["proof_pack_id"] == proof_pack["proof_pack_id"]
    assert ai_input["proof_pack_content_hash"] == proof_pack["content_hash"]
    assert ai_input["content_hash"].startswith("sha256:")
    assert ai_input["evidence_ref"]["ref_type"] == "DPM_PROOF_PACK_AI_EVIDENCE_INPUT"
    assert "place_orders" in ai_input["forbidden_actions"]


def test_generate_selected_alternative_proof_pack(client: TestClient) -> None:
    alternative_set_id, selected_alternative_id = _generate_selected_alternative(client)

    response = client.post(
        "/api/v1/rebalance/proof-packs",
        json={
            "source_type": "SELECTED_ALTERNATIVE",
            "alternative_set_id": alternative_set_id,
            "selected_alternative_id": selected_alternative_id,
            "actor_id": "pm_api",
            "reason": "Document selected construction path before approval.",
            "mandate_id": "mandate_api_001",
        },
        headers={
            "Idempotency-Key": "proof-pack-selected-alt-api-001",
            "X-Correlation-Id": "corr-proof-pack-selected-alt",
        },
    )

    assert response.status_code == 200
    proof_pack = response.json()["proof_pack"]
    assert proof_pack["source_type"] == "SELECTED_ALTERNATIVE"
    assert proof_pack["alternative_set_id"] == alternative_set_id
    assert proof_pack["selected_alternative_id"] == selected_alternative_id
    assert proof_pack["content_hash"].startswith("sha256:")
    assert any(
        section["section_type"] == "selected_alternative" and section["state"] == "READY"
        for section in proof_pack["sections"]
    )


def test_generate_proof_pack_validates_source_fields(client: TestClient) -> None:
    missing_run = client.post(
        "/api/v1/rebalance/proof-packs",
        json={
            "source_type": "REBALANCE_RUN",
            "actor_id": "pm_api",
        },
        headers={"Idempotency-Key": "proof-pack-api-missing-run"},
    )
    assert missing_run.status_code == 422
    assert missing_run.json()["detail"] == "DPM_PROOF_PACK_REBALANCE_RUN_ID_REQUIRED"

    missing_source = client.post(
        "/api/v1/rebalance/proof-packs",
        json={
            "source_type": "SELECTED_ALTERNATIVE",
            "actor_id": "pm_api",
        },
        headers={"Idempotency-Key": "proof-pack-api-missing-alt"},
    )
    assert missing_source.status_code == 422
    assert missing_source.json()["detail"] == "DPM_PROOF_PACK_SELECTED_ALTERNATIVE_SOURCE_REQUIRED"


def test_proof_pack_openapi_documents_endpoints(client: TestClient) -> None:
    openapi = client.get("/openapi.json").json()

    for path in [
        "/api/v1/rebalance/proof-packs",
        "/api/v1/rebalance/proof-packs/{proof_pack_id}",
        "/api/v1/rebalance/proof-packs/{proof_pack_id}/summary.md",
        "/api/v1/rebalance/proof-packs/{proof_pack_id}/report-input",
        "/api/v1/rebalance/proof-packs/{proof_pack_id}/ai-evidence-input",
    ]:
        assert path in openapi["paths"]

    operation = openapi["paths"]["/api/v1/rebalance/proof-packs"]["post"]
    assert operation["summary"] == "Generate a pre-trade proof pack"
    assert "Idempotency-Key" in str(operation["parameters"])
