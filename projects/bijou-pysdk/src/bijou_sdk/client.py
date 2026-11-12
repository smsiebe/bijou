"""Synchronous and Asynchronous Bijou v2 API Clients."""

from datetime import date
from typing import Any

import httpx
from typing_extensions import Self

from .exceptions import (
    BijouApiError,
    BijouConnectionError,
    BijouNotFoundError,
    BijouValidationError,
)
from .models import (
    AccessMode,
    BillOfEffortsSimulationResult,
    CapabilityTreeView,
    ConfidenceLevel,
    Effort,
    EffortEffortEdge,
    EffortInterestEdge,
    Interest,
    InterestInterestEdge,
    ManifestPayload,
    OrgEffortEdge,
    OrgInterestEdge,
    OrgOrgEdge,
    Organization,
    ResourcePool,
    TriPartiteFlowView,
)

DEFAULT_BASE_URL = "http://bijou.internal:8000"


def _extract_error(resp: httpx.Response) -> tuple[int, Any, str]:
    status = resp.status_code
    body = resp.text
    try:
        data = resp.json()
        detail = data.get("detail", body)
    except (ValueError, KeyError):
        detail = body
    return status, detail, body


def _raise_for_status(resp: httpx.Response) -> None:
    if resp.is_success:
        return
    status, detail, body = _extract_error(resp)
    msg = f"Bijou API Error ({status}): {detail}"
    if status == 404:
        raise BijouNotFoundError(msg, status_code=status, detail=detail, response_body=body)
    if status == 422:
        raise BijouValidationError(msg, status_code=status, detail=detail, response_body=body)
    raise BijouApiError(msg, status_code=status, detail=detail, response_body=body)


class BijouClient:
    """Synchronous HTTP/ASGI client for Bijou v2."""

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        transport: httpx.BaseTransport | None = None,
        timeout: float = 30.0,
        app: Any | None = None,
        client: httpx.Client | None = None,
        access_mode: AccessMode = AccessMode.GLOBAL_ANALYST,
        active_org_id: str | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.access_mode = access_mode
        self.active_org_id = active_org_id

        if client is not None:
            self._client = client
        elif app is not None:
            from starlette.testclient import TestClient

            self._client = TestClient(app, base_url=self.base_url)
        else:
            self._client = httpx.Client(
                base_url=self.base_url,
                transport=transport,
                timeout=timeout,
            )

    def __enter__(self) -> Self:
        self._client.__enter__()
        return self

    def __exit__(self, *args: object) -> None:
        self._client.__exit__(*args)

    def close(self) -> None:
        self._client.close()

    def set_perspective(self, access_mode: AccessMode, active_org_id: str | None = None) -> None:
        self.access_mode = access_mode
        self.active_org_id = active_org_id

    def _headers(self) -> dict[str, str]:
        h = {"X-Bijou-Access-Mode": self.access_mode.value}
        if self.active_org_id:
            h["X-Bijou-Active-Org"] = self.active_org_id
        return h

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        headers = {**self._headers(), **kwargs.pop("headers", {})}
        try:
            resp = self._client.request(method, path, headers=headers, **kwargs)
            _raise_for_status(resp)
            return resp
        except (httpx.ConnectError, httpx.NetworkError) as err:
            raise BijouConnectionError(f"Network transport error connecting to {self.base_url}: {err}") from err

    # Organizations & Resource Pools
    def upsert_organization(self, org: Organization | dict[str, Any]) -> Organization:
        payload = org.model_dump(mode="json", exclude_none=True) if isinstance(org, Organization) else org
        return Organization.model_validate(self._request("POST", "/api/v1/organizations", json=payload).json())

    def get_organization(self, org_id: str) -> Organization:
        return Organization.model_validate(self._request("GET", f"/api/v1/organizations/{org_id}").json())

    def list_organizations(self) -> list[Organization]:
        return [Organization.model_validate(i) for i in self._request("GET", "/api/v1/organizations").json()]

    def upsert_resource_pool(self, pool: ResourcePool | dict[str, Any]) -> ResourcePool:
        payload = pool.model_dump(mode="json", exclude_none=True) if isinstance(pool, ResourcePool) else pool
        return ResourcePool.model_validate(self._request("POST", "/api/v1/resource-pools", json=payload).json())

    def list_resource_pools(self, org_id: str | None = None) -> list[ResourcePool]:
        params = {"org_id": org_id} if org_id else {}
        return [ResourcePool.model_validate(i) for i in self._request("GET", "/api/v1/resource-pools", params=params).json()]

    # Interests
    def upsert_interest(self, interest: Interest | dict[str, Any]) -> Interest:
        payload = interest.model_dump(mode="json", exclude_none=True) if isinstance(interest, Interest) else interest
        return Interest.model_validate(self._request("POST", "/api/v1/interests", json=payload).json())

    def get_interest(self, interest_id: str) -> Interest:
        return Interest.model_validate(self._request("GET", f"/api/v1/interests/{interest_id}").json())

    def list_interests(self) -> list[Interest]:
        return [Interest.model_validate(i) for i in self._request("GET", "/api/v1/interests").json()]

    # Efforts
    def upsert_effort(self, effort: Effort | dict[str, Any]) -> Effort:
        payload = effort.model_dump(mode="json") if isinstance(effort, Effort) else effort
        return Effort.model_validate(self._request("POST", "/api/v1/efforts", json=payload).json())

    def get_effort(self, effort_id: str) -> Effort:
        return Effort.model_validate(self._request("GET", f"/api/v1/efforts/{effort_id}").json())

    def list_efforts(self) -> list[Effort]:
        return [Effort.model_validate(i) for i in self._request("GET", "/api/v1/efforts").json()]

    # Typed Edges
    def upsert_org_org_edge(self, edge: OrgOrgEdge | dict[str, Any]) -> OrgOrgEdge:
        payload = edge.model_dump(mode="json", exclude_none=True) if isinstance(edge, OrgOrgEdge) else edge
        return OrgOrgEdge.model_validate(self._request("POST", "/api/v1/edges/org-org", json=payload).json())

    def upsert_org_interest_edge(self, edge: OrgInterestEdge | dict[str, Any]) -> OrgInterestEdge:
        payload = edge.model_dump(mode="json", exclude_none=True) if isinstance(edge, OrgInterestEdge) else edge
        return OrgInterestEdge.model_validate(self._request("POST", "/api/v1/edges/org-interest", json=payload).json())

    def upsert_interest_interest_edge(self, edge: InterestInterestEdge | dict[str, Any]) -> InterestInterestEdge:
        payload = edge.model_dump(mode="json", exclude_none=True) if isinstance(edge, InterestInterestEdge) else edge
        return InterestInterestEdge.model_validate(
            self._request("POST", "/api/v1/edges/interest-interest", json=payload).json()
        )

    def upsert_org_effort_edge(self, edge: OrgEffortEdge | dict[str, Any]) -> OrgEffortEdge:
        payload = edge.model_dump(mode="json", exclude_none=True) if isinstance(edge, OrgEffortEdge) else edge
        return OrgEffortEdge.model_validate(self._request("POST", "/api/v1/edges/org-effort", json=payload).json())

    def upsert_effort_interest_edge(self, edge: EffortInterestEdge | dict[str, Any]) -> EffortInterestEdge:
        payload = edge.model_dump(mode="json", exclude_none=True) if isinstance(edge, EffortInterestEdge) else edge
        return EffortInterestEdge.model_validate(
            self._request("POST", "/api/v1/edges/effort-interest", json=payload).json()
        )

    def upsert_effort_effort_edge(self, edge: EffortEffortEdge | dict[str, Any]) -> EffortEffortEdge:
        payload = edge.model_dump(mode="json", exclude_none=True) if isinstance(edge, EffortEffortEdge) else edge
        return EffortEffortEdge.model_validate(
            self._request("POST", "/api/v1/edges/effort-effort", json=payload).json()
        )

    # Manifest
    def export_manifest(self) -> ManifestPayload:
        return ManifestPayload.model_validate(self._request("GET", "/api/v1/manifest/export").json())

    def import_manifest(self, manifest: ManifestPayload | dict[str, Any], replace_all: bool = False) -> dict[str, Any]:
        payload = manifest.model_dump(mode="json", exclude_none=True) if isinstance(manifest, ManifestPayload) else manifest
        return self._request("POST", "/api/v1/manifest/import", json=payload, params={"replace_all": replace_all}).json()

    # Views & Simulation (A / B / C)
    def get_capability_tree(
        self,
        as_of_date: date | str | None = None,
        include_hierarchy_priorities: bool = True,
        min_confidence: ConfidenceLevel | str | None = None,
    ) -> CapabilityTreeView:
        params: dict[str, Any] = {"include_hierarchy_priorities": include_hierarchy_priorities}
        if as_of_date:
            params["as_of_date"] = str(as_of_date)
        if min_confidence:
            params["min_confidence"] = min_confidence.value if isinstance(min_confidence, ConfidenceLevel) else min_confidence
        return CapabilityTreeView.model_validate(self._request("GET", "/api/v1/views/capability-tree", params=params).json())

    def get_tripartite_flow(
        self,
        as_of_date: date | str | None = None,
        include_hierarchy_priorities: bool = True,
    ) -> TriPartiteFlowView:
        params: dict[str, Any] = {"include_hierarchy_priorities": include_hierarchy_priorities}
        if as_of_date:
            params["as_of_date"] = str(as_of_date)
        return TriPartiteFlowView.model_validate(self._request("GET", "/api/v1/views/tripartite-flow", params=params).json())

    def simulate_bill_of_efforts(self, request_payload: dict[str, Any]) -> BillOfEffortsSimulationResult:
        return BillOfEffortsSimulationResult.model_validate(
            self._request("POST", "/api/v1/simulation/bill-of-efforts", json=request_payload).json()
        )

    def get_effort_focal_dashboard(self, effort_id: str) -> dict[str, Any]:
        return self._request("GET", f"/api/v1/views/efforts/{effort_id}/focal").json()

    def get_perspective_briefing(self, subject_org_id: str) -> dict[str, Any]:
        return self._request("GET", "/api/v1/views/briefing", params={"subject_org_id": subject_org_id}).json()

    def validate_manifest(self) -> dict[str, Any]:
        return self._request("POST", "/api/v1/manifest/validate").json()

    def health(self) -> dict[str, str]:
        return self._request("GET", "/api/v1/health").json()


class AsyncBijouClient:
    """Asynchronous HTTP/ASGI client for Bijou v2."""

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        transport: httpx.AsyncBaseTransport | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(base_url=self.base_url, transport=transport, timeout=timeout)

    async def __aenter__(self) -> Self:
        await self._client.__aenter__()
        return self

    async def __aexit__(self, *args: object) -> None:
        await self._client.__aexit__(*args)

    async def close(self) -> None:
        await self._client.aclose()

    async def health(self) -> dict[str, str]:
        resp = await self._client.get("/api/v1/health")
        _raise_for_status(resp)
        return resp.json()
