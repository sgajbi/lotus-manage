from __future__ import annotations

from typing import Annotated, Literal

from fastapi import Path, Query


CampaignDefinitionStatus = Literal["ACTIVE", "RETIRED", "SUPERSEDED"]

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
