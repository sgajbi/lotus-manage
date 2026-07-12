from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from src.api.services.pm_operating_quality_service import (
    DpmPmOperatingQualityApplicationService,
    DpmPmOperatingQualityServiceError,
    DpmPmQualityBookScopeCommand,
    DpmPmQualityFairnessAnalysisCommand,
    DpmPmQualityFairnessSegmentCommand,
    DpmPmQualityReviewActionCommand,
    DpmPmQualitySummaryInvocationCommand,
    DpmPmQualityScoreRunCommand,
    build_pm_quality_review_action_from_command,
    build_pm_quality_summary_invocation_from_command,
    build_pm_quality_fairness_analysis_from_command,
    build_pm_quality_score_run_from_command,
    _parse_pm_book_scope_as_of_date,
    _pm_book_member_source_refs,
    _pm_book_scope_evidence_from_membership,
    _pm_book_scope_source_id,
    resolve_pm_quality_policy_from_command,
)
from src.core.dpm_source_context import (
    DpmCorePortfolioManagerBookMember,
    DpmCorePortfolioManagerBookMembershipResponse,
    DpmCorePortfolioManagerBookSupportability,
)
from src.core.pm_quality import (
    DpmPmOperatingQualityPolicy,
    DpmPmOperatingQualityScoreRun,
    DpmPmQualityEvidenceItem,
    DpmPmQualityFairnessSegmentInput,
    DpmPmQualityGovernanceApproval,
    DpmPmQualityWeight,
    build_pm_operating_quality_score_run,
    build_pm_operating_quality_fairness_analysis,
    build_pm_quality_review_action,
)
from src.infrastructure.pm_quality import (
    InMemoryDpmPmQualitySummaryInvocationRepository,
    InMemoryDpmPmQualityReviewActionRepository,
    InMemoryDpmPmQualityFairnessAnalysisRepository,
    InMemoryDpmPmQualityScoreRunRepository,
    InMemoryDpmPmQualityPolicyRepository,
)
from src.infrastructure.outcomes import InMemoryDpmOutcomeReviewRepository


def _enabled_policy() -> DpmPmOperatingQualityPolicy:
    return DpmPmOperatingQualityPolicy(
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
        governance_approval=DpmPmQualityGovernanceApproval(
            approval_ref="PMQ-APPROVAL-2026-05",
            approved_by="pm_quality_committee",
            approved_at="2026-05-10T09:00:00Z",
            fairness_review_ref="FAIRNESS-PMQ-2026-05",
            fairness_reviewed_by="model_risk_governance",
            fairness_reviewed_at="2026-05-10T10:00:00Z",
        ),
    )


class _MembershipResolver:
    def __init__(self, membership: DpmCorePortfolioManagerBookMembershipResponse) -> None:
        self.membership = membership
        self.last_as_of_date: date | None = None

    def resolve_portfolio_manager_book_membership(
        self,
        *,
        portfolio_manager_id: str,
        as_of_date: date,
        tenant_id: str | None,
        booking_center_code: str | None,
        portfolio_types: list[str],
        include_inactive: bool,
        correlation_id: str,
    ) -> DpmCorePortfolioManagerBookMembershipResponse:
        self.last_as_of_date = as_of_date
        return self.membership


def _membership_response(
    *, snapshot_id: str = "pm-book-snapshot-20260512"
) -> DpmCorePortfolioManagerBookMembershipResponse:
    return DpmCorePortfolioManagerBookMembershipResponse(
        product_name="PortfolioManagerBookMembership",
        product_version="v1",
        as_of_date=date.fromisoformat("2026-05-12"),
        portfolio_manager_id="pm_001",
        members=[
            DpmCorePortfolioManagerBookMember(
                portfolio_id="PF_001",
                client_id="client-001",
                booking_center_code="Singapore",
                portfolio_type="DPM",
                status="ACTIVE",
            )
        ],
        supportability=DpmCorePortfolioManagerBookSupportability(
            state="READY",
            reason="PM_BOOK_SCOPE_MATERIALIZED",
            returned_portfolio_count=1,
            filters_applied={"portfolio_types": ["DPM"]},
        ),
        snapshot_id=snapshot_id,
        source_batch_fingerprint="sha256:pm-book",
    )


def _score_run(*, pm_id: str, score: Decimal, correlation_id: str) -> DpmPmOperatingQualityScoreRun:
    policy = _enabled_policy()
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


def _application_service(
    *,
    policy_repository: InMemoryDpmPmQualityPolicyRepository | None = None,
    score_run_repository: InMemoryDpmPmQualityScoreRunRepository | None = None,
    fairness_repository: InMemoryDpmPmQualityFairnessAnalysisRepository | None = None,
    review_action_repository: InMemoryDpmPmQualityReviewActionRepository | None = None,
    summary_invocation_repository: InMemoryDpmPmQualitySummaryInvocationRepository | None = None,
) -> DpmPmOperatingQualityApplicationService:
    return DpmPmOperatingQualityApplicationService(
        outcome_review_repository=InMemoryDpmOutcomeReviewRepository(),
        policy_repository=policy_repository or InMemoryDpmPmQualityPolicyRepository(),
        score_run_repository=score_run_repository or InMemoryDpmPmQualityScoreRunRepository(),
        fairness_repository=fairness_repository or InMemoryDpmPmQualityFairnessAnalysisRepository(),
        review_action_repository=review_action_repository
        or InMemoryDpmPmQualityReviewActionRepository(),
        summary_invocation_repository=summary_invocation_repository
        or InMemoryDpmPmQualitySummaryInvocationRepository(),
    )


def test_pm_quality_service_reuses_policy_when_injected() -> None:
    policy = _enabled_policy()
    resolved = resolve_pm_quality_policy_from_command(
        policy=policy,
        policy_id=None,
        policy_version=None,
        repository=InMemoryDpmPmQualityPolicyRepository(),
    )

    assert resolved == policy


def test_pm_quality_application_service_creates_score_run_through_repository_port() -> None:
    policy_repository = InMemoryDpmPmQualityPolicyRepository()
    score_run_repository = InMemoryDpmPmQualityScoreRunRepository()
    policy_repository.save_policy(policy=_enabled_policy())
    service = _application_service(
        policy_repository=policy_repository,
        score_run_repository=score_run_repository,
    )

    score_run = service.create_score_run(
        DpmPmQualityScoreRunCommand(
            pm_id="pm_001",
            book_id="sg_dpm_book",
            as_of_date="2026-05-12",
            policy=None,
            policy_id="pmq_sg_dpm",
            policy_version="2026.05",
            evidence_items=[
                DpmPmQualityEvidenceItem(
                    indicator="SOURCE_QUALITY",
                    evidence_state="READY",
                    score=Decimal("92"),
                    source_system="lotus-core",
                    source_type="PortfolioManagerBookMembership",
                    source_id="pm-book-001",
                )
            ],
            outcome_review_ids=[],
            actor_id="ops",
            correlation_id="corr-create-score-run",
        )
    )

    persisted = score_run_repository.get_score_run(score_run_id=score_run.score_run_id)
    assert persisted is not None
    assert persisted.content_hash == score_run.content_hash
    assert persisted.correlation_id == "corr-create-score-run"


def test_pm_quality_application_service_queries_score_runs_through_repository_port() -> None:
    score_run_repository = InMemoryDpmPmQualityScoreRunRepository()
    score_run = _score_run(pm_id="pm_001", score=Decimal("91"), correlation_id="corr-query")
    score_run_repository.save_score_run(score_run=score_run)
    service = _application_service(score_run_repository=score_run_repository)

    listed = service.list_score_runs(pm_id="pm_001", policy_id="pmq_sg_dpm")
    fetched = service.get_score_run(score_run_id=score_run.score_run_id)

    assert [item.score_run_id for item in listed] == [score_run.score_run_id]
    assert fetched.content_hash == score_run.content_hash
    with pytest.raises(
        DpmPmOperatingQualityServiceError,
        match="PM_QUALITY_SCORE_RUN_NOT_FOUND:missing-score-run",
    ):
        service.get_score_run(score_run_id="missing-score-run")


def test_pm_quality_application_service_creates_fairness_analysis_through_repository_port() -> None:
    score_run_repository = InMemoryDpmPmQualityScoreRunRepository()
    fairness_repository = InMemoryDpmPmQualityFairnessAnalysisRepository()
    balanced = _score_run(pm_id="pm_balanced", score=Decimal("91"), correlation_id="corr-1")
    growth = _score_run(pm_id="pm_growth", score=Decimal("59"), correlation_id="corr-2")
    score_run_repository.save_score_run(score_run=balanced)
    score_run_repository.save_score_run(score_run=growth)
    service = _application_service(
        score_run_repository=score_run_repository,
        fairness_repository=fairness_repository,
    )

    analysis = service.create_fairness_analysis(
        DpmPmQualityFairnessAnalysisCommand(
            policy_id="pmq_sg_dpm",
            policy_version="2026.05",
            as_of_date="2026-05-12",
            segments=[
                DpmPmQualityFairnessSegmentCommand(
                    segment_id="balanced",
                    segment_type="MANDATE_TYPE",
                    display_name="Balanced mandates",
                    score_run_ids=[balanced.score_run_id],
                ),
                DpmPmQualityFairnessSegmentCommand(
                    segment_id="growth",
                    segment_type="MANDATE_TYPE",
                    display_name="Growth mandates",
                    score_run_ids=[growth.score_run_id],
                ),
            ],
            minimum_segment_score_run_count=1,
            maximum_average_score_spread=Decimal("15"),
            actor_id="ops",
            correlation_id="corr-create-fairness",
        )
    )

    persisted = fairness_repository.get_fairness_analysis(
        fairness_analysis_id=analysis.fairness_analysis_id
    )
    assert persisted is not None
    assert persisted.content_hash == analysis.content_hash
    assert persisted.correlation_id == "corr-create-fairness"


def test_pm_quality_application_service_creates_review_action_through_repository_port() -> None:
    score_run_repository = InMemoryDpmPmQualityScoreRunRepository()
    review_action_repository = InMemoryDpmPmQualityReviewActionRepository()
    score_run = _score_run(pm_id="pm_001", score=Decimal("91"), correlation_id="corr-target")
    score_run_repository.save_score_run(score_run=score_run)
    service = _application_service(
        score_run_repository=score_run_repository,
        review_action_repository=review_action_repository,
    )

    review_action = service.create_review_action(
        DpmPmQualityReviewActionCommand(
            target_type="SCORE_RUN",
            target_id=score_run.score_run_id,
            action_type="ACKNOWLEDGE",
            review_action_ref="PMQ-REVIEW-2026-05-101",
            review_reason="Reviewed through application service.",
            actor_id="ops",
            remediation_due_date=None,
            source_refs=[],
            correlation_id="corr-create-review-action",
        )
    )

    persisted = review_action_repository.get_review_action(
        review_action_id=review_action.review_action_id
    )
    assert persisted is not None
    assert persisted.content_hash == review_action.content_hash
    assert persisted.correlation_id == "corr-create-review-action"


def test_pm_quality_application_service_creates_summary_invocation_through_repository_port() -> (
    None
):
    score_run_repository = InMemoryDpmPmQualityScoreRunRepository()
    review_action_repository = InMemoryDpmPmQualityReviewActionRepository()
    summary_repository = InMemoryDpmPmQualitySummaryInvocationRepository()
    score_run = _score_run(pm_id="pm_001", score=Decimal("91"), correlation_id="corr-summary")
    score_run_repository.save_score_run(score_run=score_run)
    review_action = build_pm_quality_review_action(
        target=score_run,
        target_type="SCORE_RUN",
        action_type="ACKNOWLEDGE",
        review_action_ref="PMQ-REVIEW-2026-05-102",
        review_reason="Reviewed for summary invocation.",
        actor_id="ops",
        source_refs=[],
        remediation_due_date=None,
        correlation_id="corr-summary-review",
    )
    review_action_repository.save_review_action(action=review_action)
    service = _application_service(
        score_run_repository=score_run_repository,
        review_action_repository=review_action_repository,
        summary_invocation_repository=summary_repository,
    )

    invocation = service.create_summary_invocation(
        DpmPmQualitySummaryInvocationCommand(
            score_run_id=score_run.score_run_id,
            review_action_id=review_action.review_action_id,
            invocation_state="COMPLETED",
            summary_ref="PMQ-SUMMARY-2026-05-101",
            workflow_pack_name="pm_quality_summary.pack",
            workflow_pack_version="v1",
            requested_by="ops",
            workflow_run_id="pmq-summary-run-101",
            summary_artifact_ref="pmq-summary-artifact-101",
            summary_content_hash="sha256:pmq-summary-101",
            source_refs=[],
            correlation_id="corr-create-summary",
        )
    )

    persisted = summary_repository.get_summary_invocation(
        summary_invocation_id=invocation.summary_invocation_id
    )
    assert persisted is not None
    assert persisted.content_hash == invocation.content_hash
    assert persisted.correlation_id == "corr-create-summary"


def test_pm_quality_service_builds_fairness_analysis_from_persisted_score_runs() -> None:
    repository = InMemoryDpmPmQualityScoreRunRepository()
    balanced = _score_run(pm_id="pm_balanced", score=Decimal("91"), correlation_id="corr-1")
    growth = _score_run(pm_id="pm_growth", score=Decimal("59"), correlation_id="corr-2")
    repository.save_score_run(score_run=balanced)
    repository.save_score_run(score_run=growth)

    analysis = build_pm_quality_fairness_analysis_from_command(
        command=DpmPmQualityFairnessAnalysisCommand(
            policy_id="pmq_sg_dpm",
            policy_version="2026.05",
            as_of_date="2026-05-12",
            segments=[
                DpmPmQualityFairnessSegmentCommand(
                    segment_id="balanced",
                    segment_type="MANDATE_TYPE",
                    display_name="Balanced mandates",
                    score_run_ids=[balanced.score_run_id],
                ),
                DpmPmQualityFairnessSegmentCommand(
                    segment_id="growth",
                    segment_type="MANDATE_TYPE",
                    display_name="Growth mandates",
                    score_run_ids=[growth.score_run_id],
                ),
            ],
            minimum_segment_score_run_count=1,
            maximum_average_score_spread=Decimal("15"),
            actor_id="ops",
            correlation_id="corr-fairness",
        ),
        score_run_repository=repository,
    )

    assert analysis.policy_id == "pmq_sg_dpm"
    assert analysis.state == "PENDING_REVIEW"
    assert analysis.observed_average_score_spread == Decimal("32.00")
    assert analysis.correlation_id == "corr-fairness"


def test_pm_quality_service_reports_missing_score_run_with_stable_code() -> None:
    repository = InMemoryDpmPmQualityScoreRunRepository()

    with pytest.raises(
        DpmPmOperatingQualityServiceError,
        match="PM_QUALITY_SCORE_RUN_NOT_FOUND:missing",
    ):
        build_pm_quality_fairness_analysis_from_command(
            command=DpmPmQualityFairnessAnalysisCommand(
                policy_id="pmq_sg_dpm",
                policy_version="2026.05",
                as_of_date="2026-05-12",
                segments=[
                    DpmPmQualityFairnessSegmentCommand(
                        segment_id="balanced",
                        segment_type="MANDATE_TYPE",
                        display_name="Balanced mandates",
                        score_run_ids=["missing"],
                    ),
                    DpmPmQualityFairnessSegmentCommand(
                        segment_id="growth",
                        segment_type="MANDATE_TYPE",
                        display_name="Growth mandates",
                        score_run_ids=["also-missing"],
                    ),
                ],
                minimum_segment_score_run_count=1,
                maximum_average_score_spread=Decimal("15"),
                actor_id="ops",
                correlation_id="corr-fairness",
            ),
            score_run_repository=repository,
        )


def test_pm_quality_service_builds_score_run_from_policy_reference() -> None:
    policy_repository = InMemoryDpmPmQualityPolicyRepository()
    policy_repository.save_policy(
        policy=_enabled_policy().model_copy(update={"policy_id": "pmq_reference"})
    )
    score_run = build_pm_quality_score_run_from_command(
        command=DpmPmQualityScoreRunCommand(
            pm_id="pm_001",
            book_id="sg_dpm_book",
            as_of_date="2026-05-12",
            policy=None,
            policy_id="pmq_reference",
            policy_version="2026.05",
            evidence_items=[],
            outcome_review_ids=[],
            actor_id="ops",
            correlation_id="corr-reference",
        ),
        outcome_review_repository=InMemoryDpmOutcomeReviewRepository(),
        policy_repository=policy_repository,
    )

    assert score_run.policy_id == "pmq_reference"
    assert score_run.correlation_id == "corr-reference"


def test_pm_quality_service_reports_missing_policy_reference_with_stable_code() -> None:
    with pytest.raises(
        DpmPmOperatingQualityServiceError,
        match="PM_QUALITY_POLICY_NOT_FOUND:pmq_reference:2026.05",
    ):
        build_pm_quality_score_run_from_command(
            command=DpmPmQualityScoreRunCommand(
                pm_id="pm_001",
                book_id="sg_dpm_book",
                as_of_date="2026-05-12",
                policy=None,
                policy_id="pmq_reference",
                policy_version="2026.05",
                evidence_items=[],
                outcome_review_ids=[],
                actor_id="ops",
                correlation_id="corr-missing-policy",
            ),
            outcome_review_repository=InMemoryDpmOutcomeReviewRepository(),
            policy_repository=InMemoryDpmPmQualityPolicyRepository(),
        )


def test_pm_quality_service_materializes_pm_book_scope_with_resolver() -> None:
    resolver = _MembershipResolver(membership=_membership_response())
    score_run = build_pm_quality_score_run_from_command(
        command=DpmPmQualityScoreRunCommand(
            pm_id="pm_001",
            book_id="sg_dpm_book",
            as_of_date="2026-05-12",
            policy=_enabled_policy(),
            policy_id=None,
            policy_version=None,
            evidence_items=[],
            outcome_review_ids=[],
            actor_id="ops",
            correlation_id="corr-book-scope",
            book_scope=DpmPmQualityBookScopeCommand(
                tenant_id="tenant-001",
                booking_center_code="Singapore",
                portfolio_types=["DPM"],
                include_inactive=False,
            ),
        ),
        outcome_review_repository=InMemoryDpmOutcomeReviewRepository(),
        policy_repository=InMemoryDpmPmQualityPolicyRepository(),
        core_resolver_factory=lambda: resolver,
    )

    assert score_run.book_scope_evidence is not None
    assert score_run.book_scope_evidence.source_id == "pm-book-snapshot-20260512"
    assert score_run.book_scope_evidence.filters_applied == {"portfolio_types": ["DPM"]}
    assert score_run.score_run_id.startswith("pmq_")
    assert resolver.last_as_of_date == date(2026, 5, 12)


def test_pm_book_scope_helper_parses_date_and_source_id_fallbacks() -> None:
    assert _parse_pm_book_scope_as_of_date("2026-05-12") == date(2026, 5, 12)
    with pytest.raises(DpmPmOperatingQualityServiceError, match="INVALID_AS_OF_DATE"):
        _parse_pm_book_scope_as_of_date("bad-date")

    snapshot_membership = _membership_response(snapshot_id="snapshot-001")
    batch_membership = _membership_response(snapshot_id="")
    fallback_membership = batch_membership.model_copy(
        update={"source_batch_fingerprint": None},
        deep=True,
    )

    assert _pm_book_scope_source_id(snapshot_membership) == "snapshot-001"
    assert _pm_book_scope_source_id(batch_membership) == "sha256:pm-book"
    assert _pm_book_scope_source_id(fallback_membership) == "pm-book:pm_001:2026-05-12"


def test_pm_book_scope_evidence_helper_limits_member_refs_and_preserves_filters() -> None:
    membership = _membership_response().model_copy(
        update={
            "members": [
                DpmCorePortfolioManagerBookMember(
                    portfolio_id=f"PF_{index:03d}",
                    client_id=f"client-{index:03d}",
                    booking_center_code="Singapore",
                    portfolio_type="DPM",
                    status="ACTIVE",
                    source_record_id=f"member-source-{index:03d}",
                )
                for index in range(105)
            ]
        },
        deep=True,
    )

    member_refs = _pm_book_member_source_refs(membership)
    evidence = _pm_book_scope_evidence_from_membership(membership)

    assert len(member_refs) == 100
    assert member_refs[0].source_id == "member-source-000"
    assert evidence.returned_portfolio_count == 105
    assert evidence.member_portfolio_ids[-1] == "PF_099"
    assert evidence.filters_applied == {"portfolio_types": ["DPM"]}
    assert evidence.source_refs[0].source_type == "PortfolioManagerBookMembership"


def test_pm_quality_service_builds_review_action_for_score_run() -> None:
    score_run_repository = InMemoryDpmPmQualityScoreRunRepository()
    fairness_repository = InMemoryDpmPmQualityFairnessAnalysisRepository()
    score_run = _score_run(pm_id="pm_001", score=Decimal("91"), correlation_id="corr-review-target")
    score_run_repository.save_score_run(score_run=score_run)

    review_action = build_pm_quality_review_action_from_command(
        command=DpmPmQualityReviewActionCommand(
            target_type="SCORE_RUN",
            target_id=score_run.score_run_id,
            action_type="ACKNOWLEDGE",
            review_action_ref="PMQ-REVIEW-2026-05-001",
            review_reason="Reviewed and acknowledged.",
            actor_id="ops",
            remediation_due_date=None,
            source_refs=[],
            correlation_id="corr-review",
        ),
        score_run_repository=score_run_repository,
        fairness_repository=fairness_repository,
    )

    assert review_action.target_type == "SCORE_RUN"
    assert review_action.target_id == score_run.score_run_id
    assert review_action.action_type == "ACKNOWLEDGE"


def test_pm_quality_service_builds_review_action_for_fairness_analysis() -> None:
    fairness_repository = InMemoryDpmPmQualityFairnessAnalysisRepository()
    score_run = _score_run(pm_id="pm_001", score=Decimal("91"), correlation_id="corr-fairness-base")
    analysis = build_pm_operating_quality_fairness_analysis(
        policy_id="pmq_sg_dpm",
        policy_version="2026.05",
        as_of_date="2026-05-12",
        segments=[
            DpmPmQualityFairnessSegmentInput(
                segment_id="all",
                segment_type="MANDATE_TYPE",
                display_name="All mandates",
                score_runs=[score_run],
                source_refs=[],
            ),
            DpmPmQualityFairnessSegmentInput(
                segment_id="cross",
                segment_type="MANDATE_TYPE",
                display_name="Cross mandates",
                score_runs=[
                    _score_run(
                        pm_id="pm_002", score=Decimal("89"), correlation_id="corr-fairness-cross"
                    )
                ],
                source_refs=[],
            ),
        ],
        minimum_segment_score_run_count=1,
        maximum_average_score_spread=Decimal("15"),
        generated_by="ops",
        correlation_id="corr-fairness",
    )
    fairness_repository.save_fairness_analysis(analysis=analysis)

    review_action = build_pm_quality_review_action_from_command(
        command=DpmPmQualityReviewActionCommand(
            target_type="FAIRNESS_ANALYSIS",
            target_id=analysis.fairness_analysis_id,
            action_type="REQUEST_EVIDENCE_REMEDIATION",
            review_action_ref="PMQ-REVIEW-2026-05-002",
            review_reason="Needs evidentiary material.",
            actor_id="ops",
            remediation_due_date="2026-06-15",
            source_refs=[],
            correlation_id="corr-review-fairness",
        ),
        score_run_repository=InMemoryDpmPmQualityScoreRunRepository(),
        fairness_repository=fairness_repository,
    )

    assert review_action.target_type == "FAIRNESS_ANALYSIS"
    assert review_action.target_id == analysis.fairness_analysis_id
    assert review_action.action_type == "REQUEST_EVIDENCE_REMEDIATION"


def test_pm_quality_service_review_action_targets_report_stable_missing_codes() -> None:
    score_run_repository = InMemoryDpmPmQualityScoreRunRepository()
    fairness_repository = InMemoryDpmPmQualityFairnessAnalysisRepository()

    with pytest.raises(
        DpmPmOperatingQualityServiceError,
        match="PM_QUALITY_SCORE_RUN_NOT_FOUND:missing-score-run",
    ):
        build_pm_quality_review_action_from_command(
            command=DpmPmQualityReviewActionCommand(
                target_type="SCORE_RUN",
                target_id="missing-score-run",
                action_type="ACKNOWLEDGE",
                review_action_ref="PMQ-REVIEW-2026-05-003",
                review_reason="Missing score run.",
                actor_id="ops",
                remediation_due_date=None,
                source_refs=[],
                correlation_id="corr-review-missing",
            ),
            score_run_repository=score_run_repository,
            fairness_repository=fairness_repository,
        )

    with pytest.raises(
        DpmPmOperatingQualityServiceError,
        match="PM_QUALITY_FAIRNESS_ANALYSIS_NOT_FOUND:missing-fairness",
    ):
        build_pm_quality_review_action_from_command(
            command=DpmPmQualityReviewActionCommand(
                target_type="FAIRNESS_ANALYSIS",
                target_id="missing-fairness",
                action_type="ACKNOWLEDGE",
                review_action_ref="PMQ-REVIEW-2026-05-004",
                review_reason="Missing fairness analysis.",
                actor_id="ops",
                remediation_due_date=None,
                source_refs=[],
                correlation_id="corr-review-missing",
            ),
            score_run_repository=score_run_repository,
            fairness_repository=fairness_repository,
        )


def test_pm_quality_service_builds_summary_invocation_from_score_run_and_review_action() -> None:
    score_run_repository = InMemoryDpmPmQualityScoreRunRepository()
    review_action_repository = InMemoryDpmPmQualityReviewActionRepository()
    score_run = _score_run(
        pm_id="pm_001", score=Decimal("91"), correlation_id="corr-summary-target"
    )
    score_run_repository.save_score_run(score_run=score_run)
    review_action = build_pm_quality_review_action(
        target=score_run,
        target_type="SCORE_RUN",
        action_type="ACKNOWLEDGE",
        review_action_ref="PMQ-REVIEW-2026-05-005",
        review_reason="Review action required for summary.",
        actor_id="ops",
        source_refs=[],
        remediation_due_date=None,
        correlation_id="corr-review-summary",
    )
    review_action_repository.save_review_action(action=review_action)

    summary = build_pm_quality_summary_invocation_from_command(
        command=DpmPmQualitySummaryInvocationCommand(
            score_run_id=score_run.score_run_id,
            review_action_id=review_action.review_action_id,
            invocation_state="COMPLETED",
            summary_ref="PMQ-SUMMARY-2026-05-001",
            workflow_pack_name="pm_quality_summary.pack",
            workflow_pack_version="v1",
            requested_by="ops",
            workflow_run_id="pmq-summary-run-001",
            summary_artifact_ref="pmq-summary-artifact-001",
            summary_content_hash="sha256:pmq-summary",
            source_refs=[],
            correlation_id="corr-summary",
        ),
        score_run_repository=score_run_repository,
        review_action_repository=review_action_repository,
    )

    assert summary.score_run_id == score_run.score_run_id
    assert summary.review_action_id == review_action.review_action_id
    assert summary.invocation_state == "COMPLETED"


def test_pm_quality_service_summary_invocation_reports_stable_missing_codes() -> None:
    score_run_repository = InMemoryDpmPmQualityScoreRunRepository()
    review_action_repository = InMemoryDpmPmQualityReviewActionRepository()
    score_run = _score_run(
        pm_id="pm_001", score=Decimal("91"), correlation_id="corr-summary-missing"
    )
    score_run_repository.save_score_run(score_run=score_run)
    review_action = build_pm_quality_review_action(
        target=score_run,
        target_type="SCORE_RUN",
        action_type="ACKNOWLEDGE",
        review_action_ref="PMQ-REVIEW-2026-05-006",
        review_reason="Needs summary.",
        actor_id="ops",
        source_refs=[],
        remediation_due_date=None,
        correlation_id="corr-review-summary-missing",
    )
    review_action_repository.save_review_action(action=review_action)

    with pytest.raises(
        DpmPmOperatingQualityServiceError,
        match="PM_QUALITY_SCORE_RUN_NOT_FOUND:missing-score-run",
    ):
        build_pm_quality_summary_invocation_from_command(
            command=DpmPmQualitySummaryInvocationCommand(
                score_run_id="missing-score-run",
                review_action_id=review_action.review_action_id,
                invocation_state="COMPLETED",
                summary_ref="PMQ-SUMMARY-2026-05-001",
                workflow_pack_name="pm_quality_summary.pack",
                workflow_pack_version="v1",
                requested_by="ops",
                workflow_run_id=None,
                summary_artifact_ref=None,
                summary_content_hash=None,
                source_refs=[],
                correlation_id="corr-summary-missing",
            ),
            score_run_repository=score_run_repository,
            review_action_repository=review_action_repository,
        )

    with pytest.raises(
        DpmPmOperatingQualityServiceError,
        match="PM_QUALITY_REVIEW_ACTION_NOT_FOUND:missing-review-action",
    ):
        build_pm_quality_summary_invocation_from_command(
            command=DpmPmQualitySummaryInvocationCommand(
                score_run_id=score_run.score_run_id,
                review_action_id="missing-review-action",
                invocation_state="COMPLETED",
                summary_ref="PMQ-SUMMARY-2026-05-001",
                workflow_pack_name="pm_quality_summary.pack",
                workflow_pack_version="v1",
                requested_by="ops",
                workflow_run_id=None,
                summary_artifact_ref=None,
                summary_content_hash=None,
                source_refs=[],
                correlation_id="corr-summary-missing",
            ),
            score_run_repository=score_run_repository,
            review_action_repository=review_action_repository,
        )


def test_pm_quality_service_summary_invocation_reports_review_action_hash_mismatch() -> None:
    score_run_repository = InMemoryDpmPmQualityScoreRunRepository()
    review_action_repository = InMemoryDpmPmQualityReviewActionRepository()
    score_run = _score_run(pm_id="pm_001", score=Decimal("91"), correlation_id="corr-summary-hash")
    score_run_repository.save_score_run(score_run=score_run)
    review_action = build_pm_quality_review_action(
        target=score_run,
        target_type="SCORE_RUN",
        action_type="ACKNOWLEDGE",
        review_action_ref="PMQ-REVIEW-2026-05-007",
        review_reason="Review action with mismatched hash.",
        actor_id="ops",
        source_refs=[],
        remediation_due_date=None,
        correlation_id="corr-review-summary-hash",
    )
    mismatched_review_action = review_action.model_copy(
        update={"target_content_hash": "sha256:hash-mismatch"}
    )
    review_action_repository.save_review_action(action=mismatched_review_action)

    with pytest.raises(
        DpmPmOperatingQualityServiceError,
        match="PM_QUALITY_SUMMARY_REVIEW_ACTION_HASH_MISMATCH",
    ):
        build_pm_quality_summary_invocation_from_command(
            command=DpmPmQualitySummaryInvocationCommand(
                score_run_id=score_run.score_run_id,
                review_action_id=mismatched_review_action.review_action_id,
                invocation_state="COMPLETED",
                summary_ref="PMQ-SUMMARY-2026-05-002",
                workflow_pack_name="pm_quality_summary.pack",
                workflow_pack_version="v1",
                requested_by="ops",
                workflow_run_id=None,
                summary_artifact_ref=None,
                summary_content_hash=None,
                source_refs=[],
                correlation_id="corr-summary-hash-mismatch",
            ),
            score_run_repository=score_run_repository,
            review_action_repository=review_action_repository,
        )
