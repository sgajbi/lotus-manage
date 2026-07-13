from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast


ROOT = Path(__file__).resolve().parents[1]
TESTS_ROOT = ROOT / "tests"
DEFAULT_BASELINE_PATH = ROOT / "quality" / "test_family_inventory_baseline.json"

FAMILY_DESCRIPTIONS = {
    "api_runtime": "API route, OpenAPI, live API, health, and runtime surface proof.",
    "contract_governance": "Contract, documentation, workflow, CI, and governance proof.",
    "observability_security": "Observability, audit, warning, security, and telemetry proof.",
    "domain_lifecycle_methodology": "Domain, lifecycle, calculation, source, and methodology proof.",
    "integration_runtime": "Integration, E2E, Docker, migration, Postgres, and runtime parity proof.",
}

CONTRACT_GOVERNANCE_TOKENS = (
    "clean_generated_artifacts",
    "contract",
    "contracts",
    "coverage_gate",
    "documentation_current_state",
    "domain_data_product",
    "duplicate_implementation",
    "evidence_script",
    "trust_telemetry",
    "workflow_policy",
    "ci_workflow",
    "service_boundary",
    "service_layer_architecture_boundaries",
    "router_infrastructure",
    "openapi_quality",
    "api_vocabulary",
    "no_alias",
    "test_family_inventory",
    "methodology_docs",
    "operations_runbook",
    "runbook",
)
OBSERVABILITY_SECURITY_TOKENS = (
    "observability",
    "security",
    "audit",
    "warning",
    "telemetry",
    "enterprise",
    "correlation",
)
API_RUNTIME_TOKENS = (
    "api",
    "health",
    "validate_live_api",
    "openapi",
    "service_contract",
)
INTEGRATION_RUNTIME_TOKENS = (
    "integration",
    "e2e",
    "docker",
    "migration",
    "postgres",
    "production_cutover",
    "run_demo_pack",
    "live",
)
DOMAIN_PATH_TOKENS = (
    "tests/unit/core",
    "tests/unit/dpm",
    "tests/unit/infrastructure",
)


@dataclass(frozen=True)
class ClassifiedTestFile:
    path: str
    family: str


def _normalized_path(path: Path) -> str:
    return path.as_posix()


def classify_test_file(path: Path) -> str:
    normalized = _normalized_path(path)
    lowered = normalized.lower()
    name = path.name.lower()

    if normalized.startswith(("tests/integration/", "tests/e2e/")) or any(
        token in lowered for token in INTEGRATION_RUNTIME_TOKENS
    ):
        return "integration_runtime"
    if any(token in name or token in lowered for token in OBSERVABILITY_SECURITY_TOKENS):
        return "observability_security"
    if any(token in name or token in lowered for token in CONTRACT_GOVERNANCE_TOKENS):
        return "contract_governance"
    if any(token in name or token in lowered for token in API_RUNTIME_TOKENS):
        return "api_runtime"
    if any(token in lowered for token in DOMAIN_PATH_TOKENS):
        return "domain_lifecycle_methodology"
    return "uncategorized"


def iter_test_files(tests_root: Path = TESTS_ROOT) -> list[Path]:
    return sorted(path for path in tests_root.rglob("test_*.py") if "__pycache__" not in path.parts)


def build_inventory(tests_root: Path = TESTS_ROOT) -> dict[str, Any]:
    classified: list[ClassifiedTestFile] = []
    root = tests_root.parent
    for path in iter_test_files(tests_root):
        relative = path.relative_to(root)
        classified.append(
            ClassifiedTestFile(
                path=relative.as_posix(),
                family=classify_test_file(relative),
            )
        )

    families = {family: 0 for family in FAMILY_DESCRIPTIONS}
    uncategorized: list[str] = []
    files: dict[str, str] = {}
    for item in classified:
        files[item.path] = item.family
        if item.family == "uncategorized":
            uncategorized.append(item.path)
            continue
        families[item.family] += 1

    return {
        "schema_version": 1,
        "total_test_files": len(classified),
        "family_descriptions": FAMILY_DESCRIPTIONS,
        "families": dict(sorted(families.items())),
        "uncategorized_count": len(uncategorized),
        "uncategorized": sorted(uncategorized),
        "files": dict(sorted(files.items())),
    }


def _load_baseline(path: Path) -> dict[str, Any]:
    return cast("dict[str, Any]", json.loads(path.read_text(encoding="utf-8")))


def validate_inventory(
    inventory: dict[str, Any],
    baseline: dict[str, Any],
    *,
    baseline_path: Path,
) -> list[str]:
    issues: list[str] = []
    minimums = baseline.get("minimum_family_counts", {})
    families = inventory.get("families", {})
    for family, minimum in sorted(minimums.items()):
        current = int(families.get(family, 0))
        if current < int(minimum):
            issues.append(
                f"{family}: current test-file count {current} is below baseline floor {minimum}"
            )

    allowed_uncategorized = set(baseline.get("allowed_uncategorized", []))
    current_uncategorized = set(inventory.get("uncategorized", []))
    unexpected = sorted(current_uncategorized - allowed_uncategorized)
    if unexpected:
        issues.append(
            "uncategorized: new files require classification or baseline exception in "
            f"{baseline_path.as_posix()}: {unexpected}"
        )
    return issues


def print_summary(inventory: dict[str, Any]) -> None:
    print(f"Total test files: {inventory['total_test_files']}")
    for family, count in inventory["families"].items():
        print(f"- {family}: {count}")
    print(f"- uncategorized: {inventory['uncategorized_count']}")
    if inventory["uncategorized"]:
        print("Uncategorized files:")
        for path in inventory["uncategorized"]:
            print(f"  - {path}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inventory lotus-manage test proof-family breadth."
    )
    parser.add_argument("--tests-root", type=Path, default=TESTS_ROOT)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE_PATH)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--json", action="store_true", dest="json_output")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    inventory = build_inventory(args.tests_root)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(inventory, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    if args.json_output:
        print(json.dumps(inventory, indent=2, sort_keys=True))
    else:
        print_summary(inventory)
    if not args.check:
        return 0

    baseline = _load_baseline(args.baseline)
    issues = validate_inventory(inventory, baseline, baseline_path=args.baseline)
    if issues:
        print("Test-family inventory gate failed:")
        for issue in issues:
            print(f"- {issue}")
        return 1
    print("Test-family inventory gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
