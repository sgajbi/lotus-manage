import json
from datetime import date
from decimal import Decimal

import httpx
import pytest

from src.core.construction.vocabulary import ConstructionMethodStatus
from src.infrastructure.risk_authority import (
    LotusRiskAuthorityClient,
    LotusRiskAuthorityConfig,
    LotusRiskAuthorityUnavailableError,
)
from src.infrastructure.risk_authority.client import (
    _post_with_retries,
    _regime_context_from_scenario_response,
    _scenario_bucket,
    _scenario_status_from_supportability,
)
from src.core.rebalance.engine import run_simulation
from tests.shared.factories import valid_api_payload


def _result():
    from src.api.request_models import RebalanceRequest

    payload = valid_api_payload()
    payload["model_portfolio"]["targets"] = [{"instrument_id": "EQ_1", "weight": "0.50"}]
    payload["shelf_entries"] = [
        {"instrument_id": "EQ_1", "status": "APPROVED", "asset_class": "EQUITY"}
    ]
    request = RebalanceRequest.model_validate(payload)
    return run_simulation(
        portfolio=request.portfolio_snapshot,
        market_data=request.market_data_snapshot,
        model=request.model_portfolio,
        shelf=request.shelf_entries,
        options=request.options,
        request_hash="risk-authority-test",
        correlation_id="corr-risk-authority-test",
    )


def _risk_response(
    *,
    state: str = "ready",
    reason: str = "calculation_complete",
    hhi_proposed: float = 1300.0,
    top_position_weight_proposed: float = 0.24,
    top_issuer_weight_proposed: float = 0.28,
    coverage_status: str = "complete",
) -> dict[str, object]:
    return {
        "source_service": "lotus-risk",
        "input_mode": "stateless",
        "risk_proxy": {
            "hhi_current": 1200.0,
            "hhi_proposed": hhi_proposed,
            "hhi_delta": hhi_proposed - 1200.0,
        },
        "single_position_concentration": {
            "top_position_weight_proposed": top_position_weight_proposed,
        },
        "issuer_concentration": {
            "top_issuer_weight_proposed": top_issuer_weight_proposed,
            "coverage_status": coverage_status,
        },
        "metadata": {
            "calculation_supportability": {
                "state": state,
                "reason": reason,
                "freshness_bucket": "current",
            }
        },
    }


def _regime_scenario_response(
    *,
    supportability: str = "ready",
    worst_case_loss_pct: float = 0.0845,
    maximum_allowed_loss_pct: float = 0.12,
    reason_codes: list[str] | None = None,
) -> dict[str, object]:
    return {
        "scenario_pack_id": "CIO_REGIME_2026_Q2",
        "portfolio_id": "pf_test",
        "as_of_date": "2026-05-06",
        "worst_case_loss_pct": worst_case_loss_pct,
        "maximum_allowed_loss_pct": maximum_allowed_loss_pct,
        "breach": worst_case_loss_pct > maximum_allowed_loss_pct,
        "scenario_results": [],
        "reason_codes": reason_codes or ["REGIME_SCENARIO_PACK_READY"],
        "metadata": {
            "product_name": "RegimeScenarioPackEvaluation",
            "product_version": "v1",
            "source_service": "lotus-risk",
            "lineage_version": "risk-regime-scenario-pack-evaluation.v1",
            "request_fingerprint": "sha256:test",
            "calculation_supportability": supportability,
        },
    }


def test_lotus_risk_authority_client_maps_concentration_supportability() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["payload"] = request.read()
        return httpx.Response(
            200,
            json=_risk_response(),
        )

    client = LotusRiskAuthorityClient(
        config=LotusRiskAuthorityConfig(base_url="http://risk.test"),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    context = client.concentration_context(
        result=_result(),
        correlation_id="corr-risk",
    )

    assert captured["url"] == "http://risk.test/analytics/risk/concentration"
    assert context.source_system == "lotus-risk"
    assert context.supportability_status == ConstructionMethodStatus.READY
    assert context.concentration_hhi_delta == 100
    assert context.concentration_breaches == 0
    assert context.reason_codes == ["LOTUS_RISK_CONCENTRATION_CALCULATION_COMPLETE"]


def test_lotus_risk_authority_client_maps_regime_scenario_pack_evaluation() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["headers"] = dict(request.headers)
        captured["payload"] = json.loads(request.read().decode("utf-8"))
        return httpx.Response(200, json=_regime_scenario_response())

    client = LotusRiskAuthorityClient(
        config=LotusRiskAuthorityConfig(base_url="http://risk.test"),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    context = client.regime_scenario_context(
        result=_result(),
        portfolio_id="pf_test",
        as_of_date=date(2026, 5, 6),
        correlation_id="corr-regime",
    )

    payload = captured["payload"]
    assert captured["url"] == "http://risk.test/analytics/risk/regime-scenario-pack/evaluate"
    assert captured["headers"]["x-correlation-id"] == "corr-regime"
    assert payload["scenario_pack_id"] == "CIO_REGIME_2026_Q2"
    assert payload["portfolio_id"] == "pf_test"
    assert payload["as_of_date"] == "2026-05-06"
    assert payload["maximum_allowed_loss_pct"] == 0.12
    assert {"bucket": "EQUITY", "weight": 0.5} in payload["exposures"]
    assert {"bucket": "CASH", "weight": 0.5} in payload["exposures"]
    assert context.source_system == "lotus-risk"
    assert context.supportability_status == ConstructionMethodStatus.READY
    assert context.scenario_pack_id == "CIO_REGIME_2026_Q2"
    assert context.worst_case_loss_pct == Decimal("0.0845")
    assert context.reason_codes == ["REGIME_SCENARIO_PACK_READY"]


def test_lotus_risk_authority_client_maps_regime_scenario_pending_review() -> None:
    client = LotusRiskAuthorityClient(
        config=LotusRiskAuthorityConfig(base_url="http://risk.test"),
        client=httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    200,
                    json=_regime_scenario_response(
                        supportability="pending_review",
                        worst_case_loss_pct=0.18,
                        maximum_allowed_loss_pct=0.12,
                        reason_codes=[
                            "REGIME_SCENARIO_PACK_READY",
                            "REGIME_SCENARIO_POLICY_THRESHOLD_BREACH",
                        ],
                    ),
                )
            )
        ),
    )

    context = client.regime_scenario_context(
        result=_result(),
        portfolio_id="pf_test",
        as_of_date=date(2026, 5, 6),
        correlation_id=None,
    )

    assert context.supportability_status == ConstructionMethodStatus.PENDING_REVIEW
    assert context.worst_case_loss_pct == Decimal("0.18")
    assert "REGIME_SCENARIO_POLICY_THRESHOLD_BREACH" in context.reason_codes


def test_lotus_risk_authority_client_fails_closed_on_unavailable_risk() -> None:
    client = LotusRiskAuthorityClient(
        config=LotusRiskAuthorityConfig(base_url="http://risk.test", max_attempts=1),
        client=httpx.Client(
            transport=httpx.MockTransport(lambda request: httpx.Response(503, json={}))
        ),
    )

    try:
        client.concentration_context(result=_result(), correlation_id=None)
    except LotusRiskAuthorityUnavailableError as exc:
        assert str(exc) == "LOTUS_RISK_UNAVAILABLE"
    else:
        raise AssertionError("expected lotus-risk authority failure")


def test_lotus_risk_authority_client_retries_transient_transport_failure() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise httpx.ReadTimeout("risk timeout")
        return httpx.Response(200, json=_risk_response())

    client = LotusRiskAuthorityClient(
        config=LotusRiskAuthorityConfig(base_url="http://risk.test", max_attempts=2),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    context = client.concentration_context(result=_result(), correlation_id="corr-retry")

    assert attempts == 2
    assert context.supportability_status == ConstructionMethodStatus.READY


def test_lotus_risk_authority_client_fails_closed_after_transport_retries() -> None:
    client = LotusRiskAuthorityClient(
        config=LotusRiskAuthorityConfig(base_url="http://risk.test", max_attempts=2),
        client=httpx.Client(
            transport=httpx.MockTransport(
                lambda request: (_ for _ in ()).throw(httpx.ConnectError("risk offline"))
            )
        ),
    )

    with pytest.raises(LotusRiskAuthorityUnavailableError, match="LOTUS_RISK_UNAVAILABLE"):
        client.concentration_context(result=_result(), correlation_id=None)


def test_lotus_risk_authority_client_retries_transient_503_then_maps_breaches() -> None:
    responses = [
        httpx.Response(503, json={}),
        httpx.Response(
            200,
            json=_risk_response(
                hhi_proposed=2600.0,
                top_position_weight_proposed=0.34,
                top_issuer_weight_proposed=0.45,
                coverage_status="partial",
            ),
        ),
    ]

    client = LotusRiskAuthorityClient(
        config=LotusRiskAuthorityConfig(base_url="http://risk.test", max_attempts=2),
        client=httpx.Client(transport=httpx.MockTransport(lambda request: responses.pop(0))),
    )

    context = client.concentration_context(result=_result(), correlation_id=None)

    assert context.concentration_breaches == 3
    assert context.issuer_coverage_status == "partial"
    assert context.supportability_status == ConstructionMethodStatus.READY
    assert "ISSUER_COVERAGE_PARTIAL" in context.reason_codes
    assert "RISK_CONCENTRATION_LIMIT_BREACH" in context.reason_codes


@pytest.mark.parametrize(
    ("status_code", "expected_message"),
    [
        (400, "LOTUS_RISK_CONCENTRATION_REJECTED"),
        (500, "LOTUS_RISK_UNAVAILABLE"),
    ],
)
def test_lotus_risk_authority_client_fails_closed_on_rejected_or_failed_response(
    status_code: int,
    expected_message: str,
) -> None:
    client = LotusRiskAuthorityClient(
        config=LotusRiskAuthorityConfig(base_url="http://risk.test", max_attempts=1),
        client=httpx.Client(
            transport=httpx.MockTransport(lambda request: httpx.Response(status_code, json={}))
        ),
    )

    with pytest.raises(LotusRiskAuthorityUnavailableError, match=expected_message):
        client.concentration_context(result=_result(), correlation_id=None)


def test_lotus_risk_authority_client_fails_closed_on_invalid_response_shape() -> None:
    client = LotusRiskAuthorityClient(
        config=LotusRiskAuthorityConfig(base_url="http://risk.test"),
        client=httpx.Client(
            transport=httpx.MockTransport(lambda request: httpx.Response(200, json=[]))
        ),
    )

    with pytest.raises(LotusRiskAuthorityUnavailableError, match="LOTUS_RISK_INVALID_RESPONSE"):
        client.concentration_context(result=_result(), correlation_id=None)


@pytest.mark.parametrize(
    ("state", "expected_status"),
    [
        ("stale", ConstructionMethodStatus.DEGRADED),
        ("degraded", ConstructionMethodStatus.DEGRADED),
        ("empty", ConstructionMethodStatus.PENDING_REVIEW),
        ("blocked_by_policy", ConstructionMethodStatus.BLOCKED),
    ],
)
def test_lotus_risk_authority_client_maps_non_ready_supportability_states(
    state: str,
    expected_status: ConstructionMethodStatus,
) -> None:
    client = LotusRiskAuthorityClient(
        config=LotusRiskAuthorityConfig(base_url="http://risk.test"),
        client=httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(200, json=_risk_response(state=state))
            )
        ),
    )

    context = client.concentration_context(result=_result(), correlation_id=None)

    assert context.supportability_status == expected_status


def test_lotus_risk_authority_client_closes_owned_client() -> None:
    class _OwnedClient:
        closed = False

        def close(self) -> None:
            self.closed = True

    owned_client = _OwnedClient()
    client = LotusRiskAuthorityClient(config=LotusRiskAuthorityConfig(base_url="http://risk.test"))
    client._client = owned_client

    client.close()

    assert owned_client.closed is True


def test_lotus_risk_authority_client_closes_owned_runtime_client(monkeypatch) -> None:
    closed = {"value": False}

    class _OwnedClient:
        def __init__(self, *, timeout: float) -> None:
            self.timeout = timeout

        def post(self, *_args, **_kwargs):
            return httpx.Response(200, json=_risk_response())

        def close(self) -> None:
            closed["value"] = True

    monkeypatch.setattr(httpx, "Client", _OwnedClient)
    client = LotusRiskAuthorityClient(config=LotusRiskAuthorityConfig(base_url="http://risk.test"))

    context = client.concentration_context(result=_result(), correlation_id=None)

    assert context.supportability_status == ConstructionMethodStatus.READY
    assert closed["value"] is True


def test_lotus_risk_authority_client_closes_owned_regime_runtime_client(monkeypatch) -> None:
    closed = {"value": False}

    class _OwnedClient:
        def __init__(self, *, timeout: float) -> None:
            self.timeout = timeout

        def post(self, *_args, **_kwargs):
            return httpx.Response(200, json=_regime_scenario_response())

        def close(self) -> None:
            closed["value"] = True

    monkeypatch.setattr(httpx, "Client", _OwnedClient)
    client = LotusRiskAuthorityClient(config=LotusRiskAuthorityConfig(base_url="http://risk.test"))

    context = client.regime_scenario_context(
        result=_result(),
        portfolio_id="pf_test",
        as_of_date=date(2026, 5, 6),
        correlation_id=None,
    )

    assert context.supportability_status == ConstructionMethodStatus.READY
    assert closed["value"] is True


def test_lotus_risk_authority_post_helper_rejects_invalid_json_and_empty_attempt_plan() -> None:
    invalid_json_client = httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, content=b"{"))
    )

    with pytest.raises(LotusRiskAuthorityUnavailableError, match="LOTUS_RISK_INVALID_RESPONSE"):
        _post_with_retries(
            client=invalid_json_client,
            url="http://risk.test/invalid",
            payload={},
            headers={},
            attempts=1,
        )

    idle_client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200)))
    with pytest.raises(LotusRiskAuthorityUnavailableError, match="LOTUS_RISK_UNAVAILABLE"):
        _post_with_retries(
            client=idle_client,
            url="http://risk.test/idle",
            payload={},
            headers={},
            attempts=0,
        )


def test_lotus_risk_authority_regime_response_edges_are_fail_closed() -> None:
    context = _regime_context_from_scenario_response(
        {
            **_regime_scenario_response(supportability="degraded"),
            "reason_codes": "not-a-list",
        }
    )
    assert context.supportability_status == ConstructionMethodStatus.DEGRADED
    assert context.reason_codes == ["REGIME_SCENARIO_PACK_RESPONSE_REASON_CODES_MISSING"]
    assert _scenario_status_from_supportability("blocked") == ConstructionMethodStatus.BLOCKED

    with pytest.raises(LotusRiskAuthorityUnavailableError, match="LOTUS_RISK_INVALID_RESPONSE"):
        _regime_context_from_scenario_response({"metadata": {}})


def test_lotus_risk_authority_scenario_bucket_aliases_are_stable() -> None:
    assert _scenario_bucket("stocks") == "EQUITY"
    assert _scenario_bucket("fixed income") == "FIXED_INCOME"
    assert _scenario_bucket("private-markets") == "ALTERNATIVES"
    assert _scenario_bucket("money market") == "CASH"
    assert _scenario_bucket("commodities") == "COMMODITIES"
