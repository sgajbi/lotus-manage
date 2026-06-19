from datetime import datetime, timezone

from src.core.rebalance_runs.models import DpmRunRecord
from src.core.rebalance_runs.serializers import (
    to_run_list_item_response,
    to_run_list_response,
)


def _run_record(
    *,
    rebalance_run_id: str,
    correlation_id: str,
    idempotency_key: str | None,
    status: str,
) -> DpmRunRecord:
    return DpmRunRecord(
        rebalance_run_id=rebalance_run_id,
        correlation_id=correlation_id,
        request_hash=f"sha256:{rebalance_run_id}",
        idempotency_key=idempotency_key,
        portfolio_id="pf_run_serializer",
        created_at=datetime(2026, 2, 20, 12, 0, tzinfo=timezone.utc),
        result_json={"status": status},
    )


def test_run_list_item_response_preserves_persisted_run_fields():
    run = _run_record(
        rebalance_run_id="rr_run_serializer_1",
        correlation_id="corr_run_serializer_1",
        idempotency_key=None,
        status="READY",
    )

    item = to_run_list_item_response(run)

    assert item.rebalance_run_id == "rr_run_serializer_1"
    assert item.correlation_id == "corr_run_serializer_1"
    assert item.request_hash == "sha256:rr_run_serializer_1"
    assert item.idempotency_key is None
    assert item.portfolio_id == "pf_run_serializer"
    assert item.status == "READY"
    assert item.created_at == "2026-02-20T12:00:00+00:00"


def test_run_list_response_preserves_order_and_cursor():
    first = _run_record(
        rebalance_run_id="rr_run_serializer_1",
        correlation_id="corr_run_serializer_1",
        idempotency_key="idem_run_serializer_1",
        status="PENDING_REVIEW",
    )
    second = _run_record(
        rebalance_run_id="rr_run_serializer_2",
        correlation_id="corr_run_serializer_2",
        idempotency_key=None,
        status="READY",
    )

    response = to_run_list_response(runs=[first, second], next_cursor="rr_run_serializer_2")

    assert [item.rebalance_run_id for item in response.items] == [
        "rr_run_serializer_1",
        "rr_run_serializer_2",
    ]
    assert [item.status for item in response.items] == ["PENDING_REVIEW", "READY"]
    assert response.items[0].idempotency_key == "idem_run_serializer_1"
    assert response.items[1].idempotency_key is None
    assert response.next_cursor == "rr_run_serializer_2"
