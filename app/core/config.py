from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import ConfigDict, Field

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    # Pydantic v2 style configuration; reads values from environment or .env
    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = Field(default=f"sqlite+aiosqlite:///{BASE_DIR / 'test.db'}", env="DATABASE_URL")
    secret_key: str = Field(default="change-me-very-secret", env="SECRET_KEY")
    access_token_expire_minutes: int = Field(default=120, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")

settings = Settings()
