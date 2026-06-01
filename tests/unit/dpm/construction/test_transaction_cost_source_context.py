from src.api.services.construction_transaction_cost_source_context import (
    transaction_cost_context_from_curve,
)
from src.core.construction.vocabulary import ConstructionMethodStatus
from tests.unit.dpm.construction.source_product_context_fixtures import (
    transaction_cost_curve_response,
)


def test_transaction_cost_context_preserves_core_curve_lineage_and_bounds_samples() -> None:
    context = transaction_cost_context_from_curve(transaction_cost_curve_response())

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
