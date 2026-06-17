from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from src.api.routers.wave_core_source_resolution import (
    _cio_model_change_cohort_request_for_wave,
    _pm_book_membership_request_for_wave,
    _require_cio_model_change_cohort_ready,
    _require_pm_book_membership_ready,
)
from src.api.routers.wave_request_models import DpmWavePreviewRequest
from src.api.services import wave_service


def _pm_book_request(**overrides: object) -> DpmWavePreviewRequest:
    payload: dict[str, object] = {
        "trigger_type": "PM_BOOK_REVIEW",
        "trigger_id": "wave-pm-book-20260519",
        "rationale": "Review source-owned PM book membership.",
        "as_of_date": "2026-05-19",
        "actor_id": "pm_001",
        "portfolio_manager_id": " PM_SG_DPM_001 ",
        "tenant_id": "tenant-private-bank",
        "booking_center_code": "SG",
        "portfolio_types": [" discretionary ", "DPM"],
    }
    payload.update(overrides)
    return DpmWavePreviewRequest.model_validate(payload)


def _cio_model_change_request(**overrides: object) -> DpmWavePreviewRequest:
    payload: dict[str, object] = {
        "trigger_type": "CIO_MODEL_CHANGE",
        "trigger_id": "wave-cio-model-change-20260519",
        "rationale": "Review source-owned model-change affected mandates.",
        "as_of_date": "2026-05-19",
        "actor_id": "cio_001",
        "model_portfolio_id": " MODEL_PB_SG_GLOBAL_BAL_DPM ",
        "tenant_id": "tenant-private-bank",
        "booking_center_code": "SG",
    }
    payload.update(overrides)
    return DpmWavePreviewRequest.model_validate(payload)


def _source_supportability(state: str = "READY", reason: str = "SOURCE_READY") -> object:
    return SimpleNamespace(state=state, reason=reason)


def test_pm_book_membership_request_for_wave_maps_source_query() -> None:
    membership_request = _pm_book_membership_request_for_wave(_pm_book_request())

    assert membership_request.portfolio_manager_id == "PM_SG_DPM_001"
    assert membership_request.as_of_date.isoformat() == "2026-05-19"
    assert membership_request.tenant_id == "tenant-private-bank"
    assert membership_request.booking_center_code == "SG"
    assert membership_request.portfolio_types == ["DISCRETIONARY", "DPM"]


def test_pm_book_membership_request_for_wave_rejects_caller_supplied_portfolios() -> None:
    request = _pm_book_request(
        portfolios=[
            {
                "portfolio_id": "PB_SG_GLOBAL_BAL_001",
                "mandate_id": "MANDATE_PB_SG_GLOBAL_BAL_001",
            }
        ]
    )

    with pytest.raises(wave_service.DpmWaveValidationError) as exc_info:
        _pm_book_membership_request_for_wave(request)

    assert exc_info.value.code == "PM_BOOK_REVIEW_REJECTS_CALLER_PORTFOLIOS"


def test_pm_book_membership_ready_helper_rejects_incomplete_or_empty_source_membership() -> None:
    with pytest.raises(HTTPException) as exc_info:
        _require_pm_book_membership_ready(
            SimpleNamespace(
                supportability=_source_supportability(
                    state="BLOCKED",
                    reason="PM_BOOK_MEMBERSHIP_INCOMPLETE",
                ),
                members=[object()],
            )
        )
    assert exc_info.value.status_code == 424
    assert exc_info.value.detail["code"] == "PM_BOOK_MEMBERSHIP_INCOMPLETE"

    with pytest.raises(HTTPException) as exc_info:
        _require_pm_book_membership_ready(
            SimpleNamespace(
                supportability=_source_supportability(),
                members=[],
            )
        )
    assert exc_info.value.status_code == 424
    assert exc_info.value.detail["code"] == "DPM_CORE_PM_BOOK_MEMBERSHIP_EMPTY"


def test_cio_model_change_cohort_request_for_wave_maps_source_query() -> None:
    cohort_request = _cio_model_change_cohort_request_for_wave(_cio_model_change_request())

    assert cohort_request.model_portfolio_id == "MODEL_PB_SG_GLOBAL_BAL_DPM"
    assert cohort_request.as_of_date.isoformat() == "2026-05-19"
    assert cohort_request.tenant_id == "tenant-private-bank"
    assert cohort_request.booking_center_code == "SG"


def test_cio_model_change_cohort_request_for_wave_rejects_caller_supplied_portfolios() -> None:
    request = _cio_model_change_request(
        portfolios=[
            {
                "portfolio_id": "PB_SG_GLOBAL_BAL_001",
                "mandate_id": "MANDATE_PB_SG_GLOBAL_BAL_001",
            }
        ]
    )

    with pytest.raises(wave_service.DpmWaveValidationError) as exc_info:
        _cio_model_change_cohort_request_for_wave(request)

    assert exc_info.value.code == "CIO_MODEL_CHANGE_REJECTS_CALLER_PORTFOLIOS"


def test_cio_model_change_cohort_ready_helper_rejects_incomplete_or_empty_source_cohort() -> None:
    with pytest.raises(HTTPException) as exc_info:
        _require_cio_model_change_cohort_ready(
            SimpleNamespace(
                supportability=_source_supportability(
                    state="BLOCKED",
                    reason="CIO_MODEL_CHANGE_COHORT_INCOMPLETE",
                ),
                affected_mandates=[object()],
            )
        )
    assert exc_info.value.status_code == 424
    assert exc_info.value.detail["code"] == "CIO_MODEL_CHANGE_COHORT_INCOMPLETE"

    with pytest.raises(HTTPException) as exc_info:
        _require_cio_model_change_cohort_ready(
            SimpleNamespace(
                supportability=_source_supportability(),
                affected_mandates=[],
            )
        )
    assert exc_info.value.status_code == 424
    assert exc_info.value.detail["code"] == "DPM_CORE_CIO_MODEL_CHANGE_COHORT_EMPTY"
