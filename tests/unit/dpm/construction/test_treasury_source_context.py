from datetime import date

from src.api.services.construction_treasury_source_context import (
    external_treasury_currency_overlay_context,
)
from src.core.construction.vocabulary import ConstructionMethodStatus
from src.core.dpm_source_context import (
    DpmCoreExternalCurrencyExposureResponse,
    DpmCoreExternalCurrencyExposureSupportability,
    DpmCoreExternalEligibleHedgeInstrumentResponse,
    DpmCoreExternalEligibleHedgeInstrumentSupportability,
    DpmCoreExternalFXForwardCurveResponse,
    DpmCoreExternalFXForwardCurveSupportability,
    DpmCoreExternalHedgeExecutionReadinessResponse,
    DpmCoreExternalHedgeExecutionReadinessSupportability,
    DpmCoreExternalHedgePolicyResponse,
    DpmCoreExternalHedgePolicySupportability,
)


def _hedge_readiness_response() -> DpmCoreExternalHedgeExecutionReadinessResponse:
    return DpmCoreExternalHedgeExecutionReadinessResponse(
        product_name="ExternalHedgeExecutionReadiness",
        product_version="v1",
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        client_id="client-1",
        mandate_id="mandate-1",
        as_of_date=date(2026, 6, 1),
        reporting_currency="USD",
        exposure_currencies=["EUR", "GBP"],
        readiness_checks=[{"check": "source_ingestion", "status": "missing"}],
        supportability=DpmCoreExternalHedgeExecutionReadinessSupportability(
            state="UNAVAILABLE",
            reason="EXTERNAL_TREASURY_SOURCE_NOT_INGESTED",
            missing_data_families=["external_treasury_hedge_readiness"],
            blocked_capabilities=["treasury", "oms", "execution"],
        ),
        lineage={"source_batch_fingerprint": "core-hedge-readiness"},
    )


def _currency_exposure_response() -> DpmCoreExternalCurrencyExposureResponse:
    return DpmCoreExternalCurrencyExposureResponse(
        product_name="ExternalCurrencyExposure",
        product_version="v1",
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        client_id="client-1",
        mandate_id="mandate-1",
        as_of_date=date(2026, 6, 1),
        reporting_currency="USD",
        exposure_currencies=["EUR", "JPY"],
        exposures=[{"currency": "EUR", "net_exposure": "125000"}],
        supportability=DpmCoreExternalCurrencyExposureSupportability(
            state="UNAVAILABLE",
            reason="EXTERNAL_TREASURY_SOURCE_NOT_INGESTED",
            exposure_count=1,
            missing_data_families=["external_currency_exposure"],
            blocked_capabilities=["fx", "treasury"],
        ),
        lineage={"source_batch_fingerprint": "core-currency-exposure"},
    )


def _hedge_policy_response() -> DpmCoreExternalHedgePolicyResponse:
    return DpmCoreExternalHedgePolicyResponse(
        product_name="ExternalHedgePolicy",
        product_version="v1",
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        client_id="client-1",
        mandate_id="mandate-1",
        as_of_date=date(2026, 6, 1),
        reporting_currency="USD",
        exposure_currencies=["EUR"],
        policy_rules=[{"currency": "EUR", "hedge_ratio": "0.50"}],
        supportability=DpmCoreExternalHedgePolicySupportability(
            state="UNAVAILABLE",
            reason="EXTERNAL_TREASURY_SOURCE_NOT_INGESTED",
            policy_rule_count=1,
            missing_data_families=["external_hedge_policy"],
            blocked_capabilities=["hedge-policy", "treasury"],
        ),
        lineage={"source_batch_fingerprint": "core-hedge-policy"},
    )


def _eligible_hedge_instruments_response() -> DpmCoreExternalEligibleHedgeInstrumentResponse:
    return DpmCoreExternalEligibleHedgeInstrumentResponse(
        product_name="ExternalEligibleHedgeInstrument",
        product_version="v1",
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        client_id="client-1",
        mandate_id="mandate-1",
        as_of_date=date(2026, 6, 1),
        reporting_currency="USD",
        exposure_currencies=["EUR"],
        instrument_types=["FX_FORWARD"],
        eligible_instruments=[{"instrument_id": "FXFWD_EURUSD_1M", "currency": "EUR"}],
        supportability=DpmCoreExternalEligibleHedgeInstrumentSupportability(
            state="UNAVAILABLE",
            reason="EXTERNAL_TREASURY_SOURCE_NOT_INGESTED",
            instrument_count=1,
            missing_data_families=["external_eligible_hedge_instruments"],
            blocked_capabilities=["eligible-instrument", "suitability"],
        ),
        lineage={"source_batch_fingerprint": "core-eligible-hedges"},
    )


def _fx_forward_curve_response() -> DpmCoreExternalFXForwardCurveResponse:
    return DpmCoreExternalFXForwardCurveResponse(
        product_name="ExternalFXForwardCurve",
        product_version="v1",
        portfolio_id=None,
        client_id=None,
        mandate_id=None,
        as_of_date=date(2026, 6, 1),
        reporting_currency="USD",
        exposure_currencies=["EUR/USD"],
        curve_points=[{"tenor": "1M", "forward_points": "12.5"}],
        supportability=DpmCoreExternalFXForwardCurveSupportability(
            state="UNAVAILABLE",
            reason="EXTERNAL_TREASURY_SOURCE_NOT_INGESTED",
            curve_point_count=1,
            missing_data_families=["external_fx_forward_curve"],
            blocked_capabilities=["forward-pricing", "treasury"],
        ),
        lineage={"source_batch_fingerprint": "core-fx-forward-curve"},
    )


def test_external_treasury_currency_overlay_context_preserves_fail_closed_readiness() -> None:
    context = external_treasury_currency_overlay_context(
        hedge_readiness=_hedge_readiness_response(),
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
        currency_exposure=_currency_exposure_response(),
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
        hedge_readiness=_hedge_readiness_response(),
        currency_exposure=_currency_exposure_response(),
        hedge_policy=_hedge_policy_response(),
        eligible_hedge_instruments=_eligible_hedge_instruments_response(),
        fx_forward_curve=_fx_forward_curve_response(),
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
