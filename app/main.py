"""
Diet Insight Engine - FastAPI Application

Event-driven API for symptom analysis and dietary recommendations.

Components:
- SDO (Symptom-Diet Optimizer): Symptom processing and insights
- HSA (Health Store Agent): Product search and management
"""

import logging
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from omegaconf import OmegaConf

from diet.models.errors import ProblemDetail
from diet.utils.config_manager import get_config_manager

from .routers import diet_insight_router

logger = logging.getLogger("die.app")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan events."""
    logger.info("Starting Diet Insight Engine API...")

    from diet.sdo import get_sdo_engine
    engine = get_sdo_engine()
    await engine.initialize()

    yield

    await engine.shutdown()
    logger.info("Shutting down Diet Insight Engine API...")


def create_app() -> FastAPI:
    """
    Application factory.

    Creates and configures the FastAPI application with SDO and HSA routes.
    All hardcoded values are loaded from Hydra config via ConfigManager.
    """
    cfg = get_config_manager()
    _version = cfg.get("app.service.version", "0.0.0")
    _title = cfg.get("app.service.name", "Diet Insight Engine")
    _description = cfg.get(
        "app.service.description",
        "Event-driven API for symptom analysis and dietary recommendations powered by SDO and HSA",
    )

    app = FastAPI(
        title=f"{_title} API",
        description=_description,
        version=_version,
        lifespan=lifespan,
    )

    # Load CORS config
    cors_cfg = cfg.get("app.cors", None)
    if cors_cfg is not None:
        origins = OmegaConf.to_container(cors_cfg.allow_origins, resolve=True)
        # Filter out empty strings (from unset env interpolations)
        origins = [o for o in origins if o]
        allow_credentials = cors_cfg.get("allow_credentials", True)
        allow_methods = OmegaConf.to_container(cors_cfg.get("allow_methods", ["*"]), resolve=True)
        allow_headers = OmegaConf.to_container(cors_cfg.get("allow_headers", ["*"]), resolve=True)
    else:
        origins = ["*"]
        allow_credentials = True
        allow_methods = ["*"]
        allow_headers = ["*"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=allow_credentials,
        allow_methods=allow_methods,
        allow_headers=allow_headers,
    )

    # -------------------------------------------------------------------------
    # Correlation ID Middleware
    # -------------------------------------------------------------------------
    @app.middleware("http")
    async def correlation_id_middleware(request: Request, call_next):
        """Attach a correlation ID to every request and add it to structlog context."""
        correlation_id = request.headers.get(
            "X-Correlation-ID", str(uuid.uuid4())
        )
        request.state.correlation_id = correlation_id

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)

        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response

    # -------------------------------------------------------------------------
    # Global Exception Handlers
    # -------------------------------------------------------------------------
    # Load error handling config
    error_cfg_base_uri = cfg.get(
        "app.error_handling.problem_type_base_uri",
        "https://api.syntropyhealth.com/problems",
    )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Wrap FastAPI HTTPException responses in RFC 7807 ProblemDetail."""
        correlation_id = getattr(request.state, "correlation_id", str(uuid.uuid4()))

        if isinstance(exc.detail, dict):
            detail_str = exc.detail.get("message", str(exc.detail))
            error_type = exc.detail.get("error", "unknown_error")
        else:
            detail_str = str(exc.detail)
            error_type = "http_error"

        problem = ProblemDetail(
            type=f"{error_cfg_base_uri}/{error_type}",
            title=f"HTTP {exc.status_code}",
            status=exc.status_code,
            detail=detail_str,
            correlation_id=correlation_id,
            instance=str(request.url),
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=problem.model_dump(),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        """Catch-all handler returning RFC 7807 ProblemDetail for unexpected errors."""
        correlation_id = getattr(request.state, "correlation_id", str(uuid.uuid4()))
        logger.error(
            f"Unhandled exception: {exc}",
            exc_info=True,
            extra={"correlation_id": correlation_id},
        )
        problem = ProblemDetail(
            type=f"{error_cfg_base_uri}/internal-error",
            title="Internal Server Error",
            status=500,
            detail="An unexpected error occurred. Please try again later.",
            correlation_id=correlation_id,
            instance=str(request.url),
        )
        return JSONResponse(
            status_code=500,
            content=problem.model_dump(),
        )

    # -------------------------------------------------------------------------
    # Routes
    # -------------------------------------------------------------------------
    app.include_router(
        diet_insight_router,
        prefix="/api/v1",
        tags=["Diet Insight"],
    )

    @app.get("/health", tags=["Health"])
    async def health_check():
        """Health check with real component status."""
        from diet.sdo import get_sdo_engine

        engine = get_sdo_engine()
        sdo_status = "initialized" if engine._initialized else "not_initialized"

        return {
            "status": "healthy",
            "service": "diet-insight-engine",
            "version": _version,
            "components": {
                "sdo": {
                    "name": "Symptom-Diet Optimizer",
                    "status": sdo_status,
                },
                "hsa": {
                    "name": "Health Store Agent",
                    "status": "available",
                },
            }
        }

    return app


app = create_app()
