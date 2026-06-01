from datetime import date
from decimal import Decimal

from src.api.services import mandate_diff
from src.api.services.mandate_errors import DpmMandateDiffUnavailableError
from src.api.services.mandate_diff import (
    DpmMandateDiff,
    DpmMandateFieldChange,
    build_mandate_diff,
    build_mandate_diff_for_versions,
    diff_payloads,
    iter_changed_fields,
    materiality_for_field,
)
from src.core.mandates import DpmMandateDigitalTwin


def _twin(
    *,
    version: str = "3",
    turnover_budget: Decimal = Decimal("0.15"),
) -> DpmMandateDigitalTwin:
    return DpmMandateDigitalTwin.model_validate(
        {
            "mandate_id": "MANDATE_PB_SG_GLOBAL_BAL_001",
            "portfolio_id": "PB_SG_GLOBAL_BAL_001",
            "mandate_version": version,
            "as_of_date": date(2026, 5, 3),
            "base_currency": "SGD",
            "reference_currency": "SGD",
            "risk_profile": "BALANCED",
            "investment_objective": "LONG_TERM_TOTAL_RETURN",
            "time_horizon": "LONG_TERM",
            "model_portfolio_id": "MODEL_PB_SG_GLOBAL_BAL_DPM",
            "model_portfolio_version": "2026.04",
            "constraints": {
                "cash_band_min_weight": "0.02",
                "cash_band_max_weight": "0.10",
                "turnover_budget": turnover_budget,
            },
            "review_policy": {"review_frequency": "QUARTERLY"},
        }
    )


def test_iter_changed_fields_recurses_and_ignores_source_lineage() -> None:
    previous = {
        "mandate_version": "2",
        "constraints": {"turnover_budget": "0.10", "cash_band_min_weight": "0.02"},
        "source_lineage": {"generated_at": "old"},
    }
    current = {
        "mandate_version": "3",
        "constraints": {"turnover_budget": "0.15", "cash_band_min_weight": "0.02"},
        "source_lineage": {"generated_at": "new"},
    }

    assert iter_changed_fields(previous, current) == [
        ("constraints.turnover_budget", "0.10", "0.15"),
        ("mandate_version", "2", "3"),
    ]


def test_diff_payloads_returns_sorted_materiality_changes() -> None:
    changes = diff_payloads(
        {"mandate_version": "2", "constraints": {"turnover_budget": "0.10"}},
        {
            "mandate_version": "3",
            "constraints": {"turnover_budget": "0.15"},
            "display_name": "Global balanced mandate",
        },
    )

    assert [(change.field_path, change.materiality) for change in changes] == [
        ("constraints.turnover_budget", "HIGH"),
        ("display_name", "LOW"),
        ("mandate_version", "MEDIUM"),
    ]


def test_materiality_for_field_uses_private_banking_review_thresholds() -> None:
    assert materiality_for_field("constraints.turnover_budget") == "HIGH"
    assert materiality_for_field("risk_profile") == "HIGH"
    assert materiality_for_field("as_of_date") == "MEDIUM"
    assert materiality_for_field("display_name") == "LOW"


def test_build_mandate_diff_projects_version_comparison() -> None:
    diff = build_mandate_diff(
        mandate_id="MANDATE_PB_SG_GLOBAL_BAL_001",
        previous=_twin(version="2", turnover_budget=Decimal("0.10")),
        current=_twin(version="3", turnover_budget=Decimal("0.15")),
    )

    assert diff.mandate_id == "MANDATE_PB_SG_GLOBAL_BAL_001"
    assert diff.from_version == "2"
    assert diff.to_version == "3"
    assert diff.compared_at.tzinfo is not None
    assert ("constraints.turnover_budget", "HIGH") in [
        (change.field_path, change.materiality) for change in diff.changed_fields
    ]


def test_build_mandate_diff_for_versions_uses_explicit_requested_versions() -> None:
    diff = build_mandate_diff_for_versions(
        mandate_id="MANDATE_PB_SG_GLOBAL_BAL_001",
        versions=[
            _twin(version="3", turnover_budget=Decimal("0.15")),
            _twin(version="2", turnover_budget=Decimal("0.10")),
            _twin(version="1", turnover_budget=Decimal("0.08")),
        ],
        from_version="1",
        to_version="3",
    )

    assert diff.from_version == "1"
    assert diff.to_version == "3"
    assert ("constraints.turnover_budget", "HIGH") in [
        (change.field_path, change.materiality) for change in diff.changed_fields
    ]


def test_build_mandate_diff_for_versions_defaults_to_latest_two_versions() -> None:
    diff = build_mandate_diff_for_versions(
        mandate_id="MANDATE_PB_SG_GLOBAL_BAL_001",
        versions=[
            _twin(version="3", turnover_budget=Decimal("0.15")),
            _twin(version="2", turnover_budget=Decimal("0.10")),
        ],
        from_version=None,
        to_version=None,
    )

    assert diff.from_version == "2"
    assert diff.to_version == "3"


def test_build_mandate_diff_for_versions_requires_complete_version_pair() -> None:
    try:
        build_mandate_diff_for_versions(
            mandate_id="MANDATE_PB_SG_GLOBAL_BAL_001",
            versions=[_twin(version="3")],
            from_version="2",
            to_version=None,
        )
    except DpmMandateDiffUnavailableError as exc:
        assert exc.args == ("DPM_MANDATE_DIFF_REQUIRES_TWO_VERSIONS",)
    else:
        raise AssertionError("Expected mandate diff version-pair validation error.")


def test_build_mandate_diff_for_versions_rejects_unknown_requested_version() -> None:
    try:
        build_mandate_diff_for_versions(
            mandate_id="MANDATE_PB_SG_GLOBAL_BAL_001",
            versions=[_twin(version="3"), _twin(version="2")],
            from_version="1",
            to_version="3",
        )
    except DpmMandateDiffUnavailableError as exc:
        assert exc.args == ("DPM_MANDATE_DIFF_VERSION_NOT_FOUND",)
    else:
        raise AssertionError("Expected mandate diff version-not-found validation error.")


def test_service_preserves_existing_diff_import_surface() -> None:
    from src.api.services import mandate_service

    assert mandate_service.DpmMandateDiff is DpmMandateDiff
    assert mandate_service.DpmMandateFieldChange is DpmMandateFieldChange


def test_mandate_diff_exports_public_helper_surface() -> None:
    assert set(mandate_diff.__all__) == {
        "DpmMandateDiff",
        "DpmMandateFieldChange",
        "build_mandate_diff",
        "build_mandate_diff_for_versions",
        "diff_payloads",
        "iter_changed_fields",
        "materiality_for_field",
    }
