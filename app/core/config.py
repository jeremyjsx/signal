from typing import Literal
from urllib.parse import urlparse

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def database_uses_tls(database_url: str, mode: Literal["auto", "on", "off"]) -> bool:
    if mode == "on":
        return True
    if mode == "off":
        return False
    raw = database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    try:
        parsed = urlparse(raw)
    except ValueError:
        return False
    host = (parsed.hostname or "").lower()
    if host in ("localhost", "127.0.0.1", "::1"):
        return False
    haystack = f"{host} {database_url.lower()}"
    cloud_markers = (
        "supabase.co",
        "supabase.com",
        "pooler.supabase",
        "neon.tech",
        "amazonaws.com",
    )
    return any(m in haystack for m in cloud_markers)


class Settings(BaseSettings):
    app_name: str = "Signal"
    debug: bool = False

    database_url: str = ""
    database_ssl: Literal["auto", "on", "off"] = Field(
        default="auto",
        description="TLS: auto enables for Supabase, Neon, RDS-like hosts; on/off to force.",
    )
    api_key: str = ""
    cors_origins: str = ""

    groq_api_key: str = ""
    obsidian_vault_path: str = ""
    ai_relevance_threshold: float = 0.7
    fetch_interval_hours: int = 4
    cleanup_interval_hours: int = 24
    non_curated_retention_days: int = 30
    feed_disable_after_failures: int = 5
    feed_quality_min_scored_articles: int = 10
    feed_quality_min_curated_rate: float = 0.1
    http_user_agent: str = "SignalRSSBot/1.0"
    job_lock_app_key: int = 7300
    job_lock_fetch_feeds_key: int = 1
    job_lock_cleanup_articles_key: int = 2

    model_config = SettingsConfigDict(env_file=".env")

    @field_validator("database_ssl", mode="before")
    @classmethod
    def normalize_database_ssl(cls, v: object) -> object:
        if isinstance(v, str):
            s = v.strip().lower()
            if s == "":
                return "auto"
            if s in ("auto", "on", "off"):
                return s
        return "auto"

    @field_validator("database_url", mode="before")
    @classmethod
    def coerce_async_database_url(cls, v: object) -> object:
        if not isinstance(v, str) or not v.strip():
            return v
        s = v.strip()
        if s.startswith("postgres://"):
            return "postgresql+asyncpg://" + s.removeprefix("postgres://")
        if s.startswith("postgresql://") and not s.startswith("postgresql+asyncpg://"):
            return "postgresql+asyncpg://" + s.removeprefix("postgresql://")
        return s


settings = Settings()
