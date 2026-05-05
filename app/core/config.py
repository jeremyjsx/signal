from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Signal"
    debug: bool = False


settings = Settings()
