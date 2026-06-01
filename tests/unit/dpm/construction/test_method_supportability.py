from src.api.services import construction_method_supportability


def test_method_supportability_facade_exports_supportability_helpers() -> None:
    assert construction_method_supportability.__all__ == [
        "cashflow_projection_reason_codes",
        "currency_overlay_status",
        "derive_currency_overlay_context",
        "derive_liquidity_context",
        "liquidity_reason_codes",
        "liquidity_status",
        "missing_currency_overlay_pairs",
        "post_trade_cash_weight",
        "regime_stress_status",
    ]
