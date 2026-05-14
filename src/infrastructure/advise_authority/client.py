from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Optional

import httpx


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
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            response = client.post(url, json=payload, headers=headers)
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            last_error = exc
            if attempt + 1 >= attempts:
                raise LotusAdviseAuthorityUnavailableError("LOTUS_ADVISE_UNAVAILABLE") from exc
            continue
        if response.status_code in {502, 503, 504} and attempt + 1 < attempts:
            continue
        if response.status_code >= 500:
            raise LotusAdviseAuthorityUnavailableError("LOTUS_ADVISE_UNAVAILABLE")
        if response.status_code >= 400:
            raise LotusAdviseAuthorityUnavailableError(
                "LOTUS_ADVISE_TACTICAL_HOUSE_VIEW_COHORT_REJECTED"
            )
        try:
            body = response.json()
        except ValueError as exc:
            raise LotusAdviseAuthorityUnavailableError("LOTUS_ADVISE_INVALID_RESPONSE") from exc
        if not isinstance(body, dict):
            raise LotusAdviseAuthorityUnavailableError("LOTUS_ADVISE_INVALID_RESPONSE")
        return body
    raise LotusAdviseAuthorityUnavailableError("LOTUS_ADVISE_UNAVAILABLE") from last_error


def _tactical_house_view_cohort_from_response(
    body: dict[str, Any],
) -> TacticalHouseViewAffectedCohort:
    try:
        supportability = _dict_section(body, "supportability")
        affected_payload = body.get("affected_portfolios")
        if not isinstance(affected_payload, list):
            raise ValueError("affected_portfolios must be a list")
        source_refs_payload = body.get("source_refs")
        if not isinstance(source_refs_payload, list):
            raise ValueError("source_refs must be a list")
        if not all(isinstance(portfolio, dict) for portfolio in affected_payload):
            raise ValueError("affected_portfolios entries must be objects")
        if not all(isinstance(ref, dict) for ref in source_refs_payload):
            raise ValueError("source_refs entries must be objects")
        reason_codes = supportability.get("reason_codes")
        if not isinstance(reason_codes, list):
            reason_codes = ["TACTICAL_HOUSE_VIEW_SUPPORTABILITY_REASON_CODES_MISSING"]
        affected = tuple(
            TacticalHouseViewAffectedPortfolio(
                portfolio_id=str(portfolio["portfolio_id"]),
                mandate_id=(
                    str(portfolio["mandate_id"])
                    if portfolio.get("mandate_id") is not None
                    else None
                ),
                inclusion_reason_codes=tuple(
                    str(code) for code in portfolio.get("inclusion_reason_codes", [])
                ),
                source_refs=_dict_tuple(portfolio.get("source_refs")),
            )
            for portfolio in affected_payload
        )
        return TacticalHouseViewAffectedCohort(
            cohort_id=str(body["cohort_id"]),
            tactical_view_id=str(body["tactical_view_id"]),
            tactical_view_version=str(body["tactical_view_version"]),
            theme_id=str(body["theme_id"]),
            as_of_date=str(body["as_of_date"]),
            target_action=str(body["target_action"]),
            product_name=str(body.get("product_name") or "TacticalHouseViewAffectedCohort"),
            product_version=str(body.get("product_version") or "v1"),
            source_service="lotus-advise",
            content_hash=str(body.get("content_hash") or ""),
            supportability_state=str(supportability.get("state") or "BLOCKED"),
            supportability_reason_codes=tuple(str(code) for code in reason_codes),
            affected_portfolios=affected,
            source_refs=tuple(dict(ref) for ref in source_refs_payload),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise LotusAdviseAuthorityUnavailableError("LOTUS_ADVISE_INVALID_RESPONSE") from exc


def _dict_section(body: dict[str, Any], key: str) -> dict[str, Any]:
    value = body.get(key)
    if isinstance(value, dict):
        return value
    return {}


def _dict_tuple(value: object) -> tuple[dict[str, Any], ...]:
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ValueError("source_refs must be a list of objects")
    return tuple(dict(item) for item in value)
