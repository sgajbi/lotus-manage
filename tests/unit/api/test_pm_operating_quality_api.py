from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from src.api.dependencies import get_outcome_review_repository
from src.api.dependencies import get_pm_quality_fairness_analysis_repository
from src.api.dependencies import get_pm_quality_policy_repository
from src.api.dependencies import get_pm_quality_score_run_repository
from src.api.main import app
from src.api.routers import pm_operating_quality as pmq_router
from src.core.dpm_source_context import DpmCorePortfolioManagerBookMembershipResponse
from src.infrastructure.core_sourcing import DpmCoreResolverError, DpmCoreResolverUnavailableError
from src.infrastructure.outcomes import InMemoryDpmOutcomeReviewRepository
from src.infrastructure.pm_quality import (
    InMemoryDpmPmQualityFairnessAnalysisRepository,
    InMemoryDpmPmQualityPolicyRepository,
    InMemoryDpmPmQualityScoreRunRepository,
)
from src.core.pm_quality import (
    DpmPmOperatingQualityPolicy,
    DpmPmOperatingQualityScoreRun,
    DpmPmQualityEvidenceItem,
    DpmPmQualityGovernanceApproval,
    DpmPmQualityWeight,
    build_pm_operating_quality_score_run,
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
    payload = {
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
    if enabled:
        payload["governance_approval"] = _governance_approval()
    return payload


def _scope_policy() -> dict:
    payload = _policy()
    payload["peer_group_policy"] = {
        "peer_group_id": "sg_dpm_balanced",
        "display_name": "Singapore DPM balanced mandates",
        "segment_type": "MANDATE_TYPE",
        "minimum_peer_count": 3,
        "source_refs": [
            {
                "source_system": "lotus-core",
                "source_type": "PM_QUALITY_PEER_GROUP_DEFINITION",
                "source_id": "sg_dpm_balanced",
                "source_version": "2026.05",
                "content_hash": "sha256:pmq-peer-group",
            }
        ],
    }
    payload["lookback_window_policy"] = {
        "window_id": "pmq_30d_20260512",
        "start_date": "2026-04-13",
        "end_date": "2026-05-12",
        "timezone": "Asia/Singapore",
        "source_refs": [
            {
                "source_system": "bank-governance",
                "source_type": "PM_QUALITY_LOOKBACK_WINDOW",
                "source_id": "pmq_30d_20260512",
                "source_version": "2026.05",
                "content_hash": "sha256:pmq-lookback-window",
            }
        ],
    }
    return payload


def _governance_approval() -> dict:
    return {
        "approval_ref": "PMQ-APPROVAL-2026-05",
        "approved_by": "pm_quality_committee",
        "approved_at": "2026-05-10T09:00:00Z",
        "fairness_review_ref": "FAIRNESS-PMQ-2026-05",
        "fairness_reviewed_by": "model_risk_governance",
        "fairness_reviewed_at": "2026-05-10T10:00:00Z",
        "expires_on": "2026-06-30",
        "entitled_actor_ids": ["ops"],
        "source_refs": [
            {
                "source_system": "bank-governance",
                "source_type": "PM_QUALITY_POLICY_APPROVAL",
                "source_id": "PMQ-APPROVAL-2026-05",
                "source_version": "2026.05",
                "content_hash": "sha256:pmq-approval",
            }
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


def _scope_request() -> dict:
    payload = _request()
    payload["policy"] = _scope_policy()
    payload["outcome_review_ids"] = []
    payload["evidence_items"] = [
        {
            "indicator": "OUTCOME_DISCIPLINE",
            "evidence_state": "READY",
            "score": "92",
            "source_system": "lotus-performance",
            "source_type": "PM_OUTCOME_DISCIPLINE",
            "source_id": "pm_outcome_001",
            "source_refs": [
                {
                    "source_system": "lotus-performance",
                    "source_type": "PM_OUTCOME_DISCIPLINE",
                    "source_id": "pm_outcome_001",
                    "source_version": "2026-05-10",
                }
            ],
        },
        {
            "indicator": "SOURCE_QUALITY",
            "evidence_state": "READY",
            "score": "88",
            "source_system": "lotus-risk",
            "source_type": "PM_SOURCE_QUALITY",
            "source_id": "pm_source_001",
            "source_refs": [
                {
                    "source_system": "lotus-risk",
                    "source_type": "PM_SOURCE_QUALITY",
                    "source_id": "pm_source_001",
                    "source_version": "2026-05-11",
                }
            ],
        },
    ]
    return payload


def _source_only_score_run(
    *, pm_id: str, score: Decimal, correlation_id: str = "corr"
) -> DpmPmOperatingQualityScoreRun:
    policy = DpmPmOperatingQualityPolicy(
        policy_id="pmq_sg_dpm",
        policy_version="2026.05",
        enabled=True,
        as_of_date="2026-05-12",
        access_purpose="SUPERVISORY_CONTROL_REVIEW",
        weights=[
            DpmPmQualityWeight(
                indicator="SOURCE_QUALITY",
                weight=Decimal("100"),
                minimum_evidence_count=1,
            )
        ],
        governance_approval=DpmPmQualityGovernanceApproval.model_validate(_governance_approval()),
    )
    return build_pm_operating_quality_score_run(
        pm_id=pm_id,
        book_id="sg_dpm_book",
        as_of_date="2026-05-12",
        policy=policy,
        evidence_items=[
            DpmPmQualityEvidenceItem(
                indicator="SOURCE_QUALITY",
                evidence_state="READY",
                score=score,
                source_system="lotus-risk",
                source_type="RiskMetricsReport",
                source_id=f"risk-{pm_id}",
            )
        ],
        outcome_reviews=[],
        generated_by="ops",
        correlation_id=correlation_id,
    )


def _pm_book_membership_payload(
    *, supportability_state: str = "READY", members: list | None = None
):
    return {
        "product_name": "PortfolioManagerBookMembership",
        "product_version": "v1",
        "as_of_date": "2026-05-12",
        "tenant_id": "tenant-sg",
        "portfolio_manager_id": "pm_001",
        "booking_center_code": "Singapore",
        "members": members
        if members is not None
        else [
            {
                "portfolio_id": "PB_SG_GLOBAL_BAL_001",
                "client_id": "client_001",
                "booking_center_code": "Singapore",
                "portfolio_type": "DPM",
                "status": "ACTIVE",
                "open_date": "2023-01-03",
                "base_currency": "USD",
                "source_record_id": "pm-book:001",
            },
            {
                "portfolio_id": "PB_SG_GLOBAL_INC_002",
                "client_id": "client_002",
                "booking_center_code": "Singapore",
                "portfolio_type": "DPM",
                "status": "ACTIVE",
                "open_date": "2023-02-03",
                "base_currency": "USD",
                "source_record_id": "pm-book:002",
            },
        ],
        "supportability": {
            "state": supportability_state,
            "reason": "DPM_CORE_PM_BOOK_READY"
            if supportability_state == "READY"
            else "DPM_CORE_PM_BOOK_INCOMPLETE",
            "returned_portfolio_count": 2 if members is None else len(members),
            "filters_applied": {"portfolio_types": ["DPM"], "include_inactive": False},
        },
        "lineage": {"source_system": "relationship_book", "contract_version": "rfc_041_v1"},
        "source_batch_fingerprint": "sha256:pm-book",
        "snapshot_id": "pm-book-snapshot-20260512",
    }


class _PmBookResolver:
    def __init__(self, payload: dict):
        self.payload = payload
        self.calls: list[dict[str, object]] = []

    def resolve_portfolio_manager_book_membership(self, **kwargs: object):
        self.calls.append(kwargs)
        return DpmCorePortfolioManagerBookMembershipResponse.model_validate(self.payload)


class _UnavailablePmBookResolver:
    def resolve_portfolio_manager_book_membership(self, **_kwargs: object):
        raise DpmCoreResolverUnavailableError("DPM_CORE_PM_BOOK_MEMBERSHIP_UNAVAILABLE")


class _IncompletePmBookResolver:
    def resolve_portfolio_manager_book_membership(self, **_kwargs: object):
        raise DpmCoreResolverError("DPM_CORE_PM_BOOK_MEMBERSHIP_INCOMPLETE")


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
    assert score_run["governance_evidence"]["approval_ref"] == "PMQ-APPROVAL-2026-05"
    assert score_run["governance_evidence"]["fairness_review_ref"] == "FAIRNESS-PMQ-2026-05"
    assert score_run["governance_evidence"]["actor_entitlement_state"] == "AUTHORIZED"
    assert any(ref["source_type"] == "PostTradeOutcomeReview" for ref in score_run["source_refs"])
    assert any(
        ref["source_type"] == "PM_QUALITY_POLICY_APPROVAL" for ref in score_run["source_refs"]
    )
    assert "autonomous_pm_ranking" in score_run["forbidden_uses"]


def test_pm_operating_quality_api_materializes_pm_book_scope(monkeypatch) -> None:
    repository = InMemoryDpmOutcomeReviewRepository()
    repository.save_outcome_review(review=_review(), retention_expires_at=None)
    resolver = _PmBookResolver(_pm_book_membership_payload())
    app.dependency_overrides[get_outcome_review_repository] = lambda: repository
    monkeypatch.setattr(pmq_router, "build_core_resolver_client", lambda: resolver)
    payload = {
        **_request(),
        "pm_book_scope": {
            "tenant_id": "tenant-sg",
            "booking_center_code": "Singapore",
            "portfolio_types": ["dpm"],
        },
    }
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/rebalance/pm-operating-quality/score-runs/preview",
                json=payload,
                headers={"X-Correlation-Id": "corr-pmq-book"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    score_run = response.json()["score_run"]
    assert score_run["book_scope_evidence"]["source_id"] == "pm-book-snapshot-20260512"
    assert score_run["book_scope_evidence"]["returned_portfolio_count"] == 2
    assert score_run["book_scope_evidence"]["member_portfolio_ids"] == [
        "PB_SG_GLOBAL_BAL_001",
        "PB_SG_GLOBAL_INC_002",
    ]
    assert score_run["book_scope_evidence"]["filters_applied"]["portfolio_types"] == ["DPM"]
    assert any(
        ref["source_type"] == "PortfolioManagerBookMembership" for ref in score_run["source_refs"]
    )
    assert len(resolver.calls) == 1
    call = resolver.calls[0]
    assert call["portfolio_manager_id"] == "pm_001"
    assert str(call["as_of_date"]) == "2026-05-12"
    assert call["tenant_id"] == "tenant-sg"
    assert call["booking_center_code"] == "Singapore"
    assert call["portfolio_types"] == ["DPM"]
    assert call["include_inactive"] is False
    assert call["correlation_id"] == "corr-pmq-book"


@pytest.mark.parametrize(
    ("resolver", "expected_status", "expected_code"),
    [
        (
            _PmBookResolver(_pm_book_membership_payload(supportability_state="INCOMPLETE")),
            424,
            "DPM_CORE_PM_BOOK_INCOMPLETE",
        ),
        (
            _PmBookResolver(_pm_book_membership_payload(members=[])),
            424,
            "DPM_CORE_PM_BOOK_MEMBERSHIP_EMPTY",
        ),
        (
            _UnavailablePmBookResolver(),
            503,
            "DPM_CORE_PM_BOOK_MEMBERSHIP_UNAVAILABLE",
        ),
        (
            _IncompletePmBookResolver(),
            424,
            "DPM_CORE_PM_BOOK_MEMBERSHIP_INCOMPLETE",
        ),
    ],
)
def test_pm_operating_quality_api_fails_closed_for_pm_book_scope(
    monkeypatch,
    resolver,
    expected_status: int,
    expected_code: str,
) -> None:
    repository = InMemoryDpmOutcomeReviewRepository()
    repository.save_outcome_review(review=_review(), retention_expires_at=None)
    app.dependency_overrides[get_outcome_review_repository] = lambda: repository
    monkeypatch.setattr(pmq_router, "build_core_resolver_client", lambda: resolver)
    payload = {
        **_request(),
        "pm_book_scope": {"booking_center_code": "Singapore", "portfolio_types": ["DPM"]},
    }
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/rebalance/pm-operating-quality/score-runs/preview",
                json=payload,
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == expected_status
    assert response.json()["detail"]["code"] == expected_code


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


def test_pm_operating_quality_api_materializes_policy_scope_context() -> None:
    policy_repository = InMemoryDpmPmQualityPolicyRepository()
    app.dependency_overrides[get_pm_quality_policy_repository] = lambda: policy_repository
    app.dependency_overrides[get_outcome_review_repository] = lambda: (
        InMemoryDpmOutcomeReviewRepository()
    )
    try:
        with TestClient(app) as client:
            saved = client.put(
                "/api/v1/rebalance/pm-operating-quality/policies/pmq_sg_dpm/versions/2026.05",
                json=_scope_policy(),
            )
            request = _scope_request()
            request.pop("policy")
            request["policy_id"] = "pmq_sg_dpm"
            request["policy_version"] = "2026.05"
            preview = client.post(
                "/api/v1/rebalance/pm-operating-quality/score-runs/preview",
                json=request,
            )
            stale_request = _scope_request()
            stale_request["evidence_items"][0]["source_refs"][0]["source_version"] = "2026-04-01"
            stale = client.post(
                "/api/v1/rebalance/pm-operating-quality/score-runs/preview",
                json=stale_request,
            )
    finally:
        app.dependency_overrides.clear()

    assert saved.status_code == 200
    assert preview.status_code == 200
    scope_evidence = preview.json()["score_run"]["scope_evidence"]
    assert scope_evidence["peer_group_id"] == "sg_dpm_balanced"
    assert scope_evidence["lookback_window_id"] == "pmq_30d_20260512"
    assert scope_evidence["reason_codes"] == [
        "PM_QUALITY_PEER_GROUP_MATERIALIZED",
        "PM_QUALITY_LOOKBACK_WINDOW_MATERIALIZED",
    ]
    assert stale.status_code == 422
    assert stale.json()["detail"] == "PM_QUALITY_EVIDENCE_OUTSIDE_LOOKBACK_WINDOW"


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


@pytest.mark.parametrize(
    ("policy_patch", "actor_id", "expected_detail"),
    [
        ({"governance_approval": None}, "ops", "PM_QUALITY_GOVERNANCE_APPROVAL_REQUIRED"),
        (
            {"governance_approval": {**_governance_approval(), "expires_on": "2026-05-01"}},
            "ops",
            "PM_QUALITY_GOVERNANCE_EXPIRED",
        ),
        (
            {"governance_approval": {**_governance_approval(), "expires_on": "bad"}},
            "ops",
            "PM_QUALITY_GOVERNANCE_EXPIRY_DATE_INVALID",
        ),
        (
            {"governance_approval": {**_governance_approval(), "entitled_actor_ids": ["ops_2"]}},
            "ops",
            "PM_QUALITY_ACTOR_NOT_ENTITLED",
        ),
    ],
)
def test_pm_operating_quality_api_fails_closed_for_invalid_governance(
    policy_patch: dict,
    actor_id: str,
    expected_detail: str,
) -> None:
    repository = InMemoryDpmOutcomeReviewRepository()
    repository.save_outcome_review(review=_review(), retention_expires_at=None)
    app.dependency_overrides[get_outcome_review_repository] = lambda: repository
    request = _request()
    request["actor_id"] = actor_id
    request["policy"] = {**_policy(), **policy_patch}
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/rebalance/pm-operating-quality/score-runs/preview",
                json=request,
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert expected_detail in str(response.json()["detail"])


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


def test_pm_operating_quality_api_previews_source_segment_fairness_analysis() -> None:
    score_run_repository = InMemoryDpmPmQualityScoreRunRepository()
    balanced_1 = _source_only_score_run(pm_id="pm_bal_001", score=Decimal("92"))
    balanced_2 = _source_only_score_run(
        pm_id="pm_bal_002", score=Decimal("88"), correlation_id="corr-balanced-2"
    )
    income_1 = _source_only_score_run(
        pm_id="pm_inc_001", score=Decimal("60"), correlation_id="corr-income-1"
    )
    income_2 = _source_only_score_run(
        pm_id="pm_inc_002", score=Decimal("58"), correlation_id="corr-income-2"
    )
    for score_run in [balanced_1, balanced_2, income_1, income_2]:
        score_run_repository.save_score_run(score_run=score_run)
    app.dependency_overrides[get_pm_quality_score_run_repository] = lambda: score_run_repository
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/rebalance/pm-operating-quality/fairness-analyses/preview",
                json={
                    "policy_id": "pmq_sg_dpm",
                    "policy_version": "2026.05",
                    "as_of_date": "2026-05-12",
                    "minimum_segment_score_run_count": 2,
                    "maximum_average_score_spread": "15",
                    "actor_id": "ops",
                    "segments": [
                        {
                            "segment_id": "mandate_balanced",
                            "segment_type": "MANDATE_TYPE",
                            "display_name": "Balanced DPM Mandates",
                            "score_run_ids": [
                                balanced_1.score_run_id,
                                balanced_2.score_run_id,
                            ],
                            "source_refs": [
                                {
                                    "source_system": "lotus-core",
                                    "source_type": "MandateTypeSegment",
                                    "source_id": "mandate_balanced",
                                }
                            ],
                        },
                        {
                            "segment_id": "mandate_income",
                            "segment_type": "MANDATE_TYPE",
                            "display_name": "Income DPM Mandates",
                            "score_run_ids": [income_1.score_run_id, income_2.score_run_id],
                            "source_refs": [
                                {
                                    "source_system": "lotus-core",
                                    "source_type": "MandateTypeSegment",
                                    "source_id": "mandate_income",
                                }
                            ],
                        },
                    ],
                },
                headers={"X-Correlation-Id": "corr-pmq-fairness"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    fairness_analysis = response.json()["fairness_analysis"]
    assert fairness_analysis["product_name"] == "PmOperatingQualityFairnessAnalysis"
    assert fairness_analysis["state"] == "PENDING_REVIEW"
    assert Decimal(fairness_analysis["observed_average_score_spread"]) == Decimal("31.00")
    assert fairness_analysis["reason_codes"] == ["PM_QUALITY_FAIRNESS_SPREAD_REVIEW_REQUIRED"]
    assert fairness_analysis["correlation_id"] == "corr-pmq-fairness"
    assert "protected_class_inference" in fairness_analysis["forbidden_uses"]
    assert {
        result["segment_id"]: Decimal(result["average_score"])
        for result in fairness_analysis["segment_results"]
    } == {"mandate_balanced": Decimal("90.00"), "mandate_income": Decimal("59.00")}
    assert any(
        ref["source_type"] == "PmOperatingQualityScoreRun"
        for ref in fairness_analysis["source_refs"]
    )


def test_pm_operating_quality_api_creates_gets_and_lists_fairness_analyses() -> None:
    score_run_repository = InMemoryDpmPmQualityScoreRunRepository()
    fairness_repository = InMemoryDpmPmQualityFairnessAnalysisRepository()
    balanced_1 = _source_only_score_run(pm_id="pm_bal_001", score=Decimal("92"))
    balanced_2 = _source_only_score_run(
        pm_id="pm_bal_002", score=Decimal("88"), correlation_id="corr-balanced-2"
    )
    income_1 = _source_only_score_run(
        pm_id="pm_inc_001", score=Decimal("60"), correlation_id="corr-income-1"
    )
    income_2 = _source_only_score_run(
        pm_id="pm_inc_002", score=Decimal("58"), correlation_id="corr-income-2"
    )
    for score_run in [balanced_1, balanced_2, income_1, income_2]:
        score_run_repository.save_score_run(score_run=score_run)
    app.dependency_overrides[get_pm_quality_score_run_repository] = lambda: score_run_repository
    app.dependency_overrides[get_pm_quality_fairness_analysis_repository] = lambda: (
        fairness_repository
    )
    request = {
        "policy_id": "pmq_sg_dpm",
        "policy_version": "2026.05",
        "as_of_date": "2026-05-12",
        "minimum_segment_score_run_count": 2,
        "maximum_average_score_spread": "15",
        "actor_id": "ops",
        "segments": [
            {
                "segment_id": "mandate_balanced",
                "segment_type": "MANDATE_TYPE",
                "display_name": "Balanced DPM Mandates",
                "score_run_ids": [balanced_1.score_run_id, balanced_2.score_run_id],
                "source_refs": [
                    {
                        "source_system": "lotus-core",
                        "source_type": "MandateTypeSegment",
                        "source_id": "mandate_balanced",
                    }
                ],
            },
            {
                "segment_id": "mandate_income",
                "segment_type": "MANDATE_TYPE",
                "display_name": "Income DPM Mandates",
                "score_run_ids": [income_1.score_run_id, income_2.score_run_id],
                "source_refs": [
                    {
                        "source_system": "lotus-core",
                        "source_type": "MandateTypeSegment",
                        "source_id": "mandate_income",
                    }
                ],
            },
        ],
    }
    try:
        with TestClient(app) as client:
            created = client.post(
                "/api/v1/rebalance/pm-operating-quality/fairness-analyses",
                json=request,
                headers={"X-Correlation-Id": "corr-pmq-fairness-create"},
            )
            fairness_analysis_id = created.json()["fairness_analysis"]["fairness_analysis_id"]
            fetched = client.get(
                f"/api/v1/rebalance/pm-operating-quality/fairness-analyses/{fairness_analysis_id}"
            )
            listed = client.get(
                "/api/v1/rebalance/pm-operating-quality/fairness-analyses",
                params={"policy_id": "pmq_sg_dpm", "state": "PENDING_REVIEW"},
            )
            missing = client.get("/api/v1/rebalance/pm-operating-quality/fairness-analyses/missing")
    finally:
        app.dependency_overrides.clear()

    assert created.status_code == 201
    assert created.json()["fairness_analysis"]["correlation_id"] == "corr-pmq-fairness-create"
    assert fetched.status_code == 200
    assert fetched.json()["fairness_analysis"]["fairness_analysis_id"] == fairness_analysis_id
    assert listed.status_code == 200
    assert listed.json()["count"] == 1
    assert listed.json()["fairness_analyses"][0]["fairness_analysis_id"] == fairness_analysis_id
    assert missing.status_code == 404
    assert missing.json()["detail"] == "PM_QUALITY_FAIRNESS_ANALYSIS_NOT_FOUND:missing"


def test_pm_operating_quality_api_fairness_analysis_fails_closed_for_bad_score_runs() -> None:
    score_run_repository = InMemoryDpmPmQualityScoreRunRepository()
    ready_run = _source_only_score_run(pm_id="pm_ready", score=Decimal("90"))
    mismatched_run = _source_only_score_run(pm_id="pm_mismatch", score=Decimal("91")).model_copy(
        update={"as_of_date": "2026-05-13"}
    )
    score_run_repository.save_score_run(score_run=ready_run)
    score_run_repository.save_score_run(score_run=mismatched_run)
    app.dependency_overrides[get_pm_quality_score_run_repository] = lambda: score_run_repository
    try:
        with TestClient(app) as client:
            missing = client.post(
                "/api/v1/rebalance/pm-operating-quality/fairness-analyses/preview",
                json={
                    "policy_id": "pmq_sg_dpm",
                    "policy_version": "2026.05",
                    "as_of_date": "2026-05-12",
                    "actor_id": "ops",
                    "segments": [
                        {
                            "segment_id": "region_sg",
                            "segment_type": "REGION",
                            "display_name": "Singapore",
                            "score_run_ids": [ready_run.score_run_id],
                        },
                        {
                            "segment_id": "region_hk",
                            "segment_type": "REGION",
                            "display_name": "Hong Kong",
                            "score_run_ids": ["missing"],
                        },
                    ],
                },
            )
            blocked = client.post(
                "/api/v1/rebalance/pm-operating-quality/fairness-analyses/preview",
                json={
                    "policy_id": "pmq_sg_dpm",
                    "policy_version": "2026.05",
                    "as_of_date": "2026-05-12",
                    "actor_id": "ops",
                    "minimum_segment_score_run_count": 1,
                    "segments": [
                        {
                            "segment_id": "region_sg",
                            "segment_type": "REGION",
                            "display_name": "Singapore",
                            "score_run_ids": [ready_run.score_run_id],
                        },
                        {
                            "segment_id": "region_hk",
                            "segment_type": "REGION",
                            "display_name": "Hong Kong",
                            "score_run_ids": [mismatched_run.score_run_id],
                        },
                    ],
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert missing.status_code == 404
    assert missing.json()["detail"] == "PM_QUALITY_SCORE_RUN_NOT_FOUND:missing"
    assert blocked.status_code == 200
    fairness_analysis = blocked.json()["fairness_analysis"]
    assert fairness_analysis["state"] == "BLOCKED"
    assert "PM_QUALITY_FAIRNESS_AS_OF_DATE_MISMATCH" in fairness_analysis["reason_codes"]


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

    fairness_path = "/api/v1/rebalance/pm-operating-quality/fairness-analyses/preview"
    assert fairness_path in schema["paths"]
    assert "200" in schema["paths"][fairness_path]["post"]["responses"]
    fairness_description = schema["paths"][fairness_path]["post"]["description"]
    assert all(marker in fairness_description for marker in ["What:", "When:", "How:"])
    assert "does not infer protected classes" in fairness_description

    fairness_create_path = "/api/v1/rebalance/pm-operating-quality/fairness-analyses"
    fairness_get_path = (
        "/api/v1/rebalance/pm-operating-quality/fairness-analyses/{fairness_analysis_id}"
    )
    assert fairness_create_path in schema["paths"]
    assert fairness_get_path in schema["paths"]
    assert "201" in schema["paths"][fairness_create_path]["post"]["responses"]
    assert "200" in schema["paths"][fairness_create_path]["get"]["responses"]
    assert (
        "stored fairness-analysis evidence"
        in schema["paths"][fairness_create_path]["get"]["description"]
    )
    assert "200" in schema["paths"][fairness_get_path]["get"]["responses"]
    assert (
        "does not recompute score runs" in schema["paths"][fairness_get_path]["get"]["description"]
    )
