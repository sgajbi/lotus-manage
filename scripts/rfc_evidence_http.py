from collections.abc import Mapping
from typing import Any, TypeVar

import httpx


EvidenceFailure = TypeVar("EvidenceFailure", bound=Exception)


def request_expected_status(
    client: httpx.Client,
    method: str,
    path: str,
    *,
    expected_status: int,
    failure_type: type[EvidenceFailure],
    json_body: Mapping[str, Any] | None = None,
    headers: Mapping[str, str] | None = None,
    params: Mapping[str, Any] | None = None,
) -> httpx.Response:
    response = client.request(
        method,
        path,
        json=json_body,
        headers=headers,
        params=params,
    )
    if response.status_code != expected_status:
        raise failure_type(
            f"{method} {path}: expected {expected_status}, got {response.status_code}: {response.text}"
        )
    return response
