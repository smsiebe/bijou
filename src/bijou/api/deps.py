"""FastAPI dependency injection providers."""

from typing import Any

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
