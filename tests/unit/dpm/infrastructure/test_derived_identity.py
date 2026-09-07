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
