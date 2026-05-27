import asyncio

from fastapi.testclient import TestClient

from lairservice.config import load_openlair_config
from lairservice.main import create_app
from lairservice.models.config import parse_model_gateway_config
from lairservice.models.gateway import ModelRequest, create_model_gateway_from_config, _resolve_api_key


def test_real_model_config_has_key_available() -> None:
    config = load_openlair_config()
    model_config = parse_model_gateway_config(config.model, env=config.env)
    provider = model_config.provider_for_route("agent")

    assert provider.kind == "openai_compatible"
    assert provider.model
    assert provider.base_url
    assert _resolve_api_key(provider, model_config.env)


def test_real_model_gateway_complete_returns_expected_text() -> None:
    async def run() -> str:
        gateway = create_model_gateway_from_config(None)
        response = await gateway.complete(
            ModelRequest(
                message="What is 2 + 2? Reply with only the digit.",
                user_id="real-model-test",
                route="chat",
            )
        )
        return response.message.strip()

    assert asyncio.run(run()) == "4"


def test_real_model_assistant_invoke_uses_configured_gateway(tmp_path) -> None:
    client = TestClient(create_app(database_url=f"sqlite+pysqlite:///{tmp_path}/real-model.db"))

    response = client.post(
        "/assistant/invoke",
        json={
            "message": "What is 3 + 4? Reply with only the digit.",
            "user_id": "real-model-test",
            "session_id": "real-model-session",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["session_id"] == "real-model-session"
    assert payload["route"] == "agent"
    assert payload["message"].strip() == "7"
