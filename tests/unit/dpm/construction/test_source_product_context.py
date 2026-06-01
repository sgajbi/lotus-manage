from datetime import date

from src.api.services.construction_source_product_context import (
    external_order_execution_acknowledgement_context,
    external_treasury_currency_overlay_context,
    source_status_to_method_status,
)
from src.core.construction.vocabulary import ConstructionMethodStatus
from src.core.dpm_source_context import (
    DpmCoreExternalOrderExecutionAcknowledgementResponse,
    DpmCoreExternalOrderExecutionAcknowledgementSupportability,
    DpmCoreExternalHedgeExecutionReadinessResponse,
    DpmCoreExternalHedgeExecutionReadinessSupportability,
)


def _acknowledgement_response() -> DpmCoreExternalOrderExecutionAcknowledgementResponse:
    return DpmCoreExternalOrderExecutionAcknowledgementResponse(
        product_name="ExternalOrderExecutionAcknowledgement",
        product_version="v1",
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        client_id="client-1",
        mandate_id="mandate-1",
        as_of_date=date(2026, 6, 1),
        supportability=DpmCoreExternalOrderExecutionAcknowledgementSupportability(
            state="UNAVAILABLE",
            reason="EXTERNAL_OMS_SOURCE_NOT_INGESTED",
            acknowledgement_count=0,
            missing_data_families=["external_oms_acknowledgement"],
            blocked_capabilities=["execution", "fill", "settlement"],
        ),
        lineage={"source_batch_fingerprint": "core-ack-fingerprint"},
        acknowledgements=[],
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


def test_external_order_acknowledgement_context_is_fail_closed_source_evidence() -> None:
    context = external_order_execution_acknowledgement_context(_acknowledgement_response())

    assert context is not None
    assert context.supportability_status == ConstructionMethodStatus.BLOCKED
    assert context.source_system == "lotus-core"
    assert context.source_product_name == "ExternalOrderExecutionAcknowledgement"
    assert context.source_id == "core-ack-fingerprint"
    assert context.acknowledgement_count == 0
    assert context.blocked_capabilities == ["execution", "fill", "settlement"]
    assert context.reason_codes == [
        "EXTERNAL_OMS_SOURCE_NOT_INGESTED",
        "EXTERNAL_ORDER_EXECUTION_ACKNOWLEDGEMENT_FAIL_CLOSED",
    ]


def test_external_order_acknowledgement_context_absent_without_source_response() -> None:
    assert external_order_execution_acknowledgement_context(None) is None


def test_source_status_to_method_status_maps_non_ready_fail_closed() -> None:
    assert source_status_to_method_status("READY") == ConstructionMethodStatus.READY
    assert source_status_to_method_status("DEGRADED") == ConstructionMethodStatus.DEGRADED
    assert source_status_to_method_status("UNAVAILABLE") == ConstructionMethodStatus.BLOCKED
    assert source_status_to_method_status("INCOMPLETE") == ConstructionMethodStatus.BLOCKED
