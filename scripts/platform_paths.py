"""Portable sibling ``lotus-platform`` discovery for repository validation scripts."""

from __future__ import annotations

import os
from pathlib import Path


def resolve_platform_root(*, repository_root: Path) -> Path:
    """Locate the Platform checkout from a normal repo or an isolated worktree.

    ``LOTUS_WORKSPACE_ROOT`` is authoritative when supplied. The ancestor
    fallback supports the standard ``<workspace>/_worktrees/<repo>`` layout
    without baking a developer-specific path into validation commands.
    """

    configured_root = os.environ.get("LOTUS_WORKSPACE_ROOT")
    candidates = ([Path(configured_root) / "lotus-platform"] if configured_root else []) + [
        parent / "lotus-platform" for parent in repository_root.parents
    ]
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    return repository_root.parent / "lotus-platform"


__all__ = ["resolve_platform_root"]
