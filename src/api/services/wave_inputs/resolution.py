"""Resolve Core-owned wave inputs once and retain their exact execution evidence."""

from copy import deepcopy
from datetime import date
from typing import Any

from pydantic import ValidationError

from src.api.request_models import RebalanceExecutionRequestEnvelope, RebalanceRequest
from src.api.services import rebalance_simulation_service
from src.api.services.rebalance_simulation_errors import DpmRebalanceEnvelopeValidationError
from src.api.services.wave_errors import DpmWaveValidationError
from src.api.services.wave_simulation_item import DpmWaveSimulationInput
from src.core.common.canonical import hash_canonical_payload
from src.core.construction.models import ConstructionAuthorityContext
from src.core.dpm_source_context import DpmResolvedSourceContext, DpmStatefulInput
from src.core.models import EngineOptions
from src.core.waves import DpmRebalanceWave, DpmRebalanceWaveItem


class DpmWaveFrozenInputIntegrityError(ValueError):
    """Non-retryable corruption of an admitted financial input."""


def freeze_wave_inputs(
    *,
    wave: DpmRebalanceWave,
    item_inputs: dict[str, dict[str, Any]],
    tenant_id: str,
    correlation_id: str,
    retained_inputs: dict[str, dict[str, object]] | None = None,
) -> dict[str, dict[str, Any]]:
    """Legacy stateless payloads remain unchanged; stateful retries reuse admitted evidence."""
    by_id = {item.wave_item_id: item for item in wave.items}
    frozen = {}
    for item_id, payload in item_inputs.items():
        if payload.get("input_mode") != "stateful":
            frozen[item_id] = payload
            continue
        if retained_inputs is not None:
            retained = retained_inputs.get(item_id, {})
            if retained.get("source_request") != payload:
                raise DpmWaveValidationError(
                    "DPM_WAVE_SIMULATION_IDEMPOTENCY_CONFLICT",
                    "The operation owns different immutable source input selectors or options.",
                )
            simulation_input_from_payload(retained)
            frozen[item_id] = deepcopy(retained)
            continue
        item = by_id[item_id]
        if item.state != "SOURCE_READY" or not item.mandate_id or not item.model_portfolio_id:
            raise DpmWaveValidationError(
                "DPM_WAVE_SIMULATION_SOURCE_SCOPE_REQUIRED",
                "Stateful input requires a source-ready item with mandate and model identity.",
            )
        override = payload.get("options_override", {})
        if set(override) - EngineOptions.model_fields.keys():
            raise DpmRebalanceEnvelopeValidationError("DPM_WAVE_SIMULATION_OPTIONS_INVALID")
        try:
            options = EngineOptions.model_validate(override)
        except ValidationError as exc:
            raise DpmRebalanceEnvelopeValidationError(
                "DPM_WAVE_SIMULATION_OPTIONS_INVALID"
            ) from exc
        envelope = RebalanceExecutionRequestEnvelope(
            input_mode="stateful",
            stateful_input=DpmStatefulInput(
                portfolio_id=item.portfolio_id,
                as_of=date.fromisoformat(wave.as_of_date),
                tenant_id=tenant_id,
                mandate_id=item.mandate_id,
                model_portfolio_id=item.model_portfolio_id,
                include_tax_lots=options.enable_tax_awareness,
            ),
            options_override=payload.get("options_override", {}),
        )
        request, source = rebalance_simulation_service.resolve_rebalance_request_envelope(
            envelope=envelope,
            correlation_id=correlation_id,
            admitted_tenant_id=tenant_id,
        )
        if source is None:
            raise DpmWaveValidationError(
                "DPM_WAVE_SIMULATION_SOURCE_CONTEXT_REQUIRED",
                "Stateful wave input did not resolve its source evidence.",
            )
        _require_matching_source(item=item, source=source, tenant_id=tenant_id)
        frozen[item_id] = {
            "stateless_input": request.model_dump(mode="json"),
            "source_context": source.model_dump(mode="json"),
            "source_request": deepcopy(payload),
            **(
                {"authority_context": payload["authority_context"]}
                if "authority_context" in payload
                else {}
            ),
        }
    return frozen


def _require_matching_source(
    *, item: DpmRebalanceWaveItem, source: DpmResolvedSourceContext, tenant_id: str
) -> None:
    context = source.context
    policy = context.policy_context
    twin_versions = {
        ref.source_version
        for ref in item.source_refs
        if ref.source_type == "MANDATE_DIGITAL_TWIN" and ref.source_id == item.mandate_id
    }
    if (
        context.portfolio_snapshot.portfolio_id != item.portfolio_id
        or policy.tenant_id != tenant_id
        or policy.mandate_id != item.mandate_id
        or context.source_lineage.model_portfolio_id != item.model_portfolio_id
        or policy.mandate_binding_version is None
        or twin_versions != {str(policy.mandate_binding_version)}
    ):
        raise DpmWaveValidationError(
            "DPM_WAVE_SIMULATION_SOURCE_REVISION_CONFLICT",
            "Resolved source identity or mandate version differs from the checked wave item.",
        )


def simulation_input_from_payload(payload: dict[str, Any]) -> DpmWaveSimulationInput:
    source_payload = payload.get("source_context")
    source = None
    if source_payload is not None:
        try:
            source = DpmResolvedSourceContext.model_validate(source_payload)
        except ValidationError as exc:
            raise DpmWaveFrozenInputIntegrityError(
                "DPM_WAVE_SIMULATION_SOURCE_CONTEXT_INVALID"
            ) from exc
        if source.stateful_context_hash != hash_canonical_payload(
            source.context.model_dump(mode="json")
        ):
            raise DpmWaveFrozenInputIntegrityError(
                "DPM_WAVE_SIMULATION_SOURCE_CONTEXT_HASH_CONFLICT"
            )
    elif payload.get("source_request") is not None:
        raise DpmWaveFrozenInputIntegrityError("DPM_WAVE_SIMULATION_SOURCE_CONTEXT_REQUIRED")
    authority = payload.get("authority_context")
    return DpmWaveSimulationInput(
        stateless_input=RebalanceRequest.model_validate(payload["stateless_input"]),
        source_context=source,
        authority_context=ConstructionAuthorityContext.model_validate(authority)
        if authority
        else None,
    )
