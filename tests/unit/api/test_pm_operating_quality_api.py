from decimal import Decimal

from fastapi.testclient import TestClient

from src.api.dependencies import get_outcome_review_repository
from src.api.dependencies import get_pm_quality_score_run_repository
from src.api.main import app
from src.infrastructure.outcomes import InMemoryDpmOutcomeReviewRepository
from src.infrastructure.pm_quality import InMemoryDpmPmQualityScoreRunRepository
from tests.unit.infrastructure.test_outcome_review_repository import _review


def _policy(enabled: bool = True) -> dict:
    return {
        "policy_id": "pmq_sg_dpm",
        "policy_version": "2026.05",
        "enabled": enabled,
        "as_of_date": "2026-05-12",
        "access_purpose": "SUPERVISORY_CONTROL_REVIEW",
        "weights": [
            {
                "indicator": "OUTCOME_DISCIPLINE",
                "weight": "70",
                "minimum_evidence_count": 1,
            },
            {
                "indicator": "SOURCE_QUALITY",
                "weight": "30",
                "minimum_evidence_count": 1,
            },
        ],
    }


def _request(outcome_review_id: str = "dor_001") -> dict:
    return {
        "pm_id": "pm_001",
        "book_id": "sg_dpm_book",
        "as_of_date": "2026-05-12",
        "policy": _policy(),
        "evidence_items": [],
        "outcome_review_ids": [outcome_review_id],
        "actor_id": "ops",
    }


def test_pm_operating_quality_api_scores_persisted_outcome_review_evidence() -> None:
    repository = InMemoryDpmOutcomeReviewRepository()
    repository.save_outcome_review(review=_review(), retention_expires_at=None)
    app.dependency_overrides[get_outcome_review_repository] = lambda: repository
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/rebalance/pm-operating-quality/score-runs/preview",
                json=_request(),
                headers={"X-Correlation-Id": "corr-pmq-001"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    score_run = response.json()["score_run"]
    assert score_run["state"] == "READY"
    assert Decimal(score_run["score"]) == Decimal("100.00")
    assert score_run["correlation_id"] == "corr-pmq-001"
    assert any(ref["source_type"] == "PostTradeOutcomeReview" for ref in score_run["source_refs"])
    assert "autonomous_pm_ranking" in score_run["forbidden_uses"]


def test_pm_operating_quality_api_creates_gets_and_lists_persisted_score_runs() -> None:
    outcome_repository = InMemoryDpmOutcomeReviewRepository()
    outcome_repository.save_outcome_review(review=_review(), retention_expires_at=None)
    score_run_repository = InMemoryDpmPmQualityScoreRunRepository()
    app.dependency_overrides[get_outcome_review_repository] = lambda: outcome_repository
    app.dependency_overrides[get_pm_quality_score_run_repository] = lambda: score_run_repository
    try:
        with TestClient(app) as client:
            created = client.post(
                "/api/v1/rebalance/pm-operating-quality/score-runs",
                json=_request(),
                headers={"X-Correlation-Id": "corr-pmq-create"},
            )
            score_run_id = created.json()["score_run"]["score_run_id"]
            fetched = client.get(
                f"/api/v1/rebalance/pm-operating-quality/score-runs/{score_run_id}"
            )
            listed = client.get(
                "/api/v1/rebalance/pm-operating-quality/score-runs",
                params={"pm_id": "pm_001", "policy_id": "pmq_sg_dpm"},
            )
            missing = client.get("/api/v1/rebalance/pm-operating-quality/score-runs/missing")
    finally:
        app.dependency_overrides.clear()

    assert created.status_code == 201
    assert created.json()["score_run"]["correlation_id"] == "corr-pmq-create"
    assert fetched.status_code == 200
    assert fetched.json()["score_run"]["score_run_id"] == score_run_id
    assert listed.status_code == 200
    assert listed.json()["count"] == 1
    assert listed.json()["score_runs"][0]["score_run_id"] == score_run_id
    assert missing.status_code == 404
    assert missing.json()["detail"] == "PM_QUALITY_SCORE_RUN_NOT_FOUND:missing"


def test_pm_operating_quality_api_returns_disabled_score_run_without_score() -> None:
    payload = _request()
    payload["policy"] = _policy(enabled=False)
    payload["outcome_review_ids"] = []

    app.dependency_overrides[get_outcome_review_repository] = lambda: (
        InMemoryDpmOutcomeReviewRepository()
    )
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/rebalance/pm-operating-quality/score-runs/preview",
                json=payload,
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    score_run = response.json()["score_run"]
    assert score_run["state"] == "DISABLED"
    assert score_run["score"] is None
    assert score_run["reason_codes"] == ["PM_QUALITY_POLICY_DISABLED"]


def test_pm_operating_quality_api_fails_closed_for_missing_review_and_policy_mismatch() -> None:
    repository = InMemoryDpmOutcomeReviewRepository()
    app.dependency_overrides[get_outcome_review_repository] = lambda: repository
    try:
        with TestClient(app) as client:
            missing = client.post(
                "/api/v1/rebalance/pm-operating-quality/score-runs/preview",
                json=_request("missing"),
            )
            mismatched = _request()
            mismatched["outcome_review_ids"] = []
            mismatched["as_of_date"] = "2026-05-13"
            mismatch = client.post(
                "/api/v1/rebalance/pm-operating-quality/score-runs/preview",
                json=mismatched,
            )
    finally:
        app.dependency_overrides.clear()

    assert missing.status_code == 404
    assert missing.json()["detail"] == "OUTCOME_REVIEW_NOT_FOUND:missing"
    assert mismatch.status_code == 422
    assert mismatch.json()["detail"] == "PM_QUALITY_POLICY_AS_OF_DATE_MISMATCH"


def test_pm_operating_quality_openapi_contract_is_documented() -> None:
    with TestClient(app) as client:
        schema = client.get("/openapi.json").json()

    path = "/api/v1/rebalance/pm-operating-quality/score-runs/preview"
    assert path in schema["paths"]
    operation = schema["paths"][path]["post"]
    assert operation["tags"] == ["lotus-manage PM Operating Quality"]
    assert all(marker in operation["description"] for marker in ["What:", "When:", "How:"])
    assert "requestBody" in operation
    assert "200" in operation["responses"]
    assert "compensation" in operation["description"]

    create_path = "/api/v1/rebalance/pm-operating-quality/score-runs"
    get_path = "/api/v1/rebalance/pm-operating-quality/score-runs/{score_run_id}"
    assert create_path in schema["paths"]
    assert get_path in schema["paths"]
    assert "201" in schema["paths"][create_path]["post"]["responses"]
    assert "policy" in schema["paths"][create_path]["post"]["description"]
    assert "200" in schema["paths"][create_path]["get"]["responses"]
    assert "does not recompute scores" in schema["paths"][create_path]["get"]["description"]
    assert "200" in schema["paths"][get_path]["get"]["responses"]
    assert "does not recompute" in schema["paths"][get_path]["get"]["description"]
