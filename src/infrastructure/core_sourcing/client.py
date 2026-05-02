from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any, Optional

import httpx

from src.core.dpm_source_context import (
    DpmCoreExecutionContext,
    DpmCoreInstrumentEligibilityBulkResponse,
    DpmCoreMandateBindingResponse,
    DpmCoreMarketDataCoverageWindowResponse,
    DpmCoreModelPortfolioTargetResponse,
    DpmCorePortfolioTaxLotWindowResponse,
    DpmCorePolicyContext,
    DpmCoreSourceLineage,
    DpmCoreSupportability,
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
    path_template: str = ""
    model_portfolio_targets_path_template: str = (
        "/integration/model-portfolios/{model_portfolio_id}/targets"
    )
    mandate_binding_path_template: str = "/integration/portfolios/{portfolio_id}/mandate-binding"
    instrument_eligibility_path_template: str = "/integration/instruments/eligibility-bulk"
    portfolio_tax_lots_path_template: str = "/integration/portfolios/{portfolio_id}/tax-lots"
    market_data_coverage_path_template: str = "/integration/market-data/coverage"
    portfolio_snapshot_path_template: str = "/integration/portfolios/{portfolio_id}/core-snapshot"
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

    def resolve_portfolio_snapshot_url(self, portfolio_id: str) -> str:
        path_template = self.portfolio_snapshot_path_template.strip()
        if not path_template:
            raise DpmCoreResolverUnavailableError("DPM_CORE_RESOLVER_UNAVAILABLE")
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
        )

    def resolve_portfolio_snapshot(
        self,
        *,
        portfolio_id: str,
        as_of_date: date,
        consumer_system: str,
        correlation_id: Optional[str],
    ) -> PortfolioSnapshot:
        attempts = max(self._config.max_attempts, 1)
        url = self._config.resolve_portfolio_snapshot_url(portfolio_id)
        payload = {
            "as_of_date": as_of_date.isoformat(),
            "consumer_system": consumer_system,
            "sections": ["positions_baseline", "portfolio_totals"],
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
                        raise DpmCoreResolverUnavailableError("DPM_CORE_RESOLVER_UNAVAILABLE")
                    if response.status_code >= 400:
                        raise DpmCoreResolverError("DPM_CORE_CONTEXT_INCOMPLETE")
                    return _portfolio_snapshot_from_core_snapshot(response.json())
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
