from pydantic_settings import BaseSettings, EnvSettingsSource
from pydantic.fields import FieldInfo
from typing import List, Any, Tuple, Type
import json


class SafeEnvSource(EnvSettingsSource):
    """Extends EnvSettingsSource to handle empty strings and comma-separated lists."""

    def decode_complex_value(self, field_name: str, field: FieldInfo, value: Any) -> Any:
        if isinstance(value, str):
            v = value.strip()
            if not v:
                return []  # empty string → empty list
            if not v.startswith("[") and not v.startswith("{"):
                # "123,456" → ["123", "456"] — pydantic will coerce to List[int]
                return [x.strip() for x in v.split(",") if x.strip()]
        return json.loads(value)


class Settings(BaseSettings):
    bot_token: str = "test_bot_token"
    secret_key: str = "change-this-secret-key-in-production"
    database_url: str = "sqlite:///./arkadium.db"
    admin_telegram_ids: List[int] = []
    organizer_telegram_ids: List[int] = []
    cors_origins: List[str] = ["http://localhost:5173", "http://localhost:3000"]
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days
    dev_mode: bool = True  # set to False in production
    # Web admin panel credentials
    panel_username: str = "admin"
    panel_password: str = "arkadium2026"

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: Any,
        env_settings: Any,
        dotenv_settings: Any,
        file_secret_settings: Any,
    ) -> Tuple[Any, ...]:
        return (
            init_settings,
            SafeEnvSource(settings_cls),
            dotenv_settings,
            file_secret_settings,
        )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
