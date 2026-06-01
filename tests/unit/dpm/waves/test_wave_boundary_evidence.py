from src.api.services.wave_boundary_evidence import (
    client_communication_boundary,
    external_execution_boundary,
)


def test_external_execution_boundary_blocks_until_execution_owner_exists() -> None:
    boundary = external_execution_boundary(external_execution_claimed=False)

    assert boundary.boundary_id == "DPM_WAVE_EXTERNAL_EXECUTION_BOUNDARY"
    assert boundary.supportability_state == "BLOCKED"
    assert boundary.external_execution_claimed is False
    assert boundary.reason_code == "NO_EXTERNAL_EXECUTION_OWNER"
    assert boundary.required_source_product == "ExternalOrderExecutionAcknowledgement:v1"
    assert "best_execution" in boundary.blocked_capabilities
    assert boundary.content_hash.startswith("sha256:")


def test_external_execution_boundary_marks_unsafe_execution_claim() -> None:
    boundary = external_execution_boundary(external_execution_claimed=True)

    assert boundary.external_execution_claimed is True
    assert boundary.reason_code == "UNSAFE_EXTERNAL_EXECUTION_CLAIM"
    assert "unsafe external execution claim" in boundary.summary


def test_client_communication_boundary_blocks_projection_without_source_owner() -> None:
    boundary = client_communication_boundary()

    assert boundary.boundary_id == "DPM_WAVE_CLIENT_COMMUNICATION_BOUNDARY"
    assert boundary.supportability_state == "BLOCKED"
    assert boundary.client_communication_projected is False
    assert boundary.client_approval_projected is False
    assert boundary.reason_code == "WAVE_CLIENT_COMMUNICATION_NOT_SUPPORTED"
    assert boundary.required_source_product == "ClientCommunicationRecord:v1"
    assert "client_approval" in boundary.blocked_capabilities
    assert boundary.content_hash.startswith("sha256:")
