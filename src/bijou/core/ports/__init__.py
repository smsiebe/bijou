"""Abstract ports, interfaces, and exceptions for Bijou."""

from bijou.core.ports.exceptions import (
    BijouError,
    ContractValidationError,
    DuplicateEntityError,
    EntityNotFoundError,
    GraphCycleError,
    ServiceUnavailableError,
)
from bijou.core.ports.federation import IFederationConnector
from bijou.core.ports.graph_engine import IGraphProjectionEngine
from bijou.core.ports.reasoning import IReasoningBroker
from bijou.core.ports.repository import IGraphRepository
from bijou.core.ports.telemetry_store import ITelemetryStore

__all__ = [
    "BijouError",
    "ContractValidationError",
    "DuplicateEntityError",
    "EntityNotFoundError",
    "GraphCycleError",
    "IFederationConnector",
    "IGraphProjectionEngine",
    "IGraphRepository",
    "IReasoningBroker",
    "ITelemetryStore",
    "ServiceUnavailableError",
]
