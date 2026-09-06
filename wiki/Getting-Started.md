# Getting Started

## Prerequisites

| Tool | Version | Needed for | Where that version is pinned |
| --- | --- | --- | --- |
| Python | 3.12 | everything | `pyproject.toml` (`requires-python = ">=3.12"`), `mypy.ini`, ruff `target-version`, every CI lane, and the `Dockerfile` base image |
| `make` | any | every repo-native command | `Makefile` |
| Docker | any current release | the containerised stack and PostgreSQL-backed runs | `Dockerfile`, `docker-compose.yml` |

`>=3.12` permits newer interpreters, but every gate runs 3.12, so 3.12 is what reproduces the
gates locally.

## Install

Create and activate a virtual environment first: `make install` installs into whichever
interpreter `python` resolves to, and installing into a system Python fails outright on
distributions that follow PEP 668.

Linux and macOS:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
```

Then, from the repository root:

```bash
make install
```

## Run locally

Default local runtime:

```bash
make run
```

Canonical host runtime:

```bash
make run-canonical
```

That host runtime uses port `8001` so `lotus-manage` can coexist with `lotus-advise`.

## First docs to read

- [README.md](https://github.com/sgajbi/lotus-manage/blob/main/README.md)
- [docs/documentation/project-overview.md](https://github.com/sgajbi/lotus-manage/blob/main/docs/documentation/project-overview.md)
- [docs/standards/RFC-0082-upstream-contract-family-map.md](https://github.com/sgajbi/lotus-manage/blob/main/docs/standards/RFC-0082-upstream-contract-family-map.md)
- [docs/runbooks/service-operations.md](https://github.com/sgajbi/lotus-manage/blob/main/docs/runbooks/service-operations.md)
