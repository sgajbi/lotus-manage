from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from src.api.dependencies import get_outcome_review_repository
from src.api.dependencies import get_pm_quality_fairness_analysis_repository
from src.api.dependencies import get_pm_quality_policy_repository
from src.api.dependencies import get_pm_quality_review_action_repository
from src.api.dependencies import get_pm_quality_review_action_preview_application_service
from src.api.dependencies import get_pm_quality_score_run_repository
from src.api.dependencies import get_pm_quality_score_run_preview_application_service
from src.api.dependencies import get_pm_quality_summary_invocation_repository
from src.api.main import app
from src.api.routers import pm_operating_quality as pmq_router
from src.api.routers.pm_operating_quality_book_scope_builder import (
    _parse_pm_book_scope_preview_as_of_date,
    _pm_book_member_source_refs,
    _pm_book_scope_evidence_from_membership,
    _pm_book_scope_source_id,
)
from src.api.routers.pm_operating_quality_models import (
    _has_complete_pm_quality_policy_reference,
    _has_inline_pm_quality_policy,
    _has_pm_quality_policy_reference_fragment,
    _optional_summary_text,
    _required_summary_text,
    _validate_summary_content_hash,
    _validate_summary_invocation_required_ids,
    _validate_summary_invocation_required_workflow_fields,
    _validate_summary_workflow_pack_name,
)
from src.api.services.pm_operating_quality_service import (
    DpmPmOperatingQualityApplicationService,
)
from src.core.dpm_source_context import DpmCorePortfolioManagerBookMembershipResponse
from src.infrastructure.core_sourcing import DpmCoreResolverError, DpmCoreResolverUnavailableError
from src.infrastructure.outcomes import InMemoryDpmOutcomeReviewRepository
from src.infrastructure.pm_quality import (
    InMemoryDpmPmQualityFairnessAnalysisRepository,
    InMemoryDpmPmQualityPolicyRepository,
    InMemoryDpmPmQualityReviewActionRepository,
    InMemoryDpmPmQualityScoreRunRepository,
    InMemoryDpmPmQualitySummaryInvocationRepository,
)
from src.core.pm_quality import (
    DpmPmQualityFairnessAnalysisConflictError,
    DpmPmOperatingQualityPolicy,
    DpmPmOperatingQualityScoreRun,
    DpmPmQualityEvidenceItem,
    DpmPmQualityGovernanceApproval,
    DpmPmQualityReviewAction,
    DpmPmQualityReviewActionConflictError,
    DpmPmQualityScoreRunConflictError,
    DpmPmQualitySummaryInvocationConflictError,
    DpmPmQualityWeight,
    build_pm_operating_quality_score_run,
)
from tests.unit.infrastructure.test_outcome_review_repository import _review

ROOT = Path(__file__).resolve().parents[3]


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


def _trusted_pm_quality_headers(
    *,
    actor_id: str = "ops",
    tenant_id: str = "tenant-sg",
    capabilities: str = "pm_quality.write",
) -> dict[str, str]:
    return {
        "X-Actor-Id": actor_id,
        "X-Tenant-Id": tenant_id,
        "X-Role": "operator",
        "X-Correlation-Id": "corr-trusted",
        "X-Service-Identity": "lotus-gateway",
        "X-Capabilities": capabilities,
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


def _assert_pm_quality_problem(
    response,
    *,
    status_code: int,
    reason_code: str,
    correlation_id: str | None = None,
) -> dict:
    assert response.status_code == status_code
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert body["type"] == "about:blank"
    assert body["status"] == status_code
    assert body["reasonCode"] == reason_code
    assert isinstance(body["detail"], str)
    assert body["correlationId"] == response.headers["X-Correlation-Id"]
    if correlation_id is not None:
        assert body["correlationId"] == correlation_id
    assert body["instance"].startswith("/api/v1/rebalance/pm-operating-quality")
    return body


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


def test_pm_book_scope_router_helpers_preserve_source_id_fallbacks_and_member_limit() -> None:
    snapshot_membership = DpmCorePortfolioManagerBookMembershipResponse.model_validate(
        _pm_book_membership_payload()
    )
    batch_membership = snapshot_membership.model_copy(update={"snapshot_id": ""}, deep=True)
    fallback_membership = batch_membership.model_copy(
        update={"source_batch_fingerprint": None},
        deep=True,
    )
    capped_membership = DpmCorePortfolioManagerBookMembershipResponse.model_validate(
        {
            **_pm_book_membership_payload(),
            "members": [
                {
                    "portfolio_id": f"PF_{index:03d}",
                    "client_id": f"client_{index:03d}",
                    "booking_center_code": "Singapore",
                    "portfolio_type": "DPM",
                    "status": "ACTIVE",
                    "open_date": "2023-01-03",
                    "base_currency": "USD",
                    "source_record_id": f"pm-book:{index:03d}",
                }
                for index in range(105)
            ],
        }
    )

    assert _pm_book_scope_source_id(snapshot_membership) == "pm-book-snapshot-20260512"
    assert _pm_book_scope_source_id(batch_membership) == "sha256:pm-book"
    assert _pm_book_scope_source_id(fallback_membership) == "pm_book:pm_001:2026-05-12"
    assert len(_pm_book_member_source_refs(capped_membership)) == 100
    evidence = _pm_book_scope_evidence_from_membership(capped_membership)
    assert evidence.returned_portfolio_count == 105
    assert evidence.member_portfolio_ids[-1] == "PF_099"
    assert evidence.source_refs[0].source_type == "PortfolioManagerBookMembership"


def test_pm_book_scope_router_date_helper_raises_http_422_for_invalid_date() -> None:
    assert _parse_pm_book_scope_preview_as_of_date("2026-05-12").isoformat() == "2026-05-12"
    with pytest.raises(HTTPException) as exc_info:
        _parse_pm_book_scope_preview_as_of_date("bad-date")
    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "INVALID_AS_OF_DATE"


def test_pm_operating_quality_request_models_normalize_and_validate_scope_edges() -> None:
    scope = pmq_router.DpmPmOperatingQualityPmBookScopeRequest(
        portfolio_types=[" dpm ", "DISCRETIONARY"]
    )
    assert scope.portfolio_types == ["DPM", "DISCRETIONARY"]

    with pytest.raises(ValueError, match="portfolio_types must contain at least one value"):
        pmq_router.DpmPmOperatingQualityPmBookScopeRequest(portfolio_types=[" "])
    with pytest.raises(ValueError, match="either inline policy or persisted policy reference"):
        pmq_router.DpmPmOperatingQualityScorePreviewRequest(
            **{
                **_request(),
                "policy_id": "pmq_sg_dpm",
                "policy_version": "2026.05",
            }
        )
    request = _request()
    request.pop("policy")
    with pytest.raises(ValueError, match="both policy_id and policy_version"):
        pmq_router.DpmPmOperatingQualityScorePreviewRequest(**request)
    with pytest.raises(ValueError, match="score_run_ids must contain at least one value"):
        pmq_router.DpmPmQualityFairnessSegmentRequest(
            segment_id="region_sg",
            segment_type="REGION",
            display_name="Singapore",
            score_run_ids=[" "],
        )
    with pytest.raises(ValueError, match="score_run_ids must be unique"):
        pmq_router.DpmPmQualityFairnessSegmentRequest(
            segment_id="region_sg",
            segment_type="REGION",
            display_name="Singapore",
            score_run_ids=["pmq_1", "pmq_1"],
        )
    segment = pmq_router.DpmPmQualityFairnessSegmentRequest(
        segment_id="region_sg",
        segment_type="REGION",
        display_name="Singapore",
        score_run_ids=["pmq_1"],
    )
    with pytest.raises(ValueError, match="segment_id values must be unique"):
        pmq_router.DpmPmQualityFairnessPreviewRequest(
            policy_id="pmq_sg_dpm",
            policy_version="2026.05",
            as_of_date="2026-05-12",
            actor_id="ops",
            segments=[segment, segment],
        )


def test_pm_operating_quality_policy_selection_helpers_classify_policy_inputs() -> None:
    assert _has_inline_pm_quality_policy(_policy())
    assert _has_inline_pm_quality_policy(None) is False
    assert _has_pm_quality_policy_reference_fragment(
        policy_id="pmq_sg_dpm",
        policy_version=None,
    )
    assert _has_pm_quality_policy_reference_fragment(
        policy_id=None,
        policy_version="2026.05",
    )
    assert _has_pm_quality_policy_reference_fragment(policy_id=None, policy_version=None) is False
    assert _has_complete_pm_quality_policy_reference(
        policy_id="pmq_sg_dpm",
        policy_version="2026.05",
    )
    assert (
        _has_complete_pm_quality_policy_reference(
            policy_id="pmq_sg_dpm",
            policy_version=None,
        )
        is False
    )
    assert (
        _has_complete_pm_quality_policy_reference(
            policy_id="",
            policy_version="2026.05",
        )
        is False
    )
    assert (
        _has_complete_pm_quality_policy_reference(
            policy_id="pmq_sg_dpm",
            policy_version="",
        )
        is False
    )


def test_pm_operating_quality_router_private_edges_fail_closed() -> None:
    app.dependency_overrides[get_outcome_review_repository] = lambda: (
        InMemoryDpmOutcomeReviewRepository()
    )
    try:
        with TestClient(app) as client:
            missing_policy_ref = client.post(
                "/api/v1/rebalance/pm-operating-quality/score-runs/preview",
                json={
                    "pm_id": "pm_001",
                    "book_id": "sg_dpm_book",
                    "as_of_date": "2026-05-12",
                    "evidence_items": [],
                    "outcome_review_ids": [],
                    "actor_id": "ops",
                },
            )
            invalid_book_scope_date = client.post(
                "/api/v1/rebalance/pm-operating-quality/score-runs/preview",
                json={
                    "pm_id": "pm_001",
                    "book_id": "sg_dpm_book",
                    "as_of_date": "not-a-date",
                    "policy": _policy(),
                    "evidence_items": [],
                    "outcome_review_ids": [],
                    "actor_id": "ops",
                    "pm_book_scope": {
                        "booking_center_code": "Singapore",
                    },
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert missing_policy_ref.status_code == 422
    missing_policy_detail = missing_policy_ref.json()["detail"]
    assert any(
        "Supply inline policy or both policy_id and policy_version" in error["msg"]
        for error in missing_policy_detail
    )
    assert invalid_book_scope_date.status_code == 422
    _assert_pm_quality_problem(
        invalid_book_scope_date,
        status_code=422,
        reason_code="INVALID_AS_OF_DATE",
    )


def test_pm_operating_quality_authz_rejects_missing_identity_and_capability(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENTERPRISE_ENFORCE_AUTHZ", "true")
    monkeypatch.setenv(
        "ENTERPRISE_CAPABILITY_RULES_JSON",
        '{"POST /api/v1/rebalance/pm-operating-quality": "pm_quality.write"}',
    )
    with TestClient(app) as client:
        missing_identity = client.post(
            "/api/v1/rebalance/pm-operating-quality/score-runs/preview",
            json=_scope_request(),
        )
        missing_capability = client.post(
            "/api/v1/rebalance/pm-operating-quality/score-runs/preview",
            headers=_trusted_pm_quality_headers(capabilities="pm_quality.read"),
            json=_scope_request(),
        )

    assert missing_identity.status_code == 403
    assert missing_identity.headers["content-type"].startswith("application/problem+json")
    assert missing_identity.json()["reasonCode"].startswith("missing_headers:")
    assert missing_capability.status_code == 403
    assert missing_capability.json()["reasonCode"] == "missing_capability:pm_quality.write"


def test_pm_operating_quality_write_authz_rejects_body_header_actor_and_tenant_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENTERPRISE_ENFORCE_AUTHZ", "true")
    with TestClient(app) as client:
        actor_mismatch = client.post(
            "/api/v1/rebalance/pm-operating-quality/score-runs/preview",
            headers=_trusted_pm_quality_headers(actor_id="trusted-ops"),
            json=_scope_request(),
        )
        tenant_request = _scope_request()
        tenant_request["actor_id"] = "trusted-ops"
        tenant_request["pm_book_scope"] = {
            "tenant_id": "tenant-other",
            "booking_center_code": "Singapore",
            "portfolio_types": ["DPM"],
        }
        tenant_mismatch = client.post(
            "/api/v1/rebalance/pm-operating-quality/score-runs/preview",
            headers=_trusted_pm_quality_headers(actor_id="trusted-ops", tenant_id="tenant-sg"),
            json=tenant_request,
        )

    _assert_pm_quality_problem(
        actor_mismatch,
        status_code=403,
        reason_code="PM_QUALITY_TRUSTED_ACTOR_MISMATCH",
    )
    _assert_pm_quality_problem(
        tenant_mismatch,
        status_code=403,
        reason_code="PM_QUALITY_TRUSTED_TENANT_MISMATCH",
    )


def test_pm_operating_quality_write_authz_accepts_trusted_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENTERPRISE_ENFORCE_AUTHZ", "true")
    request = _scope_request()
    request["actor_id"] = "ops"
    app.dependency_overrides[get_outcome_review_repository] = lambda: (
        InMemoryDpmOutcomeReviewRepository()
    )

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/rebalance/pm-operating-quality/score-runs/preview",
                headers=_trusted_pm_quality_headers(actor_id="ops"),
                json=request,
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["score_run"]["generated_by"] == "ops"


def test_pm_operating_quality_write_routes_use_trusted_identity_guard() -> None:
    route_files = {
        "score": (
            ROOT / "src/api/routers/pm_operating_quality_score_run_routes.py",
            "score_run_request_with_trusted_identity",
        ),
        "fairness": (
            ROOT / "src/api/routers/pm_operating_quality_fairness_routes.py",
            "fairness_request_with_trusted_identity",
        ),
        "review": (
            ROOT / "src/api/routers/pm_operating_quality_review_action_routes.py",
            "review_action_request_with_trusted_identity",
        ),
        "summary": (
            ROOT / "src/api/routers/pm_operating_quality_summary_routes.py",
            "summary_invocation_request_with_trusted_identity",
        ),
    }

    for family, (route_file, guard_name) in route_files.items():
        text = route_file.read_text(encoding="utf-8")
        assert guard_name in text, family


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


class _ConflictingScoreRunRepository(InMemoryDpmPmQualityScoreRunRepository):
    def save_score_run(self, *, score_run: DpmPmOperatingQualityScoreRun) -> None:
        raise DpmPmQualityScoreRunConflictError("PM_QUALITY_SCORE_RUN_IMMUTABLE_CONFLICT")


class _ConflictingFairnessAnalysisRepository(InMemoryDpmPmQualityFairnessAnalysisRepository):
    def save_fairness_analysis(self, *, analysis: Any) -> None:
        raise DpmPmQualityFairnessAnalysisConflictError(
            "PM_QUALITY_FAIRNESS_ANALYSIS_IMMUTABLE_CONFLICT"
        )


class _ConflictingReviewActionRepository(InMemoryDpmPmQualityReviewActionRepository):
    def save_review_action(self, *, action: Any) -> None:
        raise DpmPmQualityReviewActionConflictError("PM_QUALITY_REVIEW_ACTION_IMMUTABLE_CONFLICT")


class _ConflictingSummaryInvocationRepository(InMemoryDpmPmQualitySummaryInvocationRepository):
    def save_summary_invocation(self, *, invocation: Any) -> None:
        raise DpmPmQualitySummaryInvocationConflictError(
            "PM_QUALITY_SUMMARY_INVOCATION_IMMUTABLE_CONFLICT"
        )


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


def test_pm_operating_quality_api_materializes_pm_book_scope(
    _pm_quality_policy_repository_override: InMemoryDpmPmQualityPolicyRepository,
) -> None:
    repository = InMemoryDpmOutcomeReviewRepository()
    repository.save_outcome_review(review=_review(), retention_expires_at=None)
    resolver = _PmBookResolver(_pm_book_membership_payload())
    app.dependency_overrides[get_pm_quality_score_run_preview_application_service] = lambda: (
        DpmPmOperatingQualityApplicationService(
            outcome_review_repository=repository,
            policy_repository=_pm_quality_policy_repository_override,
            core_resolver_factory=lambda: resolver,
        )
    )
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
    _pm_quality_policy_repository_override: InMemoryDpmPmQualityPolicyRepository,
    resolver,
    expected_status: int,
    expected_code: str,
) -> None:
    repository = InMemoryDpmOutcomeReviewRepository()
    repository.save_outcome_review(review=_review(), retention_expires_at=None)
    app.dependency_overrides[get_pm_quality_score_run_preview_application_service] = lambda: (
        DpmPmOperatingQualityApplicationService(
            outcome_review_repository=repository,
            policy_repository=_pm_quality_policy_repository_override,
            core_resolver_factory=lambda: resolver,
        )
    )
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

    _assert_pm_quality_problem(
        response,
        status_code=expected_status,
        reason_code=expected_code,
    )


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
    _assert_pm_quality_problem(
        missing,
        status_code=404,
        reason_code="PM_QUALITY_POLICY_NOT_FOUND",
    )


def test_pm_operating_quality_api_materializes_policy_scope_context() -> None:
    policy_repository = InMemoryDpmPmQualityPolicyRepository()
    score_run_repository = InMemoryDpmPmQualityScoreRunRepository()
    app.dependency_overrides[get_pm_quality_policy_repository] = lambda: policy_repository
    app.dependency_overrides[get_pm_quality_score_run_repository] = lambda: score_run_repository
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
            mixed_undated_request = _scope_request()
            mixed_undated_request["evidence_items"][1]["source_refs"][0].pop("source_version")
            mixed_undated = client.post(
                "/api/v1/rebalance/pm-operating-quality/score-runs/preview",
                json=mixed_undated_request,
            )
            invalid_date_request = _scope_request()
            invalid_date_request["evidence_items"][0]["source_refs"][0]["source_version"] = (
                "2026.05"
            )
            invalid_date = client.post(
                "/api/v1/rebalance/pm-operating-quality/score-runs",
                json=invalid_date_request,
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
    _assert_pm_quality_problem(
        stale,
        status_code=422,
        reason_code="PM_QUALITY_EVIDENCE_OUTSIDE_LOOKBACK_WINDOW",
    )
    _assert_pm_quality_problem(
        mixed_undated,
        status_code=422,
        reason_code="PM_QUALITY_LOOKBACK_WINDOW_EVIDENCE_DATE_REQUIRED",
    )
    _assert_pm_quality_problem(
        invalid_date,
        status_code=422,
        reason_code="PM_QUALITY_EVIDENCE_AS_OF_DATE_INVALID",
    )


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
    _assert_pm_quality_problem(
        conflict,
        status_code=409,
        reason_code="PM_QUALITY_POLICY_IMMUTABLE_CONFLICT",
    )
    _assert_pm_quality_problem(
        mismatch,
        status_code=422,
        reason_code="PM_QUALITY_POLICY_PATH_BODY_MISMATCH",
    )
    _assert_pm_quality_problem(
        missing_policy_ref,
        status_code=404,
        reason_code="PM_QUALITY_POLICY_NOT_FOUND",
    )
    _assert_pm_quality_problem(
        missing_ref,
        status_code=404,
        reason_code="OUTCOME_REVIEW_NOT_FOUND",
    )


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
    if response.headers["content-type"].startswith("application/problem+json"):
        _assert_pm_quality_problem(
            response,
            status_code=422,
            reason_code=expected_detail,
        )
    else:
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
    _assert_pm_quality_problem(
        missing,
        status_code=404,
        reason_code="PM_QUALITY_SCORE_RUN_NOT_FOUND",
    )


def test_pm_operating_quality_api_maps_persistence_conflicts_to_409() -> None:
    outcome_repository = InMemoryDpmOutcomeReviewRepository()
    outcome_repository.save_outcome_review(review=_review(), retention_expires_at=None)
    app.dependency_overrides[get_outcome_review_repository] = lambda: outcome_repository
    app.dependency_overrides[get_pm_quality_score_run_repository] = lambda: (
        _ConflictingScoreRunRepository()
    )
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/rebalance/pm-operating-quality/score-runs",
                json=_request(),
            )
    finally:
        app.dependency_overrides.clear()

    _assert_pm_quality_problem(
        response,
        status_code=409,
        reason_code="PM_QUALITY_SCORE_RUN_IMMUTABLE_CONFLICT",
    )


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
    _assert_pm_quality_problem(
        missing,
        status_code=404,
        reason_code="PM_QUALITY_FAIRNESS_ANALYSIS_NOT_FOUND",
    )


def test_pm_operating_quality_api_creates_gets_and_lists_review_actions() -> None:
    score_repository = InMemoryDpmPmQualityScoreRunRepository()
    fairness_repository = InMemoryDpmPmQualityFairnessAnalysisRepository()
    review_repository = InMemoryDpmPmQualityReviewActionRepository()
    score_run = _source_only_score_run(pm_id="pm_001", score=Decimal("91"))
    score_repository.save_score_run(score_run=score_run)
    app.dependency_overrides[get_pm_quality_score_run_repository] = lambda: score_repository
    app.dependency_overrides[get_pm_quality_fairness_analysis_repository] = lambda: (
        fairness_repository
    )
    app.dependency_overrides[get_pm_quality_review_action_repository] = lambda: review_repository

    try:
        with TestClient(app) as client:
            request = {
                "target_type": "SCORE_RUN",
                "target_id": score_run.score_run_id,
                "action_type": "REQUEST_EVIDENCE_REMEDIATION",
                "review_action_ref": "PMQ-REVIEW-2026-05-001",
                "review_reason": "Evidence remediation required before supervisory closure.",
                "remediation_due_date": "2026-06-15",
                "actor_id": "ops",
                "source_refs": [
                    {
                        "source_system": "bank-governance",
                        "source_type": "PM_QUALITY_REVIEW_MINUTES",
                        "source_id": "pmq-review-minutes-001",
                    }
                ],
            }
            preview = client.post(
                "/api/v1/rebalance/pm-operating-quality/review-actions/preview",
                json=request,
                headers={"X-Correlation-Id": "corr-pmq-review-preview"},
            )
            created = client.post(
                "/api/v1/rebalance/pm-operating-quality/review-actions",
                json=request,
                headers={"X-Correlation-Id": "corr-pmq-review-create"},
            )
            review_action_id = created.json()["review_action"]["review_action_id"]
            fetched = client.get(
                f"/api/v1/rebalance/pm-operating-quality/review-actions/{review_action_id}"
            )
            listed = client.get(
                "/api/v1/rebalance/pm-operating-quality/review-actions"
                "?target_type=SCORE_RUN&action_state=REVIEW_REQUIRED"
            )
            missing_target = client.post(
                "/api/v1/rebalance/pm-operating-quality/review-actions/preview",
                json={**request, "target_id": "missing"},
            )
            missing_action = client.get(
                "/api/v1/rebalance/pm-operating-quality/review-actions/missing"
            )
    finally:
        app.dependency_overrides.clear()

    assert preview.status_code == 200
    assert preview.json()["review_action"]["target_content_hash"] == score_run.content_hash
    assert preview.json()["review_action"]["action_state"] == "REVIEW_REQUIRED"
    assert created.status_code == 201
    assert created.json()["review_action"]["correlation_id"] == "corr-pmq-review-create"
    assert "NO_APPROVAL_WORKFLOW" in created.json()["review_action"]["operating_boundaries"]
    assert "NO_PM_RANKING" in created.json()["review_action"]["operating_boundaries"]
    approval_boundary = created.json()["review_action"]["approval_workflow_boundary"]
    assert approval_boundary["boundary_id"] == "PM_QUALITY_APPROVAL_WORKFLOW_BOUNDARY"
    assert approval_boundary["approval_workflow_projected"] is False
    assert approval_boundary["trade_approval_projected"] is False
    assert "trade_approval" in approval_boundary["blocked_capabilities"]
    assert approval_boundary["required_source_product"] == "PmQualityApprovalWorkflowRecord:v1"
    assert approval_boundary["content_hash"].startswith("sha256:")
    assert fetched.status_code == 200
    assert fetched.json()["review_action"]["review_action_id"] == review_action_id
    assert listed.status_code == 200
    assert listed.json()["count"] == 1
    assert listed.json()["review_actions"][0]["review_action_id"] == review_action_id
    _assert_pm_quality_problem(
        missing_target,
        status_code=404,
        reason_code="PM_QUALITY_SCORE_RUN_NOT_FOUND",
    )
    _assert_pm_quality_problem(
        missing_action,
        status_code=404,
        reason_code="PM_QUALITY_REVIEW_ACTION_NOT_FOUND",
    )


def test_pm_operating_quality_api_review_action_validation_conflict_and_failure_edges(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    score_repository = InMemoryDpmPmQualityScoreRunRepository()
    score_run = _source_only_score_run(pm_id="pm_001", score=Decimal("91"))
    score_repository.save_score_run(score_run=score_run)
    app.dependency_overrides[get_pm_quality_score_run_repository] = lambda: score_repository
    app.dependency_overrides[get_pm_quality_fairness_analysis_repository] = lambda: (
        InMemoryDpmPmQualityFairnessAnalysisRepository()
    )
    app.dependency_overrides[get_pm_quality_review_action_repository] = lambda: (
        _ConflictingReviewActionRepository()
    )

    request = {
        "target_type": "SCORE_RUN",
        "target_id": score_run.score_run_id,
        "action_type": "ACKNOWLEDGE",
        "review_action_ref": "PMQ-REVIEW-2026-05-001",
        "review_reason": "Reviewed for supervisory closure.",
        "actor_id": "ops",
    }
    try:
        with TestClient(app) as client:
            bad_due_date = client.post(
                "/api/v1/rebalance/pm-operating-quality/review-actions/preview",
                json={**request, "remediation_due_date": "not-a-date"},
            )
            missing_fairness_target = client.post(
                "/api/v1/rebalance/pm-operating-quality/review-actions/preview",
                json={**request, "target_type": "FAIRNESS_ANALYSIS", "target_id": "missing"},
            )
            conflict = client.post(
                "/api/v1/rebalance/pm-operating-quality/review-actions",
                json=request,
            )

            def _raise_value_error(**_kwargs: object) -> None:
                raise ValueError("PM_QUALITY_REVIEW_ACTION_TARGET_TYPE_MISMATCH")

            app.dependency_overrides[get_pm_quality_review_action_preview_application_service] = (
                lambda: DpmPmOperatingQualityApplicationService(
                    score_run_repository=score_repository,
                    fairness_repository=InMemoryDpmPmQualityFairnessAnalysisRepository(),
                    review_action_builder=_raise_value_error,
                )
            )
            invalid_target = client.post(
                "/api/v1/rebalance/pm-operating-quality/review-actions/preview",
                json=request,
            )
    finally:
        app.dependency_overrides.clear()

    assert bad_due_date.status_code == 422
    _assert_pm_quality_problem(
        missing_fairness_target,
        status_code=404,
        reason_code="PM_QUALITY_FAIRNESS_ANALYSIS_NOT_FOUND",
    )
    _assert_pm_quality_problem(
        conflict,
        status_code=409,
        reason_code="PM_QUALITY_REVIEW_ACTION_IMMUTABLE_CONFLICT",
    )
    _assert_pm_quality_problem(
        invalid_target,
        status_code=422,
        reason_code="PM_QUALITY_REVIEW_ACTION_TARGET_TYPE_MISMATCH",
    )


def test_pm_operating_quality_api_creates_gets_and_lists_summary_invocations() -> None:
    score_repository = InMemoryDpmPmQualityScoreRunRepository()
    review_repository = InMemoryDpmPmQualityReviewActionRepository()
    summary_repository = InMemoryDpmPmQualitySummaryInvocationRepository()
    score_run = _source_only_score_run(pm_id="pm_001", score=Decimal("91"))
    score_repository.save_score_run(score_run=score_run)
    app.dependency_overrides[get_pm_quality_score_run_repository] = lambda: score_repository
    app.dependency_overrides[get_pm_quality_fairness_analysis_repository] = lambda: (
        InMemoryDpmPmQualityFairnessAnalysisRepository()
    )
    app.dependency_overrides[get_pm_quality_review_action_repository] = lambda: review_repository
    app.dependency_overrides[get_pm_quality_summary_invocation_repository] = lambda: (
        summary_repository
    )

    review_action_request = {
        "target_type": "SCORE_RUN",
        "target_id": score_run.score_run_id,
        "action_type": "ACKNOWLEDGE",
        "review_action_ref": "PMQ-REVIEW-2026-05-001",
        "review_reason": "Reviewed and acknowledged for support-summary evidence.",
        "actor_id": "ops",
    }

    request = {
        "score_run_id": score_run.score_run_id,
        "review_action_id": "placeholder",
        "invocation_state": "COMPLETED",
        "summary_ref": "PMQ-SUMMARY-2026-05-001",
        "workflow_pack_name": "pm_quality_summary.pack",
        "workflow_pack_version": "v1",
        "workflow_run_id": "pmq-summary-run-001",
        "summary_artifact_ref": "pmq-summary-artifact-001",
        "summary_content_hash": "sha256:pmq-summary",
        "requested_by": "ops",
        "source_refs": [
            {
                "source_system": "lotus-ai",
                "source_type": "pm_quality_summary.pack",
                "source_id": "pmq-summary-run-001",
                "source_version": "v1",
                "content_hash": "sha256:pmq-summary",
            }
        ],
    }
    try:
        with TestClient(app) as client:
            review_action = client.post(
                "/api/v1/rebalance/pm-operating-quality/review-actions",
                json=review_action_request,
                headers={"X-Correlation-Id": "corr-review"},
            )
            assert review_action.status_code == 201
            review_action_id = review_action.json()["review_action"]["review_action_id"]
            request["review_action_id"] = review_action_id
            preview = client.post(
                "/api/v1/rebalance/pm-operating-quality/summary-invocations/preview",
                json=request,
                headers={"X-Correlation-Id": "corr-pmq-summary-preview"},
            )
            created = client.post(
                "/api/v1/rebalance/pm-operating-quality/summary-invocations",
                json=request,
                headers={"X-Correlation-Id": "corr-pmq-summary-create"},
            )
            summary_invocation_id = created.json()["summary_invocation"]["summary_invocation_id"]
            fetched = client.get(
                "/api/v1/rebalance/pm-operating-quality/summary-invocations/"
                f"{summary_invocation_id}"
            )
            listed = client.get(
                "/api/v1/rebalance/pm-operating-quality/summary-invocations",
                params={"score_run_id": score_run.score_run_id, "invocation_state": "COMPLETED"},
            )
            missing_score_run = client.post(
                "/api/v1/rebalance/pm-operating-quality/summary-invocations/preview",
                json={**request, "score_run_id": "missing"},
            )
            requested_with_result = client.post(
                "/api/v1/rebalance/pm-operating-quality/summary-invocations/preview",
                json={**request, "invocation_state": "REQUESTED"},
            )
            completed_without_artifact = client.post(
                "/api/v1/rebalance/pm-operating-quality/summary-invocations/preview",
                json={
                    **request,
                    "summary_artifact_ref": None,
                    "summary_content_hash": "sha256:pmq-summary",
                },
            )
            failed_without_reason = client.post(
                "/api/v1/rebalance/pm-operating-quality/summary-invocations/preview",
                json={
                    **request,
                    "invocation_state": "FAILED",
                    "summary_artifact_ref": None,
                    "summary_content_hash": None,
                },
            )
            missing_invocation = client.get(
                "/api/v1/rebalance/pm-operating-quality/summary-invocations/missing"
            )
    finally:
        app.dependency_overrides.clear()

    assert preview.status_code == 200
    assert preview.json()["summary_invocation"]["score_run_content_hash"] == score_run.content_hash
    assert created.status_code == 201
    summary_invocation = created.json()["summary_invocation"]
    assert summary_invocation["correlation_id"] == "corr-pmq-summary-create"
    assert summary_invocation["summary_artifact_ref"] == "pmq-summary-artifact-001"
    assert "NO_SUMMARY_TEXT_STORAGE" in summary_invocation["operating_boundaries"]
    assert "NO_SUMMARY_TEXT_EXPOSURE" in summary_invocation["operating_boundaries"]
    assert "NO_DOWNSTREAM_SUMMARY_UX_CLAIM" in summary_invocation["operating_boundaries"]
    summary_text_boundary = summary_invocation["summary_text_boundary"]
    assert summary_text_boundary["boundary_id"] == "PM_QUALITY_SUMMARY_TEXT_BOUNDARY"
    assert summary_text_boundary["summary_text_stored"] is False
    assert summary_text_boundary["summary_text_exposed"] is False
    assert summary_text_boundary["downstream_ux_projected"] is False
    assert "summary_text_rendering" in summary_text_boundary["blocked_capabilities"]
    assert summary_text_boundary["required_source_product"] == (
        "PmQualityGeneratedSummaryArtifact:v1"
    )
    assert summary_text_boundary["content_hash"].startswith("sha256:")
    assert "summary_text_storage" in summary_invocation["forbidden_uses"]
    assert fetched.status_code == 200
    assert fetched.json()["summary_invocation"]["summary_invocation_id"] == summary_invocation_id
    assert listed.status_code == 200
    assert listed.json()["count"] == 1
    assert listed.json()["summary_invocations"][0]["summary_invocation_id"] == summary_invocation_id
    _assert_pm_quality_problem(
        missing_score_run,
        status_code=404,
        reason_code="PM_QUALITY_SCORE_RUN_NOT_FOUND",
    )
    _assert_pm_quality_problem(
        requested_with_result,
        status_code=422,
        reason_code="PM_QUALITY_SUMMARY_REQUESTED_RESULT_EVIDENCE_FORBIDDEN",
    )
    _assert_pm_quality_problem(
        completed_without_artifact,
        status_code=422,
        reason_code="PM_QUALITY_SUMMARY_COMPLETED_ARTIFACT_REF_REQUIRED",
    )
    _assert_pm_quality_problem(
        failed_without_reason,
        status_code=422,
        reason_code="PM_QUALITY_SUMMARY_FAILED_REASON_CODE_REQUIRED",
    )
    _assert_pm_quality_problem(
        missing_invocation,
        status_code=404,
        reason_code="PM_QUALITY_SUMMARY_INVOCATION_NOT_FOUND",
    )


@pytest.mark.parametrize(
    ("patch", "expected_detail"),
    [
        ({"score_run_id": "   "}, "score_run_id and review_action_id must be non-empty"),
        (
            {"summary_ref": "   "},
            "summary_ref, workflow_pack_version, and requested_by must be non-empty",
        ),
        ({"summary_content_hash": "not-a-hash"}, "summary_content_hash must start with sha256:"),
        (
            {"workflow_pack_name": "unsupported.pack"},
            "workflow_pack_name must be pm_quality_summary.pack",
        ),
    ],
)
def test_pm_operating_quality_api_summary_invocation_request_validation_edges(
    patch: dict[str, object],
    expected_detail: str,
) -> None:
    with pytest.raises(ValueError, match=expected_detail):
        pmq_router.DpmPmQualitySummaryInvocationRequest.model_validate(
            {
                "score_run_id": "score-run-001",
                "review_action_id": "review-action-001",
                "summary_ref": "PMQ-SUMMARY-2026-05-001",
                "workflow_pack_name": "pm_quality_summary.pack",
                "workflow_pack_version": "v1",
                "requested_by": "ops",
                **patch,
            }
        )


def test_pm_operating_quality_summary_invocation_text_helpers_normalize_values() -> None:
    assert _required_summary_text(" score-run-001 ") == "score-run-001"
    assert _optional_summary_text(" workflow-run-001 ") == "workflow-run-001"
    assert _optional_summary_text("   ") is None
    assert _optional_summary_text(None) is None


def test_pm_operating_quality_summary_invocation_helper_validation_edges() -> None:
    with pytest.raises(ValueError, match="score_run_id and review_action_id must be non-empty"):
        _validate_summary_invocation_required_ids(
            score_run_id="score-run-001",
            review_action_id="",
        )

    with pytest.raises(
        ValueError,
        match="summary_ref, workflow_pack_version, and requested_by must be non-empty",
    ):
        _validate_summary_invocation_required_workflow_fields(
            summary_ref="PMQ-SUMMARY-2026-05-001",
            workflow_pack_version="",
            requested_by="ops",
        )

    with pytest.raises(ValueError, match="summary_content_hash must start with sha256:"):
        _validate_summary_content_hash("not-a-hash")

    with pytest.raises(ValueError, match="workflow_pack_name must be pm_quality_summary.pack"):
        _validate_summary_workflow_pack_name("unsupported.pack")

    _validate_summary_content_hash("sha256:abc")
    _validate_summary_content_hash(None)
    _validate_summary_workflow_pack_name("pm_quality_summary.pack")


def test_pm_operating_quality_api_summary_invocation_missing_review_mismatch_and_conflict() -> None:
    score_repository = InMemoryDpmPmQualityScoreRunRepository()
    review_repository = InMemoryDpmPmQualityReviewActionRepository()
    score_run = _source_only_score_run(pm_id="pm_001", score=Decimal("91"))
    score_repository.save_score_run(score_run=score_run)
    app.dependency_overrides[get_pm_quality_score_run_repository] = lambda: score_repository
    app.dependency_overrides[get_pm_quality_fairness_analysis_repository] = lambda: (
        InMemoryDpmPmQualityFairnessAnalysisRepository()
    )
    app.dependency_overrides[get_pm_quality_review_action_repository] = lambda: review_repository
    app.dependency_overrides[get_pm_quality_summary_invocation_repository] = lambda: (
        _ConflictingSummaryInvocationRepository()
    )
    review_action_request = {
        "target_type": "SCORE_RUN",
        "target_id": score_run.score_run_id,
        "action_type": "ACKNOWLEDGE",
        "review_action_ref": "PMQ-REVIEW-2026-05-001",
        "review_reason": "Reviewed and acknowledged for support-summary evidence.",
        "actor_id": "ops",
    }

    request = {
        "score_run_id": score_run.score_run_id,
        "review_action_id": "placeholder",
        "summary_ref": "PMQ-SUMMARY-2026-05-001",
        "workflow_pack_name": "pm_quality_summary.pack",
        "workflow_pack_version": "v1",
        "requested_by": "ops",
    }
    try:
        with TestClient(app) as client:
            review_action = client.post(
                "/api/v1/rebalance/pm-operating-quality/review-actions",
                json=review_action_request,
                headers={"X-Correlation-Id": "corr-review"},
            )
            assert review_action.status_code == 201
            review_action_payload = review_action.json()["review_action"]
            mismatched_review_action = DpmPmQualityReviewAction.model_validate(
                review_action_payload
            )
            mismatched_review_action = mismatched_review_action.model_copy(
                update={
                    "review_action_id": "pmq_review_mismatch",
                    "target_content_hash": "sha256:other",
                }
            )
            review_repository.save_review_action(action=mismatched_review_action)

            request["review_action_id"] = review_action_payload["review_action_id"]
            missing_review_action = client.post(
                "/api/v1/rebalance/pm-operating-quality/summary-invocations/preview",
                json={**request, "review_action_id": "missing"},
            )
            mismatched_review_action_response = client.post(
                "/api/v1/rebalance/pm-operating-quality/summary-invocations/preview",
                json={**request, "review_action_id": mismatched_review_action.review_action_id},
            )
            conflict = client.post(
                "/api/v1/rebalance/pm-operating-quality/summary-invocations",
                json=request,
            )
    finally:
        app.dependency_overrides.clear()

    _assert_pm_quality_problem(
        missing_review_action,
        status_code=404,
        reason_code="PM_QUALITY_REVIEW_ACTION_NOT_FOUND",
    )
    _assert_pm_quality_problem(
        mismatched_review_action_response,
        status_code=422,
        reason_code="PM_QUALITY_SUMMARY_REVIEW_ACTION_HASH_MISMATCH",
    )
    _assert_pm_quality_problem(
        conflict,
        status_code=409,
        reason_code="PM_QUALITY_SUMMARY_INVOCATION_IMMUTABLE_CONFLICT",
    )


def test_pm_operating_quality_api_maps_fairness_persistence_conflicts_to_409() -> None:
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
    app.dependency_overrides[get_pm_quality_fairness_analysis_repository] = lambda: (
        _ConflictingFairnessAnalysisRepository()
    )
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/rebalance/pm-operating-quality/fairness-analyses",
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
                            "score_run_ids": [balanced_1.score_run_id, balanced_2.score_run_id],
                        },
                        {
                            "segment_id": "mandate_income",
                            "segment_type": "MANDATE_TYPE",
                            "display_name": "Income DPM Mandates",
                            "score_run_ids": [income_1.score_run_id, income_2.score_run_id],
                        },
                    ],
                },
            )
    finally:
        app.dependency_overrides.clear()

    _assert_pm_quality_problem(
        response,
        status_code=409,
        reason_code="PM_QUALITY_FAIRNESS_ANALYSIS_IMMUTABLE_CONFLICT",
    )


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

    _assert_pm_quality_problem(
        missing,
        status_code=404,
        reason_code="PM_QUALITY_SCORE_RUN_NOT_FOUND",
    )
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

    _assert_pm_quality_problem(
        missing,
        status_code=404,
        reason_code="OUTCOME_REVIEW_NOT_FOUND",
    )
    _assert_pm_quality_problem(
        mismatch,
        status_code=422,
        reason_code="PM_QUALITY_POLICY_AS_OF_DATE_MISMATCH",
    )


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
    problem_schema = schema["components"]["schemas"]["PmQualityProblemDetails"]
    assert set(problem_schema["properties"]) >= {
        "type",
        "title",
        "status",
        "detail",
        "reasonCode",
        "correlationId",
        "instance",
    }
    assert (
        operation["responses"]["404"]["content"]["application/problem+json"]["schema"]["$ref"]
        == "#/components/schemas/PmQualityProblemDetails"
    )
    assert "compensation" in operation["description"]
    correlation_header = next(
        parameter
        for parameter in operation["parameters"]
        if parameter["name"] == "x-correlation-id" and parameter["in"] == "header"
    )
    assert (
        correlation_header["description"]
        == "Optional correlation id for PM operating quality audit, supportability, and downstream governance traceability."
    )

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

    review_preview_path = "/api/v1/rebalance/pm-operating-quality/review-actions/preview"
    review_create_path = "/api/v1/rebalance/pm-operating-quality/review-actions"
    review_get_path = "/api/v1/rebalance/pm-operating-quality/review-actions/{review_action_id}"
    assert review_preview_path in schema["paths"]
    assert review_create_path in schema["paths"]
    assert review_get_path in schema["paths"]
    assert "200" in schema["paths"][review_preview_path]["post"]["responses"]
    assert "201" in schema["paths"][review_create_path]["post"]["responses"]
    assert "200" in schema["paths"][review_create_path]["get"]["responses"]
    assert "200" in schema["paths"][review_get_path]["get"]["responses"]
    review_description = schema["paths"][review_preview_path]["post"]["description"]
    assert all(marker in review_description for marker in ["What:", "When:", "How:"])
    assert "does not recalculate scores" in review_description
    assert "does not mutate" in schema["paths"][review_create_path]["post"]["description"]
    review_schema = schema["components"]["schemas"]["DpmPmQualityReviewAction"]
    assert "approval_workflow_boundary" in review_schema["properties"]
    assert "DpmPmQualityApprovalWorkflowBoundaryEvidence" in schema["components"]["schemas"]
    approval_boundary_schema = schema["components"]["schemas"][
        "DpmPmQualityApprovalWorkflowBoundaryEvidence"
    ]
    assert "approval-workflow boundary" in approval_boundary_schema["description"]
    assert "required_source_product" in approval_boundary_schema["properties"]

    summary_preview_path = "/api/v1/rebalance/pm-operating-quality/summary-invocations/preview"
    summary_create_path = "/api/v1/rebalance/pm-operating-quality/summary-invocations"
    summary_get_path = (
        "/api/v1/rebalance/pm-operating-quality/summary-invocations/{summary_invocation_id}"
    )
    assert summary_preview_path in schema["paths"]
    assert summary_create_path in schema["paths"]
    assert summary_get_path in schema["paths"]
    assert "200" in schema["paths"][summary_preview_path]["post"]["responses"]
    assert "201" in schema["paths"][summary_create_path]["post"]["responses"]
    assert "200" in schema["paths"][summary_create_path]["get"]["responses"]
    assert "200" in schema["paths"][summary_get_path]["get"]["responses"]
    summary_description = schema["paths"][summary_preview_path]["post"]["description"]
    assert all(marker in summary_description for marker in ["What:", "When:", "How:"])
    assert "does not store AI-generated narrative text" in summary_description
    assert (
        "does not expose generated summary text"
        in schema["paths"][summary_create_path]["get"]["description"]
    )
    summary_schema = schema["components"]["schemas"]["DpmPmQualitySummaryInvocation"]
    assert "summary_text_boundary" in summary_schema["properties"]
    assert "failure_reason_code" in summary_schema["properties"]
    assert "DpmPmQualitySummaryTextBoundaryEvidence" in schema["components"]["schemas"]
    summary_boundary_schema = schema["components"]["schemas"][
        "DpmPmQualitySummaryTextBoundaryEvidence"
    ]
    assert "generated-summary-text boundary" in summary_boundary_schema["description"]
    assert "downstream_ux_projected" in summary_boundary_schema["properties"]
