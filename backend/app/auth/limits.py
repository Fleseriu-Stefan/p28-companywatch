from datetime import UTC, datetime, timedelta
from hashlib import sha256
from ipaddress import ip_address
from math import ceil
from threading import Lock
from typing import Annotated

from fastapi import HTTPException, Request, Security
from fastapi.security import APIKeyHeader
from sqlalchemy import select
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.exc import SQLAlchemyError

from app.auth.models import api_keys, api_usage

API_KEY = APIKeyHeader(name="X-API-Key", auto_error=False)
MINUTE = timedelta(minutes=1)
DAY = timedelta(days=1)
KEY_MINUTE_LIMIT = 60
KEY_DAY_QUOTA = 5000
WEB_MINUTE_LIMIT = 120
MAX_WEB_PEERS = 65536


def utc_now():
    return datetime.now(UTC)


def exhausted(now, until):
    return HTTPException(
        429,
        "Request limit reached.",
        headers={"Retry-After": str(max(1, ceil((until - now).total_seconds())))},
    )


def require_api_key(request: Request, key: Annotated[str | None, Security(API_KEY)]):
    if not key:
        raise HTTPException(401, "A valid API key is required.")
    try:
        with request.app.state.engine.begin() as connection:
            # All requests for a key serialize here, including revocation.
            owner = connection.execute(
                select(api_keys.c.id, api_keys.c.daily_quota)
                .where(
                    api_keys.c.key_hash == sha256(key.encode()).digest(),
                    api_keys.c.revoked_at.is_(None),
                )
                .with_for_update()
            ).one_or_none()
            if owner is None:
                raise HTTPException(401, "A valid API key is required.")
            now = utc_now().replace(tzinfo=None)
            windows = (
                ("minute", now.replace(second=0, microsecond=0), MINUTE, KEY_MINUTE_LIMIT),
                (
                    "day",
                    now.replace(hour=0, minute=0, second=0, microsecond=0),
                    DAY,
                    owner.daily_quota,
                ),
            )
            previous = {
                row.window: row
                for row in connection.execute(
                    select(api_usage).where(api_usage.c.key_id == owner.id)
                )
            }
            increments, blocked = [], []
            for window, start, duration, limit in windows:
                row = previous.get(window)
                count = row.count if row and row.window_start == start else 0
                if count >= limit:
                    blocked.append(start + duration)
                increments.append(
                    dict(key_id=owner.id, window=window, window_start=start, count=count + 1)
                )
            if blocked:
                raise exhausted(now, max(blocked))
            statement = insert(api_usage).values(increments)
            connection.execute(
                statement.on_duplicate_key_update(
                    window_start=statement.inserted.window_start, count=statement.inserted.count
                )
            )
    except SQLAlchemyError:
        raise HTTPException(503, "Request authorization is temporarily unavailable.") from None
    request.state.external_api = True


class WebLimit:
    def __init__(self):
        self.minute = None
        self.counts = {}
        self.lock = Lock()

    def admit(self, peer):
        with self.lock:
            now = utc_now()
            minute = now.replace(second=0, microsecond=0)
            if minute != self.minute:
                self.minute = minute
                self.counts.clear()
            count = self.counts.get(peer, 0)
            if count >= WEB_MINUTE_LIMIT or (not count and len(self.counts) >= MAX_WEB_PEERS):
                raise exhausted(now, minute + MINUTE)
            self.counts[peer] = count + 1


def require_web_limit(request: Request):
    try:
        address = ip_address(request.client.host if request.client else "")
    except ValueError:
        raise HTTPException(503, "Client address is unavailable.") from None
    peer = getattr(address, "ipv4_mapped", None) or address
    request.app.state.web_limit.admit(peer)
