from __future__ import annotations

from src.api.services import construction_service
from src.api.services.wave_errors import DpmWaveLookupError, DpmWaveValidationError
from src.core.construction.repository import (
    ConstructionAlternativeBlockedError,
    ConstructionAlternativeNotFoundError,
    ConstructionAlternativeSetNotFoundError,
    ConstructionRepository,
)

_CONSTRUCTION_SELECTION_LOOKUP_ERRORS = (
    ConstructionAlternativeNotFoundError,
    ConstructionAlternativeSetNotFoundError,
)


def select_construction_alternative_for_wave(
    *,
    repository: ConstructionRepository,
    alternative_set_id: str,
    alternative_id: str,
    actor_id: str,
    reason_code: str,
    comment: str | None,
    correlation_id: str,
    tenant_id: str,
) -> None:
    try:
        construction_service.select_construction_alternative(
            repository=repository,
            alternative_set_id=alternative_set_id,
            alternative_id=alternative_id,
            actor_id=actor_id,
            reason_code=reason_code,
            comment=comment,
            correlation_id=correlation_id,
            tenant_id=tenant_id,
        )
    except ConstructionAlternativeBlockedError as exc:
        raise DpmWaveValidationError(
            "DPM_WAVE_CONSTRUCTION_ALTERNATIVE_BLOCKED",
            "A blocked construction alternative cannot be selected for a wave item.",
        ) from exc
    except _CONSTRUCTION_SELECTION_LOOKUP_ERRORS as exc:
        raise DpmWaveLookupError("DPM_CONSTRUCTION_ALTERNATIVE_NOT_FOUND", str(exc)) from exc


__all__ = ["select_construction_alternative_for_wave"]
