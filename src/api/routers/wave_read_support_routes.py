from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, status

from src.api.dependencies import (
    get_mandate_repository,
    get_outcome_review_repository,
    get_proof_pack_repository,
    get_wave_repository,
)
from src.api.routers.wave_read_http import get_wave_proof_pack_posture_response
from src.api.routers.wave_report_input_http import get_wave_report_input_response
from src.api.routers.wave_response_contracts import (
    DpmWaveProofPackPostureResponse,
    DpmWaveSupportabilityResponse,
)
from src.api.routers.wave_route_parameters import WaveIdPath
from src.api.routers.wave_supportability_http import get_wave_supportability_response
from src.core.mandate_repository import DpmMandateRepository
from src.core.outcomes.repository import DpmOutcomeReviewRepository
from src.core.proof_packs.repository import DpmProofPackRepository
from src.core.waves import DpmWaveReportInput, DpmWaveRepository


router = APIRouter()
logger = logging.getLogger(__name__)


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
    wave_id: WaveIdPath,
    wave_repository: DpmWaveRepository = Depends(get_wave_repository),
) -> DpmWaveProofPackPostureResponse:
    return get_wave_proof_pack_posture_response(
        wave_id=wave_id,
        wave_repository=wave_repository,
    )


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
        422: {
            "description": (
                "Wave evidence crosses the unsupported external OMS/execution boundary and cannot "
                "be emitted as manage report input."
            )
        },
    },
)
def get_wave_report_input(
    wave_id: WaveIdPath,
    wave_repository: DpmWaveRepository = Depends(get_wave_repository),
    proof_pack_repository: DpmProofPackRepository = Depends(get_proof_pack_repository),
    outcome_review_repository: DpmOutcomeReviewRepository = Depends(get_outcome_review_repository),
    mandate_repository: DpmMandateRepository = Depends(get_mandate_repository),
) -> DpmWaveReportInput:
    return get_wave_report_input_response(
        wave_id=wave_id,
        wave_repository=wave_repository,
        proof_pack_repository=proof_pack_repository,
        outcome_review_repository=outcome_review_repository,
        mandate_repository=mandate_repository,
    )


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
    wave_id: WaveIdPath,
    wave_repository: DpmWaveRepository = Depends(get_wave_repository),
) -> DpmWaveSupportabilityResponse:
    return get_wave_supportability_response(
        wave_id=wave_id,
        wave_repository=wave_repository,
        logger=logger,
    )
