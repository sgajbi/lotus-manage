from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field

from src.api.services.mandate_service import DpmMandateRefreshResult
from src.core.mandates import (
    DpmMandateDigitalTwin,
    DpmMandateHealthSnapshot,
    DpmMonitoringException,
)


MANDATE_RESPONSE_EXAMPLE: dict[str, Any] = {
    "mandate_id": "MANDATE_PB_SG_GLOBAL_BAL_001",
    "portfolio_id": "PB_SG_GLOBAL_BAL_001",
    "mandate_version": "3",
    "as_of_date": "2026-05-03",
    "source_system": "lotus-core",
    "base_currency": "SGD",
    "reference_currency": "SGD",
    "risk_profile": "BALANCED",
    "investment_objective": "LONG_TERM_TOTAL_RETURN",
    "time_horizon": "LONG_TERM",
    "model_portfolio_id": "MODEL_PB_SG_GLOBAL_BAL_DPM",
    "model_portfolio_version": "2026.04",
    "benchmark_id": None,
    "constraints": {
        "cash_band_min_weight": None,
        "cash_band_max_weight": None,
        "cash_reserve_weight": "0.0200000000",
        "single_position_max_weight": None,
        "issuer_max_weight": None,
        "sector_max_weight": None,
        "region_max_weight": None,
        "currency_max_weight": None,
        "turnover_budget": None,
        "tax_budget_base": None,
        "max_tracking_error": None,
        "max_active_share": None,
        "minimum_trade_notional": None,
        "allowed_product_types": [],
        "restricted_instruments": [],
        "restricted_issuers": [],
        "restricted_sectors": [],
        "sustainability_exclusions": [],
    },
    "preferences": {
        "sustainability_strategy": None,
        "income_priority": None,
        "bespoke_notes": [],
    },
    "review_policy": {
        "review_frequency": "QUARTERLY",
        "last_review_date": None,
        "next_review_due_date": None,
    },
    "source_lineage": [
        {
            "product_name": "DiscretionaryMandateBinding",
            "product_version": "v1",
            "source_system": "lotus-core",
            "source_record_id": "DiscretionaryMandateBinding:v1",
            "data_quality_status": "READY",
            "latest_evidence_timestamp": "2026-05-03T01:00:00Z",
            "lineage": {"contract_version": "DiscretionaryMandateBinding:v1"},
        },
        {
            "product_name": "ClientRestrictionProfile",
            "product_version": "v1",
            "source_system": "lotus-core",
            "source_record_id": "ClientRestrictionProfile:v1",
            "data_quality_status": "READY",
            "latest_evidence_timestamp": "2026-05-03T01:05:00Z",
            "lineage": {"contract_version": "ClientRestrictionProfile:v1"},
        },
    ],
    "field_gap_codes": [
        "MANDATE_OBJECTIVE_PROFILE_NOT_YET_SOURCED",
        "CLIENT_INCOME_NEED_PROFILE_NOT_YET_SOURCED",
        "SUSTAINABILITY_PREFERENCE_PROFILE_NOT_YET_SOURCED",
        "PORTFOLIO_CASHFLOW_PROJECTION_NOT_YET_SOURCED",
        "MANDATE_CASH_BAND_NOT_YET_SOURCED",
        "MANDATE_TURNOVER_BUDGET_NOT_YET_SOURCED",
    ],
}


class DpmMandateRefreshFromCoreRequest(BaseModel):
    portfolio_id: str = Field(
        description="Core-governed portfolio identifier whose mandate binding should be refreshed.",
        examples=["PB_SG_GLOBAL_BAL_001"],
    )
    as_of_date: date = Field(
        description="Business date for resolving lotus-core mandate and target source products.",
        examples=["2026-05-03"],
    )
    tenant_id: Optional[str] = Field(
        default=None,
        description="Optional tenant selector forwarded to lotus-core.",
        examples=["default"],
    )
    booking_center_code: Optional[str] = Field(
        default=None,
        description="Optional booking-center selector forwarded to lotus-core.",
        examples=["SG"],
    )
    model_portfolio_id: Optional[str] = Field(
        default=None,
        description=(
            "Optional model portfolio override. Omit to use the model selected by the core "
            "mandate binding."
        ),
        examples=["MODEL_PB_SG_GLOBAL_BAL_DPM"],
    )
    reference_currency: Optional[str] = Field(
        default=None,
        description="Optional mandate reporting currency override.",
        examples=["SGD"],
    )
    include_market_data_coverage: bool = Field(
        default=True,
        description=(
            "When true, lotus-manage asks core for target-instrument market-data coverage so "
            "source readiness is reflected in the generated health snapshot."
        ),
        examples=[True],
    )


class DpmMandateRefreshFromCoreResponse(BaseModel):
    contract_version: str = Field(
        description="Version of the mandate refresh response contract.",
        examples=["DpmMandateRefreshFromCoreResponse:v1"],
    )
    refreshed_at: datetime = Field(
        description="UTC timestamp when lotus-manage completed the core refresh.",
        examples=["2026-05-03T08:30:00Z"],
    )
    mandate: DpmMandateDigitalTwin = Field(
        description="Compiled discretionary mandate digital twin persisted by lotus-manage."
    )
    health_snapshot: DpmMandateHealthSnapshot = Field(
        description="Generated mandate health snapshot from available core source products."
    )
    monitoring_exceptions: list[DpmMonitoringException] = Field(
        description="Monitoring exceptions raised from non-ready health dimensions."
    )
    field_gap_codes: list[str] = Field(
        description="Known source-data gaps that remain explicit after compilation.",
        examples=[["MANDATE_OBJECTIVE_PROFILE_NOT_YET_SOURCED"]],
    )

    @classmethod
    def from_result(cls, result: DpmMandateRefreshResult) -> "DpmMandateRefreshFromCoreResponse":
        return cls(
            contract_version="DpmMandateRefreshFromCoreResponse:v1",
            refreshed_at=datetime.now(timezone.utc),
            mandate=result.twin,
            health_snapshot=result.health_snapshot,
            monitoring_exceptions=result.monitoring_exceptions,
            field_gap_codes=result.twin.field_gap_codes,
        )
