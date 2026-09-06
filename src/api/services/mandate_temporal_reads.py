from datetime import date

from src.api.services.mandate_errors import (
    DpmMandateHealthNotFoundError,
    DpmMandateNotFoundError,
)
from src.core.mandate_repository import DpmMandateRepository
from src.core.mandates import DpmMandateDigitalTwin, DpmMandateHealthSnapshot


def get_mandate_by_portfolio(
    *,
    repository: DpmMandateRepository,
    portfolio_id: str,
    as_of_date: date | None,
    tenant_id: str,
) -> DpmMandateDigitalTwin:
    if as_of_date is None:
        twin = repository.get_latest_mandate_by_portfolio(
            portfolio_id=portfolio_id, tenant_id=tenant_id
        )
    else:
        twin = repository.get_mandate_by_portfolio_as_of(
            portfolio_id=portfolio_id,
            as_of_date=as_of_date,
            tenant_id=tenant_id,
        )
    if twin is None:
        raise DpmMandateNotFoundError("DPM_MANDATE_NOT_FOUND")
    return twin


def get_mandate_health(
    *,
    repository: DpmMandateRepository,
    mandate_id: str,
    as_of_date: date | None,
    tenant_id: str,
) -> DpmMandateHealthSnapshot:
    if as_of_date is None:
        snapshot = repository.get_latest_health_snapshot(mandate_id=mandate_id, tenant_id=tenant_id)
    else:
        snapshot = repository.get_health_snapshot_as_of(
            mandate_id=mandate_id,
            as_of_date=as_of_date,
            tenant_id=tenant_id,
        )
    if snapshot is None:
        raise DpmMandateHealthNotFoundError("DPM_MANDATE_HEALTH_NOT_FOUND")
    return snapshot
