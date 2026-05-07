from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Annotated, Literal, cast

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, Field

from src.api.observability import record_wave_supportability
from src.api.dependencies import (
    get_construction_repository,
    get_mandate_repository,
    get_proof_pack_repository,
    get_risk_authority_client,
    get_wave_repository,
)
from src.api.request_models import RebalanceRequest
from src.api.routers.rebalance_runs import get_dpm_run_support_service
from src.api.services.rebalance_simulation_service import build_core_resolver_client
from src.api.services import wave_service
from src.core.construction.models import ConstructionAuthorityContext
from src.core.construction.repository import ConstructionRepository
from src.core.construction.vocabulary import ConstructionMethod
from src.core.mandate_repository import DpmMandateRepository
from src.core.proof_packs.repository import DpmProofPackRepository
from src.core.rebalance_runs.service import DpmRunSupportService
from src.core.waves import (
    DpmRebalanceWave,
    DpmWaveReportInput,
    DpmWaveRepository,
    DpmWaveSourceRef,
)
from src.infrastructure.core_sourcing import DpmCoreResolverError, DpmCoreResolverUnavailableError
from src.infrastructure.risk_authority import LotusRiskAuthorityClient
from src.core.waves.models import (
    DpmRebalanceWaveItem,
    DpmWaveAggregateMetrics,
    DpmWaveHandoffRef,
)


WAVE_EXAMPLE = {
    "wave": {
        "wave_id": "dwv_001",
        "wave_version": "1.0.0",
        "state": "PREVIEWED",
        "trigger": {
            "trigger_type": "EXPLICIT_PORTFOLIO_LIST",
            "trigger_id": "manual-wave-20260503-001",
            "rationale": "Review explicitly selected portfolios after model drift triage.",
            "source_refs": [],
        },
        "as_of_date": "2026-05-03",
        "created_at": "2026-05-03T09:30:00Z",
        "created_by": "pm_001",
        "correlation_id": "corr-wave-001",
        "version": 2,
        "items": [
            {
                "wave_item_id": "dwi_001",
                "portfolio_id": "PB_SG_GLOBAL_BAL_001",
                "mandate_id": "MANDATE_PB_SG_GLOBAL_BAL_001",
                "state": "CANDIDATE",
                "reason_codes": ["AFFECTED_PORTFOLIO_SOURCE_READY"],
                "source_refs": [
                    {
                        "source_system": "lotus-manage",
                        "source_type": "AFFECTED_PORTFOLIO_MANIFEST",
                        "source_id": "manifest_20260503_001",
                        "source_version": "1.0.0",
                        "supportability_state": "READY",
                        "content_hash": "sha256:manifest-example",
                    }
                ],
                "diagnostics": {"source_posture": "candidate_evidence_available"},
            }
        ],
        "aggregate_metrics": {
            "item_count": 1,
            "state_counts": {"CANDIDATE": 1},
            "ready_item_count": 0,
            "blocked_item_count": 0,
            "review_required_item_count": 0,
            "source_degraded_item_count": 0,
        },
        "events": [],
        "retention_policy": "DPM_WAVE_STANDARD",
    },
    "durable": False,
    "idempotent_replay": False,
}

SOURCE_CHECK_WAVE_EXAMPLE = {
    "wave": {
        **cast(dict[str, object], WAVE_EXAMPLE["wave"]),
        "state": "SOURCE_CHECKED",
        "version": 4,
        "items": [
            {
                "wave_item_id": "dwi_001",
                "portfolio_id": "PB_SG_GLOBAL_BAL_001",
                "mandate_id": "MANDATE_PB_SG_GLOBAL_BAL_001",
                "model_portfolio_id": "MODEL_PB_SG_GLOBAL_BAL_DPM",
                "state": "SOURCE_READY",
                "reason_codes": ["SOURCE_READINESS_READY"],
                "source_refs": [
                    {
                        "source_system": "lotus-manage",
                        "source_type": "MANDATE_DIGITAL_TWIN",
                        "source_id": "MANDATE_PB_SG_GLOBAL_BAL_001",
                        "source_version": "3",
                        "supportability_state": "READY",
                    },
                    {
                        "source_system": "lotus-manage",
                        "source_type": "DPM_MANDATE_HEALTH_SNAPSHOT",
                        "source_id": "mh_20260503_pb_sg_global_bal_001",
                        "source_version": "2026-05-03",
                        "supportability_state": "READY",
                    },
                    {
                        "source_system": "lotus-manage",
                        "source_type": "DPM_SOURCE_READINESS",
                        "source_id": "mh_20260503_pb_sg_global_bal_001",
                        "source_version": "2026-05-03",
                        "supportability_state": "READY",
                    },
                ],
                "diagnostics": {
                    "source_owner": "lotus-manage",
                    "health_state": "READY",
                    "source_readiness_state": "READY",
                },
            }
        ],
        "aggregate_metrics": {
            "item_count": 1,
            "state_counts": {"SOURCE_READY": 1},
            "ready_item_count": 1,
            "blocked_item_count": 0,
            "review_required_item_count": 0,
            "source_degraded_item_count": 0,
        },
    },
    "durable": True,
    "idempotent_replay": False,
}


class DpmWavePortfolioInput(BaseModel):
    portfolio_id: str = Field(
        description="Explicit affected portfolio identifier.",
        examples=["PB_SG_GLOBAL_BAL_001"],
    )
    mandate_id: str | None = Field(
        default=None,
        description="Known mandate id from reviewed source evidence, when supplied.",
        examples=["MANDATE_PB_SG_GLOBAL_BAL_001"],
    )
    source_refs: list[DpmWaveSourceRef] = Field(
        default_factory=list,
        description=(
            "Source refs proving why this portfolio belongs in the affected set. When omitted, "
            "manage attempts to attach an existing mandate digital-twin ref; otherwise the item "
            "is blocked rather than treated as source-ready."
        ),
    )


class DpmWavePreviewRequest(BaseModel):
    trigger_type: Literal[
        "EXPLICIT_PORTFOLIO_LIST",
        "PM_BOOK_REVIEW",
        "CIO_MODEL_CHANGE",
        "TACTICAL_HOUSE_VIEW",
        "RISK_EVENT",
        "BULK_REVIEW_CAMPAIGN",
    ] = Field(description="Wave trigger type.", examples=["EXPLICIT_PORTFOLIO_LIST"])
    trigger_id: str = Field(description="Business trigger identifier.", examples=["manual-001"])
    rationale: str = Field(
        description="Business rationale for reviewing the affected portfolio set.",
        examples=["Review explicit portfolio list after CIO desk model-change triage."],
    )
    as_of_date: str = Field(description="Business as-of date.", examples=["2026-05-03"])
    actor_id: str = Field(description="Human or service actor.", examples=["pm_001"])
    portfolios: list[DpmWavePortfolioInput] = Field(
        default_factory=list,
        description="Explicit affected portfolios for the first supported RFC-0041 trigger.",
        examples=[
            [
                {
                    "portfolio_id": "PB_SG_GLOBAL_BAL_001",
                    "mandate_id": "MANDATE_PB_SG_GLOBAL_BAL_001",
                    "source_refs": [
                        {
                            "source_system": "lotus-manage",
                            "source_type": "AFFECTED_PORTFOLIO_MANIFEST",
                            "source_id": "manifest_20260503_001",
                            "source_version": "1.0.0",
                            "supportability_state": "READY",
                        }
                    ],
                }
            ]
        ],
    )
    portfolio_manager_id: str | None = Field(
        default=None,
        description=(
            "Required for `PM_BOOK_REVIEW`. Manage resolves the affected cohort from the "
            "lotus-core `PortfolioManagerBookMembership:v1` source product."
        ),
        examples=["PM_SG_DPM_001"],
    )
    tenant_id: str | None = Field(
        default=None,
        description="Optional tenant selector forwarded to the PM-book source product.",
        examples=["default"],
    )
    booking_center_code: str | None = Field(
        default=None,
        description="Optional booking-center filter for PM-book discovery.",
        examples=["Singapore"],
    )
    portfolio_types: list[str] = Field(
        default_factory=lambda: ["DISCRETIONARY"],
        description="PM-book portfolio types eligible for automatic wave discovery.",
        examples=[["DISCRETIONARY"]],
    )


class DpmWaveResponse(BaseModel):
    wave: DpmRebalanceWave = Field(description="Previewed or durable rebalance wave.")
    durable: bool = Field(
        description="Whether this response was durably persisted.", examples=[False]
    )
    supportability: "DpmWaveSupportabilityResponse" = Field(
        description=(
            "Product-safe wave supportability derived by lotus-manage from item states. "
            "Gateway and Workbench must preserve this authority-owned posture instead of "
            "reconstructing readiness."
        )
    )
    idempotent_replay: bool = Field(
        default=False,
        description="True when create returned an already persisted wave for the idempotency key.",
        examples=[False],
    )


class DpmWaveSearchItem(BaseModel):
    wave_id: str = Field(description="Wave identifier.", examples=["dwv_001"])
    wave_state: str = Field(description="Current wave state.", examples=["HANDOFF_READY"])
    trigger_type: str = Field(
        description="Bounded trigger type used to create the wave.",
        examples=["EXPLICIT_PORTFOLIO_LIST"],
    )
    trigger_id: str = Field(description="Business trigger identifier.", examples=["manual-001"])
    as_of_date: str = Field(description="Business as-of date.", examples=["2026-05-03"])
    created_at: datetime = Field(
        description="UTC timestamp when the wave was created.",
        examples=["2026-05-03T09:30:00Z"],
    )
    created_by: str = Field(description="Actor that created the wave.", examples=["pm_001"])
    item_count: int = Field(description="Number of wave items.", examples=[2])
    aggregate_metrics: DpmWaveAggregateMetrics = Field(
        description="Aggregate item counts reconciled from persisted wave state."
    )
    supportability_state: Literal["ready", "degraded", "blocked"] = Field(
        description="Product-safe supportability posture for search and triage.",
        examples=["ready"],
    )
    supportability_reason: str = Field(
        description="Bounded reason for the supportability state.",
        examples=["wave_supportability_ready"],
    )
    latest_event_type: str | None = Field(
        default=None,
        description="Latest persisted event type for operator context.",
        examples=["STATE_TRANSITION"],
    )
    latest_event_reason_code: str | None = Field(
        default=None,
        description="Latest persisted event reason code for operator context.",
        examples=["WAVE_HANDOFF_READY"],
    )


class DpmWaveSearchResponse(BaseModel):
    items: list[DpmWaveSearchItem] = Field(
        description="Bounded page of persisted waves matching the search filters."
    )
    limit: int = Field(description="Requested page size.", examples=[50])
    offset: int = Field(description="Requested page offset.", examples=[0])
    returned_count: int = Field(description="Number of waves returned.", examples=[1])


class DpmWaveSourceCheckRequest(BaseModel):
    actor_id: str = Field(
        description="Human or service actor requesting the source-check.",
        examples=["pm_001"],
    )


class DpmWaveSimulationItemInput(BaseModel):
    wave_item_id: str | None = Field(
        default=None,
        description="Wave item id receiving this construction input.",
        examples=["dwi_001"],
    )
    portfolio_id: str | None = Field(
        default=None,
        description="Portfolio id fallback when the caller does not know the wave item id.",
        examples=["PB_SG_GLOBAL_BAL_001"],
    )
    stateless_input: RebalanceRequest = Field(
        description=(
            "Complete RFC-0039 stateless construction input for this ready item. "
            "Wave simulation does not synthesize holdings, market data, or shelf data."
        )
    )
    authority_context: ConstructionAuthorityContext | None = Field(
        default=None,
        description=(
            "Optional source-backed risk/performance authority context for this item. "
            "Risk context may also be resolved from lotus-risk when `DPM_RISK_BASE_URL` is "
            "configured and `RISK_AWARE` is requested; performance context must be supplied "
            "from lotus-performance until a dedicated manage performance client is promoted."
        ),
    )


class DpmWaveSimulationRequest(BaseModel):
    actor_id: str = Field(
        description="Human or service actor requesting wave simulation.",
        examples=["pm_001"],
    )
    item_inputs: list[DpmWaveSimulationItemInput] = Field(
        default_factory=list,
        description="Per-item RFC-0039 construction inputs for source-ready items.",
    )
    methods: list[ConstructionMethod] | None = Field(
        default=None,
        description="Optional RFC-0039 construction methods. Omit for the first-wave default.",
        examples=[["DO_NOTHING_BASELINE", "HEURISTIC_EXPLAINABLE", "MIN_TURNOVER"]],
    )


class DpmWaveSelectionRequest(BaseModel):
    alternative_id: str = Field(
        description="Construction alternative id selected for the wave item.",
        examples=["alt_min_turnover"],
    )
    actor_id: str = Field(
        description="Human or service actor recording the selection.",
        examples=["pm_001"],
    )
    reason_code: str = Field(
        description="Bounded reason code explaining the selection.",
        examples=["LOWER_TURNOVER_WITH_ACCEPTABLE_DRIFT"],
    )
    comment: str | None = Field(
        default=None,
        description="Optional business comment for audit.",
        examples=["Chosen before month-end liquidity window."],
    )
    generate_proof_pack: bool = Field(
        default=True,
        description=(
            "When true, generate an RFC-0040 proof pack from the selected alternative. "
            "Failures degrade the item rather than fabricating proof-pack readiness."
        ),
        examples=[True],
    )


class DpmWaveWorkflowCommandRequest(BaseModel):
    actor_id: str = Field(
        description="Human or service actor applying the workflow command.",
        examples=["pm_001"],
    )
    reason_code: str = Field(
        description="Bounded business reason code for the workflow command.",
        examples=["READY_FOR_OPERATIONS_REVIEW"],
    )
    comment: str | None = Field(
        default=None,
        description="Optional business comment for audit.",
        examples=["Approved after proof-pack review."],
    )


class DpmWaveSupportabilityIssue(BaseModel):
    support_ref: str = Field(
        description="Opaque support reference that avoids portfolio or client identifiers.",
        examples=["wave:dwv_001:item:1"],
    )
    item_state: str = Field(description="Wave item workflow state.", examples=["SOURCE_BLOCKED"])
    severity: Literal["INFO", "WARNING", "CRITICAL"] = Field(
        description="Operator severity for this issue.",
        examples=["CRITICAL"],
    )
    source_owner: str = Field(
        description="Owning product or route responsible for remediation.",
        examples=["lotus-manage"],
    )
    reason_codes: list[str] = Field(
        description="Bounded reason codes explaining supportability posture.",
        examples=[["MANDATE_DIGITAL_TWIN_MISSING"]],
    )
    remediation_route: str = Field(
        description="Product-safe remediation route or action.",
        examples=["REPAIR_SOURCE_DATA"],
    )


class DpmWaveSupportabilityResponse(BaseModel):
    wave_id: str = Field(description="Wave identifier.", examples=["dwv_001"])
    wave_state: str = Field(description="Current wave state.", examples=["SOURCE_CHECKED"])
    supportability_state: Literal["ready", "degraded", "blocked"] = Field(
        description="Bounded supportability state for the wave.",
        examples=["blocked"],
    )
    reason: str = Field(
        description="Bounded supportability reason.",
        examples=["wave_blocked_items"],
    )
    item_count: int = Field(description="Number of wave items inspected.", examples=[2])
    issue_counts: dict[str, int] = Field(
        description="Issue count by severity.",
        examples=[{"critical": 1, "warning": 0, "info": 1}],
    )
    issues: list[DpmWaveSupportabilityIssue] = Field(
        description=(
            "Product-safe issues without portfolio ids, client ids, raw requests, raw responses, "
            "secrets, or trace values."
        )
    )
    operator_actions: list[str] = Field(
        description="Deduplicated product-safe remediation actions.",
        examples=[["REPAIR_SOURCE_DATA", "RUN_WAVE_SIMULATION"]],
    )


class DpmWaveDetailResponse(BaseModel):
    wave: DpmRebalanceWave = Field(description="Persisted wave detail.")
    supportability: DpmWaveSupportabilityResponse = Field(
        description="Latest product-safe supportability derived from persisted item states."
    )
    proof_pack_posture: "DpmWaveProofPackPostureResponse" = Field(
        description="Wave proof-pack and internal operations handoff posture."
    )


class DpmWaveItemsResponse(BaseModel):
    wave_id: str = Field(description="Wave identifier.", examples=["dwv_001"])
    wave_state: str = Field(description="Current wave state.", examples=["HANDOFF_READY"])
    items: list[DpmRebalanceWaveItem] = Field(
        description="Persisted item list with source readiness, selection, proof-pack, and handoff posture."
    )
    aggregate_metrics: DpmWaveAggregateMetrics = Field(
        description="Aggregate item counts reconciled from persisted wave state."
    )


class DpmWaveProofPackRef(BaseModel):
    wave_item_id: str = Field(description="Wave item identifier.", examples=["dwi_001"])
    proof_pack_id: str | None = Field(
        default=None,
        description="Linked RFC-0040 proof-pack id when generated.",
        examples=["dpp_001"],
    )
    item_state: str = Field(description="Current item state.", examples=["PROOF_PACK_READY"])
    proof_pack_state: str | None = Field(
        default=None,
        description="Proof-pack posture captured in item diagnostics.",
        examples=["READY"],
    )
    selected_alternative_id: str | None = Field(
        default=None,
        description="Selected RFC-0039 construction alternative id.",
        examples=["alt_min_turnover"],
    )


class DpmWaveProofPackPostureResponse(BaseModel):
    wave_id: str = Field(description="Wave identifier.", examples=["dwv_001"])
    wave_state: str = Field(description="Current wave state.", examples=["HANDOFF_READY"])
    item_count: int = Field(description="Total item count.", examples=[2])
    linked_item_count: int = Field(description="Items with linked proof packs.", examples=[1])
    ready_proof_pack_count: int = Field(
        description="Linked proof packs that are not degraded.", examples=[1]
    )
    degraded_proof_pack_count: int = Field(
        description="Items with degraded proof-pack posture.", examples=[0]
    )
    proof_pack_refs: list[DpmWaveProofPackRef] = Field(
        description="Item-level proof-pack references and posture."
    )
    handoff_refs: list[DpmWaveHandoffRef] = Field(
        description="Append-only internal operations handoff evidence refs."
    )
    external_execution_claimed: bool = Field(
        description="True only if any handoff ref claims external execution; expected false.",
        examples=[False],
    )


router = APIRouter(prefix="/rebalance/waves", tags=["lotus-manage Rebalance Waves"])
logger = logging.getLogger(__name__)


def _wave_response(
    *,
    wave: DpmRebalanceWave,
    durable: bool,
    idempotent_replay: bool = False,
) -> DpmWaveResponse:
    return DpmWaveResponse(
        wave=wave,
        durable=durable,
        supportability=DpmWaveSupportabilityResponse.model_validate(
            wave_service.wave_supportability_payload(wave)
        ),
        idempotent_replay=idempotent_replay,
    )


def _portfolio_inputs_for_request(
    *,
    request: DpmWavePreviewRequest,
    correlation_id: str,
) -> list[dict[str, object]]:
    if request.trigger_type == "EXPLICIT_PORTFOLIO_LIST":
        return [portfolio.model_dump(mode="json") for portfolio in request.portfolios]
    if request.trigger_type == "PM_BOOK_REVIEW":
        return _resolve_pm_book_portfolios(request=request, correlation_id=correlation_id)
    return [portfolio.model_dump(mode="json") for portfolio in request.portfolios]


def _resolve_pm_book_portfolios(
    *,
    request: DpmWavePreviewRequest,
    correlation_id: str,
) -> list[dict[str, object]]:
    if request.portfolios:
        raise wave_service.DpmWaveValidationError(
            "PM_BOOK_REVIEW_REJECTS_CALLER_PORTFOLIOS",
            "PM_BOOK_REVIEW resolves the affected portfolio set from lotus-core.",
        )
    portfolio_manager_id = (request.portfolio_manager_id or "").strip()
    if not portfolio_manager_id:
        raise wave_service.DpmWaveValidationError(
            "PM_BOOK_REVIEW_PORTFOLIO_MANAGER_REQUIRED",
            "PM_BOOK_REVIEW requires portfolio_manager_id.",
        )
    try:
        as_of_date = date.fromisoformat(request.as_of_date)
    except ValueError as exc:
        raise wave_service.DpmWaveValidationError(
            "INVALID_AS_OF_DATE",
            "as_of_date must be an ISO date.",
        ) from exc
    portfolio_types = [value.strip().upper() for value in request.portfolio_types if value.strip()]
    if not portfolio_types:
        raise wave_service.DpmWaveValidationError(
            "PM_BOOK_REVIEW_PORTFOLIO_TYPES_REQUIRED",
            "PM_BOOK_REVIEW requires at least one portfolio type.",
        )
    try:
        membership = build_core_resolver_client().resolve_portfolio_manager_book_membership(
            portfolio_manager_id=portfolio_manager_id,
            as_of_date=as_of_date,
            tenant_id=request.tenant_id,
            booking_center_code=request.booking_center_code,
            portfolio_types=portfolio_types,
            include_inactive=False,
            correlation_id=correlation_id,
        )
    except DpmCoreResolverUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": str(exc) or "DPM_CORE_PM_BOOK_MEMBERSHIP_UNAVAILABLE"},
        ) from exc
    except DpmCoreResolverError as exc:
        raise HTTPException(
            status_code=status.HTTP_424_FAILED_DEPENDENCY,
            detail={"code": str(exc) or "DPM_CORE_PM_BOOK_MEMBERSHIP_INCOMPLETE"},
        ) from exc
    if membership.supportability.state != "READY":
        raise HTTPException(
            status_code=status.HTTP_424_FAILED_DEPENDENCY,
            detail={
                "code": membership.supportability.reason,
                "message": "PM-book membership is not source-ready.",
            },
        )
    if not membership.members:
        raise HTTPException(
            status_code=status.HTTP_424_FAILED_DEPENDENCY,
            detail={
                "code": "DPM_CORE_PM_BOOK_MEMBERSHIP_EMPTY",
                "message": "PM-book membership returned no affected portfolios.",
            },
        )
    source_id = (
        membership.snapshot_id
        or membership.source_batch_fingerprint
        or f"pm_book:{membership.portfolio_manager_id}:{membership.as_of_date.isoformat()}"
    )
    book_ref = {
        "source_system": "lotus-core",
        "source_type": "PortfolioManagerBookMembership",
        "source_id": source_id,
        "source_version": membership.product_version,
        "supportability_state": membership.supportability.state,
        "content_hash": membership.source_batch_fingerprint,
    }
    return [
        {
            "portfolio_id": member.portfolio_id,
            "source_refs": [
                book_ref,
                {
                    "source_system": "lotus-core",
                    "source_type": "PORTFOLIO_MANAGER_BOOK_MEMBER",
                    "source_id": member.source_record_id or member.portfolio_id,
                    "source_version": membership.as_of_date.isoformat(),
                    "supportability_state": "READY",
                },
            ],
        }
        for member in membership.members
    ]


@router.post(
    "/preview",
    response_model=DpmWaveResponse,
    status_code=status.HTTP_200_OK,
    summary="Preview an affected-portfolio rebalance wave",
    description=(
        "Builds a non-durable RFC-0041 affected-portfolio wave preview. "
        "`EXPLICIT_PORTFOLIO_LIST` preserves source refs from the request or existing mandate "
        "digital twins. `PM_BOOK_REVIEW` resolves the cohort from the lotus-core "
        "`PortfolioManagerBookMembership:v1` source product. Unsupported trigger types remain "
        "blocked; the endpoint does not perform CIO impact discovery, simulation, approval, "
        "staging, or operations handoff."
    ),
    responses={
        200: {
            "description": "Non-durable wave preview with explicit candidate and blocked states.",
            "content": {"application/json": {"example": WAVE_EXAMPLE}},
        },
        422: {
            "description": "Unsupported trigger or invalid request.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": {
                            "code": "NOT_SUPPORTED_TRIGGER",
                            "message": "Trigger type CIO_MODEL_CHANGE is not supported.",
                        }
                    }
                }
            },
        },
    },
)
def preview_wave(
    request: DpmWavePreviewRequest,
    x_correlation_id: Annotated[
        str | None,
        Header(
            description="Optional correlation id for supportability.", examples=["corr-wave-001"]
        ),
    ] = None,
    mandate_repository: DpmMandateRepository = Depends(get_mandate_repository),
) -> DpmWaveResponse:
    correlation_id = x_correlation_id or f"corr_wave_preview_{request.trigger_id}"
    try:
        portfolios = _portfolio_inputs_for_request(request=request, correlation_id=correlation_id)
        wave = wave_service.preview_wave(
            trigger_type=request.trigger_type,
            trigger_id=request.trigger_id,
            rationale=request.rationale,
            as_of_date=request.as_of_date,
            actor_id=request.actor_id,
            correlation_id=correlation_id,
            portfolios=portfolios,
            mandate_repository=mandate_repository,
        )
    except wave_service.DpmWaveValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    return _wave_response(wave=wave, durable=False)


@router.post(
    "",
    response_model=DpmWaveResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a durable affected-portfolio rebalance wave",
    description=(
        "Creates a durable RFC-0041 rebalance wave. `EXPLICIT_PORTFOLIO_LIST` uses caller-supplied "
        "affected portfolios, while `PM_BOOK_REVIEW` resolves the cohort from lotus-core "
        "`PortfolioManagerBookMembership:v1` before persistence. Required header: "
        "`Idempotency-Key`. Unsupported trigger types are rejected and missing source evidence "
        "produces blocked items, not false readiness."
    ),
    responses={
        201: {
            "description": "Durable wave created.",
            "content": {"application/json": {"example": {**WAVE_EXAMPLE, "durable": True}}},
        },
        409: {
            "description": "Wave identity or idempotency conflict.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": {
                            "code": "WAVE_CREATE_CONFLICT",
                            "message": "DPM_WAVE_IDEMPOTENCY_CONFLICT",
                        }
                    }
                }
            },
        },
        422: {
            "description": "Unsupported trigger or invalid request.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": {
                            "code": "NOT_SUPPORTED_TRIGGER",
                            "message": "Trigger type PM_BOOK_REVIEW is not supported.",
                        }
                    }
                }
            },
        },
    },
)
def create_wave(
    request: DpmWavePreviewRequest,
    idempotency_key: Annotated[
        str,
        Header(
            description="Required idempotency token for durable wave create.",
            examples=["wave-idem-001"],
        ),
    ],
    x_correlation_id: Annotated[
        str | None,
        Header(
            description="Optional correlation id for supportability.", examples=["corr-wave-001"]
        ),
    ] = None,
    mandate_repository: DpmMandateRepository = Depends(get_mandate_repository),
    wave_repository: DpmWaveRepository = Depends(get_wave_repository),
) -> DpmWaveResponse:
    correlation_id = x_correlation_id or f"corr_wave_create_{request.trigger_id}"
    try:
        portfolios = _portfolio_inputs_for_request(request=request, correlation_id=correlation_id)
        wave, replayed = wave_service.create_wave(
            trigger_type=request.trigger_type,
            trigger_id=request.trigger_id,
            rationale=request.rationale,
            as_of_date=request.as_of_date,
            actor_id=request.actor_id,
            correlation_id=correlation_id,
            portfolios=portfolios,
            idempotency_key=idempotency_key,
            mandate_repository=mandate_repository,
            wave_repository=wave_repository,
        )
    except wave_service.DpmWaveValidationError as exc:
        status_code = (
            status.HTTP_409_CONFLICT
            if exc.code == "WAVE_CREATE_CONFLICT"
            else status.HTTP_422_UNPROCESSABLE_CONTENT
        )
        raise HTTPException(
            status_code=status_code,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    return _wave_response(wave=wave, durable=True, idempotent_replay=replayed)


@router.get(
    "",
    response_model=DpmWaveSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Search durable rebalance waves",
    description=(
        "Returns a bounded search page over durable RFC-0041 waves. Search reads persisted manage "
        "wave truth and derives supportability from item states; it does not recalculate source "
        "readiness, construction alternatives, proof-pack state, or handoff posture."
    ),
    responses={
        200: {
            "description": "Bounded search page of durable waves.",
            "content": {
                "application/json": {
                    "example": {
                        "items": [
                            {
                                "wave_id": "dwv_001",
                                "wave_state": "HANDOFF_READY",
                                "trigger_type": "EXPLICIT_PORTFOLIO_LIST",
                                "trigger_id": "manual-wave-001",
                                "as_of_date": "2026-05-03",
                                "created_at": "2026-05-03T09:30:00Z",
                                "created_by": "pm_001",
                                "item_count": 1,
                                "aggregate_metrics": {
                                    "item_count": 1,
                                    "state_counts": {"HANDOFF_READY": 1},
                                    "ready_item_count": 1,
                                    "blocked_item_count": 0,
                                    "review_required_item_count": 0,
                                    "source_degraded_item_count": 0,
                                },
                                "supportability_state": "ready",
                                "supportability_reason": "wave_supportability_ready",
                                "latest_event_type": "STATE_TRANSITION",
                                "latest_event_reason_code": "WAVE_HANDOFF_READY",
                            }
                        ],
                        "limit": 50,
                        "offset": 0,
                        "returned_count": 1,
                    }
                }
            },
        }
    },
)
def search_waves(
    state: Annotated[
        str | None,
        Query(
            description="Optional wave state filter, for example HANDOFF_READY.",
            examples=["HANDOFF_READY"],
        ),
    ] = None,
    trigger_type: Annotated[
        str | None,
        Query(
            description="Optional trigger type filter.",
            examples=["EXPLICIT_PORTFOLIO_LIST"],
        ),
    ] = None,
    as_of_date: Annotated[
        str | None,
        Query(description="Optional business as-of date filter.", examples=["2026-05-03"]),
    ] = None,
    supportability_state: Annotated[
        Literal["ready", "degraded", "blocked"] | None,
        Query(
            description="Optional derived supportability filter.",
            examples=["ready"],
        ),
    ] = None,
    limit: Annotated[
        int,
        Query(ge=1, le=100, description="Maximum number of waves to return.", examples=[50]),
    ] = 50,
    offset: Annotated[
        int,
        Query(ge=0, description="Zero-based page offset.", examples=[0]),
    ] = 0,
    wave_repository: DpmWaveRepository = Depends(get_wave_repository),
) -> DpmWaveSearchResponse:
    items = wave_service.search_waves(
        wave_repository=wave_repository,
        state=state,
        trigger_type=trigger_type,
        as_of_date=as_of_date,
        supportability_state=supportability_state,
        limit=limit,
        offset=offset,
    )
    return DpmWaveSearchResponse(
        items=[DpmWaveSearchItem.model_validate(item) for item in items],
        limit=limit,
        offset=offset,
        returned_count=len(items),
    )


@router.get(
    "/{wave_id}",
    response_model=DpmWaveDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve durable rebalance wave detail",
    description=(
        "Returns one persisted RFC-0041 wave with items, aggregate metrics, events, source refs, "
        "latest supportability, and proof-pack/handoff posture. The endpoint reads durable manage "
        "state and does not regenerate downstream construction or proof-pack artifacts."
    ),
    responses={
        200: {"description": "Persisted wave detail."},
        404: {"description": "Wave not found."},
    },
)
def get_wave_detail(
    wave_id: str,
    wave_repository: DpmWaveRepository = Depends(get_wave_repository),
) -> DpmWaveDetailResponse:
    try:
        payload = wave_service.retrieve_wave_detail(
            wave_id=wave_id,
            wave_repository=wave_repository,
        )
    except wave_service.DpmWaveLookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    return DpmWaveDetailResponse.model_validate(payload)


@router.get(
    "/{wave_id}/items",
    response_model=DpmWaveItemsResponse,
    status_code=status.HTTP_200_OK,
    summary="List rebalance wave items",
    description=(
        "Returns persisted item-level wave posture for source readiness, construction selection, "
        "proof-pack linkage, and internal operations handoff. The response is intended for Gateway "
        "and Workbench command-center realization without UI-side recomputation."
    ),
    responses={
        200: {"description": "Persisted wave item list."},
        404: {"description": "Wave not found."},
    },
)
def get_wave_items(
    wave_id: str,
    wave_repository: DpmWaveRepository = Depends(get_wave_repository),
) -> DpmWaveItemsResponse:
    try:
        payload = wave_service.list_wave_items(
            wave_id=wave_id,
            wave_repository=wave_repository,
        )
    except wave_service.DpmWaveLookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    return DpmWaveItemsResponse.model_validate(payload)


@router.post(
    "/{wave_id}/source-check",
    response_model=DpmWaveResponse,
    status_code=status.HTTP_200_OK,
    summary="Source-check a durable rebalance wave",
    description=(
        "Evaluates RFC-0041 source readiness for each durable wave item using persisted mandate "
        "digital twins, mandate health snapshots, and their source lineage. Items are classified "
        "as `SOURCE_READY`, `SOURCE_DEGRADED`, `REVIEW_REQUIRED`, or `SOURCE_BLOCKED`; caller "
        "portfolio ids or supplied refs alone never promote an item to ready. Repeating the call "
        "after the wave is already `SOURCE_CHECKED` returns the persisted wave as an idempotent "
        "replay without appending a duplicate event."
    ),
    responses={
        200: {
            "description": "Durable source-checked wave with item classifications.",
            "content": {"application/json": {"example": SOURCE_CHECK_WAVE_EXAMPLE}},
        },
        404: {
            "description": "Wave not found.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": {
                            "code": "DPM_WAVE_NOT_FOUND",
                            "message": "Wave dwv_missing was not found.",
                        }
                    }
                }
            },
        },
        409: {
            "description": "Wave version conflict during optimistic update.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": {
                            "code": "DPM_WAVE_VERSION_CONFLICT",
                            "message": "DPM_WAVE_VERSION_CONFLICT",
                        }
                    }
                }
            },
        },
        422: {
            "description": "Wave is not in a state that can be source-checked.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": {
                            "code": "DPM_WAVE_SOURCE_CHECK_INVALID_STATE",
                            "message": "Wave dwv_001 cannot be source-checked from state DRAFT.",
                        }
                    }
                }
            },
        },
    },
)
def source_check_wave(
    wave_id: str,
    request: DpmWaveSourceCheckRequest,
    x_correlation_id: Annotated[
        str | None,
        Header(
            description="Optional correlation id for supportability.",
            examples=["corr-wave-source-check-001"],
        ),
    ] = None,
    mandate_repository: DpmMandateRepository = Depends(get_mandate_repository),
    wave_repository: DpmWaveRepository = Depends(get_wave_repository),
) -> DpmWaveResponse:
    try:
        wave, replayed = wave_service.source_check_wave(
            wave_id=wave_id,
            actor_id=request.actor_id,
            correlation_id=x_correlation_id or f"corr_wave_source_check_{wave_id}",
            mandate_repository=mandate_repository,
            wave_repository=wave_repository,
        )
    except wave_service.DpmWaveLookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    except wave_service.DpmWaveValidationError as exc:
        status_code = (
            status.HTTP_409_CONFLICT
            if exc.code == "DPM_WAVE_VERSION_CONFLICT"
            else status.HTTP_422_UNPROCESSABLE_CONTENT
        )
        raise HTTPException(
            status_code=status_code,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    return _wave_response(wave=wave, durable=True, idempotent_replay=replayed)


@router.post(
    "/{wave_id}/simulate",
    response_model=DpmWaveResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate construction alternatives for source-ready wave items",
    description=(
        "Calls the RFC-0039 construction alternative authority for source-ready wave items that "
        "have caller-supplied construction inputs. Source-blocked, degraded, and review-required "
        "items are preserved with their reasons. Ready items without construction input become "
        "`SIMULATION_BLOCKED`; the endpoint does not synthesize portfolio holdings, market data, "
        "model targets, or shelf data from mandate identifiers."
    ),
    responses={
        200: {"description": "Durable simulated or partially simulated wave."},
        404: {"description": "Wave not found."},
        409: {"description": "Wave version conflict during optimistic update."},
        422: {"description": "Wave is not source-checked or request is invalid."},
    },
)
def simulate_wave(
    wave_id: str,
    request: DpmWaveSimulationRequest,
    x_correlation_id: Annotated[
        str | None,
        Header(
            description="Optional correlation id for supportability.",
            examples=["corr-wave-simulate-001"],
        ),
    ] = None,
    construction_repository: ConstructionRepository = Depends(get_construction_repository),
    risk_authority_client: LotusRiskAuthorityClient | None = Depends(get_risk_authority_client),
    run_service: DpmRunSupportService = Depends(get_dpm_run_support_service),
    wave_repository: DpmWaveRepository = Depends(get_wave_repository),
) -> DpmWaveResponse:
    item_inputs: dict[str, RebalanceRequest | wave_service.DpmWaveSimulationInput] = {}
    for item_input in request.item_inputs:
        simulation_input = wave_service.DpmWaveSimulationInput(
            stateless_input=item_input.stateless_input,
            authority_context=item_input.authority_context,
        )
        if item_input.wave_item_id:
            item_inputs[item_input.wave_item_id] = simulation_input
        if item_input.portfolio_id:
            item_inputs[item_input.portfolio_id] = simulation_input
    try:
        wave, replayed = wave_service.simulate_wave(
            wave_id=wave_id,
            actor_id=request.actor_id,
            correlation_id=x_correlation_id or f"corr_wave_simulate_{wave_id}",
            item_inputs=item_inputs,
            methods=request.methods,
            construction_repository=construction_repository,
            run_service=run_service,
            wave_repository=wave_repository,
            risk_authority_client=risk_authority_client,
        )
    except wave_service.DpmWaveLookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    except wave_service.DpmWaveValidationError as exc:
        raise _wave_validation_http_exception(exc) from exc
    return _wave_response(wave=wave, durable=True, idempotent_replay=replayed)


@router.post(
    "/{wave_id}/items/{wave_item_id}/select",
    response_model=DpmWaveResponse,
    status_code=status.HTTP_200_OK,
    summary="Select a construction alternative for a wave item",
    description=(
        "Records item-level RFC-0039 alternative selection with actor, reason, and optional "
        "comment. When requested, it generates an RFC-0040 proof pack from the selected "
        "alternative. Proof-pack failures are represented as degraded selection posture instead "
        "of unsupported proof-pack readiness."
    ),
    responses={
        200: {"description": "Wave item selection recorded and persisted."},
        404: {"description": "Wave, item, alternative set, or alternative id was not found."},
        409: {"description": "Wave version conflict during optimistic update."},
        422: {"description": "Wave or item is not eligible for selection."},
    },
)
def select_wave_item_alternative(
    wave_id: str,
    wave_item_id: str,
    request: DpmWaveSelectionRequest,
    x_correlation_id: Annotated[
        str | None,
        Header(
            description="Optional correlation id for supportability.",
            examples=["corr-wave-select-001"],
        ),
    ] = None,
    construction_repository: ConstructionRepository = Depends(get_construction_repository),
    proof_pack_repository: DpmProofPackRepository = Depends(get_proof_pack_repository),
    mandate_repository: DpmMandateRepository = Depends(get_mandate_repository),
    run_service: DpmRunSupportService = Depends(get_dpm_run_support_service),
    wave_repository: DpmWaveRepository = Depends(get_wave_repository),
) -> DpmWaveResponse:
    try:
        wave = wave_service.select_wave_item_alternative(
            wave_id=wave_id,
            wave_item_id=wave_item_id,
            alternative_id=request.alternative_id,
            actor_id=request.actor_id,
            reason_code=request.reason_code,
            comment=request.comment,
            correlation_id=x_correlation_id or f"corr_wave_select_{wave_id}_{wave_item_id}",
            generate_proof_pack=request.generate_proof_pack,
            construction_repository=construction_repository,
            proof_pack_repository=proof_pack_repository,
            mandate_repository=mandate_repository,
            run_service=run_service,
            wave_repository=wave_repository,
        )
    except wave_service.DpmWaveLookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    except wave_service.DpmWaveValidationError as exc:
        raise _wave_validation_http_exception(exc) from exc
    return _wave_response(wave=wave, durable=True)


@router.post(
    "/{wave_id}/approve",
    response_model=DpmWaveResponse,
    status_code=status.HTTP_200_OK,
    summary="Approve selected rebalance wave items",
    description=(
        "Approves selected or proof-pack-ready wave items with actor attribution. Source-blocked, "
        "simulation-blocked, degraded, failed, or otherwise unselected items are never approved; "
        "mixed waves become `APPROVED_WITH_EXCEPTIONS`. Repeating the command after approval "
        "returns the persisted wave without appending duplicate approval evidence."
    ),
    responses={
        200: {"description": "Wave approval recorded or replayed."},
        404: {"description": "Wave not found."},
        409: {"description": "Wave version conflict during optimistic update."},
        422: {"description": "Wave has no eligible items or is not approval-ready."},
    },
)
def approve_wave(
    wave_id: str,
    request: DpmWaveWorkflowCommandRequest,
    x_correlation_id: Annotated[
        str | None,
        Header(
            description="Optional correlation id for supportability.",
            examples=["corr-wave-approve-001"],
        ),
    ] = None,
    wave_repository: DpmWaveRepository = Depends(get_wave_repository),
) -> DpmWaveResponse:
    try:
        wave, replayed = wave_service.approve_wave(
            wave_id=wave_id,
            actor_id=request.actor_id,
            reason_code=request.reason_code,
            comment=request.comment,
            correlation_id=x_correlation_id or f"corr_wave_approve_{wave_id}",
            wave_repository=wave_repository,
        )
    except wave_service.DpmWaveLookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    except wave_service.DpmWaveValidationError as exc:
        raise _wave_validation_http_exception(exc) from exc
    return _wave_response(wave=wave, durable=True, idempotent_replay=replayed)


@router.post(
    "/{wave_id}/stage",
    response_model=DpmWaveResponse,
    status_code=status.HTTP_200_OK,
    summary="Stage approved rebalance wave items",
    description=(
        "Stages approved wave items for internal operations handoff. The endpoint does not stage "
        "blocked or unapproved items and does not claim external order execution. Repeating the "
        "command after staging or handoff readiness returns the persisted wave without duplicate "
        "events."
    ),
    responses={
        200: {"description": "Wave staging recorded or replayed."},
        404: {"description": "Wave not found."},
        409: {"description": "Wave version conflict during optimistic update."},
        422: {"description": "Wave has no approved items or is not stage-ready."},
    },
)
def stage_wave(
    wave_id: str,
    request: DpmWaveWorkflowCommandRequest,
    x_correlation_id: Annotated[
        str | None,
        Header(
            description="Optional correlation id for supportability.",
            examples=["corr-wave-stage-001"],
        ),
    ] = None,
    wave_repository: DpmWaveRepository = Depends(get_wave_repository),
) -> DpmWaveResponse:
    try:
        wave, replayed = wave_service.stage_wave(
            wave_id=wave_id,
            actor_id=request.actor_id,
            reason_code=request.reason_code,
            comment=request.comment,
            correlation_id=x_correlation_id or f"corr_wave_stage_{wave_id}",
            wave_repository=wave_repository,
        )
    except wave_service.DpmWaveLookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    except wave_service.DpmWaveValidationError as exc:
        raise _wave_validation_http_exception(exc) from exc
    return _wave_response(wave=wave, durable=True, idempotent_replay=replayed)


@router.post(
    "/{wave_id}/handoff",
    response_model=DpmWaveResponse,
    status_code=status.HTTP_200_OK,
    summary="Create internal operations handoff evidence",
    description=(
        "Creates append-only internal operations handoff evidence for staged wave items. This is "
        "a manage-owned readiness package only: it records `external_execution_claimed=false` and "
        "does not send orders, client communications, or external execution instructions."
    ),
    responses={
        200: {"description": "Wave handoff evidence recorded or replayed."},
        404: {"description": "Wave not found."},
        409: {"description": "Wave version conflict during optimistic update."},
        422: {"description": "Wave has no staged items or is not handoff-ready."},
    },
)
def handoff_wave(
    wave_id: str,
    request: DpmWaveWorkflowCommandRequest,
    x_correlation_id: Annotated[
        str | None,
        Header(
            description="Optional correlation id for supportability.",
            examples=["corr-wave-handoff-001"],
        ),
    ] = None,
    wave_repository: DpmWaveRepository = Depends(get_wave_repository),
) -> DpmWaveResponse:
    try:
        wave, replayed = wave_service.handoff_wave(
            wave_id=wave_id,
            actor_id=request.actor_id,
            reason_code=request.reason_code,
            comment=request.comment,
            correlation_id=x_correlation_id or f"corr_wave_handoff_{wave_id}",
            wave_repository=wave_repository,
        )
    except wave_service.DpmWaveLookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    except wave_service.DpmWaveValidationError as exc:
        raise _wave_validation_http_exception(exc) from exc
    return _wave_response(wave=wave, durable=True, idempotent_replay=replayed)


@router.post(
    "/{wave_id}/cancel",
    response_model=DpmWaveResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel a rebalance wave before external execution",
    description=(
        "Cancels an eligible RFC-0041 wave with actor attribution and preserves all item evidence. "
        "Items that have not reached internal handoff are marked `EXCLUDED` with cancellation "
        "diagnostics; manage still records `external_execution_claimed=false`. The endpoint does "
        "not cancel external orders, because manage wave handoff is an internal readiness package "
        "and not an execution instruction. Repeating the command after cancellation returns the "
        "persisted wave without duplicate cancellation events."
    ),
    responses={
        200: {"description": "Wave cancellation recorded or replayed."},
        404: {"description": "Wave not found."},
        409: {"description": "Wave version conflict during optimistic update."},
        422: {"description": "Wave state cannot be cancelled."},
    },
)
def cancel_wave(
    wave_id: str,
    request: DpmWaveWorkflowCommandRequest,
    x_correlation_id: Annotated[
        str | None,
        Header(
            description="Optional correlation id for supportability.",
            examples=["corr-wave-cancel-001"],
        ),
    ] = None,
    wave_repository: DpmWaveRepository = Depends(get_wave_repository),
) -> DpmWaveResponse:
    try:
        wave, replayed = wave_service.cancel_wave(
            wave_id=wave_id,
            actor_id=request.actor_id,
            reason_code=request.reason_code,
            comment=request.comment,
            correlation_id=x_correlation_id or f"corr_wave_cancel_{wave_id}",
            wave_repository=wave_repository,
        )
    except wave_service.DpmWaveLookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    except wave_service.DpmWaveValidationError as exc:
        raise _wave_validation_http_exception(exc) from exc
    return _wave_response(wave=wave, durable=True, idempotent_replay=replayed)


@router.get(
    "/{wave_id}/proof-pack",
    response_model=DpmWaveProofPackPostureResponse,
    status_code=status.HTTP_200_OK,
    summary="Get wave proof-pack and handoff posture",
    description=(
        "Returns item-level RFC-0040 proof-pack refs, degraded proof-pack posture, append-only "
        "handoff refs, and the no-external-execution boundary for a persisted wave. The endpoint "
        "does not rebuild proof packs or claim external execution."
    ),
    responses={
        200: {"description": "Wave proof-pack and handoff posture."},
        404: {"description": "Wave not found."},
    },
)
def get_wave_proof_pack_posture(
    wave_id: str,
    wave_repository: DpmWaveRepository = Depends(get_wave_repository),
) -> DpmWaveProofPackPostureResponse:
    try:
        payload = wave_service.proof_pack_posture(
            wave_id=wave_id,
            wave_repository=wave_repository,
        )
    except wave_service.DpmWaveLookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    return DpmWaveProofPackPostureResponse.model_validate(payload)


@router.get(
    "/{wave_id}/report-input",
    response_model=DpmWaveReportInput,
    status_code=status.HTTP_200_OK,
    summary="Get wave report input",
    description=(
        "Returns deterministic `DpmWaveReportInput` for a persisted RFC-0041 rebalance wave. "
        "`lotus-report`, `lotus-render`, and `lotus-archive` can use this payload to materialize "
        "and govern wave evidence without reconstructing wave state, proof-pack linkage, internal "
        "handoff refs, source hashes, or supportability posture. `lotus-manage` does not generate "
        "rendered reports, archive records, or external execution claims."
    ),
    responses={
        200: {"description": "Generated wave report-input payload."},
        404: {"description": "Wave not found."},
    },
)
def get_wave_report_input(
    wave_id: str,
    wave_repository: DpmWaveRepository = Depends(get_wave_repository),
) -> DpmWaveReportInput:
    try:
        return wave_service.get_report_input(
            wave_id=wave_id,
            wave_repository=wave_repository,
        )
    except wave_service.DpmWaveLookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": exc.code, "message": exc.message},
        ) from exc


@router.get(
    "/{wave_id}/supportability",
    response_model=DpmWaveSupportabilityResponse,
    status_code=status.HTTP_200_OK,
    summary="Get product-safe wave supportability diagnostics",
    description=(
        "Returns operator-safe RFC-0041 wave supportability diagnostics. The response excludes "
        "portfolio identifiers, client identifiers, raw request bodies, raw response bodies, "
        "secrets, and trace details. Use this endpoint to understand blocked/degraded item states, "
        "source owners, bounded reason codes, remediation routes, and support references."
    ),
    responses={
        200: {"description": "Product-safe wave supportability diagnostics."},
        404: {"description": "Wave not found."},
    },
)
def get_wave_supportability(
    wave_id: str,
    wave_repository: DpmWaveRepository = Depends(get_wave_repository),
) -> DpmWaveSupportabilityResponse:
    try:
        payload = wave_service.wave_supportability(
            wave_id=wave_id,
            wave_repository=wave_repository,
        )
    except wave_service.DpmWaveLookupError as exc:
        record_wave_supportability(
            surface="rebalance/waves/supportability",
            supportability_state="not_found",
            reason="wave_not_found",
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    supportability_state = str(payload["supportability_state"])
    reason = str(payload["reason"])
    record_wave_supportability(
        surface="rebalance/waves/supportability",
        supportability_state=supportability_state,
        reason=reason,
    )
    logger.info(
        "wave.supportability.inspected",
        extra={
            "extra_fields": {
                "wave_state": payload["wave_state"],
                "supportability_state": supportability_state,
                "reason": reason,
                "issue_count": len(cast(list[object], payload["issues"])),
            }
        },
    )
    return DpmWaveSupportabilityResponse.model_validate(payload)


def _wave_validation_http_exception(exc: wave_service.DpmWaveValidationError) -> HTTPException:
    status_code = (
        status.HTTP_409_CONFLICT
        if exc.code == "DPM_WAVE_VERSION_CONFLICT"
        else status.HTTP_422_UNPROCESSABLE_CONTENT
    )
    return HTTPException(
        status_code=status_code,
        detail={"code": exc.code, "message": exc.message},
    )
