from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/project_workspace_demo"
    app_name: str = "project-workspace-demo"
    agent_provider: str = "scripted"

    class Config:
        env_file = ".env"


settings = Settings()
