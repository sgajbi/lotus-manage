from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
METHODOLOGY_PATH = ROOT / "docs" / "methodologies" / "pm-quality" / "scoring-and-fairness.md"
METHODOLOGY_LINK = "docs/methodologies/pm-quality/scoring-and-fairness.md"


def test_pm_quality_methodology_uses_required_v3_structure() -> None:
    methodology = METHODOLOGY_PATH.read_text(encoding="utf-8")

    required_headings = [
        "## Metric",
        "## Endpoint and Mode Coverage",
        "## Inputs",
        "## Upstream Data Sources",
        "## Unit Conventions",
        "## Variable Dictionary",
        "## Methodology and Formulas",
        "## Step-by-Step Computation",
        "## Validation and Failure Behavior",
        "## Configuration Options",
        "## Outputs",
        "## Worked Example",
    ]
    positions = [methodology.index(heading) for heading in required_headings]

    assert positions == sorted(positions)
    assert methodology.count("## ") == len(required_headings)


def test_pm_quality_methodology_publishes_formula_validation_and_examples() -> None:
    methodology = METHODOLOGY_PATH.read_text(encoding="utf-8")

    required_terms = [
        "pm_quality_scoring_fairness.v3",
        "PmOperatingQualityScoreRun:v1",
        "PmOperatingQualityFairnessAnalysis:v1",
        "State-to-score mapping",
        "`Q_raw = sum(S_i * w_i for scorable indicators) / sum(w_i for scorable indicators)`",
        "`Q = round_half_up(Q_raw, 2 decimal places)`",
        "ROUND_HALF_UP",
        "source_ref.source_version",
        "PM_QUALITY_LOOKBACK_WINDOW_EVIDENCE_DATE_REQUIRED",
        "PM_QUALITY_FAIRNESS_SPREAD_REVIEW_REQUIRED",
        "not an HR",
        "protected",
        "classes",
        "`score` | `round_half_up(7800 / 100, 2)` | `78.00`",
        "`observed_average_score_spread = round_half_up(86.00 - 75.00, 2) = 11.00`",
        "Update PM-quality domain tests and golden examples.",
    ]

    missing = [term for term in required_terms if term not in methodology]
    assert missing == []


def test_pm_quality_methodology_is_linked_from_reader_surfaces() -> None:
    surfaces = {
        "README.md": ROOT / "README.md",
        "wiki/Current-State.md": ROOT / "wiki" / "Current-State.md",
        "wiki/Endpoint-Certification.md": ROOT / "wiki" / "Endpoint-Certification.md",
        "wiki/Operations-Runbook.md": ROOT / "wiki" / "Operations-Runbook.md",
        "docs/operations-runbook.md": ROOT / "docs" / "operations-runbook.md",
        "contracts/domain-data-products/README.md": ROOT
        / "contracts"
        / "domain-data-products"
        / "README.md",
    }

    missing = [
        surface_name
        for surface_name, path in surfaces.items()
        if METHODOLOGY_LINK not in path.read_text(encoding="utf-8")
    ]

    assert missing == []
