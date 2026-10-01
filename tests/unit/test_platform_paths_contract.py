from __future__ import annotations

from pathlib import Path

from scripts.platform_paths import resolve_platform_root


def test_resolve_platform_root_finds_standard_isolated_worktree_layout(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    repository = workspace / "_worktrees" / "lotus-manage-713"
    repository.mkdir(parents=True)
    platform = workspace / "lotus-platform"
    platform.mkdir()

    assert resolve_platform_root(repository_root=repository) == platform


def test_resolve_platform_root_uses_configured_workspace_root(tmp_path: Path, monkeypatch) -> None:
    workspace = tmp_path / "workspace"
    platform = workspace / "lotus-platform"
    platform.mkdir(parents=True)
    repository = tmp_path / "other" / "lotus-manage"
    repository.mkdir(parents=True)
    monkeypatch.setenv("LOTUS_WORKSPACE_ROOT", str(workspace))

    assert resolve_platform_root(repository_root=repository) == platform
