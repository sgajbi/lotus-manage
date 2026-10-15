"""Explicit controlled-history trust and bounded read-only deployment custody."""

import base64
import errno
import hashlib
import json
import os
import stat
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, TypeAdapter, model_validator

from src.core.common.canonical import hash_canonical_payload
from src.core.composite_authority_models import Digest, Identity, StrictAuthorityModel
from src.core.composite_eligibility.historical_policy import HistoricalPolicyTrust
from src.core.composite_eligibility.observations import UtcInstant


def strict_controlled_json(raw: str | bytes) -> dict[str, Any]:
    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result = dict(pairs)
        if len(result) != len(pairs):
            raise ValueError("COMPOSITE_NATIVE_JSON_DUPLICATE_MEMBER")
        return result

    document = json.loads(raw, object_pairs_hook=unique)
    return TypeAdapter(dict[str, Any]).validate_python(document)


def public_key_bytes(value: str) -> bytes:
    key = base64.b64decode(value, validate=True)
    if len(key) != 32 or base64.b64encode(key).decode() != value:
        raise ValueError("COMPOSITE_NATIVE_PUBLIC_KEY_INVALID")
    return key


def key_digest(key: bytes) -> str:
    return "sha256:" + hashlib.sha256(key).hexdigest()


class NativeRevocationSnapshot(StrictAuthorityModel):
    revision: Identity
    checked_at: UtcInstant
    expires_at: UtcInstant
    revoked_principals: list[Identity] = Field(max_length=1000)
    revoked_key_digests: list[Digest] = Field(max_length=1000)
    revoked_original_digests: list[Digest] = Field(max_length=1000)

    def require_current(self, requested: datetime, now: datetime) -> None:
        checked, expiry = map(datetime.fromisoformat, (self.checked_at, self.expires_at))
        if not checked <= requested <= now < expiry or expiry > checked + timedelta(minutes=5):
            raise ValueError("COMPOSITE_NATIVE_REVOCATION_WINDOW_INVALID")


def native_configuration_digest(document: dict[str, Any]) -> str:
    material = dict(document)
    material["trust"] = {
        name: value for name, value in document["trust"].items() if name != "configuration_digest"
    }
    return hash_canonical_payload(material)


class NativeHistoricalConfiguration(StrictAuthorityModel):
    adapter: Literal["CONTROLLED_SYNTHETIC_POLICY_V1"]
    trust: HistoricalPolicyTrust
    source_public_key_base64: str = Field(min_length=44, max_length=44)
    source_key_valid_from: UtcInstant
    source_key_valid_to: UtcInstant
    verifier_id: Identity
    verifier_key_file: str = Field(min_length=1, max_length=2048)
    originals_directory: str = Field(min_length=1, max_length=2048)
    revocation: NativeRevocationSnapshot

    @model_validator(mode="after")
    def require_controlled_independent_custody(self) -> "NativeHistoricalConfiguration":
        trust = self.trust
        _require_independent_native_trust(trust, self.adapter)
        if key_digest(public_key_bytes(self.source_public_key_base64)) != trust.signer_key_digest:
            raise ValueError("COMPOSITE_NATIVE_SOURCE_KEY_MISMATCH")
        if not all(
            Path(value).is_absolute()
            for value in (self.verifier_key_file, self.originals_directory)
        ):
            raise ValueError("COMPOSITE_NATIVE_CUSTODY_PATH_INVALID")
        if self.source_key_valid_from >= self.source_key_valid_to:
            raise ValueError("COMPOSITE_NATIVE_SOURCE_KEY_WINDOW_INVALID")
        if native_configuration_digest(self.model_dump(mode="json")) != trust.configuration_digest:
            raise ValueError("COMPOSITE_NATIVE_CONFIGURATION_DIGEST_MISMATCH")
        return self


def _require_independent_native_trust(trust: HistoricalPolicyTrust, adapter: str) -> None:
    if trust.posture != "SYNTHETIC_NON_CERTIFYING" or trust.signing_contract != adapter:
        raise ValueError("COMPOSITE_NATIVE_CONTROLLED_ONLY")
    if (
        trust.signer_principal_id == trust.verifier_principal_id
        or trust.signer_key_digest == trust.verifier_key_digest
    ):
        raise ValueError("COMPOSITE_HISTORICAL_POLICY_INDEPENDENCE_REQUIRED")


def _regular_path(path: Path) -> os.stat_result:
    for entry in (path, *path.parents):
        observed = entry.lstat()
        if stat.S_ISLNK(observed.st_mode) or getattr(observed, "st_file_attributes", 0) & 0x400:
            raise ValueError("COMPOSITE_NATIVE_CUSTODY_LINK_FORBIDDEN")
    observed = path.lstat()
    if not stat.S_ISREG(observed.st_mode) or observed.st_nlink != 1:
        raise ValueError("COMPOSITE_NATIVE_CUSTODY_REGULAR_FILE_REQUIRED")
    return observed


def _require_read_only(path: Path) -> None:
    try:
        descriptor = os.open(
            path, os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
        )
    except OSError as exc:
        if exc.errno in {errno.EACCES, errno.EPERM, errno.EROFS}:
            return
        raise ValueError("COMPOSITE_NATIVE_SECRET_ACCESS_INVALID") from exc
    else:
        os.close(descriptor)
        raise ValueError("COMPOSITE_NATIVE_SECRET_READ_ONLY_REQUIRED")


def read_custody_file(path: Path, maximum_bytes: int, *, secret: bool = False) -> bytes:
    """Read bounded regular bytes; never print paths/secret contents or mutate the file."""
    try:
        before = _regular_path(path)
        if secret:
            _require_read_only(path)
        descriptor = os.open(
            path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
        )
        with os.fdopen(descriptor, "rb") as source:
            opened = os.fstat(source.fileno())
            if not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1:
                raise ValueError("COMPOSITE_NATIVE_CUSTODY_REGULAR_FILE_REQUIRED")
            if (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino):
                raise ValueError("COMPOSITE_NATIVE_CUSTODY_CHANGED")
            raw = source.read(maximum_bytes + 1)
        after = _regular_path(path)
        if (opened.st_dev, opened.st_ino) != (after.st_dev, after.st_ino):
            raise ValueError("COMPOSITE_NATIVE_CUSTODY_CHANGED")
        if not raw or len(raw) > maximum_bytes:
            raise ValueError("COMPOSITE_NATIVE_CUSTODY_SIZE_INVALID")
        return raw
    except OSError as exc:
        raise ValueError("COMPOSITE_NATIVE_CUSTODY_UNAVAILABLE") from exc
