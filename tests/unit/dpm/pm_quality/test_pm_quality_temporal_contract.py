from __future__ import annotations

from datetime import date, datetime, timezone

import pytest
from pydantic import ValidationError

from src.core.outcomes import DpmOutcomeSourceRef
from src.core.pm_quality import (
    DpmPmOperatingQualityPolicy,
    DpmPmQualityGovernanceApproval,
    DpmPmQualityLookbackWindowPolicy,
    DpmPmQualityWeight,
)
from src.core.pm_quality.temporal import (
    canonical_pm_quality_business_date,
    canonical_pm_quality_utc_datetime,
    canonical_pm_quality_utc_timestamp,
)


TENANT_ID = "tenant-sg"


def _source_ref() -> DpmOutcomeSourceRef:
    return DpmOutcomeSourceRef(
        source_system="bank-governance",
        source_type="PM_QUALITY_TEMPORAL_CONTRACT",
        source_id="pmq-temporal-contract",
        source_version="2026-05-12",
        content_hash="sha256:pmq-temporal-contract",
    )


def test_pm_quality_business_dates_are_canonical_date_only_values() -> None:
    assert canonical_pm_quality_business_date("2026-05-12", field_name="as_of_date") == (
        "2026-05-12"
    )
    assert canonical_pm_quality_business_date(date(2026, 5, 12), field_name="as_of_date") == (
        "2026-05-12"
    )

    for value in ("2026-5-12", "2026-05-12T00:00:00Z", "not-a-date"):
        with pytest.raises(ValueError, match="INVALID_PM_QUALITY_BUSINESS_DATE:as_of_date"):
            canonical_pm_quality_business_date(value, field_name="as_of_date")


def test_pm_quality_utc_timestamps_require_timezone_and_normalize_to_utc() -> None:
    assert (
        canonical_pm_quality_utc_timestamp(
            "2026-05-10T17:00:00+08:00",
            field_name="approved_at",
        )
        == "2026-05-10T09:00:00Z"
    )
    assert canonical_pm_quality_utc_datetime(
        datetime(2026, 5, 10, 9, 0, tzinfo=timezone.utc),
        field_name="generated_at",
    ) == datetime(2026, 5, 10, 9, 0, tzinfo=timezone.utc)

    for value in ("2026-05-10", "2026-05-10T09:00:00", "not-a-timestamp"):
        with pytest.raises(ValueError, match="INVALID_PM_QUALITY_UTC_TIMESTAMP:approved_at"):
            canonical_pm_quality_utc_timestamp(value, field_name="approved_at")


def test_pm_quality_policy_temporal_fields_are_normalized_before_persistence() -> None:
    approval = DpmPmQualityGovernanceApproval(
        approval_ref="PMQ-APPROVAL-2026-05",
        approved_by="pm_quality_committee",
        approved_at="2026-05-10T17:00:00+08:00",
        fairness_review_ref="FAIRNESS-PMQ-2026-05",
        fairness_reviewed_by="model_risk_governance",
        fairness_reviewed_at="2026-05-10T10:00:00Z",
        expires_on=date(2026, 6, 30),
        source_refs=[_source_ref()],
    )
    policy = DpmPmOperatingQualityPolicy(
        tenant_id=TENANT_ID,
        policy_id="pmq_sg_dpm",
        policy_version="2026.05",
        enabled=True,
        as_of_date=date(2026, 5, 12),
        access_purpose="SUPERVISORY_CONTROL_REVIEW",
        weights=[
            DpmPmQualityWeight(
                indicator="SOURCE_QUALITY",
                weight=100,
                minimum_evidence_count=1,
            )
        ],
        governance_approval=approval,
    )

    assert policy.as_of_date == "2026-05-12"
    assert policy.governance_approval is not None
    assert policy.governance_approval.approved_at == "2026-05-10T09:00:00Z"
    assert policy.governance_approval.expires_on == "2026-06-30"


def test_pm_quality_domain_models_reject_malformed_temporal_fields() -> None:
    with pytest.raises(ValidationError, match="INVALID_PM_QUALITY_BUSINESS_DATE:as_of_date"):
        DpmPmOperatingQualityPolicy(
            tenant_id=TENANT_ID,
            policy_id="pmq_sg_dpm",
            policy_version="2026.05",
            enabled=False,
            as_of_date="2026-05-12T00:00:00Z",
            access_purpose="SUPERVISORY_CONTROL_REVIEW",
        )

    with pytest.raises(ValidationError, match="INVALID_PM_QUALITY_UTC_TIMESTAMP:approved_at"):
        DpmPmQualityGovernanceApproval(
            approval_ref="PMQ-APPROVAL-2026-05",
            approved_by="pm_quality_committee",
            approved_at="2026-05-10T09:00:00",
            fairness_review_ref="FAIRNESS-PMQ-2026-05",
            fairness_reviewed_by="model_risk_governance",
            fairness_reviewed_at="2026-05-10T10:00:00Z",
            source_refs=[_source_ref()],
        )


def test_pm_quality_lookback_window_uses_canonical_date_range() -> None:
    window = DpmPmQualityLookbackWindowPolicy(
        window_id="pmq_30d_20260512",
        start_date=date(2026, 4, 12),
        end_date="2026-05-12",
        source_refs=[_source_ref()],
    )

    assert window.start_date == "2026-04-12"
    assert window.end_date == "2026-05-12"

    with pytest.raises(ValidationError, match="PM_QUALITY_LOOKBACK_WINDOW_RANGE_INVALID"):
        DpmPmQualityLookbackWindowPolicy(
            window_id="pmq_invalid",
            start_date="2026-05-13",
            end_date="2026-05-12",
            source_refs=[_source_ref()],
        )
