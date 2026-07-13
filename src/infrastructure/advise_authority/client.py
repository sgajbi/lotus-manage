from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Optional

import httpx

from src.infrastructure.authority_http import AuthorityHttpError, post_json_with_retries


class LotusAdviseAuthorityUnavailableError(RuntimeError):
    pass


@dataclass(frozen=True)
class LotusAdviseAuthorityConfig:
    base_url: str
    tactical_house_view_cohort_path: str = "/advisory/tactical-house-view/cohorts/evaluate"
    timeout_seconds: float = 2.0
    max_attempts: int = 2

    def tactical_house_view_cohort_url(self) -> str:
        return f"{self.base_url.rstrip('/')}/{self.tactical_house_view_cohort_path.lstrip('/')}"


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


class LotusAdviseAuthorityClient:
    """Bounded client for lotus-advise source products consumed by manage.

    Manage consumes source-owned tactical house-view cohort evidence. It does not recompute
    advisory, house-view, holdings, exposure, alignment, or mandate facts locally.
    """

    def __init__(
        self,
        *,
        config: LotusAdviseAuthorityConfig,
        client: Optional[httpx.Client] = None,
    ) -> None:
        self._config = config
        self._client = client
        self._owns_client = client is None

    def close(self) -> None:
        if self._owns_client and self._client is not None:
            self._client.close()

    def tactical_house_view_affected_cohort(
        self,
        *,
        tactical_view: dict[str, Any],
        candidate_portfolios: list[dict[str, Any]],
        eligible_portfolio_types: list[str],
        min_exposure_weight: Decimal | None,
        correlation_id: str,
    ) -> TacticalHouseViewAffectedCohort:
        payload: dict[str, Any] = {
            "tactical_view": tactical_view,
            "candidate_portfolios": candidate_portfolios,
            "eligible_portfolio_types": eligible_portfolio_types,
            "correlation_id": correlation_id,
        }
        if min_exposure_weight is not None:
            payload["min_exposure_weight"] = str(min_exposure_weight)
        headers = {"X-Correlation-Id": correlation_id} if correlation_id else {}
        client = self._client or httpx.Client(timeout=self._config.timeout_seconds)
        try:
            response_payload = _post_with_retries(
                client=client,
                url=self._config.tactical_house_view_cohort_url(),
                payload=payload,
                headers=headers,
                attempts=max(self._config.max_attempts, 1),
            )
        finally:
            if self._owns_client:
                client.close()
        return _tactical_house_view_cohort_from_response(response_payload)


def _post_with_retries(
    *,
    client: httpx.Client,
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    attempts: int,
) -> dict[str, Any]:
    try:
        return post_json_with_retries(
            client=client,
            url=url,
            payload=payload,
            headers=headers,
            attempts=attempts,
            unavailable_error="LOTUS_ADVISE_UNAVAILABLE",
            rejected_error="LOTUS_ADVISE_TACTICAL_HOUSE_VIEW_COHORT_REJECTED",
            invalid_response_error="LOTUS_ADVISE_INVALID_RESPONSE",
            source_service="lotus-advise",
        )
    except AuthorityHttpError as exc:
        raise LotusAdviseAuthorityUnavailableError(exc.code) from exc


def _tactical_house_view_cohort_from_response(
    body: dict[str, Any],
) -> TacticalHouseViewAffectedCohort:
    try:
        return _tactical_house_view_cohort_payload(
            body=body,
            supportability=_dict_section(body, "supportability"),
            affected_portfolios=_tactical_affected_portfolios_from_response(body),
            source_refs=_dict_list_section(body, "source_refs"),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise LotusAdviseAuthorityUnavailableError("LOTUS_ADVISE_INVALID_RESPONSE") from exc


def _tactical_house_view_cohort_payload(
    *,
    body: dict[str, Any],
    supportability: dict[str, Any],
    affected_portfolios: tuple[TacticalHouseViewAffectedPortfolio, ...],
    source_refs: list[dict[str, Any]],
) -> TacticalHouseViewAffectedCohort:
    reason_codes = _supportability_reason_codes(supportability)
    return TacticalHouseViewAffectedCohort(
        cohort_id=str(body["cohort_id"]),
        tactical_view_id=str(body["tactical_view_id"]),
        tactical_view_version=str(body["tactical_view_version"]),
        theme_id=str(body["theme_id"]),
        as_of_date=str(body["as_of_date"]),
        target_action=str(body["target_action"]),
        product_name=_cohort_optional_text(
            body,
            key="product_name",
            default="TacticalHouseViewAffectedCohort",
        ),
        product_version=_cohort_optional_text(body, key="product_version", default="v1"),
        source_service="lotus-advise",
        content_hash=_cohort_optional_text(body, key="content_hash", default=""),
        supportability_state=str(supportability.get("state") or "BLOCKED"),
        supportability_reason_codes=tuple(str(code) for code in reason_codes),
        affected_portfolios=affected_portfolios,
        source_refs=tuple(dict(ref) for ref in source_refs),
    )


def _tactical_affected_portfolios_from_response(
    body: dict[str, Any],
) -> tuple[TacticalHouseViewAffectedPortfolio, ...]:
    affected_payload = _dict_list_section(body, "affected_portfolios")
    return tuple(
        _tactical_affected_portfolio_from_payload(portfolio) for portfolio in affected_payload
    )


def _tactical_affected_portfolio_from_payload(
    portfolio: dict[str, Any],
) -> TacticalHouseViewAffectedPortfolio:
    return TacticalHouseViewAffectedPortfolio(
        portfolio_id=str(portfolio["portfolio_id"]),
        mandate_id=str(portfolio["mandate_id"])
        if portfolio.get("mandate_id") is not None
        else None,
        inclusion_reason_codes=tuple(
            str(code) for code in portfolio.get("inclusion_reason_codes", [])
        ),
        source_refs=_dict_tuple(portfolio.get("source_refs")),
    )


def _supportability_reason_codes(supportability: dict[str, Any]) -> list[Any]:
    reason_codes = supportability.get("reason_codes")
    if isinstance(reason_codes, list):
        return reason_codes
    return ["TACTICAL_HOUSE_VIEW_SUPPORTABILITY_REASON_CODES_MISSING"]


def _cohort_optional_text(body: dict[str, Any], *, key: str, default: str) -> str:
    return str(body.get(key) or default)


def _dict_list_section(body: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = body.get(key)
    if not isinstance(value, list):
        raise ValueError(f"{key} must be a list")
    if not all(isinstance(item, dict) for item in value):
        raise ValueError(f"{key} entries must be objects")
    return value


def _dict_section(body: dict[str, Any], key: str) -> dict[str, Any]:
    value = body.get(key)
    if isinstance(value, dict):
        return value
    return {}


def _dict_tuple(value: object) -> tuple[dict[str, Any], ...]:
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ValueError("source_refs must be a list of objects")
    return tuple(dict(item) for item in value)
