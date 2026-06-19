from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    APP_NAME: str = "基于多源金融数据的股票基金趋势分析与风险评估系统"
    APP_ENV: str = "development"
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    MYSQL_DSN: str = (
        "mysql+pymysql://stock_user:stock_pass@127.0.0.1:3306/"
        "stock_analysis?charset=utf8mb4"
    )
    REDIS_URL: str = "redis://127.0.0.1:6379/0"

    QUOTE_CACHE_TTL_SECONDS: int = Field(default=5, ge=1)
    HISTORY_CACHE_TTL_SECONDS: int = Field(default=1800, ge=60)
    WS_PUSH_INTERVAL_SECONDS: int = Field(default=5, ge=1)
    SQL_ECHO: bool = False
    ENABLE_FIXTURE_FALLBACK: bool = False

    RISK_NOTICE: str = "仅供学习研究，不构成投资建议。"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
