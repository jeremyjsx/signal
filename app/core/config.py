from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Signal"
    debug: bool = False

    database_url: str = ""
    api_key: str = ""

    groq_api_key: str = ""
    obsidian_vault_path: str = ""
    ai_relevance_threshold: float = 0.7
    fetch_interval_hours: int = 4
    cleanup_interval_hours: int = 24
    non_curated_retention_days: int = 30
    feed_disable_after_failures: int = 5
    http_user_agent: str = "SignalRSSBot/1.0"
    job_lock_app_key: int = 7300
    job_lock_fetch_feeds_key: int = 1
    job_lock_cleanup_articles_key: int = 2

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
