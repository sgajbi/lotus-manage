from pathlib import Path

from scripts.workspace_paths import resolve_lotus_platform_root


def test_platform_root_resolves_canonical_sibling(tmp_path: Path) -> None:
    repository_root = tmp_path / "lotus-manage"
    platform_root = tmp_path / "lotus-platform"
    repository_root.mkdir()
    platform_root.mkdir()

    assert (
        resolve_lotus_platform_root(repository_root=repository_root, environment={})
        == platform_root.resolve()
    )


def test_platform_root_resolves_isolated_worktree_layout(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspace"
    repository_root = workspace_root / "_worktrees" / "lotus-manage-715"
    platform_root = workspace_root / "lotus-platform"
    repository_root.mkdir(parents=True)
    platform_root.mkdir()

    assert (
        resolve_lotus_platform_root(repository_root=repository_root, environment={})
        == platform_root.resolve()
    )


def test_platform_root_prefers_explicit_workspace_root(tmp_path: Path) -> None:
    repository_root = tmp_path / "isolated" / "lotus-manage"
    configured_workspace = tmp_path / "configured"
    platform_root = configured_workspace / "lotus-platform"
    repository_root.mkdir(parents=True)
    platform_root.mkdir(parents=True)

    assert (
        resolve_lotus_platform_root(
            repository_root=repository_root,
            environment={"LOTUS_WORKSPACE_ROOT": str(configured_workspace)},
        )
        == platform_root.resolve()
    )
