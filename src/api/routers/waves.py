from __future__ import annotations

from fastapi import APIRouter

from src.api.routers.wave_campaign_definition_routes import (
    detail_router as campaign_definition_detail_router,
    router as campaign_definition_router,
)
from src.api.routers.wave_campaign_definition_lifecycle_routes import (
    router as campaign_definition_lifecycle_router,
)
from src.api.routers.wave_campaign_approval_decision_evidence_routes import (
    router as campaign_approval_decision_router,
)
from src.api.routers.wave_campaign_assignment_action_evidence_routes import (
    router as campaign_assignment_action_router,
)
from src.api.routers.wave_campaign_assignment_task_evidence_routes import (
    router as campaign_assignment_task_router,
)
from src.api.routers.wave_campaign_maker_checker_evidence_routes import (
    router as campaign_maker_checker_router,
)
from src.api.routers.wave_campaign_launch_routes import (
    router as campaign_launch_router,
)
from src.api.routers.wave_campaign_launch_package_routes import (
    router as campaign_launch_package_router,
)
from src.api.routers.wave_campaign_audit_read_routes import (
    router as campaign_audit_read_router,
)
from src.api.routers.wave_campaign_read_model_routes import (
    router as campaign_read_model_router,
)
from src.api.routers.wave_campaign_readiness_routes import (
    router as campaign_readiness_router,
)
from src.api.routers.wave_campaign_workflow_overview_routes import (
    router as campaign_workflow_overview_router,
)
from src.api.routers.wave_create_preview_routes import register_wave_create_preview_routes
from src.api.routers.wave_source_check_routes import (
    router as source_check_router,
)
from src.api.routers.wave_simulation_routes import (
    router as simulation_router,
)
from src.api.routers.wave_selection_routes import (
    router as selection_router,
)
from src.api.routers.wave_workflow_routes import (
    router as workflow_router,
)
from src.api.routers.wave_read_routes import register_wave_read_routes
from src.api.routers.wave_read_support_routes import (
    router as wave_read_support_router,
)
from src.api.services.rebalance_simulation_service import build_core_resolver_client

router = APIRouter(prefix="/rebalance/waves", tags=["lotus-manage Rebalance Waves"])

router.include_router(campaign_definition_router)
router.include_router(campaign_definition_lifecycle_router)
router.include_router(campaign_read_model_router)
router.include_router(campaign_definition_detail_router)
router.include_router(campaign_approval_decision_router)
router.include_router(campaign_assignment_action_router)
router.include_router(campaign_assignment_task_router)
router.include_router(campaign_maker_checker_router)
router.include_router(campaign_audit_read_router)
router.include_router(campaign_workflow_overview_router)
router.include_router(campaign_readiness_router)
router.include_router(campaign_launch_package_router)
router.include_router(campaign_launch_router)
register_wave_create_preview_routes(
    router,
    core_resolver_factory_provider=lambda: build_core_resolver_client,
)
register_wave_read_routes(router)


router.include_router(source_check_router)
router.include_router(simulation_router)
router.include_router(selection_router)
router.include_router(workflow_router)
router.include_router(wave_read_support_router)
