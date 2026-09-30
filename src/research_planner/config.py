"""Operator-only provider configuration and explicit endpoint migration."""

from typing import Annotated, Literal, Self

from pydantic import Field, SecretStr, StringConstraints, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from research_planner.endpoints import ModelEndpoint, ModelProvider, internal_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="RESEARCH_PLANNER_", extra="forbid", hide_input_in_errors=True
    )

    model_provider: ModelProvider = "internal"
    model_base_url: str | None = None
    model_url: str | None = None  # Deprecated internal origin, without /v1.
    model_api_key: SecretStr | None = None
    service_api_key: SecretStr | None = None
    model: Annotated[
        str, StringConstraints(min_length=1, max_length=160, pattern=r"^[\w./:-]+$")
    ] = "Qwen/Qwen3-4B-Instruct-2507"
    timeout_seconds: float = Field(default=8, ge=0.1, le=30, allow_inf_nan=False)
    max_tokens: int = Field(default=1200, ge=256, le=2048)
    output_mode: Literal["json_schema", "json_object"] = "json_schema"
    max_concurrent_requests: int = Field(default=2, ge=1, le=8)

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
        if self.model_url is not None:
            if self.model_provider != "internal" or self.model_base_url is not None:
                raise ValueError("legacy_model_url_requires_internal_and_no_base_url")
            self.model_url = internal_url(self.model_url, legacy=True)
            self.model_base_url = self.model_url + "/v1"
        if self.model_base_url is not None:
            self.model_base_url = ModelEndpoint(self.model_provider, self.model_base_url).base_url
        if self.model_base_url is not None and (
            self.model_api_key is None or self.service_api_key is None
        ):
            raise ValueError("configured_planner_requires_model_and_service_keys")
        return self

    @property
    def endpoint(self) -> ModelEndpoint:
        if self.model_base_url is None:
            raise ValueError("model_configuration_required")
        return ModelEndpoint(self.model_provider, self.model_base_url)
