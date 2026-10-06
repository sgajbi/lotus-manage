"""Closed synthetic monthly policy resolution; installation never grants approval."""

from __future__ import annotations

import calendar
from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import Field, StringConstraints, field_validator, model_validator

from src.core.common.canonical import hash_canonical_payload
from src.core.composite_authority_models import BusinessDate, Identity, StrictAuthorityModel

DecimalRatio = Annotated[str, StringConstraints(pattern=r"^(?:0(?:\.\d{1,12})?|1(?:\.0{1,12})?)$")]
PolicyLevel = Literal["PLATFORM", "TENANT", "STRATEGY", "COMPOSITE", "RUN"]
ThresholdField = Literal["CASH_THRESHOLD", "FLOW_THRESHOLD"]
LEVELS = ("PLATFORM", "TENANT", "STRATEGY", "COMPOSITE", "RUN")


class MonthlyPolicyScope(StrictAuthorityModel):
    """Application supplies this from admitted tenant and persisted definition truth."""

    tenant_id: Identity
    composite_id: Identity
    definition_version: Identity
    strategy_code: Identity
    run_id: Identity | None = None


def month_window(month: str) -> tuple[str, str]:
    """A whole calendar month, never a rolling thirty-day approximation."""
    try:
        first = date.fromisoformat(month + "-01")
    except ValueError as exc:
        raise ValueError("COMPOSITE_ELIGIBILITY_MONTH_INVALID") from exc
    if first.isoformat()[:7] != month:
        raise ValueError("COMPOSITE_ELIGIBILITY_MONTH_INVALID")
    last = first.replace(day=calendar.monthrange(first.year, first.month)[1])
    return first.isoformat(), last.isoformat()


class MonthlyPolicyLayer(StrictAuthorityModel):
    """Exact versioned configuration material, not a mutable catalogue lookup."""

    level: PolicyLevel
    policy_id: Identity
    revision: Identity
    tenant_id: Identity | None = None
    strategy_code: Identity | None = None
    composite_id: Identity | None = None
    run_id: Identity | None = None
    effective_from: BusinessDate
    effective_to: BusinessDate
    flow_threshold: DecimalRatio | None
    cash_threshold: DecimalRatio | None
    permitted_overrides: list[ThresholdField] = Field(max_length=2)

    @field_validator("flow_threshold", "cash_threshold")
    @classmethod
    def require_positive_ratio(cls, value: str | None) -> str | None:
        if value is not None and Decimal(value) <= 0:
            raise ValueError("COMPOSITE_ELIGIBILITY_THRESHOLD_NONPOSITIVE")
        return value

    @model_validator(mode="after")
    def require_valid_window_and_permissions(self) -> MonthlyPolicyLayer:
        if date.fromisoformat(self.effective_from) > date.fromisoformat(self.effective_to):
            raise ValueError("COMPOSITE_ELIGIBILITY_POLICY_WINDOW_INVALID")
        if self.permitted_overrides != sorted(set(self.permitted_overrides)):
            raise ValueError("COMPOSITE_ELIGIBILITY_PERMISSIONS_NONCANONICAL")
        return self


class ResolvedMonthlyPolicy(StrictAuthorityModel):
    product_name: Literal["CompositeMonthlyEligibilityPolicy"] = "CompositeMonthlyEligibilityPolicy"
    product_version: Literal["v1"] = "v1"
    profile_kind: Literal["SYNTHETIC_MONTHLY_ABS_NET_CASH_READINESS"] = (
        "SYNTHETIC_MONTHLY_ABS_NET_CASH_READINESS"
    )
    official_activation: Literal["UNAVAILABLE"] = "UNAVAILABLE"
    month: str = Field(pattern=r"^\d{4}-\d{2}$")
    scope: MonthlyPolicyScope
    layers: list[MonthlyPolicyLayer] = Field(min_length=1, max_length=5)
    flow_threshold: DecimalRatio
    cash_threshold: DecimalRatio
    membership_frequency: Literal["CALENDAR_MONTH"] = "CALENDAR_MONTH"
    flow_measure: Literal["ABS_NET"] = "ABS_NET"
    flow_denominator: Literal["PRIOR_MONTH_END_NET_ASSETS"] = "PRIOR_MONTH_END_NET_ASSETS"
    flow_breach_operator: Literal["GREATER_THAN_OR_EQUAL"] = "GREATER_THAN_OR_EQUAL"
    cash_denominator: Literal["MONTH_END_NET_ASSETS"] = "MONTH_END_NET_ASSETS"
    cash_numerator: Literal["SETTLED_UNENCUMBERED_CASH_ONLY"] = "SETTLED_UNENCUMBERED_CASH_ONLY"
    cash_breach_operator: Literal["GREATER_THAN"] = "GREATER_THAN"
    ratio_unit: Literal["DECIMAL_FRACTION"] = "DECIMAL_FRACTION"
    flow_date_basis: Literal["SOURCE_BUSINESS_DATE_UTC"] = "SOURCE_BUSINESS_DATE_UTC"
    holiday_treatment: Literal["NO_DATE_SHIFT"] = "NO_DATE_SHIFT"
    currency_treatment: Literal["SOURCE_NORMALIZED_SINGLE_CURRENCY"] = (
        "SOURCE_NORMALIZED_SINGLE_CURRENCY"
    )
    observation_window: Literal["WHOLE_TARGET_MONTH"] = "WHOLE_TARGET_MONTH"
    evaluation_timing: Literal["AFTER_MONTH_END"] = "AFTER_MONTH_END"
    source_cut_timing: Literal["AFTER_MONTH_END"] = "AFTER_MONTH_END"
    missing_data: Literal["REQUIRED_UNKNOWN"] = "REQUIRED_UNKNOWN"
    reentry: Literal["REEVALUATE_ALL_NEXT_MONTH_RULES"] = "REEVALUATE_ALL_NEXT_MONTH_RULES"
    content_hash: str = ""

    @model_validator(mode="after")
    def require_resolved_material(self) -> ResolvedMonthlyPolicy:
        expected_flow, expected_cash = _resolved_thresholds(self.layers, self.month, self.scope)
        if (self.flow_threshold, self.cash_threshold) != (expected_flow, expected_cash):
            raise ValueError("COMPOSITE_ELIGIBILITY_RESOLUTION_MISMATCH")
        expected = hash_canonical_payload(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash and self.content_hash != expected:
            raise ValueError("COMPOSITE_ELIGIBILITY_POLICY_DIGEST_MISMATCH")
        self.content_hash = expected
        return self


def _resolved_thresholds(
    layers: list[MonthlyPolicyLayer],
    month: str,
    scope: MonthlyPolicyScope,
) -> tuple[str, str]:
    start, end = month_window(month)
    layers = [MonthlyPolicyLayer.model_validate(layer.model_dump(mode="json")) for layer in layers]
    _require_layer_windows(layers, start, end)
    values: dict[ThresholdField, str] = {}
    permitted: set[ThresholdField] = set(layers[0].permitted_overrides)
    for index, layer in enumerate(layers):
        _require_layer_scope(layer, scope)
        _apply_layer_thresholds(values, permitted, layer, overrides=index > 0)
        permitted.intersection_update(layer.permitted_overrides)
    if set(values) != {"FLOW_THRESHOLD", "CASH_THRESHOLD"}:
        raise ValueError("COMPOSITE_ELIGIBILITY_THRESHOLD_REQUIRED")
    return values["FLOW_THRESHOLD"], values["CASH_THRESHOLD"]


def _require_layer_scope(layer: MonthlyPolicyLayer, scope: MonthlyPolicyScope) -> None:
    expected = {
        "PLATFORM": (None, None, None, None),
        "TENANT": (scope.tenant_id, None, None, None),
        "STRATEGY": (scope.tenant_id, scope.strategy_code, None, None),
        "COMPOSITE": (scope.tenant_id, None, scope.composite_id, None),
        "RUN": (scope.tenant_id, None, scope.composite_id, scope.run_id),
    }[layer.level]
    actual = (layer.tenant_id, layer.strategy_code, layer.composite_id, layer.run_id)
    if actual != expected or (layer.level == "RUN" and scope.run_id is None):
        raise ValueError("COMPOSITE_ELIGIBILITY_LAYER_SCOPE_MISMATCH")


def _require_layer_windows(layers: list[MonthlyPolicyLayer], start: str, end: str) -> None:
    order = [LEVELS.index(layer.level) for layer in layers]
    if not order or order[0] != 0 or order != sorted(set(order)):
        raise ValueError("COMPOSITE_ELIGIBILITY_INHERITANCE_ORDER_INVALID")
    for layer in layers:
        if not layer.effective_from <= start <= end <= layer.effective_to:
            raise ValueError("COMPOSITE_ELIGIBILITY_POLICY_NOT_EFFECTIVE")


def _apply_layer_thresholds(
    values: dict[ThresholdField, str],
    permitted: set[ThresholdField],
    layer: MonthlyPolicyLayer,
    *,
    overrides: bool,
) -> None:
    thresholds: tuple[tuple[ThresholdField, str | None], ...] = (
        ("FLOW_THRESHOLD", layer.flow_threshold),
        ("CASH_THRESHOLD", layer.cash_threshold),
    )
    for name, value in thresholds:
        if value is None:
            continue
        prior = values.get(name)
        economic_change = prior is None or Decimal(prior) != Decimal(value)
        if overrides and economic_change and name not in permitted:
            raise ValueError("COMPOSITE_ELIGIBILITY_OVERRIDE_FORBIDDEN")
        values[name] = value


def resolve_monthly_policy(
    layers: list[MonthlyPolicyLayer],
    *,
    month: str,
    scope: MonthlyPolicyScope,
) -> ResolvedMonthlyPolicy:
    if not 1 <= len(layers) <= 5:
        raise ValueError("COMPOSITE_ELIGIBILITY_LAYER_BOUND_EXCEEDED")
    scope = MonthlyPolicyScope.model_validate(scope.model_dump(mode="json"))
    flow, cash = _resolved_thresholds(layers, month, scope)
    return ResolvedMonthlyPolicy(
        month=month, scope=scope, layers=layers, flow_threshold=flow, cash_threshold=cash
    )
