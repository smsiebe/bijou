"""Core domain and infrastructure exceptions for Bijou v2."""


class BijouError(Exception):
    """Base exception for all domain errors within Bijou."""


class EntityNotFoundError(BijouError):
    """Raised when an entity is not found in the graph repository."""


class DuplicateEntityError(BijouError):
    """Raised when attempting to insert an entity with an existing identifier."""


class GraphCycleError(BijouError):
    """Raised when a cyclical dependency is detected in an acyclic graph."""

    def __init__(self, cycle_path: list[str]) -> None:
        self.cycle_path = cycle_path
        super().__init__(f"Graph cycle detected: {' -> '.join(cycle_path)}")


class ContractValidationError(BijouError):
    """Raised when an internal contract or invariant is violated."""


class PermissionDeniedError(BijouError):
    """Raised when an AccessContext lacks permission to mutate a Managed Organization."""


class ServiceUnavailableError(BijouError):
    """Raised when an external transport target (AuraRouter, Federation) is unreachable."""
