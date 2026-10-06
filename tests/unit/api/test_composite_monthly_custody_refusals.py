"""Behavioral custody fault checks; adapter doubles are not PostgreSQL durability proof."""

import pytest
from src.core.composite_eligibility.evaluation_control import (
    MonthlyEvaluationProposal,
    evaluation_key,
)
from src.core.composite_eligibility.publication import build_monthly_publication
from src.core.composite_repository import DpmCompositeConflictError
from src.infrastructure.composites import evaluation_control
from tests.unit.api.test_composite_monthly_evaluation_routes import (
    evaluation_api as evaluation_api,
    propose,
    approve,
    publications,
)


@pytest.mark.parametrize("mode", ["default", "durable", "unavailable"])
def test_composite_provider_preserves_explicit_persistence_and_failure(monkeypatch, mode):
    from src.api import dependencies
    from src.infrastructure.composites.in_memory import InMemoryDpmCompositeRepository

    monkeypatch.delenv("DPM_MANAGE_POSTGRES_DSN", raising=False)
    monkeypatch.delenv("DPM_SUPPORTABILITY_POSTGRES_DSN", raising=False)
    monkeypatch.delenv("DPM_COMPOSITE_POSTGRES_DSN", raising=False)
    monkeypatch.setattr(dependencies, "_POSTGRES_COMPOSITE_REPOSITORY", None)
    retained = InMemoryDpmCompositeRepository()
    calls = []

    def factory(*, dsn):
        calls.append(dsn)
        if mode == "unavailable":
            raise RuntimeError("DPM_COMPOSITE_POSTGRES_DRIVER_MISSING")
        return retained

    monkeypatch.setattr(dependencies, "PostgresDpmCompositeRepository", factory)
    if mode == "default":
        assert dependencies.get_composite_repository() is dependencies._COMPOSITE_REPOSITORY
        assert not calls
    else:
        monkeypatch.setenv("DPM_COMPOSITE_POSTGRES_DSN", "postgresql://explicit-custody")
        if mode == "unavailable":
            with pytest.raises(RuntimeError, match="DPM_COMPOSITE_POSTGRES_DRIVER_MISSING"):
                dependencies.get_composite_repository()
            assert dependencies._POSTGRES_COMPOSITE_REPOSITORY is None
        else:
            assert dependencies.get_composite_repository() is retained
            assert dependencies.get_composite_repository() is retained
        assert calls == ["postgresql://explicit-custody"]


def test_retained_approval_cannot_be_replaced_by_another_checker(evaluation_api):
    api = evaluation_api
    approval, _, _ = material(api)
    repository = api[1]
    repository.save_monthly_evaluation_approval(approval=approval)
    parent = repository.get_membership_revision(
        tenant_id="synthetic-tenant",
        composite_id="synthetic-composite",
        definition_version="synthetic-definition",
        membership_revision="synthetic-membership",
    )
    alternative = build_monthly_publication(
        approval.proposal, parent, approved_by="other-checker", approved_at=approval.approved_at
    )[0]
    with pytest.raises(
        DpmCompositeConflictError, match="COMPOSITE_ELIGIBILITY_ACTIVE_EVALUATION_CONFLICT"
    ):
        repository.save_monthly_evaluation_approval(approval=alternative)
    repository.save_monthly_evaluation_approval(approval=approval)
    assert len(publications(api)) == 2


@pytest.mark.parametrize(
    "lost,code",
    [
        ("definition", "COMPOSITE_DEFINITION_NOT_FOUND"),
        ("parent", "COMPOSITE_ELIGIBILITY_STALE_MEMBERSHIP"),
    ],
)
def test_evaluation_application_requires_definition_and_parent_at_each_boundary(
    evaluation_api, lost, code
):
    from tests.composite_monthly_eligibility_helpers import HEADERS
    from tests.unit.api.test_composite_monthly_evaluation_routes import URL

    api = evaluation_api
    if lost == "parent":
        proposal = propose(api)
        api[1]._membership_revisions.clear()
        response = approve(api, proposal)
    else:
        api[1]._definitions.clear()
        response = api[0].put(URL, headers=HEADERS, json=api[5])
    assert response.status_code == (409 if lost == "parent" else 404), response.text
    assert response.json()["detail"]["code"] == code
    assert len(api[1]._publications) == 1
    if lost == "parent":
        with pytest.raises(
            DpmCompositeConflictError, match="COMPOSITE_PUBLICATION_INTEGRITY_CONFLICT"
        ):
            publications(api)
    else:
        assert len(publications(api)) == 1


@pytest.mark.parametrize(
    "change,code",
    [
        ("window", "COMPOSITE_ELIGIBILITY_UNIVERSE_WINDOW_INCOMPLETE"),
        ("reference", "COMPOSITE_ELIGIBILITY_SOURCE_REFERENCE_UNAVAILABLE"),
        ("recomputed_policy", "COMPOSITE_ELIGIBILITY_EVALUATION_RECOMPUTATION_MISMATCH"),
    ],
)
def test_proposal_requires_complete_window_reference_and_reproducible_policy(
    evaluation_api, change, code
):
    from pydantic import ValidationError
    from src.core.composite_universe import DpmCompositeUniverseAttestation
    from src.core.composite_eligibility.policy import resolve_monthly_policy
    from src.core.composite_eligibility.evaluation import evaluate_monthly_eligibility

    proposal = MonthlyEvaluationProposal.model_validate(propose(evaluation_api))
    wire = proposal.model_dump(mode="json")
    wire["content_hash"] = ""
    if change == "recomputed_policy":
        policy = proposal.policy_approval.proposal.policy
        layers = [item.model_copy(update={"cash_threshold": "0.04"}) for item in policy.layers]
        alternative = resolve_monthly_policy(layers, month=policy.month, scope=policy.scope)
        wire["evaluation"] = evaluate_monthly_eligibility(
            alternative,
            proposal.observations,
            evaluated_at=proposal.proposed_at,
            universe_content_hash=proposal.universe.content_hash,
        ).model_dump(mode="json")
    else:
        universe = wire["universe"]
        universe["content_hash"] = ""
        if change == "window":
            universe["coverage_from"] = "2026-09-02"
        else:
            universe["source_products"] = [
                item
                for item in universe["source_products"]
                if item["authority_scope"] != "POLICY_INPUT"
            ]
        wire["universe"] = DpmCompositeUniverseAttestation.model_validate(universe).model_dump(
            mode="json"
        )
    with pytest.raises(ValidationError, match=code):
        MonthlyEvaluationProposal.model_validate(wire)
    assert len(publications(evaluation_api)) == 1


def test_projection_rejects_a_different_parent_content(evaluation_api):
    from src.core.composite_membership import DpmCompositeMembershipRevision

    approval, _, _ = material(evaluation_api)
    parent = evaluation_api[1].get_membership_revision(
        tenant_id="synthetic-tenant",
        composite_id="synthetic-composite",
        definition_version="synthetic-definition",
        membership_revision="synthetic-membership",
    )
    wire = parent.model_dump(mode="json")
    wire.update(content_hash="", correlation_id="different-parent-content")
    different = DpmCompositeMembershipRevision.model_validate(wire)
    with pytest.raises(ValueError, match="COMPOSITE_ELIGIBILITY_STALE_MEMBERSHIP"):
        build_monthly_publication(
            approval.proposal,
            different,
            approved_by=approval.approved_by,
            approved_at=approval.approved_at,
        )
    assert len(publications(evaluation_api)) == 1


@pytest.mark.parametrize("evaluation_api", [{"missing_member": True}], indirect=True)
def test_incomplete_month_cannot_be_projected_into_membership(evaluation_api):

    proposal = propose(evaluation_api)
    response = approve(evaluation_api, proposal)
    assert response.status_code == 422, response.text
    assert (
        response.json()["detail"]["code"] == "COMPOSITE_ELIGIBILITY_PUBLICATION_UNIVERSE_INCOMPLETE"
    )
    assert len(publications(evaluation_api)) == 1


def material(api):
    proposal = MonthlyEvaluationProposal.model_validate(propose(api))
    parent = api[1].get_membership_revision(
        tenant_id="synthetic-tenant",
        composite_id="synthetic-composite",
        definition_version="synthetic-definition",
        membership_revision="synthetic-membership",
    )
    return build_monthly_publication(
        proposal, parent, approved_by="synthetic-checker", approved_at=api[4]["now"]
    )


@pytest.mark.parametrize(
    "lost,code",
    [
        ("policy", "COMPOSITE_ELIGIBILITY_APPROVED_POLICY_MISMATCH"),
        ("universe", "COMPOSITE_ELIGIBILITY_RETAINED_UNIVERSE_MISMATCH"),
        ("publication", "COMPOSITE_ELIGIBILITY_STALE_MEMBERSHIP"),
        ("proposal", "COMPOSITE_ELIGIBILITY_EVALUATION_APPROVAL_PROPOSAL_MISMATCH"),
    ],
)
def test_memory_approval_requires_retained_inputs_and_parent(evaluation_api, lost, code):
    api = evaluation_api
    approval, _, _ = material(api)
    repository = api[1]
    collection = {
        "policy": repository._monthly_approvals,
        "universe": repository._universe_attestations,
        "publication": repository._publications,
        "proposal": repository._monthly_evaluations,
    }[lost]
    collection.clear()
    with pytest.raises(DpmCompositeConflictError, match=code):
        repository.save_monthly_evaluation_approval(approval=approval)
    assert not repository._monthly_evaluation_approvals
    assert (
        "synthetic-tenant",
        "synthetic-composite",
        "synthetic-definition",
        "synthetic-evaluated-membership",
    ) not in repository._membership_revisions


@pytest.mark.parametrize(
    "change,code",
    [
        ("approval_hash", "COMPOSITE_ELIGIBILITY_APPROVED_PUBLICATION_MISMATCH"),
        ("existing_target", "COMPOSITE_ELIGIBILITY_TARGET_REVISION_EXISTS"),
    ],
)
def test_memory_publication_refuses_noncanonical_material_or_existing_target(
    evaluation_api, change, code
):
    api = evaluation_api
    approval, revision, _ = material(api)
    repository = api[1]
    if change == "approval_hash":
        wire = approval.model_dump(mode="json")
        wire.update(content_hash="", membership_content_hash="sha256:" + "0" * 64)
        approval = type(approval).model_validate(wire)
    else:
        repository._membership_revisions[
            (
                "synthetic-tenant",
                "synthetic-composite",
                "synthetic-definition",
                revision.membership_revision,
            )
        ] = revision
    with pytest.raises(DpmCompositeConflictError, match=code):
        repository.save_monthly_evaluation_approval(approval=approval)
    assert len(publications(api)) == 1
    assert not repository._monthly_evaluation_approvals


class StoredRows:
    def __init__(self, *rows):
        self.rows = list(rows)
        self.statements = []

    def execute(self, statement, parameters):
        self.statements.append((statement, parameters))
        return self

    def fetchone(self):
        assert self.rows, "Unexpected storage read"
        return self.rows.pop(0)


@pytest.mark.parametrize("lost", ["definition", "policy_identity", "proposal"])
def test_policy_custody_refuses_missing_definition_or_unapproved_material(evaluation_api, lost):
    api = evaluation_api
    approval = material(api)[0].proposal.policy_approval
    repository = api[1]
    if lost == "proposal":
        repository._monthly_proposals.clear()

        def operation():
            repository.save_monthly_policy_approval(approval=approval)

        code = "COMPOSITE_ELIGIBILITY_APPROVAL_PROPOSAL_MISMATCH"
    else:
        proposal = approval.proposal
        if lost == "definition":
            repository._definitions.clear()
            code = "COMPOSITE_DEFINITION_NOT_FOUND"
        else:
            wire = proposal.model_dump(mode="json")
            wire.update(content_hash="", eligibility_policy_version="unowned-policy")
            proposal = type(proposal).model_validate(wire)
            code = "COMPOSITE_ELIGIBILITY_DEFINITION_POLICY_MISMATCH"

        def operation():
            repository.save_monthly_policy_proposal(proposal=proposal)

    with pytest.raises(ValueError, match=code):
        operation()
    assert len(publications(api)) == 1


@pytest.mark.parametrize("changed", ["expected_portfolio_ids", "source_revision"])
def test_evaluation_proposal_cannot_substitute_universe_or_source_reference(
    evaluation_api, changed
):
    from pydantic import ValidationError
    from src.core.composite_universe import DpmCompositeUniverseAttestation

    wire = propose(evaluation_api)
    universe = wire["universe"]
    universe["content_hash"] = ""
    if changed == "expected_portfolio_ids":
        universe[changed] = ["other-member"]
        code = "COMPOSITE_ELIGIBILITY_SOURCE_UNIVERSE_MISMATCH"
    else:
        for product in universe["source_products"]:
            if product["authority_scope"] == "POLICY_INPUT":
                product["source_watermark"] = "other-revision"
        code = "COMPOSITE_ELIGIBILITY_EVALUATION_SOURCE_BINDING_MISMATCH"
    wire["universe"] = DpmCompositeUniverseAttestation.model_validate(universe).model_dump(
        mode="json"
    )
    wire["content_hash"] = ""
    with pytest.raises(ValidationError, match=code):
        MonthlyEvaluationProposal.model_validate(wire)
    assert len(publications(evaluation_api)) == 1


@pytest.mark.parametrize("stage", ["proposal", "approval"])
@pytest.mark.parametrize("corruption", ["hash", "key"])
def test_postgres_decoder_refuses_hash_or_scope_corruption(evaluation_api, stage, corruption):
    proposal = propose(evaluation_api)
    wire = proposal if stage == "proposal" else approve(evaluation_api, proposal).json()
    key = evaluation_key(MonthlyEvaluationProposal.model_validate(proposal))
    if corruption == "key":
        key = ("foreign-tenant", *key[1:])
    row = {
        "payload_json": wire,
        "content_hash": "sha256:" + "0" * 64 if corruption == "hash" else wire["content_hash"],
    }
    connection = StoredRows(row)
    with pytest.raises(
        DpmCompositeConflictError,
        match=f"COMPOSITE_ELIGIBILITY_EVALUATION_{stage.upper()}_INTEGRITY_CONFLICT",
    ):
        getattr(evaluation_control, "get_" + stage)(connection, key)
    assert len(connection.statements) == 1
    assert connection.statements[0][0].lstrip().startswith("SELECT")


@pytest.mark.parametrize(
    "lost,code",
    [
        ("policy", "COMPOSITE_ELIGIBILITY_APPROVED_POLICY_MISMATCH"),
        ("universe", "COMPOSITE_ELIGIBILITY_RETAINED_UNIVERSE_MISMATCH"),
        ("parent", "COMPOSITE_ELIGIBILITY_STALE_MEMBERSHIP"),
    ],
)
def test_postgres_proposal_refuses_missing_immutable_inputs_before_insert(
    evaluation_api, lost, code
):
    proposal = MonthlyEvaluationProposal.model_validate(propose(evaluation_api))
    policy = proposal.policy_approval
    rows = (
        [None]
        if lost == "policy"
        else [
            {
                "content_hash": policy.content_hash,
                "proposal_content_hash": policy.proposal.content_hash,
                "payload_json": policy.model_dump(mode="json"),
            }
        ]
    )
    if lost != "policy":
        rows.append(
            None
            if lost == "universe"
            else {
                "content_hash": proposal.universe.content_hash,
                "payload_json": proposal.universe.model_dump(mode="json"),
            }
        )
    if lost == "parent":
        rows.append(None)
    connection = StoredRows(*rows)
    with pytest.raises(DpmCompositeConflictError, match=code):
        evaluation_control.save_proposal(connection, proposal)
    assert not any("INSERT INTO" in statement for statement, _ in connection.statements)
    assert not connection.rows
