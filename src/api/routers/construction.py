from __future__ import annotations

from typing import Annotated, Literal, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Path, status
from pydantic import BaseModel, Field

from src.api.dependencies import get_construction_repository, get_db_session
from src.api.request_models import RebalanceExecutionRequestEnvelope
from src.api.services import construction_service
from src.api.services.rebalance_simulation_service import resolve_rebalance_request_envelope
from src.core.construction.models import (
    ConstructionAlternativeSelection,
    ConstructionAlternativeSet,
)
from src.core.construction.repository import ConstructionRepository
from src.core.construction.vocabulary import ConstructionMethod
from src.core.dpm_source_context import DpmStatefulInput
from src.api.request_models import RebalanceRequest


CONSTRUCTION_ALTERNATIVE_SET_EXAMPLE = {
    "alternative_set_id": "cas_001",
    "portfolio_id": "PB_SG_GLOBAL_BAL_001",
    "as_of": "2026-05-03",
    "status": "PENDING_REVIEW",
    "generated_at": "2026-05-03T08:30:00Z",
    "request_hash": "sha256:example",
    "input_mode": "stateful",
    "source_supportability_state": "READY",
    "alternatives": [
        {
            "alternative_id": "alt_do_nothing_baseline",
            "method": "DO_NOTHING_BASELINE",
            "method_status": "READY",
            "summary": "No-action baseline keeps current holdings unchanged for comparison.",
            "rebalance_run_id": "rr_001",
            "objective_trace": [],
            "constraint_trace": [],
            "comparison_metrics": {
                "drift_before": "0.2500",
                "drift_after": "0.2500",
                "drift_reduction": "0.0000",
                "turnover_weight": "0.0000",
                "trade_count": 0,
                "estimated_transaction_cost": None,
                "cash_weight_after": "0.0500",
            },
            "intent_ids": [],
            "diagnostics": {"warnings": [], "data_quality": {}, "rule_result_count": 0},
        }
    ],
}


class ConstructionAlternativeSetGenerateRequest(BaseModel):
    model_config = {
        "json_schema_extra": {
            "example": {
                "input_mode": "stateless",
                "stateless_input": {
                    "portfolio_snapshot": {
                        "portfolio_id": "PB_SG_GLOBAL_BAL_001",
                        "base_currency": "SGD",
                        "positions": [],
                        "cash_balances": [{"currency": "SGD", "amount": "10000.00"}],
                    },
                    "market_data_snapshot": {
                        "prices": [{"instrument_id": "EQ_1", "price": "100.00", "currency": "SGD"}],
                        "fx_rates": [],
                    },
                    "model_portfolio": {"targets": [{"instrument_id": "EQ_1", "weight": "1.0"}]},
                    "shelf_entries": [{"instrument_id": "EQ_1", "status": "APPROVED"}],
                    "options": {},
                },
                "methods": [
                    "DO_NOTHING_BASELINE",
                    "HEURISTIC_EXPLAINABLE",
                    "MIN_TURNOVER",
                    "TAX_AWARE",
                ],
            }
        }
    }

    input_mode: Literal["stateless", "stateful"] = Field(
        default="stateless",
        description=(
            "Execution input mode. Use `stateless` for complete inline bundles and `stateful` "
            "for governed lotus-core source-data resolution."
        ),
        examples=["stateless"],
    )
    stateless_input: Optional[RebalanceRequest] = Field(
        default=None,
        description="Complete inline execution bundle required when input_mode is `stateless`.",
    )
    stateful_input: Optional[DpmStatefulInput] = Field(
        default=None,
        description="Core source-data selectors required when input_mode is `stateful`.",
    )
    options_override: dict[str, object] = Field(
        default_factory=dict,
        description="Optional engine option overrides applied after stateful source-data resolution.",
    )
    methods: list[ConstructionMethod] | None = Field(
        default=None,
        description=(
            "Optional RFC-0039 first-wave construction methods to generate. Omit for the default "
            "first-wave set. Second-wave methods are governed placeholders and are rejected until "
            "their source authority, supportability, tests, and live proof are complete."
        ),
        examples=[["DO_NOTHING_BASELINE", "HEURISTIC_EXPLAINABLE", "MIN_TURNOVER", "TAX_AWARE"]],
    )

    def to_execution_envelope(self) -> RebalanceExecutionRequestEnvelope:
        return RebalanceExecutionRequestEnvelope(
            input_mode=self.input_mode,
            stateless_input=self.stateless_input,
            stateful_input=self.stateful_input,
            options_override=self.options_override,
        )


class ConstructionAlternativeSelectionRequest(BaseModel):
    alternative_id: str = Field(
        description="Alternative identifier selected by the portfolio manager or workflow actor.",
        examples=["alt_min_turnover"],
    )
    actor_id: str = Field(
        description="Human or service actor recording the selection decision.",
        examples=["pm_001"],
    )
    reason_code: str = Field(
        description="Bounded business reason for selecting the alternative.",
        examples=["LOWER_TURNOVER_WITH_ACCEPTABLE_DRIFT"],
    )
    comment: Optional[str] = Field(
        default=None,
        description="Optional selection note for audit and review.",
        examples=["Chosen for lower turnover before month-end execution window."],
    )


router = APIRouter(
    prefix="/construction/alternative-sets",
    tags=["lotus-manage Construction Alternatives"],
)


@router.post(
    "/generate",
    response_model=ConstructionAlternativeSet,
    status_code=status.HTTP_200_OK,
    summary="Generate portfolio construction alternatives",
    description=(
        "Generates an auditable set of discretionary portfolio construction alternatives for a "
        "single mandate context. Use this endpoint when a PM, command center, or governed workflow "
        "needs a no-action baseline plus comparable rebalance alternatives before selecting a "
        "preferred implementation path. Required header: `Idempotency-Key`."
    ),
    responses={
        200: {
            "description": "Construction alternatives generated or replayed idempotently.",
            "content": {"application/json": {"example": CONSTRUCTION_ALTERNATIVE_SET_EXAMPLE}},
        },
        409: {"description": "Idempotency key conflict for a different request hash."},
        422: {"description": "Requested construction method is not yet supported."},
        424: {"description": "Stateful core source context was incomplete."},
        503: {"description": "Stateful core source resolver was unavailable."},
    },
)
def generate_alternative_set(
    request: ConstructionAlternativeSetGenerateRequest,
    idempotency_key: Annotated[
        str,
        Header(
            description="Required idempotency token for alternative-set replay.",
            examples=["construction-idem-001"],
        ),
    ],
    x_correlation_id: Annotated[
        Optional[str],
        Header(
            description="Optional trace/correlation identifier propagated to source resolution.",
            examples=["corr-construction-001"],
        ),
    ] = None,
    repository: ConstructionRepository = Depends(get_construction_repository),
    db: Annotated[None, Depends(get_db_session)] = None,
) -> ConstructionAlternativeSet:
    rebalance_request, source_context = resolve_rebalance_request_envelope(
        envelope=request.to_execution_envelope(),
        correlation_id=x_correlation_id,
    )
    try:
        return construction_service.generate_construction_alternative_set(
            request=rebalance_request,
            idempotency_key=idempotency_key,
            correlation_id=x_correlation_id,
            repository=repository,
            methods=request.methods,
            source_context=source_context,
        )
    except Exception as exc:
        raise construction_service.to_api_http_exception(exc) from exc


@router.get(
    "/{alternative_set_id}",
    response_model=ConstructionAlternativeSet,
    summary="Get a construction alternative set",
    description=(
        "Returns a previously generated construction alternative set by identifier. Use this "
        "read model for audit, replay, command-center comparison, and downstream presentation "
        "without recomputing portfolio construction results."
    ),
    responses={
        200: {
            "description": "Construction alternative set.",
            "content": {"application/json": {"example": CONSTRUCTION_ALTERNATIVE_SET_EXAMPLE}},
        },
        404: {"description": "Alternative set was not found."},
    },
)
def read_alternative_set(
    alternative_set_id: Annotated[
        str,
        Path(description="Construction alternative set identifier.", examples=["cas_001"]),
    ],
    repository: ConstructionRepository = Depends(get_construction_repository),
) -> ConstructionAlternativeSet:
    try:
        return construction_service.get_construction_alternative_set(
            repository=repository,
            alternative_set_id=alternative_set_id,
        )
    except Exception as exc:
        raise construction_service.to_api_http_exception(exc) from exc


@router.post(
    "/{alternative_set_id}/selections",
    response_model=ConstructionAlternativeSelection,
    status_code=status.HTTP_200_OK,
    summary="Select a construction alternative",
    description=(
        "Records the selected construction alternative for an alternative set. Use this endpoint "
        "after a PM, supervisor, or orchestration workflow chooses the preferred rebalance path. "
        "The selection is persisted as an auditable decision, not executed as an order."
    ),
    responses={
        200: {"description": "Selection recorded."},
        404: {"description": "Alternative set or alternative id was not found."},
    },
)
def select_alternative(
    alternative_set_id: Annotated[
        str,
        Path(description="Construction alternative set identifier.", examples=["cas_001"]),
    ],
    request: ConstructionAlternativeSelectionRequest,
    x_correlation_id: Annotated[
        Optional[str],
        Header(
            description="Optional trace/correlation identifier for the selection decision.",
            examples=["corr-selection-001"],
        ),
    ] = None,
    repository: ConstructionRepository = Depends(get_construction_repository),
) -> ConstructionAlternativeSelection:
    try:
        return construction_service.select_construction_alternative(
            repository=repository,
            alternative_set_id=alternative_set_id,
            alternative_id=request.alternative_id,
            actor_id=request.actor_id,
            reason_code=request.reason_code,
            comment=request.comment,
            correlation_id=x_correlation_id,
        )
    except Exception as exc:
        http_exc = construction_service.to_api_http_exception(exc)
        raise HTTPException(status_code=http_exc.status_code, detail=http_exc.detail) from exc
