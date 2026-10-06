"""Explicit v2 definition request: scope/actor come from the admitted route context."""

from typing import Literal

from pydantic import Field

from src.core.composite_authority_models import (
    BusinessDate,
    CompositeSourceAuthorityV2,
    Digest,
    Identity,
    StrictAuthorityModel,
)
from src.core.composite_definition_versions import CompositeAuthorityApproval


class CompositeDefinitionV2Request(StrictAuthorityModel):
    product_version: Literal["v2"]
    display_name: str = Field(min_length=1, max_length=256)
    strategy_code: Identity
    reporting_currency: str = Field(pattern=r"^[A-Z]{3}$")
    inception_date: BusinessDate
    termination_date: BusinessDate | None
    calculation_method: Literal["ASSET_WEIGHTED"]
    eligibility_policy_version: Identity
    source_authority: CompositeSourceAuthorityV2
    created_at: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z$")
    correlation_id: Identity
    definition_payload_digest: Digest
    authority_approval: CompositeAuthorityApproval
    content_hash: Digest
