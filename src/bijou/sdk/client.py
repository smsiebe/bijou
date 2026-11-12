"""Feature-complete Synchronous and Asynchronous Python SDK clients for Bijou v2."""

from __future__ import annotations

import os
from datetime import date
from typing import Any

import httpx

from bijou.sdk.exceptions import (
    BijouApiError,
    BijouConnectionError,
    BijouNotFoundError,
    BijouPayloadTooLargeError,
    BijouPermissionDeniedError,
    BijouServiceUnavailableError,
    BijouValidationError,
)
from bijou.sdk.models import (
    AccessMode,
    AccessPerspectiveStateDTO,
    BijouManifestDTO,
    BillOfEffortsSimulationRequestDTO,
    BillOfEffortsSimulationResponseDTO,
    CapabilityTreeViewDTO,
    ConfidenceLevel,
    DecisionLogEntryDTO,
    DiagnosticReportDTO,
    EffortDTO,
    EffortEffortEdgeDTO,
    EffortFocalDashboardDTO,
    EffortInterestEdgeDTO,
    EffortTelemetryEventDTO,
    InterestDTO,
    InterestFocalDashboardDTO,
    InterestInterestEdgeDTO,
    OrganizationDTO,
    OrgEffortEdgeDTO,
    OrgFocalDashboardDTO,
    OrgInterestEdgeDTO,
    OrgOrgEdgeDTO,
    PerspectiveBriefingDTO,
    ResourcePoolDTO,
    ToolDescriptorDTO,
    TriPartiteFlowViewDTO,
)

DEFAULT_BASE_URL = "http://0.0.0.0:8000"


def _extract_error(resp: httpx.Response) -> tuple[int, Any, str]:
    status = resp.status_code
    body = resp.text
    try:
        data = resp.json()
        detail = data.get("detail", body) if isinstance(data, dict) else body
    except (ValueError, KeyError):
        detail = body
    return status, detail, body


def _raise_for_status(resp: httpx.Response) -> None:
    if resp.is_success:
        return
    status, detail, body = _extract_error(resp)
    msg = f"Bijou API Error ({status}): {detail}"
    if status == 403:
        raise BijouPermissionDeniedError(msg, status_code=status, detail=detail, response_body=body)
    if status == 404:
        raise BijouNotFoundError(msg, status_code=status, detail=detail, response_body=body)
    if status == 413:
        raise BijouPayloadTooLargeError(msg, status_code=status, detail=detail, response_body=body)
    if status in (400, 422):
        raise BijouValidationError(msg, status_code=status, detail=detail, response_body=body)
    if status == 503:
        raise BijouServiceUnavailableError(msg, status_code=status, detail=detail, response_body=body)
    raise BijouApiError(msg, status_code=status, detail=detail, response_body=body)


def _serialize(model_or_dict: Any, *, exclude_none: bool = True) -> dict[str, Any]:
    if hasattr(model_or_dict, "model_dump"):
        return dict(model_or_dict.model_dump(mode="json", exclude_none=exclude_none))
    return dict(model_or_dict)


class BijouClient:
    """Synchronous HTTP/ASGI client covering all Bijou v2 REST endpoints."""

    def __init__(
        self,
        base_url: str | None = None,
        transport: httpx.BaseTransport | None = None,
        timeout: float = 30.0,
        app: Any | None = None,
        client: httpx.Client | None = None,
        access_mode: AccessMode = AccessMode.GLOBAL_ANALYST,
        active_org_id: str | None = None,
        api_key: str | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        resolved_base = base_url or os.environ.get("BIJOU_SERVER_URL", DEFAULT_BASE_URL)
        self.base_url = resolved_base.rstrip("/")
        self.access_mode = access_mode
        self.active_org_id = active_org_id
        self.api_key = api_key
        self.extra_headers = dict(extra_headers or {})

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

    def __enter__(self) -> BijouClient:
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
        h = dict(self.extra_headers)
        mode_val = self.access_mode.value if isinstance(self.access_mode, AccessMode) else str(self.access_mode)
        h["X-Bijou-Access-Mode"] = mode_val
        if self.active_org_id:
            h["X-Bijou-Active-Org"] = self.active_org_id
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        headers = {**self._headers(), **kwargs.pop("headers", {})}
        try:
            resp = self._client.request(method, path, headers=headers, **kwargs)
            _raise_for_status(resp)
            return resp
        except (httpx.ConnectError, httpx.NetworkError) as err:
            raise BijouConnectionError(f"Network transport error connecting to {self.base_url}: {err}") from err

    # --- System & Perspective ---
    def health(self) -> dict[str, str]:
        return dict(self._request("GET", "/api/v1/health").json())

    def get_openapi_schema(self) -> dict[str, Any]:
        return dict(self._request("GET", "/openapi.json").json())

    def get_perspective_state(self) -> AccessPerspectiveStateDTO:
        return AccessPerspectiveStateDTO.model_validate(self._request("GET", "/api/v1/perspective").json())

    def list_tools(self) -> list[ToolDescriptorDTO]:
        return [ToolDescriptorDTO.model_validate(i) for i in self._request("GET", "/api/v1/tools").json()]

    # --- Organizations ---
    def upsert_organization(self, org: OrganizationDTO | dict[str, Any]) -> OrganizationDTO:
        payload = _serialize(org)
        return OrganizationDTO.model_validate(self._request("POST", "/api/v1/organizations", json=payload).json())

    def get_organization(self, org_id: str) -> OrganizationDTO:
        return OrganizationDTO.model_validate(self._request("GET", f"/api/v1/organizations/{org_id}").json())

    def list_organizations(self) -> list[OrganizationDTO]:
        return [OrganizationDTO.model_validate(i) for i in self._request("GET", "/api/v1/organizations").json()]

    def delete_organization(self, org_id: str) -> bool:
        return bool(self._request("DELETE", f"/api/v1/organizations/{org_id}").json().get("deleted", False))

    # --- Resource Pools ---
    def upsert_resource_pool(self, pool: ResourcePoolDTO | dict[str, Any]) -> ResourcePoolDTO:
        payload = _serialize(pool)
        return ResourcePoolDTO.model_validate(self._request("POST", "/api/v1/resource-pools", json=payload).json())

    def list_resource_pools(self, org_id: str | None = None) -> list[ResourcePoolDTO]:
        params = {"org_id": org_id} if org_id else {}
        return [
            ResourcePoolDTO.model_validate(i)
            for i in self._request("GET", "/api/v1/resource-pools", params=params).json()
        ]

    def delete_resource_pool(self, pool_id: str) -> bool:
        return bool(self._request("DELETE", f"/api/v1/resource-pools/{pool_id}").json().get("deleted", False))

    # --- Interests ---
    def upsert_interest(self, interest: InterestDTO | dict[str, Any]) -> InterestDTO:
        payload = _serialize(interest)
        return InterestDTO.model_validate(self._request("POST", "/api/v1/interests", json=payload).json())

    def get_interest(self, interest_id: str) -> InterestDTO:
        return InterestDTO.model_validate(self._request("GET", f"/api/v1/interests/{interest_id}").json())

    def list_interests(self) -> list[InterestDTO]:
        return [InterestDTO.model_validate(i) for i in self._request("GET", "/api/v1/interests").json()]

    def delete_interest(self, interest_id: str) -> bool:
        return bool(self._request("DELETE", f"/api/v1/interests/{interest_id}").json().get("deleted", False))

    # --- Efforts ---
    def upsert_effort(self, effort: EffortDTO | dict[str, Any]) -> EffortDTO:
        payload = _serialize(effort, exclude_none=False)
        return EffortDTO.model_validate(self._request("POST", "/api/v1/efforts", json=payload).json())

    def get_effort(self, effort_id: str) -> EffortDTO:
        return EffortDTO.model_validate(self._request("GET", f"/api/v1/efforts/{effort_id}").json())

    def list_efforts(self) -> list[EffortDTO]:
        return [EffortDTO.model_validate(i) for i in self._request("GET", "/api/v1/efforts").json()]

    def delete_effort(self, effort_id: str) -> bool:
        return bool(self._request("DELETE", f"/api/v1/efforts/{effort_id}").json().get("deleted", False))

    # --- Six Typed Edges ---
    def upsert_org_org_edge(self, edge: OrgOrgEdgeDTO | dict[str, Any]) -> OrgOrgEdgeDTO:
        payload = _serialize(edge)
        return OrgOrgEdgeDTO.model_validate(self._request("POST", "/api/v1/edges/org-org", json=payload).json())

    def upsert_org_interest_edge(self, edge: OrgInterestEdgeDTO | dict[str, Any]) -> OrgInterestEdgeDTO:
        payload = _serialize(edge)
        return OrgInterestEdgeDTO.model_validate(
            self._request("POST", "/api/v1/edges/org-interest", json=payload).json()
        )

    def upsert_interest_interest_edge(self, edge: InterestInterestEdgeDTO | dict[str, Any]) -> InterestInterestEdgeDTO:
        payload = _serialize(edge)
        return InterestInterestEdgeDTO.model_validate(
            self._request("POST", "/api/v1/edges/interest-interest", json=payload).json()
        )

    def upsert_org_effort_edge(
        self,
        edge: OrgEffortEdgeDTO | dict[str, Any],
        human_slip_penalty_days: int | None = None,
    ) -> OrgEffortEdgeDTO:
        payload = _serialize(edge)
        params = {"human_slip_penalty_days": human_slip_penalty_days} if human_slip_penalty_days is not None else {}
        return OrgEffortEdgeDTO.model_validate(
            self._request("POST", "/api/v1/edges/org-effort", json=payload, params=params).json()
        )

    def upsert_effort_interest_edge(self, edge: EffortInterestEdgeDTO | dict[str, Any]) -> EffortInterestEdgeDTO:
        payload = _serialize(edge)
        return EffortInterestEdgeDTO.model_validate(
            self._request("POST", "/api/v1/edges/effort-interest", json=payload).json()
        )

    def upsert_effort_effort_edge(self, edge: EffortEffortEdgeDTO | dict[str, Any]) -> EffortEffortEdgeDTO:
        payload = _serialize(edge)
        return EffortEffortEdgeDTO.model_validate(
            self._request("POST", "/api/v1/edges/effort-effort", json=payload).json()
        )

    def delete_edge(self, edge_category: str, edge_id: str) -> bool:
        return bool(self._request("DELETE", f"/api/v1/edges/{edge_category}/{edge_id}").json().get("deleted", False))

    # --- Manifest Interchange & Diagnostics ---
    def export_manifest(self) -> BijouManifestDTO:
        return BijouManifestDTO.model_validate(self._request("GET", "/api/v1/manifest/export").json())

    def import_manifest(self, manifest: BijouManifestDTO | dict[str, Any], replace_all: bool = False) -> dict[str, int]:
        payload = _serialize(manifest)
        return dict(
            self._request("POST", "/api/v1/manifest/import", json=payload, params={"replace_all": replace_all}).json()
        )

    def validate_manifest(self, manifest: BijouManifestDTO | dict[str, Any] | None = None) -> DiagnosticReportDTO:
        kwargs: dict[str, Any] = {}
        if manifest is not None:
            kwargs["json"] = _serialize(manifest)
        return DiagnosticReportDTO.model_validate(self._request("POST", "/api/v1/manifest/validate", **kwargs).json())

    # --- Views, Focal Dashboards & Simulation ---
    def get_capability_tree(
        self,
        as_of_date: date | str | None = None,
        include_hierarchy_priorities: bool = True,
        min_confidence: ConfidenceLevel | str | None = None,
        org_filter: str | None = None,
    ) -> CapabilityTreeViewDTO:
        params: dict[str, Any] = {"include_hierarchy_priorities": include_hierarchy_priorities}
        if as_of_date:
            params["as_of_date"] = str(as_of_date)
        if min_confidence:
            params["min_confidence"] = (
                min_confidence.value if isinstance(min_confidence, ConfidenceLevel) else min_confidence
            )
        if org_filter:
            params["org_filter"] = org_filter
        return CapabilityTreeViewDTO.model_validate(
            self._request("GET", "/api/v1/views/capability-tree", params=params).json()
        )

    def get_tripartite_flow(
        self,
        as_of_date: date | str | None = None,
        include_hierarchy_priorities: bool = True,
        min_confidence: ConfidenceLevel | str | None = None,
    ) -> TriPartiteFlowViewDTO:
        params: dict[str, Any] = {"include_hierarchy_priorities": include_hierarchy_priorities}
        if as_of_date:
            params["as_of_date"] = str(as_of_date)
        if min_confidence:
            params["min_confidence"] = (
                min_confidence.value if isinstance(min_confidence, ConfidenceLevel) else min_confidence
            )
        return TriPartiteFlowViewDTO.model_validate(
            self._request("GET", "/api/v1/views/tripartite-flow", params=params).json()
        )

    def simulate_bill_of_efforts(
        self,
        request_payload: BillOfEffortsSimulationRequestDTO | dict[str, Any],
        as_of_date: date | str | None = None,
    ) -> BillOfEffortsSimulationResponseDTO:
        payload = _serialize(request_payload)
        params = {"as_of_date": str(as_of_date)} if as_of_date else {}
        return BillOfEffortsSimulationResponseDTO.model_validate(
            self._request("POST", "/api/v1/simulation/bill-of-efforts", json=payload, params=params).json()
        )

    def commit_bill_of_efforts(
        self,
        request_payload: BillOfEffortsSimulationRequestDTO | dict[str, Any],
        as_of_date: date | str | None = None,
    ) -> BillOfEffortsSimulationResponseDTO:
        payload = _serialize(request_payload)
        params = {"as_of_date": str(as_of_date)} if as_of_date else {}
        return BillOfEffortsSimulationResponseDTO.model_validate(
            self._request("POST", "/api/v1/simulation/bill-of-efforts/commit", json=payload, params=params).json()
        )

    def get_effort_focal_dashboard(
        self, effort_id: str, as_of_date: date | str | None = None
    ) -> EffortFocalDashboardDTO:
        params = {"as_of_date": str(as_of_date)} if as_of_date else {}
        return EffortFocalDashboardDTO.model_validate(
            self._request("GET", f"/api/v1/views/efforts/{effort_id}/focal", params=params).json()
        )

    def get_org_focal_dashboard(
        self,
        org_id: str,
        as_of_date: date | str | None = None,
        include_hierarchy_priorities: bool = True,
    ) -> OrgFocalDashboardDTO:
        params: dict[str, Any] = {"include_hierarchy_priorities": include_hierarchy_priorities}
        if as_of_date:
            params["as_of_date"] = str(as_of_date)
        return OrgFocalDashboardDTO.model_validate(
            self._request("GET", f"/api/v1/views/organizations/{org_id}/focal", params=params).json()
        )

    def get_interest_focal_dashboard(
        self, interest_id: str, as_of_date: date | str | None = None
    ) -> InterestFocalDashboardDTO:
        params = {"as_of_date": str(as_of_date)} if as_of_date else {}
        return InterestFocalDashboardDTO.model_validate(
            self._request("GET", f"/api/v1/views/interests/{interest_id}/focal", params=params).json()
        )

    def get_perspective_briefing(
        self,
        subject_org_id: str,
        include_hierarchy_inheritance: bool = True,
        as_of_date: date | str | None = None,
    ) -> PerspectiveBriefingDTO:
        params: dict[str, Any] = {
            "subject_org_id": subject_org_id,
            "include_hierarchy_inheritance": include_hierarchy_inheritance,
        }
        if as_of_date:
            params["as_of_date"] = str(as_of_date)
        return PerspectiveBriefingDTO.model_validate(
            self._request("GET", "/api/v1/views/briefing", params=params).json()
        )

    # --- Telemetry & Decision Provenance Ledger ---
    def ingest_telemetry_events(self, events: list[EffortTelemetryEventDTO | dict[str, Any]]) -> int:
        payload = [_serialize(ev) for ev in events]
        res = self._request("POST", "/api/v1/telemetry/events", json=payload).json()
        return int(res.get("ingested", len(payload)))

    def trace_event_provenance(self, event_id: str, max_depth: int = 10) -> list[EffortTelemetryEventDTO]:
        res = self._request(
            "GET",
            f"/api/v1/telemetry/provenance/{event_id}",
            params={"max_depth": max_depth},
        ).json()
        return [EffortTelemetryEventDTO.model_validate(i) for i in res]

    def log_decision(self, entry: DecisionLogEntryDTO | dict[str, Any]) -> DecisionLogEntryDTO:
        payload = _serialize(entry)
        return DecisionLogEntryDTO.model_validate(self._request("POST", "/api/v1/decisions", json=payload).json())

    def list_decision_logs(self, target_effort_id: str | None = None) -> list[DecisionLogEntryDTO]:
        params = {"target_effort_id": target_effort_id} if target_effort_id else {}
        res = self._request("GET", "/api/v1/decisions", params=params).json()
        return [DecisionLogEntryDTO.model_validate(i) for i in res]


class AsyncBijouClient:
    """Asynchronous HTTP/ASGI client covering all Bijou v2 REST endpoints."""

    def __init__(
        self,
        base_url: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
        timeout: float = 30.0,
        app: Any | None = None,
        client: httpx.AsyncClient | None = None,
        access_mode: AccessMode = AccessMode.GLOBAL_ANALYST,
        active_org_id: str | None = None,
        api_key: str | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        resolved_base = base_url or os.environ.get("BIJOU_SERVER_URL", DEFAULT_BASE_URL)
        self.base_url = resolved_base.rstrip("/")
        self.access_mode = access_mode
        self.active_org_id = active_org_id
        self.api_key = api_key
        self.extra_headers = dict(extra_headers or {})

        if client is not None:
            self._client = client
        elif app is not None:
            self._client = httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url=self.base_url,
                timeout=timeout,
            )
        else:
            self._client = httpx.AsyncClient(base_url=self.base_url, transport=transport, timeout=timeout)

    async def __aenter__(self) -> AsyncBijouClient:
        await self._client.__aenter__()
        return self

    async def __aexit__(self, *args: object) -> None:
        await self._client.__aexit__(*args)

    async def close(self) -> None:
        await self._client.aclose()

    def set_perspective(self, access_mode: AccessMode, active_org_id: str | None = None) -> None:
        self.access_mode = access_mode
        self.active_org_id = active_org_id

    def _headers(self) -> dict[str, str]:
        h = dict(self.extra_headers)
        mode_val = self.access_mode.value if isinstance(self.access_mode, AccessMode) else str(self.access_mode)
        h["X-Bijou-Access-Mode"] = mode_val
        if self.active_org_id:
            h["X-Bijou-Active-Org"] = self.active_org_id
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        headers = {**self._headers(), **kwargs.pop("headers", {})}
        try:
            resp = await self._client.request(method, path, headers=headers, **kwargs)
            _raise_for_status(resp)
            return resp
        except (httpx.ConnectError, httpx.NetworkError) as err:
            raise BijouConnectionError(f"Network transport error connecting to {self.base_url}: {err}") from err

    # --- System & Perspective ---
    async def health(self) -> dict[str, str]:
        return dict((await self._request("GET", "/api/v1/health")).json())

    async def get_openapi_schema(self) -> dict[str, Any]:
        return dict((await self._request("GET", "/openapi.json")).json())

    async def get_perspective_state(self) -> AccessPerspectiveStateDTO:
        return AccessPerspectiveStateDTO.model_validate((await self._request("GET", "/api/v1/perspective")).json())

    async def list_tools(self) -> list[ToolDescriptorDTO]:
        return [ToolDescriptorDTO.model_validate(i) for i in (await self._request("GET", "/api/v1/tools")).json()]

    # --- Organizations ---
    async def upsert_organization(self, org: OrganizationDTO | dict[str, Any]) -> OrganizationDTO:
        return OrganizationDTO.model_validate(
            (await self._request("POST", "/api/v1/organizations", json=_serialize(org))).json()
        )

    async def get_organization(self, org_id: str) -> OrganizationDTO:
        return OrganizationDTO.model_validate(
            (await self._request("GET", f"/api/v1/organizations/{org_id}")).json()
        )

    async def list_organizations(self) -> list[OrganizationDTO]:
        return [
            OrganizationDTO.model_validate(i) for i in (await self._request("GET", "/api/v1/organizations")).json()
        ]

    async def delete_organization(self, org_id: str) -> bool:
        return bool((await self._request("DELETE", f"/api/v1/organizations/{org_id}")).json().get("deleted", False))

    # --- Resource Pools ---
    async def upsert_resource_pool(self, pool: ResourcePoolDTO | dict[str, Any]) -> ResourcePoolDTO:
        return ResourcePoolDTO.model_validate(
            (await self._request("POST", "/api/v1/resource-pools", json=_serialize(pool))).json()
        )

    async def list_resource_pools(self, org_id: str | None = None) -> list[ResourcePoolDTO]:
        params = {"org_id": org_id} if org_id else {}
        return [
            ResourcePoolDTO.model_validate(i)
            for i in (await self._request("GET", "/api/v1/resource-pools", params=params)).json()
        ]

    async def delete_resource_pool(self, pool_id: str) -> bool:
        return bool((await self._request("DELETE", f"/api/v1/resource-pools/{pool_id}")).json().get("deleted", False))

    # --- Interests ---
    async def upsert_interest(self, interest: InterestDTO | dict[str, Any]) -> InterestDTO:
        return InterestDTO.model_validate(
            (await self._request("POST", "/api/v1/interests", json=_serialize(interest))).json()
        )

    async def get_interest(self, interest_id: str) -> InterestDTO:
        return InterestDTO.model_validate((await self._request("GET", f"/api/v1/interests/{interest_id}")).json())

    async def list_interests(self) -> list[InterestDTO]:
        return [InterestDTO.model_validate(i) for i in (await self._request("GET", "/api/v1/interests")).json()]

    async def delete_interest(self, interest_id: str) -> bool:
        return bool((await self._request("DELETE", f"/api/v1/interests/{interest_id}")).json().get("deleted", False))

    # --- Efforts ---
    async def upsert_effort(self, effort: EffortDTO | dict[str, Any]) -> EffortDTO:
        return EffortDTO.model_validate(
            (await self._request("POST", "/api/v1/efforts", json=_serialize(effort, exclude_none=False))).json()
        )

    async def get_effort(self, effort_id: str) -> EffortDTO:
        return EffortDTO.model_validate((await self._request("GET", f"/api/v1/efforts/{effort_id}")).json())

    async def list_efforts(self) -> list[EffortDTO]:
        return [EffortDTO.model_validate(i) for i in (await self._request("GET", "/api/v1/efforts")).json()]

    async def delete_effort(self, effort_id: str) -> bool:
        return bool((await self._request("DELETE", f"/api/v1/efforts/{effort_id}")).json().get("deleted", False))

    # --- Six Typed Edges ---
    async def upsert_org_org_edge(self, edge: OrgOrgEdgeDTO | dict[str, Any]) -> OrgOrgEdgeDTO:
        return OrgOrgEdgeDTO.model_validate(
            (await self._request("POST", "/api/v1/edges/org-org", json=_serialize(edge))).json()
        )

    async def upsert_org_interest_edge(self, edge: OrgInterestEdgeDTO | dict[str, Any]) -> OrgInterestEdgeDTO:
        return OrgInterestEdgeDTO.model_validate(
            (await self._request("POST", "/api/v1/edges/org-interest", json=_serialize(edge))).json()
        )

    async def upsert_interest_interest_edge(
        self, edge: InterestInterestEdgeDTO | dict[str, Any]
    ) -> InterestInterestEdgeDTO:
        return InterestInterestEdgeDTO.model_validate(
            (await self._request("POST", "/api/v1/edges/interest-interest", json=_serialize(edge))).json()
        )

    async def upsert_org_effort_edge(
        self,
        edge: OrgEffortEdgeDTO | dict[str, Any],
        human_slip_penalty_days: int | None = None,
    ) -> OrgEffortEdgeDTO:
        params = {"human_slip_penalty_days": human_slip_penalty_days} if human_slip_penalty_days is not None else {}
        return OrgEffortEdgeDTO.model_validate(
            (await self._request("POST", "/api/v1/edges/org-effort", json=_serialize(edge), params=params)).json()
        )

    async def upsert_effort_interest_edge(self, edge: EffortInterestEdgeDTO | dict[str, Any]) -> EffortInterestEdgeDTO:
        return EffortInterestEdgeDTO.model_validate(
            (await self._request("POST", "/api/v1/edges/effort-interest", json=_serialize(edge))).json()
        )

    async def upsert_effort_effort_edge(self, edge: EffortEffortEdgeDTO | dict[str, Any]) -> EffortEffortEdgeDTO:
        return EffortEffortEdgeDTO.model_validate(
            (await self._request("POST", "/api/v1/edges/effort-effort", json=_serialize(edge))).json()
        )

    async def delete_edge(self, edge_category: str, edge_id: str) -> bool:
        return bool(
            (await self._request("DELETE", f"/api/v1/edges/{edge_category}/{edge_id}")).json().get("deleted", False)
        )

    # --- Manifest Interchange & Diagnostics ---
    async def export_manifest(self) -> BijouManifestDTO:
        return BijouManifestDTO.model_validate((await self._request("GET", "/api/v1/manifest/export")).json())

    async def import_manifest(
        self, manifest: BijouManifestDTO | dict[str, Any], replace_all: bool = False
    ) -> dict[str, int]:
        return dict(
            (
                await self._request(
                    "POST",
                    "/api/v1/manifest/import",
                    json=_serialize(manifest),
                    params={"replace_all": replace_all},
                )
            ).json()
        )

    async def validate_manifest(self, manifest: BijouManifestDTO | dict[str, Any] | None = None) -> DiagnosticReportDTO:
        kwargs: dict[str, Any] = {}
        if manifest is not None:
            kwargs["json"] = _serialize(manifest)
        return DiagnosticReportDTO.model_validate(
            (await self._request("POST", "/api/v1/manifest/validate", **kwargs)).json()
        )

    # --- Views, Focal Dashboards & Simulation ---
    async def get_capability_tree(
        self,
        as_of_date: date | str | None = None,
        include_hierarchy_priorities: bool = True,
        min_confidence: ConfidenceLevel | str | None = None,
        org_filter: str | None = None,
    ) -> CapabilityTreeViewDTO:
        params: dict[str, Any] = {"include_hierarchy_priorities": include_hierarchy_priorities}
        if as_of_date:
            params["as_of_date"] = str(as_of_date)
        if min_confidence:
            params["min_confidence"] = (
                min_confidence.value if isinstance(min_confidence, ConfidenceLevel) else min_confidence
            )
        if org_filter:
            params["org_filter"] = org_filter
        return CapabilityTreeViewDTO.model_validate(
            (await self._request("GET", "/api/v1/views/capability-tree", params=params)).json()
        )

    async def get_tripartite_flow(
        self,
        as_of_date: date | str | None = None,
        include_hierarchy_priorities: bool = True,
        min_confidence: ConfidenceLevel | str | None = None,
    ) -> TriPartiteFlowViewDTO:
        params: dict[str, Any] = {"include_hierarchy_priorities": include_hierarchy_priorities}
        if as_of_date:
            params["as_of_date"] = str(as_of_date)
        if min_confidence:
            params["min_confidence"] = (
                min_confidence.value if isinstance(min_confidence, ConfidenceLevel) else min_confidence
            )
        return TriPartiteFlowViewDTO.model_validate(
            (await self._request("GET", "/api/v1/views/tripartite-flow", params=params)).json()
        )

    async def simulate_bill_of_efforts(
        self,
        request_payload: BillOfEffortsSimulationRequestDTO | dict[str, Any],
        as_of_date: date | str | None = None,
    ) -> BillOfEffortsSimulationResponseDTO:
        params = {"as_of_date": str(as_of_date)} if as_of_date else {}
        return BillOfEffortsSimulationResponseDTO.model_validate(
            (
                await self._request(
                    "POST",
                    "/api/v1/simulation/bill-of-efforts",
                    json=_serialize(request_payload),
                    params=params,
                )
            ).json()
        )

    async def commit_bill_of_efforts(
        self,
        request_payload: BillOfEffortsSimulationRequestDTO | dict[str, Any],
        as_of_date: date | str | None = None,
    ) -> BillOfEffortsSimulationResponseDTO:
        params = {"as_of_date": str(as_of_date)} if as_of_date else {}
        return BillOfEffortsSimulationResponseDTO.model_validate(
            (
                await self._request(
                    "POST",
                    "/api/v1/simulation/bill-of-efforts/commit",
                    json=_serialize(request_payload),
                    params=params,
                )
            ).json()
        )

    async def get_effort_focal_dashboard(
        self, effort_id: str, as_of_date: date | str | None = None
    ) -> EffortFocalDashboardDTO:
        params = {"as_of_date": str(as_of_date)} if as_of_date else {}
        return EffortFocalDashboardDTO.model_validate(
            (await self._request("GET", f"/api/v1/views/efforts/{effort_id}/focal", params=params)).json()
        )

    async def get_org_focal_dashboard(
        self,
        org_id: str,
        as_of_date: date | str | None = None,
        include_hierarchy_priorities: bool = True,
    ) -> OrgFocalDashboardDTO:
        params: dict[str, Any] = {"include_hierarchy_priorities": include_hierarchy_priorities}
        if as_of_date:
            params["as_of_date"] = str(as_of_date)
        return OrgFocalDashboardDTO.model_validate(
            (await self._request("GET", f"/api/v1/views/organizations/{org_id}/focal", params=params)).json()
        )

    async def get_interest_focal_dashboard(
        self, interest_id: str, as_of_date: date | str | None = None
    ) -> InterestFocalDashboardDTO:
        params = {"as_of_date": str(as_of_date)} if as_of_date else {}
        return InterestFocalDashboardDTO.model_validate(
            (await self._request("GET", f"/api/v1/views/interests/{interest_id}/focal", params=params)).json()
        )

    async def get_perspective_briefing(
        self,
        subject_org_id: str,
        include_hierarchy_inheritance: bool = True,
        as_of_date: date | str | None = None,
    ) -> PerspectiveBriefingDTO:
        params: dict[str, Any] = {
            "subject_org_id": subject_org_id,
            "include_hierarchy_inheritance": include_hierarchy_inheritance,
        }
        if as_of_date:
            params["as_of_date"] = str(as_of_date)
        return PerspectiveBriefingDTO.model_validate(
            (await self._request("GET", "/api/v1/views/briefing", params=params)).json()
        )

    # --- Telemetry & Decision Provenance Ledger ---
    async def ingest_telemetry_events(self, events: list[EffortTelemetryEventDTO | dict[str, Any]]) -> int:
        payload = [_serialize(ev) for ev in events]
        res = (await self._request("POST", "/api/v1/telemetry/events", json=payload)).json()
        return int(res.get("ingested", len(payload)))

    async def trace_event_provenance(self, event_id: str, max_depth: int = 10) -> list[EffortTelemetryEventDTO]:
        res = (
            await self._request(
                "GET",
                f"/api/v1/telemetry/provenance/{event_id}",
                params={"max_depth": max_depth},
            )
        ).json()
        return [EffortTelemetryEventDTO.model_validate(i) for i in res]

    async def log_decision(self, entry: DecisionLogEntryDTO | dict[str, Any]) -> DecisionLogEntryDTO:
        return DecisionLogEntryDTO.model_validate(
            (await self._request("POST", "/api/v1/decisions", json=_serialize(entry))).json()
        )

    async def list_decision_logs(self, target_effort_id: str | None = None) -> list[DecisionLogEntryDTO]:
        params = {"target_effort_id": target_effort_id} if target_effort_id else {}
        res = (await self._request("GET", "/api/v1/decisions", params=params)).json()
        return [DecisionLogEntryDTO.model_validate(i) for i in res]
