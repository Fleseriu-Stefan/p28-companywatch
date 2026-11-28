from datetime import UTC, datetime
from hashlib import sha256
from secrets import token_urlsafe
from typing import Annotated, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field, SecretStr
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.auth.accounts import (
    MAX_PASSWORD,
    AccountError,
    authenticate,
    create_user,
    public_fields,
)
from app.auth.limits import KEY_DAY_QUOTA
from app.auth.models import api_keys, users
from app.auth.sessions import COOKIE, LIFETIME
from app.etl.errors import ETLError
from app.etl.models import versions
from app.etl.service import Pipeline

auth = APIRouter(prefix="/api/v1/auth", tags=["Operator session"])
admin = APIRouter(prefix="/api/v1/admin", tags=["Administrator"])
curator = APIRouter(prefix="/api/v1/curator", tags=["Curator"])
COOKIE_OPTIONS = dict(httponly=True, secure=True, samesite="strict", path="/api/v1")


class Credentials(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: Annotated[str, Field(min_length=1, max_length=254)]
    password: Annotated[SecretStr, Field(min_length=1, max_length=MAX_PASSWORD)]


class User(BaseModel):
    id: UUID
    email: str
    role: Literal["curator", "admin"]
    active: bool


class NewKey(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    owner_id: UUID
    name: Annotated[str, Field(min_length=1, max_length=120)]


class IssuedKey(NewKey):
    id: UUID
    key_prefix: str
    daily_quota: int
    key: str


class Approval(BaseModel):
    model_config = ConfigDict(extra="forbid")
    report_hash: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]


def unavailable():
    return HTTPException(503, "Operator data is temporarily unavailable.")


def same_origin(request: Request):
    origin = request.headers.get("origin")
    if origin is not None and origin != f"{request.url.scheme}://{request.url.netloc}":
        raise HTTPException(403, "The request origin is forbidden.")


def operator(request: Request):
    user_id = request.app.state.sessions.user_id(request.cookies.get(COOKIE))
    if user_id is None:
        raise HTTPException(401, "Sign in to continue.")
    try:
        with request.app.state.engine.connect() as connection:
            user = (
                connection.execute(
                    select(*public_fields).where(users.c.id == user_id, users.c.active.is_(True))
                )
                .mappings()
                .one_or_none()
            )
    except SQLAlchemyError:
        raise unavailable() from None
    if user is None:
        raise HTTPException(401, "Sign in to continue.")
    return user


Operator = Annotated[dict, Depends(operator)]


def admin_only(user: Operator):
    if user["role"] != "admin":
        raise HTTPException(403, "Administrator access is required.")


def curator_only(user: Operator):
    if user["role"] != "curator":
        raise HTTPException(403, "Curator access is required.")


admin.dependencies = [Depends(admin_only), Depends(same_origin)]
curator.dependencies = [Depends(curator_only), Depends(same_origin)]


@auth.post("/login", response_model=User, dependencies=[Depends(same_origin)])
def login(body: Credentials, request: Request, response: Response):
    try:
        user = authenticate(request.app.state.engine, body.email, body.password.get_secret_value())
    except SQLAlchemyError:
        raise unavailable() from None
    if user is None:
        raise HTTPException(401, "Invalid email or password.")
    token = request.app.state.sessions.create(user["id"], request.cookies.get(COOKIE))
    response.set_cookie(COOKIE, token, max_age=int(LIFETIME.total_seconds()), **COOKIE_OPTIONS)
    response.headers["Cache-Control"] = "no-store"
    return user


@auth.post("/logout", status_code=204, dependencies=[Depends(same_origin)])
def logout(request: Request, response: Response):
    request.app.state.sessions.revoke(request.cookies.get(COOKIE))
    response.delete_cookie(COOKIE, **COOKIE_OPTIONS)
    response.headers["Cache-Control"] = "no-store"


@auth.get("/me", response_model=User)
def me(user: Operator, response: Response):
    response.headers["Cache-Control"] = "no-store"
    return user


@admin.post("/curators", status_code=201, response_model=User)
def add_curator(body: Credentials, request: Request, response: Response):
    try:
        with request.app.state.engine.begin() as connection:
            user = create_user(connection, body.email, body.password.get_secret_value(), "curator")
    except AccountError as error:
        raise HTTPException(409, str(error)) from None
    except SQLAlchemyError:
        raise unavailable() from None
    response.headers["Cache-Control"] = "no-store"
    return user


@admin.delete("/curators/{user_id}", status_code=204)
def deactivate_curator(user_id: UUID, request: Request):
    try:
        with request.app.state.engine.begin() as connection:
            updated = connection.execute(
                users.update()
                .where(users.c.id == str(user_id), users.c.role == "curator")
                .values(active=False)
            )
            if not updated.rowcount:
                raise HTTPException(404, "Curator account is unavailable.")
    except SQLAlchemyError:
        raise unavailable() from None


@admin.post("/api-keys", status_code=201, response_model=IssuedKey)
def issue_key(body: NewKey, request: Request, response: Response):
    key = token_urlsafe(32)
    values = dict(
        id=str(uuid4()),
        owner_id=str(body.owner_id),
        name=body.name,
        key_prefix=key[:12],
        daily_quota=KEY_DAY_QUOTA,
    )
    try:
        with request.app.state.engine.begin() as connection:
            owner = connection.scalar(
                select(users.c.id)
                .where(users.c.id == values["owner_id"], users.c.active.is_(True))
                .with_for_update()
            )
            if owner is None:
                raise HTTPException(404, "Key owner is unavailable.")
            connection.execute(
                api_keys.insert().values(**values, key_hash=sha256(key.encode()).digest())
            )
    except SQLAlchemyError:
        raise unavailable() from None
    response.headers["Cache-Control"] = "no-store"
    return {**values, "key": key}


@admin.delete("/api-keys/{key_id}", status_code=204)
def revoke_key(key_id: UUID, request: Request):
    try:
        with request.app.state.engine.begin() as connection:
            existing = connection.execute(
                select(api_keys.c.revoked_at).where(api_keys.c.id == str(key_id)).with_for_update()
            ).one_or_none()
            if existing is None:
                raise HTTPException(404, "API key is unavailable.")
            if existing.revoked_at is None:
                connection.execute(
                    api_keys.update()
                    .where(api_keys.c.id == str(key_id))
                    .values(revoked_at=datetime.now(UTC).replace(tzinfo=None))
                )
    except SQLAlchemyError:
        raise unavailable() from None


@curator.get("/versions")
def review_versions(
    request: Request, response: Response, state: Literal["review", "approved"] = "review"
):
    try:
        with request.app.state.engine.connect() as connection:
            rows = (
                connection.execute(
                    select(
                        versions.c.id,
                        versions.c.edition,
                        versions.c.state,
                        versions.c.report,
                        versions.c.report_hash,
                    )
                    .where(versions.c.state == state, versions.c.source_kind == "real")
                    .order_by(versions.c.edition, versions.c.id)
                )
                .mappings()
                .all()
            )
    except SQLAlchemyError:
        raise unavailable() from None
    response.headers["Cache-Control"] = "no-store"
    return {"items": [dict(row) for row in rows]}


@curator.post("/versions/{version_id}/approve", status_code=204)
def approve(version_id: UUID, body: Approval, request: Request):
    try:
        Pipeline(request.app.state.engine).approve(str(version_id), body.report_hash)
    except ETLError:
        raise HTTPException(409, "The version or reviewed report cannot be approved.") from None
    except SQLAlchemyError:
        raise unavailable() from None


@curator.post("/versions/{version_id}/publish", status_code=204)
def publish(version_id: UUID, request: Request):
    engine = request.app.state.engine
    try:
        with engine.connect() as connection:
            approval = connection.scalar(
                select(versions.c.approval).where(versions.c.id == str(version_id))
            )
        if approval is None:
            raise HTTPException(409, "The version requires approval before publishing.")
        Pipeline(engine).publish(str(version_id), approval)
    except ETLError:
        raise HTTPException(409, "The version or its approval cannot be published.") from None
    except SQLAlchemyError:
        raise unavailable() from None
