"""AI 助手 runtime：LoopEngine 抽象协议。

runtime 只依赖本协议的抽象类型，不 import 任何具体 loop 框架（pydantic-ai / pi 等）。
换底层实现 = 提供一个新的 LoopEngine 实现，runtime 与路由零改动。
"""

from dataclasses import dataclass
from typing import AsyncIterator, Awaitable, Callable, Literal, Protocol, Type

# 工具执行函数：async (**kwargs) -> str（参数类型注解即 LLM 工具 schema 来源；
# 函数体通过 tools/ledger.py 的 contextvar 获取当前用户上下文，不依赖具体框架）。
ToolFn = Callable[..., Awaitable[str]]


@dataclass
class LoopMessage:
    """历史消息（与 DB 同构，与具体 loop 框架无关）。"""

    role: Literal["user", "assistant"]
    content: str


@dataclass
class LoopTool:
    """一个可被 LLM 调用的工具。"""

    name: str
    description: str
    fn: ToolFn


@dataclass
class LoopEvent:
    """loop 执行期间产出的事件（runtime 转换为对外事件）。"""

    kind: Literal["delta", "tool_start", "tool_end", "done"]
    text: str = ""
    tool_name: str = ""
    ok: bool = True
    output: dict | None = None  # done 事件携带结构化输出（output_schema 的实例 dict）


class LoopEngine(Protocol):
    """agent 推理循环引擎（实现方：pydantic-ai / 未来可换）。"""

    name: str

    async def stream(
        self,
        *,
        system_prompt: str,
        tools: list[LoopTool],
        history: list[LoopMessage],
        prompt: str,
        output_schema: Type | None = None,
    ) -> AsyncIterator[LoopEvent]:
        """流式执行一轮对话：LLM 推理 + 工具调用循环，产出增量事件。

        output_schema 非空时，LLM 必须以该 pydantic 模型的结构化结果结束
        （done 事件的 output 字段携带实例 dict）。
        """
        ...
