"""New, explicitly unqualified v2 fixture authority for July–September monthly proofs.

This defines a separate initial profile; it never extends an issued profile or
qualifies a provider, method, financial fact or institutional approval.
"""

from copy import deepcopy

from src.core.composite_definition_versions import decode_composite_definition
from tests.composite_authority_helpers import frozen_authority_pack, rebind_definition


def synthetic_monthly_v2_definition(legacy):
    wire = deepcopy(frozen_authority_pack()["external_versions"]["original"]["definition"])
    for name in (
        "tenant_id",
        "composite_id",
        "definition_version",
        "display_name",
        "strategy_code",
        "reporting_currency",
        "inception_date",
        "termination_date",
        "eligibility_policy_version",
        "created_by",
        "correlation_id",
    ):
        wire[name] = getattr(legacy, name)
    wire["created_at"] = "2026-06-01T00:00:00.000000Z"
    profile = wire["source_authority"]["payload"]
    profile.update(
        tenant_id=legacy.tenant_id,
        composite_id=legacy.composite_id,
        profile_id="synthetic.recurring.initial.profile",
        profile_revision="synthetic.recurring.initial.r1",
        effective_from="2026-07-01",
        effective_to="2026-09-30",
    )
    identity = deepcopy(profile["member_identities"][0])
    identity.update(member_id="synthetic-member", source_member_id="synthetic-member")
    profile["member_identities"] = [identity]
    for selection in profile["selections"]:
        selection.update(
            member_ids=["synthetic-member"], effective_from="2026-07-01", effective_to="2026-09-30"
        )
    claims = wire["authority_approval"]["claims"]
    claims.update(
        tenant_id=legacy.tenant_id,
        composite_id=legacy.composite_id,
        definition_version=legacy.definition_version,
        profile_id=profile["profile_id"],
        profile_revision=profile["profile_revision"],
        effective_from=profile["effective_from"],
        effective_to=profile["effective_to"],
        approved_at="2026-06-02T00:00:00.000000Z",
    )
    return decode_composite_definition(rebind_definition(wire, refresh_approval=True))
