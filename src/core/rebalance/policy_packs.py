import json
from collections.abc import Mapping
from decimal import Decimal
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, ValidationError

from src.core.models import EngineOptions, GroupConstraint

DpmPolicyPackSource = Literal["DISABLED", "REQUEST", "TENANT_DEFAULT", "GLOBAL_DEFAULT", "NONE"]

_POLICY_PACK_SECTION_KEYS = (
    "turnover_policy",
    "tax_policy",
    "settlement_policy",
    "constraint_policy",
    "workflow_policy",
    "idempotency_policy",
)


class DpmEffectivePolicyPackResolution(BaseModel):
    enabled: bool = Field(
        description="Whether policy-pack resolution is enabled for lotus-manage request processing.",
        examples=[False],
    )
    selected_policy_pack_id: Optional[str] = Field(
        default=None,
        description="Resolved policy-pack identifier, when one is selected.",
        examples=["dpm_standard_v1"],
    )
    source: DpmPolicyPackSource = Field(
        description="Resolution source selected by precedence policy.",
        examples=["REQUEST"],
    )


class DpmPolicyPackTurnoverPolicy(BaseModel):
    max_turnover_pct: Optional[Decimal] = Field(
        default=None,
        description="Optional turnover cap override to apply on selected policy-pack.",
        examples=["0.15"],
    )


class DpmPolicyPackTaxPolicy(BaseModel):
    enable_tax_awareness: Optional[bool] = Field(
        default=None,
        description="Optional override for tax-aware sell allocation behavior.",
        examples=[True],
    )
    max_realized_capital_gains: Optional[Decimal] = Field(
        default=None,
        ge=0,
        description="Optional override for realized capital gains budget in base currency.",
        examples=["100"],
    )


class DpmPolicyPackSettlementPolicy(BaseModel):
    enable_settlement_awareness: Optional[bool] = Field(
        default=None,
        description="Optional override for settlement ladder checks.",
        examples=[True],
    )
    settlement_horizon_days: Optional[int] = Field(
        default=None,
        ge=0,
        le=10,
        description="Optional override for settlement ladder horizon in day offsets.",
        examples=[3],
    )


class DpmPolicyPackConstraintPolicy(BaseModel):
    single_position_max_weight: Optional[Decimal] = Field(
        default=None,
        ge=0,
        le=1,
        description="Optional override for single-position maximum weight.",
        examples=["0.25"],
    )
    group_constraints: dict[str, GroupConstraint] = Field(
        default_factory=dict,
        description="Optional override for group constraints by attribute key/value.",
        examples=[{"sector:TECH": {"max_weight": "0.20"}}],
    )


class DpmPolicyPackWorkflowPolicy(BaseModel):
    enable_workflow_gates: Optional[bool] = Field(
        default=None,
        description="Optional override for deterministic workflow gate output.",
        examples=[True],
    )
    workflow_requires_mandate_approval: Optional[bool] = Field(
        default=None,
        description="Optional override for workflow mandate-approval requirement.",
        examples=[False],
    )
    mandate_approval_already_obtained: Optional[bool] = Field(
        default=None,
        description="Optional override indicating mandate approval already obtained for gate evaluation.",
        examples=[False],
    )


class DpmPolicyPackIdempotencyPolicy(BaseModel):
    replay_enabled: Optional[bool] = Field(
        default=None,
        description="Optional override for idempotent replay behavior on simulate endpoint.",
        examples=[True],
    )


class DpmPolicyPackDefinition(BaseModel):
    policy_pack_id: str = Field(
        description="Unique policy-pack identifier.",
        examples=["dpm_standard_v1"],
    )
    version: str = Field(
        description="Policy-pack version.",
        examples=["1"],
    )
    turnover_policy: DpmPolicyPackTurnoverPolicy = Field(
        default_factory=DpmPolicyPackTurnoverPolicy,
        description="Turnover policy overrides for selected policy-pack.",
    )
    tax_policy: DpmPolicyPackTaxPolicy = Field(
        default_factory=DpmPolicyPackTaxPolicy,
        description="Tax policy overrides for selected policy-pack.",
    )
    settlement_policy: DpmPolicyPackSettlementPolicy = Field(
        default_factory=DpmPolicyPackSettlementPolicy,
        description="Settlement policy overrides for selected policy-pack.",
    )
    constraint_policy: DpmPolicyPackConstraintPolicy = Field(
        default_factory=DpmPolicyPackConstraintPolicy,
        description="Constraint policy overrides for selected policy-pack.",
    )
    workflow_policy: DpmPolicyPackWorkflowPolicy = Field(
        default_factory=DpmPolicyPackWorkflowPolicy,
        description="Workflow policy overrides for selected policy-pack.",
    )
    idempotency_policy: DpmPolicyPackIdempotencyPolicy = Field(
        default_factory=DpmPolicyPackIdempotencyPolicy,
        description="Idempotency policy overrides for selected policy-pack.",
    )


class DpmPolicyPackCatalogResponse(BaseModel):
    enabled: bool = Field(
        description="Whether policy-pack resolution is enabled in this runtime.",
        examples=[True],
    )
    total: int = Field(
        description="Total number of policy-pack definitions currently available in the catalog.",
        examples=[3],
    )
    selected_policy_pack_id: Optional[str] = Field(
        default=None,
        description=(
            "Resolved policy-pack identifier for the provided request context, "
            "when one is selected."
        ),
        examples=["dpm_standard_v1"],
    )
    selected_policy_pack_present: bool = Field(
        description=(
            "Whether the resolved policy-pack identifier exists in the current policy-pack catalog."
        ),
        examples=[True],
    )
    selected_policy_pack_source: DpmPolicyPackSource = Field(
        description="Resolution source selected by precedence policy.",
        examples=["REQUEST"],
    )
    items: list[DpmPolicyPackDefinition] = Field(
        description="Catalog entries keyed by policy-pack identifier.",
        examples=[
            [
                {
                    "policy_pack_id": "dpm_standard_v1",
                    "version": "1",
                    "turnover_policy": {"max_turnover_pct": "0.10"},
                    "tax_policy": {"enable_tax_awareness": True},
                    "settlement_policy": {"enable_settlement_awareness": False},
                    "constraint_policy": {"single_position_max_weight": "0.25"},
                    "workflow_policy": {"enable_workflow_gates": True},
                    "idempotency_policy": {"replay_enabled": True},
                }
            ]
        ],
    )


class DpmPolicyPackUpsertRequest(BaseModel):
    version: str = Field(
        description="Policy-pack version.",
        examples=["2"],
    )
    turnover_policy: DpmPolicyPackTurnoverPolicy = Field(
        default_factory=DpmPolicyPackTurnoverPolicy,
        description="Turnover policy overrides for selected policy-pack.",
    )
    tax_policy: DpmPolicyPackTaxPolicy = Field(
        default_factory=DpmPolicyPackTaxPolicy,
        description="Tax policy overrides for selected policy-pack.",
    )
    settlement_policy: DpmPolicyPackSettlementPolicy = Field(
        default_factory=DpmPolicyPackSettlementPolicy,
        description="Settlement policy overrides for selected policy-pack.",
    )
    constraint_policy: DpmPolicyPackConstraintPolicy = Field(
        default_factory=DpmPolicyPackConstraintPolicy,
        description="Constraint policy overrides for selected policy-pack.",
    )
    workflow_policy: DpmPolicyPackWorkflowPolicy = Field(
        default_factory=DpmPolicyPackWorkflowPolicy,
        description="Workflow policy overrides for selected policy-pack.",
    )
    idempotency_policy: DpmPolicyPackIdempotencyPolicy = Field(
        default_factory=DpmPolicyPackIdempotencyPolicy,
        description="Idempotency policy overrides for selected policy-pack.",
    )


class DpmPolicyPackMutationResponse(BaseModel):
    item: DpmPolicyPackDefinition = Field(
        description="Policy-pack definition persisted by this mutation."
    )


def resolve_effective_policy_pack(
    *,
    policy_packs_enabled: bool,
    request_policy_pack_id: Optional[str],
    tenant_default_policy_pack_id: Optional[str],
    global_default_policy_pack_id: Optional[str],
) -> DpmEffectivePolicyPackResolution:
    if not policy_packs_enabled:
        return DpmEffectivePolicyPackResolution(
            enabled=False,
            selected_policy_pack_id=None,
            source="DISABLED",
        )

    request_policy_pack_id = _normalize_policy_pack_id(request_policy_pack_id)
    tenant_default_policy_pack_id = _normalize_policy_pack_id(tenant_default_policy_pack_id)
    global_default_policy_pack_id = _normalize_policy_pack_id(global_default_policy_pack_id)

    if request_policy_pack_id is not None:
        return DpmEffectivePolicyPackResolution(
            enabled=True,
            selected_policy_pack_id=request_policy_pack_id,
            source="REQUEST",
        )
    if tenant_default_policy_pack_id is not None:
        return DpmEffectivePolicyPackResolution(
            enabled=True,
            selected_policy_pack_id=tenant_default_policy_pack_id,
            source="TENANT_DEFAULT",
        )
    if global_default_policy_pack_id is not None:
        return DpmEffectivePolicyPackResolution(
            enabled=True,
            selected_policy_pack_id=global_default_policy_pack_id,
            source="GLOBAL_DEFAULT",
        )
    return DpmEffectivePolicyPackResolution(
        enabled=True,
        selected_policy_pack_id=None,
        source="NONE",
    )


def _normalize_policy_pack_id(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def parse_policy_pack_catalog(catalog_json: Optional[str]) -> dict[str, DpmPolicyPackDefinition]:
    raw = _load_policy_pack_catalog_payload(catalog_json)

    catalog: dict[str, DpmPolicyPackDefinition] = {}
    for policy_pack_id, definition in raw.items():
        parsed = _parse_policy_pack_definition(
            policy_pack_id=policy_pack_id,
            definition=definition,
        )
        if parsed is None:
            continue
        normalized_id, policy_pack = parsed
        catalog[normalized_id] = policy_pack
    return catalog


def _load_policy_pack_catalog_payload(catalog_json: Optional[str]) -> dict[Any, Any]:
    normalized_json = (catalog_json or "").strip()
    if not normalized_json:
        return {}
    try:
        raw = json.loads(normalized_json)
    except json.JSONDecodeError:
        return {}
    if not isinstance(raw, dict):
        return {}
    return raw


def _policy_pack_definition_payload(
    *,
    policy_pack_id: Any,
    definition: Any,
) -> tuple[str, dict[str, object]] | None:
    normalized_id = _normalized_policy_pack_definition_id(policy_pack_id)
    if normalized_id is None or not isinstance(definition, Mapping):
        return None
    return normalized_id, _policy_pack_model_payload(
        normalized_id=normalized_id,
        definition=definition,
    )


def _normalized_policy_pack_definition_id(policy_pack_id: Any) -> str | None:
    if not isinstance(policy_pack_id, str):
        return None
    normalized_id = policy_pack_id.strip()
    return normalized_id or None


def _policy_pack_model_payload(
    *,
    normalized_id: str,
    definition: Mapping[str, Any],
) -> dict[str, object]:
    payload: dict[str, object] = {
        "policy_pack_id": normalized_id,
        "version": str(definition.get("version", "1")),
    }
    payload.update(
        {
            section_key: definition.get(section_key) or {}
            for section_key in _POLICY_PACK_SECTION_KEYS
        }
    )
    return payload


def _parse_policy_pack_definition(
    *,
    policy_pack_id: Any,
    definition: Any,
) -> tuple[str, DpmPolicyPackDefinition] | None:
    payload = _policy_pack_definition_payload(
        policy_pack_id=policy_pack_id,
        definition=definition,
    )
    if payload is None:
        return None
    normalized_id, model_payload = payload
    try:
        return normalized_id, DpmPolicyPackDefinition.model_validate(model_payload)
    except ValidationError:
        return None


def resolve_policy_pack_definition(
    *,
    resolution: DpmEffectivePolicyPackResolution,
    catalog: dict[str, DpmPolicyPackDefinition],
) -> Optional[DpmPolicyPackDefinition]:
    if resolution.selected_policy_pack_id is None:
        return None
    return catalog.get(resolution.selected_policy_pack_id)


def apply_policy_pack_to_engine_options(
    *,
    options: EngineOptions,
    policy_pack: Optional[DpmPolicyPackDefinition],
) -> EngineOptions:
    if policy_pack is None:
        return options
    updates = policy_pack_engine_option_updates(policy_pack=policy_pack)
    if not updates:
        return options
    return options.model_copy(update=updates)


def policy_pack_engine_option_updates(
    *,
    policy_pack: DpmPolicyPackDefinition,
) -> dict[str, object]:
    updates = {}
    updates.update(_turnover_engine_option_updates(policy_pack.turnover_policy))
    updates.update(_tax_engine_option_updates(policy_pack.tax_policy))
    updates.update(_settlement_engine_option_updates(policy_pack.settlement_policy))
    updates.update(_constraint_engine_option_updates(policy_pack.constraint_policy))
    updates.update(_workflow_engine_option_updates(policy_pack.workflow_policy))
    return updates


def _turnover_engine_option_updates(
    policy: DpmPolicyPackTurnoverPolicy,
) -> dict[str, object]:
    if policy.max_turnover_pct is None:
        return {}
    return {"max_turnover_pct": policy.max_turnover_pct}


def _tax_engine_option_updates(policy: DpmPolicyPackTaxPolicy) -> dict[str, object]:
    updates: dict[str, object] = {}
    if policy.enable_tax_awareness is not None:
        updates["enable_tax_awareness"] = policy.enable_tax_awareness
    if policy.max_realized_capital_gains is not None:
        updates["max_realized_capital_gains"] = policy.max_realized_capital_gains
    return updates


def _settlement_engine_option_updates(
    policy: DpmPolicyPackSettlementPolicy,
) -> dict[str, object]:
    updates: dict[str, object] = {}
    if policy.enable_settlement_awareness is not None:
        updates["enable_settlement_awareness"] = policy.enable_settlement_awareness
    if policy.settlement_horizon_days is not None:
        updates["settlement_horizon_days"] = policy.settlement_horizon_days
    return updates


def _constraint_engine_option_updates(
    policy: DpmPolicyPackConstraintPolicy,
) -> dict[str, object]:
    updates: dict[str, object] = {}
    if policy.single_position_max_weight is not None:
        updates["single_position_max_weight"] = policy.single_position_max_weight
    if policy.group_constraints:
        updates["group_constraints"] = policy.group_constraints
    return updates


def _workflow_engine_option_updates(
    policy: DpmPolicyPackWorkflowPolicy,
) -> dict[str, object]:
    updates: dict[str, object] = {}
    if policy.enable_workflow_gates is not None:
        updates["enable_workflow_gates"] = policy.enable_workflow_gates
    if policy.workflow_requires_mandate_approval is not None:
        updates["workflow_requires_mandate_approval"] = policy.workflow_requires_mandate_approval
    if policy.mandate_approval_already_obtained is not None:
        updates["mandate_approval_already_obtained"] = policy.mandate_approval_already_obtained
    return updates


def resolve_policy_pack_replay_enabled(
    *,
    default_replay_enabled: bool,
    policy_pack: Optional[DpmPolicyPackDefinition],
) -> bool:
    if policy_pack is None:
        return default_replay_enabled
    if policy_pack.idempotency_policy.replay_enabled is None:
        return default_replay_enabled
    return policy_pack.idempotency_policy.replay_enabled
