"""AI 助手：上下文自动压缩（compaction）的共享定义。

设计对齐主流做法（OpenAI / Anthropic 的 server-side compaction、DeepSeek Harness 的
dsh-compaction-basic）：
- 触发：历史 token 估算超过阈值；
- 保留：最近一段原文（retain 预算）；
- 摘要：单独一次 LLM 调用，把较早的完整轮次压成紧凑检查点；
- 原始消息仍在 DB 可回放，模型侧只替换派生历史。

同时定义「聊天流转框架」的公共常量：对话是一条平铺有序的 transcript，
每轮 = user → assistant（你）→ tool（工具执行结果），tool 结果是聊天流的一等公民。
"""

# 检查点前导语：告诉模型把摘要当作已建立的背景，不要复述
CHECKPOINT_PREAMBLE = (
    "以下是此前对话的自动压缩摘要。请把它当作已经确立的背景信息，"
    "直接基于它继续，不要复述这些内容。\n"
)
CHECKPOINT_OPEN = "<compacted-summary>\n"
CHECKPOINT_CLOSE = "\n</compacted-summary>"

# 工具执行结果在喂给模型时的前缀（区分「你说的话」与「工具干的事」）
TOOL_RESULT_PREFIX = "[工具结果] "

# 压缩摘要的系统提示词（只输出摘要本身，不调用工具、不额外解释）
COMPACTION_SYSTEM_PROMPT = (
    "你现在是 OpenLair 记账助手的上下文压缩引擎。"
    "请把下面的对话历史压缩成一段紧凑的中文检查点摘要，供后续轮次继续使用，"
    "确保不丢失关键信息：金额、分类、日期、账本、已确认的记账、用户偏好与未决事项。\n"
    "严格按以下结构输出，每节用简洁要点，无内容时写“（无）”：\n"
    "## 用户背景与偏好\n（无或要点）\n"
    "## 近期已记账\n（逐条：金额/分类/日期/账本）\n"
    "## 未决事项\n（无或要点）\n"
    "## 其他关键上下文\n（无或要点）\n"
    "规则：只输出摘要文本本身，不要任何额外说明，不要复述本指令。"
)


def checkpoint_message(summary: str) -> str:
    """把检查点摘要包成一条 user 角色的上下文消息。"""
    return CHECKPOINT_PREAMBLE + CHECKPOINT_OPEN + summary + CHECKPOINT_CLOSE


def estimate_tokens(text: str) -> int:
    """粗略估算 token 数：中文 1 字≈1 token，其余 4 字符≈1 token。

    OpenLair 未接入精确 tokenizer；记账场景用该启发式足够做压缩触发判断。
    """
    if not text:
        return 0
    cjk = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
    other = len(text) - cjk
    return cjk + other // 4
