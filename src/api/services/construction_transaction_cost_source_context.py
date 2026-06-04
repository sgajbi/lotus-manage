from src.api.services.construction_source_product_status import source_status_to_method_status
from src.api.services.construction_source_identity import source_product_identity
from src.core.construction.models import (
    AuthoritativeTransactionCostContext,
    AuthoritativeTransactionCostPoint,
)
from src.core.dpm_source_context import (
    DpmCoreTransactionCostCurvePoint,
    DpmCoreTransactionCostCurveResponse,
)

_MAX_TRANSACTION_COST_CURVE_POINTS = 10
_MAX_TRANSACTION_COST_SAMPLE_IDS = 5


def transaction_cost_sample_transaction_ids(
    point: DpmCoreTransactionCostCurvePoint,
) -> list[str]:
    return point.sample_transaction_ids[:_MAX_TRANSACTION_COST_SAMPLE_IDS]


def transaction_cost_curve_points(
    curve: DpmCoreTransactionCostCurveResponse,
) -> list[DpmCoreTransactionCostCurvePoint]:
    return curve.curve_points[:_MAX_TRANSACTION_COST_CURVE_POINTS]


def _transaction_cost_point(
    point: DpmCoreTransactionCostCurvePoint,
) -> AuthoritativeTransactionCostPoint:
    return AuthoritativeTransactionCostPoint(
        security_id=point.security_id,
        transaction_type=point.transaction_type,
        currency=point.currency,
        observation_count=point.observation_count,
        total_notional=point.total_notional,
        total_cost=point.total_cost,
        average_cost_bps=point.average_cost_bps,
        min_cost_bps=point.min_cost_bps,
        max_cost_bps=point.max_cost_bps,
        first_observed_date=point.first_observed_date,
        last_observed_date=point.last_observed_date,
        sample_transaction_ids=transaction_cost_sample_transaction_ids(point),
    )


def transaction_cost_context_from_curve(
    curve: DpmCoreTransactionCostCurveResponse,
) -> AuthoritativeTransactionCostContext:
    identity = source_product_identity(
        curve,
        fallback_source_id=curve.page.request_scope_fingerprint,
    )
    return AuthoritativeTransactionCostContext(
        supportability_status=source_status_to_method_status(curve.supportability.state),
        source_system=identity.source_system,
        source_product_name=identity.source_product_name,
        source_product_version=identity.source_product_version,
        source_id=identity.source_id,
        content_hash=identity.content_hash,
        as_of_date=curve.as_of_date,
        window_start_date=curve.window.start_date,
        window_end_date=curve.window.end_date,
        returned_curve_point_count=curve.supportability.returned_curve_point_count,
        missing_security_ids=curve.supportability.missing_security_ids,
        curve_points=[
            _transaction_cost_point(point) for point in transaction_cost_curve_points(curve)
        ],
        reason_codes=[curve.supportability.reason],
    )


__all__ = [
    "transaction_cost_context_from_curve",
    "transaction_cost_curve_points",
    "transaction_cost_sample_transaction_ids",
]
