from __future__ import annotations

import warnings

from starlette.exceptions import StarletteDeprecationWarning

STARLETTE_TESTCLIENT_HTTPX_WARNING = (
    r"Using `httpx` with `starlette\.testclient` is deprecated; install `httpx2` instead\."
)


def suppress_external_starlette_testclient_httpx_warning() -> None:
    """Suppress a known third-party TestClient import warning in CI entry points."""
    warnings.filterwarnings(
        "ignore",
        message=STARLETTE_TESTCLIENT_HTTPX_WARNING,
        category=StarletteDeprecationWarning,
    )
