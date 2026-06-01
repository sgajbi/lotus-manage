from datetime import date
from decimal import Decimal

from src.api.services.construction_source_product_context import (
    external_order_execution_acknowledgement_context,
    external_treasury_currency_overlay_context,
    liquidity_cashflow_projection_context,
    source_status_to_method_status,
    transaction_cost_context_from_curve,
)
from src.core.construction.vocabulary import ConstructionMethodStatus
from src.core.dpm_source_context import (
    DpmCoreExternalOrderExecutionAcknowledgementResponse,
    DpmCoreExternalOrderExecutionAcknowledgementSupportability,
    DpmCoreExternalHedgeExecutionReadinessResponse,
    DpmCoreExternalHedgeExecutionReadinessSupportability,
    DpmCoreIntegrationWindow,
    DpmCorePortfolioCashflowProjectionResponse,
    DpmCoreTransactionCostCurvePageMetadata,
    DpmCoreTransactionCostCurvePoint,
    DpmCoreTransactionCostCurveResponse,
    DpmCoreTransactionCostCurveSupportability,
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


def _transaction_cost_curve() -> DpmCoreTransactionCostCurveResponse:
    return DpmCoreTransactionCostCurveResponse(
        product_name="TransactionCostCurve",
        product_version="v1",
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        as_of_date=date(2026, 6, 1),
        window=DpmCoreIntegrationWindow(
            start_date=date(2026, 5, 1),
            end_date=date(2026, 6, 1),
        ),
        curve_points=[
            DpmCoreTransactionCostCurvePoint(
                portfolio_id="PB_SG_GLOBAL_BAL_001",
                security_id="EQ_A",
                transaction_type="BUY",
                currency="USD",
                observation_count=3,
                total_notional=Decimal("1000"),
                total_cost=Decimal("2"),
                average_cost_bps=Decimal("20"),
                min_cost_bps=Decimal("15"),
                max_cost_bps=Decimal("25"),
                first_observed_date=date(2026, 5, 1),
                last_observed_date=date(2026, 6, 1),
                sample_transaction_ids=["tx1", "tx2", "tx3", "tx4", "tx5", "tx6"],
            )
        ],
        page=DpmCoreTransactionCostCurvePageMetadata(
            page_size=50,
            sort_key="security_id",
            returned_component_count=1,
            request_scope_fingerprint="curve-page-fingerprint",
        ),
        supportability=DpmCoreTransactionCostCurveSupportability(
            state="DEGRADED",
            reason="TRANSACTION_COST_CURVE_PARTIAL",
            requested_security_count=2,
            returned_curve_point_count=1,
            missing_security_ids=["EQ_B"],
        ),
        lineage={"source_batch_fingerprint": "curve-lineage"},
    )


def _cashflow_projection() -> DpmCorePortfolioCashflowProjectionResponse:
    return DpmCorePortfolioCashflowProjectionResponse(
        product_name="PortfolioCashflowProjection",
        product_version="v1",
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        as_of_date=date(2026, 6, 1),
        range_start_date=date(2026, 6, 1),
        range_end_date=date(2026, 6, 30),
        include_projected=True,
        portfolio_currency="USD",
        points=[],
        total_net_cashflow=Decimal("1250.50"),
        projection_days=30,
        data_quality_status="DEGRADED",
        source_batch_fingerprint=None,
        lineage={"source_batch_fingerprint": "cashflow-lineage"},
    )


def test_liquidity_cashflow_projection_context_preserves_source_lineage_and_status() -> None:
    context = liquidity_cashflow_projection_context(_cashflow_projection())

    assert context.source_system == "lotus-core"
    assert context.source_product_name == "PortfolioCashflowProjection"
    assert context.source_batch_fingerprint == "cashflow-lineage"
    assert context.total_net_cashflow.amount == Decimal("1250.50")
    assert context.total_net_cashflow.currency == "USD"
    assert context.include_projected is True
    assert context.data_quality_status == ConstructionMethodStatus.DEGRADED
    assert context.reason_codes == ["CORE_CASHFLOW_PROJECTION_READY"]


def test_transaction_cost_context_preserves_core_curve_lineage_and_bounds_samples() -> None:
    context = transaction_cost_context_from_curve(_transaction_cost_curve())

    assert context.supportability_status == ConstructionMethodStatus.DEGRADED
    assert context.source_system == "lotus-core"
    assert context.source_product_name == "TransactionCostCurve"
    assert context.source_id == "curve-lineage"
    assert context.returned_curve_point_count == 1
    assert context.missing_security_ids == ["EQ_B"]
    assert context.reason_codes == ["TRANSACTION_COST_CURVE_PARTIAL"]
    assert len(context.curve_points) == 1
    assert context.curve_points[0].sample_transaction_ids == [
        "tx1",
        "tx2",
        "tx3",
        "tx4",
        "tx5",
    ]


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
