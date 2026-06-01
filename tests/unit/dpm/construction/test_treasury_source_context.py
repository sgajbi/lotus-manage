from src.api.services.construction_treasury_source_context import (
    external_treasury_currency_overlay_context,
)
from src.core.construction.vocabulary import ConstructionMethodStatus
from tests.unit.dpm.construction.source_product_context_fixtures import (
    currency_exposure_response,
    eligible_hedge_instruments_response,
    fx_forward_curve_response,
    hedge_policy_response,
    hedge_readiness_response,
)


def test_external_treasury_currency_overlay_context_preserves_fail_closed_readiness() -> None:
    context = external_treasury_currency_overlay_context(
        hedge_readiness=hedge_readiness_response(),
        currency_exposure=None,
        hedge_policy=None,
        eligible_hedge_instruments=None,
        fx_forward_curve=None,
    )

    assert context is not None
    assert context.supportability_status == ConstructionMethodStatus.BLOCKED
    assert context.source_system == "lotus-core"
    assert context.source_product_name == "ExternalHedgeExecutionReadiness"
    assert context.source_id == "core-hedge-readiness"
    assert context.eligible_currencies == ["EUR", "GBP"]
    assert context.hedge_ratio_min == 0
    assert context.hedge_ratio_max == 0
    assert context.missing_data_families == ["external_treasury_hedge_readiness"]
    assert context.blocked_capabilities == ["execution", "oms", "treasury"]
    assert context.reason_codes == [
        "EXTERNAL_TREASURY_SOURCE_NOT_INGESTED",
        "EXTERNAL_HEDGE_EXECUTION_READINESS_FAIL_CLOSED",
    ]


def test_external_treasury_currency_overlay_context_preserves_exposure_fallback() -> None:
    context = external_treasury_currency_overlay_context(
        hedge_readiness=None,
        currency_exposure=currency_exposure_response(),
        hedge_policy=None,
        eligible_hedge_instruments=None,
        fx_forward_curve=None,
    )

    assert context is not None
    assert context.supportability_status == ConstructionMethodStatus.BLOCKED
    assert context.source_product_name is None
    assert context.source_id
    assert context.eligible_currencies == ["EUR", "JPY"]
    assert context.external_currency_exposure_source_id == "core-currency-exposure"
    assert context.external_currency_exposure_count == 1
    assert context.external_currency_exposure_rows == [
        {"currency": "EUR", "net_exposure": "125000"}
    ]
    assert context.reason_codes == [
        "EXTERNAL_TREASURY_SOURCE_NOT_INGESTED",
        "EXTERNAL_CURRENCY_EXPOSURE_FAIL_CLOSED",
    ]


def test_external_treasury_currency_overlay_context_combines_source_family_evidence() -> None:
    context = external_treasury_currency_overlay_context(
        hedge_readiness=hedge_readiness_response(),
        currency_exposure=currency_exposure_response(),
        hedge_policy=hedge_policy_response(),
        eligible_hedge_instruments=eligible_hedge_instruments_response(),
        fx_forward_curve=fx_forward_curve_response(),
    )

    assert context is not None
    assert context.source_id == "core-hedge-readiness"
    assert context.external_currency_exposure_source_id == "core-currency-exposure"
    assert context.external_hedge_policy_source_id == "core-hedge-policy"
    assert context.external_eligible_hedge_instrument_source_id == "core-eligible-hedges"
    assert context.external_fx_forward_curve_source_id == "core-fx-forward-curve"
    assert context.missing_data_families == [
        "external_currency_exposure",
        "external_eligible_hedge_instruments",
        "external_fx_forward_curve",
        "external_hedge_policy",
        "external_treasury_hedge_readiness",
    ]
    assert context.blocked_capabilities == [
        "eligible-instrument",
        "execution",
        "forward-pricing",
        "fx",
        "hedge-policy",
        "oms",
        "suitability",
        "treasury",
    ]
    assert context.reason_codes == [
        "EXTERNAL_TREASURY_SOURCE_NOT_INGESTED",
        "EXTERNAL_HEDGE_EXECUTION_READINESS_FAIL_CLOSED",
        "EXTERNAL_CURRENCY_EXPOSURE_FAIL_CLOSED",
        "EXTERNAL_HEDGE_POLICY_FAIL_CLOSED",
        "EXTERNAL_ELIGIBLE_HEDGE_INSTRUMENTS_FAIL_CLOSED",
        "EXTERNAL_FX_FORWARD_CURVE_FAIL_CLOSED",
    ]


def test_external_treasury_currency_overlay_context_absent_without_source_response() -> None:
    assert (
        external_treasury_currency_overlay_context(
            hedge_readiness=None,
            currency_exposure=None,
            hedge_policy=None,
            eligible_hedge_instruments=None,
            fx_forward_curve=None,
        )
        is None
    )
