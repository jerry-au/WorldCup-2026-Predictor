from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite:///./worldcup.db"

    # JWT
    jwt_secret: str = "dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 24

    # API Keys — loaded from .env
    zafronix_api_key: str = ""
    odds_api_key: str = ""
    football_data_key: str = ""

    # Paths
    seed_teams_path: str = "../data/teams_2026.json"

    model_config = {"env_file": "../data/.env"}


settings = Settings()
