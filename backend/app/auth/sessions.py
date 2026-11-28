from datetime import UTC, datetime, timedelta
from hmac import compare_digest, digest
from secrets import token_bytes, token_urlsafe
from threading import Lock

COOKIE = "companywatch_session"
LIFETIME = timedelta(hours=8)


def utc_now():
    return datetime.now(UTC)


class Sessions:
    def __init__(self):
        self.signing_key = token_bytes(32)
        self.entries = {}
        self.lock = Lock()

    def signature(self, identifier):
        return digest(self.signing_key, identifier.encode(), "sha256").hex()

    def identifier(self, cookie):
        if cookie:
            identifier, _, signature = cookie.partition(".")
            if compare_digest(signature.encode(), self.signature(identifier).encode()):
                return identifier
        return None

    def create(self, user_id, previous_cookie):
        now = utc_now()
        identifier = token_urlsafe(32)
        with self.lock:
            self.entries.pop(self.identifier(previous_cookie), None)
            self.entries = {key: entry for key, entry in self.entries.items() if entry[1] > now}
            self.entries[identifier] = (user_id, now + LIFETIME)
        return f"{identifier}.{self.signature(identifier)}"

    def user_id(self, cookie):
        identifier = self.identifier(cookie)
        with self.lock:
            entry = self.entries.get(identifier)
            if entry:
                if entry[1] > utc_now():
                    return entry[0]
                self.entries.pop(identifier)
        return None

    def revoke(self, cookie):
        with self.lock:
            self.entries.pop(self.identifier(cookie), None)
