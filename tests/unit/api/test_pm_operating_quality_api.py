from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from src.api.dependencies import get_outcome_review_repository
from src.api.dependencies import get_pm_quality_policy_repository
from src.api.dependencies import get_pm_quality_score_run_repository
from src.api.main import app
from src.infrastructure.outcomes import InMemoryDpmOutcomeReviewRepository
from src.infrastructure.pm_quality import (
    InMemoryDpmPmQualityPolicyRepository,
    InMemoryDpmPmQualityScoreRunRepository,
)
from tests.unit.infrastructure.test_outcome_review_repository import _review


@pytest.fixture(autouse=True)
def _pm_quality_policy_repository_override():
    repository = InMemoryDpmPmQualityPolicyRepository()
    app.dependency_overrides[get_pm_quality_policy_repository] = lambda: repository
    try:
        yield repository
    finally:
        app.dependency_overrides.clear()


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


def _request_with_policy_ref(outcome_review_id: str = "dor_001") -> dict:
    payload = _request(outcome_review_id=outcome_review_id)
    policy = payload.pop("policy")
    payload["policy_id"] = policy["policy_id"]
    payload["policy_version"] = policy["policy_version"]
    return payload


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


def test_pm_operating_quality_api_administers_policies_and_uses_policy_refs() -> None:
    outcome_repository = InMemoryDpmOutcomeReviewRepository()
    outcome_repository.save_outcome_review(review=_review(), retention_expires_at=None)
    policy_repository = InMemoryDpmPmQualityPolicyRepository()
    score_run_repository = InMemoryDpmPmQualityScoreRunRepository()
    app.dependency_overrides[get_outcome_review_repository] = lambda: outcome_repository
    app.dependency_overrides[get_pm_quality_policy_repository] = lambda: policy_repository
    app.dependency_overrides[get_pm_quality_score_run_repository] = lambda: score_run_repository
    try:
        with TestClient(app) as client:
            saved = client.put(
                "/api/v1/rebalance/pm-operating-quality/policies/pmq_sg_dpm/versions/2026.05",
                json=_policy(),
            )
            fetched = client.get(
                "/api/v1/rebalance/pm-operating-quality/policies/pmq_sg_dpm/versions/2026.05"
            )
            listed = client.get(
                "/api/v1/rebalance/pm-operating-quality/policies",
                params={"enabled": "true", "policy_id": "pmq_sg_dpm"},
            )
            preview = client.post(
                "/api/v1/rebalance/pm-operating-quality/score-runs/preview",
                json=_request_with_policy_ref(),
            )
            created = client.post(
                "/api/v1/rebalance/pm-operating-quality/score-runs",
                json=_request_with_policy_ref(),
            )
            missing = client.get(
                "/api/v1/rebalance/pm-operating-quality/policies/pmq_missing/versions/2026.05"
            )
    finally:
        app.dependency_overrides.clear()

    assert saved.status_code == 200
    assert fetched.status_code == 200
    assert fetched.json()["policy_id"] == "pmq_sg_dpm"
    assert listed.status_code == 200
    assert listed.json()["count"] == 1
    assert preview.status_code == 200
    assert preview.json()["score_run"]["policy_id"] == "pmq_sg_dpm"
    assert created.status_code == 201
    assert created.json()["score_run"]["policy_version"] == "2026.05"
    assert missing.status_code == 404
    assert missing.json()["detail"] == "PM_QUALITY_POLICY_NOT_FOUND:pmq_missing:2026.05"


def test_pm_operating_quality_api_rejects_policy_admin_conflicts_and_bad_refs() -> None:
    policy_repository = InMemoryDpmPmQualityPolicyRepository()
    app.dependency_overrides[get_pm_quality_policy_repository] = lambda: policy_repository
    app.dependency_overrides[get_outcome_review_repository] = lambda: (
        InMemoryDpmOutcomeReviewRepository()
    )
    try:
        with TestClient(app) as client:
            saved = client.put(
                "/api/v1/rebalance/pm-operating-quality/policies/pmq_sg_dpm/versions/2026.05",
                json=_policy(),
            )
            changed_policy = _policy()
            changed_policy["ready_threshold"] = "90"
            conflict = client.put(
                "/api/v1/rebalance/pm-operating-quality/policies/pmq_sg_dpm/versions/2026.05",
                json=changed_policy,
            )
            mismatch_policy = _policy()
            mismatch_policy["policy_version"] = "2026.06"
            mismatch = client.put(
                "/api/v1/rebalance/pm-operating-quality/policies/pmq_sg_dpm/versions/2026.05",
                json=mismatch_policy,
            )
            missing_policy_payload = _request_with_policy_ref()
            missing_policy_payload["policy_id"] = "pmq_missing"
            missing_policy_ref = client.post(
                "/api/v1/rebalance/pm-operating-quality/score-runs/preview",
                json=missing_policy_payload,
            )
            missing_ref = client.post(
                "/api/v1/rebalance/pm-operating-quality/score-runs/preview",
                json=_request_with_policy_ref(),
            )
    finally:
        app.dependency_overrides.clear()

    assert saved.status_code == 200
    assert conflict.status_code == 409
    assert conflict.json()["detail"] == "PM_QUALITY_POLICY_IMMUTABLE_CONFLICT"
    assert mismatch.status_code == 422
    assert mismatch.json()["detail"] == "PM_QUALITY_POLICY_PATH_BODY_MISMATCH"
    assert missing_policy_ref.status_code == 404
    assert missing_policy_ref.json()["detail"] == "PM_QUALITY_POLICY_NOT_FOUND:pmq_missing:2026.05"
    assert missing_ref.status_code == 404
    assert missing_ref.json()["detail"] == "OUTCOME_REVIEW_NOT_FOUND:dor_001"


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

    policy_list_path = "/api/v1/rebalance/pm-operating-quality/policies"
    policy_get_path = (
        "/api/v1/rebalance/pm-operating-quality/policies/{policy_id}/versions/{policy_version}"
    )
    assert policy_list_path in schema["paths"]
    assert policy_get_path in schema["paths"]
    assert "200" in schema["paths"][policy_list_path]["get"]["responses"]
    assert "200" in schema["paths"][policy_get_path]["put"]["responses"]
    assert "200" in schema["paths"][policy_get_path]["get"]["responses"]
    assert "not compute PM scores" in schema["paths"][policy_list_path]["get"]["description"]
