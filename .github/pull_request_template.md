## Summary
- 

## Why
- 

## Scope
- [ ] Single RFC/slice scope
- [ ] No unrelated refactors mixed in

## Risk / Rollback
- Risk:
- Rollback:

## Validation Evidence
- Static/local gate: [ ] `make check`
- PR-grade local gate: [ ] `make ci`
- Local PR parity gate: [ ] `make ci-local`
- Workflow policy: [ ] `make workflow-policy-gate`
- Quality report freshness: [ ] `make quality-report-gate`
- Test-family inventory: [ ] `make test-family-inventory`
- Duplicate implementation gate: [ ] `make duplicate-implementation-gate`
- Coverage gate: [ ] `make coverage-gate`
- OpenAPI contract: [ ] `make openapi-gate`
- API vocabulary: [ ] `make api-vocabulary-gate`
- No-alias contract: [ ] `make no-alias-gate`
- Security audit: [ ] `make security-audit`
- Targeted tests for changed area:

## CI Expectations
- [ ] Remote Feature Lane is green
- [ ] Pull Request Merge Gate is green
- [ ] Main Releasability is green or explicitly scheduled/manual for this change class
- [ ] Heavy gates run in scheduled/manual tier where applicable

## Governance/Docs
- [ ] RFC/docs updated where behavior or standards changed
- [ ] API/OpenAPI/vocabulary updates included if contract changed
- [ ] Stranded truth reconciliation run: `git fetch origin --prune`
- [ ] Stranded truth reconciliation run: `git branch -r --no-merged origin/main`
- [ ] Unmerged governance-bearing branches classified or none found
- Wiki decision:
- Guidance decision:

## Post-Merge Hygiene
- [ ] Delete remote feature branch
- [ ] Delete local feature branch
- [ ] Sync local main with origin/main (`local = remote = main`)
