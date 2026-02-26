from datetime import datetime
from typing import Optional, Protocol

from src.core.proposals.models import (
    ProposalApprovalRecordData,
    ProposalAsyncOperationRecord,
    ProposalIdempotencyRecord,
    ProposalRecord,
    ProposalSimulationIdempotencyRecord,
    ProposalTransitionResult,
    ProposalVersionRecord,
    ProposalWorkflowEventRecord,
)


class ProposalRepository(Protocol):
    def get_idempotency(self, *, idempotency_key: str) -> Optional[ProposalIdempotencyRecord]: ...

    def save_idempotency(self, record: ProposalIdempotencyRecord) -> None: ...

    def get_simulation_idempotency(
        self, *, idempotency_key: str
    ) -> Optional[ProposalSimulationIdempotencyRecord]: ...

    def save_simulation_idempotency(self, record: ProposalSimulationIdempotencyRecord) -> None: ...

    def create_operation(self, operation: ProposalAsyncOperationRecord) -> None: ...

    def update_operation(self, operation: ProposalAsyncOperationRecord) -> None: ...

    def get_operation(self, *, operation_id: str) -> Optional[ProposalAsyncOperationRecord]: ...

    def get_operation_by_correlation(
        self, *, correlation_id: str
    ) -> Optional[ProposalAsyncOperationRecord]: ...

    def create_proposal(self, proposal: ProposalRecord) -> None: ...

    def update_proposal(self, proposal: ProposalRecord) -> None: ...

    def get_proposal(self, *, proposal_id: str) -> Optional[ProposalRecord]: ...

    def list_proposals(
        self,
        *,
        portfolio_id: Optional[str],
        state: Optional[str],
        created_by: Optional[str],
        created_from: Optional[datetime],
        created_to: Optional[datetime],
        limit: int,
        cursor: Optional[str],
    ) -> tuple[list[ProposalRecord], Optional[str]]: ...

    def create_version(self, version: ProposalVersionRecord) -> None: ...

    def get_version(
        self, *, proposal_id: str, version_no: int
    ) -> Optional[ProposalVersionRecord]: ...

    def get_current_version(self, *, proposal_id: str) -> Optional[ProposalVersionRecord]: ...

    def append_event(self, event: ProposalWorkflowEventRecord) -> None: ...

    def list_events(self, *, proposal_id: str) -> list[ProposalWorkflowEventRecord]: ...

    def create_approval(self, approval: ProposalApprovalRecordData) -> None: ...

    def list_approvals(self, *, proposal_id: str) -> list[ProposalApprovalRecordData]: ...

    def transition_proposal(
        self,
        *,
        proposal: ProposalRecord,
        event: ProposalWorkflowEventRecord,
        approval: Optional[ProposalApprovalRecordData],
    ) -> ProposalTransitionResult: ...
