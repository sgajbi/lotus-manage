"""Shared terminal-publication entrypoints for wave simulation repositories."""

from __future__ import annotations

from datetime import datetime

from src.core.waves.models import DpmRebalanceWaveItem
from src.core.waves.simulation_operations import DpmWaveSimulationItemClaim


class DpmWaveSimulationPublicationMixin:
    def publish_simulation_item_result(
        self,
        *,
        claim: DpmWaveSimulationItemClaim,
        result_item: DpmRebalanceWaveItem,
        completed_at: datetime,
    ) -> bool:
        return self._publish_simulation_item_terminal(
            claim=claim,
            completed_at=completed_at,
            status="SUCCEEDED",
            result_item=result_item,
            error_code=None,
            error_message=None,
            retryable=False,
        )

    def publish_simulation_item_failure(
        self,
        *,
        claim: DpmWaveSimulationItemClaim,
        error_code: str,
        error_message: str,
        retryable: bool,
        completed_at: datetime,
    ) -> bool:
        return self._publish_simulation_item_terminal(
            claim=claim,
            completed_at=completed_at,
            status="FAILED",
            result_item=None,
            error_code=error_code,
            error_message=error_message,
            retryable=retryable,
        )

    def _publish_simulation_item_terminal(
        self,
        *,
        claim: DpmWaveSimulationItemClaim,
        completed_at: datetime,
        status: str,
        result_item: DpmRebalanceWaveItem | None,
        error_code: str | None,
        error_message: str | None,
        retryable: bool,
    ) -> bool:
        raise NotImplementedError


__all__ = ["DpmWaveSimulationPublicationMixin"]
