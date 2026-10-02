"""Load evidence must fail promptly rather than hide unsuccessful dispositions."""

import pytest
from typing import Any

from scripts import measure_wave_simulation_workload as probe
from src.api.services import wave_simulation_operations
from src.api.services.wave_simulation_item import _PORTFOLIO_IDENTITY_CONFLICT
from src.core.waves import DpmRebalanceWaveItem
from src.infrastructure.construction import InMemoryConstructionRepository
from src.infrastructure.waves import InMemoryDpmWaveRepository


@pytest.mark.parametrize("worker_failure", ["none", "retryable", "terminal"])
def test_probe_finishes_success_and_reports_partial_failure(
    monkeypatch: pytest.MonkeyPatch, worker_failure: str
) -> None:
    waves = InMemoryDpmWaveRepository()
    construction = InMemoryConstructionRepository()
    monkeypatch.setattr(probe, "PostgresDpmWaveRepository", lambda **_: waves)
    monkeypatch.setattr(probe, "PostgresConstructionRepository", lambda **_: construction)
    monkeypatch.setattr(probe, "_database_size", lambda _: 0)
    real_simulate = wave_simulation_operations.simulate_item

    def simulate(**kwargs: Any) -> DpmRebalanceWaveItem:
        fails = kwargs["item"].portfolio_id.endswith("000")
        if worker_failure == "retryable" and fails:
            raise TimeoutError("synthetic dependency failure")
        result = real_simulate(**kwargs)
        if worker_failure == "terminal" and fails:
            return result.model_copy(update={"reason_codes": [_PORTFOLIO_IDENTITY_CONFLICT]})
        return result

    def unexpected_sleep(_: float) -> None:
        pytest.fail("A single worker must not poll after all items have dispositions")

    monkeypatch.setattr(wave_simulation_operations, "simulate_item", simulate)
    monkeypatch.setattr(probe.time, "sleep", unexpected_sleep)
    if worker_failure != "none":
        with pytest.raises(RuntimeError, match="Load probe did not complete successfully"):
            probe.run_probe(dsn="unused", item_count=2, concurrency=1, interrupt_count=0)
    else:
        result = probe.run_probe(dsn="unused", item_count=2, concurrency=1, interrupt_count=0)
        assert result["results"]["status_counts"] == {"SUCCEEDED": 2}
        assert result["results"]["error_counts"] == {}
        assert result["results"]["completed_per_worker"] == [2]
        assert result["results"]["unique_alternative_set_count"] == 2
