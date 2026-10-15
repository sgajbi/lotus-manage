from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT / "output" / "docker-image-evidence"
BASE_PLATFORM = "linux/amd64"
BASE_INDEX_DIGEST = "sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1"
BASE_IMAGE = f"docker.io/library/python:3.12.15-slim-trixie@{BASE_INDEX_DIGEST}"
BASE_SELECTION = {
    "original_repository": "docker.io/library/python",
    "distribution_repository": "public.ecr.aws/docker/library/python",
    "image_digest": BASE_INDEX_DIGEST,
    "manifest_kind": "index",
    "platform": BASE_PLATFORM,
    "platform_manifest_digest": (
        "sha256:2b4f19dae3a777dfc3b76730bda1e82e1f66ab2a2686fa93ca78edbfb4f04ffe"
    ),
    "platform_config_digest": (
        "sha256:df18428df8a0f9189c84e7424d214b4c50092af1f9dca5842a00c41c39bda316"
    ),
    "original_source_selection_approval": (
        "https://github.com/sgajbi/lotus-platform/issues/945#issuecomment-6186826582"
    ),
    "approval": "https://github.com/sgajbi/lotus-platform/issues/945#issuecomment-6089421841",
    "manifest_observation_sha256": (
        "49a6ec2252c2283133c510f66864c47b4942bcbef94e44a399d9de4488e606a5"
    ),
    "policy_revision": "842b80eb33d93a40f7318f5d97d92541440c43e6",
}


def validate_base_selection(base_image: str, platform: str) -> dict[str, str]:
    """Admit only Manage's independently approved same-runtime build input."""
    if base_image != BASE_IMAGE or platform != BASE_PLATFORM:
        raise ValueError("Python base reference/platform must equal the reviewed Manage selection")
    return {"reference": base_image, **BASE_SELECTION}


def validate_dockerfile_base(
    dockerfile: Path, base_image: str = BASE_IMAGE, platform: str = BASE_PLATFORM
) -> dict[str, str]:
    selection = validate_base_selection(base_image, platform)
    content = dockerfile.read_bytes()
    from_lines = [
        line.strip()
        for line in content.decode("utf-8").splitlines()
        if line.strip() and line.split()[0].upper() == "FROM"
    ]
    if from_lines != [f"FROM --platform={platform} {base_image}"]:
        raise ValueError(
            "Dockerfile requires one reviewed literal FROM; base overrides are unsupported"
        )
    return {
        **selection,
        "dockerfile_sha256": hashlib.sha256(content).hexdigest(),
        "evidence_posture": "validated_build_input_not_base_layer_attestation",
    }


def _run_json(command: list[str]) -> Any:
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def inspect_image(image: str) -> dict[str, Any]:
    inspected = _run_json(["docker", "image", "inspect", image])
    if not isinstance(inspected, list) or not inspected:
        raise ValueError(f"Docker image not found: {image}")
    payload = inspected[0]
    if not isinstance(payload, dict):
        raise ValueError(f"Docker image inspect returned unexpected payload for {image}")
    return payload


def _tool_status(tool: str) -> dict[str, Any]:
    path = shutil.which(tool)
    return {
        "tool": tool,
        "available": path is not None,
        "path": path,
    }


def _run_optional_report(
    *,
    tool: str,
    command: list[str],
    output_path: Path,
    status_path: Path,
) -> dict[str, Any]:
    status = _tool_status(tool)
    if not status["available"]:
        status.update(
            {
                "status": "not_available_report_only",
                "output_path": output_path.as_posix(),
            }
        )
        _write_json(status_path, status)
        return status
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if result.stdout:
        output_path.write_text(result.stdout, encoding="utf-8")
    status.update(
        {
            "status": "passed" if result.returncode == 0 else "failed",
            "returncode": result.returncode,
            "stderr": result.stderr[-4000:],
            "output_path": output_path.as_posix(),
        }
    )
    _write_json(status_path, status)
    return status


def build_release_manifest(
    *,
    image: str,
    image_inspect: dict[str, Any],
    git_sha: str,
    git_branch: str,
    build_timestamp: str,
    repo_url: str,
    ci_pipeline_id: str,
    base_image: str = BASE_IMAGE,
    platform: str = BASE_PLATFORM,
) -> dict[str, Any]:
    selection = validate_base_selection(base_image, platform)
    actual_platform = f"{image_inspect.get('Os', '')}/{image_inspect.get('Architecture', '')}"
    if actual_platform != platform:
        raise ValueError("Final image inspect platform differs from the reviewed build platform")
    labels = image_inspect.get("Config", {}).get("Labels") or {}
    repo_digests = image_inspect.get("RepoDigests") or []
    image_id = str(image_inspect.get("Id", "unknown"))
    return {
        "service_name": "lotus-manage",
        "image": image,
        "image_id": image_id,
        "image_digest": repo_digests[0] if repo_digests else image_id,
        "repo_digests": repo_digests,
        "git_commit_sha": git_sha,
        "git_branch": git_branch,
        "build_timestamp": build_timestamp,
        "repo_url": repo_url,
        "ci_pipeline_id": ci_pipeline_id,
        "oci_labels": labels,
        "platform": actual_platform,
        "selected_base": selection,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def write_docker_image_evidence(
    *,
    image: str,
    output_dir: Path,
    git_sha: str,
    git_branch: str,
    build_timestamp: str,
    repo_url: str,
    ci_pipeline_id: str,
    dockerfile: Path = ROOT / "Dockerfile",
    base_image: str = BASE_IMAGE,
    platform: str = BASE_PLATFORM,
) -> dict[str, Any]:
    selection = validate_dockerfile_base(dockerfile, base_image, platform)
    image_inspect = inspect_image(image)
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = build_release_manifest(
        image=image,
        image_inspect=image_inspect,
        git_sha=git_sha,
        git_branch=git_branch,
        build_timestamp=build_timestamp,
        repo_url=repo_url,
        ci_pipeline_id=ci_pipeline_id,
        base_image=base_image,
        platform=platform,
    )
    manifest["selected_base"] = selection
    _write_json(output_dir / "release-manifest.json", manifest)
    _write_json(output_dir / "image-inspect.json", image_inspect)
    _write_json(
        output_dir / "provenance-summary.json",
        {
            "status": "repo_native_summary",
            "subject": manifest["image_digest"],
            "builder": "lotus-manage Makefile docker-image-evidence",
            "git_commit_sha": git_sha,
            "git_branch": git_branch,
            "repo_url": repo_url,
            "ci_pipeline_id": ci_pipeline_id,
            "build_timestamp": build_timestamp,
            "selected_base": selection,
            "platform": manifest["platform"],
        },
    )
    sbom_status = _run_optional_report(
        tool="syft",
        command=["syft", image, "-o", "spdx-json"],
        output_path=output_dir / "sbom.spdx.json",
        status_path=output_dir / "sbom-status.json",
    )
    vulnerability_status = _run_optional_report(
        tool="trivy",
        command=["trivy", "image", "--format", "json", image],
        output_path=output_dir / "vulnerability-scan.json",
        status_path=output_dir / "vulnerability-scan-status.json",
    )
    signing_status = _run_optional_report(
        tool="cosign",
        command=["cosign", "verify", image],
        output_path=output_dir / "signature-verification.txt",
        status_path=output_dir / "signature-status.json",
    )
    manifest["evidence"] = {
        "sbom": sbom_status,
        "vulnerability_scan": vulnerability_status,
        "signature": signing_status,
        "provenance_summary": (output_dir / "provenance-summary.json").as_posix(),
    }
    _write_json(output_dir / "release-manifest.json", manifest)
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write Docker image supply-chain evidence.")
    parser.add_argument("--validate-base-only", action="store_true")
    parser.add_argument("--dockerfile", type=Path, default=ROOT / "Dockerfile")
    parser.add_argument("--base-image", default=BASE_IMAGE)
    parser.add_argument("--platform", default=BASE_PLATFORM)
    parser.add_argument("--image")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--git-sha")
    parser.add_argument("--git-branch")
    parser.add_argument("--build-timestamp")
    parser.add_argument("--repo-url")
    parser.add_argument("--ci-pipeline-id")
    args = parser.parse_args(argv)

    try:
        if args.validate_base_only:
            selection = validate_dockerfile_base(args.dockerfile, args.base_image, args.platform)
            print(json.dumps(selection, sort_keys=True))
            return 0
        for name in (
            "image",
            "git_sha",
            "git_branch",
            "build_timestamp",
            "repo_url",
            "ci_pipeline_id",
        ):
            if not getattr(args, name):
                parser.error(f"--{name.replace('_', '-')} is required for image evidence")
        manifest = write_docker_image_evidence(
            image=args.image,
            output_dir=args.output_dir,
            git_sha=args.git_sha,
            git_branch=args.git_branch,
            build_timestamp=args.build_timestamp,
            repo_url=args.repo_url,
            ci_pipeline_id=args.ci_pipeline_id,
            dockerfile=args.dockerfile,
            base_image=args.base_image,
            platform=args.platform,
        )
    except (subprocess.CalledProcessError, OSError, ValueError) as exc:
        print(f"Docker image evidence failed: {exc}", file=sys.stderr)
        return 1
    print(f"Wrote Docker image evidence for {manifest['image']} to {args.output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
