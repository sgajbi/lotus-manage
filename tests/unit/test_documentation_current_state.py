from pathlib import Path

from src.api.main import app


ROOT = Path(__file__).resolve().parents[2]

CURRENT_DOC_PATHS = [
    ROOT / "Makefile",
    ROOT / "README.md",
    ROOT / "REPOSITORY-ENGINEERING-CONTEXT.md",
    ROOT / "docs" / "documentation",
    ROOT / "docs" / "architecture",
    ROOT / "docs" / "standards",
    ROOT / "docs" / "demo" / "README.md",
    ROOT / "docs" / "adr" / "README.md",
    ROOT / "docs" / "rfcs" / "README.md",
    ROOT / "wiki",
]

FORBIDDEN_CURRENT_DOC_STRINGS = [
    "/rebalance/proposals",
    "PROPOSAL_",
    "src/core/proposals",
    "src/infrastructure/proposals",
    "postgres_migrations/proposals",
    "python scripts/postgres_migrate.py --target all",
    "python scripts/postgres_migrate.py --target proposals",
    "proposal persistence tables",
    "advisory proposal repository",
]


def _iter_current_docs() -> list[Path]:
    docs: list[Path] = []
    for path in CURRENT_DOC_PATHS:
        if path.is_file():
            docs.append(path)
            continue
        docs.extend(child for child in path.rglob("*.md") if "api-vocabulary" not in child.parts)
    return sorted(set(docs))


def test_current_docs_do_not_advertise_removed_advisory_runtime_surface() -> None:
    failures: list[str] = []
    for path in _iter_current_docs():
        text = path.read_text(encoding="utf-8")
        for forbidden in FORBIDDEN_CURRENT_DOC_STRINGS:
            if forbidden in text:
                failures.append(f"{path.relative_to(ROOT)} contains {forbidden!r}")

    assert failures == []


def test_removed_advisory_demo_and_rfc_sources_stay_retired() -> None:
    retired_patterns = [
        "docs/demo/*advisory*.json",
        "docs/rfcs/advisory pack/**/*.md",
        "docs/rfcs/RFC-0029-iterative-proposal-simulation-workspace-contract.md",
        "docs/rfcs/RFC-0036-postgres-only-runtime-hard-cutover.md",
    ]
    unexpected = [
        str(path.relative_to(ROOT)) for pattern in retired_patterns for path in ROOT.glob(pattern)
    ]

    assert unexpected == []


def test_removed_dpm_python_compatibility_shims_stay_retired() -> None:
    retired_paths = [
        ROOT / "src" / "api" / "routers" / "dpm_policy_packs.py",
        ROOT / "src" / "api" / "routers" / "dpm_runs.py",
        ROOT / "src" / "api" / "routers" / "dpm_runs_config.py",
        ROOT / "src" / "api" / "routers" / "dpm_runs_operations_routes.py",
        ROOT / "src" / "api" / "routers" / "dpm_runs_workflow_routes.py",
        ROOT / "src" / "api" / "routers" / "dpm_simulation.py",
        ROOT / "src" / "core" / "advisory",
        ROOT / "src" / "core" / "proposals",
        ROOT / "src" / "api" / "services" / "dpm_simulation_service.py",
        ROOT / "src" / "core" / "dpm",
        ROOT / "src" / "core" / "dpm_runs",
        ROOT / "src" / "core" / "dpm_engine.py",
        ROOT / "src" / "core" / "engine.py",
        ROOT / "src" / "infrastructure" / "dpm_runs",
        ROOT / "src" / "infrastructure" / "proposals",
        ROOT / "src" / "infrastructure" / "postgres_migrations" / "proposals",
    ]
    unexpected = [str(path.relative_to(ROOT)) for path in retired_paths if path.exists()]

    assert unexpected == []


def test_architecture_review_control_docs_stay_present() -> None:
    required_docs = [
        ROOT / "docs" / "architecture" / "README.md",
        ROOT / "docs" / "architecture" / "CODEBASE-REVIEW-PLAYBOOK.md",
        ROOT / "docs" / "architecture" / "CODEBASE-REVIEW-LEDGER.md",
    ]
    missing = [str(path.relative_to(ROOT)) for path in required_docs if not path.exists()]

    assert missing == []

    ledger = required_docs[-1].read_text(encoding="utf-8")
    required_findings = [
        "RFC36-S2-001",
        "RFC36-S2-002",
        "RFC36-S2-003",
        "RFC36-S2-004",
    ]
    missing_findings = [finding for finding in required_findings if finding not in ledger]

    assert missing_findings == []


def test_wiki_sidebar_links_resolve_to_authored_pages() -> None:
    sidebar = (ROOT / "wiki" / "_Sidebar.md").read_text(encoding="utf-8")
    missing: list[str] = []
    for line in sidebar.splitlines():
        if "](" not in line or ")" not in line:
            continue
        target = line.split("](", 1)[1].split(")", 1)[0]
        if target.startswith("http"):
            continue
        if not (ROOT / "wiki" / f"{target}.md").exists():
            missing.append(target)

    assert missing == []


def test_indexed_rfc_and_adr_files_exist() -> None:
    index_paths = [
        ROOT / "docs" / "rfcs" / "README.md",
        ROOT / "docs" / "adr" / "README.md",
    ]
    missing: list[str] = []
    for index_path in index_paths:
        for token in index_path.read_text(encoding="utf-8").split("`"):
            if not token.endswith(".md"):
                continue
            target = ROOT / token if "/" in token else index_path.parent / token
            if not target.exists():
                missing.append(f"{index_path.relative_to(ROOT)} -> {token}")

    assert missing == []


def test_endpoint_certification_wiki_covers_openapi_paths() -> None:
    certification = (ROOT / "wiki" / "Endpoint-Certification.md").read_text(encoding="utf-8")
    missing = [path for path in sorted(app.openapi()["paths"]) if path not in certification]

    assert missing == []


def test_foundation_rfcs_are_rebaselined_to_current_dpm_scope() -> None:
    reviewed_rfcs = [
        "RFC-0002-rebalance-simulation-mvp-hardening-enterprise-completeness.md",
        "RFC-0007A-contract-tightening.md",
        "RFC-0021-dpm-openapi-contract-hardening.md",
        "RFC-0024-unified-postgresql-persistence-for-dpm-and-advisory.md",
        "RFC-0025-postgres-only-production-mode-cutover.md",
        "RFC-0028-dpm-integration-capabilities-contract.md",
    ]
    missing_review = [
        rfc
        for rfc in reviewed_rfcs
        if "Current Status Review (2026-05-03)"
        not in (ROOT / "docs" / "rfcs" / rfc).read_text(encoding="utf-8")
    ]

    assert missing_review == []

    rfc_0028 = (
        ROOT / "docs" / "rfcs" / "RFC-0028-dpm-integration-capabilities-contract.md"
    ).read_text(encoding="utf-8")
    assert "`GET /api/v1/integration/capabilities`" in rfc_0028
    assert "`GET /integration/capabilities`" not in rfc_0028

    for rfc in [
        "RFC-0024-unified-postgresql-persistence-for-dpm-and-advisory.md",
        "RFC-0025-postgres-only-production-mode-cutover.md",
    ]:
        text = (ROOT / "docs" / "rfcs" / rfc).read_text(encoding="utf-8")
        assert "ADVISORY PORTION SUPERSEDED BY LOTUS-ADVISE SPLIT" in text
        assert "not current lotus-manage" in text
