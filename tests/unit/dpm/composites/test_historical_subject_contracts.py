"""Frozen additive schema/wire parity and representative invalid contract inventories."""

import json
import shutil
from pathlib import Path

import pytest

from tests.composite_historical_subject_contracts import check_contract_files

SOURCE = Path(__file__).resolve().parents[4] / "docs/contracts/composite-historical-subject"


def test_exported_historical_subject_contracts_validate_bytes_models_and_bad_vectors():
    check_contract_files(SOURCE)


@pytest.mark.parametrize("change", ["bytes", "schema", "missing", "extra", "vector"])
def test_historical_subject_contract_guard_refuses_drift(tmp_path, change):
    destination = tmp_path / "contracts"
    shutil.copytree(SOURCE, destination)
    receipt = destination / "CompositeEligibilityFinalizationReceipt.v3.controlled.json"
    if change == "bytes":
        receipt.write_bytes(receipt.read_bytes().replace(b"\n", b"\r\n"))
    elif change == "schema":
        (destination / "CompositeSubjectPolicyProposal.v2.schema.json").write_text(
            "{}", encoding="utf-8"
        )
    elif change == "missing":
        receipt.unlink()
    elif change == "extra":
        (destination / "unknown.json").write_text("{}", encoding="utf-8")
    else:
        target = destination / "refusal-vectors.json"
        vectors = json.loads(target.read_bytes())
        vectors[0]["replacement"] = "sha256:" + "1" * 64
        target.write_text(json.dumps(vectors), encoding="utf-8")
    with pytest.raises(ValueError):
        check_contract_files(destination)
