from datetime import datetime
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field

from src.core.models import RebalanceResult

DpmAsyncOperationType = Literal["ANALYZE_SCENARIOS"]
DpmAsyncOperationStatus = Literal["PENDING", "RUNNING", "SUCCEEDED", "FAILED"]
DpmWorkflowStatus = Literal["NOT_REQUIRED", "PENDING_REVIEW", "APPROVED", "REJECTED"]
DpmWorkflowActionType = Literal["APPROVE", "REJECT", "REQUEST_CHANGES"]
DpmLineageEdgeType = Literal["CORRELATION_TO_RUN", "IDEMPOTENCY_TO_RUN", "OPERATION_TO_CORRELATION"]


class DpmRunRecord(BaseModel):
    rebalance_run_id: str = Field(
        description="Internal DPM run identifier.", examples=["rr_abc12345"]
    )
    correlation_id: str = Field(
        description="Internal correlation identifier.", examples=["corr-1234-abcd"]
    )
    request_hash: str = Field(
        description="Canonical request hash associated with the run.",
        examples=["sha256:abc123"],
    )
    idempotency_key: Optional[str] = Field(
        default=None,
        description="Idempotency key associated with run when available.",
        examples=["demo-idem-001"],
    )
    portfolio_id: str = Field(description="Portfolio identifier.", examples=["pf_123"])
    created_at: datetime = Field(
        description="Run creation timestamp (UTC).",
        examples=["2026-02-20T12:00:00+00:00"],
    )
    result_json: Dict[str, Any] = Field(
        description="Serialized DPM simulation result payload.",
        examples=[{"rebalance_run_id": "rr_abc12345", "status": "READY"}],
    )


class DpmRunIdempotencyRecord(BaseModel):
    idempotency_key: str = Field(
        description="Idempotency key supplied to simulate endpoint.",
        examples=["demo-idem-001"],
    )
    request_hash: str = Field(
        description="Canonical request hash associated with idempotency key.",
        examples=["sha256:abc123"],
    )
    rebalance_run_id: str = Field(
        description="Run identifier mapped by idempotency key.",
        examples=["rr_abc12345"],
    )
    created_at: datetime = Field(
        description="Timestamp when idempotency mapping was stored.",
        examples=["2026-02-20T12:00:00+00:00"],
    )


class DpmRunLookupResponse(BaseModel):
    rebalance_run_id: str = Field(description="DPM run identifier.", examples=["rr_abc12345"])
    correlation_id: str = Field(
        description="Correlation identifier for the run.", examples=["corr-1234-abcd"]
    )
    request_hash: str = Field(
        description="Canonical request hash associated with this run.",
        examples=["sha256:abc123"],
    )
    idempotency_key: Optional[str] = Field(
        default=None,
        description="Idempotency key associated with this run when available.",
        examples=["demo-idem-001"],
    )
    portfolio_id: str = Field(description="Portfolio identifier.", examples=["pf_123"])
    created_at: str = Field(
        description="Run creation timestamp (UTC ISO8601).",
        examples=["2026-02-20T12:00:00+00:00"],
    )
    result: RebalanceResult = Field(
        description="Full DPM simulation result payload for investigation and audit."
    )


class DpmRunListItemResponse(BaseModel):
    rebalance_run_id: str = Field(description="DPM run identifier.", examples=["rr_abc12345"])
    correlation_id: str = Field(
        description="Correlation identifier associated with the run.",
        examples=["corr-1234-abcd"],
    )
    request_hash: str = Field(
        description="Canonical request hash associated with this run.",
        examples=["sha256:abc123"],
    )
    idempotency_key: Optional[str] = Field(
        default=None,
        description="Idempotency key associated with this run when available.",
        examples=["demo-idem-001"],
    )
    portfolio_id: str = Field(description="Portfolio identifier.", examples=["pf_123"])
    status: str = Field(
        description="Business run status from persisted run result.",
        examples=["READY"],
    )
    created_at: str = Field(
        description="Run creation timestamp (UTC ISO8601).",
        examples=["2026-02-20T12:00:00+00:00"],
    )


class DpmRunListResponse(BaseModel):
    items: list[DpmRunListItemResponse] = Field(
        default_factory=list,
        description="Filtered run rows ordered by created timestamp descending.",
        examples=[
            [
                {
                    "rebalance_run_id": "rr_abc12345",
                    "correlation_id": "corr-1234-abcd",
                    "request_hash": "sha256:abc123",
                    "idempotency_key": "demo-idem-001",
                    "portfolio_id": "pf_123",
                    "status": "READY",
                    "created_at": "2026-02-20T12:00:00+00:00",
                }
            ]
        ],
    )
    next_cursor: Optional[str] = Field(
        default=None,
        description="Opaque cursor for retrieving the next result page.",
        examples=["rr_abc12345"],
    )


class DpmSupportabilitySummaryData(BaseModel):
    run_count: int = Field(
        description="Total persisted supportability run records.",
        examples=[128],
    )
    operation_count: int = Field(
        description="Total persisted async operation records.",
        examples=[42],
    )
    operation_status_counts: Dict[str, int] = Field(
        default_factory=dict,
        description="Count of async operations grouped by status.",
        examples=[{"PENDING": 2, "RUNNING": 1, "SUCCEEDED": 38, "FAILED": 1}],
    )
    run_status_counts: Dict[str, int] = Field(
        default_factory=dict,
        description="Count of persisted runs grouped by business run status.",
        examples=[{"READY": 120, "PENDING_REVIEW": 6, "BLOCKED": 2}],
    )
    workflow_decision_count: int = Field(
        description="Total persisted workflow decision records.",
        examples=[16],
    )
    workflow_action_counts: Dict[str, int] = Field(
        default_factory=dict,
        description="Count of workflow decisions grouped by action type.",
        examples=[{"APPROVE": 10, "REJECT": 2, "REQUEST_CHANGES": 4}],
    )
    workflow_reason_code_counts: Dict[str, int] = Field(
        default_factory=dict,
        description="Count of workflow decisions grouped by reason code.",
        examples=[{"REVIEW_APPROVED": 10, "POLICY_REJECTED": 2, "NEEDS_DETAIL": 4}],
    )
    lineage_edge_count: int = Field(
        description="Total persisted lineage edge records.",
        examples=[260],
    )
    oldest_run_created_at: Optional[datetime] = Field(
        default=None,
        description="Oldest persisted run creation timestamp (UTC).",
        examples=["2026-02-20T12:00:00+00:00"],
    )
    newest_run_created_at: Optional[datetime] = Field(
        default=None,
        description="Newest persisted run creation timestamp (UTC).",
        examples=["2026-02-20T12:10:00+00:00"],
    )
    oldest_operation_created_at: Optional[datetime] = Field(
        default=None,
        description="Oldest persisted operation creation timestamp (UTC).",
        examples=["2026-02-20T12:00:00+00:00"],
    )
    newest_operation_created_at: Optional[datetime] = Field(
        default=None,
        description="Newest persisted operation creation timestamp (UTC).",
        examples=["2026-02-20T12:10:00+00:00"],
    )


class DpmSupportabilitySummaryResponse(BaseModel):
    store_backend: str = Field(
        description="Configured supportability storage backend.",
        examples=["SQL"],
    )
    retention_days: int = Field(
        description="Configured supportability retention window in days (0 means disabled).",
        examples=[30],
    )
    run_count: int = Field(
        description="Total persisted supportability run records.",
        examples=[128],
    )
    operation_count: int = Field(
        description="Total persisted async operation records.",
        examples=[42],
    )
    operation_status_counts: Dict[str, int] = Field(
        default_factory=dict,
        description="Count of async operations grouped by status.",
        examples=[{"PENDING": 2, "RUNNING": 1, "SUCCEEDED": 38, "FAILED": 1}],
    )
    run_status_counts: Dict[str, int] = Field(
        default_factory=dict,
        description="Count of persisted runs grouped by business run status.",
        examples=[{"READY": 120, "PENDING_REVIEW": 6, "BLOCKED": 2}],
    )
    workflow_decision_count: int = Field(
        description="Total persisted workflow decision records.",
        examples=[16],
    )
    workflow_action_counts: Dict[str, int] = Field(
        default_factory=dict,
        description="Count of workflow decisions grouped by action type.",
        examples=[{"APPROVE": 10, "REJECT": 2, "REQUEST_CHANGES": 4}],
    )
    workflow_reason_code_counts: Dict[str, int] = Field(
        default_factory=dict,
        description="Count of workflow decisions grouped by reason code.",
        examples=[{"REVIEW_APPROVED": 10, "POLICY_REJECTED": 2, "NEEDS_DETAIL": 4}],
    )
    lineage_edge_count: int = Field(
        description="Total persisted lineage edge records.",
        examples=[260],
    )
    oldest_run_created_at: Optional[str] = Field(
        default=None,
        description="Oldest persisted run creation timestamp (UTC ISO8601).",
        examples=["2026-02-20T12:00:00+00:00"],
    )
    newest_run_created_at: Optional[str] = Field(
        default=None,
        description="Newest persisted run creation timestamp (UTC ISO8601).",
        examples=["2026-02-20T12:10:00+00:00"],
    )
    oldest_operation_created_at: Optional[str] = Field(
        default=None,
        description="Oldest persisted operation creation timestamp (UTC ISO8601).",
        examples=["2026-02-20T12:00:00+00:00"],
    )
    newest_operation_created_at: Optional[str] = Field(
        default=None,
        description="Newest persisted operation creation timestamp (UTC ISO8601).",
        examples=["2026-02-20T12:10:00+00:00"],
    )


class DpmRunSupportBundleResponse(BaseModel):
    run: DpmRunLookupResponse = Field(
        description="Primary persisted run payload and metadata for investigation.",
    )
    artifact: Optional["DpmRunArtifactResponse"] = Field(
        default=None,
        description="Deterministic run artifact payload when included.",
        examples=[None],
    )
    async_operation: Optional["DpmAsyncOperationStatusResponse"] = Field(
        default=None,
        description="Latest async operation mapped by run correlation id when available.",
        examples=[None],
    )
    workflow_history: "DpmRunWorkflowHistoryResponse" = Field(
        description="Append-only workflow decision history for the run.",
    )
    lineage: "DpmLineageResponse" = Field(
        description="Lineage edges that reference the run id.",
    )
    idempotency_history: Optional["DpmRunIdempotencyHistoryResponse"] = Field(
        default=None,
        description=(
            "Append-only idempotency mapping history for run idempotency key when available."
        ),
        examples=[None],
    )


class DpmRunIdempotencyLookupResponse(BaseModel):
    idempotency_key: str = Field(
        description="Idempotency key supplied on simulation request.",
        examples=["demo-idem-001"],
    )
    request_hash: str = Field(
        description="Canonical request hash mapped to idempotency key.",
        examples=["sha256:abc123"],
    )
    rebalance_run_id: str = Field(
        description="Run identifier mapped to idempotency key.",
        examples=["rr_abc12345"],
    )
    created_at: str = Field(
        description="Idempotency mapping timestamp (UTC ISO8601).",
        examples=["2026-02-20T12:00:00+00:00"],
    )


class DpmRunIdempotencyHistoryItem(BaseModel):
    rebalance_run_id: str = Field(
        description="Run identifier observed for this idempotency key event.",
        examples=["rr_abc12345"],
    )
    correlation_id: str = Field(
        description="Correlation identifier associated with the mapped run.",
        examples=["corr-1234-abcd"],
    )
    request_hash: str = Field(
        description="Canonical request hash associated with this idempotency event.",
        examples=["sha256:abc123"],
    )
    created_at: str = Field(
        description="Timestamp when this idempotency history event was recorded (UTC ISO8601).",
        examples=["2026-02-20T12:00:00+00:00"],
    )


class DpmRunIdempotencyHistoryRecord(BaseModel):
    idempotency_key: str = Field(
        description="Idempotency key supplied to simulate endpoint.",
        examples=["demo-idem-001"],
    )
    rebalance_run_id: str = Field(
        description="Run identifier mapped by idempotency key for this history event.",
        examples=["rr_abc12345"],
    )
    correlation_id: str = Field(
        description="Correlation identifier associated with the mapped run.",
        examples=["corr-1234-abcd"],
    )
    request_hash: str = Field(
        description="Canonical request hash associated with this history event.",
        examples=["sha256:abc123"],
    )
    created_at: datetime = Field(
        description="Timestamp when idempotency history event was stored.",
        examples=["2026-02-20T12:00:00+00:00"],
    )


class DpmRunIdempotencyHistoryResponse(BaseModel):
    idempotency_key: str = Field(
        description="Requested idempotency key.",
        examples=["demo-idem-001"],
    )
    history: list[DpmRunIdempotencyHistoryItem] = Field(
        default_factory=list,
        description="Append-only history of mappings observed for this idempotency key.",
        examples=[
            [
                {
                    "rebalance_run_id": "rr_abc12345",
                    "correlation_id": "corr-1234-abcd",
                    "request_hash": "sha256:abc123",
                    "created_at": "2026-02-20T12:00:00+00:00",
                }
            ]
        ],
    )


class DpmAsyncAcceptedResponse(BaseModel):
    operation_id: str = Field(
        description="Asynchronous operation identifier.",
        examples=["dop_001"],
    )
    operation_type: DpmAsyncOperationType = Field(
        description="Operation type accepted for asynchronous execution.",
        examples=["ANALYZE_SCENARIOS"],
    )
    status: DpmAsyncOperationStatus = Field(
        description="Initial operation status.",
        examples=["PENDING"],
    )
    correlation_id: str = Field(
        description="Correlation id assigned to asynchronous operation.",
        examples=["corr-dpm-async-001"],
    )
    created_at: str = Field(
        description="Operation acceptance timestamp (UTC ISO8601).",
        examples=["2026-02-20T12:00:00+00:00"],
    )
    status_url: str = Field(
        description="Relative API path for operation status retrieval.",
        examples=["/rebalance/operations/dop_001"],
    )
    execute_url: str = Field(
        description="Relative API path to manually execute pending operation.",
        examples=["/rebalance/operations/dop_001/execute"],
    )


class DpmAsyncError(BaseModel):
    code: str = Field(
        description="Stable operation error code.",
        examples=["SCENARIO_EXECUTION_ERROR"],
    )
    message: str = Field(
        description="Human-readable operation error message.",
        examples=["SCENARIO_EXECUTION_ERROR: RuntimeError"],
    )


class DpmAsyncOperationStatusResponse(BaseModel):
    operation_id: str = Field(
        description="Asynchronous operation identifier.",
        examples=["dop_001"],
    )
    operation_type: DpmAsyncOperationType = Field(
        description="Operation type.",
        examples=["ANALYZE_SCENARIOS"],
    )
    status: DpmAsyncOperationStatus = Field(
        description="Current operation status.",
        examples=["SUCCEEDED"],
    )
    is_executable: bool = Field(
        description="Whether this operation is currently executable by manual execute endpoint.",
        examples=[False],
    )
    correlation_id: str = Field(
        description="Correlation id associated with this operation.",
        examples=["corr-dpm-async-001"],
    )
    created_at: str = Field(
        description="Operation acceptance timestamp (UTC ISO8601).",
        examples=["2026-02-20T12:00:00+00:00"],
    )
    started_at: Optional[str] = Field(
        default=None,
        description="Operation start timestamp (UTC ISO8601).",
        examples=["2026-02-20T12:00:01+00:00"],
    )
    finished_at: Optional[str] = Field(
        default=None,
        description="Operation completion timestamp (UTC ISO8601).",
        examples=["2026-02-20T12:00:02+00:00"],
    )
    result: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Successful operation result payload when status is SUCCEEDED.",
        examples=[{"batch_run_id": "batch_abc12345", "results": {}}],
    )
    error: Optional[DpmAsyncError] = Field(
        default=None,
        description="Failure details when status is FAILED.",
        examples=[{"code": "RuntimeError", "message": "boom"}],
    )


class DpmAsyncOperationListItemResponse(BaseModel):
    operation_id: str = Field(
        description="Asynchronous operation identifier.",
        examples=["dop_001"],
    )
    operation_type: DpmAsyncOperationType = Field(
        description="Operation type.",
        examples=["ANALYZE_SCENARIOS"],
    )
    status: DpmAsyncOperationStatus = Field(
        description="Current operation status.",
        examples=["SUCCEEDED"],
    )
    correlation_id: str = Field(
        description="Correlation id associated with this operation.",
        examples=["corr-dpm-async-001"],
    )
    is_executable: bool = Field(
        description="Whether this operation is currently executable via manual execute endpoint.",
        examples=[False],
    )
    created_at: str = Field(
        description="Operation acceptance timestamp (UTC ISO8601).",
        examples=["2026-02-20T12:00:00+00:00"],
    )
    started_at: Optional[str] = Field(
        default=None,
        description="Operation start timestamp (UTC ISO8601).",
        examples=["2026-02-20T12:00:01+00:00"],
    )
    finished_at: Optional[str] = Field(
        default=None,
        description="Operation completion timestamp (UTC ISO8601).",
        examples=["2026-02-20T12:00:02+00:00"],
    )


class DpmAsyncOperationListResponse(BaseModel):
    items: list[DpmAsyncOperationListItemResponse] = Field(
        default_factory=list,
        description="Filtered async operation rows ordered by creation timestamp descending.",
        examples=[
            [
                {
                    "operation_id": "dop_001",
                    "operation_type": "ANALYZE_SCENARIOS",
                    "status": "SUCCEEDED",
                    "correlation_id": "corr-dpm-async-001",
                    "is_executable": False,
                    "created_at": "2026-02-20T12:00:00+00:00",
                    "started_at": "2026-02-20T12:00:01+00:00",
                    "finished_at": "2026-02-20T12:00:02+00:00",
                }
            ]
        ],
    )
    next_cursor: Optional[str] = Field(
        default=None,
        description="Opaque cursor for retrieving the next result page.",
        examples=["dop_001"],
    )


class DpmAsyncOperationRecord(BaseModel):
    operation_id: str = Field(
        description="Internal async operation identifier.",
        examples=["dop_001"],
    )
    operation_type: DpmAsyncOperationType = Field(
        description="Internal async operation type.",
        examples=["ANALYZE_SCENARIOS"],
    )
    status: DpmAsyncOperationStatus = Field(
        description="Internal async operation status.",
        examples=["PENDING"],
    )
    correlation_id: str = Field(
        description="Internal operation correlation id.",
        examples=["corr-dpm-async-001"],
    )
    created_at: datetime = Field(
        description="Internal operation creation timestamp.",
        examples=["2026-02-20T12:00:00+00:00"],
    )
    started_at: Optional[datetime] = Field(
        default=None,
        description="Internal operation start timestamp.",
        examples=["2026-02-20T12:00:01+00:00"],
    )
    finished_at: Optional[datetime] = Field(
        default=None,
        description="Internal operation completion timestamp.",
        examples=["2026-02-20T12:00:02+00:00"],
    )
    result_json: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Internal serialized success payload.",
        examples=[{"batch_run_id": "batch_abc12345"}],
    )
    error_json: Optional[Dict[str, str]] = Field(
        default=None,
        description="Internal serialized failure payload.",
        examples=[{"code": "RuntimeError", "message": "boom"}],
    )
    request_json: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Internal request payload snapshot for deferred execution.",
        examples=[{"scenarios": {"baseline": {"options": {}}}}],
    )


class DpmRunWorkflowDecisionRecord(BaseModel):
    decision_id: str = Field(
        description="Workflow decision identifier.",
        examples=["dwd_001"],
    )
    run_id: str = Field(
        description="DPM run identifier associated with workflow decision.",
        examples=["rr_abc12345"],
    )
    action: DpmWorkflowActionType = Field(
        description="Workflow action applied by reviewer.",
        examples=["APPROVE"],
    )
    reason_code: str = Field(
        pattern=r"^[A-Z][A-Z0-9_]*$",
        description="Stable uppercase snake case reason code for the decision.",
        examples=["REVIEW_APPROVED"],
    )
    comment: Optional[str] = Field(
        default=None,
        description="Optional free-text reviewer comment.",
        examples=["Checks passed after review."],
    )
    actor_id: str = Field(
        description="Actor id of reviewer taking workflow action.",
        examples=["reviewer_001"],
    )
    decided_at: datetime = Field(
        description="Workflow decision timestamp (UTC).",
        examples=["2026-02-20T12:00:00+00:00"],
    )
    correlation_id: str = Field(
        description="Correlation id captured for workflow action tracing.",
        examples=["corr-workflow-001"],
    )


class DpmRunWorkflowDecisionResponse(BaseModel):
    decision_id: str = Field(
        description="Workflow decision identifier.",
        examples=["dwd_001"],
    )
    run_id: str = Field(
        description="DPM run identifier associated with workflow decision.",
        examples=["rr_abc12345"],
    )
    action: DpmWorkflowActionType = Field(
        description="Workflow action applied by reviewer.",
        examples=["APPROVE"],
    )
    reason_code: str = Field(
        description="Stable uppercase snake case reason code for the decision.",
        examples=["REVIEW_APPROVED"],
    )
    comment: Optional[str] = Field(
        default=None,
        description="Optional free-text reviewer comment.",
        examples=["Checks passed after review."],
    )
    actor_id: str = Field(
        description="Actor id of reviewer taking workflow action.",
        examples=["reviewer_001"],
    )
    decided_at: str = Field(
        description="Workflow decision timestamp (UTC ISO8601).",
        examples=["2026-02-20T12:00:00+00:00"],
    )
    correlation_id: str = Field(
        description="Correlation id captured for workflow action tracing.",
        examples=["corr-workflow-001"],
    )


class DpmRunWorkflowResponse(BaseModel):
    run_id: str = Field(
        description="DPM run identifier.",
        examples=["rr_abc12345"],
    )
    run_status: str = Field(
        description="Business run status retained from run output.",
        examples=["PENDING_REVIEW"],
    )
    workflow_status: DpmWorkflowStatus = Field(
        description="Current workflow state for reviewer gate decisions.",
        examples=["PENDING_REVIEW"],
    )
    requires_review: bool = Field(
        description="Whether workflow review is required for this run by policy configuration.",
        examples=[True],
    )
    latest_decision: Optional[DpmRunWorkflowDecisionResponse] = Field(
        default=None,
        description="Most recent workflow decision when available.",
        examples=[
            {
                "decision_id": "dwd_001",
                "run_id": "rr_abc12345",
                "action": "APPROVE",
                "reason_code": "REVIEW_APPROVED",
                "comment": "Checks passed after review.",
                "actor_id": "reviewer_001",
                "decided_at": "2026-02-20T12:00:00+00:00",
                "correlation_id": "corr-workflow-001",
            }
        ],
    )


class DpmRunWorkflowHistoryResponse(BaseModel):
    run_id: str = Field(
        description="DPM run identifier.",
        examples=["rr_abc12345"],
    )
    decisions: list[DpmRunWorkflowDecisionResponse] = Field(
        default_factory=list,
        description="Append-only workflow decisions ordered by decision timestamp ascending.",
        examples=[
            [
                {
                    "decision_id": "dwd_001",
                    "run_id": "rr_abc12345",
                    "action": "REQUEST_CHANGES",
                    "reason_code": "REQUIRES_ADVISOR_NOTE",
                    "comment": "Please add rationale.",
                    "actor_id": "reviewer_001",
                    "decided_at": "2026-02-20T12:00:00+00:00",
                    "correlation_id": "corr-workflow-001",
                }
            ]
        ],
    )


class DpmWorkflowDecisionListResponse(BaseModel):
    items: list[DpmRunWorkflowDecisionResponse] = Field(
        default_factory=list,
        description="Filtered workflow decisions ordered by decision timestamp descending.",
        examples=[
            [
                {
                    "decision_id": "dwd_001",
                    "run_id": "rr_abc12345",
                    "action": "APPROVE",
                    "reason_code": "REVIEW_APPROVED",
                    "comment": "Checks passed after review.",
                    "actor_id": "reviewer_001",
                    "decided_at": "2026-02-20T12:00:00+00:00",
                    "correlation_id": "corr-workflow-001",
                }
            ]
        ],
    )
    next_cursor: Optional[str] = Field(
        default=None,
        description="Opaque cursor for retrieving the next result page.",
        examples=["dwd_001"],
    )


class DpmRunWorkflowActionRequest(BaseModel):
    action: DpmWorkflowActionType = Field(
        description="Workflow action to apply to run review lifecycle.",
        examples=["APPROVE"],
    )
    reason_code: str = Field(
        pattern=r"^[A-Z][A-Z0-9_]*$",
        description="Stable uppercase snake case reason code for the action.",
        examples=["REVIEW_APPROVED"],
    )
    comment: Optional[str] = Field(
        default=None,
        description="Optional free-text comment for operational context.",
        examples=["Approved after policy review."],
    )
    actor_id: str = Field(
        description="Actor id executing the workflow action.",
        examples=["reviewer_001"],
    )


class DpmLineageEdgeRecord(BaseModel):
    source_entity_id: str = Field(
        description="Lineage source entity identifier.",
        examples=["corr-1234-abcd"],
    )
    edge_type: DpmLineageEdgeType = Field(
        description="Lineage relation type.",
        examples=["CORRELATION_TO_RUN"],
    )
    target_entity_id: str = Field(
        description="Lineage target entity identifier.",
        examples=["rr_abc12345"],
    )
    created_at: datetime = Field(
        description="Lineage edge creation timestamp (UTC).",
        examples=["2026-02-20T12:00:00+00:00"],
    )
    metadata_json: Dict[str, Any] = Field(
        default_factory=dict,
        description="Optional lineage edge metadata.",
        examples=[{"request_hash": "sha256:abc123"}],
    )


class DpmLineageEdgeResponse(BaseModel):
    source_entity_id: str = Field(
        description="Lineage source entity identifier.",
        examples=["corr-1234-abcd"],
    )
    edge_type: DpmLineageEdgeType = Field(
        description="Lineage relation type.",
        examples=["CORRELATION_TO_RUN"],
    )
    target_entity_id: str = Field(
        description="Lineage target entity identifier.",
        examples=["rr_abc12345"],
    )
    created_at: str = Field(
        description="Lineage edge creation timestamp (UTC ISO8601).",
        examples=["2026-02-20T12:00:00+00:00"],
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Optional lineage edge metadata.",
        examples=[{"request_hash": "sha256:abc123"}],
    )


class DpmLineageResponse(BaseModel):
    entity_id: str = Field(
        description="Requested entity identifier.",
        examples=["corr-1234-abcd"],
    )
    edges: list[DpmLineageEdgeResponse] = Field(
        default_factory=list,
        description="Lineage edges where entity is source or target.",
        examples=[
            [
                {
                    "source_entity_id": "corr-1234-abcd",
                    "edge_type": "CORRELATION_TO_RUN",
                    "target_entity_id": "rr_abc12345",
                    "created_at": "2026-02-20T12:00:00+00:00",
                    "metadata": {"request_hash": "sha256:abc123"},
                }
            ]
        ],
    )
    next_cursor: Optional[str] = Field(
        default=None,
        description="Cursor for the next lineage page when additional rows are available.",
        examples=["2026-02-20T12:00:00+00:00|rr_abc12345"],
    )


class DpmRunArtifactHashes(BaseModel):
    request_hash: str = Field(
        description="Canonical request hash associated with this run artifact.",
        examples=["sha256:abc123"],
    )
    artifact_hash: str = Field(
        description="Canonical deterministic artifact hash.",
        examples=["sha256:def456"],
    )


class DpmRunArtifactEvidence(BaseModel):
    engine_version: str = Field(
        description="Engine version associated with the persisted run output.",
        examples=["0.1.0"],
    )
    run_created_at: str = Field(
        description="Run creation timestamp used as deterministic artifact creation time.",
        examples=["2026-02-20T12:00:00+00:00"],
    )
    hashes: DpmRunArtifactHashes = Field(
        description="Canonical hashes associated with this artifact."
    )


class DpmRunArtifactResponse(BaseModel):
    artifact_id: str = Field(
        description="Deterministic artifact identifier derived from run id.",
        examples=["dra_abc12345"],
    )
    artifact_version: str = Field(
        description="Artifact schema version for compatibility evolution.",
        examples=["1.0"],
    )
    rebalance_run_id: str = Field(description="DPM run identifier.", examples=["rr_abc12345"])
    correlation_id: str = Field(
        description="Correlation identifier associated with this run.",
        examples=["corr-1234-abcd"],
    )
    idempotency_key: Optional[str] = Field(
        default=None,
        description="Idempotency key associated with this run when available.",
        examples=["demo-idem-001"],
    )
    portfolio_id: str = Field(description="Portfolio identifier.", examples=["pf_123"])
    status: str = Field(
        description="Run business status represented by the persisted output.",
        examples=["READY"],
    )
    request_snapshot: Dict[str, Any] = Field(
        description="Deterministic request snapshot metadata captured for replayability.",
        examples=[{"portfolio_id": "pf_123", "request_hash": "sha256:abc123"}],
    )
    before_summary: Dict[str, Any] = Field(
        description="Before-state holdings and valuation summary from run output.",
        examples=[{"total_value_base": {"amount": "10000", "currency": "USD"}}],
    )
    after_summary: Dict[str, Any] = Field(
        description="After-state holdings and valuation summary from run output.",
        examples=[{"total_value_base": {"amount": "10000", "currency": "USD"}}],
    )
    order_intents: list[Dict[str, Any]] = Field(
        default_factory=list,
        description="Order intent list captured in run output.",
        examples=[[{"intent_type": "SECURITY_TRADE", "side": "BUY", "instrument_id": "EQ_1"}]],
    )
    rule_outcomes: list[Dict[str, Any]] = Field(
        default_factory=list,
        description="Rule outcomes captured in run output.",
        examples=[[{"rule_id": "NO_SHORTING", "severity": "HARD", "status": "PASS"}]],
    )
    diagnostics: Dict[str, Any] = Field(
        default_factory=dict,
        description="Diagnostics payload captured in run output.",
        examples=[{"warnings": [], "data_quality": {"price_missing": [], "fx_missing": []}}],
    )
    result: RebalanceResult = Field(
        description="Full persisted DPM run output used as artifact source of truth.",
        examples=[{"rebalance_run_id": "rr_abc12345", "status": "READY"}],
    )
    evidence: DpmRunArtifactEvidence = Field(
        description="Evidence metadata and canonical hash information for the artifact.",
        examples=[
            {
                "engine_version": "0.1.0",
                "run_created_at": "2026-02-20T12:00:00+00:00",
                "hashes": {
                    "request_hash": "sha256:abc123",
                    "artifact_hash": "sha256:def456",
                },
            }
        ],
    )
