"""Synchronous and Asynchronous Bijou API Clients."""

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
    CausalGate,
    Concern,
    Effect,
    GraphEdge,
    ManifestPayload,
    Organization,
    PerspectiveBriefing,
    SlipSimulationResult,
    TechTreeStratificationMode,
    TechTreeView,
    Thing,
    ThingFocalDashboard,
    TradeoffProposalComparison,
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
    """Synchronous HTTP client for interacting with the Bijou Decision-Support Engine."""

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        transport: httpx.BaseTransport | None = None,
        timeout: float = 30.0,
        app: Any | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        if client is not None:
            self._client = client
        elif app is not None:
            try:
                from starlette.testclient import TestClient

                self._client = TestClient(app, base_url=self.base_url)
            except ImportError:
                self._client = httpx.Client(base_url=self.base_url, transport=transport, timeout=timeout)
        elif transport is not None and isinstance(transport, httpx.AsyncBaseTransport):
            app_target = getattr(transport, "app", None)
            if app_target is not None:
                try:
                    from starlette.testclient import TestClient

                    self._client = TestClient(app_target, base_url=self.base_url)
                except ImportError:
                    self._client = httpx.Client(base_url=self.base_url, transport=transport, timeout=timeout)
            else:
                self._client = httpx.Client(base_url=self.base_url, transport=transport, timeout=timeout)
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

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        try:
            resp = self._client.request(method, path, **kwargs)
            _raise_for_status(resp)
            return resp
        except (httpx.ConnectError, httpx.NetworkError) as err:
            raise BijouConnectionError(f"Network transport error connecting to {self.base_url}: {err}") from err

    # Organizations
    def create_organization(self, org: Organization | dict[str, Any]) -> Organization:
        payload = org.model_dump(mode="json") if isinstance(org, Organization) else org
        resp = self._request("POST", "/api/v1/organizations", json=payload)
        return Organization.model_validate(resp.json())

    def get_organization(self, org_id: str) -> Organization:
        resp = self._request("GET", f"/api/v1/organizations/{org_id}")
        return Organization.model_validate(resp.json())

    def list_organizations(self) -> list[Organization]:
        resp = self._request("GET", "/api/v1/organizations")
        return [Organization.model_validate(item) for item in resp.json()]

    # Things
    def create_thing(self, thing: Thing | dict[str, Any]) -> Thing:
        payload = thing.model_dump(mode="json") if isinstance(thing, Thing) else thing
        resp = self._request("POST", "/api/v1/things", json=payload)
        return Thing.model_validate(resp.json())

    def get_thing(self, thing_id: str) -> Thing:
        resp = self._request("GET", f"/api/v1/things/{thing_id}")
        return Thing.model_validate(resp.json())

    def list_things(self) -> list[Thing]:
        resp = self._request("GET", "/api/v1/things")
        return [Thing.model_validate(item) for item in resp.json()]

    # Concerns
    def create_concern(self, concern: Concern | dict[str, Any]) -> Concern:
        payload = concern.model_dump(mode="json") if isinstance(concern, Concern) else concern
        resp = self._request("POST", "/api/v1/concerns", json=payload)
        return Concern.model_validate(resp.json())

    def get_concern(self, concern_id: str) -> Concern:
        resp = self._request("GET", f"/api/v1/concerns/{concern_id}")
        return Concern.model_validate(resp.json())

    def list_concerns(self) -> list[Concern]:
        resp = self._request("GET", "/api/v1/concerns")
        return [Concern.model_validate(item) for item in resp.json()]

    # Causal Gates
    def create_causal_gate(self, gate: CausalGate | dict[str, Any]) -> CausalGate:
        payload = gate.model_dump(mode="json") if isinstance(gate, CausalGate) else gate
        resp = self._request("POST", "/api/v1/causal-gates", json=payload)
        return CausalGate.model_validate(resp.json())

    def get_causal_gate(self, gate_id: str) -> CausalGate:
        resp = self._request("GET", f"/api/v1/causal-gates/{gate_id}")
        return CausalGate.model_validate(resp.json())

    # Effects
    def create_effect(self, effect: Effect | dict[str, Any]) -> Effect:
        payload = effect.model_dump(mode="json") if isinstance(effect, Effect) else effect
        resp = self._request("POST", "/api/v1/effects", json=payload)
        return Effect.model_validate(resp.json())

    def get_effect(self, effect_id: str) -> Effect:
        resp = self._request("GET", f"/api/v1/effects/{effect_id}")
        return Effect.model_validate(resp.json())

    def list_effects(self) -> list[Effect]:
        resp = self._request("GET", "/api/v1/effects")
        return [Effect.model_validate(item) for item in resp.json()]

    # Edges
    def create_edge(self, edge: GraphEdge | dict[str, Any]) -> GraphEdge:
        payload = edge.model_dump(mode="json") if isinstance(edge, GraphEdge) else edge
        resp = self._request("POST", "/api/v1/edges", json=payload)
        return GraphEdge.model_validate(resp.json())

    def list_edges(self) -> list[GraphEdge]:
        resp = self._request("GET", "/api/v1/edges")
        return [GraphEdge.model_validate(item) for item in resp.json()]

    # Manifest
    def export_manifest(self) -> ManifestPayload:
        resp = self._request("GET", "/api/v1/manifest/export")
        return ManifestPayload.model_validate(resp.json())

    def import_manifest(self, manifest: ManifestPayload | dict[str, Any], replace_all: bool = False) -> dict[str, Any]:
        payload = manifest.model_dump(mode="json") if isinstance(manifest, ManifestPayload) else manifest
        resp = self._request("POST", "/api/v1/manifest/import", json=payload, params={"replace_all": replace_all})
        return resp.json()

    # Views & Analysis
    def get_tech_tree(
        self,
        stratification_mode: TechTreeStratificationMode | str = TechTreeStratificationMode.TRL_TIERS,
        as_of_date: date | str | None = None,
        org_filter: str | None = None,
    ) -> TechTreeView:
        mode_val = stratification_mode.value if isinstance(stratification_mode, TechTreeStratificationMode) else stratification_mode
        params: dict[str, Any] = {"stratification_mode": mode_val}
        if as_of_date:
            params["as_of_date"] = str(as_of_date)
        if org_filter:
            params["org_filter"] = org_filter
        resp = self._request("GET", "/api/v1/views/tech-tree", params=params)
        return TechTreeView.model_validate(resp.json())

    def simulate_slip(
        self,
        milestone_id: str,
        slip_days: int,
        simulate_cancellation: bool = False,
    ) -> SlipSimulationResult:
        resp = self._request(
            "POST",
            "/api/v1/analysis/simulate-slip",
            json={
                "milestone_id": milestone_id,
                "slip_days": slip_days,
                "simulate_cancellation": simulate_cancellation,
            },
        )
        return SlipSimulationResult.model_validate(resp.json())

    def get_perspective_briefing(
        self,
        subject_org_id: str,
        perspective_org_id: str | None = None,
        include_descendants: bool = True,
        as_of_date: date | str | None = None,
    ) -> PerspectiveBriefing:
        params: dict[str, Any] = {"include_descendants": include_descendants}
        if perspective_org_id:
            params["perspective_org_id"] = perspective_org_id
        if as_of_date:
            params["as_of_date"] = str(as_of_date)
        resp = self._request("GET", f"/api/v1/views/perspectives/{subject_org_id}", params=params)
        return PerspectiveBriefing.model_validate(resp.json())

    def get_thing_focal_dashboard(self, thing_id: str, as_of_date: date | str | None = None) -> ThingFocalDashboard:
        params: dict[str, Any] = {}
        if as_of_date:
            params["as_of_date"] = str(as_of_date)
        resp = self._request("GET", f"/api/v1/views/things/{thing_id}/focal", params=params)
        return ThingFocalDashboard.model_validate(resp.json())

    def evaluate_tradeoff(self, proposed_thing_ids: list[str]) -> TradeoffProposalComparison:
        resp = self._request("POST", "/api/v1/analysis/tradeoff", json=proposed_thing_ids)
        return TradeoffProposalComparison.model_validate(resp.json())


class AsyncBijouClient:
    """Asynchronous HTTP client for interacting with the Bijou Decision-Support Engine."""

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        transport: httpx.AsyncBaseTransport | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            transport=transport,
            timeout=timeout,
        )

    async def __aenter__(self) -> Self:
        await self._client.__aenter__()
        return self

    async def __aexit__(self, *args: object) -> None:
        await self._client.__aexit__(*args)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        try:
            resp = await self._client.request(method, path, **kwargs)
            _raise_for_status(resp)
            return resp
        except (httpx.ConnectError, httpx.NetworkError) as err:
            raise BijouConnectionError(f"Network transport error connecting to {self.base_url}: {err}") from err

    async def list_organizations(self) -> list[Organization]:
        resp = await self._request("GET", "/api/v1/organizations")
        return [Organization.model_validate(item) for item in resp.json()]

    async def get_tech_tree(
        self,
        stratification_mode: TechTreeStratificationMode | str = TechTreeStratificationMode.TRL_TIERS,
    ) -> TechTreeView:
        mode_val = (
            stratification_mode.value
            if isinstance(stratification_mode, TechTreeStratificationMode)
            else stratification_mode
        )
        resp = await self._request("GET", "/api/v1/views/tech-tree", params={"stratification_mode": mode_val})
        return TechTreeView.model_validate(resp.json())
