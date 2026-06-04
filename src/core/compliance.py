"""
FILE: src/core/compliance.py
Post-trade Rule Engine implementation (RFC-0005/RFC-0006B).
"""

from decimal import Decimal

from src.core.models import DiagnosticsData, EngineOptions, RuleResult, SimulatedState


def _cash_band_rule_result(
    *,
    state: SimulatedState,
    options: EngineOptions,
) -> RuleResult:
    cash_weight = next(
        (a.weight for a in state.allocation_by_asset_class if a.key == "CASH"), Decimal("0")
    )
    min_w = options.cash_band_min_weight
    max_w = options.cash_band_max_weight

    if cash_weight < min_w or cash_weight > max_w:
        return RuleResult(
            rule_id="CASH_BAND",
            severity="SOFT",
            status="FAIL",
            measured=cash_weight,
            threshold={"min": min_w, "max": max_w},
            reason_code="THRESHOLD_BREACH",
            remediation_hint="Portfolio cash is outside policy bands.",
        )

    return RuleResult(
        rule_id="CASH_BAND",
        severity="SOFT",
        status="PASS",
        measured=cash_weight,
        threshold={"min": min_w, "max": max_w},
        reason_code="OK",
    )


def _single_position_max_rule_results(
    *,
    state: SimulatedState,
    options: EngineOptions,
) -> list[RuleResult]:
    limit_w = options.single_position_max_weight
    if limit_w is None:
        return [
            RuleResult(
                rule_id="SINGLE_POSITION_MAX",
                severity="HARD",
                status="PASS",
                measured=Decimal("0"),
                threshold={"max": Decimal("-1")},
                reason_code="NO_LIMIT_SET",
            )
        ]

    breach_results: list[RuleResult] = []
    max_measured = Decimal("0")
    for pos in state.allocation_by_instrument:
        max_measured = max(max_measured, pos.weight)
        if pos.weight > limit_w + Decimal("0.001"):
            breach_results.append(
                RuleResult(
                    rule_id="SINGLE_POSITION_MAX",
                    severity="HARD",
                    status="FAIL",
                    measured=pos.weight,
                    threshold={"max": limit_w},
                    reason_code="LIMIT_BREACH",
                    remediation_hint=f"Instrument {pos.key} exceeds max weight.",
                )
            )

    if breach_results:
        return breach_results

    return [
        RuleResult(
            rule_id="SINGLE_POSITION_MAX",
            severity="HARD",
            status="PASS",
            measured=max_measured,
            threshold={"max": limit_w},
            reason_code="OK",
        )
    ]


def _data_quality_rule_result(
    *,
    diagnostics: DiagnosticsData,
    options: EngineOptions,
) -> RuleResult:
    dq_count = 0

    if options.block_on_missing_prices:
        dq_count += len(diagnostics.data_quality.get("price_missing", []))

    if options.block_on_missing_fx:
        dq_count += len(diagnostics.data_quality.get("fx_missing", []))

    dq_count += len(diagnostics.data_quality.get("shelf_missing", []))

    if dq_count > 0:
        return RuleResult(
            rule_id="DATA_QUALITY",
            severity="HARD",
            status="FAIL",
            measured=Decimal(dq_count),
            threshold={"max": Decimal("0")},
            reason_code="MISSING_DATA",
            remediation_hint="Check diagnostics for missing prices/FX.",
        )

    return RuleResult(
        rule_id="DATA_QUALITY",
        severity="HARD",
        status="PASS",
        measured=Decimal(dq_count),
        threshold={"max": Decimal("0")},
        reason_code="OK",
    )


def _min_trade_size_rule_result(*, diagnostics: DiagnosticsData) -> RuleResult:
    suppressed_count = len(diagnostics.suppressed_intents)
    if suppressed_count > 0:
        return RuleResult(
            rule_id="MIN_TRADE_SIZE",
            severity="SOFT",
            status="PASS",
            measured=Decimal(suppressed_count),
            threshold={"min": Decimal("0")},
            reason_code="INTENTS_SUPPRESSED",
        )

    return RuleResult(
        rule_id="MIN_TRADE_SIZE",
        severity="SOFT",
        status="PASS",
        measured=Decimal("0"),
        threshold={"min": Decimal("0")},
        reason_code="OK",
    )


def _no_shorting_rule_result(*, state: SimulatedState) -> RuleResult:
    min_qty = Decimal("0")
    for position in state.positions:
        if position.quantity < Decimal("0"):
            min_qty = min(min_qty, position.quantity)

    if min_qty < Decimal("0"):
        return RuleResult(
            rule_id="NO_SHORTING",
            severity="HARD",
            status="FAIL",
            measured=min_qty,
            threshold={"min": Decimal("0")},
            reason_code="SELL_EXCEEDS_HOLDINGS",
            remediation_hint="Reduce sell quantity.",
        )

    return RuleResult(
        rule_id="NO_SHORTING",
        severity="HARD",
        status="PASS",
        measured=Decimal("0"),
        threshold={"min": Decimal("0")},
        reason_code="OK",
    )


def _insufficient_cash_rule_result(*, state: SimulatedState) -> RuleResult:
    min_cash = Decimal("0")
    for cash_balance in state.cash_balances:
        if cash_balance.amount < Decimal("0"):
            min_cash = min(min_cash, cash_balance.amount)

    if min_cash < Decimal("0"):
        return RuleResult(
            rule_id="INSUFFICIENT_CASH",
            severity="HARD",
            status="FAIL",
            measured=min_cash,
            threshold={"min": Decimal("0")},
            reason_code="CASH_BALANCE_NEGATIVE",
            remediation_hint="Ensure sufficient funding.",
        )

    return RuleResult(
        rule_id="INSUFFICIENT_CASH",
        severity="HARD",
        status="PASS",
        measured=Decimal("0"),
        threshold={"min": Decimal("0")},
        reason_code="OK",
    )


class RuleEngine:
    """
    Evaluates business rules against the simulated after-state.
    Supports HARD (Block), SOFT (Review), and INFO (Log) severities.
    Enforces RFC-0006B: All core rules must emit a result.
    """

    @staticmethod
    def evaluate(
        state: SimulatedState, options: EngineOptions, diagnostics: DiagnosticsData
    ) -> list[RuleResult]:
        results = []

        results.append(_cash_band_rule_result(state=state, options=options))

        results.extend(_single_position_max_rule_results(state=state, options=options))
        results.append(_data_quality_rule_result(diagnostics=diagnostics, options=options))
        results.append(_min_trade_size_rule_result(diagnostics=diagnostics))
        results.append(_no_shorting_rule_result(state=state))
        results.append(_insufficient_cash_rule_result(state=state))

        return results
