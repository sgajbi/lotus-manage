# Development Workflow

## Branching and slice model

- branch from `main`
- keep one branch per RFC or documentation slice
- use PR-first delivery

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
