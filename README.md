# Lotus Manage

Discretionary portfolio management (lotus-manage) execution, supportability, and lifecycle service.

Repository-local engineering context: `REPOSITORY-ENGINEERING-CONTEXT.md`

This repository owns lotus-manage runtime workflows.
Advisor-led proposal workflows are owned by `lotus-advise`.

API docs endpoint: `/docs`

Canonical local host runtime:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/Start-CanonicalManage.ps1
```

This starts `lotus-manage` on host port `8001` so it can coexist with `lotus-advise` on `8000`
while remaining reachable through canonical ingress as `http://manage.dev.lotus`.

Local Docker runtime does not publish the internal PostgreSQL port by default.
`postgres:5432` remains internal to the Compose network, and only the application port `8000`
is published for local API access.
