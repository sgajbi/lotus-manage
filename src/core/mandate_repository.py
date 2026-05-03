from __future__ import annotations

from datetime import datetime
from typing import Optional, Protocol

from src.core.mandates import (
    DpmMandateDigitalTwin,
    DpmMandateHealthSnapshot,
    DpmMonitoringException,
)


class DpmMandateRepository(Protocol):
    def save_mandate_snapshot(self, twin: DpmMandateDigitalTwin) -> None: ...

    def get_latest_mandate_by_portfolio(
        self,
        *,
        portfolio_id: str,
    ) -> Optional[DpmMandateDigitalTwin]: ...

    def get_latest_mandate(
        self,
        *,
        mandate_id: str,
    ) -> Optional[DpmMandateDigitalTwin]: ...

    def list_mandate_versions(
        self,
        *,
        mandate_id: str,
    ) -> list[DpmMandateDigitalTwin]: ...

    def save_health_snapshot(self, snapshot: DpmMandateHealthSnapshot) -> None: ...

    def get_latest_health_snapshot(
        self,
        *,
        mandate_id: str,
    ) -> Optional[DpmMandateHealthSnapshot]: ...

    def save_monitoring_exception(self, exception: DpmMonitoringException) -> None: ...

    def list_monitoring_exceptions(
        self,
        *,
        mandate_id: Optional[str],
        portfolio_id: Optional[str],
        state: Optional[str],
        limit: int,
        cursor: Optional[str],
    ) -> tuple[list[DpmMonitoringException], Optional[str]]: ...

    def resolve_monitoring_exception(
        self,
        *,
        exception_id: str,
        resolved_at: datetime,
        resolution_reason: str,
    ) -> Optional[DpmMonitoringException]: ...

    def purge_mandate_records_before(self, *, cutoff: datetime) -> int: ...
