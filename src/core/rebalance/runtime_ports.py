"""Explicit runtime dependencies for synchronous and resumable DPM execution."""

from collections.abc import Callable
from dataclasses import dataclass
import logging

from src.core.integration_ports import CoreResolverClient
from src.core.models import BatchRebalanceResult, RebalanceResult
from src.core.rebalance.policy_packs import DpmPolicyPackDefinition
from src.core.rebalance_runs import DpmRunSupportService


@dataclass(frozen=True)
class RebalanceRuntime:
    resolver_factory: Callable[[], CoreResolverClient]
    run_simulation: Callable[..., RebalanceResult]
    record_for_support: Callable[..., object]
    support_service_factory: Callable[[], DpmRunSupportService]
    catalog_loader: Callable[[], dict[str, DpmPolicyPackDefinition]]
    logger: logging.Logger
    execute_batch: Callable[..., BatchRebalanceResult] | None = None
