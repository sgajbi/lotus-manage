"""Exact exported byte custody and independent canonical content digests."""

import hashlib
import json

import pytest

from src.core.common.canonical import hash_canonical_payload
from tests.composite_historical_policy_contracts import contract_files, check_contract_files


@pytest.fixture(scope="module")
def exported_files():
    return contract_files()


def test_contract_export_accepts_exact_bytes_and_both_digest_algorithms(tmp_path, exported_files):
    for name, content in exported_files.items():
        (tmp_path / name).write_bytes(content.encode("utf-8"))
    check_contract_files(tmp_path, exported_files)
    manifest = json.loads(exported_files["manifest.json"])
    for name, expected in manifest["raw_file_sha256"].items():
        raw = (tmp_path / name).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == expected
        assert (
            hash_canonical_payload(json.loads(raw)) == manifest["canonical_content_digests"][name]
        )
        assert expected != manifest["canonical_content_digests"][name].removeprefix("sha256:")


@pytest.mark.parametrize("mutation", ["crlf", "tamper", "missing", "extra", "manifest"])
def test_contract_export_refuses_changed_bytes(tmp_path, exported_files, mutation):
    for name, content in exported_files.items():
        (tmp_path / name).write_bytes(content.encode("utf-8"))
    victim = tmp_path / "CompositeMonthlyPolicyProposal.v2.controlled.json"
    if mutation == "crlf":
        victim.write_bytes(victim.read_bytes().replace(b"\n", b"\r\n"))
    elif mutation == "tamper":
        victim.write_bytes(
            victim.read_bytes().replace(
                b"controlled-admission-maker", b"controlled-different-maker"
            )
        )
    elif mutation == "missing":
        victim.unlink()
    elif mutation == "extra":
        (tmp_path / "unexpected.json").write_bytes(b"{}")
    else:
        path = tmp_path / "manifest.json"
        path.write_bytes(path.read_bytes().replace(b"UNAVAILABLE", b"AVAILABLE"))
    with pytest.raises(ValueError, match="Contract drift"):
        check_contract_files(tmp_path, exported_files)
