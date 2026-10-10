from __future__ import annotations

import time
import json
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
    maximum_response_bytes: int | None = None,
    reject_duplicate_members: bool = False,
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
            invalid_response_error=invalid_response_error,
            maximum_response_bytes=maximum_response_bytes,
        )
        if isinstance(response, AuthorityHttpError):
            if response.code != unavailable_error:
                _record_source_http_request(
                    source_service=source_service,
                    method="post",
                    outcome="invalid_response",
                    elapsed_seconds=time.perf_counter() - started_at,
                )
                raise response
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
                maximum_response_bytes=maximum_response_bytes,
                reject_duplicate_members=reject_duplicate_members,
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
    invalid_response_error: str,
    maximum_response_bytes: int | None,
) -> httpx.Response | AuthorityHttpError:
    try:
        if maximum_response_bytes is not None:
            with client.stream(
                "POST", url, json=payload, headers=headers, follow_redirects=False
            ) as response:
                if response.status_code >= 300:
                    return httpx.Response(response.status_code)
                if response.headers.get("content-encoding", "identity") != "identity":
                    return AuthorityHttpError(invalid_response_error)
                chunks: list[bytes] = []
                size = 0
                for chunk in response.iter_bytes():
                    size += len(chunk)
                    if size > maximum_response_bytes:
                        return AuthorityHttpError(invalid_response_error)
                    chunks.append(chunk)
                return httpx.Response(
                    response.status_code,
                    content=b"".join(chunks),
                    headers={
                        name: value
                        for name, value in response.headers.items()
                        if name.lower() not in {"content-encoding", "content-length"}
                    },
                )
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
    if response.status_code >= 300:
        raise AuthorityHttpError(rejected_error)


def _json_object_body(
    *,
    response: httpx.Response,
    invalid_response_error: str,
    maximum_response_bytes: int | None = None,
    reject_duplicate_members: bool = False,
) -> dict[str, Any]:
    if maximum_response_bytes is not None and len(response.content) > maximum_response_bytes:
        raise AuthorityHttpError(invalid_response_error)
    try:
        body = (
            json.loads(response.content, object_pairs_hook=_unique_json_members)
            if reject_duplicate_members
            else response.json()
        )
    except ValueError as exc:
        raise AuthorityHttpError(invalid_response_error, cause=exc) from exc
    if not isinstance(body, dict):
        raise AuthorityHttpError(invalid_response_error)
    return body


def _unique_json_members(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for name, value in pairs:
        if name in result:
            raise ValueError("Duplicate JSON member")
        result[name] = value
    return result


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
