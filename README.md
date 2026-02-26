# lotus-manage

Discretionary portfolio management execution and lifecycle service for Lotus platform.

## Quick Start

`powershell
make install
make lint
make typecheck
make openapi-gate
make ci
`",
  ",
  

`powershell
uvicorn src.app.main:app --reload --port 8140
`",
  ",
  

`powershell
docker compose up --build
`",
  ",
  

- CI and governance: .github/workflows/
- Engineering commands: Makefile
- Platform standards docs: docs/standards/
