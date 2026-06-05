import httpx
import pytest

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
