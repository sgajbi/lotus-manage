from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any, Optional

import httpx

from src.core.construction.models import AuthoritativeRegimeStressContext, AuthoritativeRiskContext
from src.core.construction.vocabulary import ConstructionMethodStatus
from src.core.models import RebalanceResult
from src.infrastructure.authority_http import AuthorityHttpError, post_json_with_retries


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


@dataclass(frozen=True)
class _ConcentrationBreachInputs:
    top_position_weight_proposed: Decimal
    top_issuer_weight_proposed: Decimal
    hhi_proposed: Decimal


@dataclass(frozen=True)
class _ConcentrationResponseSections:
    metadata: dict[str, Any]
    risk_proxy: dict[str, Any]
    single_position: dict[str, Any]
    issuer: dict[str, Any]
    supportability_state: str
    supportability_reason: str
    request_fingerprint: str
    issuer_coverage_status: Any


@dataclass(frozen=True)
class _RiskEventCohortMetadata:
    product_name: str
    product_version: str
    source_service: str
    request_fingerprint: str
    calculation_supportability: str


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
    try:
        return post_json_with_retries(
            client=client,
            url=url,
            payload=payload,
            headers=headers,
            attempts=attempts,
            unavailable_error="LOTUS_RISK_UNAVAILABLE",
            rejected_error=rejected_error,
            invalid_response_error="LOTUS_RISK_INVALID_RESPONSE",
        )
    except AuthorityHttpError as exc:
        raise LotusRiskAuthorityUnavailableError(exc.code) from exc


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
    sections = _concentration_response_sections(body)
    breach_inputs = _concentration_breach_inputs(
        risk_proxy=sections.risk_proxy,
        single_position=sections.single_position,
        issuer=sections.issuer,
    )
    breaches = _concentration_breach_count(breach_inputs)
    return AuthoritativeRiskContext(
        supportability_status=_risk_status_from_supportability(sections.supportability_state),
        source_system=str(body.get("source_service") or "lotus-risk"),
        source_product_name="ConcentrationAnalysis",
        source_product_version=str(sections.metadata.get("methodology_version") or "v1"),
        source_id=sections.request_fingerprint or None,
        content_hash=sections.request_fingerprint or None,
        concentration_breaches=breaches,
        concentration_hhi_delta=Decimal(str(sections.risk_proxy.get("hhi_delta", "0"))),
        top_position_weight_proposed=breach_inputs.top_position_weight_proposed,
        issuer_coverage_status=(
            str(sections.issuer_coverage_status)
            if sections.issuer_coverage_status is not None
            else None
        ),
        reason_codes=_concentration_reason_codes(
            supportability_reason=sections.supportability_reason,
            issuer_coverage_status=sections.issuer_coverage_status,
            breaches=breaches,
        ),
    )


def _concentration_response_sections(body: dict[str, Any]) -> _ConcentrationResponseSections:
    metadata = _dict_section(body, "metadata")
    supportability = _dict_section(metadata, "calculation_supportability")
    issuer = _dict_section(body, "issuer_concentration")
    return _ConcentrationResponseSections(
        metadata=metadata,
        risk_proxy=_dict_section(body, "risk_proxy"),
        single_position=_dict_section(body, "single_position_concentration"),
        issuer=issuer,
        supportability_state=str(supportability.get("state", "degraded")),
        supportability_reason=str(
            supportability.get("reason", "calculation_supportability_missing")
        ),
        request_fingerprint=str(metadata.get("request_fingerprint") or ""),
        issuer_coverage_status=issuer.get("coverage_status"),
    )


def _concentration_breach_inputs(
    *,
    risk_proxy: dict[str, Any],
    single_position: dict[str, Any],
    issuer: dict[str, Any],
) -> _ConcentrationBreachInputs:
    return _ConcentrationBreachInputs(
        top_position_weight_proposed=Decimal(
            str(single_position.get("top_position_weight_proposed", "0"))
        ),
        top_issuer_weight_proposed=Decimal(str(issuer.get("top_issuer_weight_proposed", "0"))),
        hhi_proposed=Decimal(str(risk_proxy.get("hhi_proposed", "0"))),
    )


def _concentration_breach_count(inputs: _ConcentrationBreachInputs) -> int:
    return sum(
        (
            inputs.top_position_weight_proposed > Decimal("0.30"),
            inputs.top_issuer_weight_proposed > Decimal("0.40"),
            inputs.hhi_proposed > Decimal("2500"),
        )
    )


def _concentration_reason_codes(
    *,
    supportability_reason: str,
    issuer_coverage_status: Any,
    breaches: int,
) -> list[str]:
    reason_codes = [f"LOTUS_RISK_CONCENTRATION_{supportability_reason.upper()}"]
    if issuer_coverage_status and issuer_coverage_status != "complete":
        reason_codes.append(f"ISSUER_COVERAGE_{str(issuer_coverage_status).upper()}")
    if breaches:
        reason_codes.append("RISK_CONCENTRATION_LIMIT_BREACH")
    return sorted(set(reason_codes))


def _regime_context_from_scenario_response(
    body: dict[str, Any],
) -> AuthoritativeRegimeStressContext:
    try:
        metadata = _dict_section(body, "metadata")
        governance_evidence = _optional_dict_section(body, "governance_evidence")
        supportability = str(metadata.get("calculation_supportability", "degraded"))
        portfolio_id = _optional_text(body.get("portfolio_id"))
        portfolio_applicability_ref = _optional_text(
            governance_evidence.get("portfolio_applicability_ref")
        )
        return AuthoritativeRegimeStressContext(
            supportability_status=_scenario_status_from_supportability(supportability),
            source_system=_regime_source_system(metadata),
            source_product_version=_regime_source_product_version(metadata),
            scenario_pack_id=str(body["scenario_pack_id"]),
            worst_case_loss_pct=Decimal(str(body["worst_case_loss_pct"])),
            maximum_allowed_loss_pct=Decimal(str(body["maximum_allowed_loss_pct"])),
            cio_approval_status=_optional_text(governance_evidence.get("cio_approval_status")),
            cio_approval_ref=_regime_governance_text(governance_evidence, body, "cio_approval_ref"),
            approved_by=_regime_governance_text(governance_evidence, body, "approved_by"),
            approved_at=_regime_governance_text(governance_evidence, body, "approved_at"),
            effective_from=_regime_governance_date(governance_evidence, body, "effective_from"),
            effective_to=_regime_governance_date(governance_evidence, body, "effective_to"),
            effective_period_status=_optional_text(
                governance_evidence.get("effective_period_status")
            ),
            applicability_status=_optional_text(governance_evidence.get("applicability_status")),
            applicability_scope=_text_list(governance_evidence.get("applicability_scope")),
            portfolio_applicability_ref=portfolio_applicability_ref,
            methodology_ref=_optional_text(governance_evidence.get("methodology_ref")),
            applicable_portfolio_ids=_regime_applicable_portfolio_ids(
                body=body,
                portfolio_id=portfolio_id,
                portfolio_applicability_ref=portfolio_applicability_ref,
            ),
            applicable_mandate_ids=_text_list(body.get("applicable_mandate_ids")),
            reason_codes=_regime_reason_codes(body.get("reason_codes")),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise LotusRiskAuthorityUnavailableError("LOTUS_RISK_INVALID_RESPONSE") from exc


def _regime_source_system(metadata: dict[str, Any]) -> str:
    return str(metadata.get("source_service") or "lotus-risk")


def _regime_source_product_version(metadata: dict[str, Any]) -> str:
    return str(metadata.get("product_version") or "v1")


def _regime_governance_text(
    governance_evidence: dict[str, Any],
    body: dict[str, Any],
    key: str,
) -> str | None:
    return _optional_text(governance_evidence.get(key)) or _optional_text(body.get(key))


def _regime_governance_date(
    governance_evidence: dict[str, Any],
    body: dict[str, Any],
    key: str,
) -> date | None:
    return _optional_date(governance_evidence.get(key) or body.get(key))


def _regime_reason_codes(value: Any) -> list[str]:
    if not isinstance(value, list):
        return ["REGIME_SCENARIO_PACK_RESPONSE_REASON_CODES_MISSING"]
    return sorted({str(reason_code) for reason_code in value})


def _risk_event_cohort_from_response(body: dict[str, Any]) -> RiskEventAffectedCohort:
    try:
        metadata = _risk_event_cohort_metadata(body)
        return RiskEventAffectedCohort(
            cohort_id=_required_text(body=body, key="cohort_id"),
            risk_event_id=_required_text(body=body, key="risk_event_id"),
            display_name=_required_text(body=body, key="display_name"),
            product_name=metadata.product_name,
            product_version=metadata.product_version,
            source_service=metadata.source_service,
            request_fingerprint=metadata.request_fingerprint,
            calculation_supportability=metadata.calculation_supportability,
            reason_codes=_risk_event_reason_codes(body.get("reason_codes")),
            affected_portfolios=_risk_event_affected_portfolios(body.get("affected_portfolios")),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise LotusRiskAuthorityUnavailableError("LOTUS_RISK_INVALID_RESPONSE") from exc


def _risk_event_cohort_metadata(body: dict[str, Any]) -> _RiskEventCohortMetadata:
    metadata = _dict_section(body, "metadata")
    return _RiskEventCohortMetadata(
        product_name=_metadata_text(
            metadata=metadata,
            key="product_name",
            default="RiskEventAffectedCohort",
        ),
        product_version=_metadata_text(metadata=metadata, key="product_version", default="v1"),
        source_service=_metadata_text(
            metadata=metadata, key="source_service", default="lotus-risk"
        ),
        request_fingerprint=_metadata_text(
            metadata=metadata,
            key="request_fingerprint",
            default="",
        ),
        calculation_supportability=_metadata_text(
            metadata=metadata,
            key="calculation_supportability",
            default="blocked",
        ),
    )


def _metadata_text(*, metadata: dict[str, Any], key: str, default: str) -> str:
    return str(metadata.get(key) or default)


def _required_text(*, body: dict[str, Any], key: str) -> str:
    return str(body[key])


def _risk_event_reason_codes(reason_codes: Any) -> tuple[str, ...]:
    if not isinstance(reason_codes, list):
        return ("RISK_EVENT_COHORT_REASON_CODES_MISSING",)
    return tuple(str(code) for code in reason_codes)


def _risk_event_affected_portfolios(value: Any) -> tuple[RiskEventAffectedPortfolio, ...]:
    if not isinstance(value, list):
        raise ValueError("affected_portfolios must be a list")
    if not all(isinstance(portfolio, dict) for portfolio in value):
        raise ValueError("affected_portfolios entries must be objects")
    return tuple(_risk_event_affected_portfolio(portfolio) for portfolio in value)


def _risk_event_affected_portfolio(portfolio: dict[str, Any]) -> RiskEventAffectedPortfolio:
    return RiskEventAffectedPortfolio(
        portfolio_id=str(portfolio["portfolio_id"]),
        mandate_id=str(portfolio["mandate_id"])
        if portfolio.get("mandate_id") is not None
        else None,
        source_ref=str(portfolio["source_ref"]),
        reason_codes=tuple(str(code) for code in portfolio.get("reason_codes", [])),
        impact_score=Decimal(str(portfolio["impact_score"])),
        dominant_bucket=str(portfolio["dominant_bucket"]),
    )


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


def _optional_dict_section(body: dict[str, Any], key: str) -> dict[str, Any]:
    value = body.get(key)
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    raise ValueError(f"{key} must be an object")


def _regime_applicable_portfolio_ids(
    *,
    body: dict[str, Any],
    portfolio_id: str | None,
    portfolio_applicability_ref: str | None,
) -> list[str]:
    explicit_portfolios = _text_list(body.get("applicable_portfolio_ids"))
    if explicit_portfolios:
        return explicit_portfolios
    if portfolio_id and portfolio_applicability_ref:
        return [portfolio_id]
    return []


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_date(value: Any) -> date | None:
    text = _optional_text(value)
    if text is None:
        return None
    return date.fromisoformat(text)


def _text_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [text for item in value if (text := _optional_text(item)) is not None]
