import importlib
from typing import Any

from fastapi import APIRouter

router = APIRouter()


def _load_route_callable(module_name: str, callable_name: str) -> Any:
    return getattr(importlib.import_module(module_name), callable_name)


simulate_rebalance = _load_route_callable(
    "src.api.routers.rebalance_simulation_simulate_routes",
    "simulate_rebalance",
)
analyze_scenarios = _load_route_callable(
    "src.api.routers.rebalance_simulation_analyze_routes",
    "analyze_scenarios",
)
analyze_scenarios_async = _load_route_callable(
    "src.api.routers.rebalance_simulation_async_routes",
    "analyze_scenarios_async",
)
execute_dpm_async_operation = _load_route_callable(
    "src.api.routers.rebalance_simulation_operation_routes",
    "execute_dpm_async_operation",
)
