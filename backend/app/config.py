import logging
import secrets
from typing import List

from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

_DEFAULT_JWT_SECRET = "dev-secret-change-in-production"


class Settings(BaseSettings):
    # Database
    # 生产环境使用 MySQL: mysql+pymysql://user:pass@127.0.0.1:3306/worldcup?charset=utf8mb4
    # 开发环境可继续使用 SQLite: sqlite:///./worldcup.db
    database_url: str = "sqlite:///./worldcup.db"

    # JWT
    jwt_secret: str = _DEFAULT_JWT_SECRET
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 24

    # CORS
    cors_origins: List[str] = [
        "http://localhost:9001",
        "http://127.0.0.1:9001",
    ]

    # API Keys — loaded from .env
    zafronix_api_key: str = ""
    odds_api_key: str = ""
    football_data_key: str = ""

    # Tournament dates
    tournament_start: str = "2026-06-11"
    tournament_end: str = "2026-07-19"

    # Paths
    seed_teams_path: str = "../data/teams_2026.json"

    model_config = {"env_file": "../data/.env"}


settings = Settings()

if settings.jwt_secret == _DEFAULT_JWT_SECRET:
    logger.warning(
        "⚠ JWT secret is the default value — tokens are not secure. "
        "Set JWT_SECRET in your environment or .env file."
    )
    # 自动生成随机密钥以防止使用默认值
    settings.jwt_secret = secrets.token_hex(32)
    logger.info("Auto-generated a random JWT secret for this session.")
