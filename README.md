# Lotus Manage

Discretionary portfolio management (lotus-manage) execution, supportability, and lifecycle service.

This repository owns lotus-manage runtime workflows.
Advisor-led proposal workflows are owned by `lotus-advise`.

API docs endpoint: `/docs`

Local Docker runtime does not publish the internal PostgreSQL port by default.
`postgres:5432` remains internal to the Compose network, and only the application port `8000`
is published for local API access.
