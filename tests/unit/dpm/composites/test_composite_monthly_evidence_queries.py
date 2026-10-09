"""Scoped immutable read guards; native tests separately prove real SQL custody."""

import json
from pathlib import Path

import pytest

from src.core.composite_eligibility.evaluation_control import MonthlyEvaluationApproval
from src.core.composite_repository import DpmCompositeConflictError
from src.infrastructure.composites import monthly_evidence
from tests.composite_monthly_eligibility_helpers import retained_repository, source_snapshot


class RetainedRow:
    def __init__(self, row):
        self.row = row
        self.calls = []

    def execute(self, query, parameters):
        self.calls.append((query, parameters))
        return self

    def fetchone(self):
        return self.row


@pytest.mark.parametrize("kind", ["membership", "universe"])
@pytest.mark.parametrize("fault", [None, "missing", "hash", "scope"])
def test_retained_rows_require_exact_scope_and_independent_hash_anchor(kind, fault):
    seed, universe = retained_repository(source_snapshot())
    scope = ("synthetic-tenant", "synthetic-composite", "synthetic-definition")
    key = (*scope, "synthetic-membership")
    if kind == "membership":
        material = seed.get_membership_revision(
            tenant_id=scope[0],
            composite_id=scope[1],
            definition_version=scope[2],
            membership_revision=key[3],
        )
        reader = monthly_evidence._membership
    else:
        material = universe
        key = (*key, universe.attestation_version)
        reader = monthly_evidence._universe
    row = {"payload_json": material.model_dump(mode="json"), "content_hash": material.content_hash}
    if fault == "missing":
        row = None
    elif fault == "hash":
        row["content_hash"] = "sha256:" + "e" * 64
    elif fault == "scope":
        key = ("other-tenant", *key[1:])
    connection = RetainedRow(row)
    if fault is None:
        assert reader(connection, key) == material
    else:
        with pytest.raises(DpmCompositeConflictError, match="CUSTODY_INTEGRITY_CONFLICT"):
            reader(connection, key)
    query, parameters = connection.calls[0]
    assert parameters == key
    assert query.count("%s") == len(key)
    assert key[0] not in query


@pytest.mark.parametrize("missing", [False, True])
def test_exact_reader_never_invents_publication_proof_for_old_unmarked_approval(
    monkeypatch, missing
):
    wire = json.loads(
        (
            Path(__file__).parents[3]
            / "fixtures/composites/historical-recurring-monthly-approval.json"
        ).read_text(encoding="utf-8")
    )
    approval = MonthlyEvaluationApproval.model_validate(wire)
    assert approval.proposal.publication_evidence_version is None
    connection = RetainedRow(None)
    key = (
        "synthetic-tenant",
        "synthetic-composite",
        "synthetic-definition",
        approval.proposal.evaluation_revision,
    )
    calls = []

    def retained_approval(actual_connection, actual_key):
        calls.append((actual_connection, actual_key))
        return None if missing else approval

    monkeypatch.setattr(monthly_evidence.evaluation_control, "get_approval", retained_approval)
    assert monthly_evidence.resolve(connection, key, approval.content_hash) is None
    assert calls == [(connection, key)] and connection.calls == []
