from dataclasses import dataclass
from datetime import date
from typing import Optional

import httpx

from src.core.dpm_source_context import (
    DpmCoreExecutionContext,
    DpmCoreInstrumentEligibilityBulkResponse,
    DpmCoreMandateBindingResponse,
    DpmCoreMarketDataCoverageWindowResponse,
    DpmCoreModelPortfolioTargetResponse,
    DpmCorePortfolioTaxLotWindowResponse,
    DpmStatefulInput,
    build_core_resolver_payload,
)


class DpmCoreResolverError(RuntimeError):
    pass


class DpmCoreResolverUnavailableError(DpmCoreResolverError):
    pass


LEGACY_DPM_EXECUTION_CONTEXT_PATH = "/integration/portfolios/{portfolio_id}/dpm-execution-context"


@dataclass(frozen=True)
class DpmCoreResolverConfig:
    base_url: str
    path_template: str = ""
    model_portfolio_targets_path_template: str = (
        "/integration/model-portfolios/{model_portfolio_id}/targets"
    )
    mandate_binding_path_template: str = "/integration/portfolios/{portfolio_id}/mandate-binding"
    instrument_eligibility_path_template: str = "/integration/instruments/eligibility-bulk"
    portfolio_tax_lots_path_template: str = "/integration/portfolios/{portfolio_id}/tax-lots"
    market_data_coverage_path_template: str = "/integration/market-data/coverage"
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

    def resolve_execution_context(
        self,
        *,
        stateful_input: DpmStatefulInput,
        correlation_id: Optional[str],
    ) -> DpmCoreExecutionContext:
        attempts = max(self._config.max_attempts, 1)
        url = self._config.resolve_url(stateful_input.portfolio_id)
        payload = build_core_resolver_payload(stateful_input)
        headers = {}
        if correlation_id:
            headers["X-Correlation-Id"] = correlation_id

        client = self._client or httpx.Client(timeout=self._config.timeout_seconds)
        try:
            last_error: Exception | None = None
            for attempt in range(attempts):
                try:
                    response = client.post(url, json=payload, headers=headers)
                    if response.status_code in {502, 503, 504} and attempt + 1 < attempts:
                        continue
                    if response.status_code >= 500:
                        raise DpmCoreResolverUnavailableError("DPM_CORE_RESOLVER_UNAVAILABLE")
                    if response.status_code >= 400:
                        raise DpmCoreResolverError("DPM_CORE_CONTEXT_INCOMPLETE")
                    return DpmCoreExecutionContext.model_validate(response.json())
                except (httpx.TimeoutException, httpx.TransportError) as exc:
                    last_error = exc
                    if attempt + 1 >= attempts:
                        raise DpmCoreResolverUnavailableError(
                            "DPM_CORE_RESOLVER_UNAVAILABLE"
                        ) from exc
            raise DpmCoreResolverUnavailableError("DPM_CORE_RESOLVER_UNAVAILABLE") from last_error
        finally:
            if self._owns_client:
                client.close()

    def resolve_model_portfolio_targets(
        self,
        *,
        model_portfolio_id: str,
        as_of_date: date,
        include_inactive_targets: bool = False,
        tenant_id: Optional[str] = None,
        correlation_id: Optional[str],
    ) -> DpmCoreModelPortfolioTargetResponse:
        attempts = max(self._config.max_attempts, 1)
        url = self._config.resolve_model_portfolio_targets_url(model_portfolio_id)
        payload = {
            "as_of_date": as_of_date.isoformat(),
            "include_inactive_targets": include_inactive_targets,
            "tenant_id": tenant_id,
        }
        headers = {}
        if correlation_id:
            headers["X-Correlation-Id"] = correlation_id

        client = self._client or httpx.Client(timeout=self._config.timeout_seconds)
        try:
            last_error: Exception | None = None
            for attempt in range(attempts):
                try:
                    response = client.post(url, json=payload, headers=headers)
                    if response.status_code in {502, 503, 504} and attempt + 1 < attempts:
                        continue
                    if response.status_code >= 500:
                        raise DpmCoreResolverUnavailableError(
                            "DPM_CORE_MODEL_TARGET_RESOLVER_UNAVAILABLE"
                        )
                    if response.status_code >= 400:
                        raise DpmCoreResolverError("DPM_CORE_MODEL_TARGETS_INCOMPLETE")
                    return DpmCoreModelPortfolioTargetResponse.model_validate(response.json())
                except (httpx.TimeoutException, httpx.TransportError) as exc:
                    last_error = exc
                    if attempt + 1 >= attempts:
                        raise DpmCoreResolverUnavailableError(
                            "DPM_CORE_MODEL_TARGET_RESOLVER_UNAVAILABLE"
                        ) from exc
            raise DpmCoreResolverUnavailableError(
                "DPM_CORE_MODEL_TARGET_RESOLVER_UNAVAILABLE"
            ) from last_error
        finally:
            if self._owns_client:
                client.close()

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
        attempts = max(self._config.max_attempts, 1)
        url = self._config.resolve_mandate_binding_url(portfolio_id)
        payload = {
            "as_of_date": as_of_date.isoformat(),
            "tenant_id": tenant_id,
            "mandate_id": mandate_id,
            "booking_center_code": booking_center_code,
            "include_policy_pack": include_policy_pack,
        }
        headers = {}
        if correlation_id:
            headers["X-Correlation-Id"] = correlation_id

        client = self._client or httpx.Client(timeout=self._config.timeout_seconds)
        try:
            last_error: Exception | None = None
            for attempt in range(attempts):
                try:
                    response = client.post(url, json=payload, headers=headers)
                    if response.status_code in {502, 503, 504} and attempt + 1 < attempts:
                        continue
                    if response.status_code >= 500:
                        raise DpmCoreResolverUnavailableError(
                            "DPM_CORE_MANDATE_BINDING_UNAVAILABLE"
                        )
                    if response.status_code >= 400:
                        raise DpmCoreResolverError("DPM_CORE_MANDATE_BINDING_INCOMPLETE")
                    return DpmCoreMandateBindingResponse.model_validate(response.json())
                except (httpx.TimeoutException, httpx.TransportError) as exc:
                    last_error = exc
                    if attempt + 1 >= attempts:
                        raise DpmCoreResolverUnavailableError(
                            "DPM_CORE_MANDATE_BINDING_UNAVAILABLE"
                        ) from exc
            raise DpmCoreResolverUnavailableError(
                "DPM_CORE_MANDATE_BINDING_UNAVAILABLE"
            ) from last_error
        finally:
            if self._owns_client:
                client.close()

    def resolve_instrument_eligibility(
        self,
        *,
        security_ids: list[str],
        as_of_date: date,
        tenant_id: Optional[str] = None,
        include_restricted_rationale: bool = False,
        correlation_id: Optional[str],
    ) -> DpmCoreInstrumentEligibilityBulkResponse:
        attempts = max(self._config.max_attempts, 1)
        url = self._config.resolve_instrument_eligibility_url()
        payload = {
            "as_of_date": as_of_date.isoformat(),
            "security_ids": security_ids,
            "tenant_id": tenant_id,
            "include_restricted_rationale": include_restricted_rationale,
        }
        headers = {}
        if correlation_id:
            headers["X-Correlation-Id"] = correlation_id

        client = self._client or httpx.Client(timeout=self._config.timeout_seconds)
        try:
            last_error: Exception | None = None
            for attempt in range(attempts):
                try:
                    response = client.post(url, json=payload, headers=headers)
                    if response.status_code in {502, 503, 504} and attempt + 1 < attempts:
                        continue
                    if response.status_code >= 500:
                        raise DpmCoreResolverUnavailableError(
                            "DPM_CORE_INSTRUMENT_ELIGIBILITY_UNAVAILABLE"
                        )
                    if response.status_code >= 400:
                        raise DpmCoreResolverError("DPM_CORE_INSTRUMENT_ELIGIBILITY_INCOMPLETE")
                    return DpmCoreInstrumentEligibilityBulkResponse.model_validate(response.json())
                except (httpx.TimeoutException, httpx.TransportError) as exc:
                    last_error = exc
                    if attempt + 1 >= attempts:
                        raise DpmCoreResolverUnavailableError(
                            "DPM_CORE_INSTRUMENT_ELIGIBILITY_UNAVAILABLE"
                        ) from exc
            raise DpmCoreResolverUnavailableError(
                "DPM_CORE_INSTRUMENT_ELIGIBILITY_UNAVAILABLE"
            ) from last_error
        finally:
            if self._owns_client:
                client.close()

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
        attempts = max(self._config.max_attempts, 1)
        url = self._config.resolve_portfolio_tax_lots_url(portfolio_id)
        payload = {
            "as_of_date": as_of_date.isoformat(),
            "security_ids": security_ids,
            "lot_status_filter": lot_status_filter,
            "include_closed_lots": include_closed_lots,
            "page": {"page_size": page_size, "page_token": page_token},
            "tenant_id": tenant_id,
        }
        headers = {}
        if correlation_id:
            headers["X-Correlation-Id"] = correlation_id

        client = self._client or httpx.Client(timeout=self._config.timeout_seconds)
        try:
            last_error: Exception | None = None
            for attempt in range(attempts):
                try:
                    response = client.post(url, json=payload, headers=headers)
                    if response.status_code in {502, 503, 504} and attempt + 1 < attempts:
                        continue
                    if response.status_code >= 500:
                        raise DpmCoreResolverUnavailableError(
                            "DPM_CORE_PORTFOLIO_TAX_LOTS_UNAVAILABLE"
                        )
                    if response.status_code >= 400:
                        raise DpmCoreResolverError("DPM_CORE_PORTFOLIO_TAX_LOTS_INCOMPLETE")
                    return DpmCorePortfolioTaxLotWindowResponse.model_validate(response.json())
                except (httpx.TimeoutException, httpx.TransportError) as exc:
                    last_error = exc
                    if attempt + 1 >= attempts:
                        raise DpmCoreResolverUnavailableError(
                            "DPM_CORE_PORTFOLIO_TAX_LOTS_UNAVAILABLE"
                        ) from exc
            raise DpmCoreResolverUnavailableError(
                "DPM_CORE_PORTFOLIO_TAX_LOTS_UNAVAILABLE"
            ) from last_error
        finally:
            if self._owns_client:
                client.close()

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
        attempts = max(self._config.max_attempts, 1)
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
        headers = {}
        if correlation_id:
            headers["X-Correlation-Id"] = correlation_id

        client = self._client or httpx.Client(timeout=self._config.timeout_seconds)
        try:
            last_error: Exception | None = None
            for attempt in range(attempts):
                try:
                    response = client.post(url, json=payload, headers=headers)
                    if response.status_code in {502, 503, 504} and attempt + 1 < attempts:
                        continue
                    if response.status_code >= 500:
                        raise DpmCoreResolverUnavailableError(
                            "DPM_CORE_MARKET_DATA_COVERAGE_UNAVAILABLE"
                        )
                    if response.status_code >= 400:
                        raise DpmCoreResolverError("DPM_CORE_MARKET_DATA_COVERAGE_INCOMPLETE")
                    return DpmCoreMarketDataCoverageWindowResponse.model_validate(response.json())
                except (httpx.TimeoutException, httpx.TransportError) as exc:
                    last_error = exc
                    if attempt + 1 >= attempts:
                        raise DpmCoreResolverUnavailableError(
                            "DPM_CORE_MARKET_DATA_COVERAGE_UNAVAILABLE"
                        ) from exc
            raise DpmCoreResolverUnavailableError(
                "DPM_CORE_MARKET_DATA_COVERAGE_UNAVAILABLE"
            ) from last_error
        finally:
            if self._owns_client:
                client.close()
