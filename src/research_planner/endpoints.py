"""Explicit provider policy; no arbitrary public endpoints or provider autodetection."""

from dataclasses import dataclass
from ipaddress import ip_address, ip_network
from typing import Literal
from urllib.parse import urlsplit

import httpx

ModelProvider = Literal["internal", "groq", "openai"]
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
OPENAI_BASE_URL = "https://api.openai.com/v1"
INTERNAL_NETWORKS = tuple(
    ip_network(n)
    for n in ("127.0.0.0/8", "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "::1/128", "fc00::/7")
)


def internal_url(value: str, *, legacy: bool = False) -> str:
    """Validate before URL normalization can hide credentials, escapes or delimiters."""
    if any(ord(c) <= 32 or ord(c) >= 127 for c in value) or any(c in value for c in "%?#\\"):
        raise ValueError("invalid_internal_model_url")
    try:
        url = urlsplit(value)
        address = ip_address(url.hostname or "")
        valid = (
            url.scheme in {"http", "https"}
            and url.path in ({"", "/"} if legacy else {"/v1", "/v1/"})
            and url.username is None
            and url.password is None
            and url.port is not None
            and 1 <= url.port <= 65535
            and any(address in network for network in INTERNAL_NETWORKS)
            and (url.scheme == "https" or address.is_loopback)
        )
    except ValueError:
        valid = False
    if not valid:
        raise ValueError("model_url_must_be_numeric_internal_with_explicit_port_and_expected_path")
    return value.rstrip("/")


@dataclass(frozen=True)
class ModelEndpoint:
    provider: ModelProvider
    base_url: str

    def __post_init__(self) -> None:
        if self.provider == "internal":
            canonical = internal_url(self.base_url)
        elif self.provider == "groq":
            # Exact string allowlist, before any parser can normalize an unsafe variant.
            if self.base_url != GROQ_BASE_URL:
                raise ValueError("groq_requires_canonical_api_base_url")
            canonical = GROQ_BASE_URL
        elif self.provider == "openai":
            if self.base_url != OPENAI_BASE_URL:
                raise ValueError("openai_requires_canonical_api_base_url")
            canonical = OPENAI_BASE_URL
        else:
            raise ValueError("unsupported_model_provider")
        object.__setattr__(self, "base_url", canonical)

    @property
    def models_url(self) -> str:
        return self.base_url + "/models"

    @property
    def completion_url(self) -> str:
        return self.base_url + "/chat/completions"

    def allows(self, method: str, url: httpx.URL) -> bool:
        # Full URL equality includes the raw path, query, userinfo and fragment.
        return (method, url) in {
            ("GET", httpx.URL(self.models_url)),
            ("POST", httpx.URL(self.completion_url)),
        }

    def completion_options(self, model: str) -> dict[str, object]:
        # Groq GPT-OSS defaults to a separate reasoning field, forbidden by our
        # response boundary. Suppress it at generation; never strip it afterwards.
        # Other models stay configurable and need their own operator acceptance.
        if self.provider == "groq" and model in {"openai/gpt-oss-20b", "openai/gpt-oss-120b"}:
            return {"include_reasoning": False}
        return {}
