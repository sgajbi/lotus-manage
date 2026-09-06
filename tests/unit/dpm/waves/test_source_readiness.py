from datetime import date
from decimal import Decimal

from src.core.mandates import (
    DpmMandateConstraintSet,
    DpmMandateDigitalTwin,
    DpmMandateHealthInput,
    DpmMandateReviewPolicy,
    DpmSourceProductLineage,
    calculate_mandate_health,
)
from src.core.waves.models import DpmRebalanceWaveItem
from src.core.waves.source_readiness import (
    _blocked_health_classification,
    _degraded_health_classification,
    _health_blocks_source_readiness,
    _health_degrades_source_readiness,
    _health_is_stale,
    _ready_health_classification,
    _review_required_health_classification,
    _stale_health_classification,
    classify_wave_item_source_readiness,
)


def _twin(*, lineage_record_id: str | None = "core-binding-001") -> DpmMandateDigitalTwin:
    return DpmMandateDigitalTwin(
        mandate_id="MANDATE_PB_SG_GLOBAL_BAL_001",
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        mandate_version="3",
        as_of_date=date(2026, 5, 3),
        base_currency="SGD",
        reference_currency="SGD",
        risk_profile="BALANCED",
        investment_objective="LONG_TERM_TOTAL_RETURN",
        time_horizon="LONG_TERM",
        model_portfolio_id="MODEL_PB_SG_GLOBAL_BAL_DPM",
        constraints=DpmMandateConstraintSet(
            # A fully sourced twin: both contractual limits stated, so these
            # cases exercise SOURCE readiness rather than the unsourced-limit
            # rule (issue #664). A twin missing either limit is PENDING_REVIEW
            # by design, which is covered in the mandate-health tests.
            cash_band_min_weight=Decimal("0.02"),
            cash_band_max_weight=Decimal("0.10"),
            turnover_budget=Decimal("0.15"),
        ),
        review_policy=DpmMandateReviewPolicy(next_review_due_date=date(2026, 6, 30)),
        source_lineage=[
            DpmSourceProductLineage(
                product_name="DPM_CORE_MANDATE_BINDING",
                product_version="1.0.0",
                source_record_id=lineage_record_id,
                data_quality_status="READY",
            )
        ],
    )


def _item() -> DpmRebalanceWaveItem:
    return DpmRebalanceWaveItem(
        wave_item_id="dwi_source_readiness",
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        state="CANDIDATE",
    )


def test_source_readiness_health_classification_helpers_preserve_posture() -> None:
    twin = _twin(lineage_record_id=None)
    ready_health = calculate_mandate_health(
        DpmMandateHealthInput(
            twin=twin,
            current_weights={"CASH": Decimal("0.05")},
            target_weights={"CASH": Decimal("0.05")},
            cash_weight=Decimal("0.05"),
        )
    )
    stale_health = ready_health.model_copy(update={"as_of_date": date(2026, 5, 2)})
    blocked_health = calculate_mandate_health(
        DpmMandateHealthInput(
            twin=twin,
            current_weights={"CASH": Decimal("0.05")},
            target_weights={"CASH": Decimal("0.05")},
            cash_weight=Decimal("0.05"),
            source_readiness_state="UNAVAILABLE",
        )
    )
    degraded_health = calculate_mandate_health(
        DpmMandateHealthInput(
            twin=twin,
            current_weights={"CASH": Decimal("0.05")},
            target_weights={"CASH": Decimal("0.05")},
            cash_weight=Decimal("0.05"),
            source_readiness_state="DEGRADED",
        )
    )
    review_health = calculate_mandate_health(
        DpmMandateHealthInput(
            twin=twin,
            current_weights={"CASH": Decimal("0.05")},
            target_weights={"CASH": Decimal("0.05")},
            cash_weight=Decimal("0.05"),
            approval_required=True,
        )
    )

    assert _health_is_stale(health=stale_health, wave_as_of_date="2026-05-03")
    assert _stale_health_classification(
        health=stale_health,
        wave_as_of_date="2026-05-03",
    ) == (
        "SOURCE_DEGRADED",
        ["MANDATE_HEALTH_STALE"],
        {
            "source_owner": "lotus-manage",
            "required_action": "REFRESH_MANDATE_HEALTH",
            "health_as_of_date": "2026-05-02",
            "wave_as_of_date": "2026-05-03",
        },
    )
    assert _health_blocks_source_readiness(
        health=blocked_health,
        health_state=blocked_health.health_state.value,
    )
    assert _blocked_health_classification(
        health=blocked_health,
        health_state=blocked_health.health_state.value,
    )[0:2] == (
        "SOURCE_BLOCKED",
        ["MANDATE_HEALTH_BLOCKED", "SOURCE_READINESS_UNAVAILABLE"],
    )
    assert _health_degrades_source_readiness(health=degraded_health)
    assert _degraded_health_classification(
        health=degraded_health,
        health_state=degraded_health.health_state.value,
    )[0:2] == ("SOURCE_DEGRADED", ["SOURCE_READINESS_DEGRADED"])
    assert _review_required_health_classification(
        health=review_health,
        health_state=review_health.health_state.value,
    )[0:2] == ("REVIEW_REQUIRED", ["MANDATE_HEALTH_PENDING_REVIEW"])
    assert _ready_health_classification(
        health=ready_health,
        health_state=ready_health.health_state.value,
    )[0:2] == ("SOURCE_READY", ["SOURCE_READINESS_READY"])


def test_source_readiness_blocks_missing_twin_without_synthetic_readiness() -> None:
    classified = classify_wave_item_source_readiness(
        item=_item(),
        wave_as_of_date="2026-05-03",
        mandate_twin=None,
        mandate_health=None,
    )

    assert classified.state == "SOURCE_BLOCKED"
    assert classified.reason_codes == ["MANDATE_DIGITAL_TWIN_MISSING"]
    assert classified.diagnostics["missing_source_family"] == "MANDATE_DIGITAL_TWIN"


def test_source_readiness_degrades_missing_or_stale_health() -> None:
    twin = _twin()
    missing = classify_wave_item_source_readiness(
        item=_item(),
        wave_as_of_date="2026-05-03",
        mandate_twin=twin,
        mandate_health=None,
    )
    stale_health = calculate_mandate_health(
        DpmMandateHealthInput(
            twin=twin.model_copy(update={"as_of_date": date(2026, 5, 2)}),
            current_weights={"CASH": Decimal("0.05")},
            target_weights={"CASH": Decimal("0.05")},
            cash_weight=Decimal("0.05"),
        )
    )
    stale = classify_wave_item_source_readiness(
        item=_item(),
        wave_as_of_date="2026-05-03",
        mandate_twin=twin,
        mandate_health=stale_health,
    )

    assert missing.state == "SOURCE_DEGRADED"
    assert missing.reason_codes == ["MANDATE_HEALTH_MISSING"]
    assert stale.state == "SOURCE_DEGRADED"
    assert stale.reason_codes == ["MANDATE_HEALTH_STALE"]
    assert stale.diagnostics["health_as_of_date"] == "2026-05-02"


def test_source_readiness_classifies_blocked_degraded_review_and_ready_health() -> None:
    twin_without_lineage_record = _twin(lineage_record_id=None)
    cases = [
        (
            DpmMandateHealthInput(
                twin=twin_without_lineage_record,
                current_weights={"CASH": Decimal("0.05")},
                target_weights={"CASH": Decimal("0.05")},
                cash_weight=Decimal("0.05"),
                source_readiness_state="UNAVAILABLE",
            ),
            "SOURCE_BLOCKED",
            "SOURCE_READINESS_UNAVAILABLE",
        ),
        (
            DpmMandateHealthInput(
                twin=twin_without_lineage_record,
                current_weights={"CASH": Decimal("0.05")},
                target_weights={"CASH": Decimal("0.05")},
                cash_weight=Decimal("0.05"),
                source_readiness_state="DEGRADED",
            ),
            "SOURCE_DEGRADED",
            "SOURCE_READINESS_DEGRADED",
        ),
        (
            DpmMandateHealthInput(
                twin=twin_without_lineage_record,
                current_weights={"CASH": Decimal("0.05")},
                target_weights={"CASH": Decimal("0.05")},
                cash_weight=Decimal("0.05"),
                approval_required=True,
            ),
            "REVIEW_REQUIRED",
            "MANDATE_HEALTH_PENDING_REVIEW",
        ),
        (
            DpmMandateHealthInput(
                twin=twin_without_lineage_record,
                current_weights={"CASH": Decimal("0.05")},
                target_weights={"CASH": Decimal("0.05")},
                cash_weight=Decimal("0.05"),
            ),
            "SOURCE_READY",
            "SOURCE_READINESS_READY",
        ),
    ]

    classified = [
        classify_wave_item_source_readiness(
            item=_item(),
            wave_as_of_date="2026-05-03",
            mandate_twin=twin_without_lineage_record,
            mandate_health=calculate_mandate_health(health_input),
        )
        for health_input, _state, _reason in cases
    ]

    assert [(item.state, item.reason_codes[-1]) for item in classified] == [
        (state, reason) for _input, state, reason in cases
    ]
    for item in classified:
        assert all(ref.source_id != "" for ref in item.source_refs)
