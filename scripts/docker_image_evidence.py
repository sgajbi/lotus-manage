from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT / "output" / "docker-image-evidence"


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
) -> dict[str, Any]:
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
) -> dict[str, Any]:
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
    )
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
    parser.add_argument("--image", required=True)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--git-sha", required=True)
    parser.add_argument("--git-branch", required=True)
    parser.add_argument("--build-timestamp", required=True)
    parser.add_argument("--repo-url", required=True)
    parser.add_argument("--ci-pipeline-id", required=True)
    args = parser.parse_args(argv)

    try:
        manifest = write_docker_image_evidence(
            image=args.image,
            output_dir=args.output_dir,
            git_sha=args.git_sha,
            git_branch=args.git_branch,
            build_timestamp=args.build_timestamp,
            repo_url=args.repo_url,
            ci_pipeline_id=args.ci_pipeline_id,
        )
    except (subprocess.CalledProcessError, ValueError) as exc:
        print(f"Docker image evidence failed: {exc}", file=sys.stderr)
        return 1
    print(f"Wrote Docker image evidence for {manifest['image']} to {args.output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
