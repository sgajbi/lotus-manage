from datetime import date
from decimal import Decimal

from src.api.services.construction_transaction_cost_source_context import (
    transaction_cost_context_from_curve,
)
from src.core.construction.vocabulary import ConstructionMethodStatus
from src.core.dpm_source_context import (
    DpmCoreIntegrationWindow,
    DpmCoreTransactionCostCurvePageMetadata,
    DpmCoreTransactionCostCurvePoint,
    DpmCoreTransactionCostCurveResponse,
    DpmCoreTransactionCostCurveSupportability,
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
