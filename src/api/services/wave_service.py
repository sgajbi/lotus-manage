from __future__ import annotations

import hashlib
import json
import uuid
from collections import Counter
from datetime import datetime, timezone

from src.api.request_models import RebalanceRequest
from src.api.services import construction_service, proof_pack_service
from src.core.construction.repository import ConstructionRepository
from src.core.construction.vocabulary import ConstructionMethod
from src.core.mandates import DpmMandateDigitalTwin
from src.core.mandate_repository import DpmMandateRepository
from src.core.proof_packs.repository import DpmProofPackRepository
from src.core.rebalance_runs.service import DpmRunSupportService
from src.core.waves import (
    DpmRebalanceWave,
    DpmRebalanceWaveEvent,
    DpmRebalanceWaveItem,
    DpmWaveAggregateMetrics,
    DpmWaveAlreadyExistsError,
    DpmWaveHandoffRef,
    DpmWaveIdempotencyConflictError,
    DpmWaveRepository,
    DpmWaveSourceRef,
    DpmWaveVersionConflictError,
    DpmWaveTrigger,
    WaveItemState,
    WaveState,
    apply_wave_transition,
)
from src.core.waves.source_readiness import classify_wave_item_source_readiness


SUPPORTED_CREATE_TRIGGER_TYPES = {"EXPLICIT_PORTFOLIO_LIST"}


class DpmWaveValidationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class DpmWaveLookupError(LookupError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def preview_wave(
    *,
    trigger_type: str,
    trigger_id: str,
    rationale: str,
    as_of_date: str,
    actor_id: str,
    correlation_id: str,
    portfolios: list[dict[str, object]],
    mandate_repository: DpmMandateRepository,
) -> DpmRebalanceWave:
    _validate_trigger(trigger_type)
    items = [
        _build_item(
            index=index,
            portfolio=portfolio,
            mandate_repository=mandate_repository,
        )
        for index, portfolio in enumerate(portfolios, start=1)
    ]
    wave = DpmRebalanceWave(
        wave_id=f"dwv_preview_{uuid.uuid4().hex[:12]}",
        state="DRAFT",
        trigger=DpmWaveTrigger(
            trigger_type="EXPLICIT_PORTFOLIO_LIST",
            trigger_id=trigger_id,
            rationale=rationale,
            source_refs=_trigger_source_refs(portfolios),
        ),
        as_of_date=as_of_date,
        created_at=datetime.now(timezone.utc),
        created_by=actor_id,
        correlation_id=correlation_id,
        items=items,
        aggregate_metrics=_aggregate(items),
    )
    return apply_wave_transition(
        wave=wave,
        to_state="PREVIEWED",
        event=_event(
            wave_id=wave.wave_id,
            from_state="DRAFT",
            to_state="PREVIEWED",
            actor_id=actor_id,
            correlation_id=correlation_id,
            reason_code="WAVE_PREVIEWED",
            metadata={"item_count": len(items)},
        ),
    )


def create_wave(
    *,
    trigger_type: str,
    trigger_id: str,
    rationale: str,
    as_of_date: str,
    actor_id: str,
    correlation_id: str,
    portfolios: list[dict[str, object]],
    idempotency_key: str,
    mandate_repository: DpmMandateRepository,
    wave_repository: DpmWaveRepository,
) -> tuple[DpmRebalanceWave, bool]:
    request_hash = _request_hash(
        {
            "trigger_type": trigger_type,
            "trigger_id": trigger_id,
            "rationale": rationale,
            "as_of_date": as_of_date,
            "actor_id": actor_id,
            "portfolios": portfolios,
        }
    )
    existing = wave_repository.get_wave_by_idempotency(idempotency_key=idempotency_key)
    if existing is not None:
        return existing, True

    preview = preview_wave(
        trigger_type=trigger_type,
        trigger_id=trigger_id,
        rationale=rationale,
        as_of_date=as_of_date,
        actor_id=actor_id,
        correlation_id=correlation_id,
        portfolios=portfolios,
        mandate_repository=mandate_repository,
    )
    wave = preview.model_copy(update={"wave_id": f"dwv_{uuid.uuid4().hex[:12]}"}, deep=True)
    wave = wave.model_copy(
        update={
            "events": [
                event.model_copy(update={"wave_id": wave.wave_id}, deep=True)
                for event in wave.events
            ]
        },
        deep=True,
    )
    wave = apply_wave_transition(
        wave=wave,
        to_state="CREATED",
        event=_event(
            wave_id=wave.wave_id,
            from_state="PREVIEWED",
            to_state="CREATED",
            actor_id=actor_id,
            correlation_id=correlation_id,
            reason_code="WAVE_CREATED",
            metadata={"idempotency_key_hash": hashlib.sha256(idempotency_key.encode()).hexdigest()},
        ),
    )
    try:
        wave_repository.save_wave(
            wave=wave,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
        )
    except (DpmWaveAlreadyExistsError, DpmWaveIdempotencyConflictError) as exc:
        raise DpmWaveValidationError("WAVE_CREATE_CONFLICT", str(exc)) from exc
    return wave, False


def source_check_wave(
    *,
    wave_id: str,
    actor_id: str,
    correlation_id: str,
    mandate_repository: DpmMandateRepository,
    wave_repository: DpmWaveRepository,
) -> tuple[DpmRebalanceWave, bool]:
    wave = _get_wave_or_raise(wave_id=wave_id, wave_repository=wave_repository)
    if wave.state == "SOURCE_CHECKED":
        return wave, True
    if wave.state != "CREATED":
        raise DpmWaveValidationError(
            "DPM_WAVE_SOURCE_CHECK_INVALID_STATE",
            f"Wave {wave_id} cannot be source-checked from state {wave.state}.",
        )

    classified_items = [
        _classify_item_source_readiness(
            item=item,
            wave_as_of_date=wave.as_of_date,
            mandate_repository=mandate_repository,
        )
        for item in wave.items
    ]
    candidate = wave.model_copy(
        update={
            "items": classified_items,
            "aggregate_metrics": _aggregate(classified_items),
        },
        deep=True,
    )
    checked = apply_wave_transition(
        wave=candidate,
        to_state="SOURCE_CHECKED",
        event=_event(
            wave_id=wave.wave_id,
            from_state="CREATED",
            to_state="SOURCE_CHECKED",
            actor_id=actor_id,
            correlation_id=correlation_id,
            reason_code="WAVE_SOURCE_CHECKED",
            metadata={
                "state_counts": candidate.aggregate_metrics.state_counts,
                "ready_item_count": candidate.aggregate_metrics.ready_item_count,
                "blocked_item_count": candidate.aggregate_metrics.blocked_item_count,
                "review_required_item_count": (
                    candidate.aggregate_metrics.review_required_item_count
                ),
                "source_degraded_item_count": (
                    candidate.aggregate_metrics.source_degraded_item_count
                ),
            },
        ),
    )
    try:
        wave_repository.update_wave(wave=checked, expected_version=wave.version)
    except DpmWaveVersionConflictError as exc:
        raise DpmWaveValidationError("DPM_WAVE_VERSION_CONFLICT", str(exc)) from exc
    return checked, False


def simulate_wave(
    *,
    wave_id: str,
    actor_id: str,
    correlation_id: str,
    item_inputs: dict[str, RebalanceRequest],
    methods: list[ConstructionMethod] | None,
    construction_repository: ConstructionRepository,
    run_service: DpmRunSupportService,
    wave_repository: DpmWaveRepository,
) -> tuple[DpmRebalanceWave, bool]:
    wave = _get_wave_or_raise(wave_id=wave_id, wave_repository=wave_repository)
    if wave.state in {"SIMULATED", "PARTIALLY_SIMULATED", "SIMULATION_FAILED"}:
        return wave, True
    if wave.state != "SOURCE_CHECKED":
        raise DpmWaveValidationError(
            "DPM_WAVE_SIMULATION_INVALID_STATE",
            f"Wave {wave_id} cannot be simulated from state {wave.state}.",
        )

    simulating = apply_wave_transition(
        wave=wave,
        to_state="SIMULATING",
        event=_event(
            wave_id=wave.wave_id,
            from_state="SOURCE_CHECKED",
            to_state="SIMULATING",
            actor_id=actor_id,
            correlation_id=correlation_id,
            reason_code="WAVE_SIMULATION_STARTED",
            metadata={"ready_item_count": wave.aggregate_metrics.ready_item_count},
        ),
    )
    simulated_items = [
        _simulate_item(
            item=item,
            correlation_id=correlation_id,
            item_inputs=item_inputs,
            methods=methods,
            construction_repository=construction_repository,
            run_service=run_service,
        )
        for item in simulating.items
    ]
    candidate = simulating.model_copy(
        update={
            "items": simulated_items,
            "aggregate_metrics": _aggregate(simulated_items),
        },
        deep=True,
    )
    to_state = _simulation_result_state(simulated_items)
    completed = apply_wave_transition(
        wave=candidate,
        to_state=to_state,
        event=_event(
            wave_id=wave.wave_id,
            from_state="SIMULATING",
            to_state=to_state,
            actor_id=actor_id,
            correlation_id=correlation_id,
            reason_code="WAVE_SIMULATION_COMPLETED",
            metadata={
                "state_counts": candidate.aggregate_metrics.state_counts,
                "ready_item_count": candidate.aggregate_metrics.ready_item_count,
                "blocked_item_count": candidate.aggregate_metrics.blocked_item_count,
            },
        ),
    )
    try:
        wave_repository.update_wave(wave=completed, expected_version=wave.version)
    except DpmWaveVersionConflictError as exc:
        raise DpmWaveValidationError("DPM_WAVE_VERSION_CONFLICT", str(exc)) from exc
    return completed, False


def select_wave_item_alternative(
    *,
    wave_id: str,
    wave_item_id: str,
    alternative_id: str,
    actor_id: str,
    reason_code: str,
    comment: str | None,
    correlation_id: str,
    generate_proof_pack: bool,
    construction_repository: ConstructionRepository,
    proof_pack_repository: DpmProofPackRepository,
    mandate_repository: DpmMandateRepository,
    run_service: DpmRunSupportService,
    wave_repository: DpmWaveRepository,
) -> DpmRebalanceWave:
    wave = _get_wave_or_raise(wave_id=wave_id, wave_repository=wave_repository)
    if wave.state not in {"SIMULATED", "PARTIALLY_SIMULATED"}:
        raise DpmWaveValidationError(
            "DPM_WAVE_SELECTION_INVALID_STATE",
            f"Wave {wave_id} cannot record alternative selection from state {wave.state}.",
        )
    selected_item = next((item for item in wave.items if item.wave_item_id == wave_item_id), None)
    if selected_item is None:
        raise DpmWaveLookupError("DPM_WAVE_ITEM_NOT_FOUND", f"Wave item {wave_item_id} not found.")
    if selected_item.alternative_set_id is None:
        raise DpmWaveValidationError(
            "DPM_WAVE_ITEM_ALTERNATIVES_MISSING",
            f"Wave item {wave_item_id} has no generated alternatives.",
        )
    try:
        construction_service.select_construction_alternative(
            repository=construction_repository,
            alternative_set_id=selected_item.alternative_set_id,
            alternative_id=alternative_id,
            actor_id=actor_id,
            reason_code=reason_code,
            comment=comment,
            correlation_id=correlation_id,
        )
    except Exception as exc:
        raise DpmWaveLookupError("DPM_CONSTRUCTION_ALTERNATIVE_NOT_FOUND", str(exc)) from exc

    updated_item = _with_selection_and_proof_pack(
        item=selected_item,
        alternative_id=alternative_id,
        actor_id=actor_id,
        reason_code=reason_code,
        comment=comment,
        correlation_id=correlation_id,
        generate_proof_pack=generate_proof_pack,
        construction_repository=construction_repository,
        proof_pack_repository=proof_pack_repository,
        mandate_repository=mandate_repository,
        run_service=run_service,
    )
    updated_items = [
        updated_item if item.wave_item_id == wave_item_id else item for item in wave.items
    ]
    updated = _append_event(
        wave=wave.model_copy(
            update={
                "items": updated_items,
                "aggregate_metrics": _aggregate(updated_items),
            },
            deep=True,
        ),
        event=_event(
            wave_id=wave.wave_id,
            from_state=wave.state,
            to_state=wave.state,
            actor_id=actor_id,
            correlation_id=correlation_id,
            reason_code="WAVE_ITEM_ALTERNATIVE_SELECTED",
            event_type="ITEM_SELECTION",
            metadata={
                "wave_item_id": wave_item_id,
                "alternative_set_id": selected_item.alternative_set_id,
                "selected_alternative_id": alternative_id,
                "proof_pack_id": updated_item.proof_pack_id,
                "proof_pack_state": updated_item.diagnostics.get("proof_pack_state"),
            },
        ),
    )
    try:
        wave_repository.update_wave(wave=updated, expected_version=wave.version)
    except DpmWaveVersionConflictError as exc:
        raise DpmWaveValidationError("DPM_WAVE_VERSION_CONFLICT", str(exc)) from exc
    return updated


def approve_wave(
    *,
    wave_id: str,
    actor_id: str,
    reason_code: str,
    comment: str | None,
    correlation_id: str,
    wave_repository: DpmWaveRepository,
) -> tuple[DpmRebalanceWave, bool]:
    wave = _get_wave_or_raise(wave_id=wave_id, wave_repository=wave_repository)
    if wave.state in {"APPROVED", "APPROVED_WITH_EXCEPTIONS"}:
        return wave, True
    if wave.state not in {"SIMULATED", "PARTIALLY_SIMULATED", "REVIEW_REQUIRED"}:
        raise DpmWaveValidationError(
            "DPM_WAVE_APPROVAL_INVALID_STATE",
            f"Wave {wave_id} cannot be approved from state {wave.state}.",
        )

    approved_items = [_approve_item(item, actor_id, reason_code, comment) for item in wave.items]
    approved_count = sum(1 for item in approved_items if item.state == "APPROVED")
    if approved_count == 0:
        raise DpmWaveValidationError(
            "DPM_WAVE_APPROVAL_NO_ELIGIBLE_ITEMS",
            f"Wave {wave_id} has no selected or proof-pack-ready items to approve.",
        )

    to_state: WaveState = (
        "APPROVED" if approved_count == len(approved_items) else "APPROVED_WITH_EXCEPTIONS"
    )
    candidate = wave.model_copy(
        update={
            "items": approved_items,
            "aggregate_metrics": _aggregate(approved_items),
        },
        deep=True,
    )
    approved = apply_wave_transition(
        wave=candidate,
        to_state=to_state,
        event=_event(
            wave_id=wave.wave_id,
            from_state=wave.state,
            to_state=to_state,
            actor_id=actor_id,
            correlation_id=correlation_id,
            reason_code="WAVE_APPROVED",
            metadata={
                "approved_item_count": approved_count,
                "exception_item_count": len(approved_items) - approved_count,
                "approval_reason_code": reason_code,
                **({"comment": comment} if comment else {}),
            },
        ),
    )
    try:
        wave_repository.update_wave(wave=approved, expected_version=wave.version)
    except DpmWaveVersionConflictError as exc:
        raise DpmWaveValidationError("DPM_WAVE_VERSION_CONFLICT", str(exc)) from exc
    return approved, False


def stage_wave(
    *,
    wave_id: str,
    actor_id: str,
    reason_code: str,
    comment: str | None,
    correlation_id: str,
    wave_repository: DpmWaveRepository,
) -> tuple[DpmRebalanceWave, bool]:
    wave = _get_wave_or_raise(wave_id=wave_id, wave_repository=wave_repository)
    if wave.state in {"STAGED", "HANDOFF_READY"}:
        return wave, True
    if wave.state not in {"APPROVED", "APPROVED_WITH_EXCEPTIONS"}:
        raise DpmWaveValidationError(
            "DPM_WAVE_STAGE_INVALID_STATE",
            f"Wave {wave_id} cannot be staged from state {wave.state}.",
        )

    staged_items = [_stage_item(item, actor_id, reason_code, comment) for item in wave.items]
    staged_count = sum(1 for item in staged_items if item.state == "STAGED")
    if staged_count == 0:
        raise DpmWaveValidationError(
            "DPM_WAVE_STAGE_NO_ELIGIBLE_ITEMS",
            f"Wave {wave_id} has no approved items to stage.",
        )

    candidate = wave.model_copy(
        update={
            "items": staged_items,
            "aggregate_metrics": _aggregate(staged_items),
        },
        deep=True,
    )
    staged = apply_wave_transition(
        wave=candidate,
        to_state="STAGED",
        event=_event(
            wave_id=wave.wave_id,
            from_state=wave.state,
            to_state="STAGED",
            actor_id=actor_id,
            correlation_id=correlation_id,
            reason_code="WAVE_STAGED",
            metadata={
                "staged_item_count": staged_count,
                "stage_reason_code": reason_code,
                **({"comment": comment} if comment else {}),
            },
        ),
    )
    try:
        wave_repository.update_wave(wave=staged, expected_version=wave.version)
    except DpmWaveVersionConflictError as exc:
        raise DpmWaveValidationError("DPM_WAVE_VERSION_CONFLICT", str(exc)) from exc
    return staged, False


def handoff_wave(
    *,
    wave_id: str,
    actor_id: str,
    reason_code: str,
    comment: str | None,
    correlation_id: str,
    wave_repository: DpmWaveRepository,
) -> tuple[DpmRebalanceWave, bool]:
    wave = _get_wave_or_raise(wave_id=wave_id, wave_repository=wave_repository)
    if wave.state == "HANDOFF_READY":
        return wave, True
    if wave.state != "STAGED":
        raise DpmWaveValidationError(
            "DPM_WAVE_HANDOFF_INVALID_STATE",
            f"Wave {wave_id} cannot create handoff evidence from state {wave.state}.",
        )

    handoff_items = [_handoff_item(item, actor_id, reason_code, comment) for item in wave.items]
    handoff_item_ids = [
        item.wave_item_id for item in handoff_items if item.state == "HANDOFF_READY"
    ]
    if not handoff_item_ids:
        raise DpmWaveValidationError(
            "DPM_WAVE_HANDOFF_NO_ELIGIBLE_ITEMS",
            f"Wave {wave_id} has no staged items for operations handoff.",
        )

    handoff_ref = _handoff_ref(
        wave_id=wave.wave_id,
        item_ids=handoff_item_ids,
        actor_id=actor_id,
        reason_code=reason_code,
        correlation_id=correlation_id,
        comment=comment,
    )
    candidate = wave.model_copy(
        update={
            "items": handoff_items,
            "aggregate_metrics": _aggregate(handoff_items),
            "handoff_refs": [*wave.handoff_refs, handoff_ref],
        },
        deep=True,
    )
    handoff_ready = apply_wave_transition(
        wave=candidate,
        to_state="HANDOFF_READY",
        event=_event(
            wave_id=wave.wave_id,
            from_state="STAGED",
            to_state="HANDOFF_READY",
            actor_id=actor_id,
            correlation_id=correlation_id,
            reason_code="WAVE_HANDOFF_READY",
            metadata={
                "handoff_ref_id": handoff_ref.handoff_ref_id,
                "handoff_item_count": len(handoff_item_ids),
                "external_execution_claimed": False,
                "handoff_reason_code": reason_code,
                **({"comment": comment} if comment else {}),
            },
        ),
    )
    try:
        wave_repository.update_wave(wave=handoff_ready, expected_version=wave.version)
    except DpmWaveVersionConflictError as exc:
        raise DpmWaveValidationError("DPM_WAVE_VERSION_CONFLICT", str(exc)) from exc
    return handoff_ready, False


def wave_supportability(
    *,
    wave_id: str,
    wave_repository: DpmWaveRepository,
) -> dict[str, object]:
    wave = _get_wave_or_raise(wave_id=wave_id, wave_repository=wave_repository)
    issues = [
        issue
        for index, item in enumerate(wave.items, start=1)
        if (issue := _supportability_issue(wave_id=wave.wave_id, item=item, item_index=index))
        is not None
    ]
    blocked_count = sum(1 for issue in issues if issue["severity"] == "CRITICAL")
    degraded_count = sum(1 for issue in issues if issue["severity"] == "WARNING")
    if blocked_count:
        state = "blocked"
        reason = "wave_blocked_items"
    elif degraded_count:
        state = "degraded"
        reason = "wave_degraded_items"
    else:
        state = "ready"
        reason = "wave_supportability_ready"
    return {
        "wave_id": wave.wave_id,
        "wave_state": wave.state,
        "supportability_state": state,
        "reason": reason,
        "item_count": len(wave.items),
        "issue_counts": {
            "critical": blocked_count,
            "warning": degraded_count,
            "info": sum(1 for issue in issues if issue["severity"] == "INFO"),
        },
        "issues": issues,
        "operator_actions": _operator_actions(state=state, issues=issues),
    }


def _get_wave_or_raise(
    *,
    wave_id: str,
    wave_repository: DpmWaveRepository,
) -> DpmRebalanceWave:
    wave = wave_repository.get_wave(wave_id=wave_id)
    if wave is None:
        raise DpmWaveLookupError("DPM_WAVE_NOT_FOUND", f"Wave {wave_id} was not found.")
    return wave


def _simulate_item(
    *,
    item: DpmRebalanceWaveItem,
    correlation_id: str,
    item_inputs: dict[str, RebalanceRequest],
    methods: list[ConstructionMethod] | None,
    construction_repository: ConstructionRepository,
    run_service: DpmRunSupportService,
) -> DpmRebalanceWaveItem:
    if item.state != "SOURCE_READY":
        return item
    rebalance_request = item_inputs.get(item.wave_item_id) or item_inputs.get(item.portfolio_id)
    if rebalance_request is None:
        return item.model_copy(
            update={
                "state": "SIMULATION_BLOCKED",
                "reason_codes": ["CONSTRUCTION_INPUT_MISSING"],
                "diagnostics": {
                    **item.diagnostics,
                    "source_owner": "wave-simulation-request",
                    "required_action": "SUPPLY_RFC0039_REBALANCE_REQUEST",
                },
            },
            deep=True,
        )
    try:
        alternative_set = construction_service.generate_construction_alternative_set(
            request=rebalance_request,
            idempotency_key=f"wave:{item.wave_item_id}:simulate",
            correlation_id=correlation_id,
            repository=construction_repository,
            methods=methods,
            run_service=run_service,
        )
    except Exception as exc:
        return item.model_copy(
            update={
                "state": "SIMULATION_BLOCKED",
                "reason_codes": ["CONSTRUCTION_ALTERNATIVE_GENERATION_FAILED"],
                "diagnostics": {
                    **item.diagnostics,
                    "source_owner": "lotus-manage-construction",
                    "required_action": "REVIEW_CONSTRUCTION_INPUTS",
                    "construction_error": type(exc).__name__,
                },
            },
            deep=True,
        )
    return item.model_copy(
        update={
            "state": "SIMULATED",
            "alternative_set_id": alternative_set.alternative_set_id,
            "reason_codes": ["CONSTRUCTION_ALTERNATIVES_GENERATED"],
            "diagnostics": {
                **item.diagnostics,
                "construction_state": alternative_set.status.value,
                "alternative_count": len(alternative_set.alternatives),
            },
        },
        deep=True,
    )


def _with_selection_and_proof_pack(
    *,
    item: DpmRebalanceWaveItem,
    alternative_id: str,
    actor_id: str,
    reason_code: str,
    comment: str | None,
    correlation_id: str,
    generate_proof_pack: bool,
    construction_repository: ConstructionRepository,
    proof_pack_repository: DpmProofPackRepository,
    mandate_repository: DpmMandateRepository,
    run_service: DpmRunSupportService,
) -> DpmRebalanceWaveItem:
    diagnostics = {
        **item.diagnostics,
        "selection_actor_id": actor_id,
        "selection_reason_code": reason_code,
    }
    if comment:
        diagnostics["selection_comment"] = comment
    if not generate_proof_pack:
        return item.model_copy(
            update={
                "state": "SELECTED",
                "selected_alternative_id": alternative_id,
                "reason_codes": ["CONSTRUCTION_ALTERNATIVE_SELECTED"],
                "diagnostics": {
                    **diagnostics,
                    "proof_pack_state": "DEGRADED",
                    "proof_pack_reason_code": "PROOF_PACK_GENERATION_NOT_REQUESTED",
                },
            },
            deep=True,
        )
    try:
        proof_pack = proof_pack_service.generate_proof_pack_from_selected_alternative(
            alternative_set_id=str(item.alternative_set_id),
            selected_alternative_id=alternative_id,
            actor_id=actor_id,
            reason=reason_code,
            correlation_id=correlation_id,
            mandate_id=item.mandate_id,
            idempotency_key=f"wave:{item.wave_item_id}:proof-pack:{alternative_id}",
            construction_repository=construction_repository,
            run_service=run_service,
            mandate_repository=mandate_repository,
            proof_pack_repository=proof_pack_repository,
        )
    except Exception as exc:
        return item.model_copy(
            update={
                "state": "SELECTED",
                "selected_alternative_id": alternative_id,
                "reason_codes": ["CONSTRUCTION_ALTERNATIVE_SELECTED"],
                "diagnostics": {
                    **diagnostics,
                    "proof_pack_state": "DEGRADED",
                    "proof_pack_reason_code": "PROOF_PACK_GENERATION_FAILED",
                    "proof_pack_error": type(exc).__name__,
                },
            },
            deep=True,
        )
    return item.model_copy(
        update={
            "state": "PROOF_PACK_READY",
            "selected_alternative_id": alternative_id,
            "proof_pack_id": proof_pack.proof_pack_id,
            "reason_codes": ["CONSTRUCTION_ALTERNATIVE_SELECTED", "PROOF_PACK_READY"],
            "diagnostics": {
                **diagnostics,
                "proof_pack_state": proof_pack.status,
            },
        },
        deep=True,
    )


def _approve_item(
    item: DpmRebalanceWaveItem,
    actor_id: str,
    reason_code: str,
    comment: str | None,
) -> DpmRebalanceWaveItem:
    if item.state not in {"SELECTED", "PROOF_PACK_READY"}:
        return item
    diagnostics = {
        **item.diagnostics,
        "approval_actor_id": actor_id,
        "approval_reason_code": reason_code,
    }
    if comment:
        diagnostics["approval_comment"] = comment
    return item.model_copy(
        update={
            "state": "APPROVED",
            "reason_codes": [*item.reason_codes, "WAVE_ITEM_APPROVED"],
            "diagnostics": diagnostics,
        },
        deep=True,
    )


def _stage_item(
    item: DpmRebalanceWaveItem,
    actor_id: str,
    reason_code: str,
    comment: str | None,
) -> DpmRebalanceWaveItem:
    if item.state != "APPROVED":
        return item
    diagnostics = {
        **item.diagnostics,
        "stage_actor_id": actor_id,
        "stage_reason_code": reason_code,
        "external_execution_claimed": False,
    }
    if comment:
        diagnostics["stage_comment"] = comment
    return item.model_copy(
        update={
            "state": "STAGED",
            "reason_codes": [*item.reason_codes, "WAVE_ITEM_STAGED"],
            "diagnostics": diagnostics,
        },
        deep=True,
    )


def _handoff_item(
    item: DpmRebalanceWaveItem,
    actor_id: str,
    reason_code: str,
    comment: str | None,
) -> DpmRebalanceWaveItem:
    if item.state != "STAGED":
        return item
    diagnostics = {
        **item.diagnostics,
        "handoff_actor_id": actor_id,
        "handoff_reason_code": reason_code,
        "external_execution_claimed": False,
    }
    if comment:
        diagnostics["handoff_comment"] = comment
    return item.model_copy(
        update={
            "state": "HANDOFF_READY",
            "reason_codes": [*item.reason_codes, "WAVE_ITEM_HANDOFF_READY"],
            "diagnostics": diagnostics,
        },
        deep=True,
    )


def _handoff_ref(
    *,
    wave_id: str,
    item_ids: list[str],
    actor_id: str,
    reason_code: str,
    correlation_id: str,
    comment: str | None,
) -> DpmWaveHandoffRef:
    handoff_ref_id = f"dwh_{uuid.uuid4().hex[:12]}"
    metadata: dict[str, object] = {
        "handoff_contract": "RFC-0041_INTERNAL_OPERATIONS_HANDOFF_V1",
        "handoff_boundary": "NO_EXTERNAL_EXECUTION",
        "item_count": len(item_ids),
    }
    if comment:
        metadata["comment"] = comment
    content_hash = _handoff_content_hash(
        {
            "handoff_ref_id": handoff_ref_id,
            "wave_id": wave_id,
            "item_ids": item_ids,
            "actor_id": actor_id,
            "reason_code": reason_code,
            "correlation_id": correlation_id,
            "external_execution_claimed": False,
            "metadata": metadata,
        }
    )
    return DpmWaveHandoffRef(
        handoff_ref_id=handoff_ref_id,
        wave_id=wave_id,
        item_ids=item_ids,
        actor_id=actor_id,
        reason_code=reason_code,
        correlation_id=correlation_id,
        external_execution_claimed=False,
        content_hash=content_hash,
        metadata=metadata,
    )


def _handoff_content_hash(payload: dict[str, object]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return f"sha256:{hashlib.sha256(canonical.encode()).hexdigest()}"


def _supportability_issue(
    *,
    wave_id: str,
    item: DpmRebalanceWaveItem,
    item_index: int,
) -> dict[str, object] | None:
    if item.state in {"APPROVED", "STAGED", "HANDOFF_READY", "PROOF_PACK_READY", "SIMULATED"}:
        if (
            item.state != "PROOF_PACK_READY"
            or item.diagnostics.get("proof_pack_state") != "DEGRADED"
        ):
            return None
    severity = _supportability_severity(item)
    if severity is None:
        return None
    reason_codes = item.reason_codes or [_supportability_reason(item)]
    return {
        "support_ref": f"wave:{wave_id}:item:{item_index}",
        "item_state": item.state,
        "severity": severity,
        "source_owner": _supportability_source_owner(item),
        "reason_codes": reason_codes,
        "remediation_route": _supportability_remediation(item),
    }


def _supportability_severity(item: DpmRebalanceWaveItem) -> str | None:
    if item.state in {"SOURCE_BLOCKED", "SIMULATION_BLOCKED"}:
        return "CRITICAL"
    if item.state in {"SOURCE_DEGRADED", "REVIEW_REQUIRED", "SELECTED"}:
        return "WARNING"
    if item.state == "PROOF_PACK_READY" and item.diagnostics.get("proof_pack_state") == "DEGRADED":
        return "WARNING"
    if item.state in {"CANDIDATE", "SOURCE_READY"}:
        return "INFO"
    return None


def _supportability_reason(item: DpmRebalanceWaveItem) -> str:
    reason_by_state = {
        "CANDIDATE": "SOURCE_CHECK_PENDING",
        "SOURCE_READY": "SIMULATION_PENDING",
        "SOURCE_DEGRADED": "SOURCE_DEGRADED",
        "REVIEW_REQUIRED": "REVIEW_REQUIRED",
        "SOURCE_BLOCKED": "SOURCE_BLOCKED",
        "SIMULATION_BLOCKED": "SIMULATION_BLOCKED",
        "SELECTED": "PROOF_PACK_PENDING_OR_DEGRADED",
        "PROOF_PACK_READY": "PROOF_PACK_DEGRADED",
    }
    return reason_by_state.get(item.state, "WAVE_ITEM_SUPPORTABILITY_REVIEW")


def _supportability_source_owner(item: DpmRebalanceWaveItem) -> str:
    owner = item.diagnostics.get("source_owner")
    if isinstance(owner, str) and owner:
        return owner
    if item.state in {"SOURCE_BLOCKED", "SOURCE_DEGRADED", "REVIEW_REQUIRED"}:
        return "lotus-manage"
    if item.state == "SIMULATION_BLOCKED":
        return "lotus-manage-construction"
    if item.state in {"SELECTED", "PROOF_PACK_READY"}:
        return "lotus-manage-proof-pack"
    return "lotus-manage"


def _supportability_remediation(item: DpmRebalanceWaveItem) -> str:
    explicit = item.diagnostics.get("required_action")
    if isinstance(explicit, str) and explicit:
        return explicit
    remediation_by_state = {
        "CANDIDATE": "RUN_SOURCE_CHECK",
        "SOURCE_READY": "RUN_WAVE_SIMULATION",
        "SOURCE_DEGRADED": "REFRESH_SOURCE_EVIDENCE",
        "REVIEW_REQUIRED": "PERFORM_HUMAN_REVIEW",
        "SOURCE_BLOCKED": "REPAIR_SOURCE_DATA",
        "SIMULATION_BLOCKED": "SUPPLY_VALID_RFC0039_CONSTRUCTION_INPUT",
        "SELECTED": "GENERATE_OR_REVIEW_PROOF_PACK",
        "PROOF_PACK_READY": "REVIEW_DEGRADED_PROOF_PACK",
    }
    return remediation_by_state.get(item.state, "REVIEW_WAVE_ITEM_SUPPORTABILITY")


def _operator_actions(*, state: str, issues: list[dict[str, object]]) -> list[str]:
    if state == "ready":
        return ["CONTINUE_GOVERNED_WAVE_WORKFLOW"]
    routes = {
        str(issue["remediation_route"])
        for issue in issues
        if isinstance(issue.get("remediation_route"), str)
    }
    return sorted(routes)


def _simulation_result_state(items: list[DpmRebalanceWaveItem]) -> WaveState:
    simulated = sum(1 for item in items if item.state == "SIMULATED")
    blocked = sum(1 for item in items if item.state == "SIMULATION_BLOCKED")
    if simulated and blocked:
        return "PARTIALLY_SIMULATED"
    if simulated:
        return "SIMULATED"
    return "SIMULATION_FAILED"


def _append_event(
    *,
    wave: DpmRebalanceWave,
    event: DpmRebalanceWaveEvent,
) -> DpmRebalanceWave:
    if event.wave_id != wave.wave_id:
        raise DpmWaveValidationError("DPM_WAVE_EVENT_WAVE_MISMATCH", "Wave event mismatch.")
    if event.from_state != wave.state or event.to_state != wave.state:
        raise DpmWaveValidationError("DPM_WAVE_EVENT_STATE_MISMATCH", "Wave event state mismatch.")
    return wave.model_copy(
        update={"version": wave.version + 1, "events": [*wave.events, event]},
        deep=True,
    )


def _build_item(
    *,
    index: int,
    portfolio: dict[str, object],
    mandate_repository: DpmMandateRepository,
) -> DpmRebalanceWaveItem:
    portfolio_id = str(portfolio["portfolio_id"]).strip()
    mandate_id = _optional_str(portfolio.get("mandate_id"))
    source_refs = _source_refs_from_portfolio(portfolio)
    latest_mandate = mandate_repository.get_latest_mandate_by_portfolio(portfolio_id=portfolio_id)
    if latest_mandate is not None:
        mandate_id = latest_mandate.mandate_id
        source_refs.append(
            DpmWaveSourceRef(
                source_system="lotus-manage",
                source_type="MANDATE_DIGITAL_TWIN",
                source_id=latest_mandate.mandate_id,
                source_version=latest_mandate.mandate_version,
                supportability_state="READY",
            )
        )

    if source_refs:
        state: WaveItemState = "CANDIDATE"
        reason_codes = ["AFFECTED_PORTFOLIO_SOURCE_READY"]
        diagnostics = {"source_posture": "candidate_evidence_available"}
    else:
        state = "SOURCE_BLOCKED"
        reason_codes = ["MISSING_AFFECTED_PORTFOLIO_SOURCE"]
        diagnostics = {
            "source_owner": "caller_or_lotus-core",
            "required_action": "SUPPLY_SOURCE_REF",
        }

    return DpmRebalanceWaveItem(
        wave_item_id=f"dwi_{index:03d}_{uuid.uuid4().hex[:8]}",
        portfolio_id=portfolio_id,
        mandate_id=mandate_id,
        state=state,
        reason_codes=reason_codes,
        source_refs=source_refs,
        diagnostics=diagnostics,
    )


def _classify_item_source_readiness(
    *,
    item: DpmRebalanceWaveItem,
    wave_as_of_date: str,
    mandate_repository: DpmMandateRepository,
) -> DpmRebalanceWaveItem:
    twin = _resolve_mandate_twin(item=item, mandate_repository=mandate_repository)
    health = (
        mandate_repository.get_latest_health_snapshot(mandate_id=twin.mandate_id)
        if twin is not None
        else None
    )
    return classify_wave_item_source_readiness(
        item=item,
        wave_as_of_date=wave_as_of_date,
        mandate_twin=twin,
        mandate_health=health,
    )


def _resolve_mandate_twin(
    *,
    item: DpmRebalanceWaveItem,
    mandate_repository: DpmMandateRepository,
) -> DpmMandateDigitalTwin | None:
    if item.mandate_id:
        twin = mandate_repository.get_latest_mandate(mandate_id=item.mandate_id)
        if twin is not None and twin.portfolio_id == item.portfolio_id:
            return twin
    return mandate_repository.get_latest_mandate_by_portfolio(portfolio_id=item.portfolio_id)


def _aggregate(items: list[DpmRebalanceWaveItem]) -> DpmWaveAggregateMetrics:
    state_counts = Counter(item.state for item in items)
    state_count_map = {str(state): count for state, count in state_counts.items()}
    return DpmWaveAggregateMetrics(
        item_count=len(items),
        state_counts=state_count_map,
        ready_item_count=state_counts.get("SOURCE_READY", 0)
        + state_counts.get("SIMULATED", 0)
        + state_counts.get("SELECTED", 0)
        + state_counts.get("PROOF_PACK_READY", 0)
        + state_counts.get("APPROVED", 0)
        + state_counts.get("STAGED", 0)
        + state_counts.get("HANDOFF_READY", 0),
        blocked_item_count=state_counts.get("SOURCE_BLOCKED", 0)
        + state_counts.get("SIMULATION_BLOCKED", 0),
        review_required_item_count=state_counts.get("REVIEW_REQUIRED", 0),
        source_degraded_item_count=state_counts.get("SOURCE_DEGRADED", 0),
    )


def _trigger_source_refs(portfolios: list[dict[str, object]]) -> list[DpmWaveSourceRef]:
    refs: list[DpmWaveSourceRef] = []
    for portfolio in portfolios:
        refs.extend(_source_refs_from_portfolio(portfolio))
    return refs


def _source_refs_from_portfolio(portfolio: dict[str, object]) -> list[DpmWaveSourceRef]:
    source_refs = portfolio.get("source_refs", [])
    if not isinstance(source_refs, list):
        return []
    return [
        DpmWaveSourceRef.model_validate(source_ref)
        for source_ref in source_refs
        if isinstance(source_ref, dict)
    ]


def _event(
    *,
    wave_id: str,
    from_state: WaveState,
    to_state: WaveState,
    actor_id: str,
    correlation_id: str,
    reason_code: str,
    metadata: dict[str, object],
    event_type: str = "STATE_TRANSITION",
) -> DpmRebalanceWaveEvent:
    return DpmRebalanceWaveEvent(
        event_id=f"dwe_{uuid.uuid4().hex[:12]}",
        wave_id=wave_id,
        from_state=from_state,
        to_state=to_state,
        event_type=event_type,
        actor_id=actor_id,
        reason_code=reason_code,
        correlation_id=correlation_id,
        metadata=metadata,
    )


def _validate_trigger(trigger_type: str) -> None:
    if trigger_type not in SUPPORTED_CREATE_TRIGGER_TYPES:
        raise DpmWaveValidationError(
            "NOT_SUPPORTED_TRIGGER",
            f"Trigger type {trigger_type} is not supported for RFC-0041 Slice 4.",
        )


def _request_hash(payload: dict[str, object]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return f"sha256:{hashlib.sha256(canonical.encode()).hexdigest()}"


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
