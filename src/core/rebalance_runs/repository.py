from datetime import datetime
from typing import Any, Optional, Protocol

from src.core.rebalance_runs.models import (
    DpmAsyncOperationRecord,
    DpmLineageEdgeRecord,
    DpmRunIdempotencyHistoryRecord,
    DpmRunIdempotencyRecord,
    DpmRunRecord,
    DpmSimulationSubmissionClaimRecord,
    DpmRunWorkflowDecisionRecord,
    DpmSupportabilitySummaryData,
)


class DpmRunRepositoryConflictError(Exception):
    pass


class DpmRunRepository(Protocol):
    def claim_simulation_submission(
        self,
        *,
        tenant_id: str,
        idempotency_key: str,
        request_hash: str,
        claim_token: str,
        claimed_at: datetime,
        claim_expires_at: datetime,
    ) -> DpmSimulationSubmissionClaimRecord: ...

    def get_simulation_submission_claim(
        self, *, tenant_id: str, idempotency_key: str
    ) -> Optional[DpmSimulationSubmissionClaimRecord]: ...

    def abandon_simulation_submission_claim(
        self, *, tenant_id: str, idempotency_key: str, claim_token: str, abandoned_at: datetime
    ) -> None: ...

    def complete_simulation_submission(
        self,
        *,
        tenant_id: str,
        idempotency_key: str,
        request_hash: str,
        claim_token: str,
        run: DpmRunRecord,
        artifact_json: Optional[dict[str, Any]],
        idempotency_history: DpmRunIdempotencyHistoryRecord,
        lineage_edges: list[DpmLineageEdgeRecord],
        completed_at: datetime,
    ) -> None: ...

    def save_run(self, run: DpmRunRecord) -> None: ...

    def get_run(self, *, rebalance_run_id: str) -> Optional[DpmRunRecord]: ...

    def get_run_for_tenant(
        self, *, tenant_id: str, rebalance_run_id: str
    ) -> Optional[DpmRunRecord]: ...

    def get_run_by_correlation(self, *, correlation_id: str) -> Optional[DpmRunRecord]: ...

    def get_run_by_correlation_for_tenant(
        self, *, tenant_id: str, correlation_id: str
    ) -> Optional[DpmRunRecord]: ...

    def get_run_by_request_hash(self, *, request_hash: str) -> Optional[DpmRunRecord]: ...

    def get_run_by_request_hash_for_tenant(
        self, *, tenant_id: str, request_hash: str
    ) -> Optional[DpmRunRecord]: ...

    def list_runs(
        self,
        *,
        created_from: Optional[datetime],
        created_to: Optional[datetime],
        status: Optional[str],
        request_hash: Optional[str],
        portfolio_id: Optional[str],
        limit: int,
        cursor: Optional[str],
    ) -> tuple[list[DpmRunRecord], Optional[str]]: ...

    def list_runs_for_tenant(
        self,
        *,
        tenant_id: str,
        created_from: Optional[datetime],
        created_to: Optional[datetime],
        status: Optional[str],
        request_hash: Optional[str],
        portfolio_id: Optional[str],
        limit: int,
        cursor: Optional[str],
    ) -> tuple[list[DpmRunRecord], Optional[str]]: ...

    def save_run_artifact(
        self, *, rebalance_run_id: str, artifact_json: dict[str, Any]
    ) -> None: ...

    def get_run_artifact(self, *, rebalance_run_id: str) -> Optional[dict[str, Any]]: ...

    def save_idempotency_mapping(self, record: DpmRunIdempotencyRecord) -> None: ...

    def get_idempotency_mapping(
        self, *, idempotency_key: str
    ) -> Optional[DpmRunIdempotencyRecord]: ...

    def get_idempotency_mapping_for_tenant(
        self, *, tenant_id: str, idempotency_key: str
    ) -> Optional[DpmRunIdempotencyRecord]: ...

    def append_idempotency_history(self, record: DpmRunIdempotencyHistoryRecord) -> None: ...

    def list_idempotency_history(
        self, *, idempotency_key: str
    ) -> list[DpmRunIdempotencyHistoryRecord]: ...

    def list_idempotency_history_for_tenant(
        self, *, tenant_id: str, idempotency_key: str
    ) -> list[DpmRunIdempotencyHistoryRecord]: ...

    def create_operation(self, operation: DpmAsyncOperationRecord) -> None: ...

    def update_operation(self, operation: DpmAsyncOperationRecord) -> None: ...

    def get_operation(self, *, operation_id: str) -> Optional[DpmAsyncOperationRecord]: ...

    def get_operation_by_correlation(
        self, *, correlation_id: str
    ) -> Optional[DpmAsyncOperationRecord]: ...

    def list_operations(
        self,
        *,
        created_from: Optional[datetime],
        created_to: Optional[datetime],
        operation_type: Optional[str],
        status: Optional[str],
        correlation_id: Optional[str],
        limit: int,
        cursor: Optional[str],
    ) -> tuple[list[DpmAsyncOperationRecord], Optional[str]]: ...

    def purge_expired_operations(self, *, ttl_seconds: int, now: datetime) -> int: ...

    def append_workflow_decision(self, decision: DpmRunWorkflowDecisionRecord) -> None: ...

    def list_workflow_decisions(
        self, *, rebalance_run_id: str
    ) -> list[DpmRunWorkflowDecisionRecord]: ...
    def list_workflow_decisions_filtered(
        self,
        *,
        rebalance_run_id: Optional[str],
        action: Optional[str],
        actor_id: Optional[str],
        reason_code: Optional[str],
        decided_from: Optional[datetime],
        decided_to: Optional[datetime],
        limit: int,
        cursor: Optional[str],
    ) -> tuple[list[DpmRunWorkflowDecisionRecord], Optional[str]]: ...

    def append_lineage_edge(self, edge: DpmLineageEdgeRecord) -> None: ...

    def list_lineage_edges(self, *, entity_id: str) -> list[DpmLineageEdgeRecord]: ...

    def get_supportability_summary(
        self, *, portfolio_id: Optional[str] = None
    ) -> DpmSupportabilitySummaryData: ...

    def purge_expired_runs(self, *, retention_days: int, now: datetime) -> int: ...
