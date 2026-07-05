CREATE TABLE IF NOT EXISTS dpm_bulk_review_campaign_workflow_read_model (
    campaign_id TEXT NOT NULL,
    campaign_version TEXT NOT NULL,
    definition_status TEXT NOT NULL,
    as_of_date TEXT NOT NULL,
    definition_content_hash TEXT NOT NULL,
    workflow_read_model_hash TEXT NOT NULL,
    board_status TEXT NOT NULL,
    next_action TEXT NOT NULL,
    assignment_escalation_tier TEXT NOT NULL,
    assignment_sla_posture TEXT NOT NULL,
    assigned_actor_ids TEXT[] NOT NULL DEFAULT '{}',
    assignment_task_statuses TEXT[] NOT NULL DEFAULT '{}',
    assignment_task_escalation_tiers TEXT[] NOT NULL DEFAULT '{}',
    assignment_task_sla_postures TEXT[] NOT NULL DEFAULT '{}',
    maker_checker_outcomes TEXT[] NOT NULL DEFAULT '{}',
    approval_decision_types TEXT[] NOT NULL DEFAULT '{}',
    approval_decision_count INTEGER NOT NULL DEFAULT 0,
    assignment_action_count INTEGER NOT NULL DEFAULT 0,
    assignment_task_count INTEGER NOT NULL DEFAULT 0,
    assignment_task_transition_count INTEGER NOT NULL DEFAULT 0,
    maker_checker_control_count INTEGER NOT NULL DEFAULT 0,
    projection_payload_json JSONB NOT NULL,
    projected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (campaign_id, campaign_version),
    FOREIGN KEY (campaign_id, campaign_version)
        REFERENCES dpm_bulk_review_campaign_definitions (campaign_id, campaign_version)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_dpm_bulk_review_campaign_workflow_board_status
    ON dpm_bulk_review_campaign_workflow_read_model (board_status);

CREATE INDEX IF NOT EXISTS idx_dpm_bulk_review_campaign_workflow_next_action
    ON dpm_bulk_review_campaign_workflow_read_model (next_action);

CREATE INDEX IF NOT EXISTS idx_dpm_bulk_review_campaign_workflow_assignment_tier
    ON dpm_bulk_review_campaign_workflow_read_model (assignment_escalation_tier);

CREATE INDEX IF NOT EXISTS idx_dpm_bulk_review_campaign_workflow_assignment_sla
    ON dpm_bulk_review_campaign_workflow_read_model (assignment_sla_posture);

CREATE INDEX IF NOT EXISTS idx_dpm_bulk_review_campaign_workflow_task_statuses
    ON dpm_bulk_review_campaign_workflow_read_model USING GIN (assignment_task_statuses);

CREATE INDEX IF NOT EXISTS idx_dpm_bulk_review_campaign_workflow_assigned_actors
    ON dpm_bulk_review_campaign_workflow_read_model USING GIN (assigned_actor_ids);

CREATE INDEX IF NOT EXISTS idx_dpm_bulk_review_campaign_workflow_maker_checker
    ON dpm_bulk_review_campaign_workflow_read_model USING GIN (maker_checker_outcomes);

INSERT INTO dpm_bulk_review_campaign_workflow_read_model (
    campaign_id,
    campaign_version,
    definition_status,
    as_of_date,
    definition_content_hash,
    workflow_read_model_hash,
    board_status,
    next_action,
    assignment_escalation_tier,
    assignment_sla_posture,
    assigned_actor_ids,
    assignment_task_statuses,
    assignment_task_escalation_tiers,
    assignment_task_sla_postures,
    maker_checker_outcomes,
    approval_decision_types,
    approval_decision_count,
    assignment_action_count,
    assignment_task_count,
    assignment_task_transition_count,
    maker_checker_control_count,
    projection_payload_json
)
SELECT
    campaign_id,
    campaign_version,
    status,
    as_of_date,
    content_hash,
    content_hash,
    CASE WHEN status = 'ACTIVE' THEN 'ATTENTION_FOR_ACTOR' ELSE 'CLOSED' END,
    CASE WHEN status = 'ACTIVE' THEN 'REVIEW_CAMPAIGN_ATTENTION' ELSE 'NO_ACTION_CLOSED' END,
    'OPS',
    'ATTENTION',
    COALESCE(
        ARRAY(
            SELECT DISTINCT actor_id
            FROM jsonb_array_elements(COALESCE(payload_json -> 'assignment_tasks', '[]'::jsonb)) task,
                 jsonb_array_elements_text(COALESCE(task -> 'assigned_actor_ids', '[]'::jsonb)) AS actor_ids(actor_id)
            WHERE actor_id <> ''
            ORDER BY actor_id
        ),
        '{}'::TEXT[]
    ),
    COALESCE(
        ARRAY(
            SELECT DISTINCT task ->> 'status'
            FROM jsonb_array_elements(COALESCE(payload_json -> 'assignment_tasks', '[]'::jsonb)) task
            WHERE COALESCE(task ->> 'status', '') <> ''
            ORDER BY task ->> 'status'
        ),
        '{}'::TEXT[]
    ),
    COALESCE(
        ARRAY(
            SELECT DISTINCT task ->> 'escalation_tier'
            FROM jsonb_array_elements(COALESCE(payload_json -> 'assignment_tasks', '[]'::jsonb)) task
            WHERE COALESCE(task ->> 'escalation_tier', '') <> ''
            ORDER BY task ->> 'escalation_tier'
        ),
        '{}'::TEXT[]
    ),
    COALESCE(
        ARRAY(
            SELECT DISTINCT task ->> 'sla_posture'
            FROM jsonb_array_elements(COALESCE(payload_json -> 'assignment_tasks', '[]'::jsonb)) task
            WHERE COALESCE(task ->> 'sla_posture', '') <> ''
            ORDER BY task ->> 'sla_posture'
        ),
        '{}'::TEXT[]
    ),
    COALESCE(
        ARRAY(
            SELECT DISTINCT control ->> 'control_outcome'
            FROM jsonb_array_elements(COALESCE(payload_json -> 'maker_checker_controls', '[]'::jsonb)) control
            WHERE COALESCE(control ->> 'control_outcome', '') <> ''
            ORDER BY control ->> 'control_outcome'
        ),
        '{}'::TEXT[]
    ),
    COALESCE(
        ARRAY(
            SELECT DISTINCT decision ->> 'decision_type'
            FROM jsonb_array_elements(COALESCE(payload_json -> 'approval_decisions', '[]'::jsonb)) decision
            WHERE COALESCE(decision ->> 'decision_type', '') <> ''
            ORDER BY decision ->> 'decision_type'
        ),
        '{}'::TEXT[]
    ),
    jsonb_array_length(COALESCE(payload_json -> 'approval_decisions', '[]'::jsonb)),
    jsonb_array_length(COALESCE(payload_json -> 'assignment_actions', '[]'::jsonb)),
    jsonb_array_length(COALESCE(payload_json -> 'assignment_tasks', '[]'::jsonb)),
    (
        SELECT COALESCE(SUM(jsonb_array_length(COALESCE(task -> 'transitions', '[]'::jsonb))), 0)::INTEGER
        FROM jsonb_array_elements(COALESCE(payload_json -> 'assignment_tasks', '[]'::jsonb)) task
    ),
    jsonb_array_length(COALESCE(payload_json -> 'maker_checker_controls', '[]'::jsonb)),
    jsonb_build_object(
        'projection_source', 'migration-backfill',
        'definition_content_hash', content_hash,
        'projection_owner', 'lotus-manage',
        'durable_source_table', 'dpm_bulk_review_campaign_definitions'
    )
FROM dpm_bulk_review_campaign_definitions
ON CONFLICT (campaign_id, campaign_version) DO NOTHING;
