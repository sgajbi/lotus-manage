"""Portable Lotus sibling-checkout path resolution for repository scripts."""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path


def resolve_lotus_platform_root(
    *,
    repository_root: Path,
    environment: Mapping[str, str] | None = None,
) -> Path:
    """Resolve lotus-platform in canonical or isolated-worktree layouts."""

    values = os.environ if environment is None else environment
    configured_workspace = values.get("LOTUS_WORKSPACE_ROOT", "").strip()
    candidates = []
    if configured_workspace:
        candidates.append(Path(configured_workspace).expanduser() / "lotus-platform")
    candidates.extend(
        [
            repository_root.parent / "lotus-platform",
            repository_root.parent.parent / "lotus-platform",
        ]
    )
    for candidate in candidates:
        if candidate.is_dir():
            return candidate.resolve()
    return candidates[0].resolve()


__all__ = ["resolve_lotus_platform_root"]
