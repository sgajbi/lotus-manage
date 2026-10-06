"""Source-owner integration ports and stable errors; no concrete clients."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any, Generic, Optional, Protocol, TypeVar

from src.core.construction.models import AuthoritativeRegimeStressContext, AuthoritativeRiskContext
from src.core.models import PortfolioSnapshot, RebalanceResult
from src.core.dpm_source_context import (
    DpmStatefulInput,
    DpmCoreExecutionContext,
    DpmCoreModelPortfolioTargetResponse,
    DpmCoreMandateBindingResponse,
    DpmCoreBenchmarkAssignmentResponse,
    DpmCorePortfolioManagerBookMembershipResponse,
    DpmCoreCioModelChangeAffectedCohortResponse,
    DpmCorePortfolioUniverseCandidateResponse,
    DpmCoreInstrumentEligibilityBulkResponse,
    DpmCorePortfolioTaxLotWindowResponse,
    DpmCoreMarketDataCoverageWindowResponse,
    DpmCoreSourceReadinessResponse,
    DpmCoreTransactionCostCurveResponse,
    DpmCorePortfolioCashflowProjectionResponse,
    DpmCoreClientIncomeNeedsScheduleResponse,
    DpmCoreLiquidityReserveRequirementResponse,
    DpmCorePlannedWithdrawalScheduleResponse,
    DpmCoreExternalHedgeExecutionReadinessResponse,
    DpmCoreExternalCurrencyExposureResponse,
    DpmCoreExternalHedgePolicyResponse,
    DpmCoreExternalEligibleHedgeInstrumentResponse,
    DpmCoreExternalFXForwardCurveResponse,
    DpmCoreExternalOrderExecutionAcknowledgementResponse,
    DpmCoreClientRestrictionProfileResponse,
    DpmCoreSustainabilityPreferenceProfileResponse,
)


class LotusAdviseAuthorityUnavailableError(RuntimeError):
    pass


class LotusRiskAuthorityUnavailableError(RuntimeError):
    pass


class DpmCoreResolverError(RuntimeError):
    pass


class DpmCoreResolverUnavailableError(DpmCoreResolverError):
    pass


@dataclass(frozen=True)
class RiskEventAffectedPortfolio:
    portfolio_id: str
    mandate_id: str | None
    source_ref: str
    reason_codes: tuple[str, ...]
    impact_score: Decimal
    dominant_bucket: str


@dataclass(frozen=True)
class RiskEventExcludedPortfolio:
    portfolio_id: str
    mandate_id: str | None
    source_ref: str
    impact_score: Decimal
    dominant_bucket: str


@dataclass(frozen=True)
class RiskEventAffectedCohort:
    cohort_id: str
    risk_event_id: str
    as_of_date: date
    display_name: str
    product_name: str
    product_version: str
    source_service: str
    request_fingerprint: str
    calculation_supportability: str
    reason_codes: tuple[str, ...]
    affected_portfolios: tuple[RiskEventAffectedPortfolio, ...]
    excluded_portfolios: tuple[RiskEventExcludedPortfolio, ...] = ()


@dataclass(frozen=True)
class TacticalHouseViewAffectedPortfolio:
    portfolio_id: str
    mandate_id: str | None
    inclusion_reason_codes: tuple[str, ...]
    source_refs: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class TacticalHouseViewAffectedCohort:
    cohort_id: str
    tactical_view_id: str
    tactical_view_version: str
    theme_id: str
    as_of_date: str
    target_action: str
    product_name: str
    product_version: str
    source_service: str
    content_hash: str
    supportability_state: str
    supportability_reason_codes: tuple[str, ...]
    affected_portfolios: tuple[TacticalHouseViewAffectedPortfolio, ...]
    source_refs: tuple[dict[str, Any], ...]


class RiskAuthorityClient(Protocol):
    def close(self) -> None: ...

    def concentration_context(
        self,
        *,
        result: RebalanceResult,
        correlation_id: str | None,
    ) -> AuthoritativeRiskContext: ...

    def regime_scenario_context(
        self,
        *,
        result: RebalanceResult,
        portfolio_id: str,
        as_of_date: date,
        correlation_id: str | None,
        scenario_pack_id: str = "CIO_REGIME_2026_Q2",
        maximum_allowed_loss_pct: Decimal = Decimal("0.12"),
    ) -> AuthoritativeRegimeStressContext: ...

    def risk_event_affected_cohort(
        self,
        *,
        risk_event_id: str,
        as_of_date: date,
        portfolios: list[dict[str, Any]],
        minimum_impact_score: Decimal,
        correlation_id: str | None,
    ) -> RiskEventAffectedCohort: ...


class AdviseAuthorityClient(Protocol):
    def close(self) -> None: ...

    def tactical_house_view_affected_cohort(
        self,
        *,
        tactical_view: dict[str, Any],
        candidate_portfolios: list[dict[str, Any]],
        eligible_portfolio_types: list[str],
        min_exposure_weight: Decimal | None,
        correlation_id: str,
    ) -> TacticalHouseViewAffectedCohort: ...


SourceResponseT = TypeVar("SourceResponseT", covariant=True)


class ExternalExposureSource(Protocol, Generic[SourceResponseT]):
    """Common scoped call contract; each source retains its distinct typed response."""

    def __call__(
        self,
        *,
        portfolio_id: str,
        as_of_date: date,
        tenant_id: Optional[str] = None,
        mandate_id: Optional[str] = None,
        reporting_currency: Optional[str] = None,
        exposure_currencies: Optional[list[str]] = None,
        correlation_id: Optional[str],
    ) -> SourceResponseT: ...


class CoreResolverClient(Protocol):
    def close(self) -> None: ...

    def resolve_execution_context(
        self,
        *,
        stateful_input: DpmStatefulInput,
        correlation_id: Optional[str],
    ) -> DpmCoreExecutionContext: ...

    def resolve_portfolio_snapshot(
        self,
        *,
        portfolio_id: str,
        as_of_date: date,
        consumer_system: str,
        tenant_id: Optional[str] = None,
        correlation_id: Optional[str],
    ) -> PortfolioSnapshot: ...

    def resolve_model_portfolio_targets(
        self,
        *,
        model_portfolio_id: str,
        as_of_date: date,
        include_inactive_targets: bool = False,
        tenant_id: Optional[str] = None,
        correlation_id: Optional[str],
    ) -> DpmCoreModelPortfolioTargetResponse: ...

    def resolve_mandate_binding(
        self,
        *,
        portfolio_id: str,
        as_of_date: date,
        tenant_id: Optional[str] = None,
        mandate_id: Optional[str] = None,
        booking_center_code: Optional[str] = None,
        include_policy_pack: bool = True,
        correlation_id: Optional[str],
    ) -> DpmCoreMandateBindingResponse: ...

    def resolve_benchmark_assignment(
        self,
        *,
        portfolio_id: str,
        as_of_date: date,
        reporting_currency: Optional[str] = None,
        tenant_id: Optional[str] = None,
        correlation_id: Optional[str],
    ) -> DpmCoreBenchmarkAssignmentResponse: ...

    def resolve_portfolio_manager_book_membership(
        self,
        *,
        portfolio_manager_id: str,
        as_of_date: date,
        tenant_id: Optional[str] = None,
        booking_center_code: Optional[str] = None,
        portfolio_types: Optional[list[str]] = None,
        include_inactive: bool = False,
        correlation_id: Optional[str],
    ) -> DpmCorePortfolioManagerBookMembershipResponse: ...

    def resolve_cio_model_change_affected_cohort(
        self,
        *,
        model_portfolio_id: str,
        as_of_date: date,
        tenant_id: Optional[str] = None,
        booking_center_code: Optional[str] = None,
        include_inactive_mandates: bool = False,
        correlation_id: Optional[str],
    ) -> DpmCoreCioModelChangeAffectedCohortResponse: ...

    def resolve_dpm_portfolio_universe_candidates(
        self,
        *,
        as_of_date: date,
        tenant_id: Optional[str] = None,
        booking_center_code: Optional[str] = None,
        model_portfolio_ids: Optional[list[str]] = None,
        include_inactive_mandates: bool = False,
        page_size: int = 1000,
        page_token: Optional[str] = None,
        correlation_id: Optional[str],
    ) -> DpmCorePortfolioUniverseCandidateResponse: ...

    def resolve_instrument_eligibility(
        self,
        *,
        security_ids: list[str],
        as_of_date: date,
        tenant_id: Optional[str] = None,
        include_restricted_rationale: bool = False,
        correlation_id: Optional[str],
    ) -> DpmCoreInstrumentEligibilityBulkResponse: ...

    def resolve_portfolio_tax_lots(
        self,
        *,
        portfolio_id: str,
        as_of_date: date,
        security_ids: Optional[list[str]] = None,
        lot_status_filter: Optional[str] = None,
        include_closed_lots: bool = False,
        page_size: int = 250,
        page_token: Optional[str] = None,
        tenant_id: Optional[str] = None,
        correlation_id: Optional[str],
    ) -> DpmCorePortfolioTaxLotWindowResponse: ...

    def resolve_market_data_coverage(
        self,
        *,
        instrument_ids: list[str],
        currency_pairs: list[tuple[str, str]],
        as_of_date: date,
        valuation_currency: Optional[str] = None,
        max_staleness_days: int = 5,
        tenant_id: Optional[str] = None,
        correlation_id: Optional[str],
    ) -> DpmCoreMarketDataCoverageWindowResponse: ...

    def resolve_dpm_source_readiness(
        self,
        *,
        portfolio_id: str,
        as_of_date: date,
        tenant_id: Optional[str] = None,
        mandate_id: Optional[str] = None,
        model_portfolio_id: Optional[str] = None,
        instrument_ids: Optional[list[str]] = None,
        currency_pairs: Optional[list[tuple[str, str]]] = None,
        valuation_currency: Optional[str] = None,
        max_staleness_days: int = 5,
        correlation_id: Optional[str],
    ) -> DpmCoreSourceReadinessResponse: ...

    def resolve_transaction_cost_curve(
        self,
        *,
        portfolio_id: str,
        as_of_date: date,
        window_start_date: date,
        window_end_date: date,
        security_ids: Optional[list[str]] = None,
        transaction_types: Optional[list[str]] = None,
        min_observation_count: int = 1,
        page_size: int = 250,
        page_token: Optional[str] = None,
        tenant_id: Optional[str] = None,
        correlation_id: Optional[str],
    ) -> DpmCoreTransactionCostCurveResponse: ...

    def resolve_portfolio_cashflow_projection(
        self,
        *,
        portfolio_id: str,
        as_of_date: date,
        horizon_days: int = 90,
        include_projected: bool = True,
        tenant_id: Optional[str] = None,
        correlation_id: Optional[str],
    ) -> DpmCorePortfolioCashflowProjectionResponse: ...

    def resolve_client_income_needs_schedule(
        self,
        *,
        portfolio_id: str,
        as_of_date: date,
        tenant_id: Optional[str] = None,
        mandate_id: Optional[str] = None,
        include_inactive_schedules: bool = False,
        correlation_id: Optional[str],
    ) -> DpmCoreClientIncomeNeedsScheduleResponse: ...

    def resolve_liquidity_reserve_requirement(
        self,
        *,
        portfolio_id: str,
        as_of_date: date,
        tenant_id: Optional[str] = None,
        mandate_id: Optional[str] = None,
        include_inactive_requirements: bool = False,
        correlation_id: Optional[str],
    ) -> DpmCoreLiquidityReserveRequirementResponse: ...

    def resolve_planned_withdrawal_schedule(
        self,
        *,
        portfolio_id: str,
        as_of_date: date,
        tenant_id: Optional[str] = None,
        mandate_id: Optional[str] = None,
        horizon_days: int = 365,
        include_inactive_withdrawals: bool = False,
        correlation_id: Optional[str],
    ) -> DpmCorePlannedWithdrawalScheduleResponse: ...

    @property
    def resolve_external_hedge_execution_readiness(
        self,
    ) -> ExternalExposureSource[DpmCoreExternalHedgeExecutionReadinessResponse]: ...

    @property
    def resolve_external_currency_exposure(
        self,
    ) -> ExternalExposureSource[DpmCoreExternalCurrencyExposureResponse]: ...

    @property
    def resolve_external_hedge_policy(
        self,
    ) -> ExternalExposureSource[DpmCoreExternalHedgePolicyResponse]: ...

    def resolve_external_eligible_hedge_instruments(
        self,
        *,
        portfolio_id: str,
        as_of_date: date,
        tenant_id: Optional[str] = None,
        mandate_id: Optional[str] = None,
        reporting_currency: Optional[str] = None,
        exposure_currencies: Optional[list[str]] = None,
        instrument_types: Optional[list[str]] = None,
        correlation_id: Optional[str],
    ) -> DpmCoreExternalEligibleHedgeInstrumentResponse: ...

    @property
    def resolve_external_fx_forward_curve(
        self,
    ) -> ExternalExposureSource[DpmCoreExternalFXForwardCurveResponse]: ...

    def resolve_external_order_execution_acknowledgement(
        self,
        *,
        portfolio_id: str,
        as_of_date: date,
        tenant_id: Optional[str] = None,
        mandate_id: Optional[str] = None,
        execution_intent_id: Optional[str] = None,
        order_reference_ids: Optional[list[str]] = None,
        correlation_id: Optional[str],
    ) -> DpmCoreExternalOrderExecutionAcknowledgementResponse: ...

    def resolve_client_restriction_profile(
        self,
        *,
        portfolio_id: str,
        as_of_date: date,
        tenant_id: Optional[str] = None,
        mandate_id: Optional[str] = None,
        include_inactive_restrictions: bool = False,
        correlation_id: Optional[str],
    ) -> DpmCoreClientRestrictionProfileResponse: ...

    def resolve_sustainability_preference_profile(
        self,
        *,
        portfolio_id: str,
        as_of_date: date,
        tenant_id: Optional[str] = None,
        mandate_id: Optional[str] = None,
        include_inactive_preferences: bool = False,
        correlation_id: Optional[str],
    ) -> DpmCoreSustainabilityPreferenceProfileResponse: ...


AdviseAuthorityUnavailableError = LotusAdviseAuthorityUnavailableError
RiskAuthorityUnavailableError = LotusRiskAuthorityUnavailableError
CoreResolverError = DpmCoreResolverError
CoreResolverUnavailableError = DpmCoreResolverUnavailableError
