from typing import Literal

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError

from app.db import is_database_ready

router = APIRouter(prefix="/health", tags=["Health"])


class LiveResponse(BaseModel):
    status: Literal["ok"] = "ok"


class ReadyResponse(BaseModel):
    status: Literal["ready"] = "ready"


class NotReadyResponse(BaseModel):
    status: Literal["not_ready"] = "not_ready"


@router.get("/live", response_model=LiveResponse)
def live() -> LiveResponse:
    """Check API process availability without accessing MySQL."""
    return LiveResponse()


@router.get(
    "/ready",
    response_model=ReadyResponse,
    responses={503: {"model": NotReadyResponse, "description": "Database or schema unavailable"}},
)
def ready(request: Request) -> ReadyResponse | JSONResponse:
    """Check MySQL connectivity and the expected Alembic revision (C-001)."""
    try:
        if is_database_ready(request.app.state.engine):
            return ReadyResponse()
    except SQLAlchemyError:
        pass
    return JSONResponse(status_code=503, content=NotReadyResponse().model_dump())
