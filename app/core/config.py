import os
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import ConfigDict, Field
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(override=False)

class Settings(BaseSettings):
    model_config = ConfigDict(env_file=None)

    database_url: str = Field(default=f"sqlite+aiosqlite:///{BASE_DIR / 'test.db'}", env="DATABASE_URL")
    secret_key: str = Field(default="change-me-very-secret", env="SECRET_KEY")
    access_token_expire_minutes: int = Field(default=120, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    front_users: list[str] = Field(default=["integracao_logistica", "sbf"], env="FRONT_USERS")
    front_admin_users: list[str] = Field(default=["integracao_logistica"], env="FRONT_ADMIN_USERS")

settings = Settings()
