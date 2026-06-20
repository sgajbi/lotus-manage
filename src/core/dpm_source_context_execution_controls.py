from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import AliasChoices, BaseModel, Field


class DpmCoreInstrumentEligibilityRecord(BaseModel):
    security_id: str = Field(description="Core-governed security identifier.")
    found: bool = Field(description="Whether lotus-core found an effective eligibility profile.")
    eligibility_status: Literal["APPROVED", "RESTRICTED", "SELL_ONLY", "BANNED", "UNKNOWN"] = Field(
        description="Core-governed instrument eligibility status."
    )
    product_shelf_status: Literal["APPROVED", "RESTRICTED", "SELL_ONLY", "BANNED", "SUSPENDED"] = (
        Field(description="Core product-shelf status.")
    )
    buy_allowed: bool = Field(description="Whether DPM may create buy intents.")
    sell_allowed: bool = Field(description="Whether DPM may create sell intents.")
    restriction_reason_codes: list[str] = Field(
        default_factory=list,
        description="Bounded restriction reason codes from lotus-core.",
    )
    settlement_days: Optional[int] = Field(
        default=None,
        description="Instrument settlement cycle in business days.",
    )
    settlement_calendar_id: Optional[str] = Field(
        default=None,
        description="Settlement calendar identifier.",
    )
    liquidity_tier: Optional[Literal["L1", "L2", "L3", "L4", "L5"]] = Field(
        default=None,
        description="Liquidity tier used for suitability and execution controls.",
    )
    issuer_id: Optional[str] = Field(default=None, description="Direct issuer identifier.")
    issuer_name: Optional[str] = Field(default=None, description="Direct issuer name.")
    ultimate_parent_issuer_id: Optional[str] = Field(
        default=None,
        description="Ultimate parent issuer identifier.",
    )
    ultimate_parent_issuer_name: Optional[str] = Field(
        default=None,
        description="Ultimate parent issuer name.",
    )
    asset_class: Optional[str] = Field(default=None, description="Asset-class label.")
    country_of_risk: Optional[str] = Field(default=None, description="Country of risk.")
    effective_from: Optional[date] = Field(default=None, description="Effective start date.")
    effective_to: Optional[date] = Field(default=None, description="Effective end date.")
    source_record_id: Optional[str] = Field(
        default=None,
        description="Core source record identifier for replay and audit.",
    )
    quality_status: str = Field(description="Core row-level data quality status.")


class DpmCoreInstrumentEligibilitySupportability(BaseModel):
    state: Literal["READY", "DEGRADED", "INCOMPLETE", "UNAVAILABLE"] = Field(
        description="Core readiness state for instrument eligibility consumption."
    )
    reason: str = Field(description="Bounded core readiness reason code.")
    requested_count: int = Field(description="Number of securities requested.")
    found_count: int = Field(
        validation_alias=AliasChoices("found_count", "resolved_count"),
        description="Number of securities resolved from core source data.",
    )
    missing_security_ids: list[str] = Field(
        default_factory=list,
        description="Requested securities without an effective eligibility profile.",
    )


class DpmCoreInstrumentEligibilityBulkResponse(BaseModel):
    product_name: Literal["InstrumentEligibilityProfile"] = Field(
        description="Core source-data product name."
    )
    product_version: Literal["v1"] = Field(description="Core source-data product version.")
    as_of_date: date = Field(description="As-of date used to resolve eligibility.")
    tenant_id: Optional[str] = Field(default=None, description="Optional tenant selector.")
    eligibility: list[DpmCoreInstrumentEligibilityRecord] = Field(
        validation_alias=AliasChoices("eligibility", "records"),
        description="Resolved eligibility records in request order.",
    )
    supportability: DpmCoreInstrumentEligibilitySupportability = Field(
        description="Completeness and readiness posture for the eligibility product."
    )
    lineage: dict[str, str] = Field(
        default_factory=dict,
        description="Core lineage metadata for audit and diagnostics.",
    )
    data_quality_status: Optional[str] = Field(
        default=None,
        description="Core runtime data quality status.",
    )
    latest_evidence_timestamp: Optional[datetime] = Field(
        default=None,
        description="Latest evidence timestamp returned by lotus-core.",
    )


class DpmCoreIntegrationWindow(BaseModel):
    start_date: date = Field(description="Inclusive source evidence window start date.")
    end_date: date = Field(description="Inclusive source evidence window end date.")


class DpmCoreTransactionCostCurvePoint(BaseModel):
    portfolio_id: str = Field(description="Core-governed portfolio identifier.")
    security_id: str = Field(description="Security identifier represented by the cost point.")
    transaction_type: str = Field(description="Observed transaction type.")
    currency: str = Field(description="Currency of observed notional and cost values.")
    observation_count: int = Field(description="Number of observed transactions represented.")
    total_notional: Decimal = Field(description="Total absolute observed notional.")
    total_cost: Decimal = Field(description="Total observed booked cost.")
    average_cost_bps: Decimal = Field(
        description="Observed average cost in basis points; not a predictive execution quote."
    )
    min_cost_bps: Decimal = Field(description="Minimum observed transaction cost in bps.")
    max_cost_bps: Decimal = Field(description="Maximum observed transaction cost in bps.")
    first_observed_date: date = Field(description="Earliest represented transaction date.")
    last_observed_date: date = Field(description="Latest represented transaction date.")
    sample_transaction_ids: list[str] = Field(
        default_factory=list,
        description="Bounded deterministic sample of source transaction identifiers.",
    )
    source_lineage: dict[str, str] = Field(
        default_factory=dict,
        description="Point-level source lineage from lotus-core.",
    )


class DpmCoreTransactionCostCurvePageMetadata(BaseModel):
    page_size: int = Field(description="Maximum cost-curve points requested.")
    sort_key: str = Field(description="Deterministic sort key applied by lotus-core.")
    returned_component_count: int = Field(description="Number of curve points returned.")
    request_scope_fingerprint: str = Field(
        description="Core fingerprint of request selectors and paging scope."
    )
    next_page_token: Optional[str] = Field(
        default=None,
        description="Opaque continuation token when more points are available.",
    )


class DpmCoreTransactionCostCurveSupportability(BaseModel):
    state: Literal["READY", "DEGRADED", "INCOMPLETE", "UNAVAILABLE"] = Field(
        description="Core readiness state for transaction-cost evidence."
    )
    reason: str = Field(description="Bounded core readiness reason code.")
    requested_security_count: Optional[int] = Field(
        default=None,
        description="Number of securities explicitly requested from core.",
    )
    returned_curve_point_count: int = Field(
        description="Number of qualifying observed cost-curve points returned."
    )
    missing_security_ids: list[str] = Field(
        default_factory=list,
        description="Requested securities without qualifying cost evidence.",
    )


class DpmCoreTransactionCostCurveResponse(BaseModel):
    product_name: Literal["TransactionCostCurve"] = Field(
        description="Core source-data product name."
    )
    product_version: Literal["v1"] = Field(description="Core source-data product version.")
    portfolio_id: str = Field(description="Core-governed portfolio identifier.")
    as_of_date: date = Field(description="As-of date used for the curve.")
    window: DpmCoreIntegrationWindow = Field(description="Observed transaction-date window.")
    curve_points: list[DpmCoreTransactionCostCurvePoint] = Field(
        default_factory=list,
        description="Observed transaction-cost curve points from lotus-core.",
    )
    page: DpmCoreTransactionCostCurvePageMetadata = Field(
        description="Core pagination metadata for the cost-curve response."
    )
    supportability: DpmCoreTransactionCostCurveSupportability = Field(
        description="Completeness and readiness posture for cost-curve evidence."
    )
    lineage: dict[str, str] = Field(
        default_factory=dict,
        description="Core product-level lineage metadata.",
    )
    data_quality_status: Optional[str] = Field(
        default=None,
        description="Core runtime data quality status.",
    )
    latest_evidence_timestamp: Optional[datetime] = Field(
        default=None,
        description="Latest evidence timestamp returned by lotus-core.",
    )
    source_batch_fingerprint: Optional[str] = Field(
        default=None,
        description="Core source-batch fingerprint for replay and evidence tie-out.",
    )


class DpmCoreClientRestrictionEntry(BaseModel):
    restriction_scope: str = Field(description="Source-owned restriction scope.")
    restriction_code: str = Field(description="Bounded restriction code.")
    restriction_status: str = Field(description="Restriction lifecycle status.")
    restriction_source: str = Field(description="Source channel that captured the restriction.")
    applies_to_buy: bool = Field(description="Whether the restriction applies to buy actions.")
    applies_to_sell: bool = Field(description="Whether the restriction applies to sell actions.")
    instrument_ids: list[str] = Field(default_factory=list)
    asset_classes: list[str] = Field(default_factory=list)
    issuer_ids: list[str] = Field(default_factory=list)
    country_codes: list[str] = Field(default_factory=list)
    effective_from: date = Field(description="Restriction effective start date.")
    effective_to: Optional[date] = Field(
        default=None, description="Restriction effective end date."
    )
    restriction_version: int = Field(description="Selected restriction version.")
    source_record_id: Optional[str] = Field(default=None, description="Source record identifier.")


class DpmCoreClientRestrictionSupportability(BaseModel):
    state: Literal["READY", "INCOMPLETE", "UNAVAILABLE"] = Field(
        description="Core readiness state for restriction-profile consumption."
    )
    reason: str = Field(description="Bounded core readiness reason code.")
    restriction_count: int = Field(description="Number of effective restrictions returned.")
    missing_data_families: list[str] = Field(default_factory=list)


class DpmCoreClientRestrictionProfileResponse(BaseModel):
    product_name: Literal["ClientRestrictionProfile"] = Field(
        description="Core source-data product name."
    )
    product_version: Literal["v1"] = Field(description="Core source-data product version.")
    portfolio_id: str = Field(description="Core-governed portfolio identifier.")
    client_id: str = Field(description="Core-governed client identifier.")
    mandate_id: Optional[str] = Field(default=None, description="Optional mandate identifier.")
    as_of_date: date = Field(description="Business date used to resolve the profile.")
    restrictions: list[DpmCoreClientRestrictionEntry] = Field(default_factory=list)
    supportability: DpmCoreClientRestrictionSupportability = Field(
        description="Completeness and readiness posture for restriction evidence."
    )
    lineage: dict[str, str] = Field(default_factory=dict)
    data_quality_status: Optional[str] = Field(default=None)
    latest_evidence_timestamp: Optional[datetime] = Field(default=None)
    source_batch_fingerprint: Optional[str] = Field(default=None)


class DpmCoreSustainabilityPreferenceEntry(BaseModel):
    preference_framework: str = Field(description="Source-owned sustainability framework.")
    preference_code: str = Field(description="Bounded sustainability preference code.")
    preference_status: str = Field(description="Preference lifecycle status.")
    preference_source: str = Field(description="Source channel that captured the preference.")
    minimum_allocation: Optional[Decimal] = Field(default=None)
    maximum_allocation: Optional[Decimal] = Field(default=None)
    applies_to_asset_classes: list[str] = Field(default_factory=list)
    exclusion_codes: list[str] = Field(default_factory=list)
    positive_tilt_codes: list[str] = Field(default_factory=list)
    effective_from: date = Field(description="Preference effective start date.")
    effective_to: Optional[date] = Field(default=None, description="Preference effective end date.")
    preference_version: int = Field(description="Selected preference version.")
    source_record_id: Optional[str] = Field(default=None, description="Source record identifier.")


class DpmCoreSustainabilityPreferenceSupportability(BaseModel):
    state: Literal["READY", "INCOMPLETE", "UNAVAILABLE"] = Field(
        description="Core readiness state for sustainability-preference consumption."
    )
    reason: str = Field(description="Bounded core readiness reason code.")
    preference_count: int = Field(description="Number of effective preferences returned.")
    missing_data_families: list[str] = Field(default_factory=list)


class DpmCoreSustainabilityPreferenceProfileResponse(BaseModel):
    product_name: Literal["SustainabilityPreferenceProfile"] = Field(
        description="Core source-data product name."
    )
    product_version: Literal["v1"] = Field(description="Core source-data product version.")
    portfolio_id: str = Field(description="Core-governed portfolio identifier.")
    client_id: str = Field(description="Core-governed client identifier.")
    mandate_id: Optional[str] = Field(default=None, description="Optional mandate identifier.")
    as_of_date: date = Field(description="Business date used to resolve the profile.")
    preferences: list[DpmCoreSustainabilityPreferenceEntry] = Field(default_factory=list)
    supportability: DpmCoreSustainabilityPreferenceSupportability = Field(
        description="Completeness and readiness posture for sustainability evidence."
    )
    lineage: dict[str, str] = Field(default_factory=dict)
    data_quality_status: Optional[str] = Field(default=None)
    latest_evidence_timestamp: Optional[datetime] = Field(default=None)
    source_batch_fingerprint: Optional[str] = Field(default=None)
