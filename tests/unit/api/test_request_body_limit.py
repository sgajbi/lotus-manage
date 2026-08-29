from collections.abc import AsyncIterator
from typing import Any

import pytest
from fastapi import Request, Response

from src.api.enterprise_readiness import build_enterprise_audit_middleware


def _streaming_request(
    *,
    chunks: list[bytes],
    content_length: str | None = None,
    method: str = "POST",
) -> Request:
    headers = [] if content_length is None else [(b"content-length", content_length.encode())]
    chunk_iterator: AsyncIterator[bytes] = _chunks(chunks)

    async def receive() -> dict[str, Any]:
        try:
            chunk = await anext(chunk_iterator)
        except StopAsyncIteration:
            return {"type": "http.request", "body": b"", "more_body": False}
        return {"type": "http.request", "body": chunk, "more_body": True}

    return Request(
        {
            "type": "http",
            "method": method,
            "path": "/write",
            "headers": headers,
            "scheme": "http",
            "server": ("testserver", 80),
            "client": ("testclient", 50000),
        },
        receive=receive,
    )


async def _chunks(chunks: list[bytes]) -> AsyncIterator[bytes]:
    for chunk in chunks:
        yield chunk


@pytest.mark.asyncio
async def test_middleware_measures_streamed_body_without_content_length(monkeypatch) -> None:
    monkeypatch.setenv("ENTERPRISE_ENFORCE_AUTHZ", "false")
    monkeypatch.setenv("ENTERPRISE_MAX_WRITE_PAYLOAD_BYTES", "5")
    middleware = build_enterprise_audit_middleware()
    request = _streaming_request(chunks=[b"abc", b"def"])

    async def downstream(_request: Request) -> Response:
        raise AssertionError("An oversized body must not reach route handling.")

    response = await middleware(request, downstream)

    assert response.status_code == 413
    assert bytes(response.body) == b'{"detail":"payload_too_large"}'


@pytest.mark.asyncio
async def test_middleware_measures_underdeclared_body(monkeypatch) -> None:
    monkeypatch.setenv("ENTERPRISE_ENFORCE_AUTHZ", "false")
    monkeypatch.setenv("ENTERPRISE_MAX_WRITE_PAYLOAD_BYTES", "5")
    middleware = build_enterprise_audit_middleware()
    request = _streaming_request(chunks=[b"abc", b"def"], content_length="2")

    async def downstream(_request: Request) -> Response:
        raise AssertionError("An under-declared oversized body must not reach route handling.")

    response = await middleware(request, downstream)

    assert response.status_code == 413
    assert bytes(response.body) == b'{"detail":"payload_too_large"}'


@pytest.mark.asyncio
@pytest.mark.parametrize("content_length", ["not-a-number", "-1"])
async def test_middleware_rejects_invalid_content_length(monkeypatch, content_length: str) -> None:
    monkeypatch.setenv("ENTERPRISE_ENFORCE_AUTHZ", "false")
    middleware = build_enterprise_audit_middleware()
    request = _streaming_request(chunks=[b"{}"], content_length=content_length)

    async def downstream(_request: Request) -> Response:
        raise AssertionError("An invalid declaration must not reach route handling.")

    response = await middleware(request, downstream)

    assert response.status_code == 400
    assert bytes(response.body) == b'{"detail":"invalid_content_length"}'


@pytest.mark.asyncio
async def test_middleware_replays_accepted_body_unchanged(monkeypatch) -> None:
    monkeypatch.setenv("ENTERPRISE_ENFORCE_AUTHZ", "false")
    monkeypatch.setenv("ENTERPRISE_MAX_WRITE_PAYLOAD_BYTES", "32")
    middleware = build_enterprise_audit_middleware()
    request = _streaming_request(chunks=[b'{"status":', b'"ready"}'])
    received_body = b""
    replay_messages: list[dict[str, Any]] = []

    async def downstream(replayed_request: Request) -> Response:
        nonlocal received_body
        received_body = await replayed_request.body()
        replay_messages.extend([await replayed_request.receive(), await replayed_request.receive()])
        return Response(status_code=204)

    response = await middleware(request, downstream)

    assert response.status_code == 204
    assert received_body == b'{"status":"ready"}'
    assert replay_messages == [
        {
            "type": "http.request",
            "body": b'{"status":"ready"}',
            "more_body": False,
        },
        {"type": "http.request", "body": b"", "more_body": False},
    ]


@pytest.mark.asyncio
async def test_middleware_does_not_buffer_unauthorized_write(monkeypatch) -> None:
    monkeypatch.setenv("ENTERPRISE_ENFORCE_AUTHZ", "true")
    middleware = build_enterprise_audit_middleware()
    body_read = False

    async def receive() -> dict[str, Any]:
        nonlocal body_read
        body_read = True
        return {"type": "http.request", "body": b"secret", "more_body": False}

    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/write",
            "headers": [],
            "scheme": "http",
            "server": ("testserver", 80),
            "client": ("testclient", 50000),
        },
        receive=receive,
    )

    async def downstream(_request: Request) -> Response:
        raise AssertionError("An unauthorized write must not reach route handling.")

    response = await middleware(request, downstream)

    assert response.status_code == 403
    assert body_read is False
