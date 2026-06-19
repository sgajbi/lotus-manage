from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field


class DpmCoreTaxLotPageMetadata(BaseModel):
    page_size: int = Field(description="Maximum tax lots requested from lotus-core.")
    sort_key: str = Field(description="Deterministic sort key used by lotus-core.")
    returned_component_count: int = Field(description="Number of tax lots returned in this page.")
    request_scope_fingerprint: str = Field(description="Opaque request scope fingerprint.")
    next_page_token: Optional[str] = Field(
        default=None,
        description="Opaque continuation token for the next tax-lot page.",
    )


class DpmCorePortfolioTaxLotRecord(BaseModel):
    portfolio_id: str = Field(description="Core-governed portfolio identifier.")
    security_id: str = Field(description="Core-governed security identifier.")
    instrument_id: str = Field(description="Core-governed instrument identifier.")
    lot_id: str = Field(description="Stable core tax-lot identifier.")
    open_quantity: Decimal = Field(description="Current open lot quantity.")
    original_quantity: Decimal = Field(description="Original acquired lot quantity.")
    acquisition_date: date = Field(description="Lot acquisition date.")
    cost_basis_base: Decimal = Field(description="Current lot cost basis in portfolio currency.")
    cost_basis_local: Decimal = Field(description="Current lot cost basis in local trade currency.")
    local_currency: Optional[str] = Field(
        default=None,
        description="Local trade currency for this lot when available.",
    )
    tax_lot_status: Literal["OPEN", "CLOSED"] = Field(description="Current tax-lot status.")
    source_transaction_id: str = Field(description="Core source transaction identifier.")
    source_lineage: dict[str, str] = Field(
        default_factory=dict,
        description="Lot-level core lineage metadata.",
    )


class DpmCorePortfolioTaxLotSupportability(BaseModel):
    state: Literal["READY", "DEGRADED", "INCOMPLETE", "UNAVAILABLE"] = Field(
        description="Core readiness state for tax-lot consumption."
    )
    reason: str = Field(description="Bounded core readiness reason code.")
    requested_security_count: Optional[int] = Field(
        default=None,
        description="Number of securities explicitly requested from core.",
    )
    returned_lot_count: int = Field(description="Number of tax lots returned in this page.")
    missing_security_ids: list[str] = Field(
        default_factory=list,
        description="Requested securities without tax lots after core exhausted the page scope.",
    )


class DpmCorePortfolioTaxLotWindowResponse(BaseModel):
    product_name: Literal["PortfolioTaxLotWindow"] = Field(
        description="Core source-data product name."
    )
    product_version: Literal["v1"] = Field(description="Core source-data product version.")
    portfolio_id: str = Field(description="Core-governed portfolio identifier.")
    as_of_date: date = Field(description="As-of date used to resolve tax lots.")
    lots: list[DpmCorePortfolioTaxLotRecord] = Field(
        description="Resolved tax lots from lotus-core."
    )
    page: DpmCoreTaxLotPageMetadata = Field(description="Core pagination metadata.")
    supportability: DpmCorePortfolioTaxLotSupportability = Field(
        description="Completeness and readiness posture for tax-lot consumption."
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


class DpmCoreMarketDataPriceCoverageRecord(BaseModel):
    instrument_id: str = Field(description="Requested instrument identifier.")
    found: bool = Field(description="Whether lotus-core found a price observation.")
    price_date: Optional[date] = Field(default=None, description="Resolved price date.")
    price: Optional[Decimal] = Field(default=None, description="Resolved price value.")
    currency: Optional[str] = Field(default=None, description="Resolved price currency.")
    age_days: Optional[int] = Field(default=None, description="Observation age in days.")
    quality_status: Literal["READY", "STALE", "MISSING"] = Field(
        description="Core price coverage quality status."
    )


class DpmCoreMarketDataFxCoverageRecord(BaseModel):
    from_currency: str = Field(description="Source currency.")
    to_currency: str = Field(description="Target currency.")
    found: bool = Field(description="Whether lotus-core found an FX observation.")
    rate_date: Optional[date] = Field(default=None, description="Resolved FX rate date.")
    rate: Optional[Decimal] = Field(default=None, description="Resolved FX conversion rate.")
    age_days: Optional[int] = Field(default=None, description="Observation age in days.")
    quality_status: Literal["READY", "STALE", "MISSING"] = Field(
        description="Core FX coverage quality status."
    )


class DpmCoreMarketDataCoverageSupportability(BaseModel):
    state: Literal["READY", "DEGRADED", "INCOMPLETE", "UNAVAILABLE"] = Field(
        description="Core readiness state for market-data consumption."
    )
    reason: str = Field(description="Bounded core readiness reason code.")
    requested_price_count: int = Field(description="Number of requested price observations.")
    resolved_price_count: int = Field(description="Number of resolved price observations.")
    requested_fx_count: int = Field(description="Number of requested FX observations.")
    resolved_fx_count: int = Field(description="Number of resolved FX observations.")
    missing_instrument_ids: list[str] = Field(
        default_factory=list,
        description="Requested instruments without a price observation.",
    )
    stale_instrument_ids: list[str] = Field(
        default_factory=list,
        description="Requested instruments whose price observation is stale.",
    )
    missing_currency_pairs: list[str] = Field(
        default_factory=list,
        description="Requested FX pairs without a rate observation.",
    )
    stale_currency_pairs: list[str] = Field(
        default_factory=list,
        description="Requested FX pairs whose rate observation is stale.",
    )


class DpmCoreMarketDataCoverageWindowResponse(BaseModel):
    product_name: Literal["MarketDataCoverageWindow"] = Field(
        description="Core source-data product name."
    )
    product_version: Literal["v1"] = Field(description="Core source-data product version.")
    as_of_date: date = Field(description="As-of date used to resolve market data.")
    valuation_currency: Optional[str] = Field(
        default=None,
        description="Requested valuation currency context.",
    )
    price_coverage: list[DpmCoreMarketDataPriceCoverageRecord] = Field(
        default_factory=list,
        description="Resolved price coverage records from lotus-core.",
    )
    fx_coverage: list[DpmCoreMarketDataFxCoverageRecord] = Field(
        default_factory=list,
        description="Resolved FX coverage records from lotus-core.",
    )
    supportability: DpmCoreMarketDataCoverageSupportability = Field(
        description="Completeness and readiness posture for market-data consumption."
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
