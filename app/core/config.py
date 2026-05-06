from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Signal"
    debug: bool = False

    database_url: str = ""

    groq_api_key: str = ""
    obsidian_vault_path: str = ""
    ai_relevance_threshold: float = 0.7
    fetch_interval_hours: int = 4

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
