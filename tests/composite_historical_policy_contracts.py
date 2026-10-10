"""Generate/check proposed schemas and controlled examples from actual typed models."""

import argparse
import hashlib
import json
from pathlib import Path

from src.core.common.canonical import hash_canonical_payload
from tests.composite_historical_policy_helpers import (
    historical_contract_material,
    historical_amendment_contract_material,
)


def contract_files():
    models = (*historical_contract_material()[1:], *historical_amendment_contract_material())
    files = {}
    for model in models:
        name = f"{model.product_name}.{model.product_version}"
        files[f"{name}.schema.json"] = type(model).model_json_schema()
        files[f"{name}.controlled.json"] = model.model_dump(mode="json")
    files["manifest.json"] = {
        "posture": "PROPOSED_ENGINEERING_CONTRACT_CONTROLLED_TEST_HISTORY",
        "production_adapter": "UNAVAILABLE",
        "consumer_enablement": "NOT_ADMITTED",
        "official_activation": "UNAVAILABLE",
        "baseline": "9224d85664fb07e8074ef21681b88449d05193e8",
        "roles": {
            "original_raw_bytes": "/verification/mapping/raw_original_base64",
            "original_raw_digest": "/verification/mapping/reference/raw_digest",
            "original_signing_contract": "/verification/mapping/reference/signing_contract",
            "original_credential": "/verification/mapping/original_credential",
            "normalized_policy": "/verification/mapping/policy",
            "original_approval_time": "/verification/mapping/original_approved_at",
            "present_policy_proposal_time": "/proposed_at",
            "present_policy_approval_time": "/approved_at",
            "fresh_evaluation_operation_proof": "/operation_verification",
            "fresh_operation_intent": "/operation_verification/request/intent_digest",
        },
        "role_scope": "Policy proof pointers are relative to policy v2 proposal/approval; operation proof pointers are relative to evaluation v3/v4 proposal/approval. Receipts nest the evaluation approval under /approval; policy is /approval/proposal/policy_approval.",
        "canonical_digest_algorithm": "SHA256 of UTF-8 json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True), prefixed sha256:",
        "canonical_content_digests": {
            name: hash_canonical_payload(value) for name, value in sorted(files.items())
        },
        "raw_file_encoding": "UTF-8 without BOM; sorted keys, indent=2, ensure_ascii=True, LF, one final newline",
        "raw_file_sha256": {
            name: hashlib.sha256(
                (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")
            ).hexdigest()
            for name, value in sorted(files.items())
        },
    }
    return {
        name: json.dumps(value, indent=2, sort_keys=True) + "\n" for name, value in files.items()
    }


def check_contract_files(directory: Path, files: dict[str, str]) -> None:
    mismatches = [
        name
        for name, content in files.items()
        if not (directory / name).exists()
        or (directory / name).read_bytes() != content.encode("utf-8")
    ]
    extra = {path.name for path in directory.glob("*.json")} - files.keys()
    if mismatches or extra:
        raise ValueError(f"Contract drift: changed={mismatches}, extra={sorted(extra)}")
    manifest = json.loads((directory / "manifest.json").read_bytes())
    for name, expected in manifest["raw_file_sha256"].items():
        raw = (directory / name).read_bytes()
        if (
            hashlib.sha256(raw).hexdigest() != expected
            or hash_canonical_payload(json.loads(raw))
            != manifest["canonical_content_digests"][name]
        ):
            raise ValueError(f"Contract digest mismatch: {name}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    files = contract_files()
    if args.check:
        check_contract_files(args.directory, files)
    else:
        args.directory.mkdir(parents=True, exist_ok=True)
        for name, content in files.items():
            (args.directory / name).write_bytes(content.encode("utf-8"))
    print(
        f"{'Checked' if args.check else 'Generated'} {len(files)} typed schema/example/manifest files"
    )


if __name__ == "__main__":
    main()
