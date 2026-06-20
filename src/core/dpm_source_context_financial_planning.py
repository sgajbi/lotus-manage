from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field


class DpmCoreCashflowProjectionPoint(BaseModel):
    projection_date: date = Field(description="Projection date represented by the source row.")
    net_cashflow: Decimal = Field(description="Daily net cashflow in portfolio currency.")
    projected_cumulative_cashflow: Decimal = Field(
        description="Running cumulative cashflow over the returned projection window."
    )


class DpmCorePortfolioCashflowProjectionResponse(BaseModel):
    product_name: Literal["PortfolioCashflowProjection"] = Field(
        description="Core source-data product name."
    )
    product_version: Literal["v1"] = Field(description="Core source-data product version.")
    portfolio_id: str = Field(description="Core-governed portfolio identifier.")
    as_of_date: date = Field(description="Business-date anchor for the projection.")
    range_start_date: date = Field(description="Inclusive projection-window start date.")
    range_end_date: date = Field(description="Inclusive projection-window end date.")
    include_projected: bool = Field(
        description="Whether projected future external cash movements are included."
    )
    portfolio_currency: str = Field(description="Currency for projected cashflow measures.")
    points: list[DpmCoreCashflowProjectionPoint] = Field(default_factory=list)
    total_net_cashflow: Decimal = Field(
        description="Source-owned total net cashflow over the returned projection window."
    )
    projection_days: int = Field(description="Projection horizon in days.")
    notes: Optional[str] = Field(default=None)
    data_quality_status: Optional[str] = Field(default=None)
    latest_evidence_timestamp: Optional[datetime] = Field(default=None)
    source_batch_fingerprint: Optional[str] = Field(default=None)
    lineage: dict[str, str] = Field(default_factory=dict)


class DpmCoreClientIncomeNeedsScheduleEntry(BaseModel):
    schedule_id: str = Field(description="Source-owned income-needs schedule identifier.")
    need_type: str = Field(description="Bounded income need type.")
    need_status: str = Field(description="Income-needs lifecycle status.")
    amount: Decimal = Field(description="Source-supplied income need amount.")
    currency: str = Field(description="Currency for the income need amount.")
    frequency: str = Field(description="Income-needs cadence.")
    start_date: date = Field(description="Income-needs schedule start date.")
    end_date: Optional[date] = Field(default=None, description="Income-needs schedule end date.")
    priority: int = Field(description="Source-supplied priority.")
    funding_policy: Optional[str] = Field(default=None)
    source_record_id: Optional[str] = Field(default=None, description="Source record identifier.")


class DpmCoreClientIncomeNeedsScheduleSupportability(BaseModel):
    state: Literal["READY", "INCOMPLETE", "UNAVAILABLE"] = Field(
        description="Core readiness state for income-needs schedule consumption."
    )
    reason: str = Field(description="Bounded core readiness reason code.")
    schedule_count: int = Field(description="Number of effective schedules returned.")
    missing_data_families: list[str] = Field(default_factory=list)


class DpmCoreClientIncomeNeedsScheduleResponse(BaseModel):
    product_name: Literal["ClientIncomeNeedsSchedule"] = Field(
        description="Core source-data product name."
    )
    product_version: Literal["v1"] = Field(description="Core source-data product version.")
    portfolio_id: str = Field(description="Core-governed portfolio identifier.")
    client_id: str = Field(description="Core-governed client identifier.")
    mandate_id: Optional[str] = Field(default=None, description="Optional mandate identifier.")
    as_of_date: date = Field(description="Business date used to resolve the schedules.")
    schedules: list[DpmCoreClientIncomeNeedsScheduleEntry] = Field(default_factory=list)
    supportability: DpmCoreClientIncomeNeedsScheduleSupportability = Field(
        description="Completeness and readiness posture for income-needs evidence."
    )
    lineage: dict[str, str] = Field(default_factory=dict)
    data_quality_status: Optional[str] = Field(default=None)
    latest_evidence_timestamp: Optional[datetime] = Field(default=None)
    source_batch_fingerprint: Optional[str] = Field(default=None)


class DpmCoreLiquidityReserveRequirementEntry(BaseModel):
    reserve_requirement_id: str = Field(description="Source-owned reserve requirement id.")
    reserve_type: str = Field(description="Bounded reserve requirement type.")
    reserve_status: str = Field(description="Reserve requirement lifecycle status.")
    required_amount: Decimal = Field(description="Required reserve amount.")
    currency: str = Field(description="Currency for required_amount.")
    horizon_days: int = Field(description="Reserve horizon in calendar days.")
    priority: int = Field(description="Source-supplied priority.")
    policy_source: str = Field(description="Source policy or bank reference.")
    effective_from: date = Field(description="Requirement effective start date.")
    effective_to: Optional[date] = Field(
        default=None, description="Requirement effective end date."
    )
    requirement_version: int = Field(description="Selected requirement version.")
    source_record_id: Optional[str] = Field(default=None, description="Source record identifier.")


class DpmCoreLiquidityReserveRequirementSupportability(BaseModel):
    state: Literal["READY", "INCOMPLETE", "UNAVAILABLE"] = Field(
        description="Core readiness state for liquidity-reserve requirement consumption."
    )
    reason: str = Field(description="Bounded core readiness reason code.")
    requirement_count: int = Field(description="Number of effective requirements returned.")
    missing_data_families: list[str] = Field(default_factory=list)


class DpmCoreLiquidityReserveRequirementResponse(BaseModel):
    product_name: Literal["LiquidityReserveRequirement"] = Field(
        description="Core source-data product name."
    )
    product_version: Literal["v1"] = Field(description="Core source-data product version.")
    portfolio_id: str = Field(description="Core-governed portfolio identifier.")
    client_id: str = Field(description="Core-governed client identifier.")
    mandate_id: Optional[str] = Field(default=None, description="Optional mandate identifier.")
    as_of_date: date = Field(description="Business date used to resolve requirements.")
    requirements: list[DpmCoreLiquidityReserveRequirementEntry] = Field(default_factory=list)
    supportability: DpmCoreLiquidityReserveRequirementSupportability = Field(
        description="Completeness and readiness posture for reserve evidence."
    )
    lineage: dict[str, str] = Field(default_factory=dict)
    data_quality_status: Optional[str] = Field(default=None)
    latest_evidence_timestamp: Optional[datetime] = Field(default=None)
    source_batch_fingerprint: Optional[str] = Field(default=None)


class DpmCorePlannedWithdrawalScheduleEntry(BaseModel):
    withdrawal_schedule_id: str = Field(description="Source-owned withdrawal schedule id.")
    withdrawal_type: str = Field(description="Bounded planned withdrawal type.")
    withdrawal_status: str = Field(description="Withdrawal lifecycle status.")
    amount: Decimal = Field(description="Source-supplied planned withdrawal amount.")
    currency: str = Field(description="Currency for the amount.")
    scheduled_date: date = Field(description="Scheduled withdrawal date.")
    recurrence_frequency: Optional[str] = Field(default=None)
    purpose_code: Optional[str] = Field(default=None)
    source_record_id: Optional[str] = Field(default=None, description="Source record identifier.")


class DpmCorePlannedWithdrawalScheduleSupportability(BaseModel):
    state: Literal["READY", "INCOMPLETE", "UNAVAILABLE"] = Field(
        description="Core readiness state for planned-withdrawal schedule consumption."
    )
    reason: str = Field(description="Bounded core readiness reason code.")
    withdrawal_count: int = Field(description="Number of withdrawals returned.")
    missing_data_families: list[str] = Field(default_factory=list)


class DpmCorePlannedWithdrawalScheduleResponse(BaseModel):
    product_name: Literal["PlannedWithdrawalSchedule"] = Field(
        description="Core source-data product name."
    )
    product_version: Literal["v1"] = Field(description="Core source-data product version.")
    portfolio_id: str = Field(description="Core-governed portfolio identifier.")
    client_id: str = Field(description="Core-governed client identifier.")
    mandate_id: Optional[str] = Field(default=None, description="Optional mandate identifier.")
    as_of_date: date = Field(description="Business date used to resolve the schedules.")
    horizon_days: int = Field(description="Forward withdrawal horizon.")
    withdrawals: list[DpmCorePlannedWithdrawalScheduleEntry] = Field(default_factory=list)
    supportability: DpmCorePlannedWithdrawalScheduleSupportability = Field(
        description="Completeness and readiness posture for planned-withdrawal evidence."
    )
    lineage: dict[str, str] = Field(default_factory=dict)
    data_quality_status: Optional[str] = Field(default=None)
    latest_evidence_timestamp: Optional[datetime] = Field(default=None)
    source_batch_fingerprint: Optional[str] = Field(default=None)
