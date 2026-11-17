from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import Engine

from app.api.health import router
from app.config import Settings
from app.db import create_database_engine


def create_app(engine: Engine | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        database_engine = (
            engine if engine is not None else create_database_engine(Settings.from_env())
        )
        application.state.engine = database_engine
        try:
            yield
        finally:
            database_engine.dispose()

    application = FastAPI(title="CompanyWatch API", version="0.1.0", lifespan=lifespan)
    application.include_router(router)
    return application


app = create_app()
