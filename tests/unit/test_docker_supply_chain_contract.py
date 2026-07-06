from __future__ import annotations

from pathlib import Path

from scripts.docker_image_evidence import build_release_manifest


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
