# Security and Governance

## Current governance

- RFC-0066
  `lotus-advise` and `lotus-manage` split boundary
- RFC-0067
  centralized OpenAPI and vocabulary governance
- RFC-0071
  environment-scoped service addressing and ingress posture
- RFC-0072
  multi-lane CI and release governance
- RFC-0073
  ecosystem context and agent guidance system
- RFC-0082
  upstream authority and analytics serving boundary hardening

## Repo-specific guardrails

- no-alias contract guard is active
- OpenAPI quality gate is active
- API vocabulary inventory validation is active
- migration smoke is part of the repo-native PR-grade contract
- security audit is part of `make ci`

## Operational discipline

- keep management and advisory boundaries explicit
- do not let gateway or UI infer capability truth that the backend already publishes
- keep generated artifacts truthful and avoid timestamp-only churn in docs slices
