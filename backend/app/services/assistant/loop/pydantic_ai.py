"""AI 助手 runtime：Pydantic AI 的 LoopEngine 实现。

OpenAI 兼容多 provider：base_url / api_key / model 全部来自后端配置（LLM_BASE_URL 等），
密钥只进 backend/.env，不落任何框架配置文件。

结构化输出说明：不用 pydantic-ai 的 output_type（它用 tool_choice=required + 内置 output
工具实现，与 deepseek 的 thinking 模式冲突 400）。改为「纯文本 JSON 输出 + 鲁棒解析」：
- system prompt 末尾附加 JSON 输出指令；
- 流结束后从文本中提取 JSON（容错 ```json 块/内嵌），用 output_schema 校验。
"""

import json
import re
from typing import AsyncIterator

from app.services.assistant.loop.base import LoopEvent, LoopMessage, LoopTool

_JSON_OUTPUT_INSTRUCTION = """

【输出格式要求】最后一条回复必须以纯 JSON 对象结尾（不要 markdown 代码块、不要多余说明）：
{"action": "record" 或 "skip", "type": "支出" 或 "收入", "amount": 金额数字, "category": "分类名", "date": "今天/昨天/YYYY-MM-DD", "book": "账本名", "note": "备注"}
- 用户要求记账：action=record，amount 必填（正数），其余字段可空；账本/分类从 system prompt 的「可用列表」中选择名称。
- 非记账请求（闲聊/查询）：action=skip，其余字段省略。
- JSON 前的自然语言请简短；JSON 必须是回复的最后一个内容。"""


def _extract_json(text: str) -> dict | None:
    """从回复文本中鲁棒提取 JSON 对象。"""
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    if m:
        try:
            return json.loads(m.group(1))
        except ValueError:
            pass
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except ValueError:
            pass
    return None


_MARKER = '{"action"'


async def _stream_filtered(streamed, raw_out: list[str]):
    """转发 delta，但截断从 `{"action"` 开始的 JSON 段（模型偶尔把 JSON 混进自然语言）。

    完整文本同时收集进 raw_out（JSON 提取用）；转发文本剔除 JSON 段（用户可见）。
    """
    buf = ""
    cut = False
    async for text in streamed.stream_text(delta=True):
        if not text:
            continue
        raw_out.append(text)
        if cut:
            continue  # 已到 JSON 段：不转发，但继续迭代以收集完整 raw（提取 JSON 用）
        probe = buf + text
        idx = probe.find(_MARKER)
        if idx != -1:
            if probe[:idx]:
                yield probe[:idx]
            cut = True
            continue
        # 转发 probe 中除尾部 (len(_MARKER)-1) 字符外的全部（尾部保留用于跨 chunk marker 检测）
        safe_len = len(probe) - (len(_MARKER) - 1)
        if safe_len > 0:
            yield probe[:safe_len]
            buf = probe[safe_len:]
        else:
            buf = probe
    if buf and not cut:
        yield buf


class PydanticAIEngine:
    """基于 pydantic-ai 的推理循环实现（OpenAI 兼容 chat completions）。"""

    name = "pydantic-ai"

    def __init__(self, *, base_url: str, api_key: str, model: str) -> None:
        from pydantic_ai.models.openai import OpenAIChatModel
        from pydantic_ai.providers.openai import OpenAIProvider

        provider = OpenAIProvider(base_url=base_url, api_key=api_key or "not-configured")
        self._model = OpenAIChatModel(model, provider=provider)

    async def stream(
        self,
        *,
        system_prompt: str,
        tools: list[LoopTool],
        history: list[LoopMessage],
        prompt: str,
        output_schema: type | None = None,
    ) -> AsyncIterator[LoopEvent]:
        from pydantic_ai import Agent
        from pydantic_ai.messages import ModelRequest, ModelResponse, TextPart, UserPromptPart
        from pydantic_ai.tools import Tool

        agent_kwargs: dict = {"system_prompt": system_prompt, "retries": 2}
        if tools:
            agent_kwargs["tools"] = [Tool(t.fn, name=t.name, description=t.description) for t in tools]
        if output_schema is not None:
            agent_kwargs["system_prompt"] = system_prompt + _JSON_OUTPUT_INSTRUCTION
        agent = Agent(self._model, **agent_kwargs)
        message_history = [
            ModelRequest(parts=[UserPromptPart(content=m.content)])
            if m.role == "user"
            else ModelResponse(parts=[TextPart(content=m.content)])
            for m in history
        ]
        chunks: list[str] = []
        raw_chunks: list[str] = []
        # reasoning_effort=none：关闭 deepseek thinking 模式（thinking 下 temperature 被忽略，
        # 输出随机导致 JSON 计划不稳定；关闭后采样参数生效、输出确定性）
        async with agent.run_stream(
            prompt,
            message_history=message_history,
            model_settings={"temperature": 0, "thinking": "off", "openai_reasoning_effort": "none"},
        ) as streamed:
            async for text in _stream_filtered(streamed, raw_chunks):
                chunks.append(text)
                yield LoopEvent(kind="delta", text=text)

        output = None
        if output_schema is not None:
            data = _extract_json("".join(raw_chunks))
            if data is not None:
                try:
                    output = output_schema.model_validate(data).model_dump()
                except Exception:
                    output = None  # JSON 不符合 schema：降级为纯文本回复
        yield LoopEvent(kind="done", output=output)
