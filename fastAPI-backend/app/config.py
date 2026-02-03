"""
Application configuration using Pydantic Settings
"""

from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Application
    app_name: str = Field(default="TenantBackend", description="Application name")
    app_env: str = Field(default="development", description="Environment")
    debug: bool = Field(default=False, description="Debug mode")
    secret_key: str = Field(description="Secret key for JWT encoding")
    api_v1_prefix: str = Field(default="/api/v1", description="API v1 prefix")
    bff_web_prefix: str = Field(default="/bff/web", description="Web BFF prefix")
    
    # Database
    postgres_host: str = Field(default="localhost")
    postgres_port: int = Field(default=5432)
    postgres_user: str = Field(default="tenant_admin")
    postgres_password: str = Field(default="tenant_secure_password_123")
    postgres_db: str = Field(default="tenant_db")
    database_url: str | None = Field(default=None)
    
    # CORS
    cors_origins: List[str] = Field(
        default=["http://localhost:4200", "http://localhost:3000"]
    )
    
    # Username Generation
    username_prefix: str = Field(default="user_")
    username_length: int = Field(default=8, ge=6, le=20)
    
    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            import json
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [origin.strip() for origin in v.split(",")]
        return v
    
    @property
    def async_database_url(self) -> str:
        """Build async database URL."""
        if self.database_url:
            return self.database_url
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )
    
    @property
    def sync_database_url(self) -> str:
        """Build sync database URL for Alembic."""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()


settings = get_settings()