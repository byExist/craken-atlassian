"""Atlassian settings loaded from environment variables."""

from functools import lru_cache

from pydantic import SecretStr, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ATLASSIAN_")

    write_enabled: bool = False


class Auth(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ATLASSIAN_")

    domain: str
    user: str
    token: SecretStr

    @computed_field
    @property
    def url(self) -> str:
        return f"https://{self.domain}"


config = Config()


@lru_cache
def get_auth() -> Auth:
    return Auth()  # type: ignore
