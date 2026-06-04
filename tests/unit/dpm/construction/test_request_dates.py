from datetime import date

from src.api.request_models import RebalanceRequest
from src.api.services.construction_request_dates import (
    candidate_as_of_date,
    construction_as_of_date,
)
from tests.shared.factories import valid_api_payload


def _request_with_snapshot_ids(
    *,
    market_snapshot_id: str | None,
    portfolio_snapshot_id: str | None,
) -> RebalanceRequest:
    request = RebalanceRequest.model_validate(valid_api_payload())
    return request.model_copy(
        update={
            "market_data_snapshot": request.market_data_snapshot.model_copy(
                update={"snapshot_id": market_snapshot_id}
            ),
            "portfolio_snapshot": request.portfolio_snapshot.model_copy(
                update={"snapshot_id": portfolio_snapshot_id}
            ),
        }
    )


def test_candidate_as_of_date_parses_embedded_and_iso_dates() -> None:
    assert candidate_as_of_date("market_2026-06-04_batch") == date(2026, 6, 4)
    assert candidate_as_of_date("portfolio_2026_05_31_snapshot") == date(2026, 5, 31)
    assert candidate_as_of_date("2026-04-30T15:00:00Z") == date(2026, 4, 30)
    assert candidate_as_of_date("not-a-date") is None


def test_construction_as_of_date_prefers_market_snapshot_date() -> None:
    request = _request_with_snapshot_ids(
        market_snapshot_id="market_2026-06-04_batch",
        portfolio_snapshot_id="portfolio_2026-05-31_snapshot",
    )

    assert construction_as_of_date(request=request) == date(2026, 6, 4)


def test_construction_as_of_date_falls_back_to_portfolio_snapshot_date() -> None:
    request = _request_with_snapshot_ids(
        market_snapshot_id="market-without-date",
        portfolio_snapshot_id="portfolio_2026-05-31_snapshot",
    )

    assert construction_as_of_date(request=request) == date(2026, 5, 31)
