from __future__ import annotations

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
) -> dict[str, Any]:
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
                raise response
            continue
        if _should_retry_status(response=response, attempt=attempt, attempts=attempts):
            continue
        _raise_for_status(
            response=response,
            unavailable_error=unavailable_error,
            rejected_error=rejected_error,
        )
        return _json_object_body(
            response=response,
            invalid_response_error=invalid_response_error,
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
