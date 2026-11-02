"""Abstract port for querying external enterprise telemetry federation endpoints."""

from abc import ABC, abstractmethod
from datetime import datetime

from bijou.core.contracts.models import FederationSpecDTO
from bijou.core.contracts.telemetry import TelemetryRollupDTO


class IFederationConnector(ABC):
    """Abstract port for connecting to external telemetry feeds."""

    @property
    @abstractmethod
    def connector_id(self) -> str:
        """Identifier for this federation connector."""

    @abstractmethod
    def verify_connectivity(self, spec: FederationSpecDTO) -> bool:
        """Verify reachability and authentication to the federated endpoint."""

    @abstractmethod
    def execute_federated_rollup(
        self,
        spec: FederationSpecDTO,
        window_start: datetime,
        window_end: datetime,
    ) -> TelemetryRollupDTO:
        """Execute a remote query against the federated provider and return a rollup."""
