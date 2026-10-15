"""Capture current in-process API contract wires, then check immutable exported vectors."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.api.dependencies import get_composite_subject_service
from src.api.main import app
from src.core.common.canonical import hash_canonical_payload
from src.core.composite_eligibility.staged_controls import STAGED_CONTROL_ADAPTER
from src.core.composite_eligibility.staged_publication import (
    decode_subject_finalization,
    decode_subject_receipt,
)
from tests.composite_historical_subject_sources import configured_historical_subject_service
from tests.unit.api.test_composite_historical_subject_routes import finalized


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True) + "\n").encode()


def capture_contract_files():
    """No test clock or seeded business rows; exact current API admission is retained."""
    prior = app.dependency_overrides.copy()
    with pytest.MonkeyPatch.context() as monkeypatch:
        with configured_historical_subject_service(monkeypatch) as material:
            service, *_ = material
            app.dependency_overrides[get_composite_subject_service] = lambda: service
            try:
                with TestClient(app) as client:
                    controls, _, receipt, _ = finalized((client, *material[:6]))
            finally:
                app.dependency_overrides.clear()
                app.dependency_overrides.update(prior)
    wires = [*controls, receipt["finalization"], receipt]
    files = {}
    for wire in wires:
        name = wire["product_name"] + "." + wire["product_version"]
        model = (
            decode_subject_receipt(wire)
            if wire["product_name"].endswith("Receipt")
            else decode_subject_finalization(wire)
            if wire["product_name"] == "CompositeEligibilityFinalization"
            else STAGED_CONTROL_ADAPTER.validate_python(wire)
        )
        files[name + ".controlled.json"] = model.model_dump(mode="json")
        files[name + ".schema.json"] = type(model).model_json_schema()
    vectors = []
    for case in ("nested_hash", "mixed_policy", "mixed_evaluation", "mixed_receipt", "intent"):
        wire = deepcopy(receipt)
        approval = wire["finalization"]["evaluation_approval"]
        if case == "nested_hash":
            approval["proposal"]["policy_approval"]["approval"]["content_hash"] = (
                "sha256:" + "0" * 64
            )
        elif case == "mixed_policy":
            approval["proposal"]["policy_approval"]["product_version"] = "v1"
        elif case == "mixed_evaluation":
            approval["product_version"] = "v1"
        elif case == "mixed_receipt":
            wire["product_version"] = "v1"
        else:
            approval["operation_verification"]["request"]["intent_digest"] = "sha256:" + "0" * 64
        pointers = {
            "nested_hash": "/finalization/evaluation_approval/proposal/policy_approval/approval/content_hash",
            "mixed_policy": "/finalization/evaluation_approval/proposal/policy_approval/product_version",
            "mixed_evaluation": "/finalization/evaluation_approval/product_version",
            "mixed_receipt": "/product_version",
            "intent": "/finalization/evaluation_approval/operation_verification/request/intent_digest",
        }
        replacement = wire
        for key in pointers[case].strip("/").split("/"):
            replacement = replacement[key]
        vectors.append(
            {
                "case": case,
                "expected": "REFUSE",
                "pointer": pointers[case],
                "replacement": replacement,
            }
        )
    files["refusal-vectors.json"] = vectors
    files["manifest.json"] = {
        "posture": "CONTROLLED_SYNTHETIC_ONLY_CURRENT_IN_PROCESS_ADMISSION",
        "official_activation": "UNAVAILABLE",
        "production_adapter": "UNAVAILABLE",
        "consumer_enablement": "NOT_ADMITTED",
        "source_base": "e02bfd8ae8c31bb76f93125212da6c4693caf00e",
        "canonical_content_digests": {
            name: hash_canonical_payload(value) for name, value in files.items()
        },
        "raw_file_sha256": {
            name: hashlib.sha256(encoded(value)).hexdigest() for name, value in files.items()
        },
    }
    return files


def check_contract_files(directory: Path):
    manifest = json.loads((directory / "manifest.json").read_bytes())
    expected = set(manifest["raw_file_sha256"]) | {"manifest.json"}
    if {path.name for path in directory.glob("*.json")} != expected:
        raise ValueError("Historical subject contract inventory drift")
    for name, digest in manifest["raw_file_sha256"].items():
        raw = (directory / name).read_bytes()
        value = json.loads(raw)
        if (
            hashlib.sha256(raw).hexdigest() != digest
            or hash_canonical_payload(value) != manifest["canonical_content_digests"][name]
        ):
            raise ValueError("Historical subject contract digest drift: " + name)
        if name.endswith(".controlled.json"):
            if value["product_name"].endswith("Receipt"):
                model = decode_subject_receipt(value)
            elif value["product_name"] == "CompositeEligibilityFinalization":
                model = decode_subject_finalization(value)
            else:
                model = STAGED_CONTROL_ADAPTER.validate_python(value)
            schema_path = directory / name.replace(".controlled.json", ".schema.json")
            if json.loads(schema_path.read_bytes()) != type(model).model_json_schema():
                raise ValueError("Historical subject schema drift: " + name)
            if model.model_dump(mode="json") != value:
                raise ValueError("Historical subject roundtrip drift: " + name)
    for vector in json.loads((directory / "refusal-vectors.json").read_bytes()):
        wire = json.loads(
            (directory / "CompositeEligibilityFinalizationReceipt.v3.controlled.json").read_bytes()
        )
        keys = vector["pointer"].strip("/").split("/")
        target = wire
        for key in keys[:-1]:
            target = target[key]
        target[keys[-1]] = vector["replacement"]
        try:
            decode_subject_receipt(wire)
        except ValueError:
            continue
        raise ValueError("Invalid historical subject vector accepted: " + vector["case"])
