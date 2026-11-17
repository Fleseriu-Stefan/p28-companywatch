import pytest

from app.config import Settings


def test_missing_password_fails_without_echoing_environment(monkeypatch):
    monkeypatch.delenv("MYSQL_PASSWORD", raising=False)
    with pytest.raises(ValueError, match="MYSQL_PASSWORD is required"):
        Settings.from_env()


def test_url_handles_special_characters_without_exposing_password(monkeypatch):
    # Synthetic punctuation exercises URL encoding; no real credential is used.
    monkeypatch.setenv("MYSQL_PASSWORD", "@:/#%")
    monkeypatch.setenv("MYSQL_DATABASE", "companywatch")
    monkeypatch.setenv("MYSQL_USER", "companywatch")
    settings = Settings.from_env()
    assert settings.url.password == "@:/#%"
    assert "@:/#%" not in repr(settings)
    assert "@:/#%" not in str(settings.url)
