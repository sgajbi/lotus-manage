from decimal import Decimal

from src.api.services.construction_regime_stress_supportability import (
    regime_stress_status,
    regime_stress_threshold_breached,
)
from src.core.construction.models import AuthoritativeRegimeStressContext
from src.core.construction.vocabulary import ConstructionMethodStatus


def _regime_stress_context(
    *,
    status: ConstructionMethodStatus = ConstructionMethodStatus.READY,
    worst_case_loss_pct: Decimal = Decimal("0.08"),
    maximum_allowed_loss_pct: Decimal = Decimal("0.10"),
) -> AuthoritativeRegimeStressContext:
    return AuthoritativeRegimeStressContext(
        supportability_status=status,
        source_system="lotus-risk",
        scenario_pack_id="regime_pack_1",
        worst_case_loss_pct=worst_case_loss_pct,
        maximum_allowed_loss_pct=maximum_allowed_loss_pct,
        reason_codes=["SCENARIO_PACK_READY"],
    )


def test_regime_stress_supportability_degrades_without_source_context() -> None:
    assert regime_stress_status(None) == ConstructionMethodStatus.DEGRADED


def test_regime_stress_supportability_marks_threshold_breach_pending_review() -> None:
    context = _regime_stress_context(
        worst_case_loss_pct=Decimal("0.12"),
        maximum_allowed_loss_pct=Decimal("0.10"),
    )

    assert regime_stress_status(context) == ConstructionMethodStatus.PENDING_REVIEW


def test_regime_stress_threshold_breach_helper_compares_source_threshold() -> None:
    assert regime_stress_threshold_breached(
        _regime_stress_context(
            worst_case_loss_pct=Decimal("0.12"),
            maximum_allowed_loss_pct=Decimal("0.10"),
        )
    )
    assert not regime_stress_threshold_breached(
        _regime_stress_context(
            worst_case_loss_pct=Decimal("0.08"),
            maximum_allowed_loss_pct=Decimal("0.10"),
        )
    )


def test_regime_stress_supportability_preserves_source_status_without_breach() -> None:
    context = _regime_stress_context(status=ConstructionMethodStatus.PENDING_REVIEW)

    assert regime_stress_status(context) == ConstructionMethodStatus.PENDING_REVIEW
