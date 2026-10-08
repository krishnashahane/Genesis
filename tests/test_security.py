from fastapi.testclient import TestClient

from genesis.api.app import create_app
from genesis.config import Settings
from genesis.core.runtime import Runtime


def test_production_requires_api_key():
    settings = Settings(env="production", api_key="", llm_provider="mock")
    runtime = Runtime(settings)
    try:
        create_app(runtime=runtime)
    except RuntimeError as exc:
        assert "GENESIS_API_KEY" in str(exc)
    else:
        raise AssertionError("production app must require GENESIS_API_KEY")


def test_production_api_auth_and_rate_limit():
    settings = Settings(
        env="production",
        api_key="secret",
        rate_limit_per_minute=1,
        llm_provider="mock",
    )
    runtime = Runtime(settings)
    app = create_app(runtime=runtime)

    with TestClient(app) as client:
        assert client.get("/api/health").status_code == 200
        assert client.get("/api/agents").status_code == 401

        headers = {"X-Genesis-API-Key": "secret"}
        assert client.get("/api/agents", headers=headers).status_code == 200
        assert client.get("/api/agents", headers=headers).status_code == 429
