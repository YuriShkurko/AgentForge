from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/hybrid_scoring_demo"
    app_name: str = "hybrid-scoring-demo"
    provider_name: str = "fixture"

    class Config:
        env_file = ".env"


settings = Settings()
