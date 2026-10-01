from __future__ import annotations

import json
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Optional


class AsyncOperationTerminalPublisher(ABC):
    """Shared token-fenced terminal publication contract for durable adapters."""

    def publish_operation_success(
        self,
        *,
        tenant_id: str,
        operation_id: str,
        execution_token: str,
        result_json: dict[str, Any],
        finished_at: datetime,
    ) -> bool:
        return self._publish_operation_terminal(
            tenant_id=tenant_id,
            operation_id=operation_id,
            execution_token=execution_token,
            status="SUCCEEDED",
            result_json=_json_dump(result_json),
            error_json=None,
            finished_at=finished_at,
        )

    def publish_operation_failure(
        self,
        *,
        tenant_id: str,
        operation_id: str,
        execution_token: str,
        error_json: dict[str, str],
        finished_at: datetime,
    ) -> bool:
        return self._publish_operation_terminal(
            tenant_id=tenant_id,
            operation_id=operation_id,
            execution_token=execution_token,
            status="FAILED",
            result_json=None,
            error_json=_json_dump(error_json),
            finished_at=finished_at,
        )

    @abstractmethod
    def _publish_operation_terminal(
        self,
        *,
        tenant_id: str,
        operation_id: str,
        execution_token: str,
        status: str,
        result_json: Optional[str],
        error_json: Optional[str],
        finished_at: datetime,
    ) -> bool:
        """Publish once when the supplied token remains the current owner."""


def _json_dump(value: dict[str, Any]) -> str:
    return json.dumps(value, separators=(",", ":"), sort_keys=True)


__all__ = ["AsyncOperationTerminalPublisher"]
