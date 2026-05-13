from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/hybrid_scoring_demo"
    app_name: str = "hybrid-scoring-demo"
    provider_name: str = "fixture"
    agent_provider: str = "scripted"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    class Config:
        env_file = ".env"


settings = Settings()
