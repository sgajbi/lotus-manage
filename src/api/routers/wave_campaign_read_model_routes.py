from __future__ import annotations

from fastapi import APIRouter

from src.api.routers.wave_campaign_approval_inbox_routes import (
    router as approval_inbox_router,
)
from src.api.routers.wave_campaign_assignment_plan_routes import (
    router as assignment_plan_router,
)
from src.api.routers.wave_campaign_discovery_routes import router as discovery_router
from src.api.routers.wave_campaign_operating_queue_routes import (
    router as operating_queue_router,
)
from src.api.routers.wave_campaign_workflow_board_routes import (
    router as workflow_board_router,
)
from src.api.routers.wave_campaign_workflow_automation_routes import (
    router as workflow_automation_router,
)


router = APIRouter(tags=["lotus-manage Rebalance Waves"])


router.include_router(discovery_router)
router.include_router(operating_queue_router)
router.include_router(approval_inbox_router)
router.include_router(workflow_board_router)
router.include_router(assignment_plan_router)
router.include_router(workflow_automation_router)
