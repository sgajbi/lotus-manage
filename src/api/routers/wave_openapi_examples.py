from __future__ import annotations

from typing import cast


WAVE_EXAMPLE = {
    "wave": {
        "wave_id": "dwv_001",
        "wave_version": "1.0.0",
        "state": "PREVIEWED",
        "trigger": {
            "trigger_type": "EXPLICIT_PORTFOLIO_LIST",
            "trigger_id": "manual-wave-20260503-001",
            "rationale": "Review explicitly selected portfolios after model drift triage.",
            "source_refs": [],
        },
        "as_of_date": "2026-05-03",
        "created_at": "2026-05-03T09:30:00Z",
        "created_by": "pm_001",
        "correlation_id": "corr-wave-001",
        "version": 2,
        "items": [
            {
                "wave_item_id": "dwi_001",
                "portfolio_id": "PB_SG_GLOBAL_BAL_001",
                "mandate_id": "MANDATE_PB_SG_GLOBAL_BAL_001",
                "state": "CANDIDATE",
                "reason_codes": ["AFFECTED_PORTFOLIO_SOURCE_READY"],
                "source_refs": [
                    {
                        "source_system": "lotus-manage",
                        "source_type": "AFFECTED_PORTFOLIO_MANIFEST",
                        "source_id": "manifest_20260503_001",
                        "source_version": "1.0.0",
                        "supportability_state": "READY",
                        "content_hash": "sha256:manifest-example",
                    }
                ],
                "diagnostics": {"source_posture": "candidate_evidence_available"},
            }
        ],
        "aggregate_metrics": {
            "item_count": 1,
            "state_counts": {"CANDIDATE": 1},
            "ready_item_count": 0,
            "blocked_item_count": 0,
            "review_required_item_count": 0,
            "source_degraded_item_count": 0,
        },
        "events": [],
        "retention_policy": "DPM_WAVE_STANDARD",
    },
    "durable": False,
    "idempotent_replay": False,
}

SOURCE_CHECK_WAVE_EXAMPLE = {
    "wave": {
        **cast(dict[str, object], WAVE_EXAMPLE["wave"]),
        "state": "SOURCE_CHECKED",
        "version": 4,
        "items": [
            {
                "wave_item_id": "dwi_001",
                "portfolio_id": "PB_SG_GLOBAL_BAL_001",
                "mandate_id": "MANDATE_PB_SG_GLOBAL_BAL_001",
                "model_portfolio_id": "MODEL_PB_SG_GLOBAL_BAL_DPM",
                "state": "SOURCE_READY",
                "reason_codes": ["SOURCE_READINESS_READY"],
                "source_refs": [
                    {
                        "source_system": "lotus-manage",
                        "source_type": "MANDATE_DIGITAL_TWIN",
                        "source_id": "MANDATE_PB_SG_GLOBAL_BAL_001",
                        "source_version": "3",
                        "supportability_state": "READY",
                    },
                    {
                        "source_system": "lotus-manage",
                        "source_type": "DPM_MANDATE_HEALTH_SNAPSHOT",
                        "source_id": "mh_20260503_pb_sg_global_bal_001",
                        "source_version": "2026-05-03",
                        "supportability_state": "READY",
                    },
                    {
                        "source_system": "lotus-manage",
                        "source_type": "DPM_SOURCE_READINESS",
                        "source_id": "mh_20260503_pb_sg_global_bal_001",
                        "source_version": "2026-05-03",
                        "supportability_state": "READY",
                    },
                ],
                "diagnostics": {
                    "source_owner": "lotus-manage",
                    "health_state": "READY",
                    "source_readiness_state": "READY",
                },
            }
        ],
        "aggregate_metrics": {
            "item_count": 1,
            "state_counts": {"SOURCE_READY": 1},
            "ready_item_count": 1,
            "blocked_item_count": 0,
            "review_required_item_count": 0,
            "source_degraded_item_count": 0,
        },
    },
    "durable": True,
    "idempotent_replay": False,
}
