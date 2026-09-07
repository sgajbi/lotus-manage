from __future__ import annotations

from typing import Annotated

from pydantic import AfterValidator

from fastapi import Header, Path, Query

from src.core.waves import CampaignDefinitionStatus
from src.api.routers.mandate_tenant_query import normalise_mandate_tenant

CampaignDefinitionIdPath = Annotated[
    str,
    Path(
        description="Manage-owned bulk-review campaign definition identifier.",
        examples=["campaign-holdings-apple-tesla-20260510"],
    ),
]
CampaignDefinitionVersionPath = Annotated[
    str,
    Path(
        description="Immutable campaign definition version.",
        examples=["2026.05"],
    ),
]
CampaignAssignmentTaskRefPath = Annotated[
    str,
    Path(
        description="Stable campaign assignment task reference.",
        examples=["BRC-TASK-2026-05-001"],
    ),
]
WaveIdPath = Annotated[
    str,
    Path(
        description="Durable Manage rebalance wave identifier.",
        examples=["dwv_001"],
    ),
]
WaveItemIdPath = Annotated[
    str,
    Path(
        description="Durable Manage rebalance wave item identifier.",
        examples=["dwi_001"],
    ),
]
WaveCorrelationIdHeader = Annotated[
    str | None,
    Header(
        description="Optional correlation id for wave supportability and audit traceability.",
        examples=["corr-wave-command-001"],
    ),
]
WaveTenantIdHeader = Annotated[
    str,
    Header(
        # Same boundary rule as the query form: min_length alone admits a
        # whitespace-only header, and padding must normalise rather than open a
        # private namespace nothing later reads. Unanchored deliberately - see
        # mandate_tenant_query for why an anchored form disagrees with the
        # validator on a trailing newline.
        pattern=r"\S",
        min_length=1,
        # Declared required because the handler refuses an absent tenant with
        # 422 (issue #648). Leaving it optional published a contract that
        # disagreed with the behaviour: every generated client and integration
        # test would have been built to omit a header the service rejects.
        # Stated as a rule rather than a route list. The previous wording named
        # the four routes that had it at the time, and #677 put it on every
        # wave route - a list is wrong the moment the next one is added, and
        # nothing would have failed to say so.
        description=(
            "Trusted tenant id. Required on every wave route: a wave belongs to one tenant, and "
            "a request that does not state its tenant is refused rather than answered from an "
            "assumed one. Waves persisted before tenant scoping carry no tenant and are reachable "
            "from none, including a tenant named `default`."
        ),
        examples=["tenant-sg"],
    ),
    AfterValidator(normalise_mandate_tenant),
]
WaveCreateIdempotencyKeyHeader = Annotated[
    str,
    Header(
        description="Required idempotency token for durable wave create replay protection.",
        examples=["wave-idem-001"],
    ),
]

CampaignDefinitionFilterIdQuery = Annotated[
    str | None,
    Query(
        description="Optional filter for one Manage-owned bulk-review campaign definition id.",
        examples=["campaign-holdings-apple-tesla-20260510"],
    ),
]
CampaignDefinitionStatusQuery = Annotated[
    CampaignDefinitionStatus | None,
    Query(
        description="Optional filter for campaign definition lifecycle status.",
        examples=["ACTIVE"],
    ),
]
CampaignDefinitionAsOfDateQuery = Annotated[
    str | None,
    Query(
        description="Optional campaign definition business as-of date filter.",
        examples=["2026-05-10"],
    ),
]
CampaignActiveOnQuery = Annotated[
    str | None,
    Query(
        description="Optional ISO date used to classify campaign expiry posture.",
        examples=["2026-05-10"],
    ),
]
CampaignIncludeExpiredQuery = Annotated[
    bool,
    Query(
        description="When false, omit expired campaigns from expiry-aware read models.",
    ),
]
CampaignRequestedAsOfDateQuery = Annotated[
    str | None,
    Query(
        description=(
            "Optional ISO date to evaluate read-model readiness and expiry. When omitted, each "
            "definition's persisted campaign as-of date is used."
        ),
        examples=["2026-05-10"],
    ),
]
CampaignActorIdQuery = Annotated[
    str | None,
    Query(
        description="Optional actor id to evaluate against campaign entitlement evidence.",
        examples=["pm_001"],
    ),
]
CampaignIncludeClosedQuery = Annotated[
    bool,
    Query(
        description="When false, omit closed campaign rows from attention and workflow read models.",
    ),
]
CampaignLaunchRequestedAsOfDateQuery = Annotated[
    str,
    Query(
        description="ISO date that the future wave preview/create request would use.",
        examples=["2026-05-10"],
    ),
]
CampaignLaunchActorIdOptionalQuery = Annotated[
    str | None,
    Query(
        description="Optional actor id to evaluate against campaign entitlement evidence.",
        examples=["pm_001"],
    ),
]
CampaignLaunchActorIdRequiredQuery = Annotated[
    str,
    Query(
        description="Actor id to place in the preview/create request draft.",
        examples=["pm_001"],
    ),
]
CampaignLaunchCorrelationIdQuery = Annotated[
    str | None,
    Query(
        description="Optional correlation id to carry into launch package guidance.",
        examples=["corr-campaign-launch-001"],
    ),
]
CampaignIncludeLaunchPackageQuery = Annotated[
    bool,
    Query(
        description=(
            "When true, include launch package guidance if preview readiness is READY and actor_id "
            "is supplied."
        ),
    ),
]
CampaignLaunchHistoryLimitQuery = Annotated[
    int,
    Query(
        ge=1,
        le=200,
        description="Maximum number of launch audit records to include.",
        examples=[20],
    ),
]
CampaignLaunchHistoryOffsetQuery = Annotated[
    int,
    Query(
        ge=0,
        description="Zero-based launch audit page offset.",
        examples=[0],
    ),
]
CampaignReadModelLimitQuery = Annotated[
    int,
    Query(
        ge=1,
        le=200,
        description="Maximum number of campaign read-model rows to return.",
        examples=[50],
    ),
]
CampaignReadModelOffsetQuery = Annotated[
    int,
    Query(
        ge=0,
        description="Zero-based campaign read-model page offset.",
        examples=[0],
    ),
]
CampaignEvidenceLimitQuery = Annotated[
    int,
    Query(
        ge=1,
        le=200,
        description="Maximum number of campaign evidence records to return.",
        examples=[50],
    ),
]
CampaignEvidenceOffsetQuery = Annotated[
    int,
    Query(
        ge=0,
        description="Zero-based campaign evidence page offset.",
        examples=[0],
    ),
]
