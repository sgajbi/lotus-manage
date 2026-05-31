from __future__ import annotations

from fastapi import APIRouter

from src.api.routers.wave_campaign_approval_decision_evidence_routes import (
    router as approval_decision_router,
)
from src.api.routers.wave_campaign_assignment_action_evidence_routes import (
    router as assignment_action_router,
)
from src.api.routers.wave_campaign_assignment_task_evidence_routes import (
    router as assignment_task_router,
)
from src.api.routers.wave_campaign_maker_checker_evidence_routes import (
    router as maker_checker_router,
)


router = APIRouter(tags=["lotus-manage Rebalance Waves"])
router.include_router(approval_decision_router)
router.include_router(assignment_action_router)
router.include_router(assignment_task_router)
router.include_router(maker_checker_router)
