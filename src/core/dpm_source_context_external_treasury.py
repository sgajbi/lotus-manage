from datetime import date, datetime
from typing import Literal, Optional

from pydantic import AliasChoices, BaseModel, Field


class DpmCoreExternalHedgeExecutionReadinessSupportability(BaseModel):
    state: Literal["UNAVAILABLE"] = Field(
        description="Core readiness state for external treasury hedge execution readiness."
    )
    reason: Literal["EXTERNAL_TREASURY_SOURCE_NOT_INGESTED"] = Field(
        description="Bounded core fail-closed reason code."
    )
    missing_data_families: list[str] = Field(
        default_factory=list,
        description="External treasury source families required before readiness is usable.",
    )
    blocked_capabilities: list[str] = Field(
        default_factory=list,
        description="Treasury, OMS, execution, and autonomous-action capabilities blocked.",
    )


class DpmCoreExternalHedgeExecutionReadinessResponse(BaseModel):
    product_name: Literal["ExternalHedgeExecutionReadiness"] = Field(
        description="Core source-data product name."
    )
    product_version: Literal["v1"] = Field(description="Core source-data product version.")
    portfolio_id: str = Field(description="Core-governed portfolio identifier.")
    client_id: str = Field(description="Core-governed client identifier.")
    mandate_id: Optional[str] = Field(default=None, description="Optional mandate identifier.")
    as_of_date: date = Field(description="Business date used to resolve readiness posture.")
    reporting_currency: Optional[str] = Field(default=None)
    exposure_currencies: list[str] = Field(default_factory=list)
    readiness_checks: list[dict[str, str]] = Field(
        default_factory=list,
        description="External treasury readiness checks emitted by core.",
    )
    supportability: DpmCoreExternalHedgeExecutionReadinessSupportability = Field(
        description="Fail-closed external treasury supportability posture."
    )
    lineage: dict[str, str] = Field(default_factory=dict)
    data_quality_status: Optional[str] = Field(default=None)
    latest_evidence_timestamp: Optional[datetime] = Field(default=None)
    source_batch_fingerprint: Optional[str] = Field(default=None)


class DpmCoreExternalCurrencyExposureSupportability(BaseModel):
    state: Literal["UNAVAILABLE"] = Field(
        description="Core readiness state for external treasury currency exposure."
    )
    reason: Literal["EXTERNAL_TREASURY_SOURCE_NOT_INGESTED"] = Field(
        description="Bounded core fail-closed reason code."
    )
    exposure_count: int = Field(
        ge=0,
        description="External currency exposure row count emitted by core.",
    )
    missing_data_families: list[str] = Field(
        default_factory=list,
        description="External treasury source families required before exposure is usable.",
    )
    blocked_capabilities: list[str] = Field(
        default_factory=list,
        description="FX, treasury, OMS, execution, and autonomous-action capabilities blocked.",
    )


class DpmCoreExternalCurrencyExposureResponse(BaseModel):
    product_name: Literal["ExternalCurrencyExposure"] = Field(
        description="Core source-data product name."
    )
    product_version: Literal["v1"] = Field(description="Core source-data product version.")
    portfolio_id: str = Field(description="Core-governed portfolio identifier.")
    client_id: str = Field(description="Core-governed client identifier.")
    mandate_id: Optional[str] = Field(default=None, description="Optional mandate identifier.")
    as_of_date: date = Field(description="Business date used to resolve exposure posture.")
    reporting_currency: Optional[str] = Field(default=None)
    exposure_currencies: list[str] = Field(default_factory=list)
    exposures: list[dict[str, str]] = Field(
        default_factory=list,
        description="External treasury exposure rows, empty while source ingestion is unavailable.",
    )
    supportability: DpmCoreExternalCurrencyExposureSupportability = Field(
        description="Fail-closed external treasury exposure supportability posture."
    )
    lineage: dict[str, str] = Field(default_factory=dict)
    data_quality_status: Optional[str] = Field(default=None)
    latest_evidence_timestamp: Optional[datetime] = Field(default=None)
    source_batch_fingerprint: Optional[str] = Field(default=None)


class DpmCoreExternalHedgePolicySupportability(BaseModel):
    state: Literal["UNAVAILABLE"] = Field(
        description="Core readiness state for external treasury hedge policy."
    )
    reason: Literal["EXTERNAL_TREASURY_SOURCE_NOT_INGESTED"] = Field(
        description="Bounded core fail-closed reason code."
    )
    policy_rule_count: int = Field(
        ge=0,
        description="External hedge policy rule count emitted by core.",
    )
    missing_data_families: list[str] = Field(
        default_factory=list,
        description="External treasury source families required before policy rules are usable.",
    )
    blocked_capabilities: list[str] = Field(
        default_factory=list,
        description=(
            "Hedge-policy, treasury, OMS, execution, and autonomous-action capabilities blocked."
        ),
    )


class DpmCoreExternalHedgePolicyResponse(BaseModel):
    product_name: Literal["ExternalHedgePolicy"] = Field(
        description="Core source-data product name."
    )
    product_version: Literal["v1"] = Field(description="Core source-data product version.")
    portfolio_id: str = Field(description="Core-governed portfolio identifier.")
    client_id: str = Field(description="Core-governed client identifier.")
    mandate_id: Optional[str] = Field(default=None, description="Optional mandate identifier.")
    as_of_date: date = Field(description="Business date used to resolve hedge-policy posture.")
    reporting_currency: Optional[str] = Field(default=None)
    exposure_currencies: list[str] = Field(default_factory=list)
    policy_rules: list[dict[str, str]] = Field(
        default_factory=list,
        description=(
            "External treasury hedge-policy rows, empty while source ingestion is unavailable. "
            "Manage preserves these as evidence only and never as hedge-policy approval."
        ),
    )
    supportability: DpmCoreExternalHedgePolicySupportability = Field(
        description="Fail-closed external treasury hedge-policy supportability posture."
    )
    lineage: dict[str, str] = Field(default_factory=dict)
    data_quality_status: Optional[str] = Field(default=None)
    latest_evidence_timestamp: Optional[datetime] = Field(default=None)
    source_batch_fingerprint: Optional[str] = Field(default=None)


class DpmCoreExternalEligibleHedgeInstrumentSupportability(BaseModel):
    state: Literal["UNAVAILABLE"] = Field(
        description="Core readiness state for external treasury eligible hedge instruments."
    )
    reason: Literal["EXTERNAL_TREASURY_SOURCE_NOT_INGESTED"] = Field(
        description="Bounded core fail-closed reason code."
    )
    instrument_count: int = Field(
        ge=0,
        description="External eligible hedge instrument row count emitted by core.",
    )
    missing_data_families: list[str] = Field(
        default_factory=list,
        description=(
            "External treasury source families required before eligible instrument evidence "
            "is usable."
        ),
    )
    blocked_capabilities: list[str] = Field(
        default_factory=list,
        description=(
            "Eligible-instrument, suitability, treasury, OMS, execution, and "
            "autonomous-action capabilities blocked."
        ),
    )


class DpmCoreExternalEligibleHedgeInstrumentResponse(BaseModel):
    product_name: Literal["ExternalEligibleHedgeInstrument"] = Field(
        description="Core source-data product name."
    )
    product_version: Literal["v1"] = Field(description="Core source-data product version.")
    portfolio_id: str = Field(description="Core-governed portfolio identifier.")
    client_id: str = Field(description="Core-governed client identifier.")
    mandate_id: Optional[str] = Field(default=None, description="Optional mandate identifier.")
    as_of_date: date = Field(
        description="Business date used to resolve eligible hedge instrument posture."
    )
    reporting_currency: Optional[str] = Field(default=None)
    exposure_currencies: list[str] = Field(default_factory=list)
    instrument_types: list[str] = Field(default_factory=list)
    eligible_instruments: list[dict[str, str]] = Field(
        default_factory=list,
        description=(
            "External treasury eligible hedge instrument rows, empty while source ingestion is "
            "unavailable. Manage preserves these as evidence only and never as suitability "
            "approval or product recommendation."
        ),
    )
    supportability: DpmCoreExternalEligibleHedgeInstrumentSupportability = Field(
        description="Fail-closed external treasury eligible-instrument supportability posture."
    )
    lineage: dict[str, str] = Field(default_factory=dict)
    data_quality_status: Optional[str] = Field(default=None)
    latest_evidence_timestamp: Optional[datetime] = Field(default=None)
    source_batch_fingerprint: Optional[str] = Field(default=None)


class DpmCoreExternalFXForwardCurveSupportability(BaseModel):
    state: Literal["UNAVAILABLE"] = Field(
        description="Core readiness state for external treasury FX forward curves."
    )
    reason: Literal["EXTERNAL_TREASURY_SOURCE_NOT_INGESTED"] = Field(
        description="Bounded core fail-closed reason code."
    )
    curve_point_count: int = Field(
        ge=0,
        description="External FX forward-curve point count emitted by core.",
    )
    missing_data_families: list[str] = Field(
        default_factory=list,
        description="External treasury source families required before forward curves are usable.",
    )
    blocked_capabilities: list[str] = Field(
        default_factory=list,
        description=(
            "Forward-pricing, treasury, OMS, execution, and autonomous-action capabilities blocked."
        ),
    )


class DpmCoreExternalFXForwardCurveResponse(BaseModel):
    product_name: Literal["ExternalFXForwardCurve"] = Field(
        description="Core source-data product name."
    )
    product_version: Literal["v1"] = Field(description="Core source-data product version.")
    portfolio_id: Optional[str] = Field(
        default=None,
        description=(
            "Optional core-governed portfolio identifier. The ExternalFXForwardCurve source "
            "product is market-data scoped and may be returned without a portfolio identifier."
        ),
    )
    client_id: Optional[str] = Field(
        default=None,
        description=(
            "Optional core-governed client identifier. The ExternalFXForwardCurve source "
            "product is market-data scoped and may be returned without a client identifier."
        ),
    )
    mandate_id: Optional[str] = Field(default=None, description="Optional mandate identifier.")
    as_of_date: date = Field(description="Business date used to resolve FX forward-curve posture.")
    reporting_currency: Optional[str] = Field(default=None)
    exposure_currencies: list[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("exposure_currencies", "currency_pairs"),
        description=(
            "Exposure currencies or source-owned currency-pair selectors returned by core. "
            "Manage treats these as source evidence only and never as forward-pricing authority."
        ),
    )
    curve_points: list[dict[str, str]] = Field(
        default_factory=list,
        description=(
            "External treasury FX forward-curve points, empty while source ingestion is unavailable. "
            "Manage preserves these as evidence only and never as forward pricing or valuation methodology."
        ),
    )
    supportability: DpmCoreExternalFXForwardCurveSupportability = Field(
        description="Fail-closed external treasury FX forward-curve supportability posture."
    )
    lineage: dict[str, str] = Field(default_factory=dict)
    data_quality_status: Optional[str] = Field(default=None)
    latest_evidence_timestamp: Optional[datetime] = Field(default=None)
    source_batch_fingerprint: Optional[str] = Field(default=None)


class DpmCoreExternalOrderExecutionAcknowledgementSupportability(BaseModel):
    state: Literal["UNAVAILABLE"] = Field(
        description="Core readiness state for external OMS order-execution acknowledgement."
    )
    reason: Literal["EXTERNAL_OMS_SOURCE_NOT_INGESTED"] = Field(
        description="Bounded core fail-closed reason code."
    )
    acknowledgement_count: int = Field(
        ge=0,
        description="External OMS acknowledgement row count emitted by core.",
    )
    missing_data_families: list[str] = Field(
        default_factory=list,
        description="External OMS source families required before acknowledgements are usable.",
    )
    blocked_capabilities: list[str] = Field(
        default_factory=list,
        description="Execution, OMS, fill, settlement, and autonomous-action capabilities blocked.",
    )


class DpmCoreExternalOrderExecutionAcknowledgementResponse(BaseModel):
    product_name: Literal["ExternalOrderExecutionAcknowledgement"] = Field(
        description="Core source-data product name."
    )
    product_version: Literal["v1"] = Field(description="Core source-data product version.")
    portfolio_id: str = Field(description="Core-governed portfolio identifier.")
    client_id: str = Field(description="Core-governed client identifier.")
    mandate_id: Optional[str] = Field(default=None, description="Optional mandate identifier.")
    as_of_date: date = Field(description="Business date used to resolve acknowledgement posture.")
    execution_intent_id: Optional[str] = Field(
        default=None,
        description="Optional Manage execution-intent identifier used to query acknowledgement posture.",
    )
    order_reference_ids: list[str] = Field(
        default_factory=list,
        description="Optional external order references used to query acknowledgement posture.",
    )
    acknowledgements: list[dict[str, str]] = Field(
        default_factory=list,
        description=(
            "External OMS acknowledgement rows, empty while source ingestion is unavailable. "
            "Manage preserves these as evidence only and never as order, fill, or settlement truth."
        ),
    )
    supportability: DpmCoreExternalOrderExecutionAcknowledgementSupportability = Field(
        description="Fail-closed external OMS acknowledgement supportability posture."
    )
    lineage: dict[str, str] = Field(default_factory=dict)
    data_quality_status: Optional[str] = Field(default=None)
    latest_evidence_timestamp: Optional[datetime] = Field(default=None)
    source_batch_fingerprint: Optional[str] = Field(default=None)
