from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCAL_TELEMETRY_DIR = ROOT / "contracts" / "trust-telemetry"
LOCAL_PRODUCT_DECLARATION_PATH = (
    ROOT / "contracts" / "domain-data-products" / "lotus-manage-products.v1.json"
)
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


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _product_id(product: dict) -> str:
    return f"lotus-manage:{product['product_name']}:{product['product_version']}"


def _route_path(route: object) -> str:
    if not isinstance(route, str):
        return ""
    parts = route.split(maxsplit=1)
    return parts[1] if len(parts) == 2 else route


def _route_foundation_requires_certified_route_exclusion(route_foundation: dict) -> bool:
    return (
        route_foundation.get("supportability_status") == "not_certified"
        or route_foundation.get("supported_feature_promoted") is False
        or bool(route_foundation.get("certification_blockers"))
    )


def _validate_route_foundation_boundaries(
    source_directory: Path,
    *,
    product_declaration_path: Path,
) -> list[str]:
    if not product_declaration_path.exists():
        return [f"{product_declaration_path}: product declaration does not exist"]

    issues: list[str] = []
    declaration = _load_json(product_declaration_path)
    snapshots_by_product_id: dict[str, tuple[Path, dict]] = {}
    for snapshot_path in sorted(source_directory.glob("*.json")):
        payload = _load_json(snapshot_path)
        product_id = payload.get("product_id")
        if isinstance(product_id, str):
            snapshots_by_product_id[product_id] = (snapshot_path, payload)

    for product in declaration.get("products", []):
        if not isinstance(product, dict):
            continue
        route_foundations = product.get("route_foundations", [])
        if not route_foundations:
            continue

        product_id = _product_id(product)
        snapshot = snapshots_by_product_id.get(product_id)
        if snapshot is None:
            continue

        snapshot_path, telemetry = snapshot
        telemetry_route_foundations = telemetry.get("route_foundations", [])
        if telemetry_route_foundations != route_foundations:
            issues.append(
                f"{snapshot_path}: route_foundations must match {product_declaration_path}"
            )

        current_routes = set(product.get("current_routes", []))
        serving_routes = set(telemetry.get("serving_routes", []))
        for index, route_foundation in enumerate(route_foundations):
            if not isinstance(route_foundation, dict):
                issues.append(
                    f"{product_declaration_path}: products[{product_id}].route_foundations[{index}] must be an object"
                )
                continue
            if not _route_foundation_requires_certified_route_exclusion(route_foundation):
                continue

            route = _route_path(route_foundation.get("route"))
            if route in current_routes:
                issues.append(
                    f"{product_declaration_path}: not-certified route foundation {route} must not be listed in current_routes for {product_id}"
                )
            if route in serving_routes:
                issues.append(
                    f"{snapshot_path}: not-certified route foundation {route} must not be listed in serving_routes for {product_id}"
                )

    return issues


def _validate_deferred_mesh_maturity_boundaries(
    source_directory: Path,
    *,
    product_declaration_path: Path,
) -> list[str]:
    if not product_declaration_path.exists():
        return [f"{product_declaration_path}: product declaration does not exist"]

    issues: list[str] = []
    declaration = _load_json(product_declaration_path)
    snapshots_by_product_id: dict[str, tuple[Path, dict]] = {}
    for snapshot_path in sorted(source_directory.glob("*.json")):
        payload = _load_json(snapshot_path)
        product_id = payload.get("product_id")
        if isinstance(product_id, str):
            snapshots_by_product_id[product_id] = (snapshot_path, payload)

    for product in declaration.get("products", []):
        if not isinstance(product, dict):
            continue
        mesh_posture = product.get("mesh_maturity_posture")
        if not isinstance(mesh_posture, dict):
            continue
        if not (
            mesh_posture.get("maturity_state") == "deferred"
            or mesh_posture.get("maturity_wave") == "future_wave"
        ):
            continue

        product_id = _product_id(product)
        snapshot = snapshots_by_product_id.get(product_id)
        if snapshot is None:
            continue
        snapshot_path, telemetry = snapshot
        if telemetry.get("data_quality_status") != "quality_blocked":
            issues.append(
                f"{snapshot_path}: deferred mesh product {product_id} must publish data_quality_status=quality_blocked"
            )
        if telemetry.get("lineage", {}).get("evidence_access_class") != "operator_only":
            issues.append(
                f"{snapshot_path}: deferred mesh product {product_id} must publish operator_only evidence"
            )
        if telemetry.get("blocking", {}).get("blocked") is not True:
            issues.append(
                f"{snapshot_path}: deferred mesh product {product_id} must publish blocking.blocked=true"
            )
        certification_limits = telemetry.get("certification_limits", {})
        if certification_limits.get("certification_ready") is not False:
            issues.append(
                f"{snapshot_path}: deferred mesh product {product_id} must publish certification_ready=false"
            )
        if certification_limits.get("platform_maturity_state") != mesh_posture.get(
            "maturity_state"
        ):
            issues.append(
                f"{snapshot_path}: platform_maturity_state must match {product_declaration_path}"
            )
        if certification_limits.get("maturity_wave") != mesh_posture.get("maturity_wave"):
            issues.append(f"{snapshot_path}: maturity_wave must match {product_declaration_path}")

    return issues


def validate_repo_native_trust_telemetry(
    source_directory: Path = LOCAL_TELEMETRY_DIR,
    *,
    product_declaration_path: Path = LOCAL_PRODUCT_DECLARATION_PATH,
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
        platform_issues = validator.validate_trust_telemetry_path(
            source_directory,
            catalog_path=catalog_path,
            trust_metadata_registry_path=PLATFORM_TRUST_METADATA_REGISTRY_PATH,
            semantics_registry_path=PLATFORM_SEMANTICS_REGISTRY_PATH,
        )
        return (
            platform_issues
            + _validate_route_foundation_boundaries(
                source_directory,
                product_declaration_path=product_declaration_path,
            )
            + _validate_deferred_mesh_maturity_boundaries(
                source_directory,
                product_declaration_path=product_declaration_path,
            )
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
