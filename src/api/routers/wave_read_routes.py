from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, status

from src.api.dependencies import get_wave_repository
from src.api.routers.wave_read_http import (
    get_wave_detail_response,
    get_wave_items_response,
)
from src.api.routers.wave_response_contracts import (
    DpmWaveDetailResponse,
    DpmWaveItemsResponse,
    DpmWaveSearchResponse,
)
from src.api.routers.wave_route_parameters import WaveIdPath
from src.api.routers.wave_search_http import search_waves_response
from src.core.waves import DpmWaveRepository


def register_wave_read_routes(router: APIRouter) -> None:
    @router.get(
        "",
        response_model=DpmWaveSearchResponse,
        status_code=status.HTTP_200_OK,
        summary="Search durable rebalance waves",
        description=(
            "Returns a bounded search page over durable RFC-0041 waves. Search reads persisted "
            "manage wave truth and derives supportability from item states; it does not "
            "recalculate source readiness, construction alternatives, proof-pack state, or "
            "handoff posture."
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
        return search_waves_response(
            wave_repository=wave_repository,
            state=state,
            trigger_type=trigger_type,
            as_of_date=as_of_date,
            supportability_state=supportability_state,
            limit=limit,
            offset=offset,
        )

    @router.get(
        "/{wave_id}",
        response_model=DpmWaveDetailResponse,
        status_code=status.HTTP_200_OK,
        summary="Retrieve durable rebalance wave detail",
        description=(
            "Returns one persisted RFC-0041 wave with items, aggregate metrics, events, source "
            "refs, latest supportability, and proof-pack/handoff posture. The endpoint reads "
            "durable manage state and does not regenerate downstream construction or proof-pack "
            "artifacts."
        ),
        responses={
            200: {"description": "Persisted wave detail."},
            404: {"description": "Wave not found."},
        },
    )
    def get_wave_detail(
        wave_id: WaveIdPath,
        wave_repository: DpmWaveRepository = Depends(get_wave_repository),
    ) -> DpmWaveDetailResponse:
        return get_wave_detail_response(
            wave_id=wave_id,
            wave_repository=wave_repository,
        )

    @router.get(
        "/{wave_id}/items",
        response_model=DpmWaveItemsResponse,
        status_code=status.HTTP_200_OK,
        summary="List rebalance wave items",
        description=(
            "Returns persisted item-level wave posture for source readiness, construction "
            "selection, proof-pack linkage, and internal operations handoff. The response is "
            "intended for Gateway and Workbench command-center realization without UI-side "
            "recomputation."
        ),
        responses={
            200: {"description": "Persisted wave item list."},
            404: {"description": "Wave not found."},
        },
    )
    def get_wave_items(
        wave_id: WaveIdPath,
        wave_repository: DpmWaveRepository = Depends(get_wave_repository),
    ) -> DpmWaveItemsResponse:
        return get_wave_items_response(
            wave_id=wave_id,
            wave_repository=wave_repository,
        )
