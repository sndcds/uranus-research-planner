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


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:8091/v1",
        "http://[::1]:8091/v1/",
        "https://10.0.0.1:8091/v1",
        "https://172.16.0.1:443/v1",
        "https://192.168.1.1:443/v1",
        "https://[fd00::1]:443/v1",
    ],
)
def test_internal_api_base_urls(url):
    settings = Settings(
        model_base_url=url, service_api_key=SecretStr(KEY), model_api_key=SecretStr(MODEL_KEY)
    )
    assert settings.model_provider == "internal"
    assert settings.model_base_url == url.rstrip("/")
    assert settings.endpoint.models_url == url.rstrip("/") + "/models"


@pytest.mark.parametrize(
    "url",
    [
        "https://8.8.8.8:443/v1",
        "https://api.groq.com:443/v1",
        "http://localhost:8091/v1",
        "http://127.0.0.1/v1",
        "http://127.0.0.1:0/v1",
        "http://127.0.0.1:65536/v1",
        "http://127.0.0.1:abc/v1",
        "http://127.0.0.1:8091/v1?x=1",
        "http://127.0.0.1:8091/v1?",
        "http://127.0.0.1:8091/v1#fragment",
        "http://127.0.0.1:8091/v1#",
        "http://user:password@127.0.0.1:8091/v1",
        "http://@127.0.0.1:8091/v1",
        "ftp://127.0.0.1:8091/v1",
        "http://10.0.0.1:8091/v1",
        "http://169.254.169.254:80/v1",
        "https://100.64.0.1:443/v1",
        "http://0.0.0.0:8091/v1",
        "http://[::ffff:127.0.0.1]:8091/v1",
        "https://[fe80::1%25eth0]:443/v1",
        "http://127.0.0.1:8091",
        "http://127.0.0.1:8091/openai/v1",
        "http://127.0.0.1:8091/x/../v1",
        "http://127.0.0.1:8091/%76%31",
        "http://127.0.0.1:8091/v1//",
        "http://127.0.0.1:8091/v1\n",
        " http://127.0.0.1:8091/v1",
        "http://127.0.0.1:8091\\v1",
        "http://[::1:8091/v1",
        "not a URL",
        "",
    ],
)
def test_reject_unsafe_internal_api_base_urls(url):
    with pytest.raises(ValidationError):
        Settings(
            model_base_url=url, service_api_key=SecretStr(KEY), model_api_key=SecretStr(MODEL_KEY)
        )


@pytest.mark.parametrize("model", ["openai/gpt-oss-20b", "openai/gpt-oss-120b", "another-model"])
def test_groq_exact_base_url_with_configurable_model(model):
    settings = Settings(
        model_provider="groq",
        model_base_url="https://api.groq.com/openai/v1",
        model=model,
        service_api_key=SecretStr(KEY),
        model_api_key=SecretStr(MODEL_KEY),
    )
    assert settings.model == model
    assert settings.endpoint.models_url == "https://api.groq.com/openai/v1/models"
    assert settings.endpoint.completion_url == "https://api.groq.com/openai/v1/chat/completions"


@pytest.mark.parametrize(
    "url",
    [
        "http://api.groq.com/openai/v1",
        "https://evil.example/openai/v1",
        "https://api.groq.com.evil.example/openai/v1",
        "https://api.groq.com@evil.example/openai/v1",
        "https://evil.example@api.groq.com/openai/v1",
        "https://user:password@api.groq.com/openai/v1",
        "https://api.groq.com:8443/openai/v1",
        "https://api.groq.com:443/openai/v1",
        "https://api.groq.com/openai/v1?x=1",
        "https://api.groq.com/openai/v1?",
        "https://api.groq.com/openai/v1#fragment",
        "https://api.groq.com/openai/v1#",
        "https://api.groq.com/openai/v1/",
        "https://api.groq.com/v1",
        "https://api.groq.com/openai/v1/chat/completions",
        "https://api.groq.com/openai//v1",
        "https://api.groq.com/x/../openai/v1",
        "https://api.groq.com/openai/%76%31",
        "https://api.groq.com./openai/v1",
        "https://API.GROQ.COM/openai/v1",
        "https://api.groq.com\\@evil.example/openai/v1",
        "https://127.0.0.1:443/openai/v1",
        "https://api.groq.com/openai/v1\n",
        " https://api.groq.com/openai/v1",
        "",
        "not a URL",
    ],
)
def test_reject_noncanonical_groq_base_urls(url):
    with pytest.raises(ValidationError):
        Settings(
            model_provider="groq",
            model_base_url=url,
            service_api_key=SecretStr(KEY),
            model_api_key=SecretStr(MODEL_KEY),
        )


@pytest.mark.parametrize(
    "changes",
    [
        {"model_provider": "auto"},
        {"model_provider": "openai"},
        {"model_base_url": "http://127.0.0.1:8091/v1"},
        {"model_provider": "groq", "model_url": "http://127.0.0.1:8091"},
        {"model_provider": "groq", "model_url": "https://api.groq.com/openai/v1"},
        {"model_url": "http://127.0.0.1:8091", "model_base_url": "http://127.0.0.1:8091/v1"},
    ],
)
def test_no_provider_inference_or_ambiguous_legacy_config(changes):
    with pytest.raises(ValidationError):
        Settings(**changes)


@pytest.mark.parametrize("legacy", [False, True])
def test_environment_configuration_and_legacy_migration(monkeypatch, legacy):
    monkeypatch.setenv("RESEARCH_PLANNER_MODEL_PROVIDER", "internal")
    monkeypatch.setenv("RESEARCH_PLANNER_SERVICE_API_KEY", KEY)
    monkeypatch.setenv("RESEARCH_PLANNER_MODEL_API_KEY", MODEL_KEY)
    monkeypatch.delenv("RESEARCH_PLANNER_MODEL_URL", raising=False)
    monkeypatch.delenv("RESEARCH_PLANNER_MODEL_BASE_URL", raising=False)
    name = "RESEARCH_PLANNER_MODEL_URL" if legacy else "RESEARCH_PLANNER_MODEL_BASE_URL"
    monkeypatch.setenv(name, "http://127.0.0.1:8091" + ("" if legacy else "/v1"))
    assert Settings().endpoint.base_url == "http://127.0.0.1:8091/v1"


def test_configuration_errors_hide_raw_keys():
    with pytest.raises(ValidationError) as error:
        Settings(model_provider="unknown", model_api_key=MODEL_KEY, service_api_key=KEY)
    assert MODEL_KEY not in str(error.value)
    assert KEY not in str(error.value)


def test_groq_environment_configuration_is_explicit(monkeypatch):
    monkeypatch.delenv("RESEARCH_PLANNER_MODEL_URL", raising=False)
    for suffix, value in {
        "MODEL_PROVIDER": "groq",
        "MODEL_BASE_URL": "https://api.groq.com/openai/v1",
        "MODEL": "openai/gpt-oss-20b",
        "MODEL_API_KEY": MODEL_KEY,
        "SERVICE_API_KEY": KEY,
    }.items():
        monkeypatch.setenv("RESEARCH_PLANNER_" + suffix, value)
    settings = Settings()
    assert settings.endpoint.base_url == "https://api.groq.com/openai/v1"
    assert settings.model == "openai/gpt-oss-20b"
    monkeypatch.setenv("RESEARCH_PLANNER_MODEL_URL", "http://127.0.0.1:8091")
    with pytest.raises(ValidationError, match="legacy_model_url_requires_internal_and_no_base_url"):
        Settings()


def test_internal_configuration_does_not_resolve_dns(monkeypatch):
    import socket

    def forbidden(*args, **kwargs):
        pytest.fail("Internal endpoint configuration must not resolve DNS")

    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    settings = Settings(
        model_base_url="https://10.0.0.1:8091/v1",
        service_api_key=KEY,
        model_api_key=MODEL_KEY,
    )
    assert settings.endpoint.base_url == "https://10.0.0.1:8091/v1"
