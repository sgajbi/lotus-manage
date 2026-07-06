from dataclasses import dataclass

from src.infrastructure.core_sourcing.errors import DpmCoreResolverUnavailableError


LEGACY_DPM_EXECUTION_CONTEXT_PATH = "/integration/portfolios/{portfolio_id}/dpm-execution-context"


def _resolved_core_url(
    *,
    base_url: str,
    path_template: str,
    unavailable_code: str,
    **path_parameters: str,
) -> str:
    template = path_template.strip()
    if not template:
        raise DpmCoreResolverUnavailableError(unavailable_code)
    base = base_url.rstrip("/")
    path = template.format(**path_parameters).lstrip("/")
    return f"{base}/{path}"


@dataclass(frozen=True)
class DpmCoreResolverConfig:
    base_url: str
    query_base_url: str | None = None
    path_template: str = ""
    model_portfolio_targets_path_template: str = (
        "/integration/model-portfolios/{model_portfolio_id}/targets"
    )
    mandate_binding_path_template: str = "/integration/portfolios/{portfolio_id}/mandate-binding"
    benchmark_assignment_path_template: str = (
        "/integration/portfolios/{portfolio_id}/benchmark-assignment"
    )
    portfolio_manager_book_memberships_path_template: str = (
        "/integration/portfolio-manager-books/{portfolio_manager_id}/memberships"
    )
    cio_model_change_affected_cohort_path_template: str = (
        "/integration/model-portfolios/{model_portfolio_id}/affected-mandates"
    )
    dpm_portfolio_universe_candidates_path_template: str = (
        "/integration/dpm/portfolio-universe/candidates"
    )
    instrument_eligibility_path_template: str = "/integration/instruments/eligibility-bulk"
    portfolio_tax_lots_path_template: str = "/integration/portfolios/{portfolio_id}/tax-lots"
    market_data_coverage_path_template: str = "/integration/market-data/coverage"
    dpm_source_readiness_path_template: str = (
        "/integration/portfolios/{portfolio_id}/dpm-source-readiness"
    )
    portfolio_snapshot_path_template: str = "/integration/portfolios/{portfolio_id}/core-snapshot"
    transaction_cost_curve_path_template: str = (
        "/integration/portfolios/{portfolio_id}/transaction-cost-curve"
    )
    portfolio_cashflow_projection_path_template: str = (
        "/portfolios/{portfolio_id}/cashflow-projection"
    )
    client_income_needs_schedule_path_template: str = (
        "/integration/portfolios/{portfolio_id}/client-income-needs-schedule"
    )
    liquidity_reserve_requirement_path_template: str = (
        "/integration/portfolios/{portfolio_id}/liquidity-reserve-requirement"
    )
    planned_withdrawal_schedule_path_template: str = (
        "/integration/portfolios/{portfolio_id}/planned-withdrawal-schedule"
    )
    external_hedge_execution_readiness_path_template: str = (
        "/integration/portfolios/{portfolio_id}/external-hedge-execution-readiness"
    )
    external_currency_exposure_path_template: str = (
        "/integration/portfolios/{portfolio_id}/external-currency-exposure"
    )
    external_hedge_policy_path_template: str = (
        "/integration/portfolios/{portfolio_id}/external-hedge-policy"
    )
    external_eligible_hedge_instruments_path_template: str = (
        "/integration/portfolios/{portfolio_id}/external-eligible-hedge-instruments"
    )
    external_fx_forward_curve_path_template: str = (
        "/integration/market-data/external-fx-forward-curve"
    )
    external_order_execution_acknowledgement_path_template: str = (
        "/integration/portfolios/{portfolio_id}/external-order-execution-acknowledgement"
    )
    transaction_cost_lookback_days: int = 400
    client_restriction_profile_path_template: str = (
        "/integration/portfolios/{portfolio_id}/client-restriction-profile"
    )
    sustainability_preference_profile_path_template: str = (
        "/integration/portfolios/{portfolio_id}/sustainability-preference-profile"
    )
    timeout_seconds: float = 2.0
    max_attempts: int = 2

    def resolve_url(self, portfolio_id: str) -> str:
        if self.path_template.strip() == LEGACY_DPM_EXECUTION_CONTEXT_PATH:
            raise DpmCoreResolverUnavailableError("DPM_CORE_RESOLVER_UNAVAILABLE")
        return _resolved_core_url(
            base_url=self.base_url,
            path_template=self.path_template,
            unavailable_code="DPM_CORE_RESOLVER_UNAVAILABLE",
            portfolio_id=portfolio_id,
        )

    def resolve_model_portfolio_targets_url(self, model_portfolio_id: str) -> str:
        return _resolved_core_url(
            base_url=self.base_url,
            path_template=self.model_portfolio_targets_path_template,
            unavailable_code="DPM_CORE_MODEL_TARGET_RESOLVER_UNAVAILABLE",
            model_portfolio_id=model_portfolio_id,
        )

    def resolve_mandate_binding_url(self, portfolio_id: str) -> str:
        return _resolved_core_url(
            base_url=self.base_url,
            path_template=self.mandate_binding_path_template,
            unavailable_code="DPM_CORE_MANDATE_BINDING_UNAVAILABLE",
            portfolio_id=portfolio_id,
        )

    def resolve_benchmark_assignment_url(self, portfolio_id: str) -> str:
        return _resolved_core_url(
            base_url=self.base_url,
            path_template=self.benchmark_assignment_path_template,
            unavailable_code="DPM_CORE_BENCHMARK_ASSIGNMENT_UNAVAILABLE",
            portfolio_id=portfolio_id,
        )

    def resolve_portfolio_manager_book_memberships_url(self, portfolio_manager_id: str) -> str:
        return _resolved_core_url(
            base_url=self.base_url,
            path_template=self.portfolio_manager_book_memberships_path_template,
            unavailable_code="DPM_CORE_PM_BOOK_MEMBERSHIP_UNAVAILABLE",
            portfolio_manager_id=portfolio_manager_id,
        )

    def resolve_cio_model_change_affected_cohort_url(self, model_portfolio_id: str) -> str:
        return _resolved_core_url(
            base_url=self.base_url,
            path_template=self.cio_model_change_affected_cohort_path_template,
            unavailable_code="DPM_CORE_CIO_MODEL_CHANGE_COHORT_UNAVAILABLE",
            model_portfolio_id=model_portfolio_id,
        )

    def resolve_dpm_portfolio_universe_candidates_url(self) -> str:
        return _resolved_core_url(
            base_url=self.base_url,
            path_template=self.dpm_portfolio_universe_candidates_path_template,
            unavailable_code="DPM_CORE_PORTFOLIO_UNIVERSE_UNAVAILABLE",
        )

    def resolve_instrument_eligibility_url(self) -> str:
        return _resolved_core_url(
            base_url=self.base_url,
            path_template=self.instrument_eligibility_path_template,
            unavailable_code="DPM_CORE_INSTRUMENT_ELIGIBILITY_UNAVAILABLE",
        )

    def resolve_portfolio_tax_lots_url(self, portfolio_id: str) -> str:
        return _resolved_core_url(
            base_url=self.base_url,
            path_template=self.portfolio_tax_lots_path_template,
            unavailable_code="DPM_CORE_PORTFOLIO_TAX_LOTS_UNAVAILABLE",
            portfolio_id=portfolio_id,
        )

    def resolve_market_data_coverage_url(self) -> str:
        return _resolved_core_url(
            base_url=self.base_url,
            path_template=self.market_data_coverage_path_template,
            unavailable_code="DPM_CORE_MARKET_DATA_COVERAGE_UNAVAILABLE",
        )

    def resolve_dpm_source_readiness_url(self, portfolio_id: str) -> str:
        return _resolved_core_url(
            base_url=self.base_url,
            path_template=self.dpm_source_readiness_path_template,
            unavailable_code="DPM_CORE_SOURCE_READINESS_UNAVAILABLE",
            portfolio_id=portfolio_id,
        )

    def resolve_portfolio_snapshot_url(self, portfolio_id: str) -> str:
        return _resolved_core_url(
            base_url=self.base_url,
            path_template=self.portfolio_snapshot_path_template,
            unavailable_code="DPM_CORE_RESOLVER_UNAVAILABLE",
            portfolio_id=portfolio_id,
        )

    def resolve_transaction_cost_curve_url(self, portfolio_id: str) -> str:
        return _resolved_core_url(
            base_url=self.base_url,
            path_template=self.transaction_cost_curve_path_template,
            unavailable_code="DPM_CORE_TRANSACTION_COST_CURVE_UNAVAILABLE",
            portfolio_id=portfolio_id,
        )

    def resolve_portfolio_cashflow_projection_url(self, portfolio_id: str) -> str:
        return _resolved_core_url(
            base_url=self.query_base_url or self.base_url,
            path_template=self.portfolio_cashflow_projection_path_template,
            unavailable_code="DPM_CORE_CASHFLOW_PROJECTION_UNAVAILABLE",
            portfolio_id=portfolio_id,
        )

    def resolve_client_income_needs_schedule_url(self, portfolio_id: str) -> str:
        return _resolved_core_url(
            base_url=self.base_url,
            path_template=self.client_income_needs_schedule_path_template,
            unavailable_code="DPM_CORE_INCOME_NEEDS_UNAVAILABLE",
            portfolio_id=portfolio_id,
        )

    def resolve_liquidity_reserve_requirement_url(self, portfolio_id: str) -> str:
        return _resolved_core_url(
            base_url=self.base_url,
            path_template=self.liquidity_reserve_requirement_path_template,
            unavailable_code="DPM_CORE_LIQUIDITY_RESERVE_UNAVAILABLE",
            portfolio_id=portfolio_id,
        )

    def resolve_planned_withdrawal_schedule_url(self, portfolio_id: str) -> str:
        return _resolved_core_url(
            base_url=self.base_url,
            path_template=self.planned_withdrawal_schedule_path_template,
            unavailable_code="DPM_CORE_PLANNED_WITHDRAWAL_UNAVAILABLE",
            portfolio_id=portfolio_id,
        )

    def resolve_external_hedge_execution_readiness_url(self, portfolio_id: str) -> str:
        return _resolved_core_url(
            base_url=self.base_url,
            path_template=self.external_hedge_execution_readiness_path_template,
            unavailable_code="DPM_CORE_EXTERNAL_HEDGE_READINESS_UNAVAILABLE",
            portfolio_id=portfolio_id,
        )

    def resolve_external_currency_exposure_url(self, portfolio_id: str) -> str:
        return _resolved_core_url(
            base_url=self.base_url,
            path_template=self.external_currency_exposure_path_template,
            unavailable_code="DPM_CORE_EXTERNAL_CURRENCY_EXPOSURE_UNAVAILABLE",
            portfolio_id=portfolio_id,
        )

    def resolve_external_hedge_policy_url(self, portfolio_id: str) -> str:
        return _resolved_core_url(
            base_url=self.base_url,
            path_template=self.external_hedge_policy_path_template,
            unavailable_code="DPM_CORE_EXTERNAL_HEDGE_POLICY_UNAVAILABLE",
            portfolio_id=portfolio_id,
        )

    def resolve_external_eligible_hedge_instruments_url(self, portfolio_id: str) -> str:
        return _resolved_core_url(
            base_url=self.base_url,
            path_template=self.external_eligible_hedge_instruments_path_template,
            unavailable_code="DPM_CORE_EXTERNAL_ELIGIBLE_HEDGE_INSTRUMENTS_UNAVAILABLE",
            portfolio_id=portfolio_id,
        )

    def resolve_external_fx_forward_curve_url(self) -> str:
        return _resolved_core_url(
            base_url=self.base_url,
            path_template=self.external_fx_forward_curve_path_template,
            unavailable_code="DPM_CORE_EXTERNAL_FX_FORWARD_CURVE_UNAVAILABLE",
        )

    def resolve_external_order_execution_acknowledgement_url(self, portfolio_id: str) -> str:
        return _resolved_core_url(
            base_url=self.base_url,
            path_template=self.external_order_execution_acknowledgement_path_template,
            unavailable_code="DPM_CORE_EXTERNAL_ORDER_EXECUTION_ACKNOWLEDGEMENT_UNAVAILABLE",
            portfolio_id=portfolio_id,
        )

    def resolve_client_restriction_profile_url(self, portfolio_id: str) -> str:
        return _resolved_core_url(
            base_url=self.base_url,
            path_template=self.client_restriction_profile_path_template,
            unavailable_code="DPM_CORE_CLIENT_RESTRICTIONS_UNAVAILABLE",
            portfolio_id=portfolio_id,
        )

    def resolve_sustainability_preference_profile_url(self, portfolio_id: str) -> str:
        return _resolved_core_url(
            base_url=self.base_url,
            path_template=self.sustainability_preference_profile_path_template,
            unavailable_code="DPM_CORE_SUSTAINABILITY_PREFERENCES_UNAVAILABLE",
            portfolio_id=portfolio_id,
        )
