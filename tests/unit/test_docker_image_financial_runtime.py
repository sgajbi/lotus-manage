"""Immutable Docker financial proof and fail-closed evidence contracts."""

from __future__ import annotations

from copy import deepcopy

import pytest

from scripts.image_financial_runtime import validate_image, validate_results
from scripts.workflow_policy_gate import docker_image_evidence_violations


REVISION = "a" * 40
IMAGE = {
    "Id": "sha256:" + "b" * 64,
    "Config": {"User": "dpm-user", "Labels": {"org.opencontainers.image.revision": REVISION}},
}
NAMES = (
    "test_native_network_construction_survives_api_process_replacement[USD]",
    "test_native_network_construction_survives_api_process_replacement[EUR]",
    "test_http_wave_worker_recovers_committed_financial_artifact_after_process_death",
)


def test_image_requires_exact_revision_and_immutable_identity():
    assert validate_image(IMAGE, REVISION) == IMAGE["Id"]
    for revision in ("", "unknown", "a" * 39, "c" * 40):
        with pytest.raises(ValueError):
            validate_image(IMAGE, revision)


@pytest.mark.parametrize("field,value", [("Id", "tag:latest"), ("Config", {})])
def test_missing_or_mutable_image_metadata_fails(field, value):
    payload = deepcopy(IMAGE)
    payload[field] = value
    with pytest.raises(ValueError):
        validate_image(payload, REVISION)


def test_root_image_is_not_shipped_runtime():
    payload = deepcopy(IMAGE)
    payload["Config"]["User"] = "root"
    with pytest.raises(ValueError):
        validate_image(payload, REVISION)


@pytest.mark.parametrize("outcome", ["", "<skipped/>", "<failure/>", "<error/>"])
def test_result_accounting_rejects_nonexecuted_or_failed_cases(tmp_path, outcome):
    path = tmp_path / "results.xml"
    path.write_text(
        "<testsuites><testsuite>"
        + "".join(f'<testcase name="{name}">{outcome}</testcase>' for name in NAMES)
        + "</testsuite></testsuites>",
        encoding="utf-8",
    )
    if outcome:
        with pytest.raises(ValueError):
            validate_results(path)
    else:
        assert validate_results(path) == list(NAMES)


@pytest.mark.parametrize("names", [(), NAMES[:2], NAMES + (NAMES[0],), ("unrelated",) * 3])
def test_empty_missing_duplicate_or_wrong_cases_fail(tmp_path, names):
    path = tmp_path / "results.xml"
    path.write_text(
        "<testsuites><testsuite>"
        + "".join(f'<testcase name="{name}"/>' for name in names)
        + "</testsuite></testsuites>",
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        validate_results(path)


@pytest.mark.parametrize("tamper", ["remove", "waive"])
def test_image_financial_workflow_verdict_cannot_be_removed_or_waived(tmp_path, tamper):
    from pathlib import Path

    for name in ("pr-merge-gate.yml", "main-releasability.yml"):
        original = Path(".github/workflows", name).read_text(encoding="utf-8")
        assert docker_image_evidence_violations(Path(".github/workflows", name)) == []
        if tamper == "remove":
            changed = original.replace("run: make test-image-financial-runtime", "run: true")
        else:
            changed = original.replace(
                "- name: Verify image financial recovery",
                "- name: Verify image financial recovery\n        continue-on-error: true",
            )
        path = tmp_path / name
        path.write_text(changed, encoding="utf-8")
        assert len(docker_image_evidence_violations(path)) == 1
