from decimal import Decimal

from src.api.services import construction_transaction_cost_source_context
from src.api.services.construction_transaction_cost_source_context import (
    transaction_cost_context_from_curve,
    transaction_cost_curve_points,
    transaction_cost_point,
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
        "transaction_cost_point",
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


def test_transaction_cost_point_preserves_curve_point_payload_and_bounds_samples() -> None:
    point = transaction_cost_point(transaction_cost_curve_response().curve_points[0])

    assert point.security_id == "EQ_A"
    assert point.transaction_type == "BUY"
    assert point.currency == "USD"
    assert point.observation_count == 3
    assert point.total_notional == 1000
    assert point.total_cost == 2
    assert point.average_cost_bps == 20
    assert point.min_cost_bps == 15
    assert point.max_cost_bps == 25
    assert point.sample_transaction_ids == ["tx1", "tx2", "tx3", "tx4", "tx5"]


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


def test_transaction_cost_context_degrades_duplicate_source_keys_before_bounded_projection() -> (
    None
):
    curve = transaction_cost_curve_response()
    first = curve.curve_points[0]
    unique = [first.model_copy(update={"security_id": f"EQ_{index}"}) for index in range(1, 10)]
    duplicate_after_projection_limit = first.model_copy(update={"average_cost_bps": Decimal("100")})
    curve = curve.model_copy(
        update={
            "curve_points": [first, *unique, duplicate_after_projection_limit],
            "page": curve.page.model_copy(update={"returned_component_count": 11}),
            "supportability": curve.supportability.model_copy(
                update={
                    "state": "READY",
                    "reason": "TRANSACTION_COST_CURVE_READY",
                    "returned_curve_point_count": 11,
                }
            ),
        }
    )

    context = transaction_cost_context_from_curve(curve)

    assert context.supportability_status == ConstructionMethodStatus.DEGRADED
    assert context.curve_points == []
    assert context.returned_curve_point_count == 11
    assert context.source_id == "curve-lineage"
    assert context.reason_codes == [
        "TRANSACTION_COST_CURVE_READY",
        "TRANSACTION_COST_CURVE_DUPLICATE_POINT",
    ]
