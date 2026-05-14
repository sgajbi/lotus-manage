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
