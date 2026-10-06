"""Bounded synthetic observations; schema validity is not source certification."""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import Field, StringConstraints, field_validator, model_validator

from src.core.composite_authority_models import BusinessDate, Identity, StrictAuthorityModel
from src.core.composite_eligibility.policy import month_window

MoneyText = Annotated[str, StringConstraints(pattern=r"^-?(?:0|[1-9]\d{0,23})(?:\.\d{1,12})?$")]
UtcInstant = Annotated[
    str, StringConstraints(pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z$")
]
Currency = Annotated[str, StringConstraints(pattern=r"^[A-Z]{3}$")]


class MonthlyFlowObservation(StrictAuthorityModel):
    event_id: Identity
    business_date: BusinessDate
    received_at: UtcInstant
    currency: Currency
    amount: MoneyText
    classification: Literal["EXTERNAL_CASH", "INTERNAL_TRANSFER", "REVERSAL", "IN_KIND"]
    status: Literal["POSTED", "CANCELLED"]
    reverses_event_id: Identity | None

    @model_validator(mode="after")
    def require_calendar_and_reversal_shape(self) -> MonthlyFlowObservation:
        date.fromisoformat(self.business_date)
        datetime.fromisoformat(self.received_at)
        if (self.classification == "REVERSAL") != (self.reverses_event_id is not None):
            raise ValueError("COMPOSITE_ELIGIBILITY_REVERSAL_REFERENCE_INVALID")
        if self.reverses_event_id == self.event_id:
            raise ValueError("COMPOSITE_ELIGIBILITY_REVERSAL_SELF_REFERENCE")
        return self


class MonthlyPortfolioObservations(StrictAuthorityModel):
    portfolio_id: Identity
    currency: Currency
    prior_month_end_assets: MoneyText | None
    prior_assets_as_of: BusinessDate | None
    month_end_assets: MoneyText | None
    settled_unencumbered_cash: MoneyText | None
    cash_as_of: BusinessDate | None
    discretionary: bool | None
    funded: bool | None
    invested: bool | None
    readiness_as_of: BusinessDate | None
    flow_coverage_from: BusinessDate | None
    flow_coverage_to: BusinessDate | None
    flows: list[MonthlyFlowObservation] = Field(max_length=250)

    @field_validator(
        "prior_assets_as_of",
        "cash_as_of",
        "readiness_as_of",
        "flow_coverage_from",
        "flow_coverage_to",
    )
    @classmethod
    def require_calendar_date(cls, value: str | None) -> str | None:
        if value is not None:
            date.fromisoformat(value)
        return value


class MonthlyEligibilityObservations(StrictAuthorityModel):
    """Scoped source material; authority must be admitted separately by its owning port."""

    product_name: Literal["CompositeMonthlyEligibilityObservations"]
    product_version: Literal["v1"]
    evidence_class: Literal["SYNTHETIC_UNQUALIFIED", "SOURCE_UNVERIFIED"]
    tenant_id: Identity
    composite_id: Identity
    definition_version: Identity
    month: str
    source_cut_id: Identity
    source_revision: Identity
    reporting_currency: Currency
    source_generated_at: UtcInstant
    expected_portfolio_ids: list[Identity] = Field(min_length=1, max_length=1000)
    portfolios: list[MonthlyPortfolioObservations] = Field(max_length=1000)

    @model_validator(mode="after")
    def require_universe_and_temporal_shape(self) -> MonthlyEligibilityObservations:
        month_window(self.month)
        if self.expected_portfolio_ids != sorted(set(self.expected_portfolio_ids)):
            raise ValueError("COMPOSITE_ELIGIBILITY_UNIVERSE_NONCANONICAL")
        datetime.fromisoformat(self.source_generated_at)
        expected = set(self.expected_portfolio_ids)
        if any(item.portfolio_id not in expected for item in self.portfolios):
            raise ValueError("COMPOSITE_ELIGIBILITY_UNEXPECTED_PORTFOLIO")
        return self
