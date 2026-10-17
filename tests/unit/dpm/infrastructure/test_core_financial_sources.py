"""Native normalization has independent expected domain facts and refusal outcomes."""

from dataclasses import replace
from decimal import Decimal, Inexact, Rounded, ROUND_DOWN, ROUND_HALF_EVEN, ROUND_UP, localcontext

import pytest
from pydantic import ValidationError

import src.infrastructure.composites.core_financial_sources as source_module
from src.core.common.canonical import hash_canonical_payload
from src.core.composite_eligibility.observations import (
    MonthlyEligibilityObservations,
    MonthlyFlowObservation,
    MonthlyPortfolioObservations,
)
from src.core.composite_eligibility.policy import MonthlyPolicyScope
from src.core.composite_eligibility.source import MonthlyEligibilitySourceRequest
from src.core.composite_eligibility.staged_ports import CandidateUniverseRequest
from src.infrastructure.composites.core_financial_sources import (
    CoreCandidateUniverseSource,
    CoreMonthlyEligibilitySource,
    exact_money,
    manage_role_order,
    registry_binding,
)
from src.infrastructure.composites.core_source_custody import (
    CORE_ROLE_ORDER,
    CoreCutAddress,
    RegistryDeclaration,
    RegistryMember,
    RetainedPortfolio,
    RetainedRegistry,
    RoleCapture,
)
from tests.unit.dpm.infrastructure.test_core_financial_configuration import H, configuration

NOW = "2026-10-01T00:00:00.000000Z"


def test_native_controlled_source_requires_an_explicit_paired_verifier_before_reads():
    reader = Reader()
    source = CoreMonthlyEligibilitySource(configuration(), reader, controlled_synthetic=True)
    assert source.resolve(monthly_request(reader)).observations is None
    assert reader.calls == []


@pytest.mark.parametrize(
    "boundary",
    [
        "complete",
        "singletons",
        "disjoint",
        "substituted",
        "superset",
        "overlap",
        "root_order",
        "count",
        "mixed_address",
    ],
)
def test_financial_manifest_complete_reader_monthly_assembly_and_real_proof(monkeypatch, boundary):
    from src.core.composite_eligibility.source_assembly import assembly_verification_request
    from src.infrastructure.composites.controlled_assembly_verifier import (
        ControlledAssemblyVerifierConfiguration,
    )
    from src.infrastructure.composites.core_source_reader import CoreHttpRetainedReader
    from tests.unit.dpm.infrastructure.test_controlled_assembly_verifier import harness
    from tests.unit.dpm.infrastructure.test_core_source_reader import (
        digest,
        encoded,
        rebind_financial_groups,
        source_request,
    )
    from tests.unit.dpm.composites.test_native_source_custody import owner_domain_digest

    fixture_scope = harness.__wrapped__(monkeypatch)
    h = next(fixture_scope)
    try:
        ids = ["P1", "P2", "P3"]
        hashes = [h.records[(pid, "INPUTS")][0]["input_content_hash"] for pid in ids]
        groups = (
            [[pid] for pid in ids]
            if boundary == "singletons"
            else (
                [ids[:2], ids[2:]]
                if boundary in ("disjoint", "overlap", "mixed_address")
                else [ids]
            )
        )
        committed = None
        if boundary == "superset":
            committed = [hashes + ["a" * 64]]
        elif boundary == "root_order":
            committed = [list(reversed(hashes))]
        elif boundary == "overlap":
            committed = [hashes[:2], hashes[1:]]
        elif boundary == "mixed_address":
            committed = [hashes, hashes]
        financial = rebind_financial_groups(
            h.config.financial,
            h.records,
            h.roots,
            groups,
            committed=committed,
            count_offset=1 if boundary == "count" else 0,
        )
        expected = h.expected.model_dump(mode="json")
        if boundary == "substituted":
            row = h.records[("P1", "INPUTS")][0]
            row["declaration"]["settled_unencumbered"]["amount"] = "1.00"
            row["graph"]["settled_unencumbered"]["amount"] = "1.00"
            row["input_content_hash"] = digest(
                {"contract": "PortfolioFinancialSourceCutInput:v1", "selection": row["declaration"]}
            )
            row["graph_content_hash"] = owner_domain_digest(
                "PortfolioFinancialSourceCut:v1", "cut", row["graph"]
            )
            expected["portfolios"][0]["settled_unencumbered_cash"] = "1.00"
        expected = MonthlyEligibilityObservations.model_validate(expected)
        document = h.config.model_dump(mode="json")
        document.update(
            financial=financial.model_dump(mode="json"),
            expected_observations_digest=hash_canonical_payload(expected.model_dump(mode="json")),
        )
        h.verifier.configuration = ControlledAssemblyVerifierConfiguration.model_validate_json(
            encoded(document)
        )
        reader = CoreHttpRetainedReader(h.config.reader, h.client_a, members=financial.members)
        source = CoreMonthlyEligibilitySource(financial, reader, controlled_synthetic=True)
        request = source_request(financial, expected)
        if boundary in ("complete", "singletons", "disjoint"):
            assembly = source.assemble(request)
            pair = h.verifier.verify_with_proof(assembly_verification_request(assembly))
            assert (
                pair is not None
                and pair.proof.result.native_custody_digest == assembly.native_custody.content_hash
            )
            assert len(h.signer.calls) == 1
            assert assembly.observations == expected
        else:
            refused = set()
            assembly = None
            try:
                assembly = source.assemble(request)
            except ValueError as exc:
                assert "FINANCIAL_MEMBERSHIP" in str(exc)
                refused.add("assembler")
            try:
                h.verifier.verify_with_proof(
                    assembly_verification_request(assembly) if assembly is not None else h.request
                )
            except ValueError as exc:
                assert "FINANCIAL_MEMBERSHIP" in str(exc)
                refused.add("verifier")
            assert refused == {"assembler", "verifier"}, {
                "refused": sorted(refused),
                "signatures": len(h.signer.calls),
            }
            assert h.signer.calls == []
        assert {call["view"] for call in h.calls_a} >= {"CUT", "INPUTS", "CAPTURES"}
        assert {call["view"] for call in h.calls_c} >= {"CUT", "INPUTS", "CAPTURES"}
    finally:
        fixture_scope.close()


def test_native_source_consumes_the_immutable_pair_without_mutable_last_proof(monkeypatch):
    from src.core.composite_eligibility.native_source_verification import (
        MonthlySourceAdmissionProof,
        NativeAssemblyVerification,
    )
    from src.core.composite_eligibility.source_assembly import assembly_verification_request
    from tests.unit.dpm.composites.test_native_source_verification import proof_material

    assembly, material, _ = proof_material()
    proof = MonthlySourceAdmissionProof.model_validate(material)
    requests = []

    class FixedSyntheticVerifier:
        def verify_with_proof(self, request):
            requests.append(request)
            return NativeAssemblyVerification(proof.result.receipt, proof)

    source = CoreMonthlyEligibilitySource(
        None, Reader(), verifier=FixedSyntheticVerifier(), controlled_synthetic=True
    )
    monkeypatch.setattr(source, "assemble", lambda request: assembly)
    resolution = source.resolve(monthly_request(Reader()))
    assert requests == [assembly_verification_request(assembly)]
    assert resolution.source_assembly_evidence.native_proof == proof
    assert resolution.source_assembly_evidence.verification == proof.result.receipt
    # This fixed fixture proves plumbing only, with no current deployment trust admission.


class Reader:
    def __init__(self):
        self.calls = []
        config = configuration()
        self.retained_registry = RetainedRegistry(
            address=config.registry,
            tenant_id=config.tenant_id,
            definition_version="v1",
            coverage_from="2026-09-01",
            coverage_to="2026-09-30",
            generated_at=NOW,
            declared_coverage="COMPLETE",
            expected_population_count=3,
            members=tuple(
                RegistryMember(
                    provider_namespace="native",
                    source_member_id=f"member{index}",
                    portfolio_id=f"P{index}",
                    declarations=(
                        RegistryDeclaration(
                            effective_from="2026-09-01",
                            effective_to=None,
                            definition_version="v1",
                            currency="SGD",
                            included=True,
                            discretionary=flag,
                        ),
                    ),
                )
                for index, flag in enumerate((False, None, True), 1)
            ),
        )
        self.portfolios = {}
        for member in config.members:
            observation = MonthlyPortfolioObservations(
                portfolio_id=member.portfolio_id,
                currency="SGD",
                prior_month_end_assets="1000",
                prior_assets_as_of="2026-08-31",
                month_end_assets="1100",
                settled_unencumbered_cash="0",
                cash_as_of="2026-09-30",
                discretionary=None,
                funded=False,
                invested=None,
                readiness_as_of="2026-09-30",
                flow_coverage_from="2026-09-01",
                flow_coverage_to="2026-09-30",
                flows=[],
            )
            self.portfolios[member.portfolio_id] = self.retained(member.financial_cut, observation)

    @staticmethod
    def retained(address, observation, **changes):
        products = (
            "PortfolioTimeseriesInput",
            "PortfolioTimeseriesInput",
            "PortfolioFinancialSourceObservations",
            "PortfolioFinancialSourceObservations",
            "PortfolioFinancialFlowObservations",
        )
        return RetainedPortfolio(
            address=address,
            tenant_id="tenant",
            registry_root=H,
            generated_at=NOW,
            roles=tuple(
                RoleCapture(
                    role=role,
                    product_name=product,
                    product_version="v1",
                    source_content_hash="sha256:" + str(index) * 64,
                    receipt_job_id=f"native/job/{index}",
                    descriptor_content_hash=hash_canonical_payload(
                        observation.model_dump(mode="json")
                    ),
                )
                for index, (role, product) in enumerate(
                    zip(CORE_ROLE_ORDER, products, strict=True), 1
                )
            ),
            observations=observation,
            cash_semantic_definition="explicit-settled-unencumbered-v1",
            cash_semantic_revision="source-revision1",
            **changes,
        )

    def registry(self, *, tenant_id: str, address: CoreCutAddress) -> RetainedRegistry | None:
        self.calls.append((tenant_id, address))
        return self.retained_registry

    def portfolio(
        self, *, tenant_id: str, portfolio_id: str, address: CoreCutAddress
    ) -> RetainedPortfolio | None:
        self.calls.append((tenant_id, portfolio_id, address))
        return self.portfolios.get(portfolio_id)


def expected_observations(reader):
    # This expected projection is specified independently of the normalizer.
    config = configuration()
    return MonthlyEligibilityObservations(
        product_name="CompositeMonthlyEligibilityObservations",
        product_version="v1",
        evidence_class="SOURCE_UNVERIFIED",
        tenant_id="tenant",
        composite_id="composite",
        definition_version="v1",
        month="2026-09",
        source_cut_id="normalized-cut",
        source_revision="1",
        reporting_currency="SGD",
        source_generated_at=NOW,
        expected_portfolio_ids=["P1", "P2", "P3"],
        portfolios=[
            MonthlyPortfolioObservations.model_validate(
                {
                    **reader.portfolios[binding.portfolio_id].observations.model_dump(mode="json"),
                    "discretionary": flag,
                }
            )
            for binding, flag in zip(config.members, (False, None, True), strict=True)
        ],
    )


def monthly_request(reader):
    config = configuration()
    return MonthlyEligibilitySourceRequest(
        scope=MonthlyPolicyScope(
            tenant_id="tenant",
            composite_id="composite",
            definition_version="v1",
            strategy_code="strategy",
        ),
        month=config.month,
        source_cut_id=config.observation_cut_id,
        owner_service="lotus-manage",
        expected_source_revision="1",
        expected_content_hash=hash_canonical_payload(
            expected_observations(reader).model_dump(mode="json")
        ),
        expected_portfolio_ids=("P1", "P2", "P3"),
        reporting_currency="SGD",
    )


def candidate_request():
    config = configuration()
    return CandidateUniverseRequest(
        "tenant", "composite", "v1", "2026-09", "SGD", registry_binding(config)
    )


def test_native_three_member_population_and_unverified_values_match_independent_expected_facts():
    reader, config = Reader(), configuration()
    universe = CoreCandidateUniverseSource(config, reader).resolve(candidate_request())
    assert [member.member_id for member in universe.members] == ["P1", "P2", "P3"]
    assert universe.population_verification == "UNVERIFIED"
    assert universe.registry_binding.digest == H
    assert universe.observation_owner == "lotus-manage"
    result = CoreMonthlyEligibilitySource(config, reader).resolve(monthly_request(reader))
    assert result.observations == expected_observations(reader)
    assert result.source_assembly_evidence is None
    assert result.observations.evidence_class == "SOURCE_UNVERIFIED"
    assert [
        (row.settled_unencumbered_cash, row.discretionary, row.funded, row.invested)
        for row in result.observations.portfolios
    ] == [("0", False, False, None), ("0", None, False, None), ("0", True, False, None)]


def test_absent_configuration_and_absent_member_are_unavailable_without_fabricated_population():
    reader = Reader()
    assert CoreCandidateUniverseSource(None, reader).resolve(candidate_request()) is None
    assert (
        CoreMonthlyEligibilitySource(None, reader).resolve(monthly_request(reader)).observations
        is None
    )
    assert reader.calls == []
    reader.portfolios.pop("P2")
    assert (
        CoreMonthlyEligibilitySource(configuration(), reader)
        .resolve(monthly_request(Reader()))
        .observations
        is None
    )


@pytest.mark.parametrize("change", ["tenant", "hash", "currency", "members", "owner"])
def test_wrong_monthly_scope_or_digest_never_resolves_to_an_alternative(change):
    reader = Reader()
    request = monthly_request(reader)
    if change == "tenant":
        request = replace(request, scope=request.scope.model_copy(update={"tenant_id": "foreign"}))
    else:
        field, value = {
            "hash": ("expected_content_hash", "sha256:" + "9" * 64),
            "currency": ("reporting_currency", "USD"),
            "members": ("expected_portfolio_ids", ("P1",)),
            "owner": ("owner_service", "lotus-core"),
        }[change]
        request = replace(request, **{field: value})
    with pytest.raises(ValueError):
        CoreMonthlyEligibilitySource(configuration(), reader).resolve(request)
    if change != "hash":
        assert reader.calls == []


@pytest.mark.parametrize(
    "change",
    ["partial", "count", "missing", "unmapped", "excluded", "gap", "currency", "discretionary"],
)
def test_complete_registry_cannot_hide_missing_excluded_unknown_or_changed_population(change):
    reader = Reader()
    registry = reader.retained_registry
    first = registry.members[0]
    declaration = first.declarations[0]
    if change in ("partial", "count", "missing"):
        field, value = {
            "partial": ("declared_coverage", "PARTIAL"),
            "count": ("expected_population_count", 4),
            "missing": ("members", registry.members[1:]),
        }[change]
        reader.retained_registry = registry.model_copy(update={field: value})
    else:
        if change == "unmapped":
            first = first.model_copy(update={"portfolio_id": None})
        elif change == "excluded":
            first = first.model_copy(
                update={"declarations": (declaration.model_copy(update={"included": False}),)}
            )
        elif change == "gap":
            first = first.model_copy(
                update={
                    "declarations": (
                        declaration.model_copy(update={"effective_from": "2026-09-02"}),
                    )
                }
            )
        else:
            changed = declaration.model_copy(
                update={
                    "effective_from": "2026-09-15",
                    "currency" if change == "currency" else "discretionary": "USD"
                    if change == "currency"
                    else True,
                }
            )
            first = first.model_copy(
                update={
                    "declarations": (
                        declaration.model_copy(update={"effective_to": "2026-09-15"}),
                        changed,
                    )
                }
            )
        reader.retained_registry = registry.model_copy(
            update={"members": (first, *registry.members[1:])}
        )
    with pytest.raises(ValueError, match="CORE_CUSTODY"):
        CoreCandidateUniverseSource(configuration(), reader).resolve(candidate_request())


def test_equivalent_adjacent_half_open_declarations_cover_the_month_without_inventing_history():
    reader = Reader()
    registry = reader.retained_registry
    first = registry.members[0]
    original = first.declarations[0]
    first = first.model_copy(
        update={
            "declarations": (
                original.model_copy(update={"effective_to": "2026-09-15"}),
                original.model_copy(update={"effective_from": "2026-09-15"}),
            )
        }
    )
    reader.retained_registry = registry.model_copy(
        update={"members": (first, *registry.members[1:])}
    )
    assert (
        CoreCandidateUniverseSource(configuration(), reader).resolve(candidate_request()).posture
        == "COMPLETE"
    )


def test_core_and_manage_role_orders_are_distinct_and_native_pins_are_not_rehashed():
    retained = Reader().portfolios["P1"]
    ordered = manage_role_order(retained)
    assert [role.role for role in ordered] == [
        "CASH",
        "FLOWS",
        "MONTH_END_ASSETS",
        "PRIOR_ASSETS",
        "READINESS",
    ]
    assert {role.role: role.source_content_hash for role in ordered} == {
        role.role: role.source_content_hash for role in retained.roles
    }
    with pytest.raises(ValueError, match="ROLE_ORDER"):
        manage_role_order(retained.model_copy(update={"roles": tuple(reversed(retained.roles))}))
    changed = retained.roles[0].model_copy(update={"descriptor_content_hash": "sha256:" + "9" * 64})
    with pytest.raises(ValueError, match="DESCRIPTOR_MISMATCH"):
        manage_role_order(retained.model_copy(update={"roles": (changed, *retained.roles[1:])}))


@pytest.mark.parametrize(
    "value,expected",
    [
        (None, None),
        (Decimal("-0.000"), "0"),
        (Decimal("12.3400"), "12.34"),
        (Decimal("0.000000000001"), "0.000000000001"),
    ],
)
def test_money_conversion_preserves_exact_null_zero_and_decimal_under_hostile_context(
    value, expected
):
    with localcontext() as context:
        context.prec = 1
        before = context.copy()
        assert exact_money(value) == expected
        assert context.prec == before.prec and context.flags == before.flags


@pytest.mark.parametrize(
    "value", [Decimal("1e-13"), Decimal("1e24"), Decimal("NaN"), Decimal("Infinity"), 1.2, True]
)
def test_money_never_rounds_overflow_nonfinite_or_float(value):
    with pytest.raises(ValueError, match="CORE_CUSTODY_MONEY"):
        exact_money(value)


def flow(event_id="original", **changes):
    return MonthlyFlowObservation.model_validate(
        dict(
            event_id=event_id,
            business_date="2026-09-05",
            received_at="2026-09-06T00:00:00.000000Z",
            currency="SGD",
            amount="50",
            classification="EXTERNAL_CASH",
            status="POSTED",
            reverses_event_id=None,
        )
        | changes
    )


def test_reversal_dependencies_are_verified_separately_and_never_added_to_window_amounts():
    reader = Reader()
    original, reversal = (
        flow(),
        flow("reversal", amount="-50", classification="REVERSAL", reverses_event_id="original"),
    )
    retained = reader.portfolios["P1"]
    observation = retained.observations.model_copy(update={"flows": [original, reversal]})
    reader.portfolios["P1"] = Reader.retained(
        retained.address, observation, reversal_dependencies=(original,)
    )
    result = CoreMonthlyEligibilitySource(configuration(), reader).resolve(monthly_request(reader))
    assert result.observations.portfolios[0].flows == [original, reversal]
    cross_window = original.model_copy(update={"business_date": "2026-08-31"})
    reader.portfolios["P1"] = reader.portfolios["P1"].model_copy(
        update={"reversal_dependencies": (cross_window,)}
    )
    with pytest.raises(ValueError, match="CROSS_WINDOW_REVERSAL_UNSUPPORTED"):
        CoreMonthlyEligibilitySource(configuration(), reader).resolve(monthly_request(reader))


def test_conflicting_flow_replay_and_unknown_status_refuse_instead_of_selecting_a_winner():
    reader = Reader()
    retained = reader.portfolios["P1"]
    observation = retained.observations.model_copy(update={"flows": [flow(), flow(amount="51")]})
    reader.portfolios["P1"] = Reader.retained(retained.address, observation)
    with pytest.raises(ValueError, match="FLOW_DUPLICATE_CONTENT_CONFLICT"):
        CoreMonthlyEligibilitySource(configuration(), reader).resolve(monthly_request(reader))
    with pytest.raises(ValidationError):
        flow(status="UNKNOWN")


def test_flow_totalcap_refuses_without_truncating_and_cash_requires_explicit_semantics():
    retained = Reader().portfolios["P1"]
    with pytest.raises(ValidationError):
        MonthlyPortfolioObservations.model_validate(
            {
                **retained.observations.model_dump(mode="json"),
                "flows": [flow(f"event{index}").model_dump(mode="json") for index in range(251)],
            }
        )
    reader = Reader()
    reader.portfolios["P1"] = retained.model_copy(update={"cash_semantic_definition": None})
    with pytest.raises(ValueError, match="CASH_DECLARATION_REQUIRED"):
        CoreMonthlyEligibilitySource(configuration(), reader).resolve(monthly_request(reader))


@pytest.mark.parametrize("field", ["tenant_id", "registry_root", "address", "portfolio_id"])
def test_retained_portfolio_cannot_substitute_another_tenant_registry_cut_or_member(field):
    reader = Reader()
    request = monthly_request(reader)
    retained = reader.portfolios["P1"]
    if field == "portfolio_id":
        changed = retained.observations.model_copy(update={"portfolio_id": "P2"})
        retained = retained.model_copy(update={"observations": changed})
    else:
        value = {
            "tenant_id": "foreign",
            "registry_root": "sha256:" + "9" * 64,
            "address": retained.address.model_copy(update={"revision": 2}),
        }[field]
        retained = retained.model_copy(update={field: value})
    reader.portfolios["P1"] = retained
    with pytest.raises(ValueError, match="PORTFOLIO_BINDING"):
        CoreMonthlyEligibilitySource(configuration(), reader).resolve(request)


def test_strategy_scope_and_opaque_candidate_identity_cannot_be_substituted():
    reader = Reader()
    request = monthly_request(reader)
    request = replace(request, scope=request.scope.model_copy(update={"strategy_code": "foreign"}))
    with pytest.raises(ValueError, match="REQUEST_SCOPE"):
        CoreMonthlyEligibilitySource(configuration(), reader).resolve(request)
    assert reader.calls == []
    config = configuration()
    member = config.members[0].model_copy(update={"source_member_id": "member/opaque"})
    config = config.model_copy(update={"members": (member, *config.members[1:])})
    registry = reader.retained_registry
    row = registry.members[0].model_copy(update={"source_member_id": "member/opaque"})
    reader.retained_registry = registry.model_copy(update={"members": (row, *registry.members[1:])})
    with pytest.raises(ValueError, match="IDENTITY_UNREPRESENTABLE"):
        CoreCandidateUniverseSource(config, reader).resolve(candidate_request())


def test_missing_cash_remains_unknown_and_never_uses_an_available_balance_formula():
    reader = Reader()
    retained = reader.portfolios["P1"]
    observation = retained.observations.model_copy(
        update={"settled_unencumbered_cash": None, "cash_as_of": None}
    )
    reader.portfolios["P1"] = Reader.retained(retained.address, observation)
    result = CoreMonthlyEligibilitySource(configuration(), reader).resolve(monthly_request(reader))
    assert result.observations.portfolios[0].settled_unencumbered_cash is None
    assert result.observations.portfolios[0].funded is False
    assert result.observations.portfolios[0].invested is None


@pytest.mark.parametrize(
    "value",
    [Decimal("1E+100000000"), Decimal("1E-100000000"), Decimal("1" * 37)],
)
def test_unrepresentable_money_is_refused_before_any_fixed_format_allocation(monkeypatch, value):
    def allocating_formatter(*args):
        pytest.fail("Unbounded amount reached fixed formatting")

    monkeypatch.setattr(source_module, "format", allocating_formatter, raising=False)
    with pytest.raises(ValueError, match="MONEY_UNREPRESENTABLE"):
        exact_money(value)


@pytest.mark.parametrize("value", [Decimal("-0E-100000000"), Decimal("0E+100000000")])
def test_huge_exponent_zero_normalizes_without_formatting(monkeypatch, value):
    def allocating_formatter(*args):
        pytest.fail("Zero must bypass fixed formatting")

    monkeypatch.setattr(source_module, "format", allocating_formatter, raising=False)
    assert exact_money(value) == "0"


@pytest.mark.parametrize(
    "value,expected",
    [
        (Decimal("123456789012345678901234.123456789012"), "123456789012345678901234.123456789012"),
        (
            Decimal("123456789012345678901234.123456789012" + "0" * 64),
            "123456789012345678901234.123456789012",
        ),
        (Decimal("1E+23"), "100000000000000000000000"),
        (Decimal("-1E-12"), "-0.000000000001"),
    ],
)
def test_money_formats_only_bounded_exact_coefficient_and_exponent(monkeypatch, value, expected):
    calls = []

    def bounded_formatter(bounded, specification):
        components = bounded.as_tuple()
        assert len(components.digits) <= 36
        assert -12 <= components.exponent <= 23
        calls.append(bounded)
        return format(bounded, specification)

    monkeypatch.setattr(source_module, "format", bounded_formatter, raising=False)
    with localcontext() as caller:
        caller.prec = 2
        caller.rounding = ROUND_UP
        caller.Emin, caller.Emax, caller.clamp = -2, 2, 1
        caller.traps[Inexact] = caller.traps[Rounded] = True
        caller.flags[Inexact] = True
        before = (caller.prec, caller.rounding, dict(caller.traps), dict(caller.flags))
        assert exact_money(value) == expected
        assert (caller.prec, caller.rounding, dict(caller.traps), dict(caller.flags)) == before
    assert len(calls) == 1


@pytest.mark.parametrize(
    "boundary", ["tenant", "empty_population", "declaration_currency", "empty_interval", "late_gap"]
)
def test_candidate_adapter_rejects_complete_but_invalid_registry_contract(boundary):
    reader = Reader()
    config = configuration()
    registry = reader.retained_registry
    member = registry.members[0]
    declaration = member.declarations[0]
    if boundary == "tenant":
        reader.retained_registry = registry.model_copy(update={"tenant_id": "foreign"})
        error = "REGISTRY_BINDING"
    elif boundary == "empty_population":
        config = config.model_copy(update={"members": ()})
        reader.retained_registry = registry.model_copy(
            update={"members": (), "expected_population_count": 0}
        )
        error = "EMPTY_POPULATION_UNSUPPORTED"
    else:
        if boundary == "declaration_currency":
            declarations = (declaration.model_copy(update={"currency": "USD"}),)
            error = "DECLARATION_SCOPE"
        elif boundary == "empty_interval":
            declarations = (
                declaration.model_copy(update={"effective_to": declaration.effective_from}),
            )
            error = "REGISTRY_INTERVAL_INVALID"
        else:
            declarations = (declaration.model_copy(update={"effective_to": "2026-09-15"}),)
            error = "REGISTRY_MONTH_GAP"
        member = member.model_copy(update={"declarations": declarations})
        reader.retained_registry = registry.model_copy(
            update={"members": (member, *registry.members[1:])}
        )
    with pytest.raises(ValueError, match=error):
        CoreCandidateUniverseSource(config, reader).resolve(candidate_request())


def test_candidate_adapter_ignores_outside_month_intervals_without_filling_a_gap():
    reader = Reader()
    registry = reader.retained_registry
    first = registry.members[0]
    declaration = first.declarations[0]
    past = declaration.model_copy(
        update={"effective_from": "2026-08-01", "effective_to": "2026-09-01", "currency": "USD"}
    )
    current = declaration.model_copy(update={"effective_to": "2026-10-01"})
    future = declaration.model_copy(update={"effective_from": "2026-10-01", "currency": "USD"})
    first = first.model_copy(update={"declarations": (past, current, future)})
    reader.retained_registry = registry.model_copy(
        update={"members": (first, *registry.members[1:])}
    )
    result = CoreCandidateUniverseSource(configuration(), reader).resolve(candidate_request())
    assert result.posture == "COMPLETE"
    assert result.reporting_currency == "SGD"
    assert [member.member_id for member in result.members] == ["P1", "P2", "P3"]


def test_candidate_scope_refusal_precedes_io_and_absent_registry_is_unavailable():
    reader = Reader()
    source = CoreCandidateUniverseSource(configuration(), reader)
    with pytest.raises(ValueError, match="REQUEST_SCOPE"):
        source.resolve(replace(candidate_request(), tenant_id="foreign"))
    assert reader.calls == []
    reader.retained_registry = None
    assert source.resolve(candidate_request()) is None
    assert len(reader.calls) == 1


@pytest.mark.parametrize(
    "field,value,error",
    [
        ("prior_assets_as_of", "2026-08-30", "PRIOR_DATE_MISMATCH"),
        ("readiness_as_of", "2026-09-29", "READINESS_DATE_MISMATCH"),
        ("currency", "USD", "CURRENCY_MISMATCH"),
        ("discretionary", True, "DISCRETIONARY_CONFLICT"),
    ],
)
def test_monthly_adapter_rejects_known_values_from_wrong_date_currency_or_mandate(
    field, value, error
):
    reader = Reader()
    request = monthly_request(reader)
    retained = reader.portfolios["P1"]
    observation = retained.observations.model_copy(update={field: value})
    reader.portfolios["P1"] = Reader.retained(retained.address, observation)
    with pytest.raises(ValueError, match=error):
        CoreMonthlyEligibilitySource(configuration(), reader).resolve(request)


def test_monthly_adapter_refuses_detached_dependency_and_requires_native_custody_for_assembly():
    reader = Reader()
    request = monthly_request(reader)
    retained = reader.portfolios["P1"]
    reader.portfolios["P1"] = retained.model_copy(update={"reversal_dependencies": (flow(),)})
    with pytest.raises(ValueError, match="REVERSAL_DEPENDENCY_NOT_IN_WINDOW_SET"):
        CoreMonthlyEligibilitySource(configuration(), reader).resolve(request)
    reader.portfolios["P1"] = retained
    assert (
        CoreMonthlyEligibilitySource(configuration(), reader).resolve(request).observations
        is not None
    )
    with pytest.raises(ValueError, match="NATIVE_RECONSTRUCTION_REQUIRED"):
        CoreMonthlyEligibilitySource(configuration(), reader).assemble(request)


@pytest.mark.parametrize(
    "precision,rounding,traps",
    [
        (28, ROUND_HALF_EVEN, False),
        (2, ROUND_HALF_EVEN, False),
        (2, ROUND_DOWN, True),
        (2, ROUND_UP, True),
    ],
)
@pytest.mark.parametrize(
    "original_amount,reversal_amount,valid",
    [
        ("123", "-123", True),
        ("120", "-123", False),
        ("123456789012345678901234.123456789012", "-123456789012345678901234.123456789012", True),
        ("123456789012345678901234.123456789012", "-123456789012345678901234.123456789013", False),
        ("123456789012345678901234.1235", "-123456789012345678901234.123456789012", False),
    ],
)
def test_native_adapter_reversal_equality_ignores_ambient_decimal_context(
    precision, rounding, traps, original_amount, reversal_amount, valid
):
    reader = Reader()
    retained = reader.portfolios["P1"]
    original = flow(amount=original_amount)
    reversal = flow(
        "reversal", amount=reversal_amount, classification="REVERSAL", reverses_event_id="original"
    )
    observation = retained.observations.model_copy(update={"flows": [original, reversal]})
    reader.portfolios["P1"] = Reader.retained(
        retained.address, observation, reversal_dependencies=(original,)
    )
    request = monthly_request(reader)
    with localcontext() as caller:
        caller.prec, caller.rounding = precision, rounding
        caller.traps[Inexact] = caller.traps[Rounded] = traps
        before = (caller.prec, caller.rounding, dict(caller.traps), dict(caller.flags))
        if valid:
            result = CoreMonthlyEligibilitySource(configuration(), reader).resolve(request)
            assert result.observations.portfolios[0].flows == [original, reversal]
        else:
            with pytest.raises(ValueError, match="FLOW_REVERSAL_BINDING_INVALID"):
                CoreMonthlyEligibilitySource(configuration(), reader).resolve(request)
        assert (caller.prec, caller.rounding, dict(caller.traps), dict(caller.flags)) == before
