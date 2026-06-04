from __future__ import annotations
from pydantic_settings import BaseSettings
from pydantic import Field
from zoneinfo import ZoneInfo


def _ids(value: str | None) -> set[int]:
    if not value:
        return set()
    out: set[int] = set()
    for raw in value.replace(';', ',').split(','):
        raw = raw.strip().strip('"').strip("'")
        if raw:
            try: out.add(int(raw))
            except ValueError: pass
    return out

class Settings(BaseSettings):
    BOT_TOKEN: str
    DATABASE_URL: str
    GROUP_ID: int = -1003996641790
    SUPER_ADMIN_IDS: str = ""
    ADMIN_IDS: str = ""
    TRUSTED_IDS: str = ""
    TIMEZONE: str = "Europe/Paris"
    BOT_VERSION: str = "1.0.0"
    RULES_HOURS: int = 2
    SHARE_HOURS: int = 3
    SUGGESTION_HOURS: int = 6
    LEADERBOARD_HOURS: int = 5
    TOP_INVITERS_HOUR: int = 12

    @property
    def db_url_async(self) -> str:
        url = self.DATABASE_URL.strip().strip('"').strip("'")
        if url.startswith('postgresql://'):
            return url.replace('postgresql://', 'postgresql+asyncpg://', 1)
        return url
    @property
    def super_admin_ids(self) -> set[int]: return _ids(self.SUPER_ADMIN_IDS)
    @property
    def admin_ids(self) -> set[int]: return _ids(self.ADMIN_IDS)
    @property
    def trusted_ids(self) -> set[int]: return _ids(self.TRUSTED_IDS)
    @property
    def tz(self): return ZoneInfo(self.TIMEZONE)

settings = Settings()
