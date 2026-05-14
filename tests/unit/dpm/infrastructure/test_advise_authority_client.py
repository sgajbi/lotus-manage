import json
from decimal import Decimal

import httpx
import pytest

from src.infrastructure.advise_authority import (
    LotusAdviseAuthorityClient,
    LotusAdviseAuthorityConfig,
    LotusAdviseAuthorityUnavailableError,
)
from src.infrastructure.advise_authority.client import (
    _tactical_house_view_cohort_from_response,
)


class _OwnedClientStub:
    def __init__(self, *, timeout: float) -> None:
        self.timeout = timeout
        self.closed = False

    def post(
        self,
        url: str,
        *,
        json: dict[str, object],
        headers: dict[str, str],
    ) -> httpx.Response:
        assert self.timeout == 2.0
        assert url == "http://advise.test/advisory/tactical-house-view/cohorts/evaluate"
        assert json["correlation_id"] == "corr-tactical"
        assert headers == {"X-Correlation-Id": "corr-tactical"}
        return httpx.Response(200, json=_cohort_response())

    def close(self) -> None:
        self.closed = True


def _cohort_response() -> dict[str, object]:
    return {
        "product_name": "TacticalHouseViewAffectedCohort",
        "product_version": "v1",
        "cohort_id": "sha256:tactical-cohort",
        "tactical_view_id": "THV_2026_Q2_US_QUALITY",
        "tactical_view_version": "2026.05",
        "theme_id": "US_QUALITY_EQUITIES",
        "as_of_date": "2026-05-14",
        "target_action": "INCREASE",
        "affected_portfolios": [
            {
                "portfolio_id": "PB_SG_GLOBAL_BAL_001",
                "mandate_id": "MANDATE_PB_SG_GLOBAL_BAL_001",
                "inclusion_reason_codes": [
                    "TACTICAL_HOUSE_VIEW_PORTFOLIO_AFFECTED",
                    "TACTICAL_HOUSE_VIEW_UNDERWEIGHT",
                ],
                "source_refs": [
                    {
                        "source_system": "lotus-core",
                        "source_type": "HoldingsAsOf",
                        "source_id": "holdings-asof-pb-sg-global-bal-001",
                        "source_version": "v1",
                        "content_hash": "sha256:holdings",
                    }
                ],
            }
        ],
        "excluded_portfolios": [],
        "supportability": {
            "state": "READY",
            "reason_codes": ["TACTICAL_HOUSE_VIEW_AFFECTED_COHORT_READY"],
            "evaluated_candidate_count": 1,
            "affected_count": 1,
            "excluded_count": 0,
        },
        "source_refs": [
            {
                "source_system": "lotus-advise",
                "source_type": "TACTICAL_HOUSE_VIEW_DECISION",
                "source_id": "thv-us-quality-2026-05",
                "source_version": "2026.05",
                "content_hash": "sha256:house-view",
            }
        ],
        "content_hash": "sha256:tactical-cohort-content",
        "generated_at": "2026-05-14T01:00:00Z",
        "correlation_id": "corr-tactical",
    }


def test_lotus_advise_authority_client_maps_tactical_house_view_cohort() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["headers"] = dict(request.headers)
        captured["payload"] = json.loads(request.read().decode("utf-8"))
        return httpx.Response(200, json=_cohort_response())

    client = LotusAdviseAuthorityClient(
        config=LotusAdviseAuthorityConfig(base_url="http://advise.test"),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    cohort = client.tactical_house_view_affected_cohort(
        tactical_view={
            "tactical_view_id": "THV_2026_Q2_US_QUALITY",
            "tactical_view_version": "2026.05",
            "theme_id": "US_QUALITY_EQUITIES",
            "as_of_date": "2026-05-14",
            "target_action": "INCREASE",
            "rationale": "Increase US quality equity exposure.",
            "source_refs": [
                {
                    "source_system": "lotus-advise",
                    "source_type": "TACTICAL_HOUSE_VIEW_DECISION",
                    "source_id": "thv-us-quality-2026-05",
                }
            ],
        },
        candidate_portfolios=[
            {
                "portfolio_id": "PB_SG_GLOBAL_BAL_001",
                "portfolio_type": "DISCRETIONARY",
                "discretionary_mandate": True,
                "alignment_signal": "UNDERWEIGHT",
                "source_refs": [
                    {
                        "source_system": "lotus-core",
                        "source_type": "HoldingsAsOf",
                        "source_id": "holdings-asof-pb-sg-global-bal-001",
                    }
                ],
            }
        ],
        eligible_portfolio_types=["DISCRETIONARY"],
        min_exposure_weight=Decimal("0.05"),
        correlation_id="corr-tactical",
    )

    payload = captured["payload"]
    assert captured["url"] == "http://advise.test/advisory/tactical-house-view/cohorts/evaluate"
    assert captured["headers"]["x-correlation-id"] == "corr-tactical"
    assert payload["eligible_portfolio_types"] == ["DISCRETIONARY"]
    assert payload["min_exposure_weight"] == "0.05"
    assert cohort.product_name == "TacticalHouseViewAffectedCohort"
    assert cohort.supportability_state == "READY"
    assert cohort.affected_portfolios[0].portfolio_id == "PB_SG_GLOBAL_BAL_001"
    assert cohort.affected_portfolios[0].source_refs[0]["source_type"] == "HoldingsAsOf"


def test_lotus_advise_authority_client_rejects_invalid_tactical_house_view_response() -> None:
    with pytest.raises(LotusAdviseAuthorityUnavailableError, match="LOTUS_ADVISE_INVALID_RESPONSE"):
        _tactical_house_view_cohort_from_response({"cohort_id": "missing-required-fields"})

    invalid_body = _cohort_response()
    invalid_body["affected_portfolios"] = ["not-an-object"]
    with pytest.raises(LotusAdviseAuthorityUnavailableError, match="LOTUS_ADVISE_INVALID_RESPONSE"):
        _tactical_house_view_cohort_from_response(invalid_body)


def test_lotus_advise_authority_client_maps_http_failures_to_dependency_errors() -> None:
    client = LotusAdviseAuthorityClient(
        config=LotusAdviseAuthorityConfig(base_url="http://advise.test"),
        client=httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(422))),
    )

    with pytest.raises(
        LotusAdviseAuthorityUnavailableError,
        match="LOTUS_ADVISE_TACTICAL_HOUSE_VIEW_COHORT_REJECTED",
    ):
        client.tactical_house_view_affected_cohort(
            tactical_view={},
            candidate_portfolios=[],
            eligible_portfolio_types=[],
            min_exposure_weight=None,
            correlation_id="corr-tactical",
        )


def test_lotus_advise_authority_client_retries_transient_source_failures() -> None:
    calls = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise httpx.ConnectTimeout("temporary timeout")
        return httpx.Response(200, json=_cohort_response())

    client = LotusAdviseAuthorityClient(
        config=LotusAdviseAuthorityConfig(base_url="http://advise.test", max_attempts=2),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    cohort = client.tactical_house_view_affected_cohort(
        tactical_view={},
        candidate_portfolios=[],
        eligible_portfolio_types=[],
        min_exposure_weight=None,
        correlation_id="",
    )

    assert calls == 2
    assert cohort.cohort_id == "sha256:tactical-cohort"


def test_lotus_advise_authority_client_retries_retryable_http_status() -> None:
    calls = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(503)
        return httpx.Response(200, json=_cohort_response())

    client = LotusAdviseAuthorityClient(
        config=LotusAdviseAuthorityConfig(base_url="http://advise.test", max_attempts=2),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    cohort = client.tactical_house_view_affected_cohort(
        tactical_view={},
        candidate_portfolios=[],
        eligible_portfolio_types=[],
        min_exposure_weight=None,
        correlation_id="corr-tactical",
    )

    assert calls == 2
    assert cohort.supportability_state == "READY"


def test_lotus_advise_authority_client_owns_and_closes_default_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clients: list[_OwnedClientStub] = []

    def client_factory(*, timeout: float) -> _OwnedClientStub:
        client = _OwnedClientStub(timeout=timeout)
        clients.append(client)
        return client

    monkeypatch.setattr(
        "src.infrastructure.advise_authority.client.httpx.Client",
        client_factory,
    )
    client = LotusAdviseAuthorityClient(
        config=LotusAdviseAuthorityConfig(base_url="http://advise.test"),
    )

    cohort = client.tactical_house_view_affected_cohort(
        tactical_view={},
        candidate_portfolios=[],
        eligible_portfolio_types=[],
        min_exposure_weight=None,
        correlation_id="corr-tactical",
    )

    assert cohort.cohort_id == "sha256:tactical-cohort"
    assert len(clients) == 1
    assert clients[0].closed is True


def test_lotus_advise_authority_client_closes_owned_existing_client() -> None:
    client = LotusAdviseAuthorityClient(
        config=LotusAdviseAuthorityConfig(base_url="http://advise.test"),
    )
    owned_client = httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200)))
    client._client = owned_client

    client.close()

    assert owned_client.is_closed is True


@pytest.mark.parametrize(
    ("response", "expected_code"),
    [
        (httpx.Response(500), "LOTUS_ADVISE_UNAVAILABLE"),
        (httpx.Response(200, content=b"not-json"), "LOTUS_ADVISE_INVALID_RESPONSE"),
        (httpx.Response(200, json=["not-an-object"]), "LOTUS_ADVISE_INVALID_RESPONSE"),
    ],
)
def test_lotus_advise_authority_client_rejects_source_failure_shapes(
    response: httpx.Response,
    expected_code: str,
) -> None:
    client = LotusAdviseAuthorityClient(
        config=LotusAdviseAuthorityConfig(base_url="http://advise.test"),
        client=httpx.Client(transport=httpx.MockTransport(lambda _: response)),
    )

    with pytest.raises(LotusAdviseAuthorityUnavailableError, match=expected_code):
        client.tactical_house_view_affected_cohort(
            tactical_view={},
            candidate_portfolios=[],
            eligible_portfolio_types=[],
            min_exposure_weight=None,
            correlation_id="corr-tactical",
        )


def test_lotus_advise_authority_client_rejects_final_transport_failure() -> None:
    client = LotusAdviseAuthorityClient(
        config=LotusAdviseAuthorityConfig(base_url="http://advise.test", max_attempts=1),
        client=httpx.Client(
            transport=httpx.MockTransport(
                lambda _: (_ for _ in ()).throw(httpx.ConnectTimeout("timeout"))
            )
        ),
    )

    with pytest.raises(LotusAdviseAuthorityUnavailableError, match="LOTUS_ADVISE_UNAVAILABLE"):
        client.tactical_house_view_affected_cohort(
            tactical_view={},
            candidate_portfolios=[],
            eligible_portfolio_types=[],
            min_exposure_weight=None,
            correlation_id="corr-tactical",
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source_refs", "not-a-list"),
        ("source_refs", ["not-an-object"]),
        ("affected_portfolios", [{"portfolio_id": "PB_SG_GLOBAL_BAL_001", "source_refs": ["bad"]}]),
    ],
)
def test_tactical_house_view_response_parser_rejects_invalid_source_ref_shapes(
    field: str,
    value: object,
) -> None:
    body = _cohort_response()
    body[field] = value

    with pytest.raises(LotusAdviseAuthorityUnavailableError, match="LOTUS_ADVISE_INVALID_RESPONSE"):
        _tactical_house_view_cohort_from_response(body)


def test_tactical_house_view_response_parser_defaults_optional_source_fields() -> None:
    body = _cohort_response()
    body.pop("product_name")
    body.pop("product_version")
    body.pop("content_hash")
    body["supportability"] = {"state": None}
    body["affected_portfolios"] = [
        {
            "portfolio_id": "PB_SG_GLOBAL_BAL_001",
            "mandate_id": None,
            "source_refs": [],
        }
    ]

    cohort = _tactical_house_view_cohort_from_response(body)

    assert cohort.product_name == "TacticalHouseViewAffectedCohort"
    assert cohort.product_version == "v1"
    assert cohort.content_hash == ""
    assert cohort.supportability_state == "BLOCKED"
    assert cohort.supportability_reason_codes == (
        "TACTICAL_HOUSE_VIEW_SUPPORTABILITY_REASON_CODES_MISSING",
    )
    assert cohort.affected_portfolios[0].mandate_id is None
    assert cohort.affected_portfolios[0].inclusion_reason_codes == ()
