from fastapi import APIRouter

from src.api.routers.route_registration import load_route_callable

router = APIRouter()

simulate_rebalance = load_route_callable(
    "src.api.routers.rebalance_simulation_simulate_routes",
    "simulate_rebalance",
)
analyze_scenarios = load_route_callable(
    "src.api.routers.rebalance_simulation_analyze_routes",
    "analyze_scenarios",
)
analyze_scenarios_async = load_route_callable(
    "src.api.routers.rebalance_simulation_async_routes",
    "analyze_scenarios_async",
)
execute_dpm_async_operation = load_route_callable(
    "src.api.routers.rebalance_simulation_operation_routes",
    "execute_dpm_async_operation",
)
