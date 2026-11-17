import os
from dataclasses import dataclass, field
from typing import Self

from sqlalchemy import URL


def required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise ValueError(f"{name} is required")
    return value


@dataclass(frozen=True)
class Settings:
    database: str
    user: str
    password: str = field(repr=False)
    host: str = "db"
    port: int = 3306

    @classmethod
    def from_env(cls) -> Self:
        password = required_env("MYSQL_PASSWORD")
        return cls(
            database=required_env("MYSQL_DATABASE"),
            user=required_env("MYSQL_USER"),
            password=password,
            host=os.environ.get("MYSQL_HOST", "db"),
            port=int(os.environ.get("MYSQL_PORT", "3306")),
        )

    @property
    def url(self) -> URL:
        return URL.create(
            "mysql+pymysql",
            username=self.user,
            password=self.password,
            host=self.host,
            port=self.port,
            database=self.database,
            query={"charset": "utf8mb4"},
        )
