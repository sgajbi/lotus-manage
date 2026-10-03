"""Synthetic source-ready wave fixture; not upstream authority or capacity proof."""

from datetime import UTC, datetime

from src.api.services import wave_simulation_operations
from src.core.construction.vocabulary import ConstructionMethod
from src.core.waves.models import (
    DpmRebalanceWave,
    DpmRebalanceWaveItem,
    DpmWaveAggregateMetrics,
    DpmWaveTrigger,
)
from src.core.waves.simulation_operations import DpmWaveSimulationOperation
from src.infrastructure.waves.postgres import PostgresDpmWaveRepository


def source_ready_wave(*, tenant_id: str, wave_id: str, item_count: int = 4) -> DpmRebalanceWave:
    items = [
        DpmRebalanceWaveItem(
            wave_item_id=f"{wave_id}-item-{index}",
            portfolio_id=f"portfolio-{index}",
            state="SOURCE_READY",
        )
        for index in range(item_count)
    ]
    return DpmRebalanceWave(
        wave_id=wave_id,
        state="SOURCE_CHECKED",
        trigger=DpmWaveTrigger(
            trigger_type="EXPLICIT_PORTFOLIO_LIST",
            trigger_id=f"trigger-{wave_id}",
            rationale="Prove PostgreSQL worker ownership.",
        ),
        as_of_date="2026-10-01",
        created_at=datetime(2026, 10, 1, tzinfo=UTC),
        created_by="integration-test",
        correlation_id=f"corr-wave-{wave_id}",
        tenant_id=tenant_id,
        items=items,
        aggregate_metrics=DpmWaveAggregateMetrics(
            item_count=item_count,
            state_counts={"SOURCE_READY": item_count},
            ready_item_count=item_count,
            blocked_item_count=0,
            review_required_item_count=0,
            source_degraded_item_count=0,
        ),
    )


def financial_request(portfolio_id: str) -> dict[str, object]:
    return {
        "portfolio_snapshot": {
            "portfolio_id": portfolio_id,
            "base_currency": "SGD",
            "positions": [{"instrument_id": "EQ_1", "quantity": "100"}],
            "cash_balances": [{"currency": "SGD", "amount": "5000"}],
        },
        "market_data_snapshot": {
            "prices": [{"instrument_id": "EQ_1", "price": "100", "currency": "SGD"}],
            "fx_rates": [],
        },
        "model_portfolio": {"targets": [{"instrument_id": "EQ_1", "weight": "0.80"}]},
        "shelf_entries": [{"instrument_id": "EQ_1", "status": "APPROVED"}],
        "options": {"target_method": "HEURISTIC"},
    }


def admit_financial_operation(
    *,
    repository: PostgresDpmWaveRepository,
    tenant_id: str,
    wave_id: str,
    item_count: int,
    max_concurrency: int = 4,
    max_attempts: int = 3,
) -> DpmWaveSimulationOperation:
    wave = source_ready_wave(tenant_id=tenant_id, wave_id=wave_id, item_count=item_count)
    repository.save_wave(wave=wave, idempotency_key=None, request_hash=None, tenant_id=tenant_id)
    operation, replayed = wave_simulation_operations.admit_wave_simulation_operation(
        wave_id=wave_id,
        tenant_id=tenant_id,
        actor_id="integration-test",
        correlation_id=f"corr-{wave_id}-async",
        idempotency_key=f"idem-{wave_id}",
        item_payloads=[
            {
                "wave_item_id": item.wave_item_id,
                "stateless_input": financial_request(item.portfolio_id),
            }
            for item in wave.items
        ],
        methods=[ConstructionMethod.HEURISTIC_EXPLAINABLE],
        max_concurrency=max_concurrency,
        max_attempts=max_attempts,
        repository=repository,
    )
    assert replayed is False
    return operation
