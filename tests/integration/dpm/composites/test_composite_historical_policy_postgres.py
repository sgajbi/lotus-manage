"""Historical admission shares the owning PostgreSQL transaction and authority chain."""

from concurrent.futures import ThreadPoolExecutor
import json

import psycopg
from psycopg.rows import dict_row
import pytest

from src.infrastructure.composites import universe_store
from src.infrastructure.composites.postgres import PostgresDpmCompositeRepository
from tests.composite_historical_policy_helpers import historical_approval_for, seed_historical_root
from tests.composite_monthly_amendment_helpers import corrected_monthly_proposal
from tests.integration.dpm.composites.test_composite_staged_upgrade_postgres import payload_rows
from tests.integration.dpm.network_runtime import disposable_database


def retained_state(dsn):
    with psycopg.connect(dsn, row_factory=dict_row) as connection:
        return payload_rows(connection)


@pytest.fixture(params=["v1", "v2"])
def historical(request):
    with disposable_database() as dsn:
        repository = PostgresDpmCompositeRepository(dsn=dsn)
        port, scope, receipt, parent = seed_historical_root(
            repository, definition_product_version=request.param
        )
        yield dsn, repository, port, scope, receipt, parent


def test_two_corrections_reopen_exact_original_and_each_successor(historical):
    dsn, repository, port, scope, original, parent = historical
    receipts = [original]
    for revision, cash in ((2, "100"), (3, "50")):
        prior = receipts[-1]
        proposal = corrected_monthly_proposal(
            prior,
            parent,
            sequence=prior.publication_sequence,
            historical_verifier=port,
            revision=revision,
            cash=cash,
        )
        repository.save_universe_attestation(attestation=proposal.universe)
        repository.save_monthly_evaluation_proposal(proposal=proposal)
        approval, parent, _ = historical_approval_for(proposal, parent, port)
        repository.save_monthly_evaluation_approval(approval=approval)
        receipts.append(
            repository.resolve_monthly_eligibility_evidence(
                **scope,
                evaluation_revision=proposal.evaluation_revision,
                approval_content_hash=approval.content_hash,
            )
        )
    before = retained_state(dsn)
    port.available = False
    fresh = PostgresDpmCompositeRepository(dsn=dsn)
    for receipt in receipts:
        assert (
            fresh.resolve_monthly_eligibility_evidence(
                **scope,
                evaluation_revision=receipt.approval.proposal.evaluation_revision,
                approval_content_hash=receipt.approval.content_hash,
            )
            == receipt
        )
        fresh.save_monthly_evaluation_approval(approval=receipt.approval)
        assert (
            receipt.approval.proposal.policy_approval == original.approval.proposal.policy_approval
        )
    assert retained_state(dsn) == before
    assert [item.product_version for item in receipts] == ["v3", "v4", "v4"]
    assert [item.approval.proposal.evaluation.included_count for item in receipts] == [1, 0, 1]
    assert len(before["dpm_composite_membership_publications"]) == 4


def test_historical_corrections_compete_for_same_atomic_authority(historical):
    dsn, repository, port, _, original, parent = historical
    proposals = [
        corrected_monthly_proposal(
            original,
            parent,
            sequence=original.publication_sequence,
            historical_verifier=port,
            revision=revision,
            cash=cash,
        )
        for revision, cash in ((2, "100"), (3, "200"))
    ]
    for proposal in proposals:
        repository.save_universe_attestation(attestation=proposal.universe)
        repository.save_monthly_evaluation_proposal(proposal=proposal)
    approvals = [historical_approval_for(item, parent, port)[0] for item in proposals]

    def compete(approval):
        try:
            PostgresDpmCompositeRepository(dsn=dsn).save_monthly_evaluation_approval(
                approval=approval
            )
            return approval
        except ValueError as error:
            assert "STALE_AUTHORITY" in str(error)
            return None

    with ThreadPoolExecutor(max_workers=2) as workers:
        results = list(workers.map(compete, approvals))
    assert sum(item is not None for item in results) == 1
    state = retained_state(dsn)
    assert len(state["dpm_composite_monthly_evaluation_approvals"]) == 2
    assert len(state["dpm_composite_membership_publications"]) == 3


def test_historical_approval_failure_rolls_back_canonical_projection(historical, monkeypatch):
    dsn, repository, port, _, original, parent = historical
    proposal = corrected_monthly_proposal(
        original,
        parent,
        sequence=original.publication_sequence,
        historical_verifier=port,
    )
    repository.save_universe_attestation(attestation=proposal.universe)
    repository.save_monthly_evaluation_proposal(proposal=proposal)
    approval = historical_approval_for(proposal, parent, port)[0]
    before = retained_state(dsn)
    store = universe_store.store_universe_attestation

    def fail_after_store(**kwargs):
        store(**kwargs)
        raise RuntimeError("injected-after-historical-canonical-write")

    with monkeypatch.context() as failing:
        failing.setattr(universe_store, "store_universe_attestation", fail_after_store)
        with pytest.raises(RuntimeError, match="injected-after-historical"):
            repository.save_monthly_evaluation_approval(approval=approval)
    assert retained_state(dsn) == before
    repository.save_monthly_evaluation_approval(approval=approval)


@pytest.mark.parametrize(
    "mutation", ["null", "downgrade", "staged", "policy", "lineage", "operation"]
)
def test_database_refuses_historical_wire_mutations(historical, mutation):
    dsn, repository, port, _, original, parent = historical
    proposal = corrected_monthly_proposal(
        original,
        parent,
        sequence=original.publication_sequence,
        historical_verifier=port,
    )
    repository.save_universe_attestation(attestation=proposal.universe)
    repository.save_monthly_evaluation_proposal(proposal=proposal)
    wire = proposal.model_dump(mode="json")
    subject_revision = None
    subject_content_hash = None
    staged_policy_content_hash = None
    parent_membership_revision = proposal.parent_membership_revision
    if mutation == "null":
        wire["operation_verification"] = None
    elif mutation == "downgrade":
        wire["product_version"] = "v2"
    elif mutation == "staged":
        # custody_mode is generated from these selectors; never update it directly.
        subject_revision = "controlled-staged-selector"
        subject_content_hash = original.content_hash
        staged_policy_content_hash = proposal.policy_approval.content_hash
        parent_membership_revision = None
    elif mutation == "policy":
        wire["policy_approval"]["product_version"] = "v1"
    elif mutation == "operation":
        wire["operation_verification"]["request"]["operation"] = "POLICY_PROPOSAL"
    else:
        wire["amendment"]["original_approval_binding"]["product_version"] = "v1"
    before = retained_state(dsn)
    with pytest.raises(psycopg.errors.CheckViolation) as failure:
        with psycopg.connect(dsn) as connection:
            connection.execute(
                "UPDATE dpm_composite_monthly_evaluation_proposals "
                "SET payload_json=%s::jsonb, subject_revision=%s, subject_content_hash=%s, "
                "staged_policy_content_hash=%s, parent_membership_revision=%s "
                "WHERE evaluation_revision=%s",
                (
                    json.dumps(wire),
                    subject_revision,
                    subject_content_hash,
                    staged_policy_content_hash,
                    parent_membership_revision,
                    proposal.evaluation_revision,
                ),
            )
    assert failure.value.diag.constraint_name == "monthly_evaluation_amendment_wire"
    assert retained_state(dsn) == before


@pytest.mark.parametrize("family", ["policy_proposals", "policy_approvals", "evaluation_approvals"])
@pytest.mark.parametrize("mutation", ["null", "operation", "version"])
def test_database_policy_and_approval_guards_refuse_invalid_inputs(historical, family, mutation):
    dsn, _, _, _, original, _ = historical
    products = {
        "policy_proposals": original.approval.proposal.policy_approval.proposal,
        "policy_approvals": original.approval.proposal.policy_approval,
        "evaluation_approvals": original.approval,
    }
    constraints = {
        "policy_proposals": "monthly_policy_historical_wire",
        "policy_approvals": "monthly_policy_historical_approval_wire",
        "evaluation_approvals": "monthly_evaluation_approval_amendment_wire",
    }
    wire = products[family].model_dump(mode="json")
    proof = "operation_verification" if family == "evaluation_approvals" else "verification"
    if mutation == "null":
        wire[proof] = None
    elif mutation == "operation":
        wire[proof]["request"]["operation"] = "EVALUATION_PROPOSAL"
    else:
        wire["product_version"] = "v99"
    before = retained_state(dsn)
    # Table identifiers are a closed test-owned set; values remain bound parameters.
    from psycopg import sql

    with pytest.raises(psycopg.errors.CheckViolation) as failure:
        with psycopg.connect(dsn) as connection:
            connection.execute(
                sql.SQL("UPDATE {} SET payload_json=%s::jsonb").format(
                    sql.Identifier("dpm_composite_monthly_" + family)
                ),
                (json.dumps(wire),),
            )
    assert failure.value.diag.constraint_name == constraints[family]
    assert retained_state(dsn) == before


@pytest.mark.parametrize("family", ["proposals", "approvals"])
@pytest.mark.parametrize(
    "mutation", ["frozen_v1", "missing_operation", "policy_v1", "original_policy_v1"]
)
def test_database_refuses_historical_root_wire_version_mismatch(historical, family, mutation):
    dsn, _, _, _, original, _ = historical
    product = original.approval.proposal if family == "proposals" else original.approval
    wire = product.model_dump(mode="json")
    proposal = wire if family == "proposals" else wire["proposal"]
    if mutation == "frozen_v1":
        wire["product_version"] = "v1"
        wire.pop("operation_verification")
        if family == "approvals":
            proposal["product_version"] = "v1"
            proposal.pop("operation_verification")
    elif mutation == "missing_operation":
        wire.pop("operation_verification")
    elif mutation == "policy_v1":
        proposal["policy_approval"]["product_version"] = "v1"
    else:
        proposal["policy_approval"]["proposal"]["product_version"] = "v1"
    before = retained_state(dsn)
    from psycopg import sql

    with pytest.raises(psycopg.errors.CheckViolation) as failure:
        with psycopg.connect(dsn) as connection:
            connection.execute(
                sql.SQL("UPDATE {} SET payload_json=%s::jsonb").format(
                    sql.Identifier("dpm_composite_monthly_evaluation_" + family)
                ),
                (json.dumps(wire),),
            )
    constraint = (
        "monthly_evaluation_amendment_wire"
        if family == "proposals"
        else "monthly_evaluation_approval_amendment_wire"
    )
    assert failure.value.diag.constraint_name == constraint
    assert retained_state(dsn) == before
