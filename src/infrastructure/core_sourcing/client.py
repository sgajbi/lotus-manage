from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Optional

import httpx

from src.core.dpm_source_context import (
    DpmCoreBenchmarkAssignmentResponse,
    DpmCoreExternalCurrencyExposureResponse,
    DpmCoreExternalHedgeExecutionReadinessResponse,
    DpmCoreExternalHedgePolicyResponse,
    DpmCoreClientRestrictionProfileResponse,
    DpmCoreClientIncomeNeedsScheduleResponse,
    DpmCoreCioModelChangeAffectedCohortResponse,
    DpmCoreExecutionContext,
    DpmCoreInstrumentEligibilityBulkResponse,
    DpmCoreLiquidityReserveRequirementResponse,
    DpmCoreMandateBindingResponse,
    DpmCoreMarketDataCoverageWindowResponse,
    DpmCoreModelPortfolioTargetResponse,
    DpmCorePlannedWithdrawalScheduleResponse,
    DpmCorePortfolioCashflowProjectionResponse,
    DpmCorePortfolioManagerBookMembershipResponse,
    DpmCorePortfolioTaxLotWindowResponse,
    DpmCorePolicyContext,
    DpmCoreSourceLineage,
    DpmCoreSupportability,
    DpmCoreSustainabilityPreferenceProfileResponse,
    DpmCoreTransactionCostCurveResponse,
    DpmStatefulInput,
    build_market_data_snapshot_from_core_coverage,
    build_model_portfolio_from_core_targets,
    build_policy_context_from_core_mandate,
    build_portfolio_snapshot_with_core_tax_lots,
    build_shelf_entries_from_core_eligibility,
)
from src.core.models import CashBalance, Money, PortfolioSnapshot, Position


class DpmCoreResolverError(RuntimeError):
    pass


class DpmCoreResolverUnavailableError(DpmCoreResolverError):
    pass


LEGACY_DPM_EXECUTION_CONTEXT_PATH = "/integration/portfolios/{portfolio_id}/dpm-execution-context"


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
    instrument_eligibility_path_template: str = "/integration/instruments/eligibility-bulk"
    portfolio_tax_lots_path_template: str = "/integration/portfolios/{portfolio_id}/tax-lots"
    market_data_coverage_path_template: str = "/integration/market-data/coverage"
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
        if not self.path_template.strip():
            raise DpmCoreResolverUnavailableError("DPM_CORE_RESOLVER_UNAVAILABLE")
        if self.path_template.strip() == LEGACY_DPM_EXECUTION_CONTEXT_PATH:
            raise DpmCoreResolverUnavailableError("DPM_CORE_RESOLVER_UNAVAILABLE")
        base = self.base_url.rstrip("/")
        path = self.path_template.format(portfolio_id=portfolio_id).lstrip("/")
        return f"{base}/{path}"

    def resolve_model_portfolio_targets_url(self, model_portfolio_id: str) -> str:
        path_template = self.model_portfolio_targets_path_template.strip()
        if not path_template:
            raise DpmCoreResolverUnavailableError("DPM_CORE_MODEL_TARGET_RESOLVER_UNAVAILABLE")
        base = self.base_url.rstrip("/")
        path = path_template.format(model_portfolio_id=model_portfolio_id).lstrip("/")
        return f"{base}/{path}"

    def resolve_mandate_binding_url(self, portfolio_id: str) -> str:
        path_template = self.mandate_binding_path_template.strip()
        if not path_template:
            raise DpmCoreResolverUnavailableError("DPM_CORE_MANDATE_BINDING_UNAVAILABLE")
        base = self.base_url.rstrip("/")
        path = path_template.format(portfolio_id=portfolio_id).lstrip("/")
        return f"{base}/{path}"

    def resolve_benchmark_assignment_url(self, portfolio_id: str) -> str:
        path_template = self.benchmark_assignment_path_template.strip()
        if not path_template:
            raise DpmCoreResolverUnavailableError("DPM_CORE_BENCHMARK_ASSIGNMENT_UNAVAILABLE")
        base = self.base_url.rstrip("/")
        path = path_template.format(portfolio_id=portfolio_id).lstrip("/")
        return f"{base}/{path}"

    def resolve_portfolio_manager_book_memberships_url(self, portfolio_manager_id: str) -> str:
        path_template = self.portfolio_manager_book_memberships_path_template.strip()
        if not path_template:
            raise DpmCoreResolverUnavailableError("DPM_CORE_PM_BOOK_MEMBERSHIP_UNAVAILABLE")
        base = self.base_url.rstrip("/")
        path = path_template.format(portfolio_manager_id=portfolio_manager_id).lstrip("/")
        return f"{base}/{path}"

    def resolve_cio_model_change_affected_cohort_url(self, model_portfolio_id: str) -> str:
        path_template = self.cio_model_change_affected_cohort_path_template.strip()
        if not path_template:
            raise DpmCoreResolverUnavailableError("DPM_CORE_CIO_MODEL_CHANGE_COHORT_UNAVAILABLE")
        base = self.base_url.rstrip("/")
        path = path_template.format(model_portfolio_id=model_portfolio_id).lstrip("/")
        return f"{base}/{path}"

    def resolve_instrument_eligibility_url(self) -> str:
        path_template = self.instrument_eligibility_path_template.strip()
        if not path_template:
            raise DpmCoreResolverUnavailableError("DPM_CORE_INSTRUMENT_ELIGIBILITY_UNAVAILABLE")
        base = self.base_url.rstrip("/")
        path = path_template.lstrip("/")
        return f"{base}/{path}"

    def resolve_portfolio_tax_lots_url(self, portfolio_id: str) -> str:
        path_template = self.portfolio_tax_lots_path_template.strip()
        if not path_template:
            raise DpmCoreResolverUnavailableError("DPM_CORE_PORTFOLIO_TAX_LOTS_UNAVAILABLE")
        base = self.base_url.rstrip("/")
        path = path_template.format(portfolio_id=portfolio_id).lstrip("/")
        return f"{base}/{path}"

    def resolve_market_data_coverage_url(self) -> str:
        path_template = self.market_data_coverage_path_template.strip()
        if not path_template:
            raise DpmCoreResolverUnavailableError("DPM_CORE_MARKET_DATA_COVERAGE_UNAVAILABLE")
        base = self.base_url.rstrip("/")
        path = path_template.lstrip("/")
        return f"{base}/{path}"

    def resolve_portfolio_snapshot_url(self, portfolio_id: str) -> str:
        path_template = self.portfolio_snapshot_path_template.strip()
        if not path_template:
            raise DpmCoreResolverUnavailableError("DPM_CORE_RESOLVER_UNAVAILABLE")
        base = self.base_url.rstrip("/")
        path = path_template.format(portfolio_id=portfolio_id).lstrip("/")
        return f"{base}/{path}"

    def resolve_transaction_cost_curve_url(self, portfolio_id: str) -> str:
        path_template = self.transaction_cost_curve_path_template.strip()
        if not path_template:
            raise DpmCoreResolverUnavailableError("DPM_CORE_TRANSACTION_COST_CURVE_UNAVAILABLE")
        base = self.base_url.rstrip("/")
        path = path_template.format(portfolio_id=portfolio_id).lstrip("/")
        return f"{base}/{path}"

    def resolve_portfolio_cashflow_projection_url(self, portfolio_id: str) -> str:
        path_template = self.portfolio_cashflow_projection_path_template.strip()
        if not path_template:
            raise DpmCoreResolverUnavailableError("DPM_CORE_CASHFLOW_PROJECTION_UNAVAILABLE")
        base = (self.query_base_url or self.base_url).rstrip("/")
        path = path_template.format(portfolio_id=portfolio_id).lstrip("/")
        return f"{base}/{path}"

    def resolve_client_income_needs_schedule_url(self, portfolio_id: str) -> str:
        path_template = self.client_income_needs_schedule_path_template.strip()
        if not path_template:
            raise DpmCoreResolverUnavailableError("DPM_CORE_INCOME_NEEDS_UNAVAILABLE")
        base = self.base_url.rstrip("/")
        path = path_template.format(portfolio_id=portfolio_id).lstrip("/")
        return f"{base}/{path}"

    def resolve_liquidity_reserve_requirement_url(self, portfolio_id: str) -> str:
        path_template = self.liquidity_reserve_requirement_path_template.strip()
        if not path_template:
            raise DpmCoreResolverUnavailableError("DPM_CORE_LIQUIDITY_RESERVE_UNAVAILABLE")
        base = self.base_url.rstrip("/")
        path = path_template.format(portfolio_id=portfolio_id).lstrip("/")
        return f"{base}/{path}"

    def resolve_planned_withdrawal_schedule_url(self, portfolio_id: str) -> str:
        path_template = self.planned_withdrawal_schedule_path_template.strip()
        if not path_template:
            raise DpmCoreResolverUnavailableError("DPM_CORE_PLANNED_WITHDRAWAL_UNAVAILABLE")
        base = self.base_url.rstrip("/")
        path = path_template.format(portfolio_id=portfolio_id).lstrip("/")
        return f"{base}/{path}"

    def resolve_external_hedge_execution_readiness_url(self, portfolio_id: str) -> str:
        path_template = self.external_hedge_execution_readiness_path_template.strip()
        if not path_template:
            raise DpmCoreResolverUnavailableError("DPM_CORE_EXTERNAL_HEDGE_READINESS_UNAVAILABLE")
        base = self.base_url.rstrip("/")
        path = path_template.format(portfolio_id=portfolio_id).lstrip("/")
        return f"{base}/{path}"

    def resolve_external_currency_exposure_url(self, portfolio_id: str) -> str:
        path_template = self.external_currency_exposure_path_template.strip()
        if not path_template:
            raise DpmCoreResolverUnavailableError("DPM_CORE_EXTERNAL_CURRENCY_EXPOSURE_UNAVAILABLE")
        base = self.base_url.rstrip("/")
        path = path_template.format(portfolio_id=portfolio_id).lstrip("/")
        return f"{base}/{path}"

    def resolve_external_hedge_policy_url(self, portfolio_id: str) -> str:
        path_template = self.external_hedge_policy_path_template.strip()
        if not path_template:
            raise DpmCoreResolverUnavailableError("DPM_CORE_EXTERNAL_HEDGE_POLICY_UNAVAILABLE")
        base = self.base_url.rstrip("/")
        path = path_template.format(portfolio_id=portfolio_id).lstrip("/")
        return f"{base}/{path}"

    def resolve_client_restriction_profile_url(self, portfolio_id: str) -> str:
        path_template = self.client_restriction_profile_path_template.strip()
        if not path_template:
            raise DpmCoreResolverUnavailableError("DPM_CORE_CLIENT_RESTRICTIONS_UNAVAILABLE")
        base = self.base_url.rstrip("/")
        path = path_template.format(portfolio_id=portfolio_id).lstrip("/")
        return f"{base}/{path}"

    def resolve_sustainability_preference_profile_url(self, portfolio_id: str) -> str:
        path_template = self.sustainability_preference_profile_path_template.strip()
        if not path_template:
            raise DpmCoreResolverUnavailableError("DPM_CORE_SUSTAINABILITY_PREFERENCES_UNAVAILABLE")
        base = self.base_url.rstrip("/")
        path = path_template.format(portfolio_id=portfolio_id).lstrip("/")
        return f"{base}/{path}"


class DpmCoreResolverClient:
    def __init__(
        self,
        *,
        config: DpmCoreResolverConfig,
        client: Optional[httpx.Client] = None,
    ) -> None:
        self._config = config
        self._client = client
        self._owns_client = client is None

    def close(self) -> None:
        if self._owns_client and self._client is not None:
            self._client.close()

    def _post_source_product(
        self,
        *,
        url: str,
        payload: dict[str, Any],
        correlation_id: Optional[str],
        unavailable_code: str,
        incomplete_code: str,
    ) -> dict[str, Any]:
        attempts = max(self._config.max_attempts, 1)
        headers = {"X-Correlation-Id": correlation_id} if correlation_id else {}
        client = self._client or httpx.Client(timeout=self._config.timeout_seconds)
        try:
            last_error: Exception | None = None
            for attempt in range(attempts):
                try:
                    response = client.post(url, json=payload, headers=headers)
                except (httpx.TimeoutException, httpx.TransportError) as exc:
                    last_error = exc
                    if attempt + 1 >= attempts:
                        raise DpmCoreResolverUnavailableError(unavailable_code) from exc
                    continue
                if response.status_code in {502, 503, 504} and attempt + 1 < attempts:
                    continue
                if response.status_code >= 500:
                    raise DpmCoreResolverUnavailableError(unavailable_code)
                if response.status_code >= 400:
                    raise DpmCoreResolverError(incomplete_code)
                response_payload = response.json()
                if not isinstance(response_payload, dict):
                    raise DpmCoreResolverError(incomplete_code)
                return response_payload
            raise DpmCoreResolverUnavailableError(unavailable_code) from last_error
        finally:
            if self._owns_client:
                client.close()

    def _get_source_product(
        self,
        *,
        url: str,
        params: dict[str, Any],
        correlation_id: Optional[str],
        unavailable_code: str,
        incomplete_code: str,
    ) -> dict[str, Any]:
        attempts = max(self._config.max_attempts, 1)
        headers = {"X-Correlation-Id": correlation_id} if correlation_id else {}
        client = self._client or httpx.Client(timeout=self._config.timeout_seconds)
        try:
            last_error: Exception | None = None
            for attempt in range(attempts):
                try:
                    response = client.get(url, params=params, headers=headers)
                except (httpx.TimeoutException, httpx.TransportError) as exc:
                    last_error = exc
                    if attempt + 1 >= attempts:
                        raise DpmCoreResolverUnavailableError(unavailable_code) from exc
                    continue
                if response.status_code in {502, 503, 504} and attempt + 1 < attempts:
                    continue
                if response.status_code >= 500:
                    raise DpmCoreResolverUnavailableError(unavailable_code)
                if response.status_code >= 400:
                    raise DpmCoreResolverError(incomplete_code)
                response_payload = response.json()
                if not isinstance(response_payload, dict):
                    raise DpmCoreResolverError(incomplete_code)
                return response_payload
            raise DpmCoreResolverUnavailableError(unavailable_code) from last_error
        finally:
            if self._owns_client:
                client.close()

    def resolve_execution_context(
        self,
        *,
        stateful_input: DpmStatefulInput,
        correlation_id: Optional[str],
    ) -> DpmCoreExecutionContext:
        if self._config.path_template.strip() == LEGACY_DPM_EXECUTION_CONTEXT_PATH:
            raise DpmCoreResolverUnavailableError("DPM_CORE_RESOLVER_UNAVAILABLE")

        mandate = self.resolve_mandate_binding(
            portfolio_id=stateful_input.portfolio_id,
            as_of_date=stateful_input.as_of,
            tenant_id=stateful_input.tenant_id,
            mandate_id=stateful_input.mandate_id,
            booking_center_code=stateful_input.booking_center_code,
            include_policy_pack=True,
            correlation_id=correlation_id,
        )
        model_portfolio_id = stateful_input.model_portfolio_id or mandate.model_portfolio_id
        model_targets = self.resolve_model_portfolio_targets(
            model_portfolio_id=model_portfolio_id,
            as_of_date=stateful_input.as_of,
            tenant_id=stateful_input.tenant_id,
            correlation_id=correlation_id,
        )
        portfolio_snapshot = self.resolve_portfolio_snapshot(
            portfolio_id=stateful_input.portfolio_id,
            as_of_date=stateful_input.as_of,
            consumer_system="lotus-manage",
            correlation_id=correlation_id,
        )
        held_instrument_ids = [position.instrument_id for position in portfolio_snapshot.positions]
        target_instrument_ids = [target.instrument_id for target in model_targets.targets]
        requested_instrument_ids = sorted(set(held_instrument_ids + target_instrument_ids))

        eligibility = self.resolve_instrument_eligibility(
            security_ids=requested_instrument_ids,
            as_of_date=stateful_input.as_of,
            tenant_id=stateful_input.tenant_id,
            include_restricted_rationale=True,
            correlation_id=correlation_id,
        )
        if stateful_input.include_tax_lots:
            tax_lots = self.resolve_portfolio_tax_lots(
                portfolio_id=stateful_input.portfolio_id,
                as_of_date=stateful_input.as_of,
                security_ids=held_instrument_ids,
                lot_status_filter="OPEN",
                include_closed_lots=False,
                tenant_id=stateful_input.tenant_id,
                correlation_id=correlation_id,
            )
            portfolio_snapshot = build_portfolio_snapshot_with_core_tax_lots(
                portfolio_snapshot=portfolio_snapshot,
                response=tax_lots,
            )
        market_data = self.resolve_market_data_coverage(
            instrument_ids=requested_instrument_ids,
            currency_pairs=_required_currency_pairs(
                portfolio_snapshot=portfolio_snapshot,
                base_currency=portfolio_snapshot.base_currency,
            ),
            as_of_date=stateful_input.as_of,
            valuation_currency=portfolio_snapshot.base_currency,
            tenant_id=stateful_input.tenant_id,
            correlation_id=correlation_id,
        )
        transaction_cost_curve = self._try_resolve_transaction_cost_curve(
            portfolio_id=stateful_input.portfolio_id,
            as_of_date=stateful_input.as_of,
            security_ids=requested_instrument_ids,
            tenant_id=stateful_input.tenant_id,
            correlation_id=correlation_id,
        )
        portfolio_cashflow_projection = self._try_resolve_portfolio_cashflow_projection(
            portfolio_id=stateful_input.portfolio_id,
            as_of_date=stateful_input.as_of,
            horizon_days=90,
            include_projected=True,
            correlation_id=correlation_id,
        )
        client_income_needs_schedule = self._try_resolve_client_income_needs_schedule(
            portfolio_id=stateful_input.portfolio_id,
            as_of_date=stateful_input.as_of,
            tenant_id=stateful_input.tenant_id,
            mandate_id=stateful_input.mandate_id,
            correlation_id=correlation_id,
        )
        liquidity_reserve_requirement = self._try_resolve_liquidity_reserve_requirement(
            portfolio_id=stateful_input.portfolio_id,
            as_of_date=stateful_input.as_of,
            tenant_id=stateful_input.tenant_id,
            mandate_id=stateful_input.mandate_id,
            correlation_id=correlation_id,
        )
        planned_withdrawal_schedule = self._try_resolve_planned_withdrawal_schedule(
            portfolio_id=stateful_input.portfolio_id,
            as_of_date=stateful_input.as_of,
            tenant_id=stateful_input.tenant_id,
            mandate_id=stateful_input.mandate_id,
            horizon_days=365,
            correlation_id=correlation_id,
        )
        exposure_currencies = sorted(
            {
                source_currency
                for source_currency, _ in _required_currency_pairs(
                    portfolio_snapshot=portfolio_snapshot,
                    base_currency=portfolio_snapshot.base_currency,
                )
            }
        )
        external_hedge_execution_readiness = self._try_resolve_external_hedge_execution_readiness(
            portfolio_id=stateful_input.portfolio_id,
            as_of_date=stateful_input.as_of,
            tenant_id=stateful_input.tenant_id,
            mandate_id=stateful_input.mandate_id,
            reporting_currency=portfolio_snapshot.base_currency,
            exposure_currencies=exposure_currencies,
            correlation_id=correlation_id,
        )
        external_currency_exposure = self._try_resolve_external_currency_exposure(
            portfolio_id=stateful_input.portfolio_id,
            as_of_date=stateful_input.as_of,
            tenant_id=stateful_input.tenant_id,
            mandate_id=stateful_input.mandate_id,
            reporting_currency=portfolio_snapshot.base_currency,
            exposure_currencies=exposure_currencies,
            correlation_id=correlation_id,
        )
        external_hedge_policy = self._try_resolve_external_hedge_policy(
            portfolio_id=stateful_input.portfolio_id,
            as_of_date=stateful_input.as_of,
            tenant_id=stateful_input.tenant_id,
            mandate_id=stateful_input.mandate_id,
            reporting_currency=portfolio_snapshot.base_currency,
            exposure_currencies=exposure_currencies,
            correlation_id=correlation_id,
        )
        client_restriction_profile = self._try_resolve_client_restriction_profile(
            portfolio_id=stateful_input.portfolio_id,
            as_of_date=stateful_input.as_of,
            tenant_id=stateful_input.tenant_id,
            mandate_id=stateful_input.mandate_id,
            correlation_id=correlation_id,
        )
        sustainability_preference_profile = self._try_resolve_sustainability_preference_profile(
            portfolio_id=stateful_input.portfolio_id,
            as_of_date=stateful_input.as_of,
            tenant_id=stateful_input.tenant_id,
            mandate_id=stateful_input.mandate_id,
            correlation_id=correlation_id,
        )
        policy_context = build_policy_context_from_core_mandate(
            mandate,
            tenant_id=stateful_input.tenant_id,
        )
        return DpmCoreExecutionContext(
            portfolio_snapshot=portfolio_snapshot,
            market_data_snapshot=build_market_data_snapshot_from_core_coverage(market_data),
            model_portfolio=build_model_portfolio_from_core_targets(model_targets),
            shelf_entries=build_shelf_entries_from_core_eligibility(eligibility),
            policy_context=DpmCorePolicyContext(
                recommended_policy_pack_id=(
                    stateful_input.policy_pack_id or policy_context.recommended_policy_pack_id
                ),
                tenant_id=policy_context.tenant_id,
                booking_center_code=policy_context.booking_center_code,
                mandate_id=policy_context.mandate_id,
            ),
            source_lineage=DpmCoreSourceLineage(
                portfolio_snapshot_id=portfolio_snapshot.snapshot_id
                or f"core-snapshot:{stateful_input.portfolio_id}:{stateful_input.as_of.isoformat()}",
                market_data_snapshot_id=(
                    f"market-data-coverage:{stateful_input.as_of.isoformat()}"
                ),
                model_portfolio_id=model_targets.model_portfolio_id,
                model_portfolio_version=model_targets.model_portfolio_version,
                shelf_version=eligibility.lineage.get("contract_version"),
                integration_policy_version=mandate.lineage.get("contract_version"),
                source_lineage_bundle_id=(
                    f"rfc-087:{stateful_input.portfolio_id}:{stateful_input.as_of.isoformat()}"
                ),
            ),
            supportability=DpmCoreSupportability(
                state="READY",
                reason="DPM_CORE_CONTEXT_READY",
                freshness_bucket="current",
                missing_source_families=[],
                degraded_source_families=[],
            ),
            transaction_cost_curve=transaction_cost_curve,
            portfolio_cashflow_projection=portfolio_cashflow_projection,
            client_income_needs_schedule=client_income_needs_schedule,
            liquidity_reserve_requirement=liquidity_reserve_requirement,
            planned_withdrawal_schedule=planned_withdrawal_schedule,
            external_hedge_execution_readiness=external_hedge_execution_readiness,
            external_currency_exposure=external_currency_exposure,
            external_hedge_policy=external_hedge_policy,
            client_restriction_profile=client_restriction_profile,
            sustainability_preference_profile=sustainability_preference_profile,
        )

    def resolve_portfolio_snapshot(
        self,
        *,
        portfolio_id: str,
        as_of_date: date,
        consumer_system: str,
        correlation_id: Optional[str],
    ) -> PortfolioSnapshot:
        url = self._config.resolve_portfolio_snapshot_url(portfolio_id)
        payload = {
            "as_of_date": as_of_date.isoformat(),
            "consumer_system": consumer_system,
            "sections": ["positions_baseline", "portfolio_totals"],
        }
        response = self._post_source_product(
            url=url,
            payload=payload,
            correlation_id=correlation_id,
            unavailable_code="DPM_CORE_RESOLVER_UNAVAILABLE",
            incomplete_code="DPM_CORE_CONTEXT_INCOMPLETE",
        )
        return _portfolio_snapshot_from_core_snapshot(response)

    def resolve_model_portfolio_targets(
        self,
        *,
        model_portfolio_id: str,
        as_of_date: date,
        include_inactive_targets: bool = False,
        tenant_id: Optional[str] = None,
        correlation_id: Optional[str],
    ) -> DpmCoreModelPortfolioTargetResponse:
        url = self._config.resolve_model_portfolio_targets_url(model_portfolio_id)
        payload = {
            "as_of_date": as_of_date.isoformat(),
            "include_inactive_targets": include_inactive_targets,
            "tenant_id": tenant_id,
        }
        response = self._post_source_product(
            url=url,
            payload=payload,
            correlation_id=correlation_id,
            unavailable_code="DPM_CORE_MODEL_TARGET_RESOLVER_UNAVAILABLE",
            incomplete_code="DPM_CORE_MODEL_TARGETS_INCOMPLETE",
        )
        return DpmCoreModelPortfolioTargetResponse.model_validate(response)

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
    ) -> DpmCoreMandateBindingResponse:
        url = self._config.resolve_mandate_binding_url(portfolio_id)
        payload = {
            "as_of_date": as_of_date.isoformat(),
            "tenant_id": tenant_id,
            "mandate_id": mandate_id,
            "booking_center_code": booking_center_code,
            "include_policy_pack": include_policy_pack,
        }
        response = self._post_source_product(
            url=url,
            payload=payload,
            correlation_id=correlation_id,
            unavailable_code="DPM_CORE_MANDATE_BINDING_UNAVAILABLE",
            incomplete_code="DPM_CORE_MANDATE_BINDING_INCOMPLETE",
        )
        return DpmCoreMandateBindingResponse.model_validate(response)

    def resolve_benchmark_assignment(
        self,
        *,
        portfolio_id: str,
        as_of_date: date,
        reporting_currency: Optional[str] = None,
        correlation_id: Optional[str],
    ) -> DpmCoreBenchmarkAssignmentResponse:
        url = self._config.resolve_benchmark_assignment_url(portfolio_id)
        payload: dict[str, Any] = {"as_of_date": as_of_date.isoformat()}
        if reporting_currency:
            payload["reporting_currency"] = reporting_currency
        response = self._post_source_product(
            url=url,
            payload=payload,
            correlation_id=correlation_id,
            unavailable_code="DPM_CORE_BENCHMARK_ASSIGNMENT_UNAVAILABLE",
            incomplete_code="DPM_CORE_BENCHMARK_ASSIGNMENT_INCOMPLETE",
        )
        return DpmCoreBenchmarkAssignmentResponse.model_validate(response)

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
    ) -> DpmCorePortfolioManagerBookMembershipResponse:
        url = self._config.resolve_portfolio_manager_book_memberships_url(portfolio_manager_id)
        payload = {
            "as_of_date": as_of_date.isoformat(),
            "tenant_id": tenant_id,
            "booking_center_code": booking_center_code,
            "portfolio_types": portfolio_types,
            "include_inactive": include_inactive,
        }
        response = self._post_source_product(
            url=url,
            payload=payload,
            correlation_id=correlation_id,
            unavailable_code="DPM_CORE_PM_BOOK_MEMBERSHIP_UNAVAILABLE",
            incomplete_code="DPM_CORE_PM_BOOK_MEMBERSHIP_INCOMPLETE",
        )
        return DpmCorePortfolioManagerBookMembershipResponse.model_validate(response)

    def resolve_cio_model_change_affected_cohort(
        self,
        *,
        model_portfolio_id: str,
        as_of_date: date,
        tenant_id: Optional[str] = None,
        booking_center_code: Optional[str] = None,
        include_inactive_mandates: bool = False,
        correlation_id: Optional[str],
    ) -> DpmCoreCioModelChangeAffectedCohortResponse:
        url = self._config.resolve_cio_model_change_affected_cohort_url(model_portfolio_id)
        payload = {
            "as_of_date": as_of_date.isoformat(),
            "tenant_id": tenant_id,
            "booking_center_code": booking_center_code,
            "include_inactive_mandates": include_inactive_mandates,
        }
        response = self._post_source_product(
            url=url,
            payload=payload,
            correlation_id=correlation_id,
            unavailable_code="DPM_CORE_CIO_MODEL_CHANGE_COHORT_UNAVAILABLE",
            incomplete_code="DPM_CORE_CIO_MODEL_CHANGE_COHORT_INCOMPLETE",
        )
        return DpmCoreCioModelChangeAffectedCohortResponse.model_validate(response)

    def resolve_instrument_eligibility(
        self,
        *,
        security_ids: list[str],
        as_of_date: date,
        tenant_id: Optional[str] = None,
        include_restricted_rationale: bool = False,
        correlation_id: Optional[str],
    ) -> DpmCoreInstrumentEligibilityBulkResponse:
        url = self._config.resolve_instrument_eligibility_url()
        payload = {
            "as_of_date": as_of_date.isoformat(),
            "security_ids": security_ids,
            "tenant_id": tenant_id,
            "include_restricted_rationale": include_restricted_rationale,
        }
        response = self._post_source_product(
            url=url,
            payload=payload,
            correlation_id=correlation_id,
            unavailable_code="DPM_CORE_INSTRUMENT_ELIGIBILITY_UNAVAILABLE",
            incomplete_code="DPM_CORE_INSTRUMENT_ELIGIBILITY_INCOMPLETE",
        )
        return DpmCoreInstrumentEligibilityBulkResponse.model_validate(response)

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
    ) -> DpmCorePortfolioTaxLotWindowResponse:
        url = self._config.resolve_portfolio_tax_lots_url(portfolio_id)
        payload = {
            "as_of_date": as_of_date.isoformat(),
            "security_ids": security_ids,
            "lot_status_filter": lot_status_filter,
            "include_closed_lots": include_closed_lots,
            "page": {"page_size": page_size, "page_token": page_token},
            "tenant_id": tenant_id,
        }
        response = self._post_source_product(
            url=url,
            payload=payload,
            correlation_id=correlation_id,
            unavailable_code="DPM_CORE_PORTFOLIO_TAX_LOTS_UNAVAILABLE",
            incomplete_code="DPM_CORE_PORTFOLIO_TAX_LOTS_INCOMPLETE",
        )
        return DpmCorePortfolioTaxLotWindowResponse.model_validate(response)

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
    ) -> DpmCoreMarketDataCoverageWindowResponse:
        url = self._config.resolve_market_data_coverage_url()
        payload = {
            "as_of_date": as_of_date.isoformat(),
            "instrument_ids": instrument_ids,
            "currency_pairs": [
                {"from_currency": from_currency, "to_currency": to_currency}
                for from_currency, to_currency in currency_pairs
            ],
            "valuation_currency": valuation_currency,
            "max_staleness_days": max_staleness_days,
            "tenant_id": tenant_id,
        }
        response = self._post_source_product(
            url=url,
            payload=payload,
            correlation_id=correlation_id,
            unavailable_code="DPM_CORE_MARKET_DATA_COVERAGE_UNAVAILABLE",
            incomplete_code="DPM_CORE_MARKET_DATA_COVERAGE_INCOMPLETE",
        )
        return DpmCoreMarketDataCoverageWindowResponse.model_validate(response)

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
    ) -> DpmCoreTransactionCostCurveResponse:
        url = self._config.resolve_transaction_cost_curve_url(portfolio_id)
        payload = {
            "as_of_date": as_of_date.isoformat(),
            "window": {
                "start_date": window_start_date.isoformat(),
                "end_date": window_end_date.isoformat(),
            },
            "security_ids": security_ids,
            "transaction_types": transaction_types,
            "min_observation_count": min_observation_count,
            "page": {"page_size": page_size, "page_token": page_token},
            "tenant_id": tenant_id,
        }
        response = self._post_source_product(
            url=url,
            payload=payload,
            correlation_id=correlation_id,
            unavailable_code="DPM_CORE_TRANSACTION_COST_CURVE_UNAVAILABLE",
            incomplete_code="DPM_CORE_TRANSACTION_COST_CURVE_INCOMPLETE",
        )
        return DpmCoreTransactionCostCurveResponse.model_validate(response)

    def resolve_portfolio_cashflow_projection(
        self,
        *,
        portfolio_id: str,
        as_of_date: date,
        horizon_days: int = 90,
        include_projected: bool = True,
        correlation_id: Optional[str],
    ) -> DpmCorePortfolioCashflowProjectionResponse:
        url = self._config.resolve_portfolio_cashflow_projection_url(portfolio_id)
        params = {
            "as_of_date": as_of_date.isoformat(),
            "horizon_days": horizon_days,
            "include_projected": str(include_projected).lower(),
        }
        response = self._get_source_product(
            url=url,
            params=params,
            correlation_id=correlation_id,
            unavailable_code="DPM_CORE_CASHFLOW_PROJECTION_UNAVAILABLE",
            incomplete_code="DPM_CORE_CASHFLOW_PROJECTION_INCOMPLETE",
        )
        return DpmCorePortfolioCashflowProjectionResponse.model_validate(response)

    def resolve_client_income_needs_schedule(
        self,
        *,
        portfolio_id: str,
        as_of_date: date,
        tenant_id: Optional[str] = None,
        mandate_id: Optional[str] = None,
        include_inactive_schedules: bool = False,
        correlation_id: Optional[str],
    ) -> DpmCoreClientIncomeNeedsScheduleResponse:
        url = self._config.resolve_client_income_needs_schedule_url(portfolio_id)
        payload = {
            "as_of_date": as_of_date.isoformat(),
            "tenant_id": tenant_id,
            "mandate_id": mandate_id,
            "include_inactive_schedules": include_inactive_schedules,
        }
        response = self._post_source_product(
            url=url,
            payload=payload,
            correlation_id=correlation_id,
            unavailable_code="DPM_CORE_INCOME_NEEDS_UNAVAILABLE",
            incomplete_code="DPM_CORE_INCOME_NEEDS_INCOMPLETE",
        )
        return DpmCoreClientIncomeNeedsScheduleResponse.model_validate(response)

    def resolve_liquidity_reserve_requirement(
        self,
        *,
        portfolio_id: str,
        as_of_date: date,
        tenant_id: Optional[str] = None,
        mandate_id: Optional[str] = None,
        include_inactive_requirements: bool = False,
        correlation_id: Optional[str],
    ) -> DpmCoreLiquidityReserveRequirementResponse:
        url = self._config.resolve_liquidity_reserve_requirement_url(portfolio_id)
        payload = {
            "as_of_date": as_of_date.isoformat(),
            "tenant_id": tenant_id,
            "mandate_id": mandate_id,
            "include_inactive_requirements": include_inactive_requirements,
        }
        response = self._post_source_product(
            url=url,
            payload=payload,
            correlation_id=correlation_id,
            unavailable_code="DPM_CORE_LIQUIDITY_RESERVE_UNAVAILABLE",
            incomplete_code="DPM_CORE_LIQUIDITY_RESERVE_INCOMPLETE",
        )
        return DpmCoreLiquidityReserveRequirementResponse.model_validate(response)

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
    ) -> DpmCorePlannedWithdrawalScheduleResponse:
        url = self._config.resolve_planned_withdrawal_schedule_url(portfolio_id)
        payload = {
            "as_of_date": as_of_date.isoformat(),
            "tenant_id": tenant_id,
            "mandate_id": mandate_id,
            "horizon_days": horizon_days,
            "include_inactive_withdrawals": include_inactive_withdrawals,
        }
        response = self._post_source_product(
            url=url,
            payload=payload,
            correlation_id=correlation_id,
            unavailable_code="DPM_CORE_PLANNED_WITHDRAWAL_UNAVAILABLE",
            incomplete_code="DPM_CORE_PLANNED_WITHDRAWAL_INCOMPLETE",
        )
        return DpmCorePlannedWithdrawalScheduleResponse.model_validate(response)

    def resolve_external_hedge_execution_readiness(
        self,
        *,
        portfolio_id: str,
        as_of_date: date,
        tenant_id: Optional[str] = None,
        mandate_id: Optional[str] = None,
        reporting_currency: Optional[str] = None,
        exposure_currencies: Optional[list[str]] = None,
        correlation_id: Optional[str],
    ) -> DpmCoreExternalHedgeExecutionReadinessResponse:
        url = self._config.resolve_external_hedge_execution_readiness_url(portfolio_id)
        payload = {
            "as_of_date": as_of_date.isoformat(),
            "tenant_id": tenant_id,
            "mandate_id": mandate_id,
            "reporting_currency": reporting_currency,
            "exposure_currencies": exposure_currencies or [],
        }
        response = self._post_source_product(
            url=url,
            payload=payload,
            correlation_id=correlation_id,
            unavailable_code="DPM_CORE_EXTERNAL_HEDGE_READINESS_UNAVAILABLE",
            incomplete_code="DPM_CORE_EXTERNAL_HEDGE_READINESS_INCOMPLETE",
        )
        return DpmCoreExternalHedgeExecutionReadinessResponse.model_validate(response)

    def resolve_external_currency_exposure(
        self,
        *,
        portfolio_id: str,
        as_of_date: date,
        tenant_id: Optional[str] = None,
        mandate_id: Optional[str] = None,
        reporting_currency: Optional[str] = None,
        exposure_currencies: Optional[list[str]] = None,
        correlation_id: Optional[str],
    ) -> DpmCoreExternalCurrencyExposureResponse:
        url = self._config.resolve_external_currency_exposure_url(portfolio_id)
        payload = {
            "as_of_date": as_of_date.isoformat(),
            "tenant_id": tenant_id,
            "mandate_id": mandate_id,
            "reporting_currency": reporting_currency,
            "exposure_currencies": exposure_currencies or [],
        }
        response = self._post_source_product(
            url=url,
            payload=payload,
            correlation_id=correlation_id,
            unavailable_code="DPM_CORE_EXTERNAL_CURRENCY_EXPOSURE_UNAVAILABLE",
            incomplete_code="DPM_CORE_EXTERNAL_CURRENCY_EXPOSURE_INCOMPLETE",
        )
        return DpmCoreExternalCurrencyExposureResponse.model_validate(response)

    def resolve_external_hedge_policy(
        self,
        *,
        portfolio_id: str,
        as_of_date: date,
        tenant_id: Optional[str] = None,
        mandate_id: Optional[str] = None,
        reporting_currency: Optional[str] = None,
        exposure_currencies: Optional[list[str]] = None,
        correlation_id: Optional[str],
    ) -> DpmCoreExternalHedgePolicyResponse:
        url = self._config.resolve_external_hedge_policy_url(portfolio_id)
        payload = {
            "as_of_date": as_of_date.isoformat(),
            "tenant_id": tenant_id,
            "mandate_id": mandate_id,
            "reporting_currency": reporting_currency,
            "exposure_currencies": exposure_currencies or [],
        }
        response = self._post_source_product(
            url=url,
            payload=payload,
            correlation_id=correlation_id,
            unavailable_code="DPM_CORE_EXTERNAL_HEDGE_POLICY_UNAVAILABLE",
            incomplete_code="DPM_CORE_EXTERNAL_HEDGE_POLICY_INCOMPLETE",
        )
        return DpmCoreExternalHedgePolicyResponse.model_validate(response)

    def resolve_client_restriction_profile(
        self,
        *,
        portfolio_id: str,
        as_of_date: date,
        tenant_id: Optional[str] = None,
        mandate_id: Optional[str] = None,
        include_inactive_restrictions: bool = False,
        correlation_id: Optional[str],
    ) -> DpmCoreClientRestrictionProfileResponse:
        url = self._config.resolve_client_restriction_profile_url(portfolio_id)
        payload = {
            "as_of_date": as_of_date.isoformat(),
            "tenant_id": tenant_id,
            "mandate_id": mandate_id,
            "include_inactive_restrictions": include_inactive_restrictions,
        }
        response = self._post_source_product(
            url=url,
            payload=payload,
            correlation_id=correlation_id,
            unavailable_code="DPM_CORE_CLIENT_RESTRICTIONS_UNAVAILABLE",
            incomplete_code="DPM_CORE_CLIENT_RESTRICTIONS_INCOMPLETE",
        )
        return DpmCoreClientRestrictionProfileResponse.model_validate(response)

    def resolve_sustainability_preference_profile(
        self,
        *,
        portfolio_id: str,
        as_of_date: date,
        tenant_id: Optional[str] = None,
        mandate_id: Optional[str] = None,
        include_inactive_preferences: bool = False,
        correlation_id: Optional[str],
    ) -> DpmCoreSustainabilityPreferenceProfileResponse:
        url = self._config.resolve_sustainability_preference_profile_url(portfolio_id)
        payload = {
            "as_of_date": as_of_date.isoformat(),
            "tenant_id": tenant_id,
            "mandate_id": mandate_id,
            "include_inactive_preferences": include_inactive_preferences,
        }
        response = self._post_source_product(
            url=url,
            payload=payload,
            correlation_id=correlation_id,
            unavailable_code="DPM_CORE_SUSTAINABILITY_PREFERENCES_UNAVAILABLE",
            incomplete_code="DPM_CORE_SUSTAINABILITY_PREFERENCES_INCOMPLETE",
        )
        return DpmCoreSustainabilityPreferenceProfileResponse.model_validate(response)

    def _try_resolve_transaction_cost_curve(
        self,
        *,
        portfolio_id: str,
        as_of_date: date,
        security_ids: list[str],
        tenant_id: Optional[str],
        correlation_id: Optional[str],
    ) -> DpmCoreTransactionCostCurveResponse | None:
        if not security_ids:
            return None
        try:
            return self.resolve_transaction_cost_curve(
                portfolio_id=portfolio_id,
                as_of_date=as_of_date,
                window_start_date=as_of_date
                - timedelta(days=max(self._config.transaction_cost_lookback_days, 1)),
                window_end_date=as_of_date,
                security_ids=security_ids,
                transaction_types=["BUY", "SELL"],
                min_observation_count=1,
                tenant_id=tenant_id,
                correlation_id=correlation_id,
            )
        except DpmCoreResolverError:
            return None

    def _try_resolve_portfolio_cashflow_projection(
        self,
        *,
        portfolio_id: str,
        as_of_date: date,
        horizon_days: int,
        include_projected: bool,
        correlation_id: Optional[str],
    ) -> DpmCorePortfolioCashflowProjectionResponse | None:
        try:
            return self.resolve_portfolio_cashflow_projection(
                portfolio_id=portfolio_id,
                as_of_date=as_of_date,
                horizon_days=horizon_days,
                include_projected=include_projected,
                correlation_id=correlation_id,
            )
        except DpmCoreResolverError:
            return None

    def _try_resolve_client_income_needs_schedule(
        self,
        *,
        portfolio_id: str,
        as_of_date: date,
        tenant_id: Optional[str],
        mandate_id: Optional[str],
        correlation_id: Optional[str],
    ) -> DpmCoreClientIncomeNeedsScheduleResponse | None:
        try:
            return self.resolve_client_income_needs_schedule(
                portfolio_id=portfolio_id,
                as_of_date=as_of_date,
                tenant_id=tenant_id,
                mandate_id=mandate_id,
                include_inactive_schedules=False,
                correlation_id=correlation_id,
            )
        except DpmCoreResolverError:
            return None

    def _try_resolve_liquidity_reserve_requirement(
        self,
        *,
        portfolio_id: str,
        as_of_date: date,
        tenant_id: Optional[str],
        mandate_id: Optional[str],
        correlation_id: Optional[str],
    ) -> DpmCoreLiquidityReserveRequirementResponse | None:
        try:
            return self.resolve_liquidity_reserve_requirement(
                portfolio_id=portfolio_id,
                as_of_date=as_of_date,
                tenant_id=tenant_id,
                mandate_id=mandate_id,
                include_inactive_requirements=False,
                correlation_id=correlation_id,
            )
        except DpmCoreResolverError:
            return None

    def _try_resolve_planned_withdrawal_schedule(
        self,
        *,
        portfolio_id: str,
        as_of_date: date,
        tenant_id: Optional[str],
        mandate_id: Optional[str],
        horizon_days: int,
        correlation_id: Optional[str],
    ) -> DpmCorePlannedWithdrawalScheduleResponse | None:
        try:
            return self.resolve_planned_withdrawal_schedule(
                portfolio_id=portfolio_id,
                as_of_date=as_of_date,
                tenant_id=tenant_id,
                mandate_id=mandate_id,
                horizon_days=horizon_days,
                include_inactive_withdrawals=False,
                correlation_id=correlation_id,
            )
        except DpmCoreResolverError:
            return None

    def _try_resolve_external_hedge_execution_readiness(
        self,
        *,
        portfolio_id: str,
        as_of_date: date,
        tenant_id: Optional[str],
        mandate_id: Optional[str],
        reporting_currency: Optional[str],
        exposure_currencies: list[str],
        correlation_id: Optional[str],
    ) -> DpmCoreExternalHedgeExecutionReadinessResponse | None:
        try:
            return self.resolve_external_hedge_execution_readiness(
                portfolio_id=portfolio_id,
                as_of_date=as_of_date,
                tenant_id=tenant_id,
                mandate_id=mandate_id,
                reporting_currency=reporting_currency,
                exposure_currencies=exposure_currencies,
                correlation_id=correlation_id,
            )
        except DpmCoreResolverError:
            return None

    def _try_resolve_external_currency_exposure(
        self,
        *,
        portfolio_id: str,
        as_of_date: date,
        tenant_id: Optional[str],
        mandate_id: Optional[str],
        reporting_currency: Optional[str],
        exposure_currencies: list[str],
        correlation_id: Optional[str],
    ) -> DpmCoreExternalCurrencyExposureResponse | None:
        try:
            return self.resolve_external_currency_exposure(
                portfolio_id=portfolio_id,
                as_of_date=as_of_date,
                tenant_id=tenant_id,
                mandate_id=mandate_id,
                reporting_currency=reporting_currency,
                exposure_currencies=exposure_currencies,
                correlation_id=correlation_id,
            )
        except DpmCoreResolverError:
            return None

    def _try_resolve_external_hedge_policy(
        self,
        *,
        portfolio_id: str,
        as_of_date: date,
        tenant_id: Optional[str],
        mandate_id: Optional[str],
        reporting_currency: Optional[str],
        exposure_currencies: list[str],
        correlation_id: Optional[str],
    ) -> DpmCoreExternalHedgePolicyResponse | None:
        try:
            return self.resolve_external_hedge_policy(
                portfolio_id=portfolio_id,
                as_of_date=as_of_date,
                tenant_id=tenant_id,
                mandate_id=mandate_id,
                reporting_currency=reporting_currency,
                exposure_currencies=exposure_currencies,
                correlation_id=correlation_id,
            )
        except DpmCoreResolverError:
            return None

    def _try_resolve_client_restriction_profile(
        self,
        *,
        portfolio_id: str,
        as_of_date: date,
        tenant_id: Optional[str],
        mandate_id: Optional[str],
        correlation_id: Optional[str],
    ) -> DpmCoreClientRestrictionProfileResponse | None:
        try:
            return self.resolve_client_restriction_profile(
                portfolio_id=portfolio_id,
                as_of_date=as_of_date,
                tenant_id=tenant_id,
                mandate_id=mandate_id,
                include_inactive_restrictions=False,
                correlation_id=correlation_id,
            )
        except DpmCoreResolverError:
            return None

    def _try_resolve_sustainability_preference_profile(
        self,
        *,
        portfolio_id: str,
        as_of_date: date,
        tenant_id: Optional[str],
        mandate_id: Optional[str],
        correlation_id: Optional[str],
    ) -> DpmCoreSustainabilityPreferenceProfileResponse | None:
        try:
            return self.resolve_sustainability_preference_profile(
                portfolio_id=portfolio_id,
                as_of_date=as_of_date,
                tenant_id=tenant_id,
                mandate_id=mandate_id,
                include_inactive_preferences=False,
                correlation_id=correlation_id,
            )
        except DpmCoreResolverError:
            return None


def _portfolio_snapshot_from_core_snapshot(payload: dict[str, Any]) -> PortfolioSnapshot:
    sections = payload.get("sections") or {}
    rows = sections.get("positions_baseline") or []
    valuation_context = payload.get("valuation_context") or {}
    base_currency = str(
        valuation_context.get("portfolio_currency")
        or valuation_context.get("reporting_currency")
        or "USD"
    )

    positions: list[Position] = []
    cash_by_currency: dict[str, Decimal] = {}
    for row in rows:
        instrument_id = str(row.get("security_id") or row.get("instrument_id") or "").strip()
        if not instrument_id:
            continue
        quantity = Decimal(str(row.get("quantity") or "0"))
        currency = str(row.get("currency") or base_currency).upper()
        if instrument_id.startswith("CASH_"):
            cash_by_currency[currency] = cash_by_currency.get(currency, Decimal("0")) + quantity
            continue

        market_value = row.get("market_value_local")
        positions.append(
            Position(
                instrument_id=instrument_id,
                quantity=quantity,
                market_value=(
                    Money(amount=Decimal(str(market_value)), currency=currency)
                    if market_value is not None
                    else None
                ),
            )
        )

    return PortfolioSnapshot(
        snapshot_id=payload.get("snapshot_id")
        or f"PortfolioStateSnapshot:{payload.get('portfolio_id')}:{payload.get('as_of_date')}",
        portfolio_id=str(payload["portfolio_id"]),
        base_currency=base_currency,
        positions=positions,
        cash_balances=[
            CashBalance(currency=currency, amount=amount)
            for currency, amount in sorted(cash_by_currency.items())
        ],
    )


def _required_currency_pairs(
    *,
    portfolio_snapshot: PortfolioSnapshot,
    base_currency: str,
) -> list[tuple[str, str]]:
    base = base_currency.upper()
    currencies = {
        position.market_value.currency.upper()
        for position in portfolio_snapshot.positions
        if position.market_value is not None
    }
    currencies.update(cash.currency.upper() for cash in portfolio_snapshot.cash_balances)
    return sorted((currency, base) for currency in currencies if currency != base)
