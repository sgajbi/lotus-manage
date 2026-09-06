"""Documented mandate response examples must validate against their schemas.

A hand-written `example` on a route is published in /openapi.json and read by
integrators as the shape of a real response. Adding a required field to the
response model does not update it, so the example silently becomes something
the API can never return - and every generated client and integration test
built from it starts from a shape that fails its own schema.

This walks the generated document rather than naming examples one by one, so a
field added to any mandate response model breaks here rather than in a
consumer.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.openapi.utils import get_openapi

from src.api.main import app
from src.api.services.mandate_service import DpmMandateDiff
from src.core.mandates import DpmMandateDigitalTwin

# Response models keyed by the mandate path whose 200 carries a hand-written
# example. /health is deliberately absent: it documents a description only, so
# there is nothing to drift out of step with its schema.
_MANDATE_RESPONSE_MODELS: dict[str, Any] = {
    "/api/v1/mandates/by-portfolio/{portfolio_id}": DpmMandateDigitalTwin,
    "/api/v1/mandates/{mandate_id}": DpmMandateDigitalTwin,
    "/api/v1/mandates/{mandate_id}/diff": DpmMandateDiff,
}


def _documented_examples() -> list[tuple[str, Any, Any]]:
    """Return (path, model, example) for every documented mandate 200 example."""

    openapi = get_openapi(
        title=app.title,
        version=app.version,
        routes=app.routes,
    )
    found: list[tuple[str, Any, Any]] = []
    for path, model in _MANDATE_RESPONSE_MODELS.items():
        operations = openapi["paths"].get(path, {})
        for operation in operations.values():
            content = operation.get("responses", {}).get("200", {}).get("content", {})
            example = content.get("application/json", {}).get("example")
            if example is not None:
                found.append((path, model, example))
    return found


def test_every_mandate_path_under_test_is_actually_documented() -> None:
    """Guard the guard: a renamed path would silently empty the parametrization.

    Without this, a zero-example run reports as a pass, and the check below
    would stop protecting anything while still reporting green.
    """

    openapi = get_openapi(title=app.title, version=app.version, routes=app.routes)
    missing_paths = set(_MANDATE_RESPONSE_MODELS) - set(openapi["paths"])
    assert not missing_paths, (
        f"mandate paths no longer exist and are checking nothing: {missing_paths}"
    )

    documented = {path for path, _, _ in _documented_examples()}
    assert documented == set(_MANDATE_RESPONSE_MODELS), (
        "a documented mandate example appeared or vanished; update "
        "_MANDATE_RESPONSE_MODELS so examples stay checked. Difference: "
        f"{documented ^ set(_MANDATE_RESPONSE_MODELS)}"
    )


@pytest.mark.parametrize(
    ("path", "model", "example"),
    _documented_examples(),
    ids=lambda value: value if isinstance(value, str) else "",
)
def test_documented_mandate_example_validates_against_its_response_model(
    path: str, model: Any, example: Any
) -> None:
    # model_validate raises with the offending field, which is the message
    # someone updating a response model needs to see.
    model.model_validate(example)
