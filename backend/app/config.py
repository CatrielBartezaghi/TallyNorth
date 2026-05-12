from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg2://tallynorth:tallynorth@localhost:5432/tallynorth"
    environment: str = "development"

    class Config:
        env_file = ".env"


settings = Settings()
