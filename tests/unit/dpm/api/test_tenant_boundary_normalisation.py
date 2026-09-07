"""A tenant must mean the same thing at every door into the store (#648).

Query, header and request body are three boundaries onto one tenant-scoped
store. `require_mandate_tenant` normalised, but nothing routed the typed
surfaces through it: none of the eight routes annotated with MandateTenantId
called it, and the annotation itself only required one non-whitespace
character. So `?tenant_id=%20tenant-a` was accepted and passed through padded -
reads missed rows stored under `tenant-a`, and writes persisted evidence into a
padded namespace nothing would later read. A tenant silently partitioned from
its own evidence is worse than a refusal, because nothing reports it.

Normalisation now belongs to the type, so a new surface cannot omit it by
forgetting a helper call.
"""

from __future__ import annotations

import pytest
from pydantic import TypeAdapter, ValidationError

from src.api.routers.mandate_tenant_query import (
    DpmMandateTenantRequiredError,
    NormalisedTenantId,
    normalise_mandate_tenant,
    require_mandate_tenant,
)
from src.api.routers.wave_route_parameters import WaveTenantIdHeader


@pytest.mark.parametrize(
    "annotated",
    [NormalisedTenantId, WaveTenantIdHeader],
    ids=["body", "wave-header"],
)
def test_padding_normalises_at_every_typed_tenant_boundary(annotated: object) -> None:
    """Padded and unpadded forms must resolve to one tenant, not two."""

    adapter = TypeAdapter(annotated)

    assert adapter.validate_python(" tenant-a ") == "tenant-a"
    assert adapter.validate_python("tenant-a") == "tenant-a"
    assert adapter.validate_python("\ttenant-a\n") == "tenant-a"


@pytest.mark.parametrize(
    "annotated",
    [NormalisedTenantId, WaveTenantIdHeader],
    ids=["body", "wave-header"],
)
@pytest.mark.parametrize("blank", ["", " ", "   ", "\t", "\n", " \t \n "])
def test_whitespace_only_tenants_are_refused_not_normalised_to_empty(
    annotated: object, blank: str
) -> None:
    """Stripping a blank must refuse, never yield the empty tenant.

    A normaliser that returned "" would turn every blank request into one
    shared nameless tenant - the assumed-tenant behaviour the fence exists to
    prevent, arrived at through the fix rather than despite it.
    """

    with pytest.raises(ValidationError):
        TypeAdapter(annotated).validate_python(blank)


def test_the_helper_and_the_type_agree_on_what_one_tenant_is() -> None:
    """Two normalisers that disagree re-open the partition they each closed."""

    for value in (" tenant-a ", "tenant-a", "\ttenant-a"):
        assert require_mandate_tenant(value) == normalise_mandate_tenant(value)

    with pytest.raises(DpmMandateTenantRequiredError):
        require_mandate_tenant("   ")
    with pytest.raises(DpmMandateTenantRequiredError):
        require_mandate_tenant(None)


def test_normalisation_does_not_collapse_genuinely_different_tenants() -> None:
    """Divergence half: stripping must not merge tenants that differ inside.

    A normaliser that removed all whitespace rather than trimming the ends
    would satisfy every assertion above while merging "tenant a" into
    "tenanta", which is the same partition defect pointing the other way.
    """

    assert normalise_mandate_tenant("tenant a") == "tenant a"
    assert normalise_mandate_tenant(" tenant a ") != normalise_mandate_tenant("tenanta")
    assert normalise_mandate_tenant("tenant-a") != normalise_mandate_tenant("tenant-b")
