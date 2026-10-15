"""Controlled scenario graph acceptance and immutable legacy refusal controls."""

from copy import deepcopy
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from src.api.composition import composite_source_service
from src.api.dependencies import get_composite_subject_service
from src.api.main import app
from src.core.composite_eligibility.staged_controls import STAGED_CONTROL_ADAPTER
from src.core.composite_eligibility.staged_publication import decode_subject_receipt
from tests.composite_historical_subject_sources import configured_historical_subject_service
from tests.composite_staged_eligibility_helpers import BASE, HEADERS
from tests.unit.api.test_composite_historical_subject_routes import finalized, put, retained_state
from tests.unit.dpm.infrastructure.test_historical_policy_verifier import (
    native_controlled_configuration,
)


@pytest.fixture
def scenario_native_history(tmp_path):
    from tests.composite_historical_policy_helpers import historical_contract_material
    from tests.unit.dpm.infrastructure.test_historical_policy_verifier import native_history

    return native_history.__wrapped__(tmp_path, historical_contract_material())


def capture_controlled_scenario(
    tmp_path, monkeypatch, *, inspect_controls=None, inspect_retained_retry=False
):
    import json

    with configured_historical_subject_service(monkeypatch) as material:
        _, repository, historical, subject, policy, evaluation, _ = material
        document, reference, raw, original_file, _ = native_controlled_configuration(
            tmp_path, historical.mapping
        )
        monkeypatch.setenv("DPM_COMPOSITE_HISTORICAL_POLICY_ADMISSION_JSON", json.dumps(document))
        service = composite_source_service.build_composite_subject_service(repository)
        prior = app.dependency_overrides.copy()
        app.dependency_overrides[get_composite_subject_service] = lambda: service
        try:
            with TestClient(app) as client:
                provider = SimpleNamespace(mapping=SimpleNamespace(reference=reference))
                controls, definition, receipt, body = finalized(
                    (client, service, repository, provider, subject, policy, evaluation)
                )
                assert [item["product_version"] for item in controls] == ["v3"] * 4
                assert (
                    receipt["product_version"] == receipt["finalization"]["product_version"] == "v4"
                )
                assert receipt["completeness"] == "UNVERIFIED"
                assert (
                    definition.product_version
                    == definition.source_authority.payload.product_version
                    == "v3"
                )
                assert (
                    definition.source_authority.payload.eligibility_evaluation_binding.product_version
                    == "v3"
                )
                mapping = controls[0]["proposal"]["verification"]["mapping"]
                original = json.loads(raw)
                assert mapping["actual_issued_at"] == original["actual_issued_at"]
                assert mapping["scenario_approved_at"] == original["scenario_approved_at"]
                assert (
                    not {
                        "original_proposed_at",
                        "original_approved_at",
                        "original_proposed_by",
                        "original_approved_by",
                    }
                    & mapping.keys()
                )
                assert (
                    mapping["scenario_approved_at"]
                    < mapping["actual_issued_at"]
                    <= controls[0]["proposal"]["proposed_at"]
                )
                if inspect_controls is not None:
                    inspect_controls(service, controls)
                if inspect_retained_retry:
                    assert_retained_policy_retry(client, repository, controls[0], monkeypatch)
                original_file.unlink()
                monkeypatch.delenv("DPM_COMPOSITE_SOURCES_JSON")
                monkeypatch.delenv("DPM_COMPOSITE_HISTORICAL_POLICY_ADMISSION_JSON")
                service = composite_source_service.build_composite_subject_service(repository)
                if inspect_retained_retry:
                    assert_retained_policy_retry(client, repository, controls[0], monkeypatch)
                binding = (
                    definition.source_authority.payload.eligibility_evaluation_binding.model_dump(
                        mode="json"
                    )
                )
                resolver = "/api/v1/rebalance/composites/synthetic-composite/definitions/synthetic-definition/eligibility-evidence/resolve"
                assert client.post(resolver, headers=HEADERS, json=binding).json() == receipt
                assert client.get(BASE + "/finalization", headers=HEADERS).json() == receipt
                assert put(client, BASE + "/finalization", body, checker=True) == receipt
                for item in controls:
                    assert (
                        STAGED_CONTROL_ADAPTER.validate_python(item).model_dump(mode="json") == item
                    )
                assert decode_subject_receipt(receipt).model_dump(mode="json") == receipt
                assert len(repository._publications) == 1
                return controls, receipt
        finally:
            app.dependency_overrides.clear()
            app.dependency_overrides.update(prior)


def test_controlled_scenario_complete_native_admission_and_retained_replay(tmp_path, monkeypatch):
    capture_controlled_scenario(tmp_path, monkeypatch)


def assert_retained_policy_retry(client, repository, proposal, monkeypatch):
    path = BASE + "/policies/" + proposal["proposal"]["proposal_revision"] + "/historical-admission"
    body = {
        "expected_subject_content_hash": proposal["subject"]["content_hash"],
        "reference": proposal["proposal"]["verification"]["mapping"]["reference"],
    }
    before = retained_state(repository)

    def unexpected_write(**_kwargs):
        pytest.fail("retained admission retry must not write another immutable control")

    with monkeypatch.context() as patch:
        patch.setattr(repository, "save_subject_control", unexpected_write)
        assert put(client, path, body) == proposal
        for identity, command in (
            (HEADERS | {"X-Actor-Id": "different-maker"}, body),
            (HEADERS, body | {"reference": body["reference"] | {"revision": "other-original"}}),
        ):
            response = client.put(path, headers=identity, json=command)
            assert response.status_code == 409, response.text
            assert response.json()["detail"]["code"] == "COMPOSITE_SUBJECT_IMMUTABLE_CONFLICT"
    assert retained_state(repository) == before


def test_controlled_scenario_exact_policy_put_retry_retains_custody_with_source_off(
    tmp_path, monkeypatch
):
    capture_controlled_scenario(tmp_path, monkeypatch, inspect_retained_retry=True)


@pytest.mark.parametrize(
    "change",
    [
        "legacy",
        "mixed",
        "status",
        "purpose",
        "qualified",
        "actual",
        "scenario",
        "alias",
        "key-collision",
        "legacy-definition",
        "legacy-authority",
    ],
)
def test_controlled_scenario_refuses_mixed_temporal_and_authority_claims(
    tmp_path, monkeypatch, change
):
    _, receipt = capture_controlled_scenario(tmp_path, monkeypatch)
    wire = deepcopy(receipt)
    approval = wire["finalization"]["evaluation_approval"]
    proof = approval["operation_verification"]
    if change == "legacy":
        wire["product_version"] = "v3"
    elif change == "mixed":
        approval["proposal"]["policy_approval"]["product_version"] = "v2"
    elif change == "status":
        proof["original_signature_status"] = "VERIFIED_AT_ORIGINAL_APPROVAL"
    elif change == "purpose":
        proof["request"]["purpose"] = "COMPOSITE_HISTORICAL_MONTHLY_POLICY_ADMISSION"
    elif change == "qualified":
        proof["posture"] = "QUALIFIED_RECEIPT"
    elif change == "actual":
        proof["mapping"]["actual_issued_at"] = "2099-01-01T00:00:00.000000Z"
    elif change == "scenario":
        proof["mapping"]["scenario_approved_at"] = "2099-01-01T00:00:00.000000Z"
    elif change == "alias":
        proof["mapping"]["original_approved_at"] = proof["mapping"]["scenario_approved_at"]
    elif change == "legacy-definition":
        wire["finalization"]["definition"]["product_version"] = "v2"
    elif change == "legacy-authority":
        wire["finalization"]["definition"]["source_authority"]["payload"]["product_version"] = "v2"
    else:
        proof["verifier_key_digest"] = proof["signer_key_digest"]
    with pytest.raises(ValueError):
        decode_subject_receipt(wire)


@pytest.mark.parametrize("lf_rule", [False, True], ids=["old-attributes-refuse", "lf-rule-retains"])
def test_raw_contract_family_survives_real_git_checkout_with_autocrlf(tmp_path, lf_rule):
    import hashlib
    import os
    import subprocess
    from pathlib import Path

    root = Path(__file__).resolve().parents[4]
    relative = Path("docs/contracts/composite-controlled-scenario")
    source = root / relative
    originals = {path.name: path.read_bytes() for path in source.glob("*.json")}
    assert len(originals) == 6
    rule = "docs/contracts/composite-controlled-scenario/*.json text eol=lf"
    attributes = (root / ".gitattributes").read_text(encoding="utf-8")
    if not lf_rule:
        attributes = "\n".join(line for line in attributes.splitlines() if line != rule) + "\n"
    environment = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    environment.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)

    def git(*arguments):
        subprocess.run(
            ["git", *arguments],
            cwd=tmp_path,
            env=environment,
            check=True,
            capture_output=True,
        )

    git("init", "--quiet")
    git("config", "core.autocrlf", "true")
    (tmp_path / ".gitattributes").write_text(attributes, encoding="utf-8", newline="\n")
    target = tmp_path / relative
    target.mkdir(parents=True)
    for name, raw in originals.items():
        (target / name).write_bytes(raw)
    git("add", "--all")
    for name in originals:
        (target / name).unlink()
    git("checkout-index", "--all", "--force")
    for name, expected in originals.items():
        actual = (target / name).read_bytes()
        if lf_rule:
            assert actual == expected, name
            assert hashlib.sha256(actual).digest() == hashlib.sha256(expected).digest(), name
        else:
            assert actual != expected and b"\r\n" in actual, name
            assert hashlib.sha256(actual).digest() != hashlib.sha256(expected).digest(), name


def test_exported_controlled_scenario_graph_schema_hashes_and_bad_vectors():
    import hashlib
    import json
    from pathlib import Path
    from src.core.common.canonical import hash_canonical_payload

    directory = Path(__file__).resolve().parents[4] / "docs/contracts/composite-controlled-scenario"
    manifest = json.loads((directory / "manifest.json").read_bytes())
    for name, expected in manifest["raw_file_sha256"].items():
        raw = (directory / name).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == expected
        assert (
            hash_canonical_payload(json.loads(raw)) == manifest["canonical_content_digests"][name]
        )
    wire = json.loads((directory / "valid-graph.json").read_bytes())
    model = decode_subject_receipt(wire)
    assert model.model_dump(mode="json") == wire
    from src.core.composite_eligibility.staged_publication import initial_projection

    approval = model.finalization.evaluation_approval
    products = initial_projection(
        approval.proposal, approval.claims_digest, approval.approved_by, approval.approved_at
    )
    for product in products:
        path = directory / (
            product.product_name + "." + product.product_version + ".controlled.json"
        )
        assert product.model_dump(mode="json") == json.loads(path.read_bytes())
    assert (
        type(model).model_json_schema()
        == json.loads((directory / "schemas.json").read_bytes())[
            "CompositeEligibilityFinalizationReceipt.v4"
        ]
    )
    for vector in json.loads((directory / "refusal-vectors.json").read_bytes()):
        bad = deepcopy(wire)
        keys = vector["pointer"].strip("/").split("/")
        target = bad
        for key in keys[:-1]:
            target = target[key]
        target[keys[-1]] = vector["replacement"]
        with pytest.raises(ValueError):
            decode_subject_receipt(bad)


@pytest.mark.parametrize(
    "change",
    [
        "encoding",
        "oversized",
        "digest",
        "attachments",
        "independence",
        "issuance",
        "window",
        "proof-mapping",
        "policy-mapping",
        "policy-request",
        "policy-intent",
        "self-approval",
        "approval-clock",
        "approval-request",
    ],
)
def test_controlled_scenario_normalized_guards_refuse_specific_invalid_claims(
    scenario_native_history, change
):
    import base64
    from datetime import UTC, datetime
    from src.core.common.canonical import hash_canonical_payload
    from src.core.composite_eligibility.controlled_scenario import (
        ControlledScenarioPolicyMapping,
        ControlledScenarioVerification,
        ControlledScenarioMonthlyPolicyProposal,
        ControlledScenarioMonthlyPolicyApproval,
    )
    from src.infrastructure.composites.controlled_source_verifier import (
        NativeControlledHistoricalVerifier,
    )
    from src.infrastructure.composites.native_source_configuration import (
        NativeHistoricalConfiguration,
    )

    document, request, *_ = scenario_native_history
    request = request.model_copy(
        update={
            "intent_digest": hash_canonical_payload(
                {
                    "reference": request.reference.model_dump(mode="json"),
                    "proposal_revision": request.revision,
                }
            )
        }
    )
    verifier = NativeControlledHistoricalVerifier(
        NativeHistoricalConfiguration.model_validate(document)
    )
    proof = verifier.verify(request)
    mapping = proof.mapping.model_dump(mode="json")
    if change in {"encoding", "oversized", "digest", "attachments"}:
        if change == "encoding":
            mapping["raw_original_base64"] = "!!!!"
        elif change == "oversized":
            mapping["raw_original_base64"] = base64.b64encode(bytes(2_000_001)).decode()
        elif change == "digest":
            mapping["raw_original_base64"] = base64.b64encode(b"other").decode()
        else:
            mapping["attachments"] *= 2
        with pytest.raises(
            ValueError,
            match="COMPOSITE_HISTORICAL_POLICY_RAW|COMPOSITE_ELIGIBILITY_ATTACHMENTS_NONCANONICAL",
        ):
            ControlledScenarioPolicyMapping.model_validate(mapping)
        return
    if change in {"independence", "issuance", "window", "proof-mapping"}:
        wire = proof.model_dump(mode="json")
        if change == "independence":
            wire["verifier_principal_id"] = wire["signer_principal_id"]
        elif change == "issuance":
            wire["request"]["requested_at"] = mapping["scenario_approved_at"]
        elif change == "proof-mapping":
            wire["request"]["reporting_currency"] = "EUR"
        else:
            wire["checked_at"] = "2099-01-01T00:00:00.000000Z"
        with pytest.raises(
            ValueError,
            match="COMPOSITE_HISTORICAL_POLICY_MAPPING_MISMATCH|COMPOSITE_HISTORICAL_POLICY_INDEPENDENCE_REQUIRED|COMPOSITE_HISTORICAL_POLICY_ORIGINAL_CLOCK_INVALID|COMPOSITE_HISTORICAL_POLICY_ADMISSION_WINDOW_INVALID",
        ):
            ControlledScenarioVerification.model_validate(wire)
        return
    fields = dict(
        proposal_revision=request.revision,
        eligibility_policy_version=mapping["eligibility_policy_version"],
        policy=mapping["policy"],
        attachments=mapping["attachments"],
        proposed_by=request.actor_id,
        proposed_at=request.requested_at,
        verification=proof.model_dump(mode="json"),
    )
    if change.startswith("policy-"):
        if change == "policy-mapping":
            fields["eligibility_policy_version"] = "different-policy"
        elif change == "policy-request":
            fields["proposed_by"] = "different-maker"
        else:
            wrong = request.model_copy(update={"intent_digest": "sha256:" + "0" * 64})
            fields["verification"] = verifier.verify(wrong).model_dump(mode="json")
        with pytest.raises(
            ValueError,
            match="COMPOSITE_HISTORICAL_POLICY_MAPPING_MISMATCH|COMPOSITE_HISTORICAL_POLICY_REQUEST_MISMATCH|COMPOSITE_HISTORICAL_POLICY_INTENT_MISMATCH",
        ):
            ControlledScenarioMonthlyPolicyProposal.model_validate(fields)
        return
    proposal = ControlledScenarioMonthlyPolicyProposal.model_validate(fields)
    instant = datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")
    approved_request = request.model_copy(
        update={
            "operation": "POLICY_APPROVAL",
            "actor_id": "independent-current-checker",
            "requested_at": instant,
            "intent_digest": proposal.content_hash,
        }
    )
    verification = verifier.verify(approved_request)
    fields = dict(
        proposal=proposal.model_dump(mode="json"),
        approved_by=approved_request.actor_id,
        approved_at=instant,
        verification=verification.model_dump(mode="json"),
    )
    if change == "self-approval":
        fields["approved_by"] = proposal.proposed_by
        error = "COMPOSITE_ELIGIBILITY_SELF_APPROVAL_FORBIDDEN"
    elif change == "approval-clock":
        fields["approved_at"] = mapping["scenario_approved_at"]
        error = "COMPOSITE_ELIGIBILITY_APPROVAL_BEFORE_PROPOSAL"
    else:
        fields["approved_by"] = "different-current-checker"
        error = "COMPOSITE_HISTORICAL_POLICY_REQUEST_MISMATCH"
    with pytest.raises(ValueError, match=error):
        ControlledScenarioMonthlyPolicyApproval.model_validate(fields)


def fresh_scenario_proposal(service, proposal, change):
    from src.core.composite_eligibility.evaluation import evaluate_monthly_eligibility

    wire = proposal.model_dump(mode="json", exclude={"content_hash", "operation_verification"})
    wire["proposed_at"] = service.clock()
    if change == "actor":
        wire["proposed_by"] = "other-admitted-maker"
    if change == "payload":
        wire["target_membership_revision"] = "different-membership-intent"
    wire["evaluation"] = evaluate_monthly_eligibility(
        proposal.policy_approval.approval.proposal.policy,
        proposal.observations,
        evaluated_at=wire["proposed_at"],
        universe_content_hash=proposal.policy_approval.proposal.subject.universe.content_hash,
    ).model_dump(mode="json")
    return service.historical().evaluation_proposal(wire)


def fresh_scenario_approval(service, approval, change):
    from src.core.composite_eligibility.staged_controls import subject_approval_claims
    from src.core.composite_eligibility.staged_publication import initial_projection
    from tests.composite_staged_eligibility_helpers import verification_request

    proposal = (
        fresh_scenario_proposal(service, approval.proposal, "payload")
        if change == "payload"
        else approval.proposal
    )
    actor = "other-admitted-checker" if change == "actor" else approval.approved_by
    instant = service.clock()
    claims = subject_approval_claims(proposal, actor, instant)
    membership, universe = initial_projection(proposal, claims, actor, instant)
    receipt = service.verifier.verify(
        verification_request(
            proposal.policy_approval.proposal.subject, "ELIGIBILITY_POLICY_EVALUATION", claims
        )
    )
    wire = approval.model_dump(mode="json", exclude={"content_hash", "operation_verification"})
    wire.update(
        proposal=proposal.model_dump(mode="json"),
        approved_by=actor,
        approved_at=instant,
        claims_digest=claims,
        membership_content_hash=membership.content_hash,
        universe_content_hash=universe.content_hash,
        verification=receipt.model_dump(mode="json"),
    )
    return service.historical().evaluation_approval(wire)


@pytest.mark.parametrize("kind", ["proposal", "approval"])
@pytest.mark.parametrize("change", ["same", "actor", "payload", "mixed", "missing"])
def test_controlled_scenario_conflict_recovers_only_exact_intent_same_family_winner(
    tmp_path, monkeypatch, kind, change
):
    import json
    from pathlib import Path
    from src.core.composite_eligibility.staged_subject import subject_key
    from src.core.composite_repository import DpmCompositeConflictError
    from tests.unit.api.test_composite_subject_lifecycle_routes import retained_state

    def inspect(service, controls):
        control = STAGED_CONTROL_ADAPTER.validate_python(controls[2 if kind == "proposal" else 3])
        if change == "missing":
            winner = None
        elif change == "mixed":
            name = (
                "CompositeSubjectEvaluationProposal"
                if kind == "proposal"
                else "CompositeSubjectEvaluationApproval"
            )
            path = (
                Path(__file__).resolve().parents[4]
                / "docs/contracts/composite-historical-subject"
                / (name + ".v2.controlled.json")
            )
            winner = STAGED_CONTROL_ADAPTER.validate_python(json.loads(path.read_bytes()))
        else:
            winner = (fresh_scenario_proposal if kind == "proposal" else fresh_scenario_approval)(
                service, control, change
            )
            # Winner is genuinely domain-valid, with fresh current proofs and a different attempt hash.
            assert type(winner).model_validate(winner.model_dump(mode="json")) == winner
            assert winner.content_hash != control.content_hash
        failure = DpmCompositeConflictError("injected-concurrent-immutable-winner")
        before = retained_state(service.repository)
        calls = []

        def losing_save(**kwargs):
            assert kwargs["control"] is control
            raise failure

        def retained_winner(**kwargs):
            calls.append(kwargs)
            return winner

        with monkeypatch.context() as race:
            race.setattr(service.repository, "save_subject_control", losing_save)
            race.setattr(service.repository, "get_subject_control", retained_winner)
            key = subject_key(
                control.policy_approval.proposal.subject
                if kind == "proposal"
                else control.proposal.policy_approval.proposal.subject
            )
            if change == "same":
                assert service.historical().save_evaluation(key, control) is winner
            else:
                with pytest.raises(DpmCompositeConflictError) as refused:
                    service.historical().save_evaluation(key, control)
                assert refused.value is failure
            assert calls == [
                dict(
                    key=key,
                    kind=control.product_name,
                    revision=control.evaluation_revision
                    if kind == "proposal"
                    else control.proposal.evaluation_revision,
                )
            ]
        assert retained_state(service.repository) == before

    capture_controlled_scenario(tmp_path, monkeypatch, inspect_controls=inspect)
