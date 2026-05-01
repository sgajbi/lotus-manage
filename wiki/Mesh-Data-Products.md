# Mesh Data Products

## Mesh role

`lotus-manage` is a maturity-wave producer in the Lotus enterprise data mesh.

## Governed product

- Product ID: `lotus-manage:PortfolioActionRegister:v1`
- Product role: governed portfolio action register for management, reporting, gateway, and
  Workbench discovery flows
- Implemented route families:
  - `/api/v1/rebalance/supportability/summary`
  - `/api/v1/rebalance/runs/{rebalance_run_id}/artifact`
  - `/api/v1/rebalance/runs/{rebalance_run_id}/workflow`
  - `/api/v1/rebalance/workflow/decisions`
- Source declaration: `contracts/domain-data-products/lotus-manage-products.v1.json`
- Trust telemetry: `contracts/trust-telemetry/portfolio-action-register.telemetry.v1.json`

## Platform relationship

`lotus-platform` aggregates the repo-native declaration, validates trust telemetry, applies mesh SLO/access/evidence policies, and includes this product in generated catalog, dependency graph, live certification, maturity matrix, evidence packs, and RFC-0092 operating reports.

## Operating rule

Portfolio action state and lifecycle evidence belong in `lotus-manage`. Platform certification can block publication when action-register telemetry, lifecycle, access, SLO, or evidence posture drifts.

Stateful `portfolio_id` execution is not yet a promoted mesh consumption mode. The resolver seam is
implemented, but live source-data dependency declaration waits for `sgajbi/lotus-core#330` or an
equivalent certified DPM execution-context source-data product.
