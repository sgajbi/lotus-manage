"""Explicit synthetic flow normalization: no FX, classification or fallback inference."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from src.core.composite_eligibility.observations import MonthlyFlowObservation


def admitted_monthly_flows(
    flows: list[MonthlyFlowObservation],
    *,
    start: str,
    end: str,
    currency: str,
    evaluated_at: datetime,
    source_generated_at: datetime,
) -> tuple[list[MonthlyFlowObservation], list[str]]:
    """Retain exact-ID replay once; contradictory payloads never pick a winner."""
    by_id, reasons = _unique_flows(flows)
    for flow in flows:
        reasons.update(
            _observation_reasons(
                flow,
                start=start,
                end=end,
                currency=currency,
                evaluated_at=evaluated_at,
                source_generated_at=source_generated_at,
            )
        )
    reasons.update(_reversal_reasons(by_id))
    admitted = [
        by_id[key]
        for key in sorted(by_id)
        if by_id[key].status == "POSTED"
        and by_id[key].classification in {"EXTERNAL_CASH", "REVERSAL"}
    ]
    return admitted, sorted(reasons)


def _unique_flows(
    flows: list[MonthlyFlowObservation],
) -> tuple[dict[str, MonthlyFlowObservation], set[str]]:
    by_id: dict[str, MonthlyFlowObservation] = {}
    reasons: set[str] = set()
    for flow in flows:
        prior = by_id.get(flow.event_id)
        if prior is not None and prior != flow:
            reasons.add("FLOW_DUPLICATE_CONTENT_CONFLICT")
        by_id[flow.event_id] = flow
    return by_id, reasons


def _observation_reasons(
    flow: MonthlyFlowObservation,
    *,
    start: str,
    end: str,
    currency: str,
    evaluated_at: datetime,
    source_generated_at: datetime,
) -> set[str]:
    reasons: set[str] = set()
    if not start <= flow.business_date <= end:
        reasons.add("FLOW_BUSINESS_DATE_OUTSIDE_MONTH")
    received = datetime.fromisoformat(flow.received_at)
    if received > evaluated_at:
        reasons.add("FLOW_RECEIVED_AFTER_EVALUATION")
    if received > source_generated_at:
        reasons.add("FLOW_RECEIVED_AFTER_SOURCE_CUT")
    if flow.currency != currency:
        reasons.add("FLOW_CURRENCY_NOT_NORMALIZED")
    if flow.classification == "IN_KIND":
        reasons.add("FLOW_IN_KIND_POLICY_UNAVAILABLE")
    return reasons


def _reversal_reasons(by_id: dict[str, MonthlyFlowObservation]) -> set[str]:
    reasons: set[str] = set()
    reversals: set[str] = set()
    for flow in by_id.values():
        if flow.classification != "REVERSAL" or flow.status == "CANCELLED":
            continue
        original = by_id.get(flow.reverses_event_id or "")
        if not _matches_original(original, flow):
            reasons.add("FLOW_REVERSAL_BINDING_INVALID")
        if flow.reverses_event_id in reversals:
            reasons.add("FLOW_MULTIPLE_REVERSALS")
        if flow.reverses_event_id is not None:
            reversals.add(flow.reverses_event_id)
    return reasons


def _matches_original(
    original: MonthlyFlowObservation | None,
    reversal: MonthlyFlowObservation,
) -> bool:
    if original is None:
        return False
    return (
        original.classification == "EXTERNAL_CASH"
        and original.status == "POSTED"
        and original.currency == reversal.currency
        and Decimal(original.amount) == -Decimal(reversal.amount)
    )
