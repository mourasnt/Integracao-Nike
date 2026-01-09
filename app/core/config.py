import os
from pydantic_settings import BaseSettings
from pydantic import ConfigDict

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

class Settings(BaseSettings):
    # Pydantic v2 style configuration
    model_config = ConfigDict(env_file=".env")

    database_url: str = f"sqlite+aiosqlite:///{os.path.join(BASE_DIR, 'test.db')}"
    secret_key: str = "change-me-very-secret"
    access_token_expire_minutes: int = 120
    jwt_algorithm: str = "HS256"

settings = Settings()
