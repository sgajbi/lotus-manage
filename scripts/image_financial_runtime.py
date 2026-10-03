"""Fail-closed financial/recovery acceptance of the immutable application image."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

from scripts.docker_image_evidence import inspect_image


ROOT = Path(__file__).resolve().parents[1]
CASES = (
    "tests/integration/dpm/supportability/test_construction_network_recovery.py",
    "tests/integration/dpm/waves/test_wave_network_recovery.py",
)


def validate_image(payload: dict, revision: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("Expected revision must be an exact Git SHA")
    image_id = payload.get("Id", "")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", image_id):
        raise ValueError("An immutable Docker image ID is required")
    config = payload.get("Config") or {}
    if (config.get("Labels") or {}).get("org.opencontainers.image.revision") != revision:
        raise ValueError("Image OCI revision does not match the required revision")
    if config.get("User") != "dpm-user":
        raise ValueError("Expected the shipped non-root application user")
    return image_id


def validate_results(path: Path) -> list[str]:
    cases = ET.parse(path).getroot().findall(".//testcase")
    names = [case.attrib["name"] for case in cases]
    expected = {
        "test_native_network_construction_survives_api_process_replacement[USD]",
        "test_native_network_construction_survives_api_process_replacement[EUR]",
        "test_http_wave_worker_recovers_committed_financial_artifact_after_process_death",
    }
    if len(cases) != 3 or set(names) != expected or any(list(case) for case in cases):
        raise ValueError("All three financial/recovery cases must execute and pass without skips")
    return names


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument(
        "--output-dir", type=Path, default=ROOT / "output/docker-image-evidence/financial-runtime"
    )
    args = parser.parse_args(argv)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    receipt = args.output_dir / "acceptance.json"
    # Never retain a passing receipt from an earlier failed rerun.
    receipt.unlink(missing_ok=True)
    try:
        image_id = validate_image(inspect_image(args.image), args.revision)
        environment = dict(os.environ)
        environment.update(
            DPM_NETWORK_IMAGE_ID=image_id,
            DPM_NETWORK_IMAGE_REVISION=args.revision,
            DPM_POSTGRES_INTEGRATION_REQUIRED="1",
        )
        junit = args.output_dir.resolve() / "results.xml"
        junit.unlink(missing_ok=True)
        subprocess.run(
            [sys.executable, "-m", "pytest", *CASES, "-q", f"--junitxml={junit}"],
            cwd=ROOT,
            env=environment,
            check=True,
        )
        names = validate_results(junit)
        receipt.write_text(
            json.dumps(
                {
                    "schema_version": "1",
                    "proof_type": "image_financial_recovery",
                    "owner": "lotus-manage",
                    "image_id": image_id,
                    "git_revision": args.revision,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "passed_cases": names,
                    "scope": "synthetic HTTP financial calculations and durable process/session recovery",
                    "not_proven": ["actual upstream authority", "live IAM", "production capacity"],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    except (ValueError, OSError, ET.ParseError, subprocess.CalledProcessError) as exc:
        print(f"Image financial acceptance failed: {exc}", file=sys.stderr)
        return 1
    print(f"Image financial acceptance passed: {image_id} @ {args.revision}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
