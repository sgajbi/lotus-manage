"""A declared impact window must cover every changed effective decision."""

from copy import deepcopy

import pytest

from src.core.composite_corrections import require_correction_window
from src.core.composite_membership import DpmCompositeDefinition, DpmCompositeMembershipRevision
from src.core.composite_repository import DpmCompositeConflictError
from src.infrastructure.composites.in_memory import InMemoryDpmCompositeRepository
from src.infrastructure.composites import in_memory
from tests.composite_correction_helpers import (
    correction_body,
    decision,
    definition_body,
    original_body,
)


def revision(body, name):
    return DpmCompositeMembershipRevision(
        tenant_id="tenant-sg",
        composite_id="PB_GLOBAL_BALANCED_USD",
        definition_version="2026.10",
        membership_revision=name,
        decided_by="synthetic-maker",
        **body,
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("status", "EXCLUDED"),
        ("discretionary", False),
        ("approval_ref", "substituted-approval"),
        ("source_snapshot_id", "substituted-source"),
    ],
)
def test_correction_refuses_changed_decision_evidence_outside_window(field, value):
    body = correction_body()
    body["decisions"][0][field] = value
    if field == "status":
        body["decisions"][0]["reason_code"] = "SYNTHETIC_POLICY_EXCLUSION"
    with pytest.raises(ValueError, match="COMPOSITE_MEMBERSHIP_CORRECTION_OUTSIDE_WINDOW"):
        require_correction_window(
            parent=revision(original_body(), "m1"), revision=revision(body, "m2")
        )


@pytest.mark.parametrize("index", [0, 2, 3, 5])
def test_correction_refuses_removed_history_or_unrelated_member(index):
    body = correction_body()
    del body["decisions"][index]
    with pytest.raises(ValueError, match="COMPOSITE_MEMBERSHIP_CORRECTION_OUTSIDE_WINDOW"):
        require_correction_window(
            parent=revision(original_body(), "m1"), revision=revision(body, "m2")
        )


def test_correction_accepts_exact_boundary_equivalent_splits_and_day_limits():
    parent = revision(original_body(), "m1")
    body = correction_body()
    body["decisions"][:1] = [
        decision("A", last="2026-01-02"),
        decision("A", "2026-01-03", "2026-01-04"),
    ]
    require_correction_window(parent=parent, revision=revision(body, "m2"))
    for first, last in (("0001-01-01", "0001-01-01"), ("9999-12-31", "9999-12-31")):
        unchanged = original_body() | {
            "supersedes_membership_revision": "m1",
            "affected_from": first,
            "affected_to": last,
        }
        require_correction_window(parent=parent, revision=revision(unchanged, "m2"))


def test_memory_refusal_is_atomic_and_valid_correction_replays_without_mutating_parent():
    repository = InMemoryDpmCompositeRepository()
    repository.save_definition(
        definition=DpmCompositeDefinition(
            tenant_id="tenant-sg",
            composite_id="PB_GLOBAL_BALANCED_USD",
            definition_version="2026.10",
            created_by="synthetic-maker",
            **definition_body(),
        )
    )
    parent = revision(original_body(), "m1")
    repository.save_membership_revision(revision=parent)
    invalid = deepcopy(correction_body())
    invalid["decisions"] = [decision("A", excluded=True)]
    with pytest.raises(
        DpmCompositeConflictError, match="COMPOSITE_MEMBERSHIP_CORRECTION_OUTSIDE_WINDOW"
    ):
        repository.save_membership_revision(revision=revision(invalid, "m2"))
    assert (
        len(repository.list_publications(tenant_id="tenant-sg", after_sequence=0, limit=10).items)
        == 1
    )
    corrected = revision(correction_body(), "m2")
    repository.save_membership_revision(revision=corrected)
    repository.save_membership_revision(revision=corrected)
    assert (
        repository.get_membership_revision(
            tenant_id="tenant-sg",
            composite_id=parent.composite_id,
            definition_version=parent.definition_version,
            membership_revision="m1",
        )
        == parent
    )
    assert (
        len(repository.list_publications(tenant_id="tenant-sg", after_sequence=0, limit=10).items)
        == 2
    )


def test_correction_guard_requires_an_explicit_window():
    with pytest.raises(ValueError, match="COMPOSITE_MEMBERSHIP_CORRECTION_WINDOW_REQUIRED"):
        require_correction_window(
            parent=revision(original_body(), "m1"), revision=revision(original_body(), "m2")
        )


def test_legacy_exact_replay_preserves_retained_wrong_window_without_allowing_new_revision(
    monkeypatch,
):
    repository = InMemoryDpmCompositeRepository()
    repository.save_definition(
        definition=DpmCompositeDefinition(
            tenant_id="tenant-sg",
            composite_id="PB_GLOBAL_BALANCED_USD",
            definition_version="2026.10",
            created_by="synthetic-maker",
            **definition_body(),
        )
    )
    parent = revision(original_body(), "m1")
    repository.save_membership_revision(revision=parent)
    body = correction_body() | {"decisions": [decision("A", excluded=True)]}
    retained = revision(body, "m2")
    # Model the pre-fix writer's accepted historical state, then restore enforcement.
    with monkeypatch.context() as legacy:
        legacy.setattr(in_memory, "require_correction_window", lambda **kwargs: None)
        repository.save_membership_revision(revision=retained)
    publications = repository.list_publications(tenant_id="tenant-sg", after_sequence=0, limit=10)
    repository.save_membership_revision(revision=retained)
    assert (
        repository.list_publications(tenant_id="tenant-sg", after_sequence=0, limit=10)
        == publications
    )
    with pytest.raises(
        DpmCompositeConflictError, match="COMPOSITE_MEMBERSHIP_CORRECTION_OUTSIDE_WINDOW"
    ):
        repository.save_membership_revision(revision=revision(body, "m3"))
