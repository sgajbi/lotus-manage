from typing import Any, Literal, Optional, cast

import httpx

from src.infrastructure.core_sourcing.errors import (
    DpmCoreResolverError,
    DpmCoreResolverUnavailableError,
)


SourceProductMethod = Literal["get", "post"]
TRANSIENT_SOURCE_STATUS_CODES = frozenset({502, 503, 504})


def source_product_headers(correlation_id: Optional[str]) -> dict[str, str]:
    return {"X-Correlation-Id": correlation_id} if correlation_id else {}


def source_product_response_payload(
    response: httpx.Response,
    *,
    incomplete_code: str,
) -> dict[str, Any]:
    response_payload = response.json()
    if not isinstance(response_payload, dict):
        raise DpmCoreResolverError(incomplete_code)
    return response_payload


def raise_for_source_product_status(
    response: httpx.Response,
    *,
    unavailable_code: str,
    incomplete_code: str,
) -> None:
    if response.status_code >= 500:
        raise DpmCoreResolverUnavailableError(unavailable_code)
    if response.status_code >= 400:
        raise DpmCoreResolverError(incomplete_code)


def source_product_request(
    client: Any,
    *,
    method: SourceProductMethod,
    url: str,
    selector: dict[str, Any],
    headers: dict[str, str],
) -> httpx.Response:
    if method == "post":
        return cast(httpx.Response, client.post(url, json=selector, headers=headers))
    return cast(httpx.Response, client.get(url, params=selector, headers=headers))


def final_source_product_attempt(*, attempt_index: int, attempts: int) -> bool:
    return attempt_index + 1 >= attempts


def should_retry_transient_source_status(
    response: httpx.Response,
    *,
    attempt_index: int,
    attempts: int,
) -> bool:
    return (
        response.status_code in TRANSIENT_SOURCE_STATUS_CODES
        and not final_source_product_attempt(attempt_index=attempt_index, attempts=attempts)
    )


def source_product_payload_with_retries(
    client: Any,
    *,
    attempts: int,
    method: SourceProductMethod,
    url: str,
    selector: dict[str, Any],
    headers: dict[str, str],
    unavailable_code: str,
    incomplete_code: str,
) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            response = source_product_request(
                client,
                method=method,
                url=url,
                selector=selector,
                headers=headers,
            )
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            last_error = exc
            if final_source_product_attempt(attempt_index=attempt, attempts=attempts):
                raise DpmCoreResolverUnavailableError(unavailable_code) from exc
            continue
        if should_retry_transient_source_status(
            response,
            attempt_index=attempt,
            attempts=attempts,
        ):
            continue
        raise_for_source_product_status(
            response,
            unavailable_code=unavailable_code,
            incomplete_code=incomplete_code,
        )
        return source_product_response_payload(response, incomplete_code=incomplete_code)
    raise DpmCoreResolverUnavailableError(unavailable_code) from last_error
