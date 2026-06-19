from __future__ import annotations

import warnings

from scripts.ci_warning_filters import suppress_external_starlette_testclient_httpx_warning


def test_suppresses_known_starlette_testclient_httpx_warning() -> None:
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("default")
        suppress_external_starlette_testclient_httpx_warning()

        warnings.warn(
            "Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.",
            DeprecationWarning,
            stacklevel=1,
        )

    assert captured == []


def test_does_not_suppress_unrelated_deprecation_warnings() -> None:
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("default")
        suppress_external_starlette_testclient_httpx_warning()

        warnings.warn(
            "project-owned deprecation warning",
            DeprecationWarning,
            stacklevel=1,
        )

    assert len(captured) == 1
    assert str(captured[0].message) == "project-owned deprecation warning"
