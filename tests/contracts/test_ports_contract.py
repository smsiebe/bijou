"""Contract tests verifying abstract enforcement and concurrency documentation on Ports."""

import pytest

from bijou.core.ports import (
    IFederationConnector,
    IGraphProjectionEngine,
    IGraphRepository,
    IReasoningBroker,
    ITelemetryStore,
)


def test_abstract_ports_cannot_be_instantiated() -> None:
    """Verifies all 5 port ABCs raise TypeError when instantiated directly."""
    for port_cls in [
        IGraphRepository,
        IGraphProjectionEngine,
        ITelemetryStore,
        IFederationConnector,
        IReasoningBroker,
    ]:
        with pytest.raises(TypeError):
            port_cls()  # type: ignore[abstract]


def test_shared_state_ports_document_concurrency_model() -> None:
    """Inspects __doc__ on shared-state ports and asserts 'Concurrency Model:' is documented."""
    shared_state_ports = [
        IGraphRepository,
        IGraphProjectionEngine,
        ITelemetryStore,
    ]
    for port_cls in shared_state_ports:
        doc = port_cls.__doc__
        assert doc is not None, f"Port {port_cls.__name__} has no docstring"
        assert "Concurrency Model:" in doc, (
            f"Port {port_cls.__name__} must document its concurrency model"
        )
