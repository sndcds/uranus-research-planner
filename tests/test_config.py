import pytest
from pydantic import SecretStr, ValidationError

from research_planner.config import Settings
from tests.conftest import KEY, MODEL_KEY


@pytest.mark.parametrize(
    "url",
    [
        "https://api.openai.com:443",
        "http://example.com:80",
        "file:///etc/passwd",
        "http://169.254.169.254:80",
        "http://100.64.0.1:80",
        "http://0.0.0.0:80",
        "http://127.0.0.1:8091/v1",
        "http://127.0.0.1:8091?q=secret",
        "http://127.0.0.1:8091#x",
        "http://user:password@127.0.0.1:8091",
        "http://127.0.0.1",
        "http://127.0.0.1:0",
        "http://localhost:8091",
        "http://10.0.0.1:8091",
        "http://[::ffff:127.0.0.1]:8091",
        "https://[fe80::1%25eth0]:8091",
        "http://[::]:8091",
        "http://127.0.0.1:8091\n",
        " http://127.0.0.1:8091",
    ],
)
def test_reject_public_dynamic_or_credential_origins(url):
    with pytest.raises(ValidationError):
        Settings(model_url=url, service_api_key=SecretStr(KEY), model_api_key=SecretStr(MODEL_KEY))


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:8091",
        "http://[::1]:8091/",
        "https://10.0.0.1:8091",
        "https://192.168.1.1:443",
        "https://[fd00::1]:443",
    ],
)
def test_explicit_internal_origins(url):
    settings = Settings(
        model_url=url, service_api_key=SecretStr(KEY), model_api_key=SecretStr(MODEL_KEY)
    )
    assert settings.model_url == url.rstrip("/")
    assert KEY not in repr(settings)
    assert MODEL_KEY not in repr(settings)


@pytest.mark.parametrize(
    "changes",
    [
        {"model_url": "http://127.0.0.1:8091"},
        {"timeout_seconds": float("nan")},
        {"timeout_seconds": float("inf")},
        {"timeout_seconds": 31},
        {"max_tokens": 99999},
        {"service_api_key": "short"},
        {"service_api_key": "x" * 16 + "\n"},
        {"model": "secret\nlog injection"},
        {"output_mode": "auto"},
    ],
)
def test_configuration_fails_closed(changes):
    with pytest.raises(ValidationError):
        Settings(**changes)
