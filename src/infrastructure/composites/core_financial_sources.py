"""Bounded native normalization through existing ports; no whole-cut authority is issued."""

from datetime import date, datetime, timedelta
from decimal import Decimal
from collections.abc import Iterator

from pydantic import TypeAdapter, ValidationError

from src.core.composite_authority_models import CompositeMemberIdentity, EvidenceBinding, Identity
from src.core.composite_eligibility.flows import admitted_monthly_flows
from src.core.composite_eligibility.observations import (
    MoneyText,
    MonthlyEligibilityObservations,
    MonthlyPortfolioObservations,
)
from src.core.composite_eligibility.policy import month_window
from src.core.composite_eligibility.source import (
    MonthlyEligibilitySourceRequest,
    MonthlyEligibilitySourceResolution,
    admitted_source_snapshot,
)
from src.core.composite_eligibility.staged_ports import CandidateUniverseRequest
from src.core.composite_eligibility.staged_subject import CandidateUniverse
from src.core.common.canonical import hash_canonical_payload
from src.core.composite_eligibility.native_source_custody import (
    MonthlyNativeCustody,
    NativeRegistryCustody,
    NativePortfolioCustody,
    NATIVE_ROLES,
    native_role_set_digest,
)
from src.core.composite_eligibility.native_source_verification import NativeAssemblyVerifier
from src.core.composite_eligibility.source_assembly import (
    NativeMonthlySourceAssembly,
    MonthlyInputBinding,
    VerifiedMonthlySourceAssembly,
    assembly_verification_request,
)
from src.core.composite_universe import DpmCompositeUniverseSourceProduct
from src.infrastructure.composites.core_financial_configuration import CoreFinancialConfiguration
from src.infrastructure.composites.core_source_custody import (
    CoreRetainedReader,
    RegistryDeclaration,
    RegistryMember,
    RetainedPortfolio,
    RetainedRegistry,
    RoleCapture,
)


def exact_money(value: Decimal | None) -> str | None:
    """Convert exact finite source Decimal without arithmetic, rounding or float coercion."""
    if value is None:
        return None
    if not isinstance(value, Decimal) or not value.is_finite():
        raise ValueError("CORE_CUSTODY_MONEY_INVALID")
    if value.is_zero():
        return "0"
    text = format(_bounded_nonzero_money(value), "f")
    try:
        return TypeAdapter(MoneyText).validate_python(text)
    except ValidationError as exc:
        raise ValueError("CORE_CUSTODY_MONEY_UNREPRESENTABLE") from exc


def _bounded_nonzero_money(value: Decimal) -> Decimal:
    """Construct an exact bounded tuple after finite/nonzero admission, before formatting."""
    components = value.as_tuple()
    exponent = components.exponent
    if not isinstance(exponent, int):
        raise ValueError("CORE_CUSTODY_MONEY_INVALID")
    coefficient_size = len(components.digits)
    while components.digits[coefficient_size - 1] == 0:
        coefficient_size -= 1
        exponent += 1
    if coefficient_size > 36 or exponent < -12 or coefficient_size + exponent > 24:
        raise ValueError("CORE_CUSTODY_MONEY_UNREPRESENTABLE")
    # Format only a bounded exact tuple, never the original trailing-zero expansion.
    return Decimal((components.sign, components.digits[:coefficient_size], exponent))


def manage_role_order(portfolio: RetainedPortfolio) -> tuple[RoleCapture, ...]:
    """Validate producer order before projecting the distinct Manage canonical order."""
    checked = RetainedPortfolio.model_validate(portfolio.model_dump(mode="python"))
    return tuple(sorted(checked.roles, key=lambda role: role.role))


def registry_binding(configuration: CoreFinancialConfiguration) -> EvidenceBinding:
    return EvidenceBinding(
        product_name="PortfolioHistoricalRegistry",
        product_version="v1",
        revision=str(configuration.registry.revision),
        digest=configuration.registry.content_hash,
    )


def _identity(value: str) -> str:
    try:
        return TypeAdapter(Identity).validate_python(value)
    except ValidationError as exc:
        raise ValueError("CORE_CUSTODY_IDENTITY_UNREPRESENTABLE") from exc


def _ordered_declarations(
    member: RegistryMember,
) -> Iterator[tuple[date, date | None, RegistryDeclaration]]:
    previous_end = None
    for index, declaration in enumerate(member.declarations):
        start = date.fromisoformat(declaration.effective_from)
        end = (
            date.fromisoformat(declaration.effective_to)
            if declaration.effective_to is not None
            else None
        )
        if (end is not None and start >= end) or (
            index and (previous_end is None or start < previous_end)
        ):
            raise ValueError("CORE_CUSTODY_REGISTRY_INTERVAL_INVALID")
        previous_end = end
        yield start, end, declaration


def _require_unchanged_declaration(
    selected: RegistryDeclaration | None, declaration: RegistryDeclaration
) -> None:
    if selected is not None and (
        declaration.definition_version,
        declaration.currency,
        declaration.included,
        declaration.discretionary,
    ) != (
        selected.definition_version,
        selected.currency,
        selected.included,
        selected.discretionary,
    ):
        raise ValueError("CORE_CUSTODY_REGISTRY_MONTH_CHANGE_UNSUPPORTED")


def _month_declaration(member: RegistryMember, first: date, last: date) -> RegistryDeclaration:
    cursor, selected = first, None
    for start, end, declaration in _ordered_declarations(member):
        if start > last or (end is not None and end <= first):
            continue
        if start > cursor:
            raise ValueError("CORE_CUSTODY_REGISTRY_MONTH_GAP")
        _require_unchanged_declaration(selected, declaration)
        selected = declaration
        cursor = min(end or last + timedelta(days=1), last + timedelta(days=1))
    if selected is None or cursor <= last:
        raise ValueError("CORE_CUSTODY_REGISTRY_MONTH_GAP")
    if not selected.included:
        raise ValueError("CORE_CUSTODY_EXCLUDED_MEMBER_UNSUPPORTED")
    return selected


def _require_registry_header(
    configuration: CoreFinancialConfiguration, registry: RetainedRegistry, first: date, last: date
) -> None:
    if (registry.address, registry.tenant_id, registry.definition_version) != (
        configuration.registry,
        configuration.tenant_id,
        configuration.definition_version,
    ):
        raise ValueError("CORE_CUSTODY_REGISTRY_BINDING")
    if (
        not date.fromisoformat(registry.coverage_from)
        <= first
        <= last
        <= date.fromisoformat(registry.coverage_to)
        or registry.declared_coverage != "COMPLETE"
    ):
        raise ValueError("CORE_CUSTODY_REGISTRY_INCOMPLETE")


def _require_complete_member_keys(
    configuration: CoreFinancialConfiguration, registry: RetainedRegistry
) -> None:
    keys = [(member.provider_namespace, member.source_member_id) for member in registry.members]
    configured_keys = {
        (member.provider_namespace, member.source_member_id) for member in configuration.members
    }
    if (
        keys != sorted(set(keys))
        or set(keys) != configured_keys
        or registry.expected_population_count != len(keys)
    ):
        raise ValueError("CORE_CUSTODY_POPULATION_MISMATCH")
    if not keys:
        raise ValueError("CORE_CUSTODY_EMPTY_POPULATION_UNSUPPORTED")


def _complete_registry(
    configuration: CoreFinancialConfiguration, registry: RetainedRegistry
) -> dict[str, RegistryDeclaration]:
    registry = RetainedRegistry.model_validate(registry.model_dump(mode="python"))
    first_text, last_text = month_window(configuration.month)
    first, last = date.fromisoformat(first_text), date.fromisoformat(last_text)
    _require_registry_header(configuration, registry, first, last)
    _require_complete_member_keys(configuration, registry)
    bindings = {
        (member.provider_namespace, member.source_member_id): member
        for member in configuration.members
    }
    declarations = {}
    for member in registry.members:
        binding = bindings[(member.provider_namespace, member.source_member_id)]
        if member.portfolio_id != binding.portfolio_id:
            raise ValueError("CORE_CUSTODY_PORTFOLIO_MAPPING")
        declaration = _month_declaration(member, first, last)
        if (declaration.definition_version, declaration.currency) != (
            configuration.definition_version,
            configuration.reporting_currency,
        ):
            raise ValueError("CORE_CUSTODY_DECLARATION_SCOPE")
        declarations[binding.portfolio_id] = declaration
    return declarations


class CoreCandidateUniverseSource:
    """Internal candidate adapter; absent configuration makes no reader call."""

    def __init__(
        self, configuration: CoreFinancialConfiguration | None, reader: CoreRetainedReader
    ) -> None:
        self.configuration, self.reader = configuration, reader

    def resolve(self, request: CandidateUniverseRequest) -> CandidateUniverse | None:
        configuration = self.configuration
        if configuration is None:
            return None
        if (
            request.tenant_id,
            request.composite_id,
            request.definition_version,
            request.month,
            request.reporting_currency,
            request.registry_binding,
        ) != (
            configuration.tenant_id,
            configuration.composite_id,
            configuration.definition_version,
            configuration.month,
            configuration.reporting_currency,
            registry_binding(configuration),
        ):
            raise ValueError("CORE_CUSTODY_REQUEST_SCOPE")
        registry = self.reader.registry(tenant_id=request.tenant_id, address=configuration.registry)
        if registry is None:
            return None
        _complete_registry(configuration, registry)
        binding = registry_binding(configuration)
        return CandidateUniverse(
            tenant_id=request.tenant_id,
            composite_id=request.composite_id,
            definition_version=request.definition_version,
            month=request.month,
            registry_binding=binding,
            reporting_currency=request.reporting_currency,
            members=[
                CompositeMemberIdentity(
                    member_id=member.portfolio_id,
                    identity_kind="CORE_PORTFOLIO",
                    namespace=_identity(member.provider_namespace),
                    provider_id=member.provider_id,
                    source_member_id=_identity(member.source_member_id),
                )
                for member in configuration.members
            ],
            source_products=[
                DpmCompositeUniverseSourceProduct(
                    owner_service="lotus-core",
                    product_name=binding.product_name,
                    contract_version=binding.product_version,
                    authority_scope="AUTHORITATIVE_UNIVERSE",
                    source_cut_id=_identity(configuration.registry.source_cut_id),
                    source_watermark=binding.revision,
                    content_hash=binding.digest,
                )
            ],
            observation_owner="lotus-manage",
            coverage_from=registry.coverage_from,
            coverage_to=registry.coverage_to,
            posture="COMPLETE",
            source_cut_id=_identity(configuration.registry.source_cut_id),
            generated_at=registry.generated_at,
        )


def _require_source_dates(observation: MonthlyPortfolioObservations, first: str, last: str) -> None:
    prior = (date.fromisoformat(first) - timedelta(days=1)).isoformat()
    if observation.prior_month_end_assets is not None and observation.prior_assets_as_of != prior:
        raise ValueError("CORE_CUSTODY_PRIOR_DATE_MISMATCH")
    if (observation.funded is not None or observation.invested is not None) and (
        observation.readiness_as_of != last
    ):
        raise ValueError("CORE_CUSTODY_READINESS_DATE_MISMATCH")


def _require_cash_semantics(checked: RetainedPortfolio, last: str) -> None:
    if checked.observations.settled_unencumbered_cash is not None and (
        checked.observations.cash_as_of != last
        or checked.cash_semantic_definition is None
        or checked.cash_semantic_revision is None
    ):
        raise ValueError("CORE_CUSTODY_CASH_DECLARATION_REQUIRED")


def _require_reversal_window(checked: RetainedPortfolio, first: str, last: str) -> None:
    for dependency in checked.reversal_dependencies:
        if not first <= dependency.business_date <= last:
            raise ValueError("CORE_CUSTODY_CROSS_WINDOW_REVERSAL_UNSUPPORTED")
        if dependency not in checked.observations.flows:
            raise ValueError("CORE_CUSTODY_REVERSAL_DEPENDENCY_NOT_IN_WINDOW_SET")


def _portfolio_observations(
    configuration: CoreFinancialConfiguration,
    retained: RetainedPortfolio,
    declaration: RegistryDeclaration,
) -> MonthlyPortfolioObservations:
    checked = RetainedPortfolio.model_validate(retained.model_dump(mode="python"))
    observation = checked.observations
    first, last = month_window(configuration.month)
    if observation.currency != configuration.reporting_currency:
        raise ValueError("CORE_CUSTODY_CURRENCY_MISMATCH")
    _require_source_dates(observation, first, last)
    _require_cash_semantics(checked, last)
    if observation.discretionary not in (None, declaration.discretionary):
        raise ValueError("CORE_CUSTODY_DISCRETIONARY_CONFLICT")
    _require_reversal_window(checked, first, last)
    _, reasons = admitted_monthly_flows(
        observation.flows,
        start=first,
        end=last,
        currency=configuration.reporting_currency,
        evaluated_at=datetime.fromisoformat(checked.generated_at),
        source_generated_at=datetime.fromisoformat(checked.generated_at),
    )
    if reasons:
        raise ValueError("CORE_CUSTODY_FLOW_UNSUPPORTED:" + ",".join(reasons))
    return MonthlyPortfolioObservations.model_validate(
        {**observation.model_dump(mode="json"), "discretionary": declaration.discretionary}
    )


class CoreMonthlyEligibilitySource:
    """Unverified internal resolution; whole-cut verification and public wiring remain separate."""

    def __init__(
        self,
        configuration: CoreFinancialConfiguration | None,
        reader: CoreRetainedReader,
        *,
        verifier: NativeAssemblyVerifier | None = None,
        controlled_synthetic: bool = False,
    ) -> None:
        self.configuration, self.reader = configuration, reader
        self.verifier, self.controlled_synthetic = verifier, controlled_synthetic

    def resolve(
        self, request: MonthlyEligibilitySourceRequest
    ) -> MonthlyEligibilitySourceResolution:
        if not self.controlled_synthetic:
            return self._resolve_observations(request)
        if self.verifier is None:
            return MonthlyEligibilitySourceResolution(observations=None)
        assembly = self.assemble(request)
        if assembly is None:
            return MonthlyEligibilitySourceResolution(observations=None)
        pair = self.verifier.verify_with_proof(assembly_verification_request(assembly))
        if pair is None:
            return MonthlyEligibilitySourceResolution(observations=None)
        evidence = VerifiedMonthlySourceAssembly(
            assembly=assembly, verification=pair.receipt, native_proof=pair.proof
        )
        return MonthlyEligibilitySourceResolution(assembly.observations, "lotus-manage", evidence)

    def assemble(
        self, request: MonthlyEligibilitySourceRequest
    ) -> NativeMonthlySourceAssembly | None:
        """Reconstruct source facts freshly; the verifier must use its own reader/configuration."""
        retained: list[NativeRegistryCustody | NativePortfolioCustody] = []
        resolution = self._resolve_observations(request, retained)
        if resolution.observations is None:
            return None
        if (
            not retained
            or not isinstance(retained[0], NativeRegistryCustody)
            or any(not isinstance(p, NativePortfolioCustody) for p in retained[1:])
        ):
            raise ValueError("CORE_CUSTODY_NATIVE_RECONSTRUCTION_REQUIRED")
        custody = MonthlyNativeCustody.model_validate(
            {
                "registry": retained[0].model_dump(mode="json"),
                "portfolios": [p.model_dump(mode="json") for p in retained[1:]],
            }
        )
        observations = resolution.observations
        inputs = [
            MonthlyInputBinding(
                kind=role,
                owner_service="lotus-manage",
                source_cut_id=observations.source_cut_id,
                evidence=EvidenceBinding(
                    product_name="CompositeMonthlyRoleSet",
                    product_version="v1",
                    revision=observations.source_revision,
                    digest=native_role_set_digest(custody, role),
                ),
            )
            for role in sorted(NATIVE_ROLES)
        ]
        digest = hash_canonical_payload(
            {
                "observations": observations.model_dump(mode="json"),
                "inputs": [i.model_dump(mode="json") for i in inputs],
            }
        )
        return NativeMonthlySourceAssembly(
            product_name="CompositeMonthlyEligibilityAssembly",
            product_version="v2",
            observations=observations,
            inputs=inputs,
            compatibility_binding=EvidenceBinding(
                product_name="CompositeSourceCutCompatibility",
                product_version="v1",
                revision=observations.source_revision,
                digest=digest,
            ),
            compatibility_posture="SYNTHETIC_UNQUALIFIED"
            if self.controlled_synthetic
            else "SOURCE_UNVERIFIED",
            native_custody=custody,
        )

    def _resolve_observations(
        self,
        request: MonthlyEligibilitySourceRequest,
        native: list[NativeRegistryCustody | NativePortfolioCustody] | None = None,
    ) -> MonthlyEligibilitySourceResolution:
        configuration = self.configuration
        unavailable = MonthlyEligibilitySourceResolution(observations=None)
        if configuration is None:
            return unavailable
        self._require_monthly_request(configuration, request)
        registry = self.reader.registry(
            tenant_id=configuration.tenant_id, address=configuration.registry
        )
        if registry is None:
            return unavailable
        if native is not None and registry.native_custody is not None:
            native.append(registry.native_custody)
        declarations = _complete_registry(configuration, registry)
        retained_portfolios = self._read_portfolio_observations(configuration, declarations, native)
        if retained_portfolios is None:
            return unavailable
        portfolios, generated = retained_portfolios
        generated.insert(0, registry.generated_at)
        observations = MonthlyEligibilityObservations(
            product_name="CompositeMonthlyEligibilityObservations",
            product_version="v1",
            evidence_class="SYNTHETIC_UNQUALIFIED"
            if self.controlled_synthetic
            else "SOURCE_UNVERIFIED",
            tenant_id=configuration.tenant_id,
            composite_id=configuration.composite_id,
            definition_version=configuration.definition_version,
            month=configuration.month,
            source_cut_id=configuration.observation_cut_id,
            source_revision=configuration.observation_revision,
            reporting_currency=configuration.reporting_currency,
            source_generated_at=max(generated),
            expected_portfolio_ids=list(request.expected_portfolio_ids),
            portfolios=portfolios,
        )
        result = MonthlyEligibilitySourceResolution(observations, "lotus-manage")
        admitted_source_snapshot(request, result)
        return result

    def _require_monthly_request(
        self, configuration: CoreFinancialConfiguration, request: MonthlyEligibilitySourceRequest
    ) -> None:
        if (
            request.scope.tenant_id,
            request.scope.composite_id,
            request.scope.definition_version,
            request.scope.strategy_code,
            request.month,
            request.reporting_currency,
            request.source_cut_id,
            request.expected_source_revision,
            request.expected_portfolio_ids,
            request.owner_service,
        ) != (
            configuration.tenant_id,
            configuration.composite_id,
            configuration.definition_version,
            configuration.strategy_code,
            configuration.month,
            configuration.reporting_currency,
            configuration.observation_cut_id,
            configuration.observation_revision,
            tuple(member.portfolio_id for member in configuration.members),
            "lotus-manage",
        ):
            raise ValueError("CORE_CUSTODY_REQUEST_SCOPE")

    def _read_portfolio_observations(
        self,
        configuration: CoreFinancialConfiguration,
        declarations: dict[str, RegistryDeclaration],
        native: list[NativeRegistryCustody | NativePortfolioCustody] | None,
    ) -> tuple[list[MonthlyPortfolioObservations], list[str]] | None:
        portfolios: list[MonthlyPortfolioObservations] = []
        generated: list[str] = []
        for binding in configuration.members:
            retained = self.reader.portfolio(
                tenant_id=configuration.tenant_id,
                portfolio_id=binding.portfolio_id,
                address=binding.financial_cut,
            )
            if retained is None:
                return None
            if native is not None and retained.native_custody is not None:
                native.append(retained.native_custody)
            if (retained.address, retained.tenant_id, retained.registry_root) != (
                binding.financial_cut,
                configuration.tenant_id,
                configuration.registry.content_hash,
            ) or retained.observations.portfolio_id != binding.portfolio_id:
                raise ValueError("CORE_CUSTODY_PORTFOLIO_BINDING")
            portfolios.append(
                _portfolio_observations(configuration, retained, declarations[binding.portfolio_id])
            )
            generated.append(retained.generated_at)
        return portfolios, generated
