import json

import httpx
import pytest

import src.api.observability as observability_module
from src.infrastructure.authority_http import AuthorityHttpError, post_json_with_retries


def test_post_json_with_retries_retries_transport_failure_and_status() -> None:
    calls = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise httpx.ConnectTimeout("temporary timeout")
        if calls == 2:
            return httpx.Response(503)
        return httpx.Response(200, json={"ok": True})

    body = post_json_with_retries(
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        url="http://authority.test/post",
        payload={},
        headers={},
        attempts=3,
        unavailable_error="AUTH_UNAVAILABLE",
        rejected_error="AUTH_REJECTED",
        invalid_response_error="AUTH_INVALID_RESPONSE",
    )

    assert calls == 3
    assert body == {"ok": True}


def test_post_json_with_retries_maps_terminal_status_codes() -> None:
    with pytest.raises(AuthorityHttpError, match="AUTH_REJECTED") as rejected:
        post_json_with_retries(
            client=httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(422))),
            url="http://authority.test/rejected",
            payload={},
            headers={},
            attempts=1,
            unavailable_error="AUTH_UNAVAILABLE",
            rejected_error="AUTH_REJECTED",
            invalid_response_error="AUTH_INVALID_RESPONSE",
        )
    assert rejected.value.code == "AUTH_REJECTED"

    with pytest.raises(AuthorityHttpError, match="AUTH_UNAVAILABLE") as unavailable:
        post_json_with_retries(
            client=httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(500))),
            url="http://authority.test/unavailable",
            payload={},
            headers={},
            attempts=1,
            unavailable_error="AUTH_UNAVAILABLE",
            rejected_error="AUTH_REJECTED",
            invalid_response_error="AUTH_INVALID_RESPONSE",
        )
    assert unavailable.value.code == "AUTH_UNAVAILABLE"


def test_post_json_with_retries_rejects_invalid_or_non_object_json() -> None:
    with pytest.raises(AuthorityHttpError, match="AUTH_INVALID_RESPONSE"):
        post_json_with_retries(
            client=httpx.Client(
                transport=httpx.MockTransport(lambda _: httpx.Response(200, content=b"{"))
            ),
            url="http://authority.test/invalid",
            payload={},
            headers={},
            attempts=1,
            unavailable_error="AUTH_UNAVAILABLE",
            rejected_error="AUTH_REJECTED",
            invalid_response_error="AUTH_INVALID_RESPONSE",
        )

    with pytest.raises(AuthorityHttpError, match="AUTH_INVALID_RESPONSE"):
        post_json_with_retries(
            client=httpx.Client(
                transport=httpx.MockTransport(lambda _: httpx.Response(200, json=[]))
            ),
            url="http://authority.test/non-object",
            payload={},
            headers={},
            attempts=1,
            unavailable_error="AUTH_UNAVAILABLE",
            rejected_error="AUTH_REJECTED",
            invalid_response_error="AUTH_INVALID_RESPONSE",
        )


def test_post_json_with_retries_rejects_empty_attempt_plan() -> None:
    with pytest.raises(AuthorityHttpError, match="AUTH_UNAVAILABLE"):
        post_json_with_retries(
            client=httpx.Client(
                transport=httpx.MockTransport(lambda _: httpx.Response(200, json={"ok": True}))
            ),
            url="http://authority.test/idle",
            payload={},
            headers={},
            attempts=0,
            unavailable_error="AUTH_UNAVAILABLE",
            rejected_error="AUTH_REJECTED",
            invalid_response_error="AUTH_INVALID_RESPONSE",
        )


def test_post_json_with_retries_records_bounded_source_http_metrics(monkeypatch) -> None:
    captured: list[tuple[str, dict[str, str]]] = []
    calls = 0

    class _Counter:
        def __init__(self, name: str) -> None:
            self.name = name

        def labels(self, **labels):
            captured.append((self.name, labels))
            return self

        def inc(self) -> None:
            return None

    class _Histogram:
        def labels(self, **labels):
            captured.append(("duration", labels))
            return self

        def observe(self, value: float) -> None:
            assert value >= 0.0
            return None

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise httpx.ConnectTimeout("temporary timeout")
        if calls == 2:
            return httpx.Response(503)
        return httpx.Response(200, json={"ok": True})

    monkeypatch.setattr(
        observability_module,
        "SOURCE_HTTP_REQUEST_TOTAL",
        _Counter("request"),
    )
    monkeypatch.setattr(
        observability_module,
        "SOURCE_HTTP_RETRY_TOTAL",
        _Counter("retry"),
    )
    monkeypatch.setattr(
        observability_module,
        "SOURCE_HTTP_REQUEST_DURATION_SECONDS",
        _Histogram(),
    )

    body = post_json_with_retries(
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        url="http://authority.test/post",
        payload={"portfolio_id": "PB_SG_GLOBAL_BAL_001"},
        headers={"X-Correlation-Id": "corr-sensitive"},
        attempts=3,
        unavailable_error="AUTH_UNAVAILABLE",
        rejected_error="AUTH_REJECTED",
        invalid_response_error="AUTH_INVALID_RESPONSE",
        source_service="lotus-risk",
    )

    assert body == {"ok": True}
    assert captured == [
        (
            "retry",
            {
                "source_service": "lotus-risk",
                "method": "post",
                "reason": "transport_error",
            },
        ),
        (
            "retry",
            {
                "source_service": "lotus-risk",
                "method": "post",
                "reason": "transient_status",
            },
        ),
        (
            "request",
            {
                "source_service": "lotus-risk",
                "method": "post",
                "outcome": "success",
            },
        ),
        (
            "duration",
            {
                "source_service": "lotus-risk",
                "method": "post",
                "outcome": "success",
            },
        ),
    ]
    assert "PB_SG_GLOBAL_BAL_001" not in json.dumps(captured)
    assert "corr-sensitive" not in json.dumps(captured)
