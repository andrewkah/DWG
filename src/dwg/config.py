from pathlib import Path
from pydantic import PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIRECTORY = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    DATABASE_URL: str
    
    @field_validator("DATABASE_URL", mode="before")
    def assemble_async_db_connection(cls, v: str) -> str:
        if isinstance(v, str) and v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v
    
    # Model config
    model_config = SettingsConfigDict(env_file=ROOT_DIRECTORY / ".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()