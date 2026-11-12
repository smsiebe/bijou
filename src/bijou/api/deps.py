"""FastAPI dependency injection and access-perspective resolution providers."""

from typing import Annotated, Any

from fastapi import Depends, Header

from bijou.core.contracts.enums import AccessMode
from bijou.core.ports.access_control import AccessContext
from bijou.core.ports.exceptions import ServiceUnavailableError

_orchestrator_instance: Any = None


def set_orchestrator(orchestrator: Any) -> None:
    """Register the active orchestrator service instance."""
    global _orchestrator_instance
    _orchestrator_instance = orchestrator


def get_orchestrator() -> Any:
    """Retrieve the injected orchestrator service, raising 503 if uninitialized."""
    if _orchestrator_instance is None:
        raise ServiceUnavailableError("Service backend not initialized")
    return _orchestrator_instance


def get_access_context(
    orchestrator: Annotated[Any, Depends(get_orchestrator)],
    x_bijou_access_mode: str | None = Header(default=None),
    x_bijou_active_org: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
) -> AccessContext:
    """Resolve active AccessContext via pluggable AccessControlProvider seam."""
    req_mode = None
    if x_bijou_access_mode:
        try:
            req_mode = AccessMode(x_bijou_access_mode)
        except ValueError:
            req_mode = None
    return orchestrator.resolve_access_context(
        requested_mode=req_mode,
        requested_org_id=x_bijou_active_org,
        auth_token=authorization,
    )
