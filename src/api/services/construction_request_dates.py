from __future__ import annotations

from datetime import date, datetime, timezone
import re

from src.api.request_models import RebalanceRequest

_DATE_PATTERN = re.compile(r"(\d{4})[-_](\d{2})[-_](\d{2})")


def construction_as_of_date(*, request: RebalanceRequest) -> date:
    snapshot_id = getattr(request.market_data_snapshot, "snapshot_id", "")
    for candidate in (
        snapshot_id or "",
        getattr(request.portfolio_snapshot, "snapshot_id", "") or "",
    ):
        match = _DATE_PATTERN.search(candidate)
        if match is not None:
            return date(
                year=int(match.group(1)),
                month=int(match.group(2)),
                day=int(match.group(3)),
            )
        try:
            return date.fromisoformat(candidate[:10])
        except ValueError:
            continue
    return datetime.now(timezone.utc).date()


__all__ = ["construction_as_of_date"]
