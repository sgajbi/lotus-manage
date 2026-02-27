from src.core.common.canonical import hash_canonical_payload, strip_keys
from src.core.dpm_runs.models import (
    DpmRunArtifactEvidence,
    DpmRunArtifactHashes,
    DpmRunArtifactResponse,
    DpmRunRecord,
)
from src.core.models import RebalanceResult

ARTIFACT_VERSION = "1.0"


def build_dpm_run_artifact(*, run: DpmRunRecord) -> DpmRunArtifactResponse:
    result = RebalanceResult.model_validate(run.result_json)
    base_payload = DpmRunArtifactResponse(
        artifact_id=run.rebalance_run_id.replace("rr_", "dra_", 1),
        artifact_version=ARTIFACT_VERSION,
        rebalance_run_id=run.rebalance_run_id,
        correlation_id=run.correlation_id,
        idempotency_key=run.idempotency_key,
        portfolio_id=run.portfolio_id,
        status=result.status,
        request_snapshot={
            "portfolio_id": run.portfolio_id,
            "request_hash": run.request_hash,
        },
        before_summary=result.before.model_dump(mode="json"),
        after_summary=result.after_simulated.model_dump(mode="json"),
        order_intents=[intent.model_dump(mode="json") for intent in result.intents],
        rule_outcomes=[rule.model_dump(mode="json") for rule in result.rule_results],
        diagnostics=result.diagnostics.model_dump(mode="json"),
        result=result,
        evidence=DpmRunArtifactEvidence(
            engine_version=result.lineage.engine_version or "unknown",
            run_created_at=run.created_at.isoformat(),
            hashes=DpmRunArtifactHashes(
                request_hash=run.request_hash,
                artifact_hash="",
            ),
        ),
    )
    payload = base_payload.model_dump(mode="json")
    canonical_payload = strip_keys(payload, exclude={"artifact_hash"})
    payload["evidence"]["hashes"]["artifact_hash"] = hash_canonical_payload(canonical_payload)
    return DpmRunArtifactResponse.model_validate(payload)
