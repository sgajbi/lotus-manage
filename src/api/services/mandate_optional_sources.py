from __future__ import annotations

from typing import Any

from src.core.dpm_source_context import DpmCoreBenchmarkAssignmentResponse
from src.infrastructure.core_sourcing import DpmCoreResolverClient, DpmCoreResolverError


def try_resolve_optional_source(
    *,
    resolver: DpmCoreResolverClient,
    method_name: str,
    family_name: str,
    **kwargs: Any,
) -> tuple[Any | None, str | None]:
    method = getattr(resolver, method_name, None)
    if method is None:
        return None, None
    try:
        return method(**kwargs), None
    except DpmCoreResolverError:
        return None, family_name


def ready_optional_source(
    *,
    source: Any | None,
    unavailable_family: str | None,
    family_name: str,
) -> tuple[Any | None, str | None]:
    if source is None:
        return None, unavailable_family
    supportability = getattr(source, "supportability", None)
    if supportability is not None and getattr(supportability, "state", None) != "READY":
        return None, family_name
    data_quality_status = getattr(source, "data_quality_status", None)
    if data_quality_status is not None and str(data_quality_status).upper() not in {
        "READY",
        "COMPLETE",
        "ACCEPTED",
    }:
        return None, family_name
    return source, unavailable_family


def ready_benchmark_assignment_source(
    *,
    source: DpmCoreBenchmarkAssignmentResponse | None,
    unavailable_family: str | None,
) -> tuple[DpmCoreBenchmarkAssignmentResponse | None, str | None]:
    if source is None:
        return None, unavailable_family
    if source.assignment_status.upper() != "ACTIVE":
        return None, "BENCHMARK_ASSIGNMENT"
    return source, unavailable_family


__all__ = [
    "ready_benchmark_assignment_source",
    "ready_optional_source",
    "try_resolve_optional_source",
]
