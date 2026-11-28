import re
from uuid import uuid4

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.auth.models import users

EMAIL_PATTERN = re.compile(r"[^\s@]+@[^\s@]+\.[^\s@]+")
MAX_PASSWORD = 1024
passwords = PasswordHasher()
dummy_hash = passwords.hash("unused-password-for-unrecognized-accounts")
public_fields = (users.c.id, users.c.email, users.c.role, users.c.active)


class AccountError(ValueError):
    pass


def normalize_email(email):
    normalized = email.strip().lower()
    if len(normalized) > 254 or not EMAIL_PATTERN.fullmatch(normalized):
        raise AccountError("Enter a valid email address.")
    return normalized


def create_user(connection, email, password, role):
    if not 1 <= len(password) <= MAX_PASSWORD:
        raise AccountError("Invalid password length.")
    user = dict(id=str(uuid4()), email=normalize_email(email), role=role, active=True)
    try:
        connection.execute(users.insert().values(**user, password_hash=passwords.hash(password)))
    except IntegrityError:
        raise AccountError("An account with this email already exists.") from None
    return user


def authenticate(engine, email, password):
    try:
        email = normalize_email(email)
    except AccountError:
        email = ""
    with engine.connect() as connection:
        account = (
            connection.execute(
                select(*public_fields, users.c.password_hash).where(users.c.email == email)
            )
            .mappings()
            .one_or_none()
        )
    try:
        passwords.verify(account["password_hash"] if account else dummy_hash, password)
    except VerifyMismatchError:
        return None
    if account and account["active"]:
        return {field.name: account[field.name] for field in public_fields}
    return None


def bootstrap_admin(engine, email, password):
    lock = "companywatch_bootstrap_admin"
    with engine.connect() as connection:
        if connection.scalar(select(func.get_lock(lock, 2))) != 1:
            raise AccountError("Another administrator bootstrap is in progress.")
        try:
            if connection.scalar(select(users.c.id).where(users.c.role == "admin").limit(1)):
                raise AccountError("An administrator already exists.")
            create_user(connection, email, password, "admin")
            connection.commit()
        finally:
            connection.rollback()
            if not connection.invalidated:
                connection.scalar(select(func.release_lock(lock)))
