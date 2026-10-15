from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from scripts import docker_image_evidence
from scripts.docker_image_evidence import (
    BASE_IMAGE,
    BASE_PLATFORM,
    BASE_SELECTION,
    build_release_manifest,
    validate_base_selection,
    validate_dockerfile_base,
)


REQUIRED_DOCKERIGNORE_PATTERNS = {
    ".git",
    ".venv",
    ".venv-*",
    "__pycache__",
    "*.pyc",
    ".coverage",
    ".coverage.*",
    "build",
    "dist",
    "output",
    "*.log",
    "manage-*.log",
    ".env",
    ".env.*",
    "!.env.example",
}

REQUIRED_OCI_LABELS = {
    "org.opencontainers.image.version",
    "org.opencontainers.image.revision",
    "org.opencontainers.image.ref.name",
    "org.opencontainers.image.created",
    "org.opencontainers.image.source",
    "lotus.ci.pipeline_id",
    "lotus.image.digest",
}


def test_dockerignore_protects_build_context_from_generated_and_secret_like_files() -> None:
    dockerignore = set(Path(".dockerignore").read_text(encoding="utf-8").splitlines())

    assert REQUIRED_DOCKERIGNORE_PATTERNS <= dockerignore


def test_dockerfile_exposes_non_secret_oci_labels_and_version_environment() -> None:
    dockerfile = Path("Dockerfile").read_text(encoding="utf-8")

    for label in REQUIRED_OCI_LABELS:
        assert label in dockerfile
    for build_arg in [
        "ARG GIT_SHA=unknown",
        "ARG GIT_BRANCH=unknown",
        "ARG BUILD_TIMESTAMP=unknown",
        "ARG REPO_URL=https://github.com/sgajbi/lotus-manage",
        "ARG IMAGE_DIGEST=unknown",
        "ARG CI_PIPELINE_ID=local",
    ]:
        assert build_arg in dockerfile
    for runtime_env in [
        "LOTUS_IMAGE_GIT_SHA",
        "LOTUS_IMAGE_GIT_BRANCH",
        "LOTUS_IMAGE_BUILD_TIMESTAMP",
        "LOTUS_IMAGE_REPO_URL",
        "LOTUS_IMAGE_DIGEST",
        "LOTUS_IMAGE_CI_PIPELINE_ID",
    ]:
        assert runtime_env in dockerfile

    assert "SECRET" not in dockerfile
    assert "TOKEN" not in dockerfile
    assert "PASSWORD" not in dockerfile


def test_makefile_keeps_fast_build_and_separate_docker_evidence_target() -> None:
    makefile = Path("Makefile").read_text(encoding="utf-8")

    assert "docker-build:" in makefile
    assert "docker-image-evidence: docker-build" in makefile
    assert "scripts/docker_image_evidence.py" in makefile
    assert "--build-arg GIT_SHA=$(GIT_SHA)" in makefile
    assert "--build-arg CI_PIPELINE_ID=$(CI_PIPELINE_ID)" in makefile
    assert "-t $(IMAGE_REF)" in makefile
    assert "-t lotus-manage:ci" in makefile
    assert "docker-build: docker-supply-chain-gate" in makefile
    assert "docker build --platform linux/amd64" in makefile
    assert "python scripts/docker_image_evidence.py --validate-base-only" in makefile
    static_gate = makefile.split("static-quality-gates:", 1)[1].split("\n\n", 1)[0]
    assert "docker-supply-chain-gate" in static_gate


def test_blocking_workflows_upload_docker_image_evidence() -> None:
    for workflow_path in [
        Path(".github/workflows/pr-merge-gate.yml"),
        Path(".github/workflows/main-releasability.yml"),
    ]:
        workflow = workflow_path.read_text(encoding="utf-8")
        assert "make docker-image-evidence" in workflow
        assert "actions/upload-artifact@v7" in workflow
        assert "output/docker-image-evidence" in workflow
        assert "make docker-build" not in workflow


def test_release_manifest_prefers_repo_digest_and_preserves_oci_labels() -> None:
    manifest = build_release_manifest(
        image="lotus-manage:test",
        image_inspect={
            "Id": "sha256:local-image-id",
            "Os": "linux",
            "Architecture": "amd64",
            "RepoDigests": ["ghcr.io/sgajbi/lotus-manage@sha256:pushed"],
            "Config": {
                "Labels": {
                    "org.opencontainers.image.revision": "abc123",
                    "lotus.ci.pipeline_id": "42",
                }
            },
        },
        git_sha="abc123",
        git_branch="feature",
        build_timestamp="2026-07-06T00:00:00Z",
        repo_url="https://github.com/sgajbi/lotus-manage",
        ci_pipeline_id="42",
    )

    assert manifest["image_digest"] == "ghcr.io/sgajbi/lotus-manage@sha256:pushed"
    assert manifest["git_commit_sha"] == "abc123"
    assert manifest["git_branch"] == "feature"
    assert manifest["ci_pipeline_id"] == "42"
    assert manifest["oci_labels"]["org.opencontainers.image.revision"] == "abc123"
    assert manifest["selected_base"] == {"reference": BASE_IMAGE, **BASE_SELECTION}
    assert manifest["platform"] == "linux/amd64"


def test_reviewed_default_base_and_literal_dockerfile_are_admitted() -> None:
    selected = validate_dockerfile_base(Path("Dockerfile"))
    assert selected["reference"] == BASE_IMAGE
    assert selected["platform"] == BASE_PLATFORM
    assert selected["image_digest"] == (
        "sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1"
    )
    assert selected["platform_manifest_digest"] == (
        "sha256:2b4f19dae3a777dfc3b76730bda1e82e1f66ab2a2686fa93ca78edbfb4f04ffe"
    )
    assert selected["platform_config_digest"] == (
        "sha256:df18428df8a0f9189c84e7424d214b4c50092af1f9dca5842a00c41c39bda316"
    )
    assert selected["original_source_selection_approval"].endswith("6186826582")
    assert len(selected["dockerfile_sha256"]) == 64
    assert selected["evidence_posture"] == "validated_build_input_not_base_layer_attestation"


@pytest.mark.parametrize(
    "reference",
    [
        "python:3.12-slim",
        "docker.io/library/python:3.12.15-slim-trixie",
        BASE_IMAGE.rsplit("@", 1)[0] + "@sha256:invalid",
        BASE_IMAGE.rsplit("@", 1)[0] + "@sha256:" + "0" * 64,
        BASE_IMAGE.replace("docker.io/library", "unapproved.example/library"),
        BASE_IMAGE.replace("docker.io/library", "public.ecr.aws/docker/library"),
        BASE_IMAGE.replace("3.12.15-slim-trixie", "3.12-slim-bookworm"),
        "${PYTHON_IMAGE}",
        "",
    ],
)
def test_unreviewed_or_mutable_base_override_is_rejected(reference) -> None:
    with pytest.raises(ValueError, match="reviewed Manage selection"):
        validate_base_selection(reference, BASE_PLATFORM)


@pytest.mark.parametrize(
    "platform", ["linux/arm64", "windows/amd64", "linux", "", "$TARGETPLATFORM"]
)
def test_wrong_or_unbound_platform_is_rejected(platform) -> None:
    with pytest.raises(ValueError, match="reviewed Manage selection"):
        validate_base_selection(BASE_IMAGE, platform)


@pytest.mark.parametrize(
    "instructions",
    [
        "FROM python:3.12-slim",
        f"ARG PYTHON_IMAGE={BASE_IMAGE}\nFROM --platform=linux/amd64 ${{PYTHON_IMAGE}}",
        f"FROM --platform=$TARGETPLATFORM {BASE_IMAGE}",
        f"FROM --platform=linux/arm64 {BASE_IMAGE}",
        f"FROM {BASE_IMAGE}",
        f"FROM --platform=linux/amd64 {BASE_IMAGE}\nFROM python:3.12-slim",
        "# no effective base\nARG PYTHON_IMAGE=python:3.12-slim",
    ],
)
def test_effective_dockerfile_base_bypass_refuses_before_inspection(
    tmp_path, monkeypatch, instructions
) -> None:
    dockerfile = tmp_path / "Dockerfile"
    dockerfile.write_text(instructions, encoding="utf-8")

    def forbidden_inspection(image):
        pytest.fail(f"Invalid base must refuse before daemon inspection of {image}")

    monkeypatch.setattr(docker_image_evidence, "inspect_image", forbidden_inspection)
    with pytest.raises(ValueError, match="reviewed literal FROM"):
        docker_image_evidence.write_docker_image_evidence(
            image="lotus-manage:test",
            output_dir=tmp_path / "evidence",
            git_sha="abc123",
            git_branch="feature",
            build_timestamp="2026-10-15T00:00:00Z",
            repo_url="https://github.com/sgajbi/lotus-manage",
            ci_pipeline_id="test",
            dockerfile=dockerfile,
        )
    assert not (tmp_path / "evidence").exists()


def test_offline_guard_cli_accepts_reviewed_source_and_refuses_overrides(capsys) -> None:
    assert docker_image_evidence.main(["--validate-base-only"]) == 0
    assert json.loads(capsys.readouterr().out)["reference"] == BASE_IMAGE
    assert (
        docker_image_evidence.main(["--validate-base-only", "--base-image", "python:3.12-slim"])
        == 1
    )
    assert "reviewed Manage selection" in capsys.readouterr().err
    assert docker_image_evidence.main(["--validate-base-only", "--platform", "linux/arm64"]) == 1
    assert "reviewed Manage selection" in capsys.readouterr().err


@pytest.mark.parametrize(
    "os,architecture", [("linux", "arm64"), ("windows", "amd64"), (None, None)]
)
def test_final_image_wrong_or_missing_platform_cannot_emit_release_evidence(
    os, architecture
) -> None:
    with pytest.raises(ValueError, match="Final image inspect platform"):
        build_release_manifest(
            image="lotus-manage:test",
            image_inspect={"Id": "sha256:local", "Os": os, "Architecture": architecture},
            git_sha="abc123",
            git_branch="feature",
            build_timestamp="2026-10-15T00:00:00Z",
            repo_url="https://github.com/sgajbi/lotus-manage",
            ci_pipeline_id="test",
        )


def test_native_evidence_retains_selected_base_source_and_final_image(
    tmp_path, monkeypatch
) -> None:
    inspected = {"Id": "sha256:" + "1" * 64, "Os": "linux", "Architecture": "amd64"}

    def inspect_expected_image(image):
        assert image == "lotus-manage:test"
        return inspected

    monkeypatch.setattr(docker_image_evidence, "inspect_image", inspect_expected_image)
    monkeypatch.setattr(
        docker_image_evidence,
        "_run_optional_report",
        lambda **kwargs: {"status": "not_available_report_only"},
    )
    manifest = docker_image_evidence.write_docker_image_evidence(
        image="lotus-manage:test",
        output_dir=tmp_path,
        git_sha="abc123",
        git_branch="feature",
        build_timestamp="2026-10-15T00:00:00Z",
        repo_url="https://github.com/sgajbi/lotus-manage",
        ci_pipeline_id="test",
    )
    retained = json.loads((tmp_path / "release-manifest.json").read_text())
    provenance = json.loads((tmp_path / "provenance-summary.json").read_text())
    assert retained == manifest
    assert retained["image_id"] == inspected["Id"]
    assert retained["git_commit_sha"] == "abc123"
    assert retained["selected_base"]["reference"] == BASE_IMAGE
    assert provenance["selected_base"] == retained["selected_base"]
    assert provenance["platform"] == "linux/amd64"
    assert retained["evidence"]["sbom"]["status"] == "not_available_report_only"


def test_compose_forwards_only_the_three_supported_metadata_build_inputs() -> None:
    model = yaml.safe_load(Path("docker-compose.yml").read_text(encoding="utf-8"))
    assert model["services"]["lotus-manage"]["build"]["args"] == {
        name: "${" + name + ":-unknown}" for name in ("GIT_SHA", "GIT_BRANCH", "BUILD_TIMESTAMP")
    }
