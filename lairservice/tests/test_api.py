import asyncio
import json
import time

from fastapi.testclient import TestClient

from lairservice.agent.compact import ContextCompactor
from lairservice.config import ensure_openlair_config, load_openlair_config, load_openlair_env
from lairservice.main import create_app
from lairservice.models.config import ProviderConfig, load_model_gateway_config
from lairservice.models.gateway import AgentModelRequest, AgentModelResponse, ScriptedAgentModelGateway, create_model_gateway_from_config
from lairservice.models.gateway import _resolve_api_key
from lairservice.runtime.langgraph_runtime import LangGraphAssistantRuntime


def make_client(tmp_path) -> TestClient:
    gateway = ScriptedAgentModelGateway(
        responses=[
            AgentModelResponse(
                content=[{"type": "text", "text": "[test-agent] 帮我背单词"}],
                stop_reason="end_turn",
                provider="test",
                model="scripted",
            )
        ]
    )
    return TestClient(create_app(database_url=f"sqlite+pysqlite:///{tmp_path}/lair-test.db", model_gateway=gateway))


def test_health(tmp_path) -> None:
    client = make_client(tmp_path)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_assistant_invoke_runs_agent_runtime(tmp_path) -> None:
    client = make_client(tmp_path)

    response = client.post(
        "/assistant/invoke",
        json={
            "message": "帮我背单词",
            "user_id": "u1",
            "session_id": "s1",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "message": "[test-agent] 帮我背单词",
        "session_id": "s1",
        "route": "agent",
    }


def test_notes_endpoint_returns_seeded_notes(tmp_path) -> None:
    client = make_client(tmp_path)

    response = client.get("/notes", params={"user_id": "u1"})

    assert response.status_code == 200
    notes = response.json()
    assert isinstance(notes, list)
    assert len(notes) == 5  # seed 演示数据（u1 → 演示用户 1）
    assert {"id", "content"} <= set(notes[0])


def test_model_config_loads_json_routes_and_provider(tmp_path) -> None:
    config_path = tmp_path / "models.json"
    config_path.write_text(
        json.dumps(
            {
                "default_route": "agent",
                "routes": {"agent": "main", "summary": "main"},
                "providers": {
                    "main": {
                        "kind": "openai_compatible",
                        "model": "glm-4-flash",
                        "base_url": "https://example.invalid/v1",
                        "api_key": "$LAIR_TEST_MODEL_KEY",
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    config = load_model_gateway_config(config_path)

    provider = config.provider_for_route("agent")
    assert provider.name == "main"
    assert provider.kind == "openai_compatible"
    assert provider.model == "glm-4-flash"
    assert provider.api_key == "$LAIR_TEST_MODEL_KEY"


def test_provider_api_key_supports_raw_and_env_reference(monkeypatch) -> None:
    raw = ProviderConfig(name="raw", kind="openai_compatible", model="m", api_key="sk-raw")
    env_ref = ProviderConfig(name="env-ref", kind="openai_compatible", model="m", api_key="$OPENLAIR_TEST_KEY")
    legacy_env = ProviderConfig(name="legacy", kind="openai_compatible", model="m", api_key_env="OPENLAIR_TEST_KEY")

    monkeypatch.setenv("OPENLAIR_TEST_KEY", "sk-env")

    assert _resolve_api_key(raw) == "sk-raw"
    assert _resolve_api_key(env_ref) == "sk-env"
    assert _resolve_api_key(legacy_env) == "sk-env"


def test_openlair_env_file_takes_priority_over_process_env(tmp_path, monkeypatch) -> None:
    config_path = tmp_path / ".openlair" / "openlair.json"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        json.dumps(
            {
                "model": {
                    "default_route": "agent",
                    "routes": {"agent": "main"},
                    "providers": {
                        "main": {
                            "kind": "openai_compatible",
                            "model": "m",
                            "base_url": "https://example.invalid/v1",
                            "api_key": "$OPENLAIR_TEST_KEY",
                        }
                    },
                }
            }
        ),
        encoding="utf-8",
    )
    (config_path.parent / ".env").write_text("OPENLAIR_TEST_KEY=sk-from-file\n", encoding="utf-8")
    monkeypatch.setenv("OPENLAIR_TEST_KEY", "sk-from-process")

    config = load_openlair_config(config_path)

    assert config.env["OPENLAIR_TEST_KEY"] == "sk-from-file"
    model_provider = create_model_gateway_from_config(config_path)._config.provider_for_route("agent")
    assert _resolve_api_key(model_provider, config.env) == "sk-from-file"


def test_model_gateway_creates_openlair_config_template(tmp_path) -> None:
    config_path = tmp_path / ".openlair" / "openlair.json"

    ensured_path = ensure_openlair_config(config_path)
    gateway = create_model_gateway_from_config(config_path)

    assert ensured_path == config_path
    assert config_path.exists()
    data = json.loads(config_path.read_text(encoding="utf-8"))
    assert data["model"]["routes"]["agent"] == "main"
    assert data["model"]["providers"]["main"]["kind"] == "openai_compatible"
    assert (config_path.parent / ".env").exists()
    assert gateway is not None


def test_openlair_config_exposes_model_section(tmp_path) -> None:
    config_path = tmp_path / "openlair.json"
    config_path.write_text(
        json.dumps(
            {
                "model": {
                    "default_route": "agent",
                    "routes": {"agent": "main"},
                    "providers": {
                        "main": {
                            "kind": "openai_compatible",
                            "model": "glm-4-flash",
                            "base_url": "https://example.invalid/v1",
                            "api_key_env": "OPENLAIR_TEST_KEY",
                        }
                    },
                }
            }
        ),
        encoding="utf-8",
    )

    config = load_openlair_config(config_path)

    assert config.path == config_path
    assert config.model["providers"]["main"]["model"] == "glm-4-flash"


def test_load_openlair_env_parses_quotes_and_comments(tmp_path) -> None:
    config_path = tmp_path / ".openlair" / "openlair.json"
    config_path.parent.mkdir(parents=True)
    (config_path.parent / ".env").write_text(
        "# comment\nOPENLAIR_A='one'\nOPENLAIR_B=\"two\"\nOPENLAIR_C=three\n",
        encoding="utf-8",
    )

    values = load_openlair_env(config_path)

    assert values == {"OPENLAIR_A": "one", "OPENLAIR_B": "two", "OPENLAIR_C": "three"}


def test_s01_agent_loop_stops_without_tool_use(tmp_path) -> None:
    gateway = ScriptedAgentModelGateway(
        responses=[
            AgentModelResponse(
                content=[{"type": "text", "text": "done"}],
                stop_reason="end_turn",
                provider="test",
                model="scripted",
            )
        ]
    )
    runtime = LangGraphAssistantRuntime(model_gateway=gateway, workspace_path=tmp_path)

    response = asyncio.run(runtime.invoke(message="hello", user_id="u1", session_id="s1"))

    assert response.message == "done"
    assert response.route == "agent"
    assert len(gateway.calls) == 1


def test_s02_tool_use_executes_and_loops_back(tmp_path) -> None:
    gateway = ScriptedAgentModelGateway(
        responses=[
            AgentModelResponse(
                content=[
                    {
                        "type": "tool_use",
                        "id": "tool-1",
                        "name": "write_file",
                        "input": {"path": "hello.txt", "content": "hello"},
                    }
                ],
                stop_reason="tool_use",
                provider="test",
                model="scripted",
            ),
            AgentModelResponse(
                content=[{"type": "text", "text": "wrote file"}],
                stop_reason="end_turn",
                provider="test",
                model="scripted",
            ),
        ]
    )
    runtime = LangGraphAssistantRuntime(model_gateway=gateway, workspace_path=tmp_path)

    response = asyncio.run(runtime.invoke(message="write hello", user_id="u1", session_id="s1"))

    assert response.message == "wrote file"
    assert (tmp_path / "hello.txt").read_text() == "hello"
    assert gateway.calls[1].messages[-1]["content"] == [
        {"type": "tool_result", "tool_use_id": "tool-1", "content": "Wrote 5 bytes to hello.txt"}
    ]


def test_s03_permission_blocks_destructive_tool(tmp_path) -> None:
    gateway = ScriptedAgentModelGateway(
        responses=[
            AgentModelResponse(
                content=[
                    {
                        "type": "tool_use",
                        "id": "tool-1",
                        "name": "bash",
                        "input": {"command": "rm important.txt"},
                    }
                ],
                stop_reason="tool_use",
                provider="test",
                model="scripted",
            ),
            AgentModelResponse(
                content=[{"type": "text", "text": "blocked safely"}],
                stop_reason="end_turn",
                provider="test",
                model="scripted",
            ),
        ]
    )
    runtime = LangGraphAssistantRuntime(model_gateway=gateway, workspace_path=tmp_path)

    response = asyncio.run(runtime.invoke(message="delete", user_id="u1", session_id="s1"))

    assert response.message == "blocked safely"
    assert gateway.calls[1].messages[-1]["content"][0]["content"] == "Permission denied: 'rm ' requires approval"


def test_s05_todo_write_updates_session_tasks(tmp_path) -> None:
    gateway = ScriptedAgentModelGateway(
        responses=[
            AgentModelResponse(
                content=[
                    {
                        "type": "tool_use",
                        "id": "tool-1",
                        "name": "todo_write",
                        "input": {"todos": [{"content": "plan", "status": "in_progress"}]},
                    }
                ],
                stop_reason="tool_use",
                provider="test",
                model="scripted",
            ),
            AgentModelResponse(
                content=[{"type": "text", "text": "planned"}],
                stop_reason="end_turn",
                provider="test",
                model="scripted",
            ),
        ]
    )
    runtime = LangGraphAssistantRuntime(model_gateway=gateway, workspace_path=tmp_path)

    response = asyncio.run(runtime.invoke(message="plan", user_id="u1", session_id="s1"))

    assert response.message == "planned"
    assert gateway.calls[1].messages[-1]["content"] == [
        {"type": "tool_result", "tool_use_id": "tool-1", "content": "Updated 1 tasks"}
    ]


def test_s06_subagent_uses_fresh_context_and_returns_summary(tmp_path) -> None:
    gateway = ScriptedAgentModelGateway(
        responses=[
            AgentModelResponse(
                content=[
                    {
                        "type": "tool_use",
                        "id": "tool-1",
                        "name": "task",
                        "input": {"description": "inspect isolated context"},
                    }
                ],
                stop_reason="tool_use",
                provider="test",
                model="scripted",
            ),
            AgentModelResponse(
                content=[{"type": "text", "text": "subagent summary"}],
                stop_reason="end_turn",
                provider="test",
                model="scripted",
            ),
            AgentModelResponse(
                content=[{"type": "text", "text": "parent done"}],
                stop_reason="end_turn",
                provider="test",
                model="scripted",
            ),
        ]
    )
    runtime = LangGraphAssistantRuntime(model_gateway=gateway, workspace_path=tmp_path)

    response = asyncio.run(runtime.invoke(message="delegate", user_id="u1", session_id="s1"))

    assert response.message == "parent done"
    assert gateway.calls[1].messages == [{"role": "user", "content": "inspect isolated context"}]
    assert gateway.calls[2].messages[-1]["content"] == [
        {"type": "tool_result", "tool_use_id": "tool-1", "content": "subagent summary"}
    ]


def test_s07_load_skill_injects_full_skill_content(tmp_path) -> None:
    skill_dir = tmp_path / "skills" / "code-review"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: code-review\ndescription: Review code carefully\n---\n\nFull review instructions",
        encoding="utf-8",
    )
    gateway = ScriptedAgentModelGateway(
        responses=[
            AgentModelResponse(
                content=[
                    {
                        "type": "tool_use",
                        "id": "tool-1",
                        "name": "load_skill",
                        "input": {"name": "code-review"},
                    }
                ],
                stop_reason="tool_use",
                provider="test",
                model="scripted",
            ),
            AgentModelResponse(
                content=[{"type": "text", "text": "skill loaded"}],
                stop_reason="end_turn",
                provider="test",
                model="scripted",
            ),
        ]
    )
    runtime = LangGraphAssistantRuntime(model_gateway=gateway, workspace_path=tmp_path)

    response = asyncio.run(runtime.invoke(message="review this", user_id="u1", session_id="s1"))

    assert response.message == "skill loaded"
    assert "code-review" in gateway.calls[0].system
    assert "Review code carefully" in gateway.calls[0].system
    assert "Full review instructions" in gateway.calls[1].messages[-1]["content"][0]["content"]


def test_s08_context_compactor_persists_large_tool_results(tmp_path) -> None:
    compactor = ContextCompactor(tmp_path, persist_threshold=10)
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": "big",
                    "content": "x" * 40,
                }
            ],
        }
    ]

    compacted = compactor.tool_result_budget(messages, max_bytes=20)

    content = compacted[-1]["content"][0]["content"]
    assert "<persisted-output>" in content
    assert (tmp_path / ".task_outputs" / "tool-results" / "big.txt").read_text() == "x" * 40


def test_s09_memory_extracts_remembered_user_fact(tmp_path) -> None:
    gateway = ScriptedAgentModelGateway(
        responses=[
            AgentModelResponse(
                content=[{"type": "text", "text": "remembered"}],
                stop_reason="end_turn",
                provider="test",
                model="scripted",
            )
        ]
    )
    runtime = LangGraphAssistantRuntime(model_gateway=gateway, workspace_path=tmp_path)

    response = asyncio.run(
        runtime.invoke(message="remember that I prefer concise Chinese replies", user_id="u1", session_id="s1")
    )

    assert response.message == "remembered"
    index = (tmp_path / ".memory" / "MEMORY.md").read_text(encoding="utf-8")
    assert "concise Chinese replies" in index


def test_s10_system_prompt_assembles_memory_and_tools(tmp_path) -> None:
    memory_dir = tmp_path / ".memory"
    memory_dir.mkdir()
    (memory_dir / "preference.md").write_text(
        "---\nname: preference\ndescription: User likes terse answers\ntype: user\n---\n\nKeep it terse.",
        encoding="utf-8",
    )
    gateway = ScriptedAgentModelGateway(
        responses=[
            AgentModelResponse(
                content=[{"type": "text", "text": "ok"}],
                stop_reason="end_turn",
                provider="test",
                model="scripted",
            )
        ]
    )
    runtime = LangGraphAssistantRuntime(model_gateway=gateway, workspace_path=tmp_path)

    response = asyncio.run(runtime.invoke(message="hello", user_id="u1", session_id="s1"))

    assert response.message == "ok"
    assert "Available tools:" in gateway.calls[0].system
    assert "todo_write" in gateway.calls[0].system
    assert "Memories available:" in gateway.calls[0].system
    assert "User likes terse answers" in gateway.calls[0].system


def test_s11_max_tokens_recovery_escalates_and_retries(tmp_path) -> None:
    gateway = ScriptedAgentModelGateway(
        responses=[
            AgentModelResponse(
                content=[{"type": "text", "text": "partial"}],
                stop_reason="max_tokens",
                provider="test",
                model="scripted",
            ),
            AgentModelResponse(
                content=[{"type": "text", "text": "completed after escalation"}],
                stop_reason="end_turn",
                provider="test",
                model="scripted",
            ),
        ]
    )
    runtime = LangGraphAssistantRuntime(model_gateway=gateway, workspace_path=tmp_path)

    response = asyncio.run(runtime.invoke(message="long answer", user_id="u1", session_id="s1"))

    assert response.message == "completed after escalation"
    assert gateway.calls[0].max_tokens == 8_000
    assert gateway.calls[1].max_tokens == 64_000


def test_s12_task_system_persists_dependencies_and_unlocks(tmp_path) -> None:
    gateway = ScriptedAgentModelGateway(
        responses=[
            AgentModelResponse(
                content=[
                    {
                        "type": "tool_use",
                        "id": "tool-1",
                        "name": "create_task",
                        "input": {"subject": "foundation", "description": "Build the first task"},
                    }
                ],
                stop_reason="tool_use",
                provider="test",
                model="scripted",
            ),
            AgentModelResponse(content=[{"type": "text", "text": "task created"}], stop_reason="end_turn", provider="test", model="scripted"),
        ]
    )
    runtime = LangGraphAssistantRuntime(model_gateway=gateway, workspace_path=tmp_path)

    response = asyncio.run(runtime.invoke(message="create a task", user_id="u1", session_id="s1"))

    assert response.message == "task created"
    task_result = json.loads(gateway.calls[1].messages[-1]["content"][0]["content"])
    task_id = task_result["id"]
    assert task_result["status"] == "pending"
    assert (tmp_path / ".tasks" / f"{task_id}.json").exists()

    child = json.loads(runtime._task_system.create_task("child", "Depends on foundation", [task_id]))
    blocked = runtime._task_system.claim_task(child["id"], "agent-a")
    assert f"blocked by {task_id}" in blocked

    completed = json.loads(runtime._task_system.complete_task(task_id))
    assert child["id"] in completed["unlocked"]


def test_s13_background_bash_returns_notification_on_next_model_call(tmp_path) -> None:
    gateway = ScriptedAgentModelGateway(
        responses=[
            AgentModelResponse(
                content=[
                    {
                        "type": "tool_use",
                        "id": "tool-1",
                        "name": "bash",
                        "input": {"command": "printf background-ready", "run_in_background": True},
                    }
                ],
                stop_reason="tool_use",
                provider="test",
                model="scripted",
            ),
            AgentModelResponse(content=[{"type": "text", "text": "background started"}], stop_reason="end_turn", provider="test", model="scripted"),
            AgentModelResponse(content=[{"type": "text", "text": "notification consumed"}], stop_reason="end_turn", provider="test", model="scripted"),
        ]
    )
    runtime = LangGraphAssistantRuntime(model_gateway=gateway, workspace_path=tmp_path)

    first = asyncio.run(runtime.invoke(message="run slow command", user_id="u1", session_id="s1"))
    for _ in range(20):
        if "completed" in runtime._background_tasks.list_tasks():
            break
        time.sleep(0.01)
    second = asyncio.run(runtime.invoke(message="continue", user_id="u1", session_id="s1"))

    assert first.message == "background started"
    assert "Started background task" in gateway.calls[1].messages[-1]["content"][0]["content"]
    assert second.message == "notification consumed"
    assert "<task_notification" in gateway.calls[2].messages[-1]["content"]
    assert "background-ready" in gateway.calls[2].messages[-1]["content"]


def test_s14_cron_scheduler_persists_and_validates_jobs(tmp_path) -> None:
    gateway = ScriptedAgentModelGateway(
        responses=[
            AgentModelResponse(
                content=[
                    {
                        "type": "tool_use",
                        "id": "tool-1",
                        "name": "schedule_cron",
                        "input": {"cron": "*/5 * * * *", "prompt": "review vocabulary", "durable": True},
                    }
                ],
                stop_reason="tool_use",
                provider="test",
                model="scripted",
            ),
            AgentModelResponse(content=[{"type": "text", "text": "scheduled"}], stop_reason="end_turn", provider="test", model="scripted"),
        ]
    )
    runtime = LangGraphAssistantRuntime(model_gateway=gateway, workspace_path=tmp_path)

    response = asyncio.run(runtime.invoke(message="schedule reminder", user_id="u1", session_id="s1"))

    assert response.message == "scheduled"
    job = json.loads(gateway.calls[1].messages[-1]["content"][0]["content"])
    assert job["prompt"] == "review vocabulary"
    assert job["durable"] is True
    assert (tmp_path / ".scheduled_tasks.json").exists()
    assert runtime._cron.schedule_cron("bad cron", "nope") == "Error: cron must have 5 fields"


def test_s19_mcp_plugin_connects_and_routes_prefixed_tools(tmp_path) -> None:
    gateway = ScriptedAgentModelGateway(
        responses=[
            AgentModelResponse(
                content=[
                    {
                        "type": "tool_use",
                        "id": "tool-1",
                        "name": "connect_mcp",
                        "input": {"name": "docs"},
                    }
                ],
                stop_reason="tool_use",
                provider="test",
                model="scripted",
            ),
            AgentModelResponse(
                content=[
                    {
                        "type": "tool_use",
                        "id": "tool-2",
                        "name": "mcp__docs__search",
                        "input": {"query": "agent loop"},
                    }
                ],
                stop_reason="tool_use",
                provider="test",
                model="scripted",
            ),
            AgentModelResponse(content=[{"type": "text", "text": "mcp done"}], stop_reason="end_turn", provider="test", model="scripted"),
        ]
    )
    runtime = LangGraphAssistantRuntime(model_gateway=gateway, workspace_path=tmp_path)

    response = asyncio.run(runtime.invoke(message="connect docs mcp", user_id="u1", session_id="s1"))

    assert response.message == "mcp done"
    assert "Connected MCP server docs" in gateway.calls[1].messages[-1]["content"][0]["content"]
    assert "mcp__docs__search" in [tool["name"] for tool in gateway.calls[1].tools]
    assert gateway.calls[2].messages[-1]["content"] == [
        {"type": "tool_result", "tool_use_id": "tool-2", "content": "Docs result for: agent loop"}
    ]
