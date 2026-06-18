from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    # 生产环境使用 MySQL: mysql+pymysql://user:pass@127.0.0.1:3306/worldcup?charset=utf8mb4
    # 开发环境可继续使用 SQLite: sqlite:///./worldcup.db
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
