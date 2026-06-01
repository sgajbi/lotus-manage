from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from src.core.construction.models import AuthoritativeRegimeStressContext
from src.core.proof_packs.models import DpmPreTradeProofPack


PROOF_PACK_EXAMPLE = {
    "proof_pack_id": "dpp_rr_001",
    "proof_pack_version": "1.0",
    "portfolio_id": "PB_SG_GLOBAL_BAL_001",
    "mandate_id": "mandate_001",
    "source_type": "REBALANCE_RUN",
    "rebalance_run_id": "rr_001",
    "alternative_set_id": None,
    "selected_alternative_id": None,
    "as_of_date": "2026-05-03",
    "status": "DEGRADED",
    "content_hash": "sha256:example",
    "created_at": "2026-05-03T09:30:00+00:00",
    "created_by": "pm_001",
    "correlation_id": "corr-proof-pack-001",
}


class DpmProofPackGenerateRequest(BaseModel):
    source_type: Literal["REBALANCE_RUN", "SELECTED_ALTERNATIVE"] = Field(
        description="Source object used to generate the proof pack.",
        examples=["REBALANCE_RUN"],
    )
    rebalance_run_id: str | None = Field(
        default=None,
        description="Source rebalance run id required when source_type is `REBALANCE_RUN`.",
        examples=["rr_001"],
    )
    alternative_set_id: str | None = Field(
        default=None,
        description="Construction alternative set id required for selected-alternative proof.",
        examples=["cas_001"],
    )
    selected_alternative_id: str | None = Field(
        default=None,
        description="Selected alternative id required for selected-alternative proof.",
        examples=["alt_min_turnover"],
    )
    include_markdown: bool = Field(
        default=True,
        description="Whether the caller intends to retrieve deterministic Markdown.",
        examples=[True],
    )
    include_report_input: bool = Field(
        default=False,
        description="Whether to append a deterministic report-input evidence reference.",
        examples=[False],
    )
    include_ai_evidence_input: bool = Field(
        default=False,
        description="Whether to append a deterministic AI-evidence input reference.",
        examples=[False],
    )
    actor_id: str = Field(
        description="Human or service actor generating the proof pack.",
        examples=["pm_001"],
    )
    reason: str | None = Field(
        default=None,
        description="Business rationale for generating the proof pack.",
        examples=["Rebalance back to model after drift review."],
    )
    mandate_id: str | None = Field(
        default=None,
        description="Mandate identifier when available.",
        examples=["mandate_001"],
    )
    regime_stress_context: AuthoritativeRegimeStressContext | None = Field(
        default=None,
        description=(
            "Optional source-owned `RegimeScenarioPackEvaluation:v1` context for direct "
            "proof-pack scenario/regime enrichment. It is used only when the selected "
            "construction alternative does not already carry regime-stress authority context; "
            "Manage preserves source-supplied scenario, CIO approval, effective-period, and "
            "portfolio/mandate applicability evidence, does not calculate scenario methodology, "
            "and does not validate source-owner approval workflow."
        ),
    )


class DpmProofPackGenerateResponse(BaseModel):
    proof_pack: DpmPreTradeProofPack = Field(description="Generated durable proof pack.")
    markdown_url: str | None = Field(
        default=None,
        description="Relative URL for deterministic Markdown retrieval when requested.",
        examples=["/api/v1/rebalance/proof-packs/dpp_rr_001/summary.md"],
    )
    report_input_url: str | None = Field(
        default=None,
        description="Relative URL for report input retrieval when requested.",
        examples=["/api/v1/rebalance/proof-packs/dpp_rr_001/report-input"],
    )
    ai_evidence_input_url: str | None = Field(
        default=None,
        description="Relative URL for AI evidence input retrieval when requested.",
        examples=["/api/v1/rebalance/proof-packs/dpp_rr_001/ai-evidence-input"],
    )


class DpmProofPackLookupResponse(BaseModel):
    proof_pack: DpmPreTradeProofPack = Field(description="Persisted proof pack.")
