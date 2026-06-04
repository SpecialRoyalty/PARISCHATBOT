from __future__ import annotations
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


def parse_ids(raw: str | None) -> set[int]:
    if not raw:
        return set()
    ids: set[int] = set()
    for x in raw.replace(';', ',').split(','):
        x = x.strip().strip('\"').strip("'")
        if x:
            try:
                ids.add(int(x))
            except ValueError:
                pass
    return ids


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
    BOT_TOKEN: str
    DATABASE_URL: str
    GROUP_ID: int = -1003996641790
    SUPER_ADMIN_IDS: str = ''
    ADMIN_IDS: str = ''
    TRUSTED_IDS: str = ''
    TIMEZONE: str = 'Europe/Paris'
    PRONO_REPOST_MINUTES: int = 30
    LEADERBOARD_HOURS: int = 5
    RULES_HOURS: int = 2
    SHARE_HOURS: int = 3
    SUGGESTION_HOURS: int = 6
    IDENTITY_PUBLIC_COOLDOWN_HOURS: int = 12
    MIN_RANKING_PARTICIPATIONS: int = 10
    FORBID_LINKS: bool = True
    APP_VERSION: str = '1.0.0'

    @property
    def super_admin_ids(self) -> set[int]: return parse_ids(self.SUPER_ADMIN_IDS)
    @property
    def admin_ids(self) -> set[int]: return parse_ids(self.ADMIN_IDS) | self.super_admin_ids
    @property
    def trusted_ids(self) -> set[int]: return parse_ids(self.TRUSTED_IDS)


@lru_cache
def get_settings() -> Settings:
    return Settings()
