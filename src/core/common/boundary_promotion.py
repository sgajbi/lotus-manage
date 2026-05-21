"""Shared promotion requirements for unsupported external source-owner boundaries."""

EXTERNAL_EXECUTION_PROMOTION_REQUIREMENTS = [
    "certified_execution_oms_source_owner",
    "ExternalOrderExecutionAcknowledgement:v1",
    "source_product_contract",
    "producer_lineage_and_freshness_controls",
    "acknowledgement_fill_settlement_reconciliation_controls",
    "manage_consumer_declaration",
    "gateway_bff_realization",
    "workbench_gateway_only_realization",
    "operations_audit_and_exception_reconciliation_evidence",
]

CLIENT_COMMUNICATION_PROMOTION_REQUIREMENTS = [
    "certified_client_communication_source_owner",
    "ClientCommunicationRecord:v1",
    "source_product_contract",
    "producer_lineage_and_freshness_controls",
    "delivery_approval_and_audit_reconciliation_controls",
    "manage_consumer_declaration",
    "gateway_bff_realization",
    "workbench_gateway_only_realization",
    "client_communication_consent_and_evidence_controls",
]
