"""Injective identity encoding for derived mandate-evidence keys (#648).

Concatenating identifier components with a separator is not injective when the
components may themselves contain that separator: tenant "a" with mandate
"b_c" and tenant "a_b" with mandate "c" produce the same string. For a primary
key that means a spurious unique violation between two records that are
genuinely distinct - and PostgreSQL raises it on the key rather than on the
tenant-scoped conflict target, so it does not even present as a tenancy
problem.

The components are hashed as a length-prefixed sequence, which cannot be
ambiguous whatever the identifiers contain. The readable columns are still
stored alongside, so nothing is lost for debugging; only the surrogate key is
opaque.
"""

from __future__ import annotations

import hashlib


def derived_identity(prefix: str, *components: str) -> str:
    """Return a stable, injective key over the given identity components."""

    digest = hashlib.sha256()
    for component in components:
        encoded = component.encode("utf-8")
        # The length prefix is what makes the encoding unambiguous: without it
        # ("a", "b_c") and ("a_b", "c") hash identically.
        digest.update(str(len(encoded)).encode("ascii"))
        digest.update(b":")
        digest.update(encoded)
    return f"{prefix}_{digest.hexdigest()[:32]}"


__all__ = ["derived_identity"]
