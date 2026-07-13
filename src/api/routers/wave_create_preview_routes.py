from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter, Depends, status

from src.api.dependencies import (
    get_advise_authority_client,
    get_campaign_definition_repository,
    get_mandate_repository,
    get_risk_authority_client,
    get_wave_repository,
)
from src.api.routers.wave_create_preview_http import create_wave_response, preview_wave_response
from src.api.routers.wave_openapi_examples import WAVE_EXAMPLE
from src.api.routers.wave_request_models import DpmWavePreviewRequest
from src.api.routers.wave_response_contracts import DpmWaveResponse
from src.api.routers.wave_route_parameters import (
    WaveCorrelationIdHeader,
    WaveCreateIdempotencyKeyHeader,
    WaveTenantIdHeader,
)
from src.api.services.core_resolver_service import build_core_resolver_client
from src.api.services.authority_client_service import (
    AdviseAuthorityClient,
    RiskAuthorityClient,
)
from src.core.mandate_repository import DpmMandateRepository
from src.core.waves import (
    DpmBulkReviewCampaignDefinitionRepository,
    DpmWaveRepository,
)


def register_wave_create_preview_routes(
    router: APIRouter,
    *,
    core_resolver_factory_provider: Callable[[], Callable[[], object]] = (
        lambda: build_core_resolver_client
    ),
) -> None:
    @router.post(
        "/preview",
        response_model=DpmWaveResponse,
        status_code=status.HTTP_200_OK,
        summary="Preview an affected-portfolio rebalance wave",
        description=(
            "Builds a non-durable RFC-0041 affected-portfolio wave preview. "
            "`EXPLICIT_PORTFOLIO_LIST` preserves source refs from the request or existing mandate "
            "digital twins. `PM_BOOK_REVIEW` resolves the cohort from the lotus-core "
            "`PortfolioManagerBookMembership:v1` source product. `CIO_MODEL_CHANGE` resolves the "
            "cohort from lotus-core `CioModelChangeAffectedCohort:v1`. `RISK_EVENT` evaluates "
            "the candidate set through lotus-risk `RiskEventAffectedCohort:v1` and preserves "
            "source-owned membership evidence. `TACTICAL_HOUSE_VIEW` evaluates the candidate set "
            "through lotus-advise `TacticalHouseViewAffectedCohort:v1` and preserves "
            "source-owned house-view/candidate evidence. `BULK_REVIEW_CAMPAIGN` builds the "
            "Manage-owned `BulkReviewCampaignMembership:v1` envelope from inline or persisted "
            "source-backed candidate portfolios, or from lotus-core "
            "`DpmPortfolioUniverseCandidate:v1` when "
            "`campaign_candidate_source=CORE_DPM_PORTFOLIO_UNIVERSE`. Core candidate discovery "
            "walks bounded continuation pages to terminal exhaustion and fails closed on "
            "unavailable, incomplete, degraded, empty, duplicate, non-terminating, or "
            "still-truncated source pages. Unsupported trigger types remain blocked; the endpoint "
            "does not recompute house-view, holdings, risk, performance, simulation, approval, "
            "staging, operations handoff, relationship householding, global portfolio-universe "
            "semantics, workflow orchestration, or OMS execution."
        ),
        responses={
            200: {
                "description": "Non-durable wave preview with explicit candidate and blocked states.",
                "content": {"application/json": {"example": WAVE_EXAMPLE}},
            },
            422: {
                "description": "Unsupported trigger, missing source evidence, or invalid request.",
                "content": {
                    "application/json": {
                        "example": {
                            "detail": {
                                "code": "TACTICAL_HOUSE_VIEW_REQUIRED",
                                "message": "TACTICAL_HOUSE_VIEW requires tactical_house_view source evidence.",
                            }
                        }
                    }
                },
            },
        },
    )
    def preview_wave(
        request: DpmWavePreviewRequest,
        x_correlation_id: WaveCorrelationIdHeader = None,
        x_tenant_id: WaveTenantIdHeader = None,
        mandate_repository: DpmMandateRepository = Depends(get_mandate_repository),
        advise_authority_client: AdviseAuthorityClient | None = Depends(
            get_advise_authority_client
        ),
        risk_authority_client: RiskAuthorityClient | None = Depends(get_risk_authority_client),
        campaign_definition_repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
            get_campaign_definition_repository
        ),
    ) -> DpmWaveResponse:
        correlation_id = x_correlation_id or f"corr_wave_preview_{request.trigger_id}"
        return preview_wave_response(
            request=request,
            tenant_id=x_tenant_id,
            correlation_id=correlation_id,
            mandate_repository=mandate_repository,
            advise_authority_client=advise_authority_client,
            risk_authority_client=risk_authority_client,
            campaign_definition_repository=campaign_definition_repository,
            core_resolver_factory=core_resolver_factory_provider(),
        )

    @router.post(
        "",
        response_model=DpmWaveResponse,
        status_code=status.HTTP_201_CREATED,
        summary="Create a durable affected-portfolio rebalance wave",
        description=(
            "Creates a durable RFC-0041 rebalance wave. `EXPLICIT_PORTFOLIO_LIST` uses "
            "caller-supplied affected portfolios, while `PM_BOOK_REVIEW` and `CIO_MODEL_CHANGE` "
            "resolve cohorts from lotus-core source products and `RISK_EVENT` evaluates the "
            "candidate set through lotus-risk `RiskEventAffectedCohort:v1` before persistence. "
            "`TACTICAL_HOUSE_VIEW` evaluates the candidate set through lotus-advise "
            "`TacticalHouseViewAffectedCohort:v1` before persistence. `BULK_REVIEW_CAMPAIGN` "
            "persists a Manage-owned campaign membership wave from inline, persisted, or "
            "lotus-core `DpmPortfolioUniverseCandidate:v1` source-backed candidates. Core "
            "candidate discovery requires `campaign_candidate_source=CORE_DPM_PORTFOLIO_UNIVERSE`, "
            "walks bounded continuation pages to terminal exhaustion, and fails closed on "
            "unavailable, incomplete, degraded, empty, duplicate, non-terminating, or "
            "still-truncated source pages. Required header: `Idempotency-Key`. Unsupported "
            "trigger types are rejected and missing source evidence produces blocked items, not "
            "false readiness; the route does not claim relationship householding, global "
            "portfolio-universe ownership, workflow orchestration, client communication workflow, "
            "order routing, or OMS execution."
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
                "description": "Unsupported trigger, missing source evidence, or invalid request.",
                "content": {
                    "application/json": {
                        "example": {
                            "detail": {
                                "code": "TACTICAL_HOUSE_VIEW_REQUIRED",
                                "message": "TACTICAL_HOUSE_VIEW requires tactical_house_view source evidence.",
                            }
                        }
                    }
                },
            },
        },
    )
    def create_wave(
        request: DpmWavePreviewRequest,
        idempotency_key: WaveCreateIdempotencyKeyHeader,
        x_correlation_id: WaveCorrelationIdHeader = None,
        x_tenant_id: WaveTenantIdHeader = None,
        mandate_repository: DpmMandateRepository = Depends(get_mandate_repository),
        wave_repository: DpmWaveRepository = Depends(get_wave_repository),
        advise_authority_client: AdviseAuthorityClient | None = Depends(
            get_advise_authority_client
        ),
        risk_authority_client: RiskAuthorityClient | None = Depends(get_risk_authority_client),
        campaign_definition_repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
            get_campaign_definition_repository
        ),
    ) -> DpmWaveResponse:
        correlation_id = x_correlation_id or f"corr_wave_create_{request.trigger_id}"
        return create_wave_response(
            request=request,
            tenant_id=x_tenant_id,
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
            mandate_repository=mandate_repository,
            wave_repository=wave_repository,
            advise_authority_client=advise_authority_client,
            risk_authority_client=risk_authority_client,
            campaign_definition_repository=campaign_definition_repository,
            core_resolver_factory=core_resolver_factory_provider(),
        )
