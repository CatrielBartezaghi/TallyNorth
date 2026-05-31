from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg2://tallynorth:tallynorth@localhost:5432/tallynorth"
    environment: str = "development"
    exchange_rate_cron_enabled: bool = True
    exchange_rate_cron_hours: str = "0,8,16"
    exchange_rate_sync_to: str = "ARS"
    exchange_rate_sync_from: str = "USD"

    class Config:
        env_file = ".env"


settings = Settings()
