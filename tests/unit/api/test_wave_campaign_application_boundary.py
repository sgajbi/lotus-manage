from __future__ import annotations

from pathlib import Path


def test_campaign_definition_routes_depend_on_application_service_boundary() -> None:
    route_paths = [
        Path("src/api/routers/wave_campaign_definition_routes.py"),
        Path("src/api/routers/wave_campaign_definition_lifecycle_routes.py"),
        Path("src/api/routers/wave_campaign_readiness_routes.py"),
        Path("src/api/routers/wave_campaign_discovery_routes.py"),
        Path("src/api/routers/wave_campaign_operating_queue_routes.py"),
        Path("src/api/routers/wave_campaign_approval_inbox_routes.py"),
        Path("src/api/routers/wave_campaign_workflow_board_routes.py"),
        Path("src/api/routers/wave_campaign_assignment_plan_routes.py"),
        Path("src/api/routers/wave_campaign_workflow_automation_routes.py"),
        Path("src/api/routers/wave_campaign_workflow_overview_routes.py"),
        Path("src/api/routers/wave_campaign_launch_package_routes.py"),
        Path("src/api/routers/wave_campaign_launch_routes.py"),
        Path("src/api/routers/wave_campaign_audit_read_routes.py"),
        Path("src/api/routers/wave_campaign_approval_decision_evidence_routes.py"),
        Path("src/api/routers/wave_campaign_assignment_action_evidence_routes.py"),
        Path("src/api/routers/wave_campaign_assignment_task_evidence_routes.py"),
        Path("src/api/routers/wave_campaign_maker_checker_evidence_routes.py"),
    ]

    for route_path in route_paths:
        source = route_path.read_text(encoding="utf-8")
        assert "get_wave_campaign_application_service" in source
        assert "get_campaign_definition_repository" not in source
        assert "DpmBulkReviewCampaignDefinitionRepository" not in source


def test_obsolete_campaign_http_helpers_are_removed() -> None:
    helper_paths = [
        Path("src/api/routers/wave_campaign_approval_decision_http.py"),
        Path("src/api/routers/wave_campaign_assignment_action_http.py"),
        Path("src/api/routers/wave_campaign_assignment_task_http.py"),
        Path("src/api/routers/wave_campaign_audit_read_http.py"),
        Path("src/api/routers/wave_campaign_definition_lifecycle_http.py"),
        Path("src/api/routers/wave_campaign_definition_read_http.py"),
        Path("src/api/routers/wave_campaign_definition_write_http.py"),
        Path("src/api/routers/wave_campaign_launch_package_http.py"),
        Path("src/api/routers/wave_campaign_maker_checker_http.py"),
        Path("src/api/routers/wave_campaign_preview_readiness_http.py"),
        Path("src/api/routers/wave_campaign_read_model_query.py"),
        Path("src/api/routers/wave_campaign_workflow_overview_http.py"),
    ]

    for helper_path in helper_paths:
        assert not helper_path.exists(), f"{helper_path} should not be revived"
