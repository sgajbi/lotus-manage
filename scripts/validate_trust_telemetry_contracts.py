from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCAL_TELEMETRY_DIR = ROOT / "contracts" / "trust-telemetry"
PLATFORM_ROOT = ROOT.parent / "lotus-platform"
PLATFORM_AUTOMATION_DIR = PLATFORM_ROOT / "automation"
PLATFORM_VALIDATOR_PATH = PLATFORM_AUTOMATION_DIR / "validate_trust_telemetry.py"
PLATFORM_CATALOG_PATH = PLATFORM_ROOT / "generated" / "domain-product-catalog.json"
PLATFORM_DISCOVERY_PATH = PLATFORM_AUTOMATION_DIR / "domain_product_discovery.py"
PLATFORM_VOCABULARY_DIR = PLATFORM_ROOT / "platform-contracts" / "domain-vocabulary"
PLATFORM_TRUST_METADATA_REGISTRY_PATH = (
    PLATFORM_VOCABULARY_DIR / "domain-data-product-trust-metadata.v1.json"
)
PLATFORM_SEMANTICS_REGISTRY_PATH = PLATFORM_VOCABULARY_DIR / "domain-data-product-semantics.v1.json"


def _load_platform_validator():
    if not PLATFORM_VALIDATOR_PATH.exists():
        raise FileNotFoundError(
            f"Platform trust telemetry validator not found at {PLATFORM_VALIDATOR_PATH}. "
            "Ensure the sibling lotus-platform repository is available."
        )

    automation_path = str(PLATFORM_AUTOMATION_DIR)
    inserted = automation_path not in sys.path
    if inserted:
        sys.path.insert(0, automation_path)
    try:
        spec = importlib.util.spec_from_file_location(
            "lotus_platform_trust_telemetry_validator",
            PLATFORM_VALIDATOR_PATH,
        )
        if spec is None or spec.loader is None:
            raise ImportError(
                f"Unable to load platform trust telemetry validator from {PLATFORM_VALIDATOR_PATH}"
            )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        if inserted:
            sys.path.remove(automation_path)


def _load_platform_discovery():
    if not PLATFORM_DISCOVERY_PATH.exists():
        raise FileNotFoundError(
            f"Platform domain-product discovery generator not found at {PLATFORM_DISCOVERY_PATH}. "
            "Ensure the sibling lotus-platform repository is available."
        )

    automation_path = str(PLATFORM_AUTOMATION_DIR)
    inserted = automation_path not in sys.path
    if inserted:
        sys.path.insert(0, automation_path)
    try:
        spec = importlib.util.spec_from_file_location(
            "lotus_platform_domain_product_discovery",
            PLATFORM_DISCOVERY_PATH,
        )
        if spec is None or spec.loader is None:
            raise ImportError(
                f"Unable to load platform domain-product discovery generator from {PLATFORM_DISCOVERY_PATH}"
            )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        if inserted:
            sys.path.remove(automation_path)


def platform_validation_dependencies_available() -> bool:
    return all(
        path.exists()
        for path in (
            PLATFORM_VALIDATOR_PATH,
            PLATFORM_CATALOG_PATH,
            PLATFORM_TRUST_METADATA_REGISTRY_PATH,
            PLATFORM_SEMANTICS_REGISTRY_PATH,
        )
    )


def validate_repo_native_trust_telemetry(
    source_directory: Path = LOCAL_TELEMETRY_DIR,
) -> list[str]:
    source_directory = source_directory.resolve()
    if not source_directory.exists():
        return [f"{source_directory}: repo-native trust telemetry directory does not exist"]
    if not list(source_directory.glob("*.json")):
        return [f"{source_directory}: no repo-native trust telemetry snapshot files were found"]

    validator = _load_platform_validator()
    with tempfile.TemporaryDirectory(prefix="lotus-manage-trust-telemetry-catalog-") as temp_dir:
        catalog_path = PLATFORM_CATALOG_PATH
        if PLATFORM_DISCOVERY_PATH.exists():
            discovery = _load_platform_discovery()
            output_directory = Path(temp_dir)
            discovery.write_discovery_artifacts(output_directory=output_directory)
            catalog_path = output_directory / discovery.CATALOG_FILENAME
        return validator.validate_trust_telemetry_path(
            source_directory,
            catalog_path=catalog_path,
            trust_metadata_registry_path=PLATFORM_TRUST_METADATA_REGISTRY_PATH,
            semantics_registry_path=PLATFORM_SEMANTICS_REGISTRY_PATH,
        )


def main() -> int:
    issues = validate_repo_native_trust_telemetry()
    if issues:
        for issue in issues:
            print(issue)
        return 1

    snapshot_count = len(list(LOCAL_TELEMETRY_DIR.glob("*.json")))
    print(
        f"Validated {snapshot_count} repo-native trust telemetry snapshot(s) "
        f"in {LOCAL_TELEMETRY_DIR}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
