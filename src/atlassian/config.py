"""Atlassian settings loaded from environment variables."""

from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ATLASSIAN_")

    write_enabled: bool = False


class Auth(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ATLASSIAN_")

    url: str
    user: str
    token: SecretStr


config = Config()


@lru_cache
def get_auth() -> Auth:
    return Auth()  # type: ignore
