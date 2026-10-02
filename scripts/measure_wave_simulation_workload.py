"""Measure the bounded asynchronous wave-simulation operating envelope.

This is a controlled workload probe, not a production capacity certification. It requires a
caller-supplied PostgreSQL DSN and emits no credentials or portfolio payloads.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import sys
import time
import tracemalloc
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Lock

import psycopg

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.api.request_models import RebalanceRequest  # noqa: E402
from src.api.services import wave_simulation_operations  # noqa: E402
from src.api.services.wave_simulation_item import (  # noqa: E402
    DpmWaveSimulationInput,
    simulate_item,
)
from src.core.construction.vocabulary import ConstructionMethod  # noqa: E402
from src.core.rebalance_runs.service import DpmRunSupportService  # noqa: E402
from src.core.waves import (  # noqa: E402
    DpmRebalanceWave,
    DpmRebalanceWaveItem,
    DpmWaveAggregateMetrics,
    DpmWaveTrigger,
)
from src.infrastructure.construction import PostgresConstructionRepository  # noqa: E402
from src.infrastructure.rebalance_runs import InMemoryDpmRunRepository  # noqa: E402
from src.infrastructure.waves import PostgresDpmWaveRepository  # noqa: E402


def _request(portfolio_id: str) -> dict[str, object]:
    return {
        "portfolio_snapshot": {
            "snapshot_id": "synthetic-holdings-v1",
            "portfolio_id": portfolio_id,
            "base_currency": "SGD",
            "positions": [
                {
                    "instrument_id": "EQ_SGD",
                    "quantity": "100",
                    "lots": [
                        {
                            "lot_id": "LOT_1",
                            "quantity": "60",
                            "unit_cost": {"amount": "80", "currency": "SGD"},
                            "purchase_date": "2024-01-15",
                        },
                        {
                            "lot_id": "LOT_2",
                            "quantity": "40",
                            "unit_cost": {"amount": "110", "currency": "SGD"},
                            "purchase_date": "2025-06-30",
                        },
                    ],
                },
                {"instrument_id": "BOND_EUR", "quantity": "20"},
            ],
            "cash_balances": [
                {"currency": "SGD", "amount": "5000", "settled": "4000", "pending": "1000"},
                {"currency": "EUR", "amount": "1000", "settled": "800", "pending": "200"},
            ],
        },
        "market_data_snapshot": {
            "snapshot_id": "synthetic-market-v1",
            "prices": [
                {"instrument_id": "EQ_SGD", "price": "100", "currency": "SGD"},
                {"instrument_id": "BOND_EUR", "price": "50", "currency": "EUR"},
                {"instrument_id": "EQ_RESTRICTED", "price": "25", "currency": "SGD"},
            ],
            "fx_rates": [{"pair": "EUR/SGD", "rate": "1.45"}],
        },
        "model_portfolio": {
            "targets": [
                {"instrument_id": "EQ_SGD", "weight": "0.55"},
                {"instrument_id": "BOND_EUR", "weight": "0.30"},
                {"instrument_id": "EQ_RESTRICTED", "weight": "0.10"},
            ]
        },
        "shelf_entries": [
            {
                "instrument_id": "EQ_SGD",
                "status": "APPROVED",
                "asset_class": "EQUITY",
                "issuer_id": "ISSUER_EQ",
                "liquidity_tier": "L1",
                "settlement_days": 2,
                "min_notional": {"amount": "100", "currency": "SGD"},
                "attributes": {"sector": "FINANCIALS"},
            },
            {
                "instrument_id": "BOND_EUR",
                "status": "APPROVED",
                "asset_class": "FIXED_INCOME",
                "issuer_id": "ISSUER_BOND",
                "liquidity_tier": "L2",
                "settlement_days": 2,
                "min_notional": {"amount": "100", "currency": "EUR"},
                "attributes": {"sector": "SOVEREIGN"},
            },
            {
                "instrument_id": "EQ_RESTRICTED",
                "status": "RESTRICTED",
                "asset_class": "EQUITY",
                "issuer_id": "ISSUER_RESTRICTED",
                "liquidity_tier": "L2",
                "settlement_days": 2,
                "attributes": {"sector": "TECH"},
            },
        ],
        "options": {
            "target_method": "HEURISTIC",
            "cash_band_min_weight": "0.03",
            "cash_band_max_weight": "0.10",
            "single_position_max_weight": "0.60",
            "min_trade_notional": {"amount": "100", "currency": "SGD"},
            "allow_restricted": False,
            "suppress_dust_trades": True,
            "max_turnover_pct": "0.25",
            "enable_tax_awareness": True,
            "max_realized_capital_gains": "2000",
            "enable_settlement_awareness": True,
            "min_cash_buffer_pct": "0.03",
            "settlement_horizon_days": 5,
            "fx_settlement_days": 2,
            "max_overdraft_by_ccy": {"SGD": "0", "EUR": "0"},
            "group_constraints": {"sector:TECH": {"max_weight": "0.05"}},
        },
    }


def _wave(*, tenant_id: str, wave_id: str, item_count: int) -> DpmRebalanceWave:
    items = [
        DpmRebalanceWaveItem(
            wave_item_id=f"{wave_id}-item-{index:03d}",
            portfolio_id=f"SYNTHETIC_DPM_{index:03d}",
            mandate_id=f"SYNTHETIC_MANDATE_{index:03d}",
            model_portfolio_id="SYNTHETIC_BALANCED_MODEL_V1",
            state="SOURCE_READY",
            reason_codes=["SYNTHETIC_SOURCE_READY"],
        )
        for index in range(item_count)
    ]
    return DpmRebalanceWave(
        wave_id=wave_id,
        state="SOURCE_CHECKED",
        trigger=DpmWaveTrigger(
            trigger_type="EXPLICIT_PORTFOLIO_LIST",
            trigger_id=f"synthetic-load-{wave_id}",
            rationale="Controlled asynchronous wave-simulation operating-envelope measurement.",
        ),
        as_of_date="2026-10-01",
        created_by="wave-load-probe",
        correlation_id=f"corr-{wave_id}",
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


def _database_size(dsn: str) -> int:
    with psycopg.connect(dsn) as connection:
        row = connection.execute("SELECT pg_database_size(current_database())").fetchone()
    return 0 if row is None else int(row[0])


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int((len(ordered) * percentile) + 0.999999) - 1))
    return ordered[index]


def run_probe(
    *,
    dsn: str,
    item_count: int,
    concurrency: int,
    interrupt_count: int,
) -> dict[str, object]:
    suffix = uuid.uuid4().hex[:12]
    tenant_id = f"synthetic-load-{suffix}"
    wave_id = f"dwv-synthetic-{suffix}"
    repository = PostgresDpmWaveRepository(dsn=dsn)
    construction_repository = PostgresConstructionRepository(dsn=dsn)
    wave = _wave(tenant_id=tenant_id, wave_id=wave_id, item_count=item_count)
    repository.save_wave(wave=wave, idempotency_key=None, request_hash=None, tenant_id=tenant_id)

    database_bytes_before = _database_size(dsn)
    cpu_started = time.process_time()
    wall_started = time.perf_counter()
    tracemalloc.start()
    operation, replayed = wave_simulation_operations.admit_wave_simulation_operation(
        wave_id=wave_id,
        tenant_id=tenant_id,
        actor_id="wave-load-probe",
        correlation_id=f"corr-{wave_id}-operation",
        idempotency_key=f"idem-{wave_id}",
        item_payloads=[
            {
                "wave_item_id": item.wave_item_id,
                "stateless_input": _request(item.portfolio_id),
            }
            for item in wave.items
        ],
        methods=[ConstructionMethod.HEURISTIC_EXPLAINABLE],
        max_concurrency=concurrency,
        max_attempts=3,
        repository=repository,
    )
    if replayed:
        raise RuntimeError("A unique load-probe operation unexpectedly replayed.")

    interrupted_at = datetime(2026, 1, 1, tzinfo=UTC)
    interrupted_claims = repository.claim_simulation_items(
        tenant_id=tenant_id,
        operation_id=operation.operation_id,
        worker_id="interrupted-worker",
        limit=min(interrupt_count, concurrency),
        claimed_at=interrupted_at,
        lease_expires_at=interrupted_at + timedelta(seconds=5),
    )
    admitted_wave = repository.get_wave(wave_id=wave_id, tenant_id=tenant_id)
    if admitted_wave is None:
        raise RuntimeError("The admitted wave could not be reloaded.")
    by_item_id = {item.wave_item_id: item for item in admitted_wave.items}
    interrupted_run_service = DpmRunSupportService(repository=InMemoryDpmRunRepository())
    for claim in interrupted_claims:
        simulate_item(
            item=by_item_id[claim.wave_item_id],
            tenant_id=tenant_id,
            correlation_id=f"{operation.operation_id}:{claim.wave_item_id}",
            item_inputs={
                claim.wave_item_id: DpmWaveSimulationInput(
                    stateless_input=RebalanceRequest.model_validate(
                        claim.input_payload["stateless_input"]
                    )
                )
            },
            methods=[ConstructionMethod.HEURISTIC_EXPLAINABLE],
            construction_repository=construction_repository,
            run_service=interrupted_run_service,
            risk_authority_client=None,
            construction_idempotency_key=(
                f"wave-operation:{operation.operation_id}:{claim.wave_item_id}:simulate"
            ),
        )

    restart_started = time.perf_counter()
    completion_latencies: list[float] = []
    latency_lock = Lock()

    def drain(worker_index: int) -> int:
        worker_repository = PostgresDpmWaveRepository(dsn=dsn)
        worker_construction_repository = PostgresConstructionRepository(dsn=dsn)
        run_service = DpmRunSupportService(repository=InMemoryDpmRunRepository())
        worker_completed = 0
        while True:
            current = worker_repository.get_simulation_operation(
                tenant_id=tenant_id, operation_id=operation.operation_id
            )
            if current is None:
                raise RuntimeError("The worker could not reload the operation.")
            if current.status in {"SUCCEEDED", "FAILED", "CANCELLED"}:
                return worker_completed
            if current.status == "PARTIALLY_COMPLETED":
                counts = worker_repository.simulation_item_counts(
                    tenant_id=tenant_id, operation_id=operation.operation_id
                )
                if counts.get("PENDING", 0) == 0 and counts.get("RUNNING", 0) == 0:
                    # Explicit retry is not part of this probe. Report failed dispositions below.
                    return worker_completed
            _, claimed, completed, _ = wave_simulation_operations.execute_wave_simulation_work(
                tenant_id=tenant_id,
                operation_id=operation.operation_id,
                worker_id=f"replacement-worker-{worker_index}",
                max_items=1,
                lease_seconds=60,
                repository=worker_repository,
                construction_repository=worker_construction_repository,
                run_service=run_service,
                risk_authority_client=None,
            )
            if completed:
                with latency_lock:
                    completion_latencies.extend([time.perf_counter() - restart_started] * completed)
                worker_completed += completed
            if claimed == 0:
                time.sleep(0.005)

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        completed_per_worker = list(executor.map(drain, range(concurrency)))

    restart_drain_seconds = time.perf_counter() - restart_started
    current_heap_bytes, peak_heap_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    wall_seconds = time.perf_counter() - wall_started
    cpu_seconds = time.process_time() - cpu_started
    database_bytes_after = _database_size(dsn)
    results = repository.list_simulation_items(
        tenant_id=tenant_id,
        operation_id=operation.operation_id,
        limit=max(item_count, 1),
        offset=0,
    )
    status_counts: dict[str, int] = {}
    error_counts: dict[str, int] = {}
    alternative_ids: list[str] = []
    for item in results.items:
        status_counts[item.status] = status_counts.get(item.status, 0) + 1
        if item.error_code:
            error_counts[item.error_code] = error_counts.get(item.error_code, 0) + 1
        if item.result_item and item.result_item.alternative_set_id:
            alternative_ids.append(item.result_item.alternative_set_id)
    if len(results.items) != item_count or status_counts.get("SUCCEEDED") != item_count:
        raise RuntimeError(f"Load probe did not complete successfully: {status_counts}")

    return {
        "schema_version": "wave-simulation-load-probe.v1",
        "measured_at": datetime.now(UTC).isoformat(),
        "claim": "controlled_local_measurement_not_production_capacity_certification",
        "workload": {
            "item_count": item_count,
            "configured_concurrency": concurrency,
            "interrupted_after_artifact_commit_count": len(interrupted_claims),
            "methods": [ConstructionMethod.HEURISTIC_EXPLAINABLE.value],
            "input_profile": (
                "multi-currency holdings, tax lots, restricted instrument, cash bands, "
                "minimum notionals, turnover cap, settlement ladder and group constraint"
            ),
        },
        "results": {
            "status_counts": status_counts,
            "error_counts": error_counts,
            "completed_per_worker": completed_per_worker,
            "completed_portfolios_per_second": round(item_count / restart_drain_seconds, 4),
            "restart_backlog_drain_seconds": round(restart_drain_seconds, 6),
            "completion_latency_seconds": {
                "p50": round(statistics.median(completion_latencies), 6),
                "p95": round(_percentile(completion_latencies, 0.95), 6),
                "p99": round(_percentile(completion_latencies, 0.99), 6),
                "max": round(max(completion_latencies), 6),
            },
            "duplicate_alternative_count": len(alternative_ids) - len(set(alternative_ids)),
            "unique_alternative_set_count": len(set(alternative_ids)),
        },
        "resources": {
            "wall_seconds_including_admission_and_interruption": round(wall_seconds, 6),
            "python_process_cpu_seconds": round(cpu_seconds, 6),
            "python_traced_heap_current_bytes": current_heap_bytes,
            "python_traced_heap_peak_bytes": peak_heap_bytes,
            "postgres_database_bytes_before": database_bytes_before,
            "postgres_database_bytes_after": database_bytes_after,
            "postgres_database_growth_bytes": database_bytes_after - database_bytes_before,
        },
        "environment": {
            "operating_system": platform.system(),
            "machine": platform.machine(),
            "python": platform.python_version(),
            "logical_cpu_count": os.cpu_count(),
        },
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dsn", required=True, help="PostgreSQL DSN; never emitted in output.")
    parser.add_argument("--items", type=int, default=100)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--interrupt-count", type=int, default=4)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if args.items < 1 or args.concurrency < 1 or args.concurrency > 64:
        raise SystemExit("items must be positive and concurrency must be between 1 and 64")
    if args.interrupt_count < 0:
        raise SystemExit("interrupt-count must not be negative")
    result = run_probe(
        dsn=args.dsn,
        item_count=args.items,
        concurrency=args.concurrency,
        interrupt_count=args.interrupt_count,
    )
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
