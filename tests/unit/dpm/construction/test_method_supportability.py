from decimal import Decimal

from src.api.services.construction_method_supportability import regime_stress_status
from src.core.construction.models import AuthoritativeRegimeStressContext
from src.core.construction.vocabulary import ConstructionMethodStatus


def test_regime_stress_supportability_marks_threshold_breach_pending_review() -> None:
    context = AuthoritativeRegimeStressContext(
        supportability_status=ConstructionMethodStatus.READY,
        source_system="lotus-risk",
        scenario_pack_id="regime_pack_1",
        worst_case_loss_pct=Decimal("0.12"),
        maximum_allowed_loss_pct=Decimal("0.10"),
        reason_codes=["SCENARIO_PACK_READY"],
    )

    assert regime_stress_status(context) == ConstructionMethodStatus.PENDING_REVIEW
