from __future__ import annotations

from pathlib import Path

from scripts.test_family_inventory import (
    build_inventory,
    classify_test_file,
    validate_inventory,
)


def test_test_family_classifier_covers_representative_proof_families() -> None:
    examples = {
        "tests/unit/dpm/api/test_portfolio_memory_api.py": "api_runtime",
        "tests/unit/test_domain_data_product_contracts.py": "contract_governance",
        "tests/unit/test_observability_contracts.py": "observability_security",
        "tests/unit/dpm/waves/test_wave_lifecycle_commands.py": ("domain_lifecycle_methodology"),
        "tests/integration/test_health.py": "integration_runtime",
        "tests/unit/test_new_backlog.py": "uncategorized",
    }

    for path, expected_family in examples.items():
        assert classify_test_file(Path(path)) == expected_family


def test_test_family_inventory_counts_files_by_family(tmp_path: Path) -> None:
    tests_root = tmp_path / "tests"
    for relative in [
        "unit/dpm/api/test_portfolio_memory_api.py",
        "unit/test_domain_data_product_contracts.py",
        "unit/test_observability_contracts.py",
        "unit/dpm/waves/test_wave_lifecycle_commands.py",
        "integration/test_health.py",
        "unit/test_new_backlog.py",
    ]:
        path = tests_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("def test_placeholder():\n    assert True\n", encoding="utf-8")

    inventory = build_inventory(tests_root)

    assert inventory["families"] == {
        "api_runtime": 1,
        "contract_governance": 1,
        "domain_lifecycle_methodology": 1,
        "integration_runtime": 1,
        "observability_security": 1,
    }
    assert inventory["uncategorized"] == ["tests/unit/test_new_backlog.py"]


def test_test_family_inventory_validation_blocks_family_loss_and_new_uncategorized() -> None:
    inventory = {
        "families": {
            "api_runtime": 1,
            "contract_governance": 2,
            "domain_lifecycle_methodology": 3,
            "integration_runtime": 4,
            "observability_security": 0,
        },
        "uncategorized": ["tests/unit/test_new_backlog.py"],
    }
    baseline = {
        "minimum_family_counts": {
            "api_runtime": 2,
            "contract_governance": 2,
            "observability_security": 1,
        },
        "allowed_uncategorized": [],
    }

    issues = validate_inventory(
        inventory,
        baseline,
        baseline_path=Path("quality/test_family_inventory_baseline.json"),
    )

    assert issues == [
        "api_runtime: current test-file count 1 is below baseline floor 2",
        "observability_security: current test-file count 0 is below baseline floor 1",
        "uncategorized: new files require classification or baseline exception in "
        "quality/test_family_inventory_baseline.json: ['tests/unit/test_new_backlog.py']",
    ]
