import httpx
import pytest

from src.core.construction.vocabulary import ConstructionMethodStatus
from src.infrastructure.risk_authority import (
    LotusRiskAuthorityClient,
    LotusRiskAuthorityConfig,
    LotusRiskAuthorityUnavailableError,
)
from src.core.rebalance.engine import run_simulation
from tests.shared.factories import valid_api_payload


def _result():
    from src.api.request_models import RebalanceRequest

    request = RebalanceRequest.model_validate(valid_api_payload())
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
