"""
FILE: tests/golden/test_golden_batch_analysis.py
"""

import json
import os
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from src.api.main import app, get_db_session


def load_golden_file(filename: str) -> dict:
    path = os.path.join(os.path.dirname(__file__), "../golden_data", filename)
    with open(path, "r") as f:
        return json.loads(f.read(), parse_float=Decimal)


async def override_get_db_session():
    yield None


@pytest.fixture(autouse=True)
def override_db_dependency():
    original_overrides = dict(app.dependency_overrides)
    app.dependency_overrides[get_db_session] = override_get_db_session
    yield
    app.dependency_overrides = original_overrides


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_golden_batch_scenario_13_what_if_analysis(client):
    data = load_golden_file("scenario_13_what_if_analysis.json")
    payload = data["batch_inputs"]

    response = client.post("/api/v1/rebalance/analyze", json=payload)
    assert response.status_code == 200
    body = response.json()

    assert body["batch_run_id"].startswith("batch_")
    assert (
        body["base_snapshot_ids"]["portfolio_snapshot_id"]
        == payload["portfolio_snapshot"]["portfolio_id"]
    )
    assert body["base_snapshot_ids"]["market_data_snapshot_id"] == "md"

    assert "ignore_checks" in body["results"]
    assert "invalid_case" in body["failed_scenarios"]
    assert body["failed_scenarios"]["invalid_case"].startswith("INVALID_OPTIONS:")
    assert "PARTIAL_BATCH_FAILURE" in body["warnings"]

    compare = body["comparison_metrics"]["ignore_checks"]
    result = body["results"]["ignore_checks"]
    expected_turnover = sum(
        Decimal(i["notional_base"]["amount"])
        for i in result["intents"]
        if i["intent_type"] == "SECURITY_TRADE"
    )
    assert Decimal(compare["gross_turnover_notional_base"]["amount"]) == expected_turnover


def test_golden_batch_scenario_13_zero_turnover(client):
    data = load_golden_file("scenario_13_zero_turnover_batch.json")
    payload = data["batch_inputs"]

    response = client.post("/api/v1/rebalance/analyze", json=payload)
    assert response.status_code == 200
    body = response.json()

    assert "steady" in body["results"]
    assert body["failed_scenarios"] == {}
    metric = body["comparison_metrics"]["steady"]
    assert metric["security_intent_count"] == 0
    assert Decimal(metric["gross_turnover_notional_base"]["amount"]) == Decimal("0")


