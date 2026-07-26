from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg2://tallynorth:tallynorth@localhost:5432/tallynorth"
    environment: str = "development"
    openai_api_key: str | None = None
    openai_agent_model: str = "gpt-4.1-mini"
    openai_agent_max_turns: int = 4
    app_timezone: str = 'America/Buenos_Aires'
    chatgpt_action_base_url: str | None = None
    exchange_rate_cron_enabled: bool = True
    exchange_rate_cron_hours: str = "0,8,16"
    exchange_rate_sync_to: str = "ARS"
    exchange_rate_sync_from: str = "USD"

    class Config:
        env_file = ".env"


settings = Settings()
