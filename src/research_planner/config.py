"""Fixed numeric internal origin; no DNS, redirects or request-selected providers."""

from ipaddress import ip_address, ip_network
from typing import Annotated, Literal, Self
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, StringConstraints, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

INTERNAL_NETWORKS = tuple(
    ip_network(n)
    for n in ("127.0.0.0/8", "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "::1/128", "fc00::/7")
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="RESEARCH_PLANNER_", extra="forbid")

    model_url: str | None = None
    model_api_key: SecretStr | None = None
    service_api_key: SecretStr | None = None
    model: Annotated[
        str, StringConstraints(min_length=1, max_length=160, pattern=r"^[\w./:-]+$")
    ] = "Qwen/Qwen3-4B-Instruct-2507"
    timeout_seconds: float = Field(default=8, ge=0.1, le=30, allow_inf_nan=False)
    max_tokens: int = Field(default=1200, ge=256, le=2048)
    output_mode: Literal["json_schema", "json_object"] = "json_schema"
    max_concurrent_requests: int = Field(default=2, ge=1, le=8)

    @field_validator("model_url")
    @classmethod
    def internal_origin(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if any(ord(character) <= 32 or ord(character) >= 127 for character in value):
            raise ValueError("invalid_internal_origin_characters")
        try:
            url = urlsplit(value)
            address = ip_address(url.hostname or "")
            valid = (
                url.scheme in {"http", "https"}
                and url.path in {"", "/"}
                and not url.query
                and not url.fragment
                and url.username is None
                and url.password is None
                and url.port is not None
                and 1 <= url.port <= 65535
                and "%" not in value
                and any(address in network for network in INTERNAL_NETWORKS)
                and (url.scheme == "https" or address.is_loopback)
            )
        except ValueError:
            valid = False
        if not valid:
            raise ValueError("model_url_must_be_numeric_internal_origin_with_explicit_port")
        return value.rstrip("/")

    @field_validator("model_api_key", "service_api_key")
    @classmethod
    def safe_key(cls, value: SecretStr | None) -> SecretStr | None:
        if value is not None:
            raw = value.get_secret_value()
            if not 16 <= len(raw) <= 512 or any(ord(c) < 33 or ord(c) > 126 for c in raw):
                raise ValueError("invalid_service_key")
        return value

    @model_validator(mode="after")
    def complete_configuration(self) -> Self:
        if self.model_url is not None and (
            self.model_api_key is None or self.service_api_key is None
        ):
            raise ValueError("configured_planner_requires_model_and_service_keys")
        return self
