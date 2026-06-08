from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    slack_webhook_url: str | None = None
    schedule_cron: str = Field(default="0 18 * * 1-5", description="APScheduler cron: minute hour day month day_of_week")

    watchlist_us: str = "AAPL,MSFT,NVDA"
    watchlist_cn: str = "600519,000001,300750"
    watchlist_hk: str = "0700.HK,9988.HK,3690.HK"

    host: str = "0.0.0.0"
    port: int = 8000

    def us_symbols(self) -> list[str]:
        return [s.strip() for s in self.watchlist_us.split(",") if s.strip()]

    def cn_symbols(self) -> list[str]:
        return [s.strip() for s in self.watchlist_cn.split(",") if s.strip()]

    def hk_symbols(self) -> list[str]:
        return [s.strip() for s in self.watchlist_hk.split(",") if s.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
