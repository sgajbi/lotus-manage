"""A real finalized staged root must not accept ordinary monthly amendment authority."""

from src.infrastructure.composites.in_memory import InMemoryDpmCompositeRepository
from tests.composite_monthly_amendment_helpers import (
    corrected_monthly_proposal,
    seed_complete_monthly_root,
)
from tests.composite_staged_eligibility_helpers import finalization_material


def staged_root_amendment(repository):
    scope, ordinary, _ = seed_complete_monthly_root(InMemoryDpmCompositeRepository())
    subject, controls, finalization = finalization_material()
    repository.save_eligibility_subject(subject=subject)
    for control in controls:
        repository.save_subject_control(control=control)
    issued = repository.finalize_eligibility_subject(finalization=finalization)
    parent = repository.get_membership_revision(
        **scope,
        membership_revision=finalization.evaluation_approval.proposal.target_membership_revision,
    )
    # These locators belong to a different ordinary history. They cannot grant
    # amendment authority over the actual retained staged root in this repository.
    proposal = corrected_monthly_proposal(ordinary, parent, sequence=issued.publication_sequence)
    return proposal, parent
