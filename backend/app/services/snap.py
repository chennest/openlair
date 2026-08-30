"""截图识别服务：图片 → 多模态 LLM → 结构化记账数据。

- 调用 OpenAI 兼容 `/chat/completions`（图片以 data URI 内联，无需图床）。
- 独立配置 SNAP_BASE_URL / SNAP_API_KEY / SNAP_MODEL，留空回退 LLM_*；
  注意：视觉识别需要多模态模型（如 qwen-vl-max / gpt-4o-mini），
  DeepSeek 等纯文本模型不支持图像，画风与 transcribe 一致（可插拔协议层）。
- 输出为纯文本 JSON + 鲁棒解析（同 AI 助手引擎的策略：温度 0 + 指令强约束）。
"""

import base64
import json
import re
from typing import Any

import httpx
from pydantic import BaseModel, Field

from app.core.envelope import ApiError

# 允许的图片 MIME（与 App 端 uni.chooseImage 产出对齐）
ALLOWED_IMAGE_MIME: dict[str, str] = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}

MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB

TIMEOUT = 120.0


class SnapParseData(BaseModel):
    """识别输出结构（与 App 端契约一致）。"""

    type: str = Field(default="支出", description="支出/收入")
    amount: float = Field(default=0.0, ge=0)
    category: str = Field(default="")
    note: str = Field(default="")
    date: str = Field(default="", description="YYYY-MM-DD")
    confidence: float = Field(default=0.0, ge=0, le=1)


_SYSTEM_PROMPT = (
    "你是一个记账助手。用户提供一张包含消费/收入信息的屏幕截图"
    "（如支付宝/微信支付记录、银行账单、购物小票、外卖/生鲜订单）。"
    "请识别其中的记账信息并严格输出 JSON（不要 markdown 代码块、不要多余文字）：\n"
    '{"type": "支出" 或 "收入", "amount": 正数金额数字, "category": "简短分类名(2-4字)", '
    '"note": "一句话备注(可为空字符串)", "date": "YYYY-MM-DD", '
    '"confidence": 0到1小数的置信度}\n'
    "规则：\n"
    "1. 订单类截图：一笔订单记一笔，amount 取实付总额（含包装费/配送费，扣优惠），不要拆分商品；"
    "category 用「餐饮」「购物」等，note 简要描述（如『小象超市买菜』）。\n"
    "2. date 以下单/支付日期为准；若图中只有预计送达/收货日期而无支付日期，取支付记录或截图中的当天日期。\n"
    '3. 若图片中无可识别的记账信息，输出 {"type":"支出","amount":0,"category":"","note":"","date":"","confidence":0}。'
)


def _extract_json(text: str) -> dict | None:
    """从回复文本鲁棒提取 JSON 对象（与 AI 助手引擎同款策略）。"""
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


class SnapParser:
    """多模态图片识别：OpenAI 兼容 chat.completions（图片 data URI 内联）。"""

    def __init__(self, *, base_url: str, api_key: str, model: str) -> None:
        self._base_url = base_url
        self._api_key = api_key
        self._model = model

    async def parse(self, *, image_bytes: bytes, mime: str) -> dict:
        if not self._api_key:
            raise ApiError(503, "截图识别未配置（缺少 SNAP_API_KEY）")
        if not self._base_url:
            raise ApiError(503, "截图识别未配置（缺少 SNAP_BASE_URL）")

        b64 = base64.b64encode(image_bytes).decode("ascii")
        url = f"{self._base_url.rstrip('/')}/chat/completions"
        payload: dict[str, Any] = {
            "model": self._model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "请识别下图中的记账信息。"},
                        {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                    ],
                },
            ],
        }

        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(
                url,
                json=payload,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
            )

        if resp.status_code != 200:
            message = ""
            try:
                body = resp.json()
                message = body.get("error", {}).get("message", "") or body.get("message", "") or ""
            except Exception:
                message = resp.text[:200]
            raise ApiError(502, f"截图识别失败（HTTP {resp.status_code}）：{message}")

        try:
            body = resp.json()
        except Exception:
            raise ApiError(502, "截图识别失败：无法解析响应")

        choices = body.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ApiError(502, "截图识别失败：响应缺少 choices")
        content = choices[0].get("message", {}).get("content", "")
        if not isinstance(content, str) or not content:
            raise ApiError(502, "截图识别失败：响应缺少内容")

        data = _extract_json(content)
        if data is None:
            raise ApiError(502, "截图识别失败：模型未返回结构化 JSON")
        try:
            parsed = SnapParseData.model_validate(data)
        except Exception:
            raise ApiError(502, "截图识别失败：模型输出不符合契约") from None

        return parsed.model_dump()
