from pydantic_settings import BaseSettings
from typing import Set


def parse_ids(value: str | None) -> Set[int]:
    if not value:
        return set()
    cleaned = value.replace('"', '').replace("'", '').replace(';', ',').strip()
    out: Set[int] = set()
    for part in cleaned.split(','):
        part = part.strip()
        if part:
            try:
                out.add(int(part))
            except ValueError:
                pass
    return out

class Settings(BaseSettings):
    BOT_TOKEN: str
    DATABASE_URL: str
    GROUP_ID: int = -1003996641790
    SUPER_ADMIN_IDS: str = ""
    ADMIN_IDS: str = ""
    TRUSTED_IDS: str = ""
    TIMEZONE: str = "Europe/Paris"
    BOT_USERNAME: str = ""

    @property
    def db_url_async(self) -> str:
        url = self.DATABASE_URL
        if url.startswith('postgresql://'):
            return url.replace('postgresql://', 'postgresql+asyncpg://', 1)
        if url.startswith('postgres://'):
            return url.replace('postgres://', 'postgresql+asyncpg://', 1)
        return url

    @property
    def super_admin_ids(self): return parse_ids(self.SUPER_ADMIN_IDS)
    @property
    def admin_ids(self): return parse_ids(self.ADMIN_IDS) | self.super_admin_ids
    @property
    def trusted_ids(self): return parse_ids(self.TRUSTED_IDS)

    class Config:
        env_file = '.env'
        extra = 'ignore'

settings = Settings()
