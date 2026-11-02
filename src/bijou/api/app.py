"""FastAPI application factory, lifespan management, and static mounting."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from bijou.adapters.db import SqlAlchemyGraphRepository
from bijou.adapters.federation import HttpFederationConnector
from bijou.adapters.llm import AuraRouterAdapter
from bijou.adapters.telemetry import DuckDbTelemetryStore
from bijou.api.deps import set_orchestrator
from bijou.api.v1.routers import v1_router
from bijou.config import BijouSettings
from bijou.core.engine import InMemoryGraphProjectionEngine
from bijou.core.ports.exceptions import EntityNotFoundError, ServiceUnavailableError
from bijou.services import BijouOrchestrationService


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan context manager initializing repository, telemetry, and orchestrator."""
    settings: BijouSettings = getattr(app.state, "settings", BijouSettings())

    # Initialize infrastructure adapters if not already provided (e.g. via test injection)
    repo = getattr(app.state, "repository", None)
    if repo is None:
        repo = SqlAlchemyGraphRepository(db_uri=settings.db_uri)
        app.state.repository = repo

    telemetry_store = getattr(app.state, "telemetry_store", None)
    if telemetry_store is None:
        telemetry_store = DuckDbTelemetryStore(db_path=settings.duckdb_path)
        app.state.telemetry_store = telemetry_store

    federation_connector = getattr(app.state, "federation_connector", None)
    if federation_connector is None:
        federation_connector = HttpFederationConnector()
        app.state.federation_connector = federation_connector

    reasoning_broker = getattr(app.state, "reasoning_broker", None)
    if reasoning_broker is None:
        reasoning_broker = AuraRouterAdapter(
            aurarouter_url=settings.aurarouter_url,
            model=settings.aurarouter_model,
        )
        app.state.reasoning_broker = reasoning_broker

    projection_engine = getattr(app.state, "projection_engine", None)
    if projection_engine is None:
        projection_engine = InMemoryGraphProjectionEngine()
        app.state.projection_engine = projection_engine

    orchestrator = getattr(app.state, "orchestrator", None)
    if orchestrator is None:
        orchestrator = BijouOrchestrationService(
            repository=repo,
            projection_engine=projection_engine,
            telemetry_store=telemetry_store,
            federation_connector=federation_connector,
            reasoning_broker=reasoning_broker,
            enable_reasoning=settings.enable_reasoning,
        )
        orchestrator.initialize()
        app.state.orchestrator = orchestrator

    set_orchestrator(orchestrator)

    yield

    # Clean shutdown of connection pools
    set_orchestrator(None)
    if hasattr(repo, "close"):
        repo.close()
    if hasattr(telemetry_store, "close"):
        telemetry_store.close()
    if hasattr(federation_connector, "close"):
        federation_connector.close()
    if hasattr(reasoning_broker, "close"):
        reasoning_broker.close()


def create_app(settings: BijouSettings | None = None) -> FastAPI:
    """Create and configure the FastAPI application instance."""
    app_settings = settings or BijouSettings()

    app = FastAPI(
        title="Bijou Causal Graph API",
        version="1.0.0",
        description="Offline-capable multi-echelon causal graph and decision-support engine.",
        lifespan=lifespan,
    )
    app.state.settings = app_settings

    # Exception Handlers
    @app.exception_handler(ServiceUnavailableError)
    async def service_unavailable_handler(
        request: Request,
        exc: ServiceUnavailableError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": str(exc)},
        )

    @app.exception_handler(EntityNotFoundError)
    async def entity_not_found_handler(
        request: Request,
        exc: EntityNotFoundError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": str(exc)},
        )

    # Middleware: Payload Size Limit
    @app.middleware("http")
    async def payload_size_limit_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > app_settings.max_payload_bytes:
            return JSONResponse(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                content={"detail": "Payload exceeds maximum allowed bytes limit"},
            )
        return await call_next(request)

    # Mount API routers
    app.include_router(v1_router)

    # Static Web distribution files
    static_dir = Path(__file__).parent.parent / "web" / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

        @app.get("/", include_in_schema=False)
        def serve_index() -> FileResponse:
            index_file = static_dir / "index.html"
            return FileResponse(str(index_file))

    return app


app = create_app()
