from __future__ import annotations

import time
from typing import Any

import httpx


class AuthorityHttpError(RuntimeError):
    def __init__(self, code: str, *, cause: Exception | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.cause = cause
        self.__cause__ = cause


def post_json_with_retries(
    *,
    client: httpx.Client,
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    attempts: int,
    unavailable_error: str,
    rejected_error: str,
    invalid_response_error: str,
    source_service: str = "unknown",
) -> dict[str, Any]:
    started_at = time.perf_counter()
    last_error: Exception | None = None
    for attempt in range(attempts):
        response = _post_json_attempt(
            client=client,
            url=url,
            payload=payload,
            headers=headers,
            unavailable_error=unavailable_error,
        )
        if isinstance(response, AuthorityHttpError):
            last_error = response.cause
            if attempt + 1 >= attempts:
                _record_source_http_request(
                    source_service=source_service,
                    method="post",
                    outcome="unavailable",
                    elapsed_seconds=time.perf_counter() - started_at,
                )
                raise response
            _record_source_http_retry(
                source_service=source_service,
                method="post",
                reason="transport_error",
            )
            continue
        if _should_retry_status(response=response, attempt=attempt, attempts=attempts):
            _record_source_http_retry(
                source_service=source_service,
                method="post",
                reason="transient_status",
            )
            continue
        try:
            _raise_for_status(
                response=response,
                unavailable_error=unavailable_error,
                rejected_error=rejected_error,
            )
            body = _json_object_body(
                response=response,
                invalid_response_error=invalid_response_error,
            )
        except AuthorityHttpError as exc:
            _record_source_http_request(
                source_service=source_service,
                method="post",
                outcome=_authority_http_outcome(exc.code, unavailable_error, rejected_error),
                elapsed_seconds=time.perf_counter() - started_at,
            )
            raise
        _record_source_http_request(
            source_service=source_service,
            method="post",
            outcome="success",
            elapsed_seconds=time.perf_counter() - started_at,
        )
        return body
    _record_source_http_request(
        source_service=source_service,
        method="post",
        outcome="unavailable",
        elapsed_seconds=time.perf_counter() - started_at,
    )
    raise AuthorityHttpError(unavailable_error, cause=last_error)


def _post_json_attempt(
    *,
    client: httpx.Client,
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    unavailable_error: str,
) -> httpx.Response | AuthorityHttpError:
    try:
        return client.post(url, json=payload, headers=headers)
    except (httpx.TimeoutException, httpx.TransportError) as exc:
        return AuthorityHttpError(unavailable_error, cause=exc)


def _should_retry_status(*, response: httpx.Response, attempt: int, attempts: int) -> bool:
    return response.status_code in {502, 503, 504} and attempt + 1 < attempts


def _raise_for_status(
    *,
    response: httpx.Response,
    unavailable_error: str,
    rejected_error: str,
) -> None:
    if response.status_code >= 500:
        raise AuthorityHttpError(unavailable_error)
    if response.status_code >= 400:
        raise AuthorityHttpError(rejected_error)


def _json_object_body(
    *,
    response: httpx.Response,
    invalid_response_error: str,
) -> dict[str, Any]:
    try:
        body = response.json()
    except ValueError as exc:
        raise AuthorityHttpError(invalid_response_error, cause=exc) from exc
    if not isinstance(body, dict):
        raise AuthorityHttpError(invalid_response_error)
    return body


def _authority_http_outcome(code: str, unavailable_error: str, rejected_error: str) -> str:
    if code == unavailable_error:
        return "unavailable"
    if code == rejected_error:
        return "rejected"
    return "invalid_response"


def _record_source_http_request(
    *,
    source_service: str,
    method: str,
    outcome: str,
    elapsed_seconds: float,
) -> None:
    from src.api.observability import record_source_http_request

    record_source_http_request(
        source_service=source_service,
        method=method,
        outcome=outcome,
        elapsed_seconds=elapsed_seconds,
    )


def _record_source_http_retry(*, source_service: str, method: str, reason: str) -> None:
    from src.api.observability import record_source_http_retry

    record_source_http_retry(
        source_service=source_service,
        method=method,
        reason=reason,
    )
