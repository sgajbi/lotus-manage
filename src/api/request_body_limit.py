from typing import Any

from fastapi import Request


def declared_content_length(request: Request) -> int | None:
    raw_content_length = request.headers.get("content-length")
    if raw_content_length is None:
        return None
    try:
        declared_length = int(raw_content_length)
    except ValueError as exc:
        raise ValueError("invalid_content_length") from exc
    if declared_length < 0:
        raise ValueError("invalid_content_length")
    return declared_length


async def read_limited_body(request: Request, *, max_bytes: int) -> bytes | None:
    chunks: list[bytes] = []
    received_bytes = 0
    async for chunk in request.stream():
        if not chunk:
            continue
        received_bytes += len(chunk)
        if received_bytes > max_bytes:
            return None
        chunks.append(chunk)
    return b"".join(chunks)


def replay_body_for_downstream(request: Request, body: bytes) -> None:
    sent = False

    async def receive() -> dict[str, Any]:
        nonlocal sent
        if sent:
            return {"type": "http.request", "body": b"", "more_body": False}
        sent = True
        return {"type": "http.request", "body": body, "more_body": False}

    setattr(request, "_body", body)
    setattr(request, "_receive", receive)
