import importlib

from fastapi import APIRouter

router = APIRouter()


_simulate_routes = importlib.import_module("src.api.routers.rebalance_simulation_simulate_routes")
simulate_rebalance = _simulate_routes.simulate_rebalance
_analyze_routes = importlib.import_module("src.api.routers.rebalance_simulation_analyze_routes")
analyze_scenarios = _analyze_routes.analyze_scenarios
_async_routes = importlib.import_module("src.api.routers.rebalance_simulation_async_routes")
analyze_scenarios_async = _async_routes.analyze_scenarios_async
_operation_routes = importlib.import_module("src.api.routers.rebalance_simulation_operation_routes")
execute_dpm_async_operation = _operation_routes.execute_dpm_async_operation
