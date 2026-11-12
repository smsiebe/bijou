"""Access control & organizational perspective abstraction port."""

from abc import ABC, abstractmethod

from bijou.core.contracts.base import BijouBaseModel
from bijou.core.contracts.enums import AccessMode
from bijou.core.contracts.models import OrganizationDTO


class AccessContext(BijouBaseModel):
    """Resolved security & organizational perspective context for a request."""

    mode: AccessMode = AccessMode.GLOBAL_ANALYST
    active_org_id: str | None = None
    principal_id: str = "demo-analyst"


class IAccessControlProvider(ABC):
    """Port abstracting authentication & RBAC so auth systems can swap in without domain rewrites.

    Concurrency Model: Thread-safe stateless or token-cached verification.
    """

    @abstractmethod
    def resolve_context(
        self,
        requested_mode: AccessMode | None = None,
        requested_org_id: str | None = None,
        auth_token: str | None = None,
    ) -> AccessContext:
        """Resolve an AccessContext from request metadata or credentials."""

    @abstractmethod
    def can_manage_org(
        self,
        context: AccessContext,
        org: OrganizationDTO,
    ) -> bool:
        """Determine whether the active context may mutate managed inventories for an Organization."""


class DemoAccessControlProvider(IAccessControlProvider):
    """Manual perspective-switching access provider for offline/demo workflows."""

    def resolve_context(
        self,
        requested_mode: AccessMode | None = None,
        requested_org_id: str | None = None,
        auth_token: str | None = None,
    ) -> AccessContext:
        mode = requested_mode or AccessMode.GLOBAL_ANALYST
        if mode == AccessMode.MANAGED_ORG_OWNER and requested_org_id:
            return AccessContext(
                mode=AccessMode.MANAGED_ORG_OWNER,
                active_org_id=requested_org_id,
                principal_id=f"owner:{requested_org_id}",
            )
        return AccessContext(
            mode=AccessMode.GLOBAL_ANALYST,
            active_org_id=None,
            principal_id="demo-global-analyst",
        )

    def can_manage_org(
        self,
        context: AccessContext,
        org: OrganizationDTO,
    ) -> bool:
        if context.mode == AccessMode.GLOBAL_ANALYST:
            return True
        return context.active_org_id == org.id
