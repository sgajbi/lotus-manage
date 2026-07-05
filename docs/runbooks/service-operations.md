# Service Operations Runbook

## Standard Commands

- make lint
- make typecheck
- make ci
- docker compose up --build

## Health and Readiness

- Liveness: `/health/live` returns `{"status":"live"}` and does not touch persistence dependencies.
- Readiness: `/health/ready` returns `{"status":"ready"}` after persistence guardrails pass; in
  production profile it also validates required cutover migrations.
- General health: `/health` returns `{"status":"ok"}` for lightweight service health checks.
- Health probes are infrastructure endpoints and intentionally remain unversioned.
- OpenAPI docs: `/docs`

## Incident First Checks

1. Check container logs for request failures and stack traces.
2. Verify `/health/ready` and metrics endpoint.
3. Run local parity check (`make ci`) before hotfix PR.

## Campaign Workflow Recovery

- Use `wiki/Operations-Runbook.md` as the canonical operator-facing campaign workflow runbook.
- Diagnose campaign launch, approval-decision, assignment-action, assignment-task,
  maker-checker-control, workflow-board, assignment-plan, workflow-automation, and launch-history
  incidents through the public campaign routes before inspecting persistence stores.
- Retry-safe paths are bounded by deterministic launch idempotency, conflict-safe evidence refs,
  and campaign definition content-hash protection. Manual database edits are not the normal
  campaign workflow recovery mechanism.
- For default workflow-board and assignment-plan filter drift, compare public route output with the
  `dpm_bulk_review_campaign_workflow_read_model` projection. The projection is rebuildable from
  `dpm_bulk_review_campaign_definitions.payload_json`; do not hand-edit projection rows as durable
  truth.
- Preserve no-claim boundaries in incident notes: no OMS/order routing, no client contact, no
  external workflow orchestration, and no raw portfolio/client/actor/idempotency/correlation
  identifiers in logs, metrics, screenshots, or public incident summaries.
