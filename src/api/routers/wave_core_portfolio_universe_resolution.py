from __future__ import annotations

from collections.abc import Callable
from typing import Any

from src.api.routers.wave_date_validation import parse_wave_as_of_date
from src.api.routers.wave_source_dependency_http import (
    source_dependency_failed_http_exception,
    upstream_unavailable_http_exception,
)
from src.api.services import wave_service
from src.api.services.wave_core_portfolio_universe_resolution import (
    resolve_core_dpm_portfolio_universe_candidates as _resolve_core_dpm_portfolio_universe_candidates,
)
from src.api.services.wave_errors import DpmWaveDependencyError
from src.api.services.wave_errors import DpmWaveDependencyUnavailableError
from src.api.routers.wave_request_models import DpmWavePreviewRequest


def resolve_core_dpm_portfolio_universe_candidates(
    *,
    request: DpmWavePreviewRequest,
    correlation_id: str,
    core_resolver_factory: Callable[[], Any],
) -> list[dict[str, object]]:
    if request.portfolios:
        raise wave_service.DpmWaveValidationError(
            "BULK_REVIEW_CAMPAIGN_CORE_UNIVERSE_REJECTS_CALLER_PORTFOLIOS",
            "Core DPM portfolio-universe discovery supplies the candidate portfolio set.",
        )
    as_of_date = parse_wave_as_of_date(request.as_of_date)
    try:
        return _resolve_core_dpm_portfolio_universe_candidates(
            as_of_date=as_of_date,
            tenant_id=request.tenant_id,
            booking_center_code=request.booking_center_code,
            model_portfolio_ids=request.model_portfolio_ids,
            include_inactive_mandates=request.include_inactive_mandates,
            campaign_candidate_page_size=request.campaign_candidate_page_size,
            correlation_id=correlation_id,
            core_resolver_factory=core_resolver_factory,
        )
    except DpmWaveDependencyUnavailableError as exc:
        raise upstream_unavailable_http_exception(exc, default_code=exc.code) from exc
    except DpmWaveDependencyError as exc:
        raise source_dependency_failed_http_exception(code=exc.code, message=exc.message) from exc


__all__ = ["resolve_core_dpm_portfolio_universe_candidates"]
