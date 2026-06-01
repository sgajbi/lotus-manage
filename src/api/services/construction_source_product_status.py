from src.core.construction.vocabulary import ConstructionMethodStatus


def source_status_to_method_status(status: str) -> ConstructionMethodStatus:
    if status == "READY":
        return ConstructionMethodStatus.READY
    if status == "DEGRADED":
        return ConstructionMethodStatus.DEGRADED
    return ConstructionMethodStatus.BLOCKED


__all__ = ["source_status_to_method_status"]
