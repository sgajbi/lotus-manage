"""Published examples of the tenant-scoped derived identities (#648).

Every id here is a hash over a length-prefixed component sequence, so none of
them can be written by hand and stay correct. They were all readable strings
before #648 - `mh_<date>_<portfolio>`, `dpp_rr_001`, `me_<date>_<portfolio>_<dimension>` -
and the published examples kept those shapes after the derivations changed, so
the OpenAPI document described ids the service can no longer emit and every
generated client was built from them.

Each example is stored beside the inputs it derives from, so a test can
re-derive it through the production path rather than trusting the literal. That
is the point of this module: an example nobody can verify is an example nobody
notices going stale.

The tenant is the canonical demo dataset's query tenant, so a reader can
reproduce these values rather than merely believe them.
"""

from __future__ import annotations

EXAMPLE_TENANT_ID = "default"
EXAMPLE_PORTFOLIO_ID = "PB_SG_GLOBAL_BAL_001"
EXAMPLE_AS_OF_DATE = "2026-05-03"

# derived_identity("mh", tenant, portfolio, as_of_date)
HEALTH_SNAPSHOT_ID_EXAMPLE = "mh_8ecb4ce03a9091104414e926331f0c3d"

# derived_identity("me", tenant, as_of_date, portfolio, dimension)
EXAMPLE_EXCEPTION_DIMENSION = "SOURCE_READINESS"
MONITORING_EXCEPTION_ID_EXAMPLE = "me_f3d508fd9d651dc1c40d2e80e9fec9f6"

# derived_identity("dpp", tenant, rebalance_run_id)
EXAMPLE_REBALANCE_RUN_ID = "drr_001"
PROOF_PACK_ID_EXAMPLE = "dpp_e63c4f04bf4e75d37bb3bf3a8b4cd221"

# derived_identity("dpp", tenant, alternative_set_id, selected_alternative_id)
EXAMPLE_ALTERNATIVE_SET_ID = "das_001"
EXAMPLE_SELECTED_ALTERNATIVE_ID = "dalt_001"
PROOF_PACK_ALTERNATIVE_ID_EXAMPLE = "dpp_33c6cd64b5ccd18ef77ad02f86d4c9c0"

__all__ = [
    "EXAMPLE_TENANT_ID",
    "EXAMPLE_PORTFOLIO_ID",
    "EXAMPLE_AS_OF_DATE",
    "HEALTH_SNAPSHOT_ID_EXAMPLE",
    "EXAMPLE_EXCEPTION_DIMENSION",
    "MONITORING_EXCEPTION_ID_EXAMPLE",
    "EXAMPLE_REBALANCE_RUN_ID",
    "PROOF_PACK_ID_EXAMPLE",
    "EXAMPLE_ALTERNATIVE_SET_ID",
    "EXAMPLE_SELECTED_ALTERNATIVE_ID",
    "PROOF_PACK_ALTERNATIVE_ID_EXAMPLE",
]
