from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import Engine

from app.api.auth import admin, auth, curator
from app.api.health import router as health_router
from app.api.onrc import router as onrc_router
from app.auth.limits import WebLimit, require_api_key, require_web_limit
from app.auth.sessions import Sessions
from app.config import Settings
from app.db import create_database_engine


def create_app(engine: Engine | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        database_engine = (
            engine if engine is not None else create_database_engine(Settings.from_env())
        )
        application.state.engine = database_engine
        application.state.sessions = Sessions()
        application.state.web_limit = WebLimit()
        try:
            yield
        finally:
            database_engine.dispose()

    application = FastAPI(title="CompanyWatch API", version="0.1.0", lifespan=lifespan)
    application.include_router(health_router)
    application.include_router(auth)
    application.include_router(admin)
    application.include_router(curator)
    application.include_router(
        onrc_router,
        prefix="/api/v1",
        dependencies=[Depends(require_api_key)],
        responses={
            401: {"description": "A valid API key is required."},
            429: {
                "description": "API key limit reached.",
                "headers": {"Retry-After": {"schema": {"type": "integer"}}},
            },
        },
    )
    application.include_router(
        onrc_router,
        prefix="/api/web/v1",
        dependencies=[Depends(require_web_limit)],
        responses={
            429: {
                "description": "Client IP limit reached.",
                "headers": {"Retry-After": {"schema": {"type": "integer"}}},
            },
        },
    )

    @application.exception_handler(RequestValidationError)
    async def validation_error(request: Request, error: RequestValidationError):
        if request.url.path.startswith(("/api/v1/auth/", "/api/v1/admin/", "/api/v1/curator/")):
            return JSONResponse(status_code=422, content={"detail": "Invalid operator request."})
        return await request_validation_exception_handler(request, error)

    return application


app = create_app()
