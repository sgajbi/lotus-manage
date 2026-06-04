from src.api.services import construction_transaction_cost_source_context
from src.api.services.construction_transaction_cost_source_context import (
    transaction_cost_context_from_curve,
    transaction_cost_curve_points,
    transaction_cost_sample_transaction_ids,
)
from src.core.construction.vocabulary import ConstructionMethodStatus
from tests.unit.dpm.construction.source_product_context_fixtures import (
    transaction_cost_curve_response,
)


def test_transaction_cost_source_context_exports_only_curve_mapper() -> None:
    assert construction_transaction_cost_source_context.__all__ == [
        "transaction_cost_context_from_curve",
        "transaction_cost_curve_points",
        "transaction_cost_sample_transaction_ids",
    ]


def test_transaction_cost_sample_transaction_ids_bounds_source_evidence() -> None:
    point = (
        transaction_cost_curve_response()
        .curve_points[0]
        .model_copy(update={"sample_transaction_ids": ["tx1", "tx2", "tx3", "tx4", "tx5", "tx6"]})
    )

    assert transaction_cost_sample_transaction_ids(point) == [
        "tx1",
        "tx2",
        "tx3",
        "tx4",
        "tx5",
    ]


def test_transaction_cost_curve_points_bounds_source_evidence() -> None:
    curve = transaction_cost_curve_response()
    curve = curve.model_copy(update={"curve_points": curve.curve_points * 12})

    assert len(transaction_cost_curve_points(curve)) == 10


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


def test_transaction_cost_context_falls_back_to_page_fingerprint_source_id() -> None:
    curve = transaction_cost_curve_response().model_copy(
        update={
            "source_batch_fingerprint": None,
            "lineage": {},
        }
    )

    context = transaction_cost_context_from_curve(curve)

    assert context.source_id == "curve-page-fingerprint"
