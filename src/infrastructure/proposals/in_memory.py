from copy import deepcopy
from datetime import datetime
from threading import Lock
from typing import Optional

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
from src.core.proposals.repository import ProposalRepository


class InMemoryProposalRepository(ProposalRepository):
    def __init__(self) -> None:
        self._lock = Lock()
        self._proposals: dict[str, ProposalRecord] = {}
        self._versions: dict[tuple[str, int], ProposalVersionRecord] = {}
        self._events: dict[str, list[ProposalWorkflowEventRecord]] = {}
        self._approvals: dict[str, list[ProposalApprovalRecordData]] = {}
        self._idempotency: dict[str, ProposalIdempotencyRecord] = {}
        self._simulation_idempotency: dict[str, ProposalSimulationIdempotencyRecord] = {}
        self._operations: dict[str, ProposalAsyncOperationRecord] = {}
        self._operation_by_correlation: dict[str, str] = {}

    def get_idempotency(self, *, idempotency_key: str) -> Optional[ProposalIdempotencyRecord]:
        with self._lock:
            record = self._idempotency.get(idempotency_key)
            return deepcopy(record) if record is not None else None

    def save_idempotency(self, record: ProposalIdempotencyRecord) -> None:
        with self._lock:
            self._idempotency[record.idempotency_key] = deepcopy(record)

    def get_simulation_idempotency(
        self, *, idempotency_key: str
    ) -> Optional[ProposalSimulationIdempotencyRecord]:
        with self._lock:
            record = self._simulation_idempotency.get(idempotency_key)
            return deepcopy(record) if record is not None else None

    def save_simulation_idempotency(self, record: ProposalSimulationIdempotencyRecord) -> None:
        with self._lock:
            self._simulation_idempotency[record.idempotency_key] = deepcopy(record)

    def create_operation(self, operation: ProposalAsyncOperationRecord) -> None:
        with self._lock:
            self._operations[operation.operation_id] = deepcopy(operation)
            self._operation_by_correlation[operation.correlation_id] = operation.operation_id

    def update_operation(self, operation: ProposalAsyncOperationRecord) -> None:
        with self._lock:
            self._operations[operation.operation_id] = deepcopy(operation)
            self._operation_by_correlation[operation.correlation_id] = operation.operation_id

    def get_operation(self, *, operation_id: str) -> Optional[ProposalAsyncOperationRecord]:
        with self._lock:
            operation = self._operations.get(operation_id)
            return deepcopy(operation) if operation is not None else None

    def get_operation_by_correlation(
        self, *, correlation_id: str
    ) -> Optional[ProposalAsyncOperationRecord]:
        with self._lock:
            operation_id = self._operation_by_correlation.get(correlation_id)
            if operation_id is None:
                return None
            operation = self._operations.get(operation_id)
            return deepcopy(operation) if operation is not None else None

    def create_proposal(self, proposal: ProposalRecord) -> None:
        with self._lock:
            self._proposals[proposal.proposal_id] = deepcopy(proposal)

    def update_proposal(self, proposal: ProposalRecord) -> None:
        with self._lock:
            self._proposals[proposal.proposal_id] = deepcopy(proposal)

    def get_proposal(self, *, proposal_id: str) -> Optional[ProposalRecord]:
        with self._lock:
            proposal = self._proposals.get(proposal_id)
            return deepcopy(proposal) if proposal is not None else None

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
    ) -> tuple[list[ProposalRecord], Optional[str]]:
        with self._lock:
            rows = list(self._proposals.values())

        rows = sorted(rows, key=lambda x: (x.created_at, x.proposal_id), reverse=True)

        if portfolio_id is not None:
            rows = [row for row in rows if row.portfolio_id == portfolio_id]
        if state is not None:
            rows = [row for row in rows if row.current_state == state]
        if created_by is not None:
            rows = [row for row in rows if row.created_by == created_by]
        if created_from is not None:
            rows = [row for row in rows if row.created_at >= created_from]
        if created_to is not None:
            rows = [row for row in rows if row.created_at <= created_to]

        if cursor:
            row_ids = [row.proposal_id for row in rows]
            if cursor in row_ids:
                start = row_ids.index(cursor) + 1
                rows = rows[start:]

        page = rows[:limit]
        next_cursor = page[-1].proposal_id if len(rows) > limit else None
        return [deepcopy(row) for row in page], next_cursor

    def create_version(self, version: ProposalVersionRecord) -> None:
        with self._lock:
            self._versions[(version.proposal_id, version.version_no)] = deepcopy(version)

    def get_version(self, *, proposal_id: str, version_no: int) -> Optional[ProposalVersionRecord]:
        with self._lock:
            version = self._versions.get((proposal_id, version_no))
            return deepcopy(version) if version is not None else None

    def get_current_version(self, *, proposal_id: str) -> Optional[ProposalVersionRecord]:
        with self._lock:
            versions = [v for (pid, _), v in self._versions.items() if pid == proposal_id]
        if not versions:
            return None
        versions.sort(key=lambda x: x.version_no, reverse=True)
        return deepcopy(versions[0])

    def append_event(self, event: ProposalWorkflowEventRecord) -> None:
        with self._lock:
            events = self._events.setdefault(event.proposal_id, [])
            events.append(deepcopy(event))

    def list_events(self, *, proposal_id: str) -> list[ProposalWorkflowEventRecord]:
        with self._lock:
            events = self._events.get(proposal_id, [])
            return [deepcopy(event) for event in events]

    def create_approval(self, approval: ProposalApprovalRecordData) -> None:
        with self._lock:
            approvals = self._approvals.setdefault(approval.proposal_id, [])
            approvals.append(deepcopy(approval))

    def list_approvals(self, *, proposal_id: str) -> list[ProposalApprovalRecordData]:
        with self._lock:
            approvals = self._approvals.get(proposal_id, [])
            return [deepcopy(approval) for approval in approvals]

    def transition_proposal(
        self,
        *,
        proposal: ProposalRecord,
        event: ProposalWorkflowEventRecord,
        approval: Optional[ProposalApprovalRecordData],
    ) -> ProposalTransitionResult:
        with self._lock:
            self._events.setdefault(event.proposal_id, []).append(deepcopy(event))
            if approval is not None:
                self._approvals.setdefault(approval.proposal_id, []).append(deepcopy(approval))
            self._proposals[proposal.proposal_id] = deepcopy(proposal)

        return ProposalTransitionResult(
            proposal=deepcopy(proposal),
            event=deepcopy(event),
            approval=deepcopy(approval) if approval is not None else None,
        )
