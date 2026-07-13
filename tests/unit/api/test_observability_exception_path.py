from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from src.api.main import (
    _campaign_problem_details_exception_handler,
    _pm_quality_problem_details_exception_handler,
)
from src.api.observability import setup_observability


def test_observability_middleware_logs_and_reraises_unhandled_exceptions() -> None:
    app = FastAPI()
    setup_observability(app)

    @app.get("/boom")
    async def boom() -> None:
        raise RuntimeError("boom")

    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/boom")

    assert response.status_code == 500


@pytest.mark.asyncio
async def test_problem_details_exception_wrappers_reraise_unexpected_exceptions() -> None:
    pm_quality_error = RuntimeError("unexpected-pm-quality")
    with pytest.raises(RuntimeError, match="unexpected-pm-quality"):
        await _pm_quality_problem_details_exception_handler(None, pm_quality_error)  # type: ignore[arg-type]

    campaign_error = RuntimeError("unexpected-campaign")
    with pytest.raises(RuntimeError, match="unexpected-campaign"):
        await _campaign_problem_details_exception_handler(None, campaign_error)  # type: ignore[arg-type]
