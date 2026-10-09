"""Registered custody/publication proof using explicitly unqualified synthetic inputs."""

import pytest
from decimal import Inexact, ROUND_UP, Rounded, localcontext
from fastapi.testclient import TestClient

from src.api.dependencies import get_composite_monthly_eligibility_service
from src.api.main import app
from src.api.services.composite_monthly_eligibility import (
    CompositeMonthlyEligibilityApplicationService,
)
from src.core.composite_eligibility.source import MonthlyEligibilitySourceResolution
from src.core.common.canonical import hash_canonical_payload
from src.core.composite_universe import DpmCompositeUniverseAttestation
from src.core.composite_eligibility.evaluation_control import MonthlyEvaluationProposal
from src.core.composite_eligibility.evaluation_control import MonthlyEvaluationApproval
from src.core.composite_repository import DpmCompositeConflictError
from pydantic import ValidationError
from tests.composite_monthly_eligibility_helpers import (
    BASE,
    HEADERS,
    prospective_proposal_body,
    retained_repository,
    source_snapshot,
)

CHECKER = HEADERS | {"X-Actor-Id": "synthetic-checker"}
URL = BASE + "/evaluations/synthetic-evaluation-r1"


@pytest.mark.parametrize(
    "evaluation_api",
    [{"prior_month_end_assets": "300", "month_end_assets": "300"}],
    indirect=True,
)
def test_registered_proposal_approval_and_replay_preserve_hash_under_hostile_context(
    evaluation_api,
):
    normal = propose(evaluation_api)
    client, _, _, _, _, body, resolutions = evaluation_api
    hostile_url = BASE + "/evaluations/synthetic-hostile-context"
    with localcontext() as caller:
        caller.rounding = ROUND_UP
        caller.prec = 6
        caller.traps[Inexact] = caller.traps[Rounded] = True
        retained = client.get(URL, headers=HEADERS)
        assert retained.status_code == 200 and retained.json() == normal
        response = client.put(hostile_url, headers=HEADERS, json=body)
        assert response.status_code == 200, response.text
        proposal = response.json()
        assert proposal["evaluation"] == normal["evaluation"]
        expected = {"expected_proposal_content_hash": proposal["content_hash"]}
        approved = client.put(hostile_url + "/approval", headers=CHECKER, json=expected)
        assert approved.status_code == 200, approved.text
        replay = client.put(hostile_url + "/approval", headers=CHECKER, json=expected)
        assert replay.status_code == 200 and replay.json() == approved.json()
        retained_approval = client.get(hostile_url + "/approval", headers=HEADERS)
        assert retained_approval.status_code == 200 and retained_approval.json() == approved.json()
        assert caller.rounding == ROUND_UP and caller.prec == 6
        assert caller.traps[Inexact] and caller.traps[Rounded]
    assert len(resolutions) == 2 and len(publications(evaluation_api)) == 2


def test_exact_resolver_openapi_declares_both_receipt_products_without_new_route():
    schema = app.openapi()
    path = "/api/v1/rebalance/composites/{composite_id}/definitions/{definition_version}/eligibility-evidence/resolve"
    response = schema["paths"][path]["post"]["responses"]["200"]["content"]["application/json"][
        "schema"
    ]
    assert response["discriminator"]["propertyName"] == "product_name"
    assert set(response["discriminator"]["mapping"]) == {
        "CompositeEligibilityFinalizationReceipt",
        "CompositeMonthlyEligibilityPublicationReceipt",
    }
    monthly = schema["components"]["schemas"]["MonthlyEligibilityPublicationReceipt"]
    assert monthly["additionalProperties"] is False
    assert monthly["properties"]["publication_sequence"]["exclusiveMinimum"] == 0
    assert set(monthly["required"]) >= {
        "definition",
        "approval",
        "membership_binding",
        "universe_binding",
        "source_cut_id",
        "publication_sequence",
    }


def test_actual_791_main_unmarked_monthly_approval_preserves_original_wire_and_hash():
    import json
    from pathlib import Path

    wire = json.loads(
        (
            Path(__file__).parents[2]
            / "fixtures/composites/historical-recurring-monthly-approval.json"
        ).read_text(encoding="utf-8")
    )
    assert (
        wire["content_hash"]
        == "sha256:9fe7b283b8f54763a5d345034716f79993b3bce4881b7f747862e54f3876f72b"
    )
    assert "publication_evidence_version" not in wire["proposal"]
    restored = MonthlyEvaluationApproval.model_validate(wire)
    assert restored.model_dump(mode="json") == wire
    assert restored.proposal.source_assembly_evidence is not None


@pytest.mark.parametrize("legacy", [False, True])
def test_monthly_unqualified_or_unmarked_custody_cannot_invent_published_proof(
    evaluation_api, legacy
):
    repository = evaluation_api[1]
    wire = propose(evaluation_api)
    if legacy:
        wire.pop("publication_evidence_version")
        wire["content_hash"] = ""
        retained = MonthlyEvaluationProposal.model_validate(wire)
        # Restore an earlier unmarked proposal, without authorizing a client marker downgrade.
        repository._monthly_evaluations.clear()
        repository.save_monthly_evaluation_proposal(proposal=retained)
        wire = retained.model_dump(mode="json")
    response = approve(evaluation_api, wire)
    assert response.status_code == 200, response.text
    approval = response.json()
    arguments = dict(
        tenant_id="synthetic-tenant",
        composite_id="synthetic-composite",
        definition_version="synthetic-definition",
        evaluation_revision=wire["evaluation_revision"],
        approval_content_hash=approval["content_hash"],
    )
    if legacy:
        assert repository.resolve_monthly_eligibility_evidence(**arguments) is None
        assert "publication_evidence_version" not in approval["proposal"]
    else:
        with pytest.raises(ValueError, match="COMPOSITE_MONTHLY_EVIDENCE_UNAVAILABLE"):
            repository.resolve_monthly_eligibility_evidence(**arguments)
    assert evaluation_api[0].get(URL + "/approval", headers=HEADERS).json() == approval
    assert approve(evaluation_api, wire).json() == approval
    assert len(publications(evaluation_api)) == 2 and len(evaluation_api[6]) == 1


@pytest.mark.parametrize(
    "corruption",
    [
        None,
        "policy",
        "policy_proposal",
        "evaluation",
        "parent",
        "membership",
        "universe",
        "publication",
        "input_universe",
        "policy_rehashed",
        "evaluation_rehashed",
        "publication_count",
    ],
)
def test_monthly_memory_resolver_joins_independent_custody(evaluation_api, corruption):
    approval = approve_with_complete_source(evaluation_api)
    proposal = approval["proposal"]
    repository = evaluation_api[1]
    check_monthly_custody(evaluation_api, repository, proposal, approval, corruption)


def approve_with_complete_source(evaluation_api):
    from src.core.composite_eligibility.source_assembly import (
        MonthlySourceAssembly,
        VerifiedMonthlySourceAssembly,
        assembly_verification_request,
    )
    from tests.composite_staged_eligibility_helpers import synthetic_verification
    from tests.composite_monthly_source_helpers import (
        assembly_material,
    )

    _, material = assembly_material()
    assembly = MonthlySourceAssembly.model_validate(material)
    evaluation_api[4]["evidence"] = VerifiedMonthlySourceAssembly(
        assembly=assembly,
        verification=synthetic_verification(assembly_verification_request(assembly)),
    )
    proposal = propose(evaluation_api)
    response = approve(evaluation_api, proposal)
    assert response.status_code == 200, response.text
    approval = response.json()
    return approval


@pytest.fixture
def amendment_projection(evaluation_api):
    from src.core.composite_eligibility.publication import build_monthly_publication
    from tests.composite_monthly_amendment_helpers import corrected_monthly_proposal

    original = approve_with_complete_source(evaluation_api)
    repository = evaluation_api[1]
    scope = dict(
        tenant_id="synthetic-tenant",
        composite_id="synthetic-composite",
        definition_version="synthetic-definition",
    )
    resolver = scope | {
        "evaluation_revision": original["proposal"]["evaluation_revision"],
        "approval_content_hash": original["content_hash"],
    }
    receipt = repository.resolve_monthly_eligibility_evidence(**resolver)
    retained_wire = receipt.model_dump(mode="json")
    parent = repository.get_membership_revision(
        **scope, membership_revision=original["proposal"]["target_membership_revision"]
    )
    proposal = corrected_monthly_proposal(receipt, parent, sequence=receipt.publication_sequence)
    result = build_monthly_publication(
        proposal,
        parent,
        approved_by="synthetic-correction-checker",
        approved_at="2026-10-02T02:00:00.000000Z",
    )
    return original, repository, scope, resolver, receipt, retained_wire, parent, proposal, result


def test_domain_source_amendment_binds_changed_facts_and_preserves_original_custody(
    amendment_projection,
):
    from src.core.composite_eligibility.monthly_amendment import (
        MonthlyAmendmentApproval,
        decode_monthly_proposal,
        decode_monthly_approval,
    )
    from src.core.composite_eligibility.publication import build_monthly_publication
    from src.core.composite_eligibility.monthly_evidence import (
        MonthlyAmendmentPublicationReceipt,
        MonthlyEligibilityPublicationReceipt,
    )

    original, repository, _, resolver, receipt, retained_wire, parent, proposal, result = (
        amendment_projection
    )
    approval, member, universe = result
    assert isinstance(approval, MonthlyAmendmentApproval)
    assert proposal.evaluation.included_count == 0
    assert original["proposal"]["evaluation"]["included_count"] == 1
    assert member.supersedes_membership_revision == parent.membership_revision
    locator = next(
        item for item in universe.source_products if item.product_name == approval.product_name
    )
    assert locator.contract_version == "v2" and locator.content_hash == approval.content_hash
    assert decode_monthly_proposal(proposal.model_dump(mode="json")) == proposal
    assert decode_monthly_approval(approval.model_dump(mode="json")) == approval
    amended_receipt = MonthlyAmendmentPublicationReceipt(
        definition=receipt.definition,
        approval=approval,
        membership_binding={
            "product_name": "CompositeMembership",
            "product_version": "v1",
            "revision": member.membership_revision,
            "digest": member.content_hash,
        },
        universe_binding={
            "product_name": "CompositeUniverseAttestation",
            "product_version": "v1",
            "revision": universe.attestation_version,
            "digest": universe.content_hash,
        },
        source_cut_id=universe.source_cut_id,
        publication_sequence=receipt.publication_sequence + 1,
        lineage=proposal.amendment,
    )
    assert (
        MonthlyAmendmentPublicationReceipt.model_validate(amended_receipt.model_dump(mode="json"))
        == amended_receipt
    )
    with pytest.raises(ValidationError):
        MonthlyEligibilityPublicationReceipt.model_validate(amended_receipt.model_dump(mode="json"))
    altered_lineage = amended_receipt.model_dump(mode="json")
    altered_lineage["content_hash"] = ""
    altered_lineage["lineage"]["reason"] = "Not approved with this replacement graph"
    with pytest.raises(ValidationError, match="RECEIPT_LINEAGE_MISMATCH"):
        MonthlyAmendmentPublicationReceipt.model_validate(altered_lineage)
    assert (
        build_monthly_publication(
            proposal, parent, approved_by=approval.approved_by, approved_at=approval.approved_at
        )
        == result
    )
    assert (
        repository.resolve_monthly_eligibility_evidence(**resolver).model_dump(mode="json")
        == retained_wire
    )
    for model, value in (
        (MonthlyEvaluationProposal, proposal),
        (MonthlyEvaluationApproval, approval),
    ):
        with pytest.raises(ValidationError):
            model.model_validate(value.model_dump(mode="json"))
    with pytest.raises(ValueError, match="SELF_APPROVAL_FORBIDDEN"):
        build_monthly_publication(
            proposal, parent, approved_by=proposal.proposed_by, approved_at=approval.approved_at
        )
    tampered = approval.model_dump(mode="json")
    tampered["proposal"]["amendment"]["reason"] = "Changed after independent approval"
    with pytest.raises(ValidationError, match="CONTENT_MISMATCH"):
        decode_monthly_approval(tampered)


def test_monthly_authority_selects_chain_tip_and_refuses_forks_and_stale_scope(
    amendment_projection,
):
    from src.core.composite_eligibility.monthly_amendment import MonthlyAmendmentProposal
    from src.core.composite_eligibility.monthly_authority import (
        selected_monthly_approval,
        require_source_correction,
        MAX_MONTHLY_AUTHORITY_RECORDS,
    )
    from src.core.composite_eligibility.publication import build_monthly_publication

    _, _, scope, _, receipt, _, parent, proposal, result = amendment_projection
    root, corrected = receipt.approval, result[0]
    query = dict(scope=tuple(scope.values()), month="2026-09")
    assert selected_monthly_approval([corrected, root], **query) == corrected
    assert selected_monthly_approval([root], **query) == root
    require_source_correction(proposal, root)
    with pytest.raises(ValueError, match="STALE_AUTHORITY"):
        require_source_correction(proposal, corrected)
    fork_wire = proposal.model_dump(mode="json")
    fork_wire.update(
        evaluation_revision="competing.correction.r2",
        target_membership_revision="competing.membership.r2",
        content_hash="",
    )
    competing, _, _ = build_monthly_publication(
        MonthlyAmendmentProposal.model_validate(fork_wire),
        parent,
        approved_by="synthetic-other-checker",
        approved_at=corrected.approved_at,
    )
    with pytest.raises(ValueError, match="FORK_FORBIDDEN"):
        selected_monthly_approval([root, corrected, competing], **query)
    for rows, expected in (
        ([], "HISTORY_UNAVAILABLE"),
        ([corrected], "ROOT_AMBIGUOUS"),
        ([root] * (MAX_MONTHLY_AUTHORITY_RECORDS + 1), "HISTORY_UNAVAILABLE"),
    ):
        with pytest.raises(ValueError, match=expected):
            selected_monthly_approval(rows, **query)
    with pytest.raises(ValueError, match="SCOPE_MISMATCH"):
        selected_monthly_approval(
            [root, corrected], scope=("foreign-tenant", *query["scope"][1:]), month="2026-09"
        )


def check_monthly_custody(evaluation_api, repository, proposal, approval, corruption):
    arguments = dict(
        tenant_id="synthetic-tenant",
        composite_id="synthetic-composite",
        definition_version="synthetic-definition",
        evaluation_revision=proposal["evaluation_revision"],
        approval_content_hash=approval["content_hash"],
    )
    receipt = repository.resolve_monthly_eligibility_evidence(**arguments)
    assert receipt.approval.model_dump(mode="json") == approval
    assert receipt.publication_sequence == 2
    if corruption is None:
        from copy import deepcopy
        from src.core.composite_eligibility.monthly_evidence import (
            MonthlyEligibilityPublicationReceipt,
        )

        for field, value in (
            (
                "membership_binding",
                {**receipt.membership_binding.model_dump(), "revision": "wrong-member"},
            ),
            (
                "universe_binding",
                {**receipt.universe_binding.model_dump(), "revision": "wrong-month"},
            ),
            ("source_cut_id", "wrong-cut"),
            ("publication_sequence", 0),
            ("content_hash", "sha256:" + "e" * 64),
            ("unknown", "refuse"),
        ):
            changed = {**receipt.model_dump(mode="json"), "content_hash": "", field: value}
            with pytest.raises(ValidationError):
                MonthlyEligibilityPublicationReceipt.model_validate(changed)
        for target in ("definition", "source_authority"):
            changed = deepcopy(receipt.model_dump(mode="json"))
            selected = (
                changed["definition"] if target == "definition" else changed["definition"][target]
            )
            selected["unknown"] = "must-not-be-dropped"
            changed["content_hash"] = ""
            with pytest.raises(ValidationError, match="DEFINITION_WIRE_INVALID"):
                MonthlyEligibilityPublicationReceipt.model_validate(changed)
    with pytest.raises(DpmCompositeConflictError, match="BINDING_MISMATCH"):
        repository.resolve_monthly_eligibility_evidence(
            **{**arguments, "approval_content_hash": "sha256:" + "e" * 64}
        )
    stores = {
        "policy": repository._monthly_approvals,
        "policy_proposal": repository._monthly_proposals,
        "evaluation": repository._monthly_evaluations,
        "parent": repository._membership_revisions,
        "membership": repository._membership_revisions,
        "universe": repository._universe_attestations,
        "input_universe": repository._universe_attestations,
        "publication": repository._publications,
        "policy_rehashed": repository._monthly_proposals,
        "evaluation_rehashed": repository._monthly_evaluations,
        "publication_count": repository._publications,
    }
    if corruption is not None:
        store = stores[corruption]
        key = (
            next(iter(store))
            if corruption in ("parent", "input_universe")
            else next(reversed(store))
        )
        retained = store.pop(key)
        if corruption in ("policy_rehashed", "evaluation_rehashed"):
            changed = retained.model_dump(mode="json")
            changed["proposed_by" if corruption == "policy_rehashed" else "correlation_id"] = (
                "other-valid-retained-input"
            )
            changed["content_hash"] = ""
            store[key] = type(retained).model_validate(changed)
        elif corruption == "publication_count":
            store[key] = retained.model_copy(update={"decision_count": retained.decision_count + 1})
        try:
            with pytest.raises((DpmCompositeConflictError, ValueError)):
                repository.resolve_monthly_eligibility_evidence(**arguments)
        finally:
            store[key] = retained
        assert repository.resolve_monthly_eligibility_evidence(**arguments) == receipt
    assert len(publications(evaluation_api)) == 2
    assert len(evaluation_api[6]) == 1


@pytest.mark.parametrize(
    "fault",
    [
        None,
        "proposal",
        "policy",
        "policy_proposal",
        "definition",
        "definition_hash",
        "publication",
        "publication_body",
        "digest",
    ],
)
def test_monthly_sql_join_fails_closed_on_partial_snapshot(evaluation_api, monkeypatch, fault):
    from src.infrastructure.composites import monthly_evidence

    wire = approve_with_complete_source(evaluation_api)
    repository = evaluation_api[1]
    key = (
        "synthetic-tenant",
        "synthetic-composite",
        "synthetic-definition",
        wire["proposal"]["evaluation_revision"],
    )
    approval = repository.get_monthly_evaluation_approval(
        tenant_id=key[0], composite_id=key[1], definition_version=key[2], evaluation_revision=key[3]
    )
    proposal = approval.proposal
    definition = repository.get_definition(
        tenant_id=key[0], composite_id=key[1], definition_version=key[2]
    )
    rows = [
        None
        if fault == "definition"
        else {
            "payload_json": definition.model_dump(mode="json"),
            "content_hash": "sha256:" + "e" * 64
            if fault == "definition_hash"
            else definition.content_hash,
        },
        None if fault == "publication" else {"sequence": 2},
    ]

    class ReadSnapshot:
        def execute(self, query, parameters):
            assert parameters == (
                key[:3]
                if "dpm_composite_definitions" in query
                else (*key[:3], proposal.target_membership_revision)
            )
            return self

        def fetchone(self):
            return rows.pop(0)

    monkeypatch.setattr(
        monthly_evidence.evaluation_control, "get_approval", lambda connection, requested: approval
    )
    monkeypatch.setattr(
        monthly_evidence.evaluation_control,
        "get_proposal",
        lambda connection, requested: None if fault == "proposal" else proposal,
    )
    monkeypatch.setattr(
        monthly_evidence.policy_control,
        "get_approval",
        lambda connection, requested: None if fault == "policy" else proposal.policy_approval,
    )
    monkeypatch.setattr(
        monthly_evidence.policy_control,
        "get_proposal",
        lambda connection, requested: (
            None if fault == "policy_proposal" else proposal.policy_approval.proposal
        ),
    )
    monkeypatch.setattr(
        monthly_evidence,
        "_membership",
        lambda connection, requested: repository.get_membership_revision(
            tenant_id=requested[0],
            composite_id=requested[1],
            definition_version=requested[2],
            membership_revision=requested[3],
        ),
    )
    monkeypatch.setattr(
        monthly_evidence,
        "_universe",
        lambda connection, requested: repository.get_universe_attestation(
            tenant_id=requested[0],
            composite_id=requested[1],
            definition_version=requested[2],
            membership_revision=requested[3],
            attestation_version=requested[4],
        ),
    )
    monkeypatch.setattr(
        monthly_evidence.publication,
        "get_publication",
        lambda **kwargs: (
            None
            if fault == "publication_body"
            else repository.get_publication(tenant_id=key[0], sequence=2)
        ),
    )
    digest = "sha256:" + "e" * 64 if fault == "digest" else approval.content_hash
    if fault is None:
        resolved = monthly_evidence.resolve(ReadSnapshot(), key, digest)
        assert resolved.approval == approval and resolved.publication_sequence == 2
    else:
        with pytest.raises(
            DpmCompositeConflictError,
            match="BINDING_MISMATCH" if fault == "digest" else "CUSTODY_INTEGRITY_CONFLICT",
        ):
            monthly_evidence.resolve(ReadSnapshot(), key, digest)


def test_monthly_publication_marker_is_server_owned_and_legacy_omission_is_preserved(
    evaluation_api,
):
    from src.core.composite_eligibility.publication import build_monthly_publication

    wire = propose(evaluation_api)
    assert wire["publication_evidence_version"] == "v1"
    proposal = MonthlyEvaluationProposal.model_validate(wire)
    for invalid in (None, "v2", "", 1, False):
        with pytest.raises(ValidationError):
            MonthlyEvaluationProposal.model_validate(
                {**wire, "publication_evidence_version": invalid}
            )
    for supplied in (None, "v1"):
        refused = evaluation_api[0].put(
            URL,
            headers=HEADERS,
            json={**evaluation_api[5], "publication_evidence_version": supplied},
        )
        assert refused.status_code == 422, refused.text
    legacy_wire = dict(wire)
    legacy_wire.pop("publication_evidence_version")
    legacy_wire["content_hash"] = ""
    legacy = MonthlyEvaluationProposal.model_validate(legacy_wire)
    assert "publication_evidence_version" not in legacy.model_dump(mode="json")
    assert legacy.content_hash == hash_canonical_payload(
        {name: value for name, value in legacy_wire.items() if name != "content_hash"}
    )
    parent = evaluation_api[1].get_membership_revision(
        tenant_id="synthetic-tenant",
        composite_id="synthetic-composite",
        definition_version="synthetic-definition",
        membership_revision="synthetic-membership",
    )
    checked, _, universe = build_monthly_publication(
        proposal, parent, approved_by="synthetic-checker", approved_at=proposal.proposed_at
    )
    locators = [
        item
        for item in universe.source_products
        if item.product_name == "CompositeMonthlyEvaluationApproval"
    ]
    assert len(locators) == 1
    locator = locators[0]
    assert (
        locator.owner_service,
        locator.contract_version,
        locator.authority_scope,
        locator.source_cut_id,
        locator.source_watermark,
        locator.content_hash,
    ) == (
        "lotus-manage",
        "v1",
        "POLICY_INPUT",
        universe.source_cut_id,
        proposal.evaluation_revision,
        checked.content_hash,
    )
    assert checked.published_universe_content_hash == universe.content_hash
    _, _, old_universe = build_monthly_publication(
        legacy, parent, approved_by="synthetic-checker", approved_at=legacy.proposed_at
    )
    assert old_universe.source_products == legacy.universe.source_products
    field = MonthlyEvaluationProposal.model_json_schema()["properties"][
        "publication_evidence_version"
    ]
    assert field["const"] == "v1" and field["type"] == "string"
    assert "default" not in field and "anyOf" not in field


@pytest.mark.parametrize("fault", ["unfinalized_source", "parent_coverage_gap"])
def test_publication_refuses_individually_valid_unfinalized_or_incomplete_history(
    evaluation_api, fault
):
    from src.core.composite_eligibility.evaluation import evaluate_monthly_eligibility
    from src.core.composite_eligibility.observations import MonthlyEligibilityObservations
    from src.core.composite_eligibility.publication import build_monthly_publication
    from src.core.composite_membership import DpmCompositeMembershipRevision

    wire = propose(evaluation_api)
    parent = evaluation_api[1].get_membership_revision(
        tenant_id="synthetic-tenant",
        composite_id="synthetic-composite",
        definition_version="synthetic-definition",
        membership_revision=wire["parent_membership_revision"],
    )
    if fault == "unfinalized_source":
        wire["observations"]["source_generated_at"] = "2026-09-30T23:59:00.000000Z"
        product = next(
            item
            for item in wire["universe"]["source_products"]
            if item["product_name"] == "CompositeMonthlyEligibilityObservations"
        )
        product["content_hash"] = hash_canonical_payload(wire["observations"])
        expected = "COMPOSITE_ELIGIBILITY_PUBLICATION_SOURCE_NOT_FINALIZED"
    else:
        parent_wire = parent.model_dump(mode="json")
        parent_wire["decisions"][0]["effective_to"] = "2026-09-29"
        parent_wire["content_hash"] = ""
        parent = DpmCompositeMembershipRevision.model_validate(parent_wire)
        wire["parent_membership_content_hash"] = parent.content_hash
        wire["universe"]["membership_content_hash"] = parent.content_hash
        expected = "COMPOSITE_ELIGIBILITY_PUBLICATION_UNIVERSE_INCOMPLETE"
    wire["universe"]["content_hash"] = ""
    universe = DpmCompositeUniverseAttestation.model_validate(wire["universe"])
    wire["universe"] = universe.model_dump(mode="json")
    original = MonthlyEvaluationProposal.model_validate(propose(evaluation_api))
    wire["evaluation"] = evaluate_monthly_eligibility(
        original.policy_approval.proposal.policy,
        MonthlyEligibilityObservations.model_validate(wire["observations"]),
        evaluated_at=wire["proposed_at"],
        universe_content_hash=universe.content_hash,
    ).model_dump(mode="json")
    wire["content_hash"] = ""
    proposal = MonthlyEvaluationProposal.model_validate(wire)
    with pytest.raises(ValueError, match=expected):
        build_monthly_publication(
            proposal, parent, approved_by="synthetic-checker", approved_at=proposal.proposed_at
        )
    assert len(publications(evaluation_api)) == 1


def test_projected_universe_refuses_valid_revision_missing_one_business_day(evaluation_api):
    from src.core.composite_eligibility.publication import _published_universe
    from src.core.composite_membership import DpmCompositeMembershipRevision

    proposal = MonthlyEvaluationProposal.model_validate(propose(evaluation_api))
    parent = evaluation_api[1].get_membership_revision(
        tenant_id="synthetic-tenant",
        composite_id="synthetic-composite",
        definition_version="synthetic-definition",
        membership_revision=proposal.parent_membership_revision,
    )
    wire = parent.model_dump(mode="json")
    wire["decisions"][0]["effective_to"] = "2026-09-29"
    wire["content_hash"] = ""
    missing_day = DpmCompositeMembershipRevision.model_validate(wire)
    with pytest.raises(ValueError, match="COMPOSITE_ELIGIBILITY_PROJECTED_UNIVERSE_MISMATCH"):
        _published_universe(proposal, missing_day, "synthetic-checker", proposal.proposed_at)
    assert len(publications(evaluation_api)) == 1


def test_publication_refuses_hash_convention_change_that_creates_approval_cycle(
    evaluation_api, monkeypatch
):
    import src.core.composite_universe as universe_models
    from src.core.composite_eligibility.evaluation import evaluate_monthly_eligibility
    from src.core.composite_eligibility.publication import build_monthly_publication

    wire = propose(evaluation_api)
    original = MonthlyEvaluationProposal.model_validate(wire)
    parent = evaluation_api[1].get_membership_revision(
        tenant_id="synthetic-tenant",
        composite_id="synthetic-composite",
        definition_version="synthetic-definition",
        membership_revision=original.parent_membership_revision,
    )
    # Current hashing accepts the acyclic locator. Including nested approval hashes
    # would create a cycle; the publisher must reject that convention change.
    build_monthly_publication(
        original, parent, approved_by="synthetic-checker", approved_at=original.proposed_at
    )
    monkeypatch.setattr(
        universe_models,
        "composite_universe_attestation_hash",
        lambda value: hash_canonical_payload(
            value.model_dump(mode="json", exclude={"content_hash"})
        ),
    )
    wire["universe"]["content_hash"] = ""
    universe = DpmCompositeUniverseAttestation.model_validate(wire["universe"])
    wire["universe"] = universe.model_dump(mode="json")
    wire["evaluation"] = evaluate_monthly_eligibility(
        original.policy_approval.proposal.policy,
        original.observations,
        evaluated_at=original.proposed_at,
        universe_content_hash=universe.content_hash,
    ).model_dump(mode="json")
    wire["content_hash"] = ""
    valid_under_changed_convention = MonthlyEvaluationProposal.model_validate(wire)
    with pytest.raises(ValueError, match="COMPOSITE_ELIGIBILITY_PUBLICATION_LOCATOR_HASH_CYCLE"):
        build_monthly_publication(
            valid_under_changed_convention,
            parent,
            approved_by="synthetic-checker",
            approved_at=original.proposed_at,
        )
    assert len(publications(evaluation_api)) == 1


@pytest.mark.parametrize("stage", ["proposal", "approval"])
@pytest.mark.parametrize("winner", ["same", "different", "absent"])
def test_evaluation_conflict_reconciles_only_exact_retained_winner(
    evaluation_api, monkeypatch, stage, winner
):
    api = evaluation_api
    repository = api[1]
    proposal = propose(api) if stage == "approval" else None
    method = "save_monthly_evaluation_" + stage
    original = getattr(repository, method)

    def competing_save(**kwargs):
        material = kwargs[stage]
        if winner == "different":
            if stage == "approval":
                # A different valid checker publishes its own bound claims and membership.
                from src.core.composite_eligibility.publication import build_monthly_publication

                parent = repository.get_membership_revision(
                    tenant_id="synthetic-tenant",
                    composite_id="synthetic-composite",
                    definition_version="synthetic-definition",
                    membership_revision="synthetic-membership",
                )
                material = build_monthly_publication(
                    material.proposal,
                    parent,
                    approved_by="other-agent",
                    approved_at=material.approved_at,
                )[0]
            else:
                wire = material.model_dump(mode="json")
                wire.update(content_hash="", proposed_by="other-agent")
                material = MonthlyEvaluationProposal.model_validate(wire)
        if winner != "absent":
            original(**{stage: material})
        raise DpmCompositeConflictError(
            "COMPOSITE_ELIGIBILITY_EVALUATION_PROPOSAL_IMMUTABLE_CONFLICT"
        )

    monkeypatch.setattr(repository, method, competing_save)
    response = (
        approve(api, proposal)
        if stage == "approval"
        else api[0].put(URL, headers=HEADERS, json=api[5])
    )
    assert response.status_code == (200 if winner == "same" else 409), response.text
    assert len(publications(api)) == (2 if stage == "approval" and winner != "absent" else 1)
    assert len(api[6]) == 1
    if winner == "same":
        retained = api[0].get(URL + ("/approval" if stage == "approval" else ""), headers=HEADERS)
        assert response.json() == retained.json()


@pytest.mark.parametrize(
    "field,value,code",
    [
        ("month", "2026-08", "COMPOSITE_ELIGIBILITY_APPROVED_POLICY_NOT_FOUND"),
        (
            "policy_approval_content_hash",
            "sha256:" + "0" * 64,
            "COMPOSITE_ELIGIBILITY_APPROVED_POLICY_MISMATCH",
        ),
        ("parent_membership_revision", "missing", "COMPOSITE_ELIGIBILITY_STALE_MEMBERSHIP"),
        (
            "parent_membership_content_hash",
            "sha256:" + "0" * 64,
            "COMPOSITE_ELIGIBILITY_STALE_MEMBERSHIP",
        ),
    ],
)
def test_evaluation_missing_or_mismatched_parent_policy_refuses_without_source(
    evaluation_api, field, value, code
):
    api = evaluation_api
    response = api[0].put(URL, headers=HEADERS, json=api[5] | {field: value})
    expected_status = {
        "month": 404,
        "policy_approval_content_hash": 422,
        "parent_membership_revision": 409,
        "parent_membership_content_hash": 409,
    }
    assert response.status_code == expected_status[field], response.text
    assert response.json()["detail"]["code"] == code
    assert not api[6]
    assert len(publications(api)) == 1


@pytest.mark.parametrize(
    "field,value,code",
    [
        (
            "proposed_at",
            "2026-10-02T01:00:00.000000Z",
            "COMPOSITE_ELIGIBILITY_PROPOSAL_CLOCK_MISMATCH",
        ),
        (
            "target_membership_revision",
            "synthetic-membership",
            "COMPOSITE_ELIGIBILITY_TARGET_REVISION_REUSED",
        ),
        (
            "content_hash",
            "sha256:" + "0" * 64,
            "COMPOSITE_ELIGIBILITY_EVALUATION_PROPOSAL_CONTENT_MISMATCH",
        ),
        (
            "parent_membership_content_hash",
            "sha256:" + "0" * 64,
            "COMPOSITE_ELIGIBILITY_EVALUATION_UNIVERSE_BINDING_MISMATCH",
        ),
    ],
)
def test_evaluation_proposal_exact_binding_refuses_tampering(evaluation_api, field, value, code):
    wire = propose(evaluation_api)
    wire["content_hash"] = ""
    wire[field] = value
    with pytest.raises(ValidationError, match=code):
        MonthlyEvaluationProposal.model_validate(wire)
    assert len(publications(evaluation_api)) == 1


def test_recurring_proposal_source_custody_preserves_legacy_hash_and_binds_observations(
    evaluation_api,
):
    from src.core.composite_eligibility.source_assembly import (
        MonthlySourceAssembly,
        VerifiedMonthlySourceAssembly,
        assembly_verification_request,
    )
    from tests.composite_staged_eligibility_helpers import synthetic_verification
    from tests.composite_monthly_source_helpers import (
        assembly_material,
    )

    legacy = propose(evaluation_api)
    assert "source_assembly_evidence" not in legacy
    assert MonthlyEvaluationProposal.model_validate(legacy).model_dump(mode="json") == legacy
    _, material = assembly_material()
    assembly = MonthlySourceAssembly.model_validate(material)
    evidence = VerifiedMonthlySourceAssembly(
        assembly=assembly,
        verification=synthetic_verification(assembly_verification_request(assembly)),
    )
    retained = MonthlyEvaluationProposal.model_validate(
        {**legacy, "source_assembly_evidence": evidence.model_dump(mode="json"), "content_hash": ""}
    )
    assert retained.source_assembly_evidence == evidence
    assert retained.content_hash != legacy["content_hash"]
    assert MonthlyEvaluationProposal.model_validate(retained.model_dump(mode="json")) == retained
    material["observations"]["portfolios"][0]["funded"] = False
    material["compatibility_binding"]["digest"] = hash_canonical_payload(
        {"observations": material["observations"], "inputs": material["inputs"]}
    )
    changed = MonthlySourceAssembly.model_validate(material)
    changed_evidence = VerifiedMonthlySourceAssembly(
        assembly=changed,
        verification=synthetic_verification(assembly_verification_request(changed)),
    )
    wire = retained.model_dump(mode="json")
    wire["source_assembly_evidence"] = changed_evidence.model_dump(mode="json")
    wire["content_hash"] = ""
    with pytest.raises(ValidationError, match="COMPOSITE_SOURCE_ASSEMBLY_OBSERVATIONS_MISMATCH"):
        MonthlyEvaluationProposal.model_validate(wire)
    wire = retained.model_dump(mode="json")
    wire["source_assembly_evidence"]["verification"]["request"]["claims_digest"] = (
        "sha256:" + "f" * 64
    )
    wire["source_assembly_evidence"]["verification"]["content_hash"] = ""
    with pytest.raises(ValidationError, match="COMPOSITE_SOURCE_ASSEMBLY_VERIFICATION_MISMATCH"):
        MonthlyEvaluationProposal.model_validate(wire)


@pytest.mark.parametrize(
    "field,value,code",
    [
        ("approved_by", "synthetic-maker", "COMPOSITE_ELIGIBILITY_SELF_APPROVAL_FORBIDDEN"),
        (
            "approved_at",
            "2026-09-30T01:00:00.000000Z",
            "COMPOSITE_ELIGIBILITY_APPROVAL_BEFORE_PROPOSAL",
        ),
        (
            "claims_digest",
            "sha256:" + "0" * 64,
            "COMPOSITE_ELIGIBILITY_EVALUATION_APPROVAL_CLAIMS_MISMATCH",
        ),
        (
            "content_hash",
            "sha256:" + "0" * 64,
            "COMPOSITE_ELIGIBILITY_EVALUATION_APPROVAL_CONTENT_MISMATCH",
        ),
    ],
)
def test_evaluation_approval_checker_clock_claims_and_digest_are_bound(
    evaluation_api, field, value, code
):
    proposal = propose(evaluation_api)
    response = approve(evaluation_api, proposal)
    assert response.status_code == 200
    wire = response.json()
    wire["content_hash"] = ""
    wire[field] = value
    with pytest.raises(ValidationError, match=code):
        MonthlyEvaluationApproval.model_validate(wire)
    assert approve(evaluation_api, proposal).json() == response.json()
    assert len(publications(evaluation_api)) == 2


@pytest.mark.parametrize("lost", ["membership", "universe", "publication"])
def test_approval_read_refuses_missing_published_custody(evaluation_api, lost):
    api = evaluation_api
    proposal = propose(api)
    assert approve(api, proposal).status_code == 200
    repository = api[1]
    if lost == "membership":
        repository._membership_revisions.pop(
            (
                "synthetic-tenant",
                "synthetic-composite",
                "synthetic-definition",
                "synthetic-evaluated-membership",
            )
        )
    elif lost == "universe":
        repository._universe_attestations.pop(
            (
                "synthetic-tenant",
                "synthetic-composite",
                "synthetic-definition",
                "synthetic-evaluated-membership",
                "synthetic-evaluation-r1",
            )
        )
    else:
        repository._publications.pop(max(repository._publications))
    response = api[0].get(URL + "/approval", headers=HEADERS)
    assert response.status_code == 422, response.text
    assert (
        response.json()["detail"]["code"] == "COMPOSITE_ELIGIBILITY_APPROVED_PUBLICATION_MISMATCH"
    )


@pytest.fixture
def evaluation_api(request):
    snapshot = source_snapshot()
    alteration = getattr(request, "param", {})
    if alteration.get("missing_member"):
        snapshot.portfolios = []
    elif alteration:
        for field, value in alteration.items():
            if field == "wide_window":
                continue
            setattr(snapshot.portfolios[0], field, value)
    window = (
        {"coverage_from": "2026-08-01", "coverage_to": "2026-12-31"}
        if alteration.get("wide_window")
        else {}
    )
    repository, universe = retained_repository(snapshot, **window)
    state = {"now": "2026-08-20T01:00:00.000000Z", "owner": "synthetic-source"}
    resolutions = []

    class SyntheticSource:
        def resolve(self, request):
            resolutions.append(request)
            return MonthlyEligibilitySourceResolution(
                snapshot,
                owner_service=state["owner"],
                source_assembly_evidence=state.get("evidence"),
            )

    service = CompositeMonthlyEligibilityApplicationService(
        repository=repository,
        source=SyntheticSource(),
        clock=lambda: state["now"],
    )
    prior = app.dependency_overrides.copy()
    app.dependency_overrides[get_composite_monthly_eligibility_service] = lambda: service
    try:
        with TestClient(app) as client:
            policy_url = BASE + "/policies/2026-09/proposals/synthetic-config-r1"
            proposal = client.put(
                policy_url, json=prospective_proposal_body(universe), headers=HEADERS
            )
            assert proposal.status_code == 200, proposal.text
            approval = client.put(
                policy_url + "/approval",
                headers=CHECKER,
                json={"expected_proposal_content_hash": proposal.json()["content_hash"]},
            )
            assert approval.status_code == 200, approval.text
            parent = repository.get_membership_revision(
                tenant_id=snapshot.tenant_id,
                composite_id=snapshot.composite_id,
                definition_version=snapshot.definition_version,
                membership_revision="synthetic-membership",
            )
            body = {
                "month": "2026-09",
                "policy_approval_content_hash": approval.json()["content_hash"],
                "parent_membership_revision": parent.membership_revision,
                "parent_membership_content_hash": parent.content_hash,
                "attestation_version": universe.attestation_version,
                "universe_content_hash": universe.content_hash,
                "target_membership_revision": "synthetic-evaluated-membership",
                "correlation_id": "synthetic-evaluation",
            }
            state["now"] = "2026-10-01T01:00:00.000000Z"
            yield client, repository, snapshot, universe, state, body, resolutions
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(prior)


def propose(api):
    client, _, _, _, _, body, _ = api
    response = client.put(URL, headers=HEADERS, json=body)
    assert response.status_code == 200, response.text
    return response.json()


def approve(api, proposal, headers=CHECKER):
    return api[0].put(
        URL + "/approval",
        headers=headers,
        json={"expected_proposal_content_hash": proposal["content_hash"]},
    )


def publications(api):
    return (
        api[1].list_publications(tenant_id=HEADERS["X-Tenant-Id"], after_sequence=0, limit=10).items
    )


def test_approved_evaluation_publishes_exact_governed_identity_and_replays_without_source(
    evaluation_api,
):
    api = evaluation_api
    client, repository, _, _, state, _, resolutions = api
    original = publications(api)
    proposal = propose(api)
    assert publications(api) == original
    assert proposal["evaluation"]["included_count"] == 1
    assert [row["outcome"] for row in proposal["evaluation"]["portfolios"][0]["assessments"]] == [
        "PASS"
    ] * 3
    assert proposal["policy_approval"]["proposal"]["proposal_revision"] == "synthetic-config-r1"
    assert (
        proposal["policy_approval"]["proposal"]["eligibility_policy_version"] == "synthetic-policy"
    )
    assert approve(api, proposal, HEADERS).status_code == 422
    response = approve(api, proposal)
    assert response.status_code == 200, response.text
    approved = response.json()
    assert approved["official_activation"] == "UNAVAILABLE"
    assert len(publications(api)) == len(original) + 1
    membership = repository.get_membership_revision(
        tenant_id="synthetic-tenant",
        composite_id="synthetic-composite",
        definition_version="synthetic-definition",
        membership_revision="synthetic-evaluated-membership",
    )
    assert membership.content_hash == approved["membership_content_hash"]
    assert membership.policy_version == "synthetic-policy" != "synthetic-config-r1"
    assert membership.supersedes_membership_revision == "synthetic-membership"
    assert membership.decisions[0].approval_ref == approved["claims_digest"]
    assert membership.decisions[0].source_snapshot_id == proposal["evaluation"]["content_hash"]
    state["now"] = "2026-12-01T01:00:00.000000Z"
    state["owner"] = "unavailable-after-original-resolution"
    assert propose(api) == proposal
    assert approve(api, proposal).json() == approved
    assert client.get(URL, headers=HEADERS).json() == proposal
    assert client.get(URL + "/approval", headers=HEADERS).json() == approved
    assert len(resolutions) == 1
    assert len(publications(api)) == 2


def test_stale_hash_unauthorized_checker_and_foreign_scope_do_not_publish(evaluation_api):
    api = evaluation_api
    proposal = propose(api)
    client = api[0]
    stale = client.put(
        URL + "/approval",
        headers=CHECKER,
        json={"expected_proposal_content_hash": "sha256:" + "0" * 64},
    )
    assert stale.status_code == 409
    assert approve(api, proposal, CHECKER | {"X-Role": "DPM_PORTFOLIO_MANAGER"}).status_code == 403
    assert client.get(URL, headers=HEADERS | {"X-Tenant-Id": "foreign"}).status_code == 404
    assert len(publications(api)) == 1


@pytest.mark.parametrize(
    "field,value",
    [
        ("tenant_id", "foreign"),
        ("observations", {}),
        ("proposed_by", "forged"),
        ("evaluated_at", "2099-01-01T00:00:00.000000Z"),
    ],
)
def test_caller_cannot_supply_financial_or_custody_authority(evaluation_api, field, value):
    api = evaluation_api
    response = api[0].put(URL, headers=HEADERS, json=api[5] | {field: value})
    assert response.status_code == 422
    assert not api[6]
    assert len(publications(api)) == 1


def test_wrong_source_owner_refuses_before_retaining_evaluation(evaluation_api):
    api = evaluation_api
    api[4]["owner"] = "foreign-source"
    response = api[0].put(URL, headers=HEADERS, json=api[5])
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "COMPOSITE_ELIGIBILITY_SOURCE_OWNER_MISMATCH"
    assert api[0].get(URL, headers=HEADERS).status_code == 404
    assert len(publications(api)) == 1


def test_same_revision_cannot_rebind_target_or_maker(evaluation_api):
    api = evaluation_api
    propose(api)
    assert (
        api[0]
        .put(URL, headers=HEADERS, json=api[5] | {"target_membership_revision": "other"})
        .status_code
        == 409
    )
    assert api[0].put(URL, headers=CHECKER, json=api[5]).status_code == 409
    assert len(api[6]) == 1
    assert len(publications(api)) == 1


@pytest.mark.parametrize("material", ["observations", "evaluation", "policy_approval", "universe"])
def test_retained_proposal_revalidates_nested_material_before_custody(evaluation_api, material):
    proposal = propose(evaluation_api)
    proposal["content_hash"] = ""
    if material == "observations":
        proposal[material]["portfolios"][0]["settled_unencumbered_cash"] = "500"
    elif material == "evaluation":
        proposal[material]["portfolios"][0]["status"] = "EXCLUDED"
    elif material == "policy_approval":
        proposal[material]["proposal"]["attachments"][0]["digest"] = "sha256:" + "c" * 64
    else:
        proposal[material]["coverage_to"] = "2026-09-29"
    with pytest.raises(ValidationError):
        MonthlyEvaluationProposal.model_validate(proposal)
    assert len(publications(evaluation_api)) == 1


def test_competing_evaluations_cannot_both_publish_one_month(evaluation_api):
    api = evaluation_api
    first = propose(api)
    other_url = BASE + "/evaluations/synthetic-evaluation-r2"
    other = api[0].put(
        other_url, headers=HEADERS, json=api[5] | {"target_membership_revision": "other-membership"}
    )
    assert other.status_code == 200, other.text
    assert approve(api, first).status_code == 200
    conflict = api[0].put(
        other_url + "/approval",
        headers=CHECKER,
        json={"expected_proposal_content_hash": other.json()["content_hash"]},
    )
    assert conflict.status_code == 409, conflict.text
    assert len(publications(api)) == 2


@pytest.mark.parametrize(
    "evaluation_api,status,approval_status,code",
    [
        (
            {"missing_member": True},
            "PENDING_REVIEW",
            422,
            "COMPOSITE_ELIGIBILITY_PUBLICATION_UNIVERSE_INCOMPLETE",
        ),
        (
            {"discretionary": None},
            "PENDING_REVIEW",
            503,
            "COMPOSITE_ELIGIBILITY_DISCRETIONARY_FACT_UNAVAILABLE",
        ),
        ({"prior_month_end_assets": None}, "PENDING_REVIEW", 200, None),
        (
            {"settled_unencumbered_cash": "51", "funded": False, "invested": None},
            "EXCLUDED",
            200,
            None,
        ),
    ],
    indirect=["evaluation_api"],
)
def test_missing_facts_are_not_zero_or_business_exclusion(
    evaluation_api, status, approval_status, code
):
    api = evaluation_api
    proposal = propose(api)
    result = proposal["evaluation"]["portfolios"][0]
    assert result["status"] == status
    assert len(result["assessments"]) == 3
    response = approve(api, proposal)
    assert response.status_code == approval_status, response.text
    if code:
        assert response.json()["detail"]["code"] == code
        assert len(publications(api)) == 1
        assert api[0].get(URL + "/approval", headers=HEADERS).status_code == 404
    else:
        assert len(publications(api)) == 2
        retained = api[1].get_membership_revision(
            tenant_id="synthetic-tenant",
            composite_id="synthetic-composite",
            definition_version="synthetic-definition",
            membership_revision="synthetic-evaluated-membership",
        )
        assert retained.decisions[0].status == status
        assert retained.decisions[0].discretionary is True
    if status == "EXCLUDED":
        assert result["assessments"][1]["failure_reasons"]
        assert result["assessments"][2]["failure_reasons"]
        assert result["assessments"][2]["unknown_reasons"]


@pytest.mark.parametrize(
    "evaluation_api", [{"wide_window": True, "settled_unencumbered_cash": "51"}], indirect=True
)
def test_monthly_exclusion_preserves_history_and_reentry_rechecks_remaining_rules(evaluation_api):
    api = evaluation_api
    client, repository, snapshot, universe, state, body, _ = api
    # Three policies approved before any assessed month. Source population is explicitly synthetic.
    state["now"] = "2026-08-20T01:00:00.000000Z"
    policy_hashes = {}
    for month in ("2026-10", "2026-11"):
        policy_url = BASE + f"/policies/{month}/proposals/synthetic-config-r1"
        policy = client.put(policy_url, headers=HEADERS, json=prospective_proposal_body(universe))
        assert policy.status_code == 200, policy.text
        approved = client.put(
            policy_url + "/approval",
            headers=CHECKER,
            json={"expected_proposal_content_hash": policy.json()["content_hash"]},
        )
        assert approved.status_code == 200, approved.text
        policy_hashes[month] = approved.json()["content_hash"]
    state["now"] = "2026-10-01T01:00:00.000000Z"
    original = repository.get_membership_revision(
        tenant_id="synthetic-tenant",
        composite_id="synthetic-composite",
        definition_version="synthetic-definition",
        membership_revision="synthetic-membership",
    )
    first = propose(api)
    assert first["evaluation"]["portfolios"][0]["status"] == "EXCLUDED"
    assert approve(api, first).status_code == 200
    parent_id = body["target_membership_revision"]
    for month, prior_date, last, generated, funded, expected in (
        ("2026-10", "2026-09-30", "2026-10-31", "2026-11-01T00:00:00.000000Z", False, "EXCLUDED"),
        ("2026-11", "2026-10-31", "2026-11-30", "2026-12-01T00:00:00.000000Z", True, "INCLUDED"),
    ):
        parent = repository.get_membership_revision(
            tenant_id="synthetic-tenant",
            composite_id="synthetic-composite",
            definition_version="synthetic-definition",
            membership_revision=parent_id,
        )
        snapshot.month = month
        snapshot.source_cut_id = "synthetic-cut-" + month
        snapshot.source_revision = "synthetic-source-" + month
        snapshot.source_generated_at = generated
        facts = snapshot.portfolios[0]
        facts.prior_assets_as_of = prior_date
        facts.cash_as_of = facts.readiness_as_of = facts.flow_coverage_to = last
        facts.flow_coverage_from = month + "-01"
        facts.settled_unencumbered_cash = "0"
        facts.funded = funded
        facts.flows = []
        wire = universe.model_dump(mode="json", exclude={"content_hash"})
        wire.update(
            membership_revision=parent.membership_revision,
            membership_content_hash=parent.content_hash,
            attestation_version="synthetic-universe-" + month,
            coverage_from=month + "-01",
            coverage_to=last,
        )
        product = wire["source_products"][1]
        product.update(
            source_cut_id=snapshot.source_cut_id,
            source_watermark=snapshot.source_revision,
            content_hash=hash_canonical_payload(snapshot.model_dump(mode="json")),
        )
        pinned = DpmCompositeUniverseAttestation.model_validate(wire)
        repository.save_universe_attestation(attestation=pinned)
        state["now"] = generated
        target = "synthetic-membership-" + month
        request = body | {
            "month": month,
            "policy_approval_content_hash": policy_hashes[month],
            "parent_membership_revision": parent.membership_revision,
            "parent_membership_content_hash": parent.content_hash,
            "attestation_version": pinned.attestation_version,
            "universe_content_hash": pinned.content_hash,
            "target_membership_revision": target,
        }
        url = BASE + "/evaluations/synthetic-evaluation-" + month
        proposal = client.put(url, headers=HEADERS, json=request)
        assert proposal.status_code == 200, proposal.text
        result = proposal.json()["evaluation"]["portfolios"][0]
        assert result["status"] == expected
        assert result["assessments"][1]["outcome"] == "PASS"
        assert result["assessments"][2]["outcome"] == ("PASS" if funded else "FAIL")
        approved = client.put(
            url + "/approval",
            headers=CHECKER,
            json={"expected_proposal_content_hash": proposal.json()["content_hash"]},
        )
        assert approved.status_code == 200, approved.text
        parent_id = target
    final = repository.get_membership_revision(
        tenant_id="synthetic-tenant",
        composite_id="synthetic-composite",
        definition_version="synthetic-definition",
        membership_revision=parent_id,
    )
    assert [(item.effective_from, item.effective_to, item.status) for item in final.decisions] == [
        ("2026-08-01", "2026-08-31", "INCLUDED"),
        ("2026-09-01", "2026-09-30", "EXCLUDED"),
        ("2026-10-01", "2026-10-31", "EXCLUDED"),
        ("2026-11-01", "2026-11-30", "INCLUDED"),
        ("2026-12-01", "2026-12-31", "INCLUDED"),
    ]
    assert (
        repository.get_membership_revision(
            tenant_id="synthetic-tenant",
            composite_id="synthetic-composite",
            definition_version="synthetic-definition",
            membership_revision="synthetic-membership",
        )
        == original
    )
