# Development Workflow

## Branching and slice model

- branch from `main`
- keep one branch per RFC or documentation slice
- use PR-first delivery
- before RFC tightening, implementation start, final closure, post-merge audit, or moving to the
  next RFC, run stranded-truth reconciliation:
  `git fetch origin --prune` and `git branch -r --no-merged origin/main`
- classify every unmerged branch that touches RFC, wiki, README, context, AGENTS, contracts,
  standards, OpenAPI/vocabulary, migrations, CI workflows, or supported-features truth as
  `must-merge`, `cherry-pick`, `superseded`, `delete`, or `active`
- do not claim RFC closure while durable truth exists only on an unmerged side branch

## Repo-native commands

- `make check`
  fast local gate
- `make ci`
  PR-grade local proof
- `make ci-local`
  split local merge-gate flow
- `make ci-local-docker`
  Docker parity

## Documentation workflow

- keep `README.md` concise and operator-facing
- keep `wiki/` as the authored wiki source
- keep deep implementation detail in `docs/`
- inspect generated API vocabulary diffs before committing docs-only slices
- index durable control artifacts such as RFC ledgers and pin them with docs/current-state tests
  when a test pack exists
