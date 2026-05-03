from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Optional

import httpx

from src.core.construction.models import AuthoritativeRiskContext
from src.core.construction.vocabulary import ConstructionMethodStatus
from src.core.models import RebalanceResult


class LotusRiskAuthorityUnavailableError(RuntimeError):
    pass


@dataclass(frozen=True)
class LotusRiskAuthorityConfig:
    base_url: str
    concentration_path: str = "/analytics/risk/concentration"
    timeout_seconds: float = 2.0
    max_attempts: int = 2

    def concentration_url(self) -> str:
        return f"{self.base_url.rstrip('/')}/{self.concentration_path.lstrip('/')}"


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


def _post_with_retries(
    *,
    client: httpx.Client,
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    attempts: int,
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
            raise LotusRiskAuthorityUnavailableError("LOTUS_RISK_CONCENTRATION_REJECTED")
        body = response.json()
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


def _risk_context_from_concentration_response(body: dict[str, Any]) -> AuthoritativeRiskContext:
    metadata = _dict_section(body, "metadata")
    supportability = _dict_section(metadata, "calculation_supportability")
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
        concentration_breaches=breaches,
        concentration_hhi_delta=Decimal(str(risk_proxy.get("hhi_delta", "0"))),
        top_position_weight_proposed=Decimal(
            str(single_position.get("top_position_weight_proposed", "0"))
        ),
        issuer_coverage_status=str(coverage_status) if coverage_status is not None else None,
        reason_codes=sorted(set(reason_codes)),
    )


def _risk_status_from_supportability(state: str) -> ConstructionMethodStatus:
    if state == "ready":
        return ConstructionMethodStatus.READY
    if state in {"stale", "degraded"}:
        return ConstructionMethodStatus.DEGRADED
    if state == "empty":
        return ConstructionMethodStatus.PENDING_REVIEW
    return ConstructionMethodStatus.BLOCKED


def _dict_section(body: dict[str, Any], key: str) -> dict[str, Any]:
    value = body.get(key)
    return value if isinstance(value, dict) else {}
