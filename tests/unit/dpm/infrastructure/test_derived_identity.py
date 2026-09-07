"""Derived evidence keys must be injective and tenant-distinct (#648).

Two separate defects meet in these keys, and both were found by review after
the reads were already tenant-scoped:

- a key that omits the tenant lets two tenants collide on it, so scoping every
  read achieves nothing when the write itself overwrites;
- a key built by joining components with a separator is not injective when the
  components may contain that separator, so two genuinely distinct records
  raise a spurious unique violation.
"""

from __future__ import annotations

from datetime import date

from src.core.common.identity_examples import (
    EXAMPLE_ALTERNATIVE_SET_ID,
    EXAMPLE_AS_OF_DATE,
    EXAMPLE_EXCEPTION_DIMENSION,
    EXAMPLE_PORTFOLIO_ID,
    EXAMPLE_REBALANCE_RUN_ID,
    EXAMPLE_SELECTED_ALTERNATIVE_ID,
    EXAMPLE_TENANT_ID,
    HEALTH_SNAPSHOT_ID_EXAMPLE,
    MONITORING_EXCEPTION_ID_EXAMPLE,
    PROOF_PACK_ALTERNATIVE_ID_EXAMPLE,
    PROOF_PACK_ID_EXAMPLE,
)
from src.core.proof_packs.identity import (
    proof_pack_id_for_rebalance_run,
    proof_pack_id_for_selected_alternative,
)
from src.core.mandate_health_scoring import _mandate_health_snapshot_id
from src.core.mandate_models import DpmMandateHealthInput
from src.core.mandates import DpmMandateConstraintSet, DpmMandateDigitalTwin, DpmMandateReviewPolicy
from src.core.common.derived_identity import derived_identity
from src.infrastructure.mandates.postgres import _mandate_snapshot_id


def _twin(*, mandate_id: str = "MANDATE_A", portfolio_id: str = "PF_A") -> DpmMandateDigitalTwin:
    return DpmMandateDigitalTwin(
        mandate_id=mandate_id,
        portfolio_id=portfolio_id,
        mandate_version="3",
        as_of_date=date(2026, 5, 3),
        source_system="lotus-core",
        base_currency="SGD",
        reference_currency="SGD",
        risk_profile="BALANCED",
        investment_objective="LONG_TERM_TOTAL_RETURN",
        time_horizon="LONG_TERM",
        model_portfolio_id="MODEL_A",
        constraints=DpmMandateConstraintSet(),
        review_policy=DpmMandateReviewPolicy(next_review_due_date=date(2026, 6, 30)),
    )


def test_the_encoding_is_injective_across_component_boundaries() -> None:
    """Underscores are legal in identifiers, so joining on one is ambiguous.

    Tenant 'a' with mandate 'b_c' and tenant 'a_b' with mandate 'c' join to the
    same string. As a primary key that is a unique violation between two
    records that are genuinely distinct - and PostgreSQL raises it on the key
    rather than on the tenant-scoped conflict target, so it does not even
    present as a tenancy problem.
    """

    assert derived_identity("ms", "a", "b_c") != derived_identity("ms", "a_b", "c")
    assert derived_identity("ms", "a", "b", "c") != derived_identity("ms", "a_b_c")
    assert derived_identity("ms", "", "ab") != derived_identity("ms", "a", "b")

    # Still deterministic, which is what makes replay idempotent.
    assert derived_identity("ms", "t", "m") == derived_identity("ms", "t", "m")
    assert derived_identity("ms", "t", "m").startswith("ms_")


def test_the_mandate_snapshot_key_separates_tenants_and_resists_collisions() -> None:
    twin = _twin()
    assert _mandate_snapshot_id(twin, tenant_id="alpha") != _mandate_snapshot_id(
        twin, tenant_id="beta"
    )

    # The ambiguity case, through the real derivation rather than the helper.
    assert _mandate_snapshot_id(_twin(mandate_id="b_c"), tenant_id="a") != _mandate_snapshot_id(
        _twin(mandate_id="c"), tenant_id="a_b"
    )


def test_the_health_snapshot_key_separates_tenants() -> None:
    """Health snapshots upsert on health_snapshot_id alone.

    The key was mh_{date}_{portfolio} with no tenant, so two tenants
    calculating health for the same portfolio and business date derived the
    same id. The second write replaced the first's payload while leaving its
    tenant_id, so one tenant read the other's scores, breaches and reason
    codes and the other read nothing. Scoping the reads cannot help when the
    key collides.
    """

    health_input = DpmMandateHealthInput(twin=_twin())

    alpha = _mandate_health_snapshot_id(health_input, tenant_id="alpha")
    beta = _mandate_health_snapshot_id(health_input, tenant_id="beta")

    assert alpha != beta
    assert alpha == _mandate_health_snapshot_id(health_input, tenant_id="alpha")


def test_health_keys_stay_distinct_across_portfolios_within_one_tenant() -> None:
    """Adding the tenant must not collapse the distinctions already there."""

    alpha_a = _mandate_health_snapshot_id(
        DpmMandateHealthInput(twin=_twin(portfolio_id="PF_A")), tenant_id="alpha"
    )
    alpha_b = _mandate_health_snapshot_id(
        DpmMandateHealthInput(twin=_twin(portfolio_id="PF_B")), tenant_id="alpha"
    )
    assert alpha_a != alpha_b


def test_the_published_health_snapshot_example_is_reproducible_from_its_inputs() -> None:
    """The OpenAPI example must be a value this derivation can actually emit.

    The example previously showed the readable mh_<date>_<portfolio> shape and
    stayed on the page unchanged when this derivation became a tenant-scoped
    hash, so the published contract described an id the service could no longer
    produce and no test noticed. Pinning the example to the derivation means a
    future change to either one fails here rather than silently teaching every
    consumer the wrong shape. The inputs are the canonical demo dataset's, so
    the example is reproducible by a reader rather than merely plausible.
    """

    derived = _mandate_health_snapshot_id(
        DpmMandateHealthInput(twin=_twin(portfolio_id=EXAMPLE_PORTFOLIO_ID)),
        tenant_id=EXAMPLE_TENANT_ID,
    )

    assert derived == HEALTH_SNAPSHOT_ID_EXAMPLE
    assert date.fromisoformat(EXAMPLE_AS_OF_DATE) == _twin().as_of_date
    # Divergence half: a derivation ignoring its inputs would satisfy the
    # equality above, so the example must also NOT be what another tenant gets.
    assert derived != _mandate_health_snapshot_id(
        DpmMandateHealthInput(twin=_twin(portfolio_id=EXAMPLE_PORTFOLIO_ID)),
        tenant_id="tenant-other",
    )


def test_every_published_identity_example_is_reproducible_from_its_inputs() -> None:
    """The health snapshot was not the only example left on a dead shape.

    Fixing that one and not sweeping for the others is how the proof-pack and
    monitoring-exception examples survived a round of review still showing
    dpp_rr_001 and me_<date>_<portfolio>_<dimension>. All four derivations
    changed in the same tranche, so all four examples are pinned here rather
    than found one at a time by whoever next reads the OpenAPI document.
    """

    assert PROOF_PACK_ID_EXAMPLE == proof_pack_id_for_rebalance_run(
        tenant_id=EXAMPLE_TENANT_ID, rebalance_run_id=EXAMPLE_REBALANCE_RUN_ID
    )
    assert PROOF_PACK_ALTERNATIVE_ID_EXAMPLE == proof_pack_id_for_selected_alternative(
        tenant_id=EXAMPLE_TENANT_ID,
        alternative_set_id=EXAMPLE_ALTERNATIVE_SET_ID,
        selected_alternative_id=EXAMPLE_SELECTED_ALTERNATIVE_ID,
    )
    assert MONITORING_EXCEPTION_ID_EXAMPLE == derived_identity(
        "me",
        EXAMPLE_TENANT_ID,
        EXAMPLE_AS_OF_DATE,
        EXAMPLE_PORTFOLIO_ID,
        EXAMPLE_EXCEPTION_DIMENSION,
    )

    # Divergence half for each: the published example must belong to the tenant
    # it is documented under, not merely be some value the derivation emits.
    assert PROOF_PACK_ID_EXAMPLE != proof_pack_id_for_rebalance_run(
        tenant_id="tenant-other", rebalance_run_id=EXAMPLE_REBALANCE_RUN_ID
    )
    assert PROOF_PACK_ALTERNATIVE_ID_EXAMPLE != proof_pack_id_for_selected_alternative(
        tenant_id="tenant-other",
        alternative_set_id=EXAMPLE_ALTERNATIVE_SET_ID,
        selected_alternative_id=EXAMPLE_SELECTED_ALTERNATIVE_ID,
    )
    # The two proof-pack forms must not collide with each other either: both
    # carry the dpp prefix and the same tenant.
    assert PROOF_PACK_ID_EXAMPLE != PROOF_PACK_ALTERNATIVE_ID_EXAMPLE


def test_no_published_example_still_carries_a_pre_hash_identity_shape() -> None:
    """Catch the next dead-shape example without needing to know its prefix.

    Every id in this module is now a prefix plus 32 hex characters. A readable
    example - dpp_rr_001, me_20260503_pb_sg_global_bal_001_source_readiness -
    is by construction one the service can no longer emit, so the shape itself
    is the check and a new identity example cannot regress silently.
    """

    published = {
        "HEALTH_SNAPSHOT_ID_EXAMPLE": HEALTH_SNAPSHOT_ID_EXAMPLE,
        "MONITORING_EXCEPTION_ID_EXAMPLE": MONITORING_EXCEPTION_ID_EXAMPLE,
        "PROOF_PACK_ID_EXAMPLE": PROOF_PACK_ID_EXAMPLE,
        "PROOF_PACK_ALTERNATIVE_ID_EXAMPLE": PROOF_PACK_ALTERNATIVE_ID_EXAMPLE,
    }

    for name, value in published.items():
        prefix, _, digest = value.partition("_")
        assert prefix in {"mh", "me", "dpp"}, name
        assert len(digest) == 32, f"{name} is not a 32-character digest: {value}"
        assert set(digest) <= set("0123456789abcdef"), f"{name} is not hex: {value}"
