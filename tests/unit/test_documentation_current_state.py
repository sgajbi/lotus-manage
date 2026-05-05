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


def test_rfc0039_source_map_preserves_first_wave_and_source_authority() -> None:
    source_map = (ROOT / "docs" / "rfcs" / "RFC-0039-source-data-and-method-map.md").read_text(
        encoding="utf-8"
    )
    rfc = (
        ROOT
        / "docs"
        / "rfcs"
        / "RFC-0039-advanced-portfolio-construction-and-rebalance-alternatives.md"
    ).read_text(encoding="utf-8")

    required_first_wave_methods = [
        "`DO_NOTHING_BASELINE`",
        "`HEURISTIC_EXPLAINABLE`",
        "`MIN_TURNOVER`",
        "`TAX_AWARE`",
    ]
    missing_methods = [method for method in required_first_wave_methods if method not in source_map]

    assert missing_methods == []
    assert "RFC-0039-source-data-and-method-map.md" in rfc

    required_source_authorities = [
        "`lotus-core`",
        "`lotus-risk`",
        "`lotus-performance`",
        "TransactionCostCurve:v1",
        "CurrencyExposurePolicy:v1",
        "RegimeScenarioPack:v1",
    ]
    missing_authorities = [
        authority for authority in required_source_authorities if authority not in source_map
    ]

    assert missing_authorities == []
    assert "must not fabricate" in source_map
    assert (
        "Gateway and Workbench realization RFCs must be produced after manage contracts"
        in source_map
    )


def test_rfc0039_scaffolding_standard_preserves_trace_and_status_governance() -> None:
    standard = (
        ROOT / "docs" / "standards" / "construction-alternatives-api-governance.md"
    ).read_text(encoding="utf-8")
    rfc = (
        ROOT
        / "docs"
        / "rfcs"
        / "RFC-0039-advanced-portfolio-construction-and-rebalance-alternatives.md"
    ).read_text(encoding="utf-8")

    required_terms = [
        "`construction_alternative_set`",
        "`construction_alternative`",
        "`selected_alternative`",
        "`objective_trace`",
        "`constraint_trace`",
        "`method_status`",
        "`source_supportability`",
    ]
    missing_terms = [term for term in required_terms if term not in standard]

    assert missing_terms == []
    assert "No `lotus-platform` automation change is required" in standard
    assert "hidden fallback from solver to heuristic" in standard
    assert "No method may be `READY` when its mandatory source family is missing" in standard
    assert "construction-alternatives-api-governance.md" in rfc


def test_rfc0040_slice_evidence_stays_linked_and_support_claim_is_bounded() -> None:
    rfc = (
        ROOT / "docs" / "rfcs" / "RFC-0040-pre-trade-proof-pack-and-evidence-fabric.md"
    ).read_text(encoding="utf-8")
    slice12 = (ROOT / "docs" / "rfcs" / "RFC-0040-mandate-context-hardening-slice12.md").read_text(
        encoding="utf-8"
    )
    index = (ROOT / "docs" / "rfcs" / "README.md").read_text(encoding="utf-8")
    supported_features = (ROOT / "wiki" / "Supported-Features.md").read_text(encoding="utf-8")

    required_evidence = [
        "RFC-0040-source-map-and-gap-analysis.md",
        "RFC-0040-platform-automation-slice1.md",
        "RFC-0040-cleanup-and-structure-slice2.md",
        "RFC-0040-domain-builder-slice3.md",
        "RFC-0040-markdown-summary-slice4.md",
        "RFC-0040-persistence-slice5.md",
        "RFC-0040-api-slice6.md",
        "RFC-0040-handoffs-slice7.md",
        "RFC-0040-gateway-workbench-realization-slice8.md",
        "RFC-0040-implementation-proof-slice9.md",
        "RFC-0040-hardening-review-slice10.md",
        "RFC-0040-mandate-context-hardening-slice12.md",
    ]
    missing_evidence = [name for name in required_evidence if name not in rfc]

    assert missing_evidence == []
    assert "DONE - MANAGE BACKEND COMPLETE" in rfc
    assert "DONE (MANAGE BACKEND COMPLETE" in index
    assert "MANAGE BACKEND COMPLETE" in rfc
    assert "MANAGE BACKEND COMPLETE" in index
    assert "POST-MERGE GOLD-PASS AUDIT AND SLICE 12 MANDATE-CONTEXT HARDENING COMPLETE" in rfc
    assert "POST-MERGE GOLD-PASS AUDIT AND MANDATE-CONTEXT HARDENING COMPLETE" in index
    assert "PR/CI/WIKI PUBLICATION PENDING" not in rfc
    assert "requires normal wiki publication after this audit PR merges" not in rfc
    assert "output/rfc0040-proof/20260503-135112" in rfc
    assert "output/rfc0040-proof/20260503-142438" in rfc
    assert "output/rfc0040-proof/20260503-145818" in rfc
    assert "critical-review.json" in rfc
    assert "Slice 12 - Post-Gold Mandate-Context Source Hardening" in rfc
    assert "DPM_MANDATE_TWIN_EVIDENCE_MISSING" in slice12
    assert "DPM_MANDATE_TWIN_PORTFOLIO_MISMATCH" in slice12
    assert "Gold-Pass Assessment Template" not in rfc
    assert "Full front-office proof-pack product realization remains explicitly gated" in rfc
    assert "b2c3734" in rfc
    assert "b63981b" in rfc
    assert "risk drawdown returned `partial`" in rfc
    assert "| Pre-trade proof packs |" in supported_features
    assert "Supported as RFC-0040 manage backend authority" in supported_features
    assert "source-backed mandate-context attachment" in supported_features
    assert "Gateway composition, Workbench review UX" in supported_features
    assert "Pre-Trade Proof Pack Flow" in supported_features
    assert "output/rfc0040-proof/20260503-145818" in supported_features
    assert "critical-review.json" in supported_features
    assert "| Pre-trade proof pack | Supported |" not in supported_features


def test_rfc0041_slice0_source_map_guardrails_stay_truthful() -> None:
    rfc = (
        ROOT
        / "docs"
        / "rfcs"
        / "RFC-0041-rebalance-wave-orchestration-and-cio-model-change-impact.md"
    ).read_text(encoding="utf-8")
    source_map = (ROOT / "docs" / "rfcs" / "RFC-0041-source-map-and-gap-analysis.md").read_text(
        encoding="utf-8"
    )
    index = (ROOT / "docs" / "rfcs" / "README.md").read_text(encoding="utf-8")
    wiki_index = (ROOT / "wiki" / "RFC-Index.md").read_text(encoding="utf-8")
    wiki_index_normalized = " ".join(wiki_index.split())
    roadmap = (ROOT / "wiki" / "Roadmap.md").read_text(encoding="utf-8")
    supported_features = (ROOT / "wiki" / "Supported-Features.md").read_text(encoding="utf-8")

    required_sections = [
        "## 1. Critical Review of the Prior Draft",
        "## 5. Source Map and Gap Policy",
        "### Slice 1 - Platform Automation and Scaffolding Improvement",
        "### Slice 2 - Cleanup and Structure",
        "### Slice 9 - Gateway and Workbench Realization RFC Slice",
        "### Slice 10 - Implementation Proof",
        "### Slice 11 - Second-Last Hardening and Review",
        "### Slice 12 - Final Closure",
        "## 15. Supported-Features Ledger",
        "## 19. Final Gold-Pass Assessment",
    ]
    missing_sections = [section for section in required_sections if section not in rfc]

    assert missing_sections == []
    assert "| **Status** | DONE |" in rfc
    assert "| RFC-0041 | Rebalance Wave Orchestration and CIO Model Change Impact | DONE |" in index
    assert "feat/rfc0041-gold-standard-tightening" in rfc
    assert "feat/rfc0041-implementation" in rfc
    assert "RFC-0041-source-map-and-gap-analysis.md" in rfc
    assert "`lotus-platform` PR #296, merge `47d3c7f`" in rfc
    assert "tests/unit/dpm/waves/test_wave_domain.py" in rfc
    assert "No source-data gap may be hidden in manage-local placeholders" in rfc
    assert "create or tighten paired RFCs in" in rfc
    assert "`lotus-gateway` and `lotus-workbench`" in rfc
    assert "Gold-standard conclusion" in rfc
    assert "is `DONE` for the manage-owned explicit portfolio-list wave backend authority" in rfc
    assert (
        "is `DONE` for the manage-owned explicit portfolio-list wave backend authority"
        in wiki_index_normalized
    )
    assert "Manage backend implementation is `DONE` for explicit portfolio-list waves" in roadmap
    assert "| Explicit portfolio-list rebalance waves |" in supported_features
    assert "Supported as RFC-0041 `DONE` manage backend authority" in supported_features
    assert "Automatic PM-book/CIO cohort discovery" in supported_features
    assert (
        "full front-office product support are not supported by `lotus-manage`"
        in supported_features
    )

    assert "## Slice 0 Result" in source_map
    assert "## Slice 1 Platform Result" in source_map
    assert "## Slice 2 Cleanup Result" in source_map
    assert "## Slice 3 Domain Foundation Result" in source_map
    assert "src/core/waves/state_machine.py" in source_map
    assert "0007_rebalance_waves.sql" in source_map
    assert "No route, capability, or supported-feature claim is added in Slice 3" in source_map
    assert "## Slice 4 Preview/Create Result" in source_map
    assert "POST /api/v1/rebalance/waves/preview" in source_map
    assert "NOT_SUPPORTED_TRIGGER" in source_map
    assert "## Slice 5 Source Check Result" in source_map
    assert "POST /api/v1/rebalance/waves/{wave_id}/source-check" in source_map
    assert "MANDATE_HEALTH_MISSING" in source_map
    assert "DPM_SOURCE_READINESS" in source_map
    assert "## Slice 6 Simulation, Selection, and Proof-Pack Linkage Result" in source_map
    assert "POST /api/v1/rebalance/waves/{wave_id}/simulate" in source_map
    assert "POST /api/v1/rebalance/waves/{wave_id}/items/{wave_item_id}/select" in source_map
    assert "CONSTRUCTION_INPUT_MISSING" in source_map
    assert "proof_pack_service.generate_proof_pack_from_selected_alternative" in source_map
    assert "No manage-local evidence convention is introduced for RFC-0041." in source_map
    assert "## Slice 7 Approval, Staging, and Operations Handoff Result" in source_map
    assert "POST /api/v1/rebalance/waves/{wave_id}/approve" in source_map
    assert "POST /api/v1/rebalance/waves/{wave_id}/stage" in source_map
    assert "POST /api/v1/rebalance/waves/{wave_id}/handoff" in source_map
    assert "external_execution_claimed=false" in source_map
    assert "## Slice 8 Supportability, Observability, and Operator Diagnostics Result" in source_map
    assert "GET /api/v1/rebalance/waves/{wave_id}/supportability" in source_map
    assert "lotus_manage_wave_supportability_total" in source_map
    assert "portfolio identifiers, client identifiers, raw request" in source_map
    assert "## Slice 9 Gateway and Workbench Realization RFC Result" in source_map
    assert "`lotus-gateway` PR #183, merge `e0e4b1b`" in source_map
    assert "`lotus-workbench` PR #143, merge `c4888d4`" in source_map
    assert "/api/v1/dpm/command-center/waves*" in source_map
    assert "Workbench must consume Gateway wave routes only" in source_map
    assert "misleading RFC-0041 documentation guardrail name" in source_map
    assert "## Slice 10 Live Implementation Proof Result" in source_map
    assert "output/rfc0041-wave-proof/20260504-231914/" in source_map
    assert "`DPM_MANAGE_POSTGRES_DSN`" in source_map
    assert "method-specific run correlation ids" in source_map
    assert "PARTIALLY_SIMULATED" in source_map
    assert "GET /api/v1/rebalance/waves/{wave_id}/proof-pack" in source_map
    assert "POST /api/v1/rebalance/waves/{wave_id}/cancel" in source_map
    assert "## Slice 11 Hardening Review Result" in source_map
    assert "book/PM filters remain deferred" in source_map
    assert "tests/unit/dpm/waves/test_source_readiness.py" in source_map
    assert "## Slice 12 Final Closure Result" in source_map
    assert "Skills/context/guidance decision is `no change needed`" in source_map
    assert "| `EXPLICIT_PORTFOLIO_LIST` | Supported first |" in source_map
    assert "| `PM_BOOK_REVIEW` | Deferred, except supplied manifest posture |" in source_map
    assert "| `CIO_MODEL_CHANGE` | Deferred for automatic discovery" in source_map
    assert "`portfolio_manager_id`" not in rfc
    assert "`dpm_cio_model_change_impacts`" not in rfc
    assert "output/rfc0041-wave-proof/<timestamp>/" in source_map
    assert (
        "Do not start product implementation before this Slice 0 artifact is reviewed" in source_map
    )


def test_rfc0041_work_to_be_done_ledger_preserves_deferred_boundaries() -> None:
    ledger = (ROOT / "docs" / "rfcs" / "RFC-worktobedone.md").read_text(encoding="utf-8")
    ledger_normalized = " ".join(ledger.split())
    index = (ROOT / "docs" / "rfcs" / "README.md").read_text(encoding="utf-8")

    required_items = [
        "RFC41-WTBD-001",
        "RFC41-WTBD-002",
        "RFC41-WTBD-003",
        "RFC41-WTBD-004",
        "RFC41-WTBD-005",
        "RFC41-WTBD-006",
        "RFC41-WTBD-007",
        "RFC41-WTBD-008",
        "RFC41-WTBD-009",
        "RFC41-WTBD-010",
    ]
    missing_items = [item for item in required_items if item not in ledger]

    assert missing_items == []
    assert "`docs/rfcs/RFC-worktobedone.md`" in index
    assert "no item in this ledger is a supported-feature claim" in ledger
    assert "no additional wiki source change is required for this slice" in ledger_normalized
    assert "explicit portfolio-list rebalance waves" in ledger_normalized
    assert "Automatic PM-book / portfolio-manager cohort discovery" in ledger
    assert "Automatic CIO model-change affected-mandate discovery" in ledger
    assert "Gateway wave composition" in ledger
    assert "Workbench wave command center" in ledger
    assert "Report materialization from wave/proof-pack evidence" in ledger_normalized
    assert "AI PM memo generation from wave evidence" in ledger_normalized
    assert "External execution integration" in ledger
    assert "Source-owned discovery should then improve trigger quality" in ledger_normalized
    assert "OpenAPI/Swagger quality is certified for every API added or changed" in ledger


def test_rfc0040_work_to_be_done_ledger_preserves_deferred_boundaries() -> None:
    ledger = (ROOT / "docs" / "rfcs" / "RFC-worktobedone.md").read_text(encoding="utf-8")
    ledger_normalized = " ".join(ledger.split())

    required_items = [
        "RFC40-WTBD-001",
        "RFC40-WTBD-002",
        "RFC40-WTBD-003",
        "RFC40-WTBD-004",
        "RFC40-WTBD-005",
        "RFC40-WTBD-006",
        "RFC40-WTBD-007",
        "RFC40-WTBD-008",
        "RFC40-WTBD-009",
        "RFC40-WTBD-010",
    ]
    missing_items = [item for item in required_items if item not in ledger]

    assert missing_items == []
    assert "RFC-0040 - Pre-Trade Proof Pack And Evidence Fabric" in ledger
    assert "DpmPreTradeProofPack" in ledger
    assert "output/rfc0040-proof/20260503-145818/manifest.json" in ledger
    assert "lotus-gateway` PR #181 merge `b2c3734" in ledger
    assert "lotus-workbench` PR #142 merge `b63981b" in ledger
    assert "sgajbi/lotus-gateway#182" in ledger
    assert "Gateway proof-pack composition" in ledger
    assert "Workbench proof-pack review UX" in ledger
    assert "Full front-office proof-pack product realization" in ledger
    assert "Report materialization from `DpmProofPackReportInput`" in ledger
    assert "AI PM memo generation from `DpmProofPackAiEvidenceInput`" in ledger
    assert "Broader risk and performance proof-pack enrichment" in ledger
    assert "Authoritative transaction-cost curve" in ledger
    assert "Sustainability preferences and client restriction profiles" in ledger
    assert "Scenario-pack authority beyond supplied context" in ledger
    assert "Decision Timeline And Portfolio Memory" in ledger
    assert "manage remains proof-pack authority" in ledger
    assert "Portfolio memory should wait until wave and post-trade outcome events exist" in (
        ledger_normalized
    )


def test_rfc0038_work_to_be_done_ledger_preserves_deferred_boundaries() -> None:
    ledger = (ROOT / "docs" / "rfcs" / "RFC-worktobedone.md").read_text(encoding="utf-8")
    ledger_normalized = " ".join(ledger.split())

    required_items = [
        "RFC38-WTBD-001",
        "RFC38-WTBD-002",
        "RFC38-WTBD-003",
        "RFC38-WTBD-004",
        "RFC38-WTBD-005",
        "RFC38-WTBD-006",
        "RFC38-WTBD-007",
        "RFC38-WTBD-008",
    ]
    missing_items = [item for item in required_items if item not in ledger]

    assert missing_items == []
    assert "RFC-0038 - Mandate Digital Twin, Health Score" in ledger
    assert "output/rfc0038-live-proof/20260503T063617Z/summary.json" in ledger
    assert "sgajbi/lotus-gateway#180" in ledger
    assert "sgajbi/lotus-workbench#140" in ledger
    assert "sgajbi/lotus-platform#294" in ledger
    assert "Gateway DPM command-center composition" in ledger
    assert "Workbench DPM cockpit panels" in ledger
    assert "Platform canonical seed automation" in ledger
    assert "PM-book discovery for monitoring and command-center cohorts" in ledger
    assert "Mandate objective, benchmark, review cadence, and model-change source products" in ledger
    assert "Client restriction, sustainability, and cashflow source products" in ledger
    assert "Broader risk and performance health enrichment" in ledger
    assert "Full front-office command-center product support" in ledger
    assert "Gateway and Workbench can realize the already-supported backend foundation" in (
        ledger_normalized
    )


def test_rfc0036_work_to_be_done_ledger_preserves_deferred_boundaries() -> None:
    ledger = (ROOT / "docs" / "rfcs" / "RFC-worktobedone.md").read_text(encoding="utf-8")
    ledger_normalized = " ".join(ledger.split())

    required_items = [
        "RFC36-WTBD-001",
        "RFC36-WTBD-002",
        "RFC36-WTBD-003",
        "RFC36-WTBD-004",
        "RFC36-WTBD-005",
        "RFC36-WTBD-006",
    ]
    missing_items = [item for item in required_items if item not in ledger]

    assert missing_items == []
    assert "RFC-0036 - DPM Stateful Core Sourcing And Endpoint Consolidation" in ledger
    assert "make live-api-validate-core" in ledger
    assert "DpmModelPortfolioTarget:v1" in ledger
    assert "DpmSourceReadiness:v1" in ledger
    assert "Gateway integration rebuilt against canonical `/api/v1` manage APIs" in ledger
    assert "Workbench product surfaces over stateful manage execution" in ledger
    assert "Portfolio-level DPM operation dashboards over stateful executions" in ledger
    assert "Promote additional stateful DPM source-data products into platform mesh certification" in (
        ledger
    )
    assert "Additional upstream source-product depth for stateful execution" in ledger
    assert "Conditional Downstream Migration Handling" in ledger
    assert "canonical `/api/v1` contracts remain the only supported service APIs" in (
        ledger_normalized
    )


def test_rfc0037_work_to_be_done_ledger_preserves_target_state_boundaries() -> None:
    ledger = (ROOT / "docs" / "rfcs" / "RFC-worktobedone.md").read_text(encoding="utf-8")
    ledger_normalized = " ".join(ledger.split())

    required_items = [
        "RFC37-WTBD-001",
        "RFC37-WTBD-002",
        "RFC37-WTBD-003",
        "RFC37-WTBD-004",
        "RFC37-WTBD-005",
        "RFC37-WTBD-006",
        "RFC37-WTBD-007",
    ]
    missing_items = [item for item in required_items if item not in ledger]

    assert missing_items == []
    assert "RFC-0037 - DPM Operating System And Mandate Intelligence" in ledger
    assert "strategic parent roadmap" in ledger
    assert "Complete RFC-0042 post-trade outcome feedback loop" in ledger
    assert "Complete RFC-0043 governed AI PM copilot" in ledger
    assert "Full front-office DPM product realization across Gateway and Workbench" in ledger
    assert "Source-product depth for mandate personalization" in ledger
    assert "Report, archive, and client/internal evidence materialization" in ledger
    assert "Canonical sales/demo story from implementation-backed stack evidence" in ledger
    assert "Portfolio memory across mandate, construction, proof-pack, wave, outcome, report, and AI events" in (
        ledger
    )
    assert "proof exists beyond roadmap language" in ledger_normalized


def test_rfc0039_work_to_be_done_ledger_preserves_deferred_boundaries() -> None:
    ledger = (ROOT / "docs" / "rfcs" / "RFC-worktobedone.md").read_text(encoding="utf-8")
    ledger_normalized = " ".join(ledger.split())

    required_items = [
        "RFC39-WTBD-001",
        "RFC39-WTBD-002",
        "RFC39-WTBD-003",
        "RFC39-WTBD-004",
        "RFC39-WTBD-005",
        "RFC39-WTBD-006",
        "RFC39-WTBD-007",
        "RFC39-WTBD-008",
        "RFC39-WTBD-009",
        "RFC39-WTBD-010",
    ]
    missing_items = [item for item in required_items if item not in ledger]

    assert missing_items == []
    assert "RFC-0039 - Advanced Portfolio Construction And Rebalance Alternatives" in ledger
    assert "output/rfc0039-proof/20260503-193842-authority-backed-canonical/summary.json" in ledger
    assert "ESG_RESTRICTION_AWARE_CONSTRUCTION_DEFERRED" in ledger
    assert "Gateway construction-alternatives composition" in ledger
    assert "Workbench construction lab / alternatives comparison UX" in ledger
    assert "Full front-office construction-lab product realization" in ledger
    assert "ESG/restriction-aware construction support" in ledger
    assert "Broader risk/performance alternative enrichment" in ledger
    assert "Authoritative transaction-cost and cost-aware alternatives" in ledger
    assert "Cashflow/income-need aware liquidity construction" in ledger
    assert "Treasury-depth currency overlay" in ledger
    assert "First-class regime scenario-pack source" in ledger
    assert "Construction Lifecycle Across Proof Packs, Waves, Reports, And AI" in ledger
    assert "Gateway and Workbench can expose the supported manage backend methods" in (
        ledger_normalized
    )
