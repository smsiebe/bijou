"""Contract tests for abstract ports, exceptions, and access perspective seam."""

import pytest

from bijou.core.contracts.enums import AccessMode
from bijou.core.contracts.models import OrganizationDTO
from bijou.core.ports import (
    DemoAccessControlProvider,
    EntityNotFoundError,
    GraphCycleError,
    IAccessControlProvider,
    IGraphProjectionEngine,
    IGraphRepository,
    IReasoningBroker,
    ITelemetryStore,
    PermissionDeniedError,
)


@pytest.mark.parametrize(
    "port_cls",
    [
        IGraphRepository,
        IGraphProjectionEngine,
        ITelemetryStore,
        IReasoningBroker,
        IAccessControlProvider,
    ],
)
def test_abstract_ports_cannot_be_instantiated(port_cls: type) -> None:
    """ABC ports must reject direct instantiation."""
    with pytest.raises(TypeError):
        port_cls()  # type: ignore[call-arg]


def test_demo_access_control_provider_enforces_managed_org_boundaries() -> None:
    """DemoAccessControlProvider models both Global Analyst and Managed Org Owner permissions."""
    provider = DemoAccessControlProvider()
    org_joint = OrganizationDTO(id="org-joint-c2", name="Joint C2", is_managed=True)
    org_space = OrganizationDTO(id="org-strat-space", name="Space Cmd", is_managed=True)

    global_ctx = provider.resolve_context(AccessMode.GLOBAL_ANALYST)
    assert provider.can_manage_org(global_ctx, org_space) is True

    owner_ctx = provider.resolve_context(AccessMode.MANAGED_ORG_OWNER, "org-joint-c2")
    assert provider.can_manage_org(owner_ctx, org_joint) is True
    assert provider.can_manage_org(owner_ctx, org_space) is False


def test_domain_exceptions_carry_messages() -> None:
    assert "cycle" in str(GraphCycleError(["a", "b", "a"])).lower()
    assert "missing" in str(EntityNotFoundError("Effort", "missing")).lower()
    assert "denied" in str(PermissionDeniedError("Denied")).lower()
