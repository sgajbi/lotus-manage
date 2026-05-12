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


def test_completed_wtbd_gold_pass_truth_is_not_left_in_pre_merge_language() -> None:
    audited_paths = [
        ROOT / "docs" / "rfcs" / "RFC-worktobedone.md",
        ROOT
        / "docs"
        / "rfcs"
        / "RFC-0039-advanced-portfolio-construction-and-rebalance-alternatives.md",
        ROOT / "docs" / "rfcs" / "RFC-0040-pre-trade-proof-pack-and-evidence-fabric.md",
        ROOT
        / "docs"
        / "rfcs"
        / "RFC-0041-rebalance-wave-orchestration-and-cio-model-change-impact.md",
        ROOT / "docs" / "rfcs" / "RFC-0042-post-trade-outcome-feedback-loop.md",
    ]
    stale_closure_terms = [
        "ready for PR merge/wiki publication",
        "once this RFC/WTBD/wiki truth is merged to `lotus-manage` `main`",
        "once this branch is merged to `main`",
        "the supported manage wave path remains unchanged until a later manage consumer slice",
    ]
    failures: list[str] = []
    for path in audited_paths:
        text = path.read_text(encoding="utf-8")
        for term in stale_closure_terms:
            if term in text:
                failures.append(f"{path.relative_to(ROOT)} contains stale closure term {term!r}")

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


def test_rfc0036_completed_wtbd_truth_is_integrated_into_rfc_and_wiki() -> None:
    rfc = (
        ROOT / "docs" / "rfcs" / "RFC-0036-dpm-stateful-core-sourcing-and-endpoint-consolidation.md"
    ).read_text(encoding="utf-8")
    wtbd = (ROOT / "docs" / "rfcs" / "RFC-worktobedone.md").read_text(encoding="utf-8")
    supported_features = (ROOT / "wiki" / "Supported-Features.md").read_text(encoding="utf-8")

    assert "## Post-Closure WTBD Integration Audit" in rfc
    assert (
        "RFC36-WTBD-001 - Gateway integration rebuilt against canonical `/api/v1` manage APIs"
        in rfc
    )
    assert "RFC36-WTBD-002 - Workbench product surfaces over stateful manage execution" in rfc
    assert (
        "RFC36-WTBD-003 - Portfolio-level DPM operation dashboards over stateful executions" in rfc
    )
    assert "canonical-front-office-qa-20260509-214551.json" in rfc
    assert "wtbd-rfc36-audit-20260509-214550" in rfc
    assert "truthfully_degraded" in rfc
    assert "Expected-standard decision" in rfc
    assert "Completed: rebuild `lotus-gateway` integration" in rfc
    assert "Completed: close conditional downstream migration handling" in rfc
    assert "`lotus-platform` PR #316" in rfc
    assert "Remaining: promote stateful DPM source-data products" in rfc

    assert "RFC36 Gold-Pass Audit And RFC Reintegration - 2026-05-09" in wtbd
    assert "Their implementation truth has been incorporated into RFC-0036" in wtbd
    assert "canonical-front-office-qa-20260509-214551.json" in wtbd
    assert "wtbd-rfc36-audit-20260509-214550" in wtbd
    assert (
        "The completed RFC36 WTBDs have genuinely reached the expected first-wave standard" in wtbd
    )

    assert "## RFC-0036 Stateful Execution Product Path" in supported_features
    assert "lotus-gateway Workbench overview BFF" in supported_features
    assert "Missing supportability is rendered as unknown/N/A" in supported_features
    assert "| Contract governance |" in supported_features
    assert (
        "Client demos should claim first-wave supportability and operations visibility only"
        in supported_features
    )


def test_rfc0037_completed_child_truth_is_integrated_into_parent_rfc() -> None:
    rfc = (
        ROOT / "docs" / "rfcs" / "RFC-0037-dpm-operating-system-and-mandate-intelligence.md"
    ).read_text(encoding="utf-8")
    wtbd = (ROOT / "docs" / "rfcs" / "RFC-worktobedone.md").read_text(encoding="utf-8")
    supported_features = (ROOT / "wiki" / "Supported-Features.md").read_text(encoding="utf-8")

    required_rfc_terms = [
        "STRATEGIC PARENT ROADMAP - CHILD CAPABILITIES PARTIALLY IMPLEMENTED",
        "Post-Closure WTBD Integration Audit",
        "RFC37-WTBD-001",
        "RFC37-WTBD-006",
        "RFC37-WTBD-005",
        "bounded first-wave outcome-review product path",
        "Supported proof-pack, rebalance-wave, and outcome-review evidence now flow",
        "client communication execution remains unsupported",
        "`lotus-platform` PR #310",
        "`884bec3`",
        "DPM sales/demo story | RFC-0037 plus wiki | Supported canonical story",
    ]
    missing_rfc_terms = [term for term in required_rfc_terms if term not in rfc]

    assert missing_rfc_terms == []

    required_wtbd_terms = [
        "RFC37 Gold-Pass Audit And RFC Reintegration - 2026-05-09",
        "RFC37-WTBD-006 is complete as an implementation-backed canonical sales/demo",
        "RFC37-WTBD-001 is complete for the bounded RFC-0042 first-wave outcome-review product",
        "RFC37-WTBD-005 is complete for supported proof-pack, wave, and outcome-review report",
        "Supported proof-pack, wave, and outcome-review evidence now flow",
        "`42e0ecff3597257ac3ea63b0c59b425603eeb291`",
        "`884bec3`",
    ]
    missing_wtbd_terms = [term for term in required_wtbd_terms if term not in wtbd]

    assert missing_wtbd_terms == []

    assert "`lotus-platform` PR #310 and wiki publication commit `884bec3`" in supported_features
    assert "Canonical DPM demo story" in supported_features
    assert "Report, archive, and evidence materialization" in supported_features
    assert "RFC37-WTBD-005 is complete for first-wave generated report" in supported_features
    assert "Post-trade outcome feedback | RFC-0042 | Proposed" not in rfc
    assert "DPM sales/demo story | RFC-0037 plus wiki | Proposed" not in rfc


def test_rfc0038_completed_wtbd_truth_is_integrated_into_rfc_and_wiki() -> None:
    rfc = (
        ROOT / "docs" / "rfcs" / "RFC-0038-mandate-digital-twin-health-and-command-center.md"
    ).read_text(encoding="utf-8")
    wtbd = (ROOT / "docs" / "rfcs" / "RFC-worktobedone.md").read_text(encoding="utf-8")
    supported_features = (ROOT / "wiki" / "Supported-Features.md").read_text(encoding="utf-8")

    assert "## 17. Post-Closure WTBD Integration Audit" in rfc
    assert "RFC38-WTBD-001 - Gateway DPM command-center composition" in rfc
    assert "RFC38-WTBD-002 - Workbench DPM cockpit panels" in rfc
    assert "RFC38-WTBD-003 - Platform canonical seed automation" in rfc
    assert "RFC38-WTBD-004 - PM-book discovery for monitoring and command-center cohorts" in rfc
    assert (
        "RFC38-WTBD-006 - Client restriction, sustainability, and cashflow source products" in rfc
    )
    assert (
        "RFC38-WTBD-005 - Mandate objective, benchmark, review cadence, and model-change sources"
        in rfc
    )
    assert "RFC38-WTBD-008 - Full front-office command-center product support" in rfc
    assert "### 17.5 WTBD-005 Gold-Pass Assessment" in rfc
    assert "### 17.6 WTBD-008 Gold-Pass Assessment" in rfc
    assert "### 17.7 WTBD-006 Gold-Pass Assessment" in rfc
    assert "canonical-front-office-qa-20260509-214551.json" in rfc
    assert "dpm-command-center-seed-20260509-220332.json" in rfc
    assert "supportabilityState=READY" in rfc
    assert "Expected-standard decision" in rfc

    assert "RFC38 Gold-Pass Audit And RFC Reintegration - 2026-05-09" in wtbd
    assert "Their implementation truth has been incorporated into RFC-0038" in wtbd
    assert "RFC38-WTBD-005 reaches the expected first-wave standard" in wtbd
    assert "RFC38-WTBD-008 reaches the expected first-wave product standard" in wtbd
    assert "dpm-command-center-live.png" in wtbd
    assert (
        "populated ready, selector-driven partial, and empty-date command-center postures" in wtbd
    )

    assert "## RFC-0038 DPM Command Center Product Path" in supported_features
    assert "lotus-core PortfolioManagerBookMembership:v1" in supported_features
    assert "| Failure behavior |" in supported_features
    assert "daily discretionary mandate control surface" in supported_features


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
        "RFC-0001-rebalance-simulation-mvp.md",
        "RFC-0002-rebalance-simulation-mvp-hardening-enterprise-completeness.md",
        "RFC-0003-contract-engine-completion.md",
        "RFC-0004-institutional-afterstate-holdings-goldens.md",
        "RFC-0005-institutional-tightening-post-trade-rules-reconciliation-demo-pack.md",
        "RFC-0006A-pre-persistence-safety-afterstate.md",
        "RFC-0006B-pre-persistence-rules-scenarios-demo.md",
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

    early_foundation = (ROOT / "docs" / "rfcs" / "RFC-0001-rebalance-simulation-mvp.md").read_text(
        encoding="utf-8"
    )
    assert "historical MVP foundation" in early_foundation
    assert "not be read as the target-state product definition" in early_foundation

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
        "RegimeScenarioPackEvaluation:v1",
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


def test_rfc0039_completed_wtbd_truth_is_integrated_into_rfc_and_wiki() -> None:
    rfc = (
        ROOT
        / "docs"
        / "rfcs"
        / "RFC-0039-advanced-portfolio-construction-and-rebalance-alternatives.md"
    ).read_text(encoding="utf-8")
    wtbd = (ROOT / "docs" / "rfcs" / "RFC-worktobedone.md").read_text(encoding="utf-8")
    supported_features = (ROOT / "wiki" / "Supported-Features.md").read_text(encoding="utf-8")

    required_rfc_terms = [
        "Post-Closure WTBD Integration Audit",
        "RFC39-WTBD-001",
        "lotus-workbench` PR #171",
        "construction-live-fixed2",
        "HTTP 409",
        "HTTP 500",
        "cas_ca8c4e1351aa",
        "no local optimizer/methodology claim",
        "RFC39-WTBD-010",
        "bounded construction lifecycle support",
        "outcome expected-snapshot reconciliation",
    ]
    missing_rfc_terms = [term for term in required_rfc_terms if term not in rfc]

    assert missing_rfc_terms == []

    required_wtbd_terms = [
        "RFC39 Gold-Pass Audit And RFC Reintegration - 2026-05-09",
        "lotus-workbench` PR #171",
        "construction-live-fixed2",
        "deterministic idempotency",
        "deterministic correlation",
        "RFC39-WTBD-010 - Construction Lifecycle Across Proof Packs, Waves, Reports, And AI",
        "101 focused tests passed",
        "Expected-standard decision",
    ]
    missing_wtbd_terms = [term for term in required_wtbd_terms if term not in wtbd]

    assert missing_wtbd_terms == []

    required_wiki_terms = [
        "RFC-0039 Construction Alternatives Product Path",
        "TransactionCostCurve:v1",
        "PortfolioCashflowProjection:v1",
        "ClientRestrictionProfile:v1",
        "SustainabilityPreferenceProfile:v1",
        "RegimeScenarioPackEvaluation:v1",
        "bounded selected-alternative lifecycle support",
        "outcome expected-snapshot reconciliation",
    ]
    missing_wiki_terms = [term for term in required_wiki_terms if term not in supported_features]

    assert missing_wiki_terms == []
    assert "Full product-surface promotion still requires" not in supported_features


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
    assert "FIRST-WAVE PRODUCT PATH LIVE-PROVEN" in rfc
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
    assert "b2c3734" in rfc
    assert "b63981b" in rfc
    assert "risk drawdown returned `partial`" in rfc
    assert "| Pre-trade proof packs |" in supported_features
    assert "Supported as RFC-0040 manage backend authority" in supported_features
    assert "source-backed mandate-context attachment" in supported_features
    assert "Gateway proof-pack composition is implementation-backed" in supported_features
    assert "Pre-Trade Proof Pack Flow" in supported_features
    assert "GET /api/v1/rebalance/portfolio-memory/{portfolio_id}" in supported_features
    assert "src/core/portfolio_memory/" in supported_features
    assert "first-wave Gateway/Workbench product path" in supported_features
    assert "Gateway PR #199 exposes the command-center composition" in supported_features
    assert "output/rfc0040-proof/20260503-145818" in supported_features
    assert "critical-review.json" in supported_features


def test_rfc0040_completed_wtbd_truth_is_integrated_into_rfc_and_wiki() -> None:
    rfc = (
        ROOT / "docs" / "rfcs" / "RFC-0040-pre-trade-proof-pack-and-evidence-fabric.md"
    ).read_text(encoding="utf-8")
    wtbd = (ROOT / "docs" / "rfcs" / "RFC-worktobedone.md").read_text(encoding="utf-8")
    supported_features = (ROOT / "wiki" / "Supported-Features.md").read_text(encoding="utf-8")

    required_rfc_terms = [
        "FIRST-WAVE PRODUCT PATH LIVE-PROVEN",
        "Post-Closure WTBD Integration Audit",
        "RFC40-WTBD-001",
        "lotus-gateway` PR #195",
        "lotus-workbench` PR #156/#164",
        "lotus-report` PR #90/#92/#93",
        "lotus-ai` PR #61/#62/#64",
        "selected-alternative scenario-pack preservation",
        "RFC40-WTBD-009",
        "canonical-front-office-qa-20260509-225912.json",
        "wtbd-rfc40-audit-20260509",
        "external OMS execution",
    ]
    missing_rfc_terms = [term for term in required_rfc_terms if term not in rfc]

    assert missing_rfc_terms == []

    required_wtbd_terms = [
        "RFC40 Gold-Pass Audit And RFC Reintegration - 2026-05-09",
        "wiki-published through `lotus-gateway` PR #195",
        "DpmProofPackReportInput",
        "DpmProofPackAiEvidenceInput",
        "Gold-pass assessment - 2026-05-10",
        "`RegimeScenarioPackEvaluation:v1` context in `scenario_and_regime_evidence`",
        "portfolio-memory consumers",
        "canonical-front-office-qa-20260509-225912.json",
        "wtbd-rfc40-audit-20260509",
    ]
    missing_wtbd_terms = [term for term in required_wtbd_terms if term not in wtbd]

    assert missing_wtbd_terms == []

    required_wiki_terms = [
        "RFC-0040 Pre-Trade Proof-Pack Product Path",
        "lotus-report + lotus-render + lotus-archive",
        "DpmProofPackReportInput",
        "DpmProofPackAiEvidenceInput",
        "selected-alternative scenario-pack preservation from `lotus-risk`",
        "`scenario_and_regime_evidence` sections preserve",
        "review-gated PM memo",
        "canonical-front-office-qa-20260509-225912.json",
        "wtbd-rfc40-audit-20260509",
    ]
    missing_wiki_terms = [term for term in required_wiki_terms if term not in supported_features]

    assert missing_wiki_terms == []
    assert "Full front-office proof-pack product realization remains explicitly gated" not in rfc
    assert "| Pre-trade proof pack | Supported |" not in supported_features


def test_rfc0043_ai_copilot_truth_reflects_implemented_owner_side_packs() -> None:
    rfc = (ROOT / "docs" / "rfcs" / "RFC-0043-governed-ai-pm-copilot-for-dpm.md").read_text(
        encoding="utf-8"
    )
    index = (ROOT / "docs" / "rfcs" / "README.md").read_text(encoding="utf-8")
    wtbd = (ROOT / "docs" / "rfcs" / "RFC-worktobedone.md").read_text(encoding="utf-8")
    supported_features = (ROOT / "wiki" / "Supported-Features.md").read_text(encoding="utf-8")
    wiki_index = (ROOT / "wiki" / "RFC-Index.md").read_text(encoding="utf-8")

    required_terms = [
        "PARTIALLY IMPLEMENTED - BOUNDED DPM WORKFLOW PACKS AND FIRST-WAVE PRODUCT INVOCATION",
        "`dpm_pm_memo.pack@v1`",
        "`dpm_wave_pm_memo.pack@v1`",
        "`outcome_review_narrative.pack@v1`",
        "`dpm_operations_handoff_summary.pack@v1`",
        "The bounded DPM workflow-pack result from RFC37-WTBD-002 is incorporated",
        "bounded current RFC37-WTBD-002 product path",
        "WTBD Reintegration Audit - 2026-05-10",
        "review-gated proof-pack PM memo, wave PM memo, outcome-review narrative, operations handoff summary, and exception summary packs",
        "`dpm_exception_summary.pack@v1`",
        "lotus-ai` PR #68",
        "support-only narrative aids",
    ]

    for term in required_terms:
        assert term in rfc or term in wtbd or term in supported_features or term in wiki_index

    assert (
        "PARTIALLY IMPLEMENTED (BOUNDED DPM WORKFLOW PACKS; FIRST-WAVE PRODUCT INVOCATION COMPLETE)"
        in index
    )
    assert "Partially supported through bounded DPM workflow packs and first-wave product invocation" in (
        supported_features
    )
    assert "all AI copilot features as proposed" not in rfc
    assert "RFC-0043 remains proposed" not in wtbd
    assert "Exception-summary packs, full copilot workspace UX" not in supported_features


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
    assert "FIRST-WAVE PRODUCT PATH LIVE-PROVEN" in rfc
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
    assert "bounded first-wave product path is implementation-backed" in rfc
    assert (
        "is `DONE` for the manage-owned explicit portfolio-list wave backend authority"
        in wiki_index_normalized
    )
    assert "Manage backend implementation is `DONE` for explicit portfolio-list waves" in roadmap
    assert "| Explicit portfolio-list rebalance waves |" in supported_features
    assert "Supported as RFC-0041 `DONE` manage backend authority" in supported_features
    assert "PM-book wave discovery is source-backed through lotus-core" in supported_features
    assert "source-owned `PM_BOOK_REVIEW` and `CIO_MODEL_CHANGE` cohorts" in supported_features
    assert (
        "Gateway command-center composition, Workbench first-wave wave command-center UX, "
        "wave report materialization, and wave PM memo assistance are implementation-backed"
        in supported_features
    )
    assert "external OMS execution remain unsupported future WTBDs" in supported_features

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
    assert "Source-owned `PM_BOOK_REVIEW` and `CIO_MODEL_CHANGE` cohort discovery" in source_map
    assert "tests/unit/dpm/waves/test_source_readiness.py" in source_map
    assert "## Slice 12 Final Closure Result" in source_map
    assert "Skills/context/guidance decision is `no change needed`" in source_map
    assert "| `EXPLICIT_PORTFOLIO_LIST` | Supported first |" in source_map
    assert "| `PM_BOOK_REVIEW` | Supported for source-owned PM-book discovery |" in source_map
    assert (
        "| `CIO_MODEL_CHANGE` | Supported for source-owned model-change affected-mandate discovery |"
        in source_map
    )
    assert "`portfolio_manager_id`" in rfc
    assert "`CioModelChangeAffectedCohort:v1`" in rfc
    assert "`dpm_cio_model_change_impacts`" not in rfc
    assert "## Post-Closure Audit Result - 2026-05-05" in source_map
    assert "output/rfc0041-wave-proof/<timestamp>/" in source_map
    assert (
        "Do not start product implementation before this Slice 0 artifact is reviewed" in source_map
    )


def test_rfc0041_completed_wtbd_truth_is_integrated_into_rfc_and_wiki() -> None:
    rfc = (
        ROOT
        / "docs"
        / "rfcs"
        / "RFC-0041-rebalance-wave-orchestration-and-cio-model-change-impact.md"
    ).read_text(encoding="utf-8")
    wtbd = (ROOT / "docs" / "rfcs" / "RFC-worktobedone.md").read_text(encoding="utf-8")
    supported_features = (ROOT / "wiki" / "Supported-Features.md").read_text(encoding="utf-8")

    required_rfc_terms = [
        "FIRST-WAVE PRODUCT PATH LIVE-PROVEN",
        "Post-Closure WTBD Integration Audit",
        "RFC41-WTBD-001",
        "RFC41-WTBD-010",
        "`lotus-gateway` PR #196/#197/#201",
        "`lotus-workbench` PR #165/#168",
        "`lotus-report` PR #91",
        "`lotus-ai` PR #63",
        "`CioModelChangeAffectedCohort:v1`",
        "`RiskEventAffectedCohort:v1`",
        "`lotus-risk` PR #115",
        "`lotus-platform` PR #313",
        "`91f933a`",
        "external_execution_claimed=false",
        "canonical-front-office-qa-20260509-225912.json",
        "wtbd-rfc40-audit-20260509",
    ]
    missing_rfc_terms = [term for term in required_rfc_terms if term not in rfc]

    assert missing_rfc_terms == []

    required_wtbd_terms = [
        "RFC41 Gold-Pass Audit And RFC Reintegration - 2026-05-09",
        "Completed for first-wave wave command-center product support",
        "Full front-office command-center product support",
        "bounded `RISK_EVENT` wave preview and durable",
        "Gold-pass assessment for the 2026-05-10 risk-event consumer slice",
        "canonical-front-office-qa-20260509-225912.json",
        "dpm-wave-command-center-live.png",
        "external OMS execution",
    ]
    missing_wtbd_terms = [term for term in required_wtbd_terms if term not in wtbd]

    assert missing_wtbd_terms == []

    required_wiki_terms = [
        "Rebalance Wave Flow",
        "source-owned PM-book wave discovery",
        "lotus-report/render/archive wave report",
        "review-gated wave PM memo",
        "Source-owned risk-event rebalance waves",
        "bounded risk-event wave discovery is source-backed through lotus-risk",
        "canonical-front-office-qa-20260509-225912.json",
        "external OMS execution is not supported",
    ]
    missing_wiki_terms = [term for term in required_wiki_terms if term not in supported_features]

    assert missing_wiki_terms == []
    assert "Gateway wave composition | Not supported in manage RFC" not in rfc
    assert "Workbench wave command center | Not supported in manage RFC" not in rfc
    assert (
        "RFC41-WTBD-007 | Full front-office command-center product support | "
        "`lotus-gateway`, `lotus-workbench`, with manage as backend authority | "
        "Proposed, not supported" not in wtbd
    )
    assert "Gateway/Workbench product consumption and canonical proof remain open" not in wtbd


def test_rfc0042_gold_standard_tightening_preserves_source_boundaries() -> None:
    rfc = (ROOT / "docs" / "rfcs" / "RFC-0042-post-trade-outcome-feedback-loop.md").read_text(
        encoding="utf-8"
    )
    source_map = (ROOT / "docs" / "rfcs" / "RFC-0042-source-map-and-gap-analysis.md").read_text(
        encoding="utf-8"
    )
    platform_slice = (ROOT / "docs" / "rfcs" / "RFC-0042-platform-automation-slice1.md").read_text(
        encoding="utf-8"
    )
    cleanup_slice = (ROOT / "docs" / "rfcs" / "RFC-0042-cleanup-and-structure-slice2.md").read_text(
        encoding="utf-8"
    )
    domain_slice = (ROOT / "docs" / "rfcs" / "RFC-0042-domain-model-slice3.md").read_text(
        encoding="utf-8"
    )
    expected_snapshot_slice = (
        ROOT / "docs" / "rfcs" / "RFC-0042-expected-snapshot-slice4.md"
    ).read_text(encoding="utf-8")
    realized_source_slice = (
        ROOT / "docs" / "rfcs" / "RFC-0042-realized-source-adapters-slice5.md"
    ).read_text(encoding="utf-8")
    persistence_slice = (
        ROOT / "docs" / "rfcs" / "RFC-0042-persistence-events-slice6.md"
    ).read_text(encoding="utf-8")
    api_slice = (ROOT / "docs" / "rfcs" / "RFC-0042-api-openapi-slice7.md").read_text(
        encoding="utf-8"
    )
    handoff_slice = (ROOT / "docs" / "rfcs" / "RFC-0042-report-ai-handoffs-slice8.md").read_text(
        encoding="utf-8"
    )
    supportability_slice = (
        ROOT / "docs" / "rfcs" / "RFC-0042-supportability-observability-slice9.md"
    ).read_text(encoding="utf-8")
    gateway_workbench_slice = (
        ROOT / "docs" / "rfcs" / "RFC-0042-gateway-workbench-realization-slice10.md"
    ).read_text(encoding="utf-8")
    implementation_proof_slice = (
        ROOT / "docs" / "rfcs" / "RFC-0042-implementation-proof-slice11.md"
    ).read_text(encoding="utf-8")
    hardening_slice = (ROOT / "docs" / "rfcs" / "RFC-0042-hardening-review-slice12.md").read_text(
        encoding="utf-8"
    )
    index = (ROOT / "docs" / "rfcs" / "README.md").read_text(encoding="utf-8")
    wiki_index = (ROOT / "wiki" / "RFC-Index.md").read_text(encoding="utf-8")
    roadmap = (ROOT / "wiki" / "Roadmap.md").read_text(encoding="utf-8")
    supported_features = (ROOT / "wiki" / "Supported-Features.md").read_text(encoding="utf-8")
    development_workflow = (ROOT / "wiki" / "Development-Workflow.md").read_text(encoding="utf-8")

    required_sections = [
        "## 1. Critical Review of the Prior Draft",
        "## 6. Work-To-Be-Done Ledger Intake",
        "## 7. Source Map and Gap Policy",
        "## 8. First-Wave Support Boundary",
        "### Slice 1 - Platform Automation and Scaffolding Improvement",
        "### Slice 2 - Cleanup and Structure",
        "### Slice 10 - Gateway and Workbench Realization RFC Slice",
        "### Slice 11 - Implementation Proof",
        "### Slice 12 - Second-Last Hardening and Review",
        "### Slice 13 - Final Closure",
        "## 15. Supported-Features Ledger",
        "## 19. Final Gold-Pass Assessment",
        "## 20. Post-Closure WTBD Integration Audit",
    ]
    missing_sections = [section for section in required_sections if section not in rfc]

    assert missing_sections == []
    assert (
        "DONE - MANAGE BACKEND COMPLETE; FIRST-WAVE PRODUCT REALIZATION COMPLETE; SOURCE-OWNER ENRICHMENT REMAINS"
        in rfc
    )
    assert "RFC-0042-source-map-and-gap-analysis.md" in rfc
    assert "RFC-0042-platform-automation-slice1.md" in rfc
    assert "RFC-0042-cleanup-and-structure-slice2.md" in rfc
    assert "RFC-0042-domain-model-slice3.md" in rfc
    assert "RFC-0042-expected-snapshot-slice4.md" in rfc
    assert "RFC-0042-realized-source-adapters-slice5.md" in rfc
    assert "RFC-0042-persistence-events-slice6.md" in rfc
    assert "RFC-0042-api-openapi-slice7.md" in rfc
    assert "RFC-0042-report-ai-handoffs-slice8.md" in rfc
    assert "RFC-0042-supportability-observability-slice9.md" in rfc
    assert "RFC-0042-gateway-workbench-realization-slice10.md" in rfc
    assert "RFC-0042-implementation-proof-slice11.md" in rfc
    assert "RFC-0042-hardening-review-slice12.md" in rfc
    assert "RFC-0042-final-closure-slice13.md" in rfc
    assert (
        "Support below includes the manage backend authority plus the bounded first-wave product "
        "realization" in rfc
    )
    assert "Outcome review creation | Supported as manage backend authority" in rfc
    assert "Gold-standard conclusion" in rfc
    assert "genuinely reached the expected enterprise standard" in rfc
    assert "output/rfc0042-outcome-proof/20260505-024352/critical-review.json" in rfc
    assert "output/rfc0042-outcome-proof/20260505-025613/critical-review.json" in rfc
    assert "scripts/Start-CanonicalManage.ps1" in rfc
    assert "`lotus-gateway` composes manage-owned outcome-review truth" in rfc
    assert "`lotus-workbench` renders the" in rfc
    assert "outcome-review surface through Gateway/BFF contracts" in rfc
    assert "`lotus-manage` must not clone risk, performance, tax-lot, fill, cash" in rfc
    assert "`EXECUTION_EVIDENCE_BLOCKED`" in rfc
    assert "RFC41-WTBD-010" in rfc
    assert "DpmOutcomeReportInput" in rfc
    assert "DpmOutcomeAiEvidenceInput" in rfc
    assert "PM quality scoring | Not supported" in rfc
    assert "External execution integration | Not supported" in rfc
    assert "RFC42-WTBD-001" in rfc
    assert "RFC42-WTBD-008" in rfc
    assert "`lotus-gateway` PR #186/#187/#188/#189" in rfc
    assert "`lotus-workbench` PR #146/#147/#148" in rfc
    assert "`lotus-ai` PR #59/#60" in rfc
    assert "canonical-front-office-qa-20260509-225912.json" in rfc
    assert "feat/rfc0042-implementation" in rfc
    assert "output/rfc0042-outcome-proof/<timestamp>/" in rfc

    assert "## Slice 0 Result" in source_map
    assert "No route, persistence table, runtime capability" in source_map
    assert "## Slice 1 Platform Result" in source_map
    assert "sgajbi/lotus-platform#297" in source_map
    assert "## Slice 2 Cleanup and Structure Result" in source_map
    assert "wiki/Supported-Features.md" in source_map
    assert "## Slice 3 Domain Model and Pure Comparison Result" in source_map
    assert "src/core/outcomes/" in source_map
    assert "## Slice 4 Expected Snapshot Assembly Result" in source_map
    assert "does not default" in source_map
    assert "risk, performance, tax, FX, or execution-quality values" in source_map
    assert "## Slice 5 Realized Source Adapter Result" in source_map
    assert "`EXECUTION_EVIDENCE_BLOCKED`" in source_map
    assert "## Slice 6 Persistence, Repository, Events, and Retention Result" in source_map
    assert "0008_post_trade_outcome_reviews.sql" in source_map
    assert "## Slice 7 Certified Manage APIs and OpenAPI Quality Result" in source_map
    assert "src/api/routers/outcome_reviews.py" in source_map
    assert "source-refresh re-evaluation with append-only event evidence" in source_map
    assert "## Slice 8 Report Input and AI Evidence Input Handoffs Result" in source_map
    assert "DpmOutcomeReportInput" in source_map
    assert "DpmOutcomeAiEvidenceInput" in source_map
    assert "## Slice 9 Supportability, Observability, and Operator Diagnostics Result" in source_map
    assert "lotus_manage_outcome_review_supportability_total" in source_map
    assert "## Slice 10 Gateway and Workbench Realization RFC Result" in source_map
    assert "`lotus-gateway` RFC-0098" in source_map
    assert "`lotus-workbench` RFC-0098" in source_map
    assert "## Slice 11 Live Implementation Proof Result" in source_map
    assert "output/rfc0042-outcome-proof/20260505-024352/" in source_map
    assert "What/When/How OpenAPI guidance" in source_map
    assert "reserved PowerShell `$PID` variable" in source_map
    assert "## Slice 12 Hardening Review Result" in source_map
    assert "DPM_OUTCOME_REVIEW_IDEMPOTENCY_CONFLICT" in source_map
    assert "04b-idempotency-conflict-response.json" in source_map
    assert "## Slice 13 Final Closure Result" in source_map
    assert (
        "DONE - MANAGE BACKEND COMPLETE; FIRST-WAVE PRODUCT REALIZATION COMPLETE; SOURCE-OWNER ENRICHMENT REMAINS"
        in source_map
    )
    assert (
        "Skills/context/guidance decision: no central Lotus skill or context change is needed"
        in (source_map)
    )
    assert "First-Wave Outcome Dimension Posture" in source_map
    assert "Gateway and Workbench Realization Boundary" in source_map
    assert "RFC-0042 promotes manage backend outcome-review authority only" in source_map
    assert "Deferred Questions After Manage Closure" in source_map
    assert (
        "| Fill/order/execution detail | `lotus-core` or future execution/OMS owner |" in source_map
    )
    assert "| `EXECUTION_QUALITY` | Fill/order/execution source exists" in source_map
    assert "Workbench must consume Gateway/BFF only" in source_map
    assert "PB_SG_GLOBAL_BAL_001" in source_map
    assert "PortfolioLiquidityLadder" in rfc
    assert "`lotus-core` PR #356 / wiki `28c4ae2`" in rfc
    assert "PortfolioLiquidityLadder opening-cash" in source_map
    assert "PortfolioLiquidityLadder:v1" in roadmap
    assert (
        "PortfolioLiquidityLadder:v1` methodology truth through `lotus-core` PR #356"
        in supported_features
    )

    assert "Slice 1 - Platform Automation and Scaffolding Improvement" in platform_slice
    assert "sgajbi/lotus-platform#297" in platform_slice
    assert "source-degraded and reconciliation endpoint" in platform_slice
    assert "does not clone calculations owned by another Lotus app" in platform_slice
    assert "No supported feature is promoted by this slice" in platform_slice

    assert "Slice 2 - Cleanup and Structure" in cleanup_slice
    assert "No runtime `outcomes` authority exists yet" in cleanup_slice
    assert "No supported feature is promoted by Slice 2" in cleanup_slice
    assert "dedicated outcome domain" in cleanup_slice
    assert "API router" in cleanup_slice

    assert "Slice 3 - Domain Model and Pure Comparison Engine" in domain_slice
    assert "Unsupported dimensions cannot become `READY`" in domain_slice
    assert "PM scoring, AI judgment, and narrative generation are absent" in domain_slice
    assert "`10 passed`" in domain_slice

    assert "Slice 4 - Expected Snapshot Assembly" in expected_snapshot_slice
    assert "Handoff refs must belong to the wave" in expected_snapshot_slice
    assert "Missing values are" in expected_snapshot_slice
    assert "omitted rather than silently defaulted" in expected_snapshot_slice
    assert "`5 passed`" in expected_snapshot_slice

    assert (
        "Slice 5 - Realized Source Adapters and Degraded Source Handling" in realized_source_slice
    )
    assert "does not calculate source-owner truth locally" in realized_source_slice
    assert "Missing `EXECUTION_QUALITY` source" in realized_source_slice
    assert "WORKSPACE_SUMMARY_TWR_RETURN" in realized_source_slice
    assert "performance_sources.py" in realized_source_slice
    assert "RISK_METRICS_REPORT" in realized_source_slice
    assert "risk_sources.py" in realized_source_slice
    assert "HOLDINGS_AS_OF_CASH_BALANCE" in realized_source_slice
    assert "core_sources.py" in realized_source_slice
    assert "`17 passed`" in realized_source_slice
    assert "`20 passed`" in realized_source_slice
    assert "`18 passed`" in realized_source_slice

    assert "Slice 6 - Persistence, Repository, Events, and Retention" in persistence_slice
    assert "Review body is immutable" in persistence_slice
    assert "Postgres stores the complete review JSON" in persistence_slice
    assert "`5 passed`" in persistence_slice

    assert "Slice 7 - Certified Manage APIs and OpenAPI Quality" in api_slice
    assert "POST /api/v1/rebalance/outcome-reviews/preview" in api_slice
    assert "Source refresh reuses the immutable expected snapshot" in api_slice
    assert "No full RFC-0042 supported feature is promoted by Slice 7" in api_slice

    assert "Slice 8 - Report Input and AI Evidence Input Handoffs" in handoff_slice
    assert "DpmOutcomeReportInput" in handoff_slice
    assert "DpmOutcomeAiEvidenceInput" in handoff_slice
    assert "score_portfolio_manager" in handoff_slice
    assert "No full outcome-review product support is claimed" in handoff_slice

    assert "Slice 9 - Supportability, Observability, and Operator Diagnostics" in (
        supportability_slice
    )
    assert "lotus_manage_outcome_review_supportability_total" in supportability_slice
    assert "outcome_review.supportability.inspected" in supportability_slice
    assert "No live canonical product proof is claimed by this slice" in supportability_slice

    assert "Slice 10 - Gateway and Workbench Realization RFCs" in gateway_workbench_slice
    assert "`lotus-gateway` | `feat/rfc0042-outcome-realization` | `38d46f9`" in (
        gateway_workbench_slice
    )
    assert "`lotus-workbench` | `feat/rfc0042-outcome-realization` | `3b5182f`" in (
        gateway_workbench_slice
    )
    assert "/api/v1/dpm/command-center/outcome-reviews*" in gateway_workbench_slice

    assert "Slice 11 - Implementation Proof" in implementation_proof_slice
    assert "output/rfc0042-outcome-proof/20260505-024352/" in implementation_proof_slice
    assert "The accepted run is `passed`." in implementation_proof_slice
    assert "What/When/How guidance" in implementation_proof_slice
    assert "reserved `$PID` variable" in implementation_proof_slice
    assert "No full RFC-0042 product support is promoted by Slice 11" in implementation_proof_slice

    assert "Slice 12 - Second-Last Hardening and Review" in hardening_slice
    assert "output/rfc0042-outcome-proof/20260505-025613/" in hardening_slice
    assert "same-key changed-evidence" in hardening_slice
    assert "OutcomeReviewState" in hardening_slice
    assert "_handoff_ref" in hardening_slice
    assert "idempotency_conflict_rejected" in hardening_slice
    assert "No full RFC-0042 product support is promoted by Slice 12" in hardening_slice

    closure_slice = (ROOT / "docs" / "rfcs" / "RFC-0042-final-closure-slice13.md").read_text(
        encoding="utf-8"
    )
    assert "Slice 13 - Final Closure" in closure_slice
    assert "COMPLETE FOR MANAGE BACKEND" in closure_slice
    assert "FIRST-WAVE PRODUCT REALIZATION COMPLETE; SOURCE-OWNER ENRICHMENT REMAINS" in (
        closure_slice
    )
    assert "lotus-workbench/output/playwright/rfc42-wtbd-audit-20260506-fixed/" in closure_slice
    assert "No central Lotus skill or context change is required" in closure_slice
    assert "full Gateway/Workbench product experience" in closure_slice

    assert (
        "| RFC-0042 | Post-Trade Outcome Feedback Loop | DONE (MANAGE BACKEND COMPLETE; FIRST-WAVE PRODUCT REALIZATION COMPLETE; SOURCE-OWNER ENRICHMENT REMAINS)"
        in index
    )
    assert "API evidence: `docs/rfcs/RFC-0042-api-openapi-slice7.md`" in index
    assert "report/AI evidence: `docs/rfcs/RFC-0042-report-ai-handoffs-slice8.md`" in index
    assert (
        "supportability evidence: `docs/rfcs/RFC-0042-supportability-observability-slice9.md`"
        in index
    )
    assert (
        "Gateway/Workbench evidence: `docs/rfcs/RFC-0042-gateway-workbench-realization-slice10.md`"
        in index
    )
    assert "implementation proof: `docs/rfcs/RFC-0042-implementation-proof-slice11.md`" in index
    assert "hardening evidence: `docs/rfcs/RFC-0042-hardening-review-slice12.md`" in index
    assert "closure evidence: `docs/rfcs/RFC-0042-final-closure-slice13.md`" in index
    assert "source map: `docs/rfcs/RFC-0042-source-map-and-gap-analysis.md`" in index
    assert "Durable cross-RFC follow-up control" in index
    assert "docs/rfcs/RFC-worktobedone.md" in index
    assert "Mandatory branch hygiene for RFC work" in index
    assert "git branch -r --no-merged origin/main" in index
    assert "Closure truth that exists only on an unmerged side branch is not complete" in index
    assert "stranded-truth reconciliation" in development_workflow
    assert "git branch -r --no-merged origin/main" in development_workflow
    assert (
        "do not claim RFC closure while durable truth exists only on an unmerged side branch"
        in (development_workflow)
    )
    assert "gold-standard" in wiki_index
    assert "tightening on 2026-05-05" in wiki_index
    assert "Slice 3 pure domain comparison evidence" in wiki_index
    assert "Slice 4 expected snapshot assembly evidence" in wiki_index
    assert "Slice 5 realized source-degraded evidence" in wiki_index
    assert "Slice 6 persistence/events evidence" in wiki_index
    assert "Slice 7 certified\n  manage API/OpenAPI evidence" in wiki_index
    assert "Slice 8 report-input/AI-evidence handoff contracts" in wiki_index
    assert "Slice 9\n  supportability/observability diagnostics" in wiki_index
    assert "Slice 10 Gateway/Workbench realization RFC" in wiki_index
    assert "Slice 11 live manage implementation proof" in wiki_index
    assert "output/rfc0042-outcome-proof/20260505-024352/" in wiki_index
    assert "Slice 12 hardening proof" in wiki_index
    assert "output/rfc0042-outcome-proof/20260505-025613/" in wiki_index
    assert "`DONE` for the manage backend authority" in wiki_index
    assert "first-wave product realization" in roadmap
    assert "output/rfc0042-wtbd-audit-outcome-proof/20260505-211611/" in roadmap
    assert "lotus-workbench/output/playwright/rfc42-wtbd-audit-20260506-fixed/" in roadmap
    assert "Remaining roadmap work is source-owner methodology enrichment" in roadmap
    assert "rolling tracking-error methodology truth" in supported_features
    assert "`lotus-risk` PR #113" in supported_features
    assert "wiki `d1330ee`" in supported_features
    assert "rolling information-ratio methodology truth" in supported_features
    assert "`lotus-risk` PR #114" in supported_features
    assert "wiki `105b716`" in supported_features
    assert "`PortfolioCashflowProjection:v1` methodology truth" in supported_features
    assert "`lotus-core` PR #344" in supported_features
    assert "wiki `231bd75`" in supported_features
    assert "| Post-trade outcome feedback | RFC-0042 |" in supported_features
    assert (
        "Supported as RFC-0042 manage backend authority plus first-wave product realization"
        in supported_features
    )
    assert "output/rfc0042-outcome-proof/20260505-024352/" in supported_features
    assert "output/rfc0042-outcome-proof/20260505-025613/" in supported_features
    assert "output/rfc0042-outcome-proof/20260505-040212/" in supported_features
    assert "output/rfc0042-wtbd-audit-outcome-proof/20260505-211611/" in supported_features
    assert (
        "lotus-workbench/output/playwright/rfc42-wtbd-audit-20260506-fixed/" in supported_features
    )
    assert "Post-Trade Outcome Feedback Flow" in supported_features
    assert "DpmOutcomeReportInput" in supported_features
    assert "DpmOutcomeAiEvidenceInput" in supported_features
    assert "lotus-report / lotus-render / lotus-archive" in supported_features
    assert "lotus-ai governed narrative" in supported_features
    assert "canonical-front-office-qa-20260509-225912.json" in supported_features
    assert "output/rfc0042-outcome-proof/20260505-040212/" in wiki_index
    assert "output/rfc0042-wtbd-audit-outcome-proof/20260505-211611/" in wiki_index
    assert "lotus-workbench/output/playwright/rfc42-wtbd-audit-20260506-fixed/" in wiki_index
    assert "output/rfc0042-outcome-proof/20260505-040212/" in roadmap
    assert "Execution/OMS integration, PM quality scoring" in supported_features
    assert "Gateway command-center composition, Workbench timeline rendering" in supported_features
    assert "mandate health, monitoring exception, proof-pack" in supported_features
    assert "stable event identity plus retention, redaction, access, audit policy" in (
        supported_features
    )
    assert "`lotus-report` now has the bounded context consumer seam" in supported_features
    assert "`lotus-ai` has bounded DPM memo/narrative consumers plus an AI-owned" in (
        supported_features
    )
    assert "`lotus-archive` PR #25 has the generated-document/client-delivery" in supported_features
    assert "GET /documents/{document_id}/source-events" in supported_features
    assert "Remaining OMS and PM-scoring source-event families" in supported_features
    assert "Supported as RFC-0042 full product experience" not in supported_features
    assert "Gateway and Workbench product support must not be claimed" not in rfc
    assert (
        "The full front-office product outcome remains deliberately unclaimed until "
        "Gateway/Workbench implementation" not in rfc
    )

    work_to_be_done = (ROOT / "docs" / "rfcs" / "RFC-worktobedone.md").read_text(encoding="utf-8")
    assert "## Completed WTBD RFC Reintegration Index" in work_to_be_done
    assert (
        "Completed and audited WTBD truth belongs in the original RFC that introduced the business change."
        in work_to_be_done
    )
    assert (
        "| RFC-0038 | RFC38-WTBD-001 through RFC38-WTBD-006 and RFC38-WTBD-008 are incorporated into "
        "`docs/rfcs/RFC-0038-mandate-digital-twin-health-and-command-center.md`." in work_to_be_done
    )
    assert (
        "| RFC-0042 | RFC42-WTBD-001 through RFC42-WTBD-005 are incorporated into "
        "`docs/rfcs/RFC-0042-post-trade-outcome-feedback-loop.md`." in work_to_be_done
    )
    assert "RFC42 Gold-Pass Audit And RFC Reintegration - 2026-05-09" in work_to_be_done
    assert "RFC42-WTBD-001 through RFC42-WTBD-005 are completed" in work_to_be_done
    assert "stale RFC wording that said Gateway/Workbench product proof remained unclaimed" in (
        work_to_be_done
    )
    assert "RFC Work To Be Done Ledger" in work_to_be_done
    assert "## Mainline WTBD Control Snapshot" in work_to_be_done
    assert "| Total WTBD items | 59 |" in work_to_be_done
    assert "| Done on merged/published truth | 43 |" in work_to_be_done
    assert "| Partial / in progress | 4 |" in work_to_be_done
    assert "| Remaining / open | 12 |" in work_to_be_done
    assert "RFC36-WTBD-006 is now closed as a no-migration-required" in work_to_be_done
    assert "`lotus-platform` PR #316" in work_to_be_done
    assert "RFC38-WTBD-004 - PM-Book Discovery" in work_to_be_done
    assert "source-owned populated PM-book monitoring path" in work_to_be_done
    assert "RFC38-WTBD-003 hardening" in work_to_be_done
    assert "ready/partial/empty seed-posture checks" in work_to_be_done
    assert "The current hardening adds platform seed `posture_checks`" in work_to_be_done
    assert "RFC41-WTBD-003 - Tactical House-View, Risk-Event, And Implicit Campaign Cohorts" in (
        work_to_be_done
    )
    assert "`RiskEventAffectedCohort:v1` at `POST /analytics/risk/risk-event-cohorts/evaluate`" in (
        work_to_be_done
    )
    assert "`lotus-risk.wiki` commit `91f933a`" in work_to_be_done
    assert "`lotus-platform` PR #313 (`4218d4319d5dac82e87106429fadb14247c36515`)" in (
        work_to_be_done
    )
    assert "GET /api/v1/rebalance/portfolio-memory/{portfolio_id}" in work_to_be_done
    assert "RFC40-WTBD-001 - Gateway Proof-Pack Composition" in work_to_be_done
    assert "Completed, merged, CI-proven, and wiki-published through `lotus-gateway` PR #195" in (
        work_to_be_done
    )
    assert "`lotus-gateway` merge commit `f706853`" in work_to_be_done
    assert "`lotus-gateway` wiki publication commit `7b97aac`" in work_to_be_done
    assert "Completed, merged, CI-proven, and wiki-published through `lotus-workbench` PR #156" in (
        work_to_be_done
    )
    assert "`lotus-workbench` merge commit `8acf276`" in work_to_be_done
    assert "`lotus-workbench` wiki publication commit `1b4b095`" in work_to_be_done
    assert "RFC40-WTBD-003 - Full Front-Office Proof-Pack Product Realization" in work_to_be_done
    assert (
        "Completed for the first-wave full front-office proof-pack product path" in work_to_be_done
    )
    assert (
        "`lotus-manage` PR #117 made proof-pack generation replay deterministic source identities"
        in (work_to_be_done)
    )
    assert "canonical-front-office-qa-20260507-124405.json" in work_to_be_done
    assert "`dpm.proof_pack` as `ready` with proof pack `dpp_c09f73d0`" in work_to_be_done
    assert "RFC40-WTBD-004 - Report Materialization From `DpmProofPackReportInput`" in (
        work_to_be_done
    )
    assert "Completed on 2026-05-07 across the owning repositories" in work_to_be_done
    assert "`lotus-render` PR #11" in work_to_be_done
    assert "`lotus-report` PR #90" in work_to_be_done
    assert "`lotus-archive` PR #23" in work_to_be_done
    assert "RFC40-WTBD-005 - AI PM Memo Generation From `DpmProofPackAiEvidenceInput`" in (
        work_to_be_done
    )
    assert "`lotus-ai` PR #61" in work_to_be_done
    assert "`lotus-gateway` PR #198" in work_to_be_done
    assert "`lotus-workbench` PR #166" in work_to_be_done
    assert "canonical-front-office-qa-20260507-210641.json" in work_to_be_done
    assert "packrun_dpm_pm_memo_air_b69bcfd16d7341b889b0037f884839fa" in work_to_be_done
    assert "RFC40-WTBD-006 - Broader Risk And Performance Proof-Pack Enrichment" in (
        work_to_be_done
    )
    assert "`risk_impact` and `performance_context` sections preserve" in work_to_be_done
    assert "src/core/proof_packs/source_analytics.py" in work_to_be_done
    assert "risk_context` / `performance_context` source" in work_to_be_done
    assert "output/rfc0040-proof/20260507-230235/manifest.json" in work_to_be_done
    assert "risk_source_state=READY" in work_to_be_done
    assert "performance_source_state=DEGRADED" in work_to_be_done
    assert "RFC40-WTBD-007 - Authoritative Transaction-Cost Curve" in work_to_be_done
    assert "`TransactionCostCurve:v1`" in work_to_be_done
    assert "AuthoritativeTransactionCostContext" in work_to_be_done
    assert "RFC40-WTBD-008 - Sustainability Preferences And Client Restriction Profiles" in (
        work_to_be_done
    )
    assert "`eligibility_and_restrictions` and `sustainability_controls`" in work_to_be_done
    assert "RFC39-WTBD-006 - Authoritative Transaction-Cost And Cost-Aware Alternatives" in (
        work_to_be_done
    )
    assert "`COST_AWARE` construction method" in work_to_be_done
    assert "RFC39-WTBD-004 - ESG/Restriction-Aware Construction Support" in work_to_be_done
    assert "`ClientRestrictionProfile:v1` and `SustainabilityPreferenceProfile:v1`" in (
        work_to_be_done
    )
    assert "hard client restrictions" in work_to_be_done
    assert "automatic ESG approval" in work_to_be_done
    assert "TRANSACTION_COST_CURVE_APPLIED_TO_CANDIDATE_NOTIONALS" not in work_to_be_done
    assert "market-impact modelling, venue routing" in work_to_be_done
    assert "lotus-gateway` PR #199" in work_to_be_done
    assert "lotus-workbench` PR #167" in work_to_be_done
    assert "lotus-platform` PR #307" in work_to_be_done
    assert "dpm-portfolio-memory-live.png" in work_to_be_done
    assert "MANDATE_HEALTH_SNAPSHOT" in work_to_be_done
    assert "MANDATE_MONITORING_EXCEPTION" in work_to_be_done
    assert "event identity, retention, redaction, access, and audit policy are implemented" in (
        work_to_be_done
    )
    assert "`lotus-report` PR #92" in work_to_be_done
    assert "`lotus-report` PR #93" in work_to_be_done
    assert "GET /reports/jobs/{job_id}/portfolio-memory-events" in work_to_be_done
    assert "Manage report-input APIs now attach bounded portfolio-memory context" in work_to_be_done
    assert "tests/unit/core/test_outcome_handoffs.py" in work_to_be_done
    assert "`lotus-ai` PR #62 adds bounded portfolio-memory consumers" in work_to_be_done
    assert "`lotus-ai` PR #64 adds the AI-owned workflow-pack source-event family" in (
        work_to_be_done
    )
    assert "GET /platform/workflow-packs/source-events" in work_to_be_done
    assert "GET /platform/workflow-packs/runs/{run_id}/source-events" in work_to_be_done
    assert "`lotus-ai` wiki publication commit `a4e70d3`" in work_to_be_done
    assert "no-reconstruction source-authority policy" in work_to_be_done
    assert "`lotus-archive` PR #25" in work_to_be_done
    assert "`aa3a3a8f28b666cb85100c0859f77ff2dab9cede`" in work_to_be_done
    assert "`lotus-archive.wiki` publication commit `d5e5918`" in work_to_be_done
    assert "lotus-archive.generated_document_client_communication.v1" in work_to_be_done
    assert "GET /documents/{document_id}/source-events" in work_to_be_done
    assert "no raw document bytes, storage keys, raw report payloads, or raw client references" in (
        work_to_be_done
    )
    assert "Latest WTBD-006 risk rolling-tracking-error methodology proof" in work_to_be_done
    assert "`lotus-risk` PR #113" in work_to_be_done
    assert "`e00ece9279082a96071bd9e745b7211232b82db6`" in work_to_be_done
    assert "`lotus-risk.wiki` commit `d1330ee`" in work_to_be_done
    assert "`RollingRiskMetricsReport:v1`" in work_to_be_done
    assert "percentage-point input conventions, decimal conversion, inner date alignment" in (
        work_to_be_done
    )
    assert "tests/unit/test_methodology_docs.py" in work_to_be_done
    assert "this advances RFC42-WTBD-006 but does not close it" in work_to_be_done
    assert "Latest WTBD-006 risk rolling-information-ratio methodology proof" in work_to_be_done
    assert "`lotus-risk` PR #114" in work_to_be_done
    assert "`ffa881e3266c09a4d48044b50df5bb2db43bd489`" in work_to_be_done
    assert "`lotus-risk.wiki` commit `105b716`" in work_to_be_done
    assert "`ROLLING_INFORMATION_RATIO` source-owner methodology" in work_to_be_done
    assert "zero-tracking-error flagging" in work_to_be_done
    assert "rolling active-risk contract test" in work_to_be_done
    assert "local test-pyramid proof showing `307` unit, `94`" in work_to_be_done
    assert "`22` e2e tests within policy" in work_to_be_done
    assert "RFC41-WTBD-006 - Workbench Wave Command Center" in work_to_be_done
    assert "Completed, merged, CI-proven, and wiki-published through `lotus-gateway` PR #196" in (
        work_to_be_done
    )
    assert "`c29d895f08b7316dd363d77559623eabfc3137e8`" in work_to_be_done
    assert "`fc427a9`" in work_to_be_done
    assert "RFC41-WTBD-008 - Report Materialization From Wave / Proof-Pack Evidence" in (
        work_to_be_done
    )
    assert "Status: Completed on merged, validated, and wiki-published owning-repo truth." in (
        work_to_be_done
    )
    assert "`lotus-manage` PR #124" in work_to_be_done
    assert "`lotus-report` PR #91" in work_to_be_done
    assert "`lotus-render` PR #12" in work_to_be_done
    assert "`lotus-archive` PR #24" in work_to_be_done
    assert "RFC41-WTBD-009 - AI PM Memo Generation From Wave Evidence" in work_to_be_done
    assert "`lotus-ai` PR #63" in work_to_be_done
    assert "`lotus-gateway` PR #201" in work_to_be_done
    assert "`lotus-workbench` PR #168" in work_to_be_done
    assert "`dpm_wave_pm_memo.pack@v1`" in work_to_be_done
    assert "review-required support-only memo payload" in work_to_be_done
    assert "This WTBD is complete for the first-wave governed product path" in work_to_be_done
    assert "RFC37-WTBD-006" in work_to_be_done
    assert "`lotus-platform` PR #310" in work_to_be_done
    assert "`lotus-platform` wiki publication commit `884bec3`" in work_to_be_done
    assert "Canonical-DPM-Demo-Story.md" in work_to_be_done
    assert "external OMS execution" in work_to_be_done
    assert "PM quality scoring" in work_to_be_done
    assert "client communication execution" in work_to_be_done
    assert "## RFC-0042 - Post-Trade Outcome Feedback Loop" in work_to_be_done
    assert "RFC42-WTBD-001" in work_to_be_done
    assert "RFC42-WTBD-008" in work_to_be_done
    assert "no item in this ledger is a supported-feature claim" in work_to_be_done
    assert "Post-merge audit rerun" in work_to_be_done
    assert "output/rfc0042-outcome-proof/20260505-040212/critical-review.json" in (work_to_be_done)
    assert "WTBD audit refresh on 2026-05-06" in work_to_be_done
    assert "output/rfc0042-wtbd-audit-outcome-proof/20260505-211611/critical-review.json" in (
        work_to_be_done
    )
    assert (
        "lotus-workbench/output/playwright/rfc42-wtbd-audit-20260506-fixed/live-validation-summary.json"
        in work_to_be_done
    )
    assert "source_system`, `source_id`, and `content_hash` lineage rendered as `N/A`" in (
        work_to_be_done
    )
    assert "relative `--output-root`" in work_to_be_done
    assert "Workbench must consume Gateway/BFF only" in work_to_be_done
    assert "PM quality scoring" in work_to_be_done
    assert "pending PR publication" not in work_to_be_done
    assert "Completed, merged, CI-proven, and wiki-published through `lotus-core` PR #339" in (
        work_to_be_done
    )
    assert "and `lotus-manage` PR #126" in work_to_be_done
    assert "RFC41-WTBD-004 - Risk And Performance Aggregate Enrichment" in work_to_be_done
    assert "Latest WTBD-006 performance MWR source-truth proof" in work_to_be_done
    assert "Latest WTBD-006 performance contribution source-truth proof" in work_to_be_done
    assert "Latest WTBD-006 performance attribution source-truth proof" in work_to_be_done
    assert "Latest WTBD-006 core realized-outcome source-boundary proof" in work_to_be_done
    assert "lotus-core` PR #343" in work_to_be_done
    assert "`25cbff191d681a6518dfc7072dc2a8c9cf2fd7f0`" in work_to_be_done
    assert "`lotus-core.wiki` commit `a9d1f68`" in work_to_be_done
    assert "Latest WTBD-006 core cashflow-projection methodology proof" in work_to_be_done
    assert "`lotus-core` PR #344" in work_to_be_done
    assert "`3a29c3ea92fce92d39fbc91f325bd04cb1157d20`" in work_to_be_done
    assert "`lotus-core.wiki` commit `231bd75`" in work_to_be_done
    assert "PortfolioCashflowProjection:v1` methodology" in work_to_be_done
    assert "same-day booked/projected additivity" in work_to_be_done
    assert "Latest WTBD-006 core transaction-ledger-window methodology proof" in work_to_be_done
    assert "`lotus-core` PR #347" in work_to_be_done
    assert "`7aef82bc8f9232c62333b8386001527b19829f86`" in work_to_be_done
    assert "`lotus-core.wiki` commit `6bb1041`" in work_to_be_done
    assert "`TransactionLedgerWindow:v1` methodology" in work_to_be_done
    assert "reporting-currency restatement" in work_to_be_done
    assert "FX attribution" in work_to_be_done
    assert "Latest WTBD-006 core portfolio-tax-lot methodology proof" in work_to_be_done
    assert "`lotus-core` PR #346" in work_to_be_done
    assert "`e48d85a98ae3f53199bdccbe2e83f6304c9e050c`" in work_to_be_done
    assert "`lotus-core.wiki` commit `f37af67`" in work_to_be_done
    assert "`PortfolioTaxLotWindow:v1` methodology" in work_to_be_done
    assert "empty full-portfolio" in work_to_be_done
    assert "jurisdiction-specific tax advice" in work_to_be_done
    assert "Latest WTBD-006 core transaction-cost-curve methodology proof" in work_to_be_done
    assert "`lotus-core` PR #345" in work_to_be_done
    assert "`83d791d0e599f06a2c0caab6eaba647f717d4658`" in work_to_be_done
    assert "`lotus-core.wiki` commit `154ae27`" in work_to_be_done
    assert "`TransactionCostCurve:v1` methodology" in work_to_be_done
    assert "observed booked-fee aggregation" in work_to_be_done
    assert "notional-weighted average bps" in work_to_be_done
    assert "best execution" in work_to_be_done
    assert "Latest WTBD-006 core holdings-as-of methodology proof" in work_to_be_done
    assert "`lotus-core` PR #348" in work_to_be_done
    assert "`0a8785e0a4be7ea737b40eded07bd9c7f8002f25`" in work_to_be_done
    assert "`lotus-core.wiki` commit `2a428eb`" in work_to_be_done
    assert "`HoldingsAsOf:v1` methodology" in work_to_be_done
    assert "snapshot-versus-history fallback" in work_to_be_done
    assert "reporting-currency cash balances" in work_to_be_done
    assert "PortfolioLiquidityLadder:v1` methodology" in work_to_be_done
    assert "`lotus-core` PR #356" in work_to_be_done
    assert "Latest WTBD-006 core market-data coverage methodology proof" in work_to_be_done
    assert "`lotus-core` PR #349" in work_to_be_done
    assert "`4101f1ba321b8464093c12358e57f5c448440413`" in work_to_be_done
    assert "`lotus-core.wiki` commit `9be04cc`" in work_to_be_done
    assert "`MarketDataCoverageWindow:v1` methodology" in work_to_be_done
    assert "latest observation selection at or before `as_of_date`" in work_to_be_done
    assert "price and FX freshness posture" in work_to_be_done
    assert "valuation methodology, FX attribution" in work_to_be_done
    assert "Latest WTBD-006 core DPM source-readiness methodology proof" in work_to_be_done
    assert "`lotus-core` PR #350" in work_to_be_done
    assert "`c17bfa3298470375faa0b5e15bf369fa88a70597`" in work_to_be_done
    assert "`lotus-core.wiki` commit `e3fd859`" in work_to_be_done
    assert "`DpmSourceReadiness:v1` methodology" in work_to_be_done
    assert "fail-closed source-family precedence" in work_to_be_done
    assert "mandate approval, client suitability" in work_to_be_done
    assert "OpenAPI quality, API vocabulary" in work_to_be_done
    assert "tests/unit/docs/test_source_data_product_boundaries.py" in work_to_be_done
    assert "stateful lotus-core source resolution" in work_to_be_done
    assert "stateful lotus-core portfolio/position timeseries normalization" in work_to_be_done
    assert (
        "stateful lotus-core portfolio/position, benchmark, and source-currency normalization"
        in (work_to_be_done)
    )
    assert "downstream no-reconstruction posture" in work_to_be_done
    assert "`aggregate_metrics.source_analytics`" in work_to_be_done
    assert "does not calculate risk or performance methodology locally" in work_to_be_done
    assert "tests/unit/test_rfc0041_evidence_script.py" in work_to_be_done
    assert "not complete by mainline definition until merge and wiki publication" not in (
        work_to_be_done
    )

    assert "## Product Readiness At A Glance" in supported_features
    assert "## WTBD Product-Readiness Roadmap" in supported_features
    assert "flowchart LR" in supported_features
    assert "developers, business users, operations, sales/pre-sales" in supported_features
    assert "59 WTBD items: 43 done on merged/published truth, 4 partial" in (supported_features)
    assert "`lotus-platform` PR #310 and wiki publication commit `884bec3`" in (supported_features)
    assert "Canonical DPM demo story" in supported_features
    assert (
        "MWR methodology truth, contribution methodology truth, and attribution methodology truth"
        in supported_features
    )
    assert "contribution methodology truth" in supported_features
    assert "attribution methodology truth" in supported_features
    assert "current core slices" in supported_features
    assert "market-data coverage, DPM source-readiness" in supported_features
    assert "transaction-ledger row measures" in supported_features
    assert (
        "cashflow projection totals, liquidity-ladder buckets, tax lots, and observed "
        "transaction-cost evidence"
    ) in supported_features
    assert "`MarketDataCoverageWindow:v1` methodology truth through `lotus-core` PR #349" in (
        supported_features
    )
    assert "`DpmSourceReadiness:v1` methodology truth through `lotus-core` PR #350" in (
        supported_features
    )
    assert "`HoldingsAsOf:v1` methodology truth through `lotus-core` PR #348" in (
        supported_features
    )
    assert "`TransactionLedgerWindow:v1` methodology truth through `lotus-core` PR #347" in (
        supported_features
    )
    assert "`PortfolioTaxLotWindow:v1` methodology truth through `lotus-core` PR #346" in (
        supported_features
    )
    assert "`TransactionCostCurve:v1` methodology truth through `lotus-core` PR #345" in (
        supported_features
    )
    assert (
        "source-owned observed transaction-cost evidence from `TransactionCostCurve:v1` with merged source-owner methodology proof"
        in (supported_features)
    )
    assert "transaction-ledger row measures" in supported_features
    assert "cashflow projection totals" in supported_features
    assert "benchmark context" in supported_features
    assert "PM-book-backed monitoring cohort resolution" in supported_features
    assert "PortfolioManagerBookMembership:v1" in supported_features
    assert "source-owned risk/performance enrichment from selected construction alternatives" in (
        supported_features
    )
    assert "source-owned observed transaction-cost evidence from `lotus-core`" in (
        supported_features
    )
    assert "Core restriction and sustainability profile sourcing" in supported_features
    assert "`ClientRestrictionProfile:v1` and `SustainabilityPreferenceProfile:v1`" in (
        supported_features
    )
    assert (
        "optional `ClientRestrictionProfile:v1`, `SustainabilityPreferenceProfile:v1`, and `PortfolioCashflowProjection:v1`"
        in (supported_features)
    )
    assert "restricted active model targets can block eligibility health" in supported_features
    assert "source-owned negative projected net cashflow can raise cash-liquidity attention" in (
        supported_features
    )
    assert "cost-aware comparison from `lotus-core` `TransactionCostCurve:v1`" in (
        supported_features
    )
    assert "`COST_AWARE` applies source-owned observed average cost bps" in supported_features
    assert "Local estimated construction cost remains labelled separately" in supported_features
    assert "src/core/proof_packs/source_analytics.py" in supported_features
    assert "output/rfc0040-proof/20260507-230235/manifest.json" in supported_features
    assert "output/rfc0040-proof/20260507-230235/critical-review.json" in supported_features
    assert "Explicit portfolio-list waves" in supported_features
    assert "`aggregate_metrics.source_analytics`" in supported_features
    assert "manage does not recalculate risk or performance" in supported_features
    assert "governed rebalance-wave report materialization in report/render/archive" in (
        supported_features
    )
    assert "AI memo generation from wave evidence" in supported_features
    assert "`lotus-ai` owns the guarded wave PM memo workflow pack" in (supported_features)
    assert (
        "Gateway and Workbench consume those AI workflows without local prompt or memo generation"
        in (supported_features)
    )
    assert "Gateway proof-pack composition is implementation-backed" in supported_features
    assert (
        "Supported as a manage backend foundation and first-wave Gateway/Workbench product path"
        in (supported_features)
    )
    assert "canonical live validation captured `dpm-portfolio-memory-live.png`" in (
        supported_features
    )
    assert "persisted mandate health snapshots, monitoring exceptions, proof packs" in (
        supported_features
    )
    assert (
        "Workbench proof-pack review UX is implementation-backed through `lotus-workbench` PR #156"
        in (supported_features)
    )
    assert "Full first-wave canonical product realization is live-proven" in supported_features
    assert (
        "First-wave full proof-pack product realization is supported for the canonical portfolio"
        in (supported_features)
    )
    assert "report/render/archive proof-pack materialization in owning services" in (
        supported_features
    )
    assert "governed PM memo request posture are implementation-backed" in supported_features
    assert "A WTBD is not complete until merged to `main`" in supported_features
