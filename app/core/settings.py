from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', case_sensitive=False)

    app_name: str = 'Simulacao API'
    api_v1_prefix: str = '/api/v1'

    database_url: str

    celery_broker_url: str
    celery_result_backend: str

    log_level: str = 'INFO'

    # Optional: default timeouts for worker execution (seconds)
    simulation_timeout_seconds: int = 300


@lru_cache
def get_settings() -> Settings:
    return Settings()
