from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field

from src.core.mandates import DpmMonitoringException, DpmMonitoringRun


class DpmMonitoringRunOnceRequest(BaseModel):
    mandate_ids: list[str] = Field(
        default_factory=list,
        description=(
            "Explicit mandate ids to evaluate. Leave empty only when resolving a source-owned "
            "PM-book cohort from lotus-core."
        ),
        examples=[["MANDATE_PB_SG_GLOBAL_BAL_001"]],
    )
    as_of_date: date = Field(
        description="Business date used to evaluate mandate health.",
        examples=["2026-05-03"],
    )
    tenant_id: Optional[str] = Field(
        default=None,
        description="Optional tenant context captured for audit and later Gateway orchestration.",
        examples=["default"],
    )
    portfolio_manager_id: Optional[str] = Field(
        default=None,
        description=(
            "Portfolio-manager selector captured for audit. When `mandate_ids` is empty, Manage "
            "uses this selector to resolve the cohort from lotus-core "
            "`PortfolioManagerBookMembership:v1`."
        ),
        examples=["PM_SG_DPM_001"],
    )
    book_id: Optional[str] = Field(
        default=None,
        description="Optional PM book id captured for command-center filtering.",
        examples=["BOOK_SG_BALANCED_DPM"],
    )
    booking_center_code: Optional[str] = Field(
        default=None,
        description="Optional booking-center filter forwarded to lotus-core PM-book membership.",
        examples=["Singapore"],
    )
    portfolio_types: list[str] = Field(
        default_factory=lambda: ["DISCRETIONARY"],
        description="Portfolio types eligible for source-owned PM-book monitoring.",
        examples=[["DISCRETIONARY"]],
    )
    requested_by: Optional[str] = Field(
        default=None,
        description="Actor or automation id requesting the monitoring run.",
        examples=["ops_sg_001"],
    )


class DpmMonitoringRunPage(BaseModel):
    items: list[DpmMonitoringRun] = Field(description="Monitoring runs in newest-first order.")
    next_cursor: Optional[str] = Field(
        default=None,
        description="Cursor to request the next page, or null when no next page exists.",
        examples=["dmr_20260503_083000"],
    )


class DpmMonitoringExceptionPage(BaseModel):
    items: list[DpmMonitoringException] = Field(
        description="Monitoring exceptions in newest-first order."
    )
    next_cursor: Optional[str] = Field(
        default=None,
        description="Cursor to request the next page, or null when no next page exists.",
        examples=["me_20260503_pb_sg_global_bal_001_source_readiness"],
    )


class DpmMonitoringExceptionResolveRequest(BaseModel):
    resolution_reason: str = Field(
        description="Bounded business reason explaining why the exception was resolved.",
        examples=["PM_CONFIRMED_EXIT_REQUIRED"],
    )
