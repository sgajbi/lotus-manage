from fastapi.testclient import TestClient

from src.api.dependencies import get_outcome_review_repository
from src.api.main import app
from src.infrastructure.outcomes import InMemoryDpmOutcomeReviewRepository
from tests.unit.infrastructure.test_outcome_review_repository import _review


def _request_payload() -> dict:
    review = _review()
    return {
        "expected_snapshot": review.expected_snapshot.model_dump(mode="json"),
        "realized_snapshot": review.realized_snapshot.model_dump(mode="json"),
        "dimension_configs": [
            {
                "dimension": "DRIFT_REDUCTION",
                "tolerance": {"soft": "0.0025", "hard": "0.0100"},
                "materiality": "0.0050",
                "direction": "LOWER_IS_BETTER",
            }
        ],
        "actor_id": "pm_001",
    }


def _refresh_payload() -> dict:
    payload = _request_payload()
    return {
        "actor_id": "system",
        "realized_snapshot": payload["realized_snapshot"],
        "dimension_configs": payload["dimension_configs"],
    }


def test_outcome_review_api_preview_create_lookup_supportability_and_events() -> None:
    repository = InMemoryDpmOutcomeReviewRepository()
    app.dependency_overrides[get_outcome_review_repository] = lambda: repository
    try:
        with TestClient(app) as client:
            preview = client.post("/api/v1/rebalance/outcome-reviews/preview", json=_request_payload())
            assert preview.status_code == 200
            assert preview.json()["comparison"]["state"] == "READY"

            created = client.post(
                "/api/v1/rebalance/outcome-reviews",
                json=_request_payload(),
                headers={"Idempotency-Key": "outcome-idem-001", "X-Correlation-Id": "corr-001"},
            )
            assert created.status_code == 200
            outcome_review = created.json()["outcome_review"]
            outcome_review_id = outcome_review["outcome_review_id"]
            assert outcome_review["state"] == "READY"
            assert outcome_review["content_hash"].startswith("sha256:")

            replay = client.post(
                "/api/v1/rebalance/outcome-reviews",
                json=_request_payload(),
                headers={"Idempotency-Key": "outcome-idem-001", "X-Correlation-Id": "corr-001"},
            )
            assert replay.status_code == 200
            assert replay.json()["outcome_review"]["outcome_review_id"] == outcome_review_id

            lookup = client.get(f"/api/v1/rebalance/outcome-reviews/{outcome_review_id}")
            assert lookup.status_code == 200
            supportability = client.get(
                f"/api/v1/rebalance/outcome-reviews/{outcome_review_id}/supportability"
            )
            assert supportability.status_code == 200
            assert supportability.json()["state"] == "READY"

            refresh = client.post(
                f"/api/v1/rebalance/outcome-reviews/{outcome_review_id}/refresh-sources",
                json=_refresh_payload(),
            )
            assert refresh.status_code == 200
            assert refresh.json()["event"]["event_type"] == "OUTCOME_REVIEW_SOURCE_REFRESHED"
            assert refresh.json()["comparison"]["state"] == "READY"
    finally:
        app.dependency_overrides.clear()


def test_outcome_review_openapi_contract_is_grouped_and_guided() -> None:
    with TestClient(app) as client:
        schema = client.get("/openapi.json").json()

    expected_paths = [
        "/api/v1/rebalance/outcome-reviews/preview",
        "/api/v1/rebalance/outcome-reviews",
        "/api/v1/rebalance/outcome-reviews/{outcome_review_id}",
        "/api/v1/rebalance/outcome-reviews/{outcome_review_id}/refresh-sources",
        "/api/v1/rebalance/outcome-reviews/{outcome_review_id}/supportability",
        "/api/v1/rebalance/runs/{rebalance_run_id}/outcome-review",
        "/api/v1/rebalance/waves/{wave_id}/outcome-reviews",
    ]
    for path in expected_paths:
        assert path in schema["paths"]

    preview = schema["paths"]["/api/v1/rebalance/outcome-reviews/preview"]["post"]
    assert preview["tags"] == ["lotus-manage Outcome Reviews"]
    assert all(marker in preview["description"] for marker in ["What:", "When:", "How:"])
    assert "requestBody" in preview
    assert "200" in preview["responses"]

    refresh = schema["paths"]["/api/v1/rebalance/outcome-reviews/{outcome_review_id}/refresh-sources"][
        "post"
    ]
    assert refresh["tags"] == ["lotus-manage Outcome Reviews"]
    assert all(marker in refresh["description"] for marker in ["What:", "When:", "How:"])
    assert "requestBody" in refresh
    assert "200" in refresh["responses"]


def test_outcome_review_api_search_run_wave_and_missing_dimension_guardrail() -> None:
    repository = InMemoryDpmOutcomeReviewRepository()
    app.dependency_overrides[get_outcome_review_repository] = lambda: repository
    try:
        with TestClient(app) as client:
            created = client.post(
                "/api/v1/rebalance/outcome-reviews",
                json=_request_payload(),
                headers={"Idempotency-Key": "outcome-idem-002"},
            )
            assert created.status_code == 200
            review_id = created.json()["outcome_review"]["outcome_review_id"]

            search = client.get(
                "/api/v1/rebalance/outcome-reviews",
                params={"portfolio_id": "PB_SG_GLOBAL_BAL_001"},
            )
            assert search.status_code == 200
            assert search.json()["items"][0]["outcome_review_id"] == review_id

            by_run = client.get("/api/v1/rebalance/runs/rr_001/outcome-review")
            assert by_run.status_code == 200
            by_wave = client.get("/api/v1/rebalance/waves/dwv_001/outcome-reviews")
            assert by_wave.status_code == 200
            assert by_wave.json()["items"][0]["outcome_review_id"] == review_id

            bad_payload = _request_payload()
            bad_payload["dimension_configs"][0]["dimension"] = "PERFORMANCE"
            bad = client.post("/api/v1/rebalance/outcome-reviews/preview", json=bad_payload)
            assert bad.status_code == 422
            assert "DPM_OUTCOME_DIMENSION_EVIDENCE_MISSING" in bad.text
    finally:
        app.dependency_overrides.clear()
