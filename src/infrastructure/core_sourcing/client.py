from datetime import date, timedelta
from typing import Any, Literal, Optional, cast

import httpx

from src.core.dpm_source_context import (
    DpmCoreBenchmarkAssignmentResponse,
    DpmCoreExternalCurrencyExposureResponse,
    DpmCoreExternalEligibleHedgeInstrumentResponse,
    DpmCoreExternalFXForwardCurveResponse,
    DpmCoreExternalHedgeExecutionReadinessResponse,
    DpmCoreExternalHedgePolicyResponse,
    DpmCoreExternalOrderExecutionAcknowledgementResponse,
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
    DpmCorePortfolioUniverseCandidateResponse,
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
from src.core.models import PortfolioSnapshot
from src.infrastructure.core_sourcing.errors import (
    DpmCoreResolverError as DpmCoreResolverError,
    DpmCoreResolverUnavailableError as DpmCoreResolverUnavailableError,
)
from src.infrastructure.core_sourcing.resolver_config import (
    LEGACY_DPM_EXECUTION_CONTEXT_PATH as LEGACY_DPM_EXECUTION_CONTEXT_PATH,
    DpmCoreResolverConfig as DpmCoreResolverConfig,
)
from src.infrastructure.core_sourcing import snapshot_mapping as _snapshot_mapping


_SourceProductMethod = Literal["get", "post"]
_TRANSIENT_SOURCE_STATUS_CODES = frozenset({502, 503, 504})

_cash_balance_currencies = _snapshot_mapping.cash_balance_currencies
_core_snapshot_base_currency = _snapshot_mapping.core_snapshot_base_currency
_core_snapshot_row_currency = _snapshot_mapping.core_snapshot_row_currency
_held_instrument_ids = _snapshot_mapping.held_instrument_ids
_map_core_snapshot_row = _snapshot_mapping.map_core_snapshot_row
_portfolio_positions_and_cash_from_core_rows = (
    _snapshot_mapping.portfolio_positions_and_cash_from_core_rows
)
_portfolio_snapshot_from_core_snapshot = _snapshot_mapping.portfolio_snapshot_from_core_snapshot
_position_market_value_currencies = _snapshot_mapping.position_market_value_currencies
_required_currency_pairs = _snapshot_mapping.required_currency_pairs
_required_non_base_currencies = _snapshot_mapping.required_non_base_currencies


def _source_product_headers(correlation_id: Optional[str]) -> dict[str, str]:
    return {"X-Correlation-Id": correlation_id} if correlation_id else {}


def _source_product_response_payload(
    response: httpx.Response,
    *,
    incomplete_code: str,
) -> dict[str, Any]:
    response_payload = response.json()
    if not isinstance(response_payload, dict):
        raise DpmCoreResolverError(incomplete_code)
    return response_payload


def _raise_for_source_product_status(
    response: httpx.Response,
    *,
    unavailable_code: str,
    incomplete_code: str,
) -> None:
    if response.status_code >= 500:
        raise DpmCoreResolverUnavailableError(unavailable_code)
    if response.status_code >= 400:
        raise DpmCoreResolverError(incomplete_code)


def _source_product_request(
    client: Any,
    *,
    method: _SourceProductMethod,
    url: str,
    selector: dict[str, Any],
    headers: dict[str, str],
) -> httpx.Response:
    if method == "post":
        return cast(httpx.Response, client.post(url, json=selector, headers=headers))
    return cast(httpx.Response, client.get(url, params=selector, headers=headers))


def _final_source_product_attempt(*, attempt_index: int, attempts: int) -> bool:
    return attempt_index + 1 >= attempts


def _should_retry_transient_source_status(
    response: httpx.Response,
    *,
    attempt_index: int,
    attempts: int,
) -> bool:
    return (
        response.status_code in _TRANSIENT_SOURCE_STATUS_CODES
        and not _final_source_product_attempt(attempt_index=attempt_index, attempts=attempts)
    )


def _source_product_payload_with_retries(
    client: Any,
    *,
    attempts: int,
    method: _SourceProductMethod,
    url: str,
    selector: dict[str, Any],
    headers: dict[str, str],
    unavailable_code: str,
    incomplete_code: str,
) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            response = _source_product_request(
                client,
                method=method,
                url=url,
                selector=selector,
                headers=headers,
            )
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            last_error = exc
            if _final_source_product_attempt(attempt_index=attempt, attempts=attempts):
                raise DpmCoreResolverUnavailableError(unavailable_code) from exc
            continue
        if _should_retry_transient_source_status(
            response,
            attempt_index=attempt,
            attempts=attempts,
        ):
            continue
        _raise_for_source_product_status(
            response,
            unavailable_code=unavailable_code,
            incomplete_code=incomplete_code,
        )
        return _source_product_response_payload(response, incomplete_code=incomplete_code)
    raise DpmCoreResolverUnavailableError(unavailable_code) from last_error


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
        return self._request_source_product(
            method="post",
            url=url,
            selector=payload,
            correlation_id=correlation_id,
            unavailable_code=unavailable_code,
            incomplete_code=incomplete_code,
        )

    def _get_source_product(
        self,
        *,
        url: str,
        params: dict[str, Any],
        correlation_id: Optional[str],
        unavailable_code: str,
        incomplete_code: str,
    ) -> dict[str, Any]:
        return self._request_source_product(
            method="get",
            url=url,
            selector=params,
            correlation_id=correlation_id,
            unavailable_code=unavailable_code,
            incomplete_code=incomplete_code,
        )

    def _request_source_product(
        self,
        *,
        method: _SourceProductMethod,
        url: str,
        selector: dict[str, Any],
        correlation_id: Optional[str],
        unavailable_code: str,
        incomplete_code: str,
    ) -> dict[str, Any]:
        attempts = max(self._config.max_attempts, 1)
        headers = _source_product_headers(correlation_id)
        client = self._client or httpx.Client(timeout=self._config.timeout_seconds)
        try:
            return _source_product_payload_with_retries(
                client,
                attempts=attempts,
                method=method,
                url=url,
                selector=selector,
                headers=headers,
                unavailable_code=unavailable_code,
                incomplete_code=incomplete_code,
            )
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
        held_instrument_ids = _held_instrument_ids(portfolio_snapshot)
        requested_instrument_ids = _requested_execution_instrument_ids(
            portfolio_snapshot=portfolio_snapshot,
            model_targets=model_targets,
        )

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
        currency_pairs = _execution_context_currency_pairs(portfolio_snapshot)
        market_data = self.resolve_market_data_coverage(
            instrument_ids=requested_instrument_ids,
            currency_pairs=currency_pairs,
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
        exposure_currencies = _execution_context_exposure_currencies(currency_pairs)
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
        external_eligible_hedge_instruments = self._try_resolve_external_eligible_hedge_instruments(
            portfolio_id=stateful_input.portfolio_id,
            as_of_date=stateful_input.as_of,
            tenant_id=stateful_input.tenant_id,
            mandate_id=stateful_input.mandate_id,
            reporting_currency=portfolio_snapshot.base_currency,
            exposure_currencies=exposure_currencies,
            instrument_types=["FX_FORWARD", "FX_SWAP"],
            correlation_id=correlation_id,
        )
        external_fx_forward_curve = self._try_resolve_external_fx_forward_curve(
            portfolio_id=stateful_input.portfolio_id,
            as_of_date=stateful_input.as_of,
            tenant_id=stateful_input.tenant_id,
            mandate_id=stateful_input.mandate_id,
            reporting_currency=portfolio_snapshot.base_currency,
            exposure_currencies=exposure_currencies,
            correlation_id=correlation_id,
        )
        external_order_execution_acknowledgement = (
            self._try_resolve_external_order_execution_acknowledgement(
                portfolio_id=stateful_input.portfolio_id,
                as_of_date=stateful_input.as_of,
                tenant_id=stateful_input.tenant_id,
                mandate_id=stateful_input.mandate_id,
                correlation_id=correlation_id,
            )
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
            policy_context=_execution_context_policy(
                stateful_input=stateful_input,
                policy_context=policy_context,
            ),
            source_lineage=_execution_context_lineage(
                stateful_input=stateful_input,
                portfolio_snapshot=portfolio_snapshot,
                model_targets=model_targets,
                eligibility=eligibility,
                mandate=mandate,
            ),
            supportability=_ready_execution_context_supportability(),
            transaction_cost_curve=transaction_cost_curve,
            portfolio_cashflow_projection=portfolio_cashflow_projection,
            client_income_needs_schedule=client_income_needs_schedule,
            liquidity_reserve_requirement=liquidity_reserve_requirement,
            planned_withdrawal_schedule=planned_withdrawal_schedule,
            external_hedge_execution_readiness=external_hedge_execution_readiness,
            external_currency_exposure=external_currency_exposure,
            external_hedge_policy=external_hedge_policy,
            external_eligible_hedge_instruments=external_eligible_hedge_instruments,
            external_fx_forward_curve=external_fx_forward_curve,
            external_order_execution_acknowledgement=external_order_execution_acknowledgement,
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
    ) -> DpmCorePortfolioUniverseCandidateResponse:
        url = self._config.resolve_dpm_portfolio_universe_candidates_url()
        payload = {
            "as_of_date": as_of_date.isoformat(),
            "tenant_id": tenant_id,
            "booking_center_code": booking_center_code,
            "model_portfolio_ids": model_portfolio_ids or [],
            "include_inactive_mandates": include_inactive_mandates,
            "page": {
                "page_size": page_size,
                "page_token": page_token,
            },
        }
        response = self._post_source_product(
            url=url,
            payload=payload,
            correlation_id=correlation_id,
            unavailable_code="DPM_CORE_PORTFOLIO_UNIVERSE_UNAVAILABLE",
            incomplete_code="DPM_CORE_PORTFOLIO_UNIVERSE_INCOMPLETE",
        )
        return DpmCorePortfolioUniverseCandidateResponse.model_validate(response)

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
    ) -> DpmCoreExternalEligibleHedgeInstrumentResponse:
        url = self._config.resolve_external_eligible_hedge_instruments_url(portfolio_id)
        payload = {
            "as_of_date": as_of_date.isoformat(),
            "tenant_id": tenant_id,
            "mandate_id": mandate_id,
            "reporting_currency": reporting_currency,
            "exposure_currencies": exposure_currencies or [],
            "instrument_types": instrument_types or [],
        }
        response = self._post_source_product(
            url=url,
            payload=payload,
            correlation_id=correlation_id,
            unavailable_code="DPM_CORE_EXTERNAL_ELIGIBLE_HEDGE_INSTRUMENTS_UNAVAILABLE",
            incomplete_code="DPM_CORE_EXTERNAL_ELIGIBLE_HEDGE_INSTRUMENTS_INCOMPLETE",
        )
        return DpmCoreExternalEligibleHedgeInstrumentResponse.model_validate(response)

    def resolve_external_fx_forward_curve(
        self,
        *,
        portfolio_id: str,
        as_of_date: date,
        tenant_id: Optional[str] = None,
        mandate_id: Optional[str] = None,
        reporting_currency: Optional[str] = None,
        exposure_currencies: Optional[list[str]] = None,
        correlation_id: Optional[str],
    ) -> DpmCoreExternalFXForwardCurveResponse:
        url = self._config.resolve_external_fx_forward_curve_url()
        payload = {
            "portfolio_id": portfolio_id,
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
            unavailable_code="DPM_CORE_EXTERNAL_FX_FORWARD_CURVE_UNAVAILABLE",
            incomplete_code="DPM_CORE_EXTERNAL_FX_FORWARD_CURVE_INCOMPLETE",
        )
        return DpmCoreExternalFXForwardCurveResponse.model_validate(response)

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
    ) -> DpmCoreExternalOrderExecutionAcknowledgementResponse:
        url = self._config.resolve_external_order_execution_acknowledgement_url(portfolio_id)
        payload = {
            "as_of_date": as_of_date.isoformat(),
            "tenant_id": tenant_id,
            "mandate_id": mandate_id,
            "execution_intent_id": execution_intent_id,
            "order_reference_ids": order_reference_ids or [],
        }
        response = self._post_source_product(
            url=url,
            payload=payload,
            correlation_id=correlation_id,
            unavailable_code="DPM_CORE_EXTERNAL_ORDER_EXECUTION_ACKNOWLEDGEMENT_UNAVAILABLE",
            incomplete_code="DPM_CORE_EXTERNAL_ORDER_EXECUTION_ACKNOWLEDGEMENT_INCOMPLETE",
        )
        return DpmCoreExternalOrderExecutionAcknowledgementResponse.model_validate(response)

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

    def _try_resolve_external_eligible_hedge_instruments(
        self,
        *,
        portfolio_id: str,
        as_of_date: date,
        tenant_id: Optional[str],
        mandate_id: Optional[str],
        reporting_currency: Optional[str],
        exposure_currencies: list[str],
        instrument_types: list[str],
        correlation_id: Optional[str],
    ) -> DpmCoreExternalEligibleHedgeInstrumentResponse | None:
        try:
            return self.resolve_external_eligible_hedge_instruments(
                portfolio_id=portfolio_id,
                as_of_date=as_of_date,
                tenant_id=tenant_id,
                mandate_id=mandate_id,
                reporting_currency=reporting_currency,
                exposure_currencies=exposure_currencies,
                instrument_types=instrument_types,
                correlation_id=correlation_id,
            )
        except DpmCoreResolverError:
            return None

    def _try_resolve_external_fx_forward_curve(
        self,
        *,
        portfolio_id: str,
        as_of_date: date,
        tenant_id: Optional[str],
        mandate_id: Optional[str],
        reporting_currency: Optional[str],
        exposure_currencies: list[str],
        correlation_id: Optional[str],
    ) -> DpmCoreExternalFXForwardCurveResponse | None:
        try:
            return self.resolve_external_fx_forward_curve(
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

    def _try_resolve_external_order_execution_acknowledgement(
        self,
        *,
        portfolio_id: str,
        as_of_date: date,
        tenant_id: Optional[str],
        mandate_id: Optional[str],
        correlation_id: Optional[str],
    ) -> DpmCoreExternalOrderExecutionAcknowledgementResponse | None:
        try:
            return self.resolve_external_order_execution_acknowledgement(
                portfolio_id=portfolio_id,
                as_of_date=as_of_date,
                tenant_id=tenant_id,
                mandate_id=mandate_id,
                execution_intent_id=None,
                order_reference_ids=[],
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


def _requested_execution_instrument_ids(
    *,
    portfolio_snapshot: PortfolioSnapshot,
    model_targets: DpmCoreModelPortfolioTargetResponse,
) -> list[str]:
    held_instrument_ids = _held_instrument_ids(portfolio_snapshot)
    target_instrument_ids = [target.instrument_id for target in model_targets.targets]
    return sorted(set(held_instrument_ids + target_instrument_ids))


def _execution_context_currency_pairs(
    portfolio_snapshot: PortfolioSnapshot,
) -> list[tuple[str, str]]:
    return _required_currency_pairs(
        portfolio_snapshot=portfolio_snapshot,
        base_currency=portfolio_snapshot.base_currency,
    )


def _execution_context_exposure_currencies(
    currency_pairs: list[tuple[str, str]],
) -> list[str]:
    return sorted({source_currency for source_currency, _ in currency_pairs})


def _execution_context_policy(
    *,
    stateful_input: DpmStatefulInput,
    policy_context: DpmCorePolicyContext,
) -> DpmCorePolicyContext:
    return DpmCorePolicyContext(
        recommended_policy_pack_id=(
            stateful_input.policy_pack_id or policy_context.recommended_policy_pack_id
        ),
        tenant_id=policy_context.tenant_id,
        booking_center_code=policy_context.booking_center_code,
        mandate_id=policy_context.mandate_id,
    )


def _execution_context_lineage(
    *,
    stateful_input: DpmStatefulInput,
    portfolio_snapshot: PortfolioSnapshot,
    model_targets: DpmCoreModelPortfolioTargetResponse,
    eligibility: DpmCoreInstrumentEligibilityBulkResponse,
    mandate: DpmCoreMandateBindingResponse,
) -> DpmCoreSourceLineage:
    as_of_date = stateful_input.as_of.isoformat()
    return DpmCoreSourceLineage(
        portfolio_snapshot_id=portfolio_snapshot.snapshot_id
        or f"core-snapshot:{stateful_input.portfolio_id}:{as_of_date}",
        market_data_snapshot_id=f"market-data-coverage:{as_of_date}",
        model_portfolio_id=model_targets.model_portfolio_id,
        model_portfolio_version=model_targets.model_portfolio_version,
        shelf_version=eligibility.lineage.get("contract_version"),
        integration_policy_version=mandate.lineage.get("contract_version"),
        source_lineage_bundle_id=f"rfc-087:{stateful_input.portfolio_id}:{as_of_date}",
    )


def _ready_execution_context_supportability() -> DpmCoreSupportability:
    return DpmCoreSupportability(
        state="READY",
        reason="DPM_CORE_CONTEXT_READY",
        freshness_bucket="current",
        missing_source_families=[],
        degraded_source_families=[],
    )
