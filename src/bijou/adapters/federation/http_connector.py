"""Authentic HTTP federation connector for external enterprise telemetry rollups."""

import json
import threading
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Any

import httpx

from bijou.core.contracts.models import FederationSpecDTO
from bijou.core.contracts.telemetry import TelemetryRollupDTO
from bijou.core.ports.exceptions import ServiceUnavailableError
from bijou.core.ports.federation import IFederationConnector


class HttpFederationConnector(IFederationConnector):
    """Authentic HTTP federation connector with bounded TTL cache fallback."""

    def __init__(self, connector_id: str = "http-federation", max_entries: int = 256) -> None:
        self._connector_id = connector_id
        self._max_entries = max_entries
        self._cache_lock = threading.RLock()
        self._cache: OrderedDict[str, tuple[float, TelemetryRollupDTO]] = OrderedDict()
        self._client = httpx.Client(timeout=5.0)

    @property
    def connector_id(self) -> str:
        return self._connector_id

    def close(self) -> None:
        """Close HTTP transport client."""
        self._client.close()

    def _cache_key(self, spec: FederationSpecDTO) -> str:
        sorted_params = json.dumps(spec.params, sort_keys=True)
        return f"{self._connector_id}:{spec.query_template}:{sorted_params}"

    def verify_connectivity(self, spec: FederationSpecDTO) -> bool:
        """Verify reachability of remote federated telemetry endpoint."""
        url = spec.query_template
        try:
            resp = self._client.get(url, params={"ping": "true"})
            return resp.status_code == 200
        except (httpx.HTTPError, OSError):
            return False

    def execute_federated_rollup(
        self,
        spec: FederationSpecDTO,
        window_start: datetime,
        window_end: datetime,
    ) -> TelemetryRollupDTO:
        """Execute a live HTTP query or fall back to valid cached entry if offline."""
        cache_key = self._cache_key(spec)
        now_ts = datetime.now(timezone.utc).timestamp()

        try:
            # Live transport attempt
            resp = self._client.post(
                spec.query_template,
                json={
                    "params": spec.params,
                    "accumulator": spec.accumulator.value,
                    "window_start": window_start.isoformat(),
                    "window_end": window_end.isoformat(),
                    "sla_target": spec.sla_target,
                },
            )
            if resp.status_code != 200:
                raise ServiceUnavailableError(
                    f"Federated endpoint returned HTTP {resp.status_code}: {resp.text}"
                )

            data: dict[str, Any] = resp.json()
            rollup = TelemetryRollupDTO.model_validate(data)

            # Store in bounded LRU cache
            with self._cache_lock:
                if len(self._cache) >= self._max_entries:
                    self._cache.popitem(last=False)
                self._cache[cache_key] = (now_ts, rollup)
                self._cache.move_to_end(cache_key)

            return rollup

        except Exception as err:
            # Check for valid cached entry within cache_ttl_seconds
            with self._cache_lock:
                if cache_key in self._cache:
                    cached_ts, cached_rollup = self._cache[cache_key]
                    if (now_ts - cached_ts) <= spec.cache_ttl_seconds:
                        self._cache.move_to_end(cache_key)
                        return cached_rollup

            # No valid cache available: raise ServiceUnavailableError
            raise ServiceUnavailableError(
                f"Federation endpoint '{spec.query_template}' unreachable and no valid cache found: {err}"
            ) from err
