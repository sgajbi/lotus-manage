from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any, Optional

import httpx

from src.core.construction.models import AuthoritativeRegimeStressContext, AuthoritativeRiskContext
from src.core.construction.vocabulary import ConstructionMethodStatus
from src.core.models import RebalanceResult


class LotusRiskAuthorityUnavailableError(RuntimeError):
    pass


@dataclass(frozen=True)
class LotusRiskAuthorityConfig:
    base_url: str
    concentration_path: str = "/analytics/risk/concentration"
    regime_scenario_pack_path: str = "/analytics/risk/regime-scenario-pack/evaluate"
    risk_event_cohort_path: str = "/analytics/risk/risk-event-cohorts/evaluate"
    timeout_seconds: float = 2.0
    max_attempts: int = 2

    def concentration_url(self) -> str:
        return f"{self.base_url.rstrip('/')}/{self.concentration_path.lstrip('/')}"

    def regime_scenario_pack_url(self) -> str:
        return f"{self.base_url.rstrip('/')}/{self.regime_scenario_pack_path.lstrip('/')}"

    def risk_event_cohort_url(self) -> str:
        return f"{self.base_url.rstrip('/')}/{self.risk_event_cohort_path.lstrip('/')}"


@dataclass(frozen=True)
class RiskEventAffectedPortfolio:
    portfolio_id: str
    mandate_id: str | None
    source_ref: str
    reason_codes: tuple[str, ...]
    impact_score: Decimal
    dominant_bucket: str


@dataclass(frozen=True)
class RiskEventAffectedCohort:
    cohort_id: str
    risk_event_id: str
    display_name: str
    product_name: str
    product_version: str
    source_service: str
    request_fingerprint: str
    calculation_supportability: str
    reason_codes: tuple[str, ...]
    affected_portfolios: tuple[RiskEventAffectedPortfolio, ...]


class LotusRiskAuthorityClient:
    """Bounded client for lotus-risk authority outputs used by construction.

    Manage consumes supportability and concentration outputs. It does not copy risk
    methodology or compute risk formulas locally.
    """

    def __init__(
        self,
        *,
        config: LotusRiskAuthorityConfig,
        client: Optional[httpx.Client] = None,
    ) -> None:
        self._config = config
        self._client = client
        self._owns_client = client is None

    def close(self) -> None:
        if self._owns_client and self._client is not None:
            self._client.close()

    def concentration_context(
        self,
        *,
        result: RebalanceResult,
        correlation_id: str | None,
    ) -> AuthoritativeRiskContext:
        payload = _concentration_payload(result=result)
        headers = {"X-Correlation-Id": correlation_id} if correlation_id else {}
        client = self._client or httpx.Client(timeout=self._config.timeout_seconds)
        try:
            response_payload = _post_with_retries(
                client=client,
                url=self._config.concentration_url(),
                payload=payload,
                headers=headers,
                attempts=max(self._config.max_attempts, 1),
            )
        finally:
            if self._owns_client:
                client.close()
        return _risk_context_from_concentration_response(response_payload)

    def regime_scenario_context(
        self,
        *,
        result: RebalanceResult,
        portfolio_id: str,
        as_of_date: date,
        correlation_id: str | None,
        scenario_pack_id: str = "CIO_REGIME_2026_Q2",
        maximum_allowed_loss_pct: Decimal = Decimal("0.12"),
    ) -> AuthoritativeRegimeStressContext:
        payload = _regime_scenario_payload(
            result=result,
            portfolio_id=portfolio_id,
            as_of_date=as_of_date,
            scenario_pack_id=scenario_pack_id,
            maximum_allowed_loss_pct=maximum_allowed_loss_pct,
        )
        headers = {"X-Correlation-Id": correlation_id} if correlation_id else {}
        client = self._client or httpx.Client(timeout=self._config.timeout_seconds)
        try:
            response_payload = _post_with_retries(
                client=client,
                url=self._config.regime_scenario_pack_url(),
                payload=payload,
                headers=headers,
                attempts=max(self._config.max_attempts, 1),
                rejected_error="LOTUS_RISK_REGIME_SCENARIO_REJECTED",
            )
        finally:
            if self._owns_client:
                client.close()
        return _regime_context_from_scenario_response(response_payload)

    def risk_event_affected_cohort(
        self,
        *,
        risk_event_id: str,
        as_of_date: date,
        portfolios: list[dict[str, Any]],
        minimum_impact_score: Decimal,
        correlation_id: str | None,
    ) -> RiskEventAffectedCohort:
        payload = {
            "risk_event_id": risk_event_id,
            "as_of_date": as_of_date.isoformat(),
            "portfolios": portfolios,
            "minimum_impact_score": float(minimum_impact_score),
        }
        headers = {"X-Correlation-Id": correlation_id} if correlation_id else {}
        client = self._client or httpx.Client(timeout=self._config.timeout_seconds)
        try:
            response_payload = _post_with_retries(
                client=client,
                url=self._config.risk_event_cohort_url(),
                payload=payload,
                headers=headers,
                attempts=max(self._config.max_attempts, 1),
                rejected_error="LOTUS_RISK_EVENT_COHORT_REJECTED",
            )
        finally:
            if self._owns_client:
                client.close()
        return _risk_event_cohort_from_response(response_payload)


def _post_with_retries(
    *,
    client: httpx.Client,
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    attempts: int,
    rejected_error: str = "LOTUS_RISK_CONCENTRATION_REJECTED",
) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            response = client.post(url, json=payload, headers=headers)
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            last_error = exc
            if attempt + 1 >= attempts:
                raise LotusRiskAuthorityUnavailableError("LOTUS_RISK_UNAVAILABLE") from exc
            continue
        if response.status_code in {502, 503, 504} and attempt + 1 < attempts:
            continue
        if response.status_code >= 500:
            raise LotusRiskAuthorityUnavailableError("LOTUS_RISK_UNAVAILABLE")
        if response.status_code >= 400:
            raise LotusRiskAuthorityUnavailableError(rejected_error)
        try:
            body = response.json()
        except ValueError as exc:
            raise LotusRiskAuthorityUnavailableError("LOTUS_RISK_INVALID_RESPONSE") from exc
        if not isinstance(body, dict):
            raise LotusRiskAuthorityUnavailableError("LOTUS_RISK_INVALID_RESPONSE")
        return body
    raise LotusRiskAuthorityUnavailableError("LOTUS_RISK_UNAVAILABLE") from last_error


def _concentration_payload(*, result: RebalanceResult) -> dict[str, Any]:
    return {
        "input_mode": "stateless",
        "issuer_grouping_level": "ultimate_parent",
        "enrichment_policy": "use_caller_only",
        "stateless_input": {
            "current_positions": [
                {
                    "security_id": position.instrument_id,
                    "quantity": str(position.quantity),
                    "market_value_base": str(position.value_in_base_ccy.amount),
                    "weight": str(position.weight),
                }
                for position in result.before.positions
            ],
            "projected_positions": [
                {
                    "security_id": position.instrument_id,
                    "proposed_quantity": str(position.quantity),
                    "projected_market_value_base": str(position.value_in_base_ccy.amount),
                    "projected_weight": str(position.weight),
                }
                for position in result.after_simulated.positions
            ],
            "top_n": 10,
        },
    }


def _regime_scenario_payload(
    *,
    result: RebalanceResult,
    portfolio_id: str,
    as_of_date: date,
    scenario_pack_id: str,
    maximum_allowed_loss_pct: Decimal,
) -> dict[str, Any]:
    return {
        "scenario_pack_id": scenario_pack_id,
        "portfolio_id": portfolio_id,
        "as_of_date": as_of_date.isoformat(),
        "maximum_allowed_loss_pct": float(maximum_allowed_loss_pct),
        "exposures": [
            {
                "bucket": _scenario_bucket(allocation.key),
                "weight": float(allocation.weight),
            }
            for allocation in result.after_simulated.allocation_by_asset_class
            if allocation.weight > Decimal("0")
        ],
    }


def _risk_context_from_concentration_response(body: dict[str, Any]) -> AuthoritativeRiskContext:
    metadata = _dict_section(body, "metadata")
    supportability = _dict_section(metadata, "calculation_supportability")
    request_fingerprint = str(metadata.get("request_fingerprint") or "")
    risk_proxy = _dict_section(body, "risk_proxy")
    single_position = _dict_section(body, "single_position_concentration")
    issuer = _dict_section(body, "issuer_concentration")
    state = str(supportability.get("state", "degraded"))
    reason = str(supportability.get("reason", "calculation_supportability_missing"))
    coverage_status = issuer.get("coverage_status")
    breaches = 0
    if Decimal(str(single_position.get("top_position_weight_proposed", "0"))) > Decimal("0.30"):
        breaches += 1
    if Decimal(str(issuer.get("top_issuer_weight_proposed", "0"))) > Decimal("0.40"):
        breaches += 1
    if Decimal(str(risk_proxy.get("hhi_proposed", "0"))) > Decimal("2500"):
        breaches += 1
    reason_codes = [f"LOTUS_RISK_CONCENTRATION_{reason.upper()}"]
    if coverage_status and coverage_status != "complete":
        reason_codes.append(f"ISSUER_COVERAGE_{str(coverage_status).upper()}")
    if breaches:
        reason_codes.append("RISK_CONCENTRATION_LIMIT_BREACH")
    return AuthoritativeRiskContext(
        supportability_status=_risk_status_from_supportability(state),
        source_system=str(body.get("source_service") or "lotus-risk"),
        source_product_name="ConcentrationAnalysis",
        source_product_version=str(metadata.get("methodology_version") or "v1"),
        source_id=request_fingerprint or None,
        content_hash=request_fingerprint or None,
        concentration_breaches=breaches,
        concentration_hhi_delta=Decimal(str(risk_proxy.get("hhi_delta", "0"))),
        top_position_weight_proposed=Decimal(
            str(single_position.get("top_position_weight_proposed", "0"))
        ),
        issuer_coverage_status=str(coverage_status) if coverage_status is not None else None,
        reason_codes=sorted(set(reason_codes)),
    )


def _regime_context_from_scenario_response(
    body: dict[str, Any],
) -> AuthoritativeRegimeStressContext:
    try:
        metadata = _dict_section(body, "metadata")
        supportability = str(metadata.get("calculation_supportability", "degraded"))
        reason_codes = body.get("reason_codes")
        if not isinstance(reason_codes, list):
            reason_codes = ["REGIME_SCENARIO_PACK_RESPONSE_REASON_CODES_MISSING"]
        return AuthoritativeRegimeStressContext(
            supportability_status=_scenario_status_from_supportability(supportability),
            source_system=str(metadata.get("source_service") or "lotus-risk"),
            scenario_pack_id=str(body["scenario_pack_id"]),
            worst_case_loss_pct=Decimal(str(body["worst_case_loss_pct"])),
            maximum_allowed_loss_pct=Decimal(str(body["maximum_allowed_loss_pct"])),
            reason_codes=sorted({str(reason_code) for reason_code in reason_codes}),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise LotusRiskAuthorityUnavailableError("LOTUS_RISK_INVALID_RESPONSE") from exc


def _risk_event_cohort_from_response(body: dict[str, Any]) -> RiskEventAffectedCohort:
    try:
        metadata = _dict_section(body, "metadata")
        affected_payload = body.get("affected_portfolios")
        if not isinstance(affected_payload, list):
            raise ValueError("affected_portfolios must be a list")
        reason_codes = body.get("reason_codes")
        if not isinstance(reason_codes, list):
            reason_codes = ["RISK_EVENT_COHORT_REASON_CODES_MISSING"]
        if not all(isinstance(portfolio, dict) for portfolio in affected_payload):
            raise ValueError("affected_portfolios entries must be objects")
        affected = tuple(
            RiskEventAffectedPortfolio(
                portfolio_id=str(portfolio["portfolio_id"]),
                mandate_id=(
                    str(portfolio["mandate_id"])
                    if portfolio.get("mandate_id") is not None
                    else None
                ),
                source_ref=str(portfolio["source_ref"]),
                reason_codes=tuple(str(code) for code in portfolio.get("reason_codes", [])),
                impact_score=Decimal(str(portfolio["impact_score"])),
                dominant_bucket=str(portfolio["dominant_bucket"]),
            )
            for portfolio in affected_payload
        )
        return RiskEventAffectedCohort(
            cohort_id=str(body["cohort_id"]),
            risk_event_id=str(body["risk_event_id"]),
            display_name=str(body["display_name"]),
            product_name=str(metadata.get("product_name") or "RiskEventAffectedCohort"),
            product_version=str(metadata.get("product_version") or "v1"),
            source_service=str(metadata.get("source_service") or "lotus-risk"),
            request_fingerprint=str(metadata.get("request_fingerprint") or ""),
            calculation_supportability=str(metadata.get("calculation_supportability") or "blocked"),
            reason_codes=tuple(str(code) for code in reason_codes),
            affected_portfolios=affected,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise LotusRiskAuthorityUnavailableError("LOTUS_RISK_INVALID_RESPONSE") from exc


def _risk_status_from_supportability(state: str) -> ConstructionMethodStatus:
    if state == "ready":
        return ConstructionMethodStatus.READY
    if state in {"stale", "degraded"}:
        return ConstructionMethodStatus.DEGRADED
    if state == "empty":
        return ConstructionMethodStatus.PENDING_REVIEW
    return ConstructionMethodStatus.BLOCKED


def _scenario_status_from_supportability(state: str) -> ConstructionMethodStatus:
    if state == "ready":
        return ConstructionMethodStatus.READY
    if state == "pending_review":
        return ConstructionMethodStatus.PENDING_REVIEW
    if state == "degraded":
        return ConstructionMethodStatus.DEGRADED
    return ConstructionMethodStatus.BLOCKED


def _scenario_bucket(asset_class: str) -> str:
    normalized = asset_class.strip().upper().replace("-", "_").replace(" ", "_")
    if normalized in {"EQUITY", "EQUITIES", "STOCK", "STOCKS"}:
        return "EQUITY"
    if normalized in {"FIXED_INCOME", "FIXEDINCOME", "BOND", "BONDS"}:
        return "FIXED_INCOME"
    if normalized in {"ALTERNATIVE", "ALTERNATIVES", "HEDGE_FUND", "PRIVATE_MARKETS"}:
        return "ALTERNATIVES"
    if normalized in {"CASH", "MONEY_MARKET"}:
        return "CASH"
    return normalized


def _dict_section(body: dict[str, Any], key: str) -> dict[str, Any]:
    value = body.get(key)
    return value if isinstance(value, dict) else {}
