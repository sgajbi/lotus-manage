from src.core.mandates import DpmMandateDigitalTwin
from src.core.mandate_repository import DpmMandateRepository
from src.core.waves import DpmRebalanceWaveItem
from src.core.waves.source_readiness import classify_wave_item_source_readiness


def classify_item_source_readiness(
    *,
    item: DpmRebalanceWaveItem,
    wave_as_of_date: str,
    mandate_repository: DpmMandateRepository,
    tenant_id: str,
) -> DpmRebalanceWaveItem:
    twin = resolve_mandate_twin(
        item=item, mandate_repository=mandate_repository, tenant_id=tenant_id
    )
    health = (
        mandate_repository.get_latest_health_snapshot(
            mandate_id=twin.mandate_id, tenant_id=tenant_id
        )
        if twin is not None
        else None
    )
    return classify_wave_item_source_readiness(
        item=item,
        wave_as_of_date=wave_as_of_date,
        mandate_twin=twin,
        mandate_health=health,
    )


def resolve_mandate_twin(
    *,
    item: DpmRebalanceWaveItem,
    mandate_repository: DpmMandateRepository,
    tenant_id: str,
) -> DpmMandateDigitalTwin | None:
    if item.mandate_id:
        twin = mandate_repository.get_latest_mandate(
            mandate_id=item.mandate_id, tenant_id=tenant_id
        )
        if twin is not None and twin.portfolio_id == item.portfolio_id:
            return twin
    return mandate_repository.get_latest_mandate_by_portfolio(
        portfolio_id=item.portfolio_id, tenant_id=tenant_id
    )


__all__ = ["classify_item_source_readiness", "resolve_mandate_twin"]
