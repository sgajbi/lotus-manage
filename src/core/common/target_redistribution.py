from decimal import Decimal
from typing import Literal


def redistribute_sell_only_excess(
    *,
    eligible_targets: dict[str, Decimal],
    buy_set: set[str],
    sell_only_excess: Decimal,
) -> Literal["READY", "PENDING_REVIEW"]:
    if sell_only_excess <= Decimal("0.0"):
        return "READY"

    recipients = {k: v for k, v in eligible_targets.items() if k in buy_set}
    total_recipient_weight = sum(recipients.values())
    if total_recipient_weight <= Decimal("0.0"):
        return "PENDING_REVIEW"

    for instrument_id, weight in recipients.items():
        eligible_targets[instrument_id] = weight + (
            sell_only_excess * (weight / total_recipient_weight)
        )
    return "READY"
