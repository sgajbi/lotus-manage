from __future__ import annotations

from typing import Annotated, Literal, cast

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field

from src.api.dependencies import (
    get_construction_repository,
    get_mandate_repository,
    get_proof_pack_repository,
    get_wave_repository,
)
from src.api.request_models import RebalanceRequest
from src.api.routers.rebalance_runs import get_dpm_run_support_service
from src.api.services import wave_service
from src.core.construction.repository import ConstructionRepository
from src.core.construction.vocabulary import ConstructionMethod
from src.core.mandate_repository import DpmMandateRepository
from src.core.proof_packs.repository import DpmProofPackRepository
from src.core.rebalance_runs.service import DpmRunSupportService
from src.core.waves import DpmRebalanceWave, DpmWaveRepository, DpmWaveSourceRef


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


class DpmWaveResponse(BaseModel):
    wave: DpmRebalanceWave = Field(description="Previewed or durable rebalance wave.")
    durable: bool = Field(
        description="Whether this response was durably persisted.", examples=[False]
    )
    idempotent_replay: bool = Field(
        default=False,
        description="True when create returned an already persisted wave for the idempotency key.",
        examples=[False],
    )


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


router = APIRouter(prefix="/rebalance/waves", tags=["lotus-manage Rebalance Waves"])


@router.post(
    "/preview",
    response_model=DpmWaveResponse,
    status_code=status.HTTP_200_OK,
    summary="Preview an affected-portfolio rebalance wave",
    description=(
        "Builds a non-durable RFC-0041 affected-portfolio wave preview for the first supported "
        "trigger, `EXPLICIT_PORTFOLIO_LIST`. The endpoint preserves source refs from the request "
        "or existing mandate digital twins and blocks items whose affected-portfolio evidence is "
        "missing. It does not perform PM-book discovery, CIO impact discovery, source readiness, "
        "simulation, approval, staging, or operations handoff."
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
    try:
        wave = wave_service.preview_wave(
            trigger_type=request.trigger_type,
            trigger_id=request.trigger_id,
            rationale=request.rationale,
            as_of_date=request.as_of_date,
            actor_id=request.actor_id,
            correlation_id=x_correlation_id or f"corr_wave_preview_{request.trigger_id}",
            portfolios=[portfolio.model_dump(mode="json") for portfolio in request.portfolios],
            mandate_repository=mandate_repository,
        )
    except wave_service.DpmWaveValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    return DpmWaveResponse(wave=wave, durable=False)


@router.post(
    "",
    response_model=DpmWaveResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a durable affected-portfolio rebalance wave",
    description=(
        "Creates a durable RFC-0041 rebalance wave for `EXPLICIT_PORTFOLIO_LIST` requests. "
        "Required header: `Idempotency-Key`. Unsupported trigger types are rejected and missing "
        "affected-portfolio source evidence produces blocked items, not false readiness."
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
    try:
        wave, replayed = wave_service.create_wave(
            trigger_type=request.trigger_type,
            trigger_id=request.trigger_id,
            rationale=request.rationale,
            as_of_date=request.as_of_date,
            actor_id=request.actor_id,
            correlation_id=x_correlation_id or f"corr_wave_create_{request.trigger_id}",
            portfolios=[portfolio.model_dump(mode="json") for portfolio in request.portfolios],
            idempotency_key=idempotency_key,
            mandate_repository=mandate_repository,
            wave_repository=wave_repository,
        )
    except wave_service.DpmWaveValidationError as exc:
        status_code = (
            status.HTTP_409_CONFLICT
            if exc.code == "WAVE_CREATE_CONFLICT"
            else status.HTTP_422_UNPROCESSABLE_ENTITY
        )
        raise HTTPException(
            status_code=status_code,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    return DpmWaveResponse(wave=wave, durable=True, idempotent_replay=replayed)


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
            else status.HTTP_422_UNPROCESSABLE_ENTITY
        )
        raise HTTPException(
            status_code=status_code,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    return DpmWaveResponse(wave=wave, durable=True, idempotent_replay=replayed)


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
    run_service: DpmRunSupportService = Depends(get_dpm_run_support_service),
    wave_repository: DpmWaveRepository = Depends(get_wave_repository),
) -> DpmWaveResponse:
    item_inputs: dict[str, RebalanceRequest] = {}
    for item_input in request.item_inputs:
        if item_input.wave_item_id:
            item_inputs[item_input.wave_item_id] = item_input.stateless_input
        if item_input.portfolio_id:
            item_inputs[item_input.portfolio_id] = item_input.stateless_input
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
        )
    except wave_service.DpmWaveLookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    except wave_service.DpmWaveValidationError as exc:
        raise _wave_validation_http_exception(exc) from exc
    return DpmWaveResponse(wave=wave, durable=True, idempotent_replay=replayed)


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
    return DpmWaveResponse(wave=wave, durable=True)


def _wave_validation_http_exception(exc: wave_service.DpmWaveValidationError) -> HTTPException:
    status_code = (
        status.HTTP_409_CONFLICT
        if exc.code == "DPM_WAVE_VERSION_CONFLICT"
        else status.HTTP_422_UNPROCESSABLE_ENTITY
    )
    return HTTPException(
        status_code=status_code,
        detail={"code": exc.code, "message": exc.message},
    )
