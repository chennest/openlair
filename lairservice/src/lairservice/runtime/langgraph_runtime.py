import operator
from pathlib import Path
from typing import Annotated, Any, NotRequired, TypedDict

from langgraph.graph import END, START, StateGraph

from lairservice.agent.compact import ContextCompactor
from lairservice.agent.background import BackgroundTaskManager
from lairservice.agent.cron import CronScheduler
from lairservice.agent.hooks import HookRegistry, large_output_hook
from lairservice.agent.memory import MemoryStore
from lairservice.agent.mcp import MCPPluginManager
from lairservice.agent.permissions import PermissionPolicy, permission_hook
from lairservice.agent.prompts import SystemPromptBuilder
from lairservice.agent.recovery import AgentRecovery, RecoveryState
from lairservice.agent.skills import SkillRegistry
from lairservice.agent.task_system import TaskSystem
from lairservice.agent.tools import ToolDefinition, ToolRegistry, WorkspaceTools, create_workspace_tool_registry
from lairservice.models.gateway import AgentModelRequest, ModelGateway
from lairservice.runtime.base import AssistantResponse


class RuntimeMessage(TypedDict):
    role: str
    content: Any


class RuntimeTrace(TypedDict):
    event: str
    detail: str


class AssistantState(TypedDict):
    messages: Annotated[list[RuntimeMessage], operator.add]
    traces: Annotated[list[RuntimeTrace], operator.add]
    user_id: str
    session_id: str
    rounds_since_todo: int
    iteration_count: int
    final_message: NotRequired[str]
    stop_reason: NotRequired[str]


class LangGraphAssistantRuntime:
    def __init__(
        self,
        model_gateway: ModelGateway,
        tool_registry: ToolRegistry | None = None,
        workspace_path: Path | str = ".",
        hook_registry: HookRegistry | None = None,
        max_iterations: int = 50,
        subagent_max_iterations: int = 30,
    ) -> None:
        self._model_gateway = model_gateway
        self._workspace_path = Path(workspace_path).resolve()
        self._workspace_tools = WorkspaceTools(workspace_path)
        self._tool_registry = tool_registry or create_workspace_tool_registry(self._workspace_tools)
        self._skills = SkillRegistry(self._workspace_path / "skills")
        self._memory = MemoryStore(self._workspace_path / ".memory")
        self._compactor = ContextCompactor(self._workspace_path)
        self._task_system = TaskSystem(self._workspace_path)
        self._background_tasks = BackgroundTaskManager()
        self._cron = CronScheduler(self._workspace_path)
        self._mcp = MCPPluginManager()
        self._prompt_builder = SystemPromptBuilder(
            workspace=str(self._workspace_path),
            tools=self._tool_registry,
            skills=self._skills,
            memory=self._memory,
        )
        self._recovery = AgentRecovery(self._compactor)
        self._register_harness_tools()
        self._tool_registry.register_dynamic_provider(self._mcp.assemble_tool_pool)
        self._hook_registry = hook_registry or HookRegistry()
        self._permission_policy = PermissionPolicy(workspace_path)
        self._hook_registry.register("PreToolUse", permission_hook(self._permission_policy))
        self._hook_registry.register("PostToolUse", large_output_hook)
        self._max_iterations = max_iterations
        self._subagent_max_iterations = subagent_max_iterations
        self._graph = self._build_graph()

    def _build_graph(self):
        graph = StateGraph(AssistantState)
        graph.add_node("model", self._model_node)
        graph.add_node("tools", self._tools_node)
        graph.add_edge(START, "model")
        graph.add_conditional_edges(
            "model",
            self._next_step,
            {
                "tools": "tools",
                "end": END,
            },
        )
        graph.add_edge("tools", "model")
        return graph.compile()

    async def _model_node(self, state: AssistantState) -> dict[str, object]:
        messages = self._compactor.compact_before_model(self._with_todo_reminder(state))
        background_notifications = self._background_tasks.collect_notifications()
        if background_notifications:
            messages.append({"role": "user", "content": "\n".join(background_notifications)})
        relevant_memories = self._memory.load_relevant(messages)
        recovery_state = RecoveryState()

        while True:
            try:
                response = await self._recovery.call_with_retry(
                    lambda: self._model_gateway.create_agent_response(
                        AgentModelRequest(
                            messages=messages,
                            tools=self._tool_definitions(include_task=True),
                            system=self._system_prompt(relevant_memories=relevant_memories),
                            user_id=state["user_id"],
                            session_id=state["session_id"],
                            max_tokens=recovery_state.max_tokens,
                        )
                    )
                )
            except Exception as error:
                recovered = self._recovery.recover_error(
                    error=error,
                    messages=messages,
                    recovery_state=recovery_state,
                )
                if recovered is None:
                    raise
                messages = recovered
                continue

            if response.stop_reason == "max_tokens":
                recovered = self._recovery.recover_max_tokens(
                    messages=messages,
                    response_content=response.content,
                    recovery_state=recovery_state,
                )
                if recovered is not None:
                    messages = recovered
                    continue

            break

        final_message = self._extract_text(response.content)
        return {
            "messages": [{"role": "assistant", "content": response.content}],
            "traces": [{"event": "model", "detail": response.stop_reason}],
            "stop_reason": response.stop_reason,
            "final_message": final_message,
            "iteration_count": state["iteration_count"] + 1,
            "rounds_since_todo": state["rounds_since_todo"],
        }

    async def _tools_node(self, state: AssistantState) -> dict[str, object]:
        results: list[dict[str, str]] = []
        traces: list[RuntimeTrace] = []
        rounds_since_todo = state["rounds_since_todo"] + 1

        for tool_call in self._tool_calls(state):
            blocked = self._hook_registry.trigger("PreToolUse", tool_call)
            if blocked is not None:
                output = blocked
                traces.append({"event": "tool_blocked", "detail": tool_call["name"]})
            elif tool_call["name"] == "task":
                output = await self._spawn_subagent(
                    description=str(tool_call["input"].get("description", "")),
                    parent_state=state,
                )
                traces.append({"event": "subagent", "detail": tool_call["id"]})
            elif self._background_tasks.should_run_background(tool_call["name"], tool_call["input"]):
                tool_name = tool_call["name"]
                arguments = dict(tool_call["input"])
                arguments.pop("run_in_background", None)
                background_id = self._background_tasks.start(
                    name=tool_name,
                    run=lambda tool_name=tool_name, arguments=arguments: self._tool_registry.execute(tool_name, arguments),
                )
                output = f"Started background task {background_id} for {tool_name}"
                traces.append({"event": "background_task", "detail": background_id})
            else:
                arguments = dict(tool_call["input"])
                arguments.pop("run_in_background", None)
                output = self._tool_registry.execute(tool_call["name"], arguments)
                traces.append({"event": "tool", "detail": tool_call["name"]})

            self._hook_registry.trigger("PostToolUse", tool_call, output)
            if tool_call["name"] == "todo_write":
                rounds_since_todo = 0
            results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": tool_call["id"],
                    "content": output,
                }
            )

        return {
            "messages": [{"role": "user", "content": results}],
            "traces": traces,
            "rounds_since_todo": rounds_since_todo,
        }

    def _next_step(self, state: AssistantState) -> str:
        if state["iteration_count"] >= self._max_iterations:
            return "end"
        if state.get("stop_reason") != "tool_use":
            self._hook_registry.trigger("Stop", state["messages"])
            self._memory.extract_from_messages([dict(message) for message in state["messages"]])
            return "end"
        return "tools"

    async def invoke(self, *, message: str, user_id: str, session_id: str) -> AssistantResponse:
        self._hook_registry.trigger("UserPromptSubmit", message)
        state: AssistantState = {
            "messages": [{"role": "user", "content": message}],
            "traces": [],
            "user_id": user_id,
            "session_id": session_id,
            "rounds_since_todo": 0,
            "iteration_count": 0,
        }
        result = await self._graph.ainvoke(
            state,
            config={"configurable": {"thread_id": f"{user_id}:{session_id}"}},
        )
        assistant_message = result.get("final_message") or self._extract_text(result["messages"][-1]["content"])
        return AssistantResponse(
            message=assistant_message,
            session_id=session_id,
            route="agent",
        )

    def _tool_definitions(self, *, include_task: bool) -> list[dict[str, Any]]:
        definitions = self._tool_registry.definitions()
        if include_task:
            definitions.append(
                ToolDefinition(
                    name="task",
                    description="Launch an isolated subagent for a complex subtask. Returns only the final summary.",
                    input_schema={
                        "type": "object",
                        "properties": {"description": {"type": "string"}},
                        "required": ["description"],
                    },
                ).as_model_tool()
            )
        return definitions

    def _tool_calls(self, state: AssistantState) -> list[dict[str, Any]]:
        content = state["messages"][-1]["content"]
        if not isinstance(content, list):
            return []

        calls: list[dict[str, Any]] = []
        for block in content:
            if not isinstance(block, dict) or block.get("type") != "tool_use":
                continue
            tool_input = block.get("input", {})
            calls.append(
                {
                    "id": str(block.get("id", f"tool-{len(calls) + 1}")),
                    "name": str(block.get("name", "")),
                    "input": tool_input if isinstance(tool_input, dict) else {},
                }
            )
        return calls

    def _with_todo_reminder(self, state: AssistantState) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = [dict(message) for message in state["messages"]]
        if state["rounds_since_todo"] >= 3:
            messages.append({"role": "user", "content": "<reminder>Update your todos.</reminder>"})
        return messages

    def _system_prompt(self, *, relevant_memories: str = "") -> str:
        return self._prompt_builder.build(
            {
                "memory_index": self._memory.index(),
                "relevant_memories": relevant_memories,
                "tools": [tool["name"] for tool in self._tool_registry.definitions()],
            }
        )

    async def _spawn_subagent(self, *, description: str, parent_state: AssistantState) -> str:
        messages: list[dict[str, Any]] = [{"role": "user", "content": description}]

        for _ in range(self._subagent_max_iterations):
            response = await self._model_gateway.create_agent_response(
                AgentModelRequest(
                    messages=messages,
                    tools=self._tool_definitions(include_task=False),
                    system="Complete the task you were given, then return a concise summary. Do not delegate further.",
                    user_id=parent_state["user_id"],
                    session_id=f"{parent_state['session_id']}:subagent",
                )
            )
            messages.append({"role": "assistant", "content": response.content})
            if response.stop_reason != "tool_use":
                return self._extract_text(response.content) or "Subagent completed without text output."

            results = []
            for tool_call in self._tool_calls_from_content(response.content):
                blocked = self._hook_registry.trigger("PreToolUse", tool_call)
                arguments = dict(tool_call["input"])
                arguments.pop("run_in_background", None)
                output = blocked if blocked is not None else self._tool_registry.execute(tool_call["name"], arguments)
                self._hook_registry.trigger("PostToolUse", tool_call, output)
                results.append({"type": "tool_result", "tool_use_id": tool_call["id"], "content": output})
            messages.append({"role": "user", "content": results})

        return "Subagent stopped after reaching the safety limit."

    def _tool_calls_from_content(self, content: list[dict[str, Any]]) -> list[dict[str, Any]]:
        calls: list[dict[str, Any]] = []
        for block in content:
            if block.get("type") != "tool_use":
                continue
            tool_input = block.get("input", {})
            calls.append(
                {
                    "id": str(block.get("id", f"tool-{len(calls) + 1}")),
                    "name": str(block.get("name", "")),
                    "input": tool_input if isinstance(tool_input, dict) else {},
                }
            )
        return calls

    def _extract_text(self, content: Any) -> str:
        if isinstance(content, str):
            return content
        if not isinstance(content, list):
            return str(content)

        texts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                texts.append(str(block.get("text", "")))
        return "\n".join(text for text in texts if text)

    def _register_harness_tools(self) -> None:
        self._tool_registry.register(
            ToolDefinition(
                name="load_skill",
                description="Load the full content of a skill by name.",
                input_schema={
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                    "required": ["name"],
                },
            ),
            self._skills.load,
        )
        self._tool_registry.register(
            ToolDefinition(
                name="compact",
                description="Request conversation compaction before continuing.",
                input_schema={"type": "object", "properties": {"focus": {"type": "string"}}},
            ),
            self._compact_tool,
        )
        self._register_task_system_tools()
        self._register_background_tools()
        self._register_cron_tools()
        self._register_mcp_tools()

    def _compact_tool(self, focus: str = "") -> str:
        return f"Compaction requested. Focus: {focus}" if focus else "Compaction requested."

    def _register_task_system_tools(self) -> None:
        self._tool_registry.register(
            ToolDefinition(
                name="create_task",
                description="Create a persistent harness task with optional dependency task IDs.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "subject": {"type": "string"},
                        "description": {"type": "string"},
                        "blockedBy": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["subject", "description"],
                },
            ),
            self._task_system.create_task,
        )
        self._tool_registry.register(
            ToolDefinition(
                name="list_tasks",
                description="List persistent harness tasks.",
                input_schema={"type": "object", "properties": {}},
            ),
            self._task_system.list_tasks,
        )
        self._tool_registry.register(
            ToolDefinition(
                name="get_task",
                description="Get one persistent harness task by ID.",
                input_schema={"type": "object", "properties": {"task_id": {"type": "string"}}, "required": ["task_id"]},
            ),
            self._task_system.get_task,
        )
        self._tool_registry.register(
            ToolDefinition(
                name="claim_task",
                description="Claim a pending harness task when dependencies are complete.",
                input_schema={
                    "type": "object",
                    "properties": {"task_id": {"type": "string"}, "owner": {"type": "string"}},
                    "required": ["task_id", "owner"],
                },
            ),
            self._task_system.claim_task,
        )
        self._tool_registry.register(
            ToolDefinition(
                name="complete_task",
                description="Complete a harness task and report any newly unblocked tasks.",
                input_schema={"type": "object", "properties": {"task_id": {"type": "string"}}, "required": ["task_id"]},
            ),
            self._task_system.complete_task,
        )

    def _register_background_tools(self) -> None:
        self._tool_registry.register(
            ToolDefinition(
                name="list_background_tasks",
                description="List background tasks started by the harness.",
                input_schema={"type": "object", "properties": {}},
            ),
            self._background_tasks.list_tasks,
        )

    def _register_cron_tools(self) -> None:
        self._tool_registry.register(
            ToolDefinition(
                name="schedule_cron",
                description="Schedule a prompt with a five-field cron expression.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "cron": {"type": "string"},
                        "prompt": {"type": "string"},
                        "recurring": {"type": "boolean"},
                        "durable": {"type": "boolean"},
                    },
                    "required": ["cron", "prompt"],
                },
            ),
            self._cron.schedule_cron,
        )
        self._tool_registry.register(
            ToolDefinition(
                name="list_crons",
                description="List scheduled cron prompts.",
                input_schema={"type": "object", "properties": {}},
            ),
            self._cron.list_crons,
        )
        self._tool_registry.register(
            ToolDefinition(
                name="cancel_cron",
                description="Cancel a scheduled cron prompt by ID.",
                input_schema={"type": "object", "properties": {"job_id": {"type": "string"}}, "required": ["job_id"]},
            ),
            self._cron.cancel_cron,
        )

    def _register_mcp_tools(self) -> None:
        self._tool_registry.register(
            ToolDefinition(
                name="connect_mcp",
                description="Connect to a mock MCP server (docs, deploy) and discover prefixed external tools.",
                input_schema={"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]},
            ),
            self._mcp.connect_mcp,
        )
