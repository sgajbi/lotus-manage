"""Registered custody/publication proof using explicitly unqualified synthetic inputs."""

import pytest
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
    from tests.unit.dpm.infrastructure.test_composite_monthly_source_assembly import (
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
            return MonthlyEligibilitySourceResolution(snapshot, owner_service=state["owner"])

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
