"""语音转写服务：可插拔协议层（BaseTranscriber）+ DashScope / OpenAI 兼容双实现。

通过 TRANSCRIBE_ENGINE 环境变量切换：
  - dashscope（默认）：阿里云百炼 qwen3-asr-flash（multimodal-generation）
  - openai-compatible：POST {base}/audio/transcriptions（multipart file + model）
    适用于自建 faster-whisper-server 或任何 OpenAI 兼容 STT 网关。
"""

import base64
import mimetypes
from abc import ABC, abstractmethod
from pathlib import Path

import httpx

from app.core.envelope import ApiError

# 扩展名 → MIME 类型映射（兜底 mimetypes 未命中场景）
_EXT_MIME: dict[str, str] = {
    ".wav": "audio/wav",
    ".mp3": "audio/mpeg",
    ".m4a": "audio/mp4",
    ".mp4": "audio/mp4",
    ".webm": "audio/webm",
    ".ogg": "audio/ogg",
    ".flac": "audio/flac",
    ".aac": "audio/aac",
    ".opus": "audio/opus",
}

# 允许上传的扩展名集合
ALLOWED_EXTENSIONS: set[str] = {
    ".wav", ".mp3", ".m4a", ".mp4", ".webm", ".ogg", ".flac", ".aac", ".opus",
}

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

TIMEOUT = 120.0


def _guess_mime(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix in _EXT_MIME:
        return _EXT_MIME[suffix]
    mime, _ = mimetypes.guess_type(filename)
    return mime or "application/octet-stream"


def _parse_response(data: dict) -> str:
    """解析 DashScope 多模态响应，兼容两种结构。

    1. 标准多模态：output.choices[0].message.content[0].text
    2. ASR 特化：output.output.sentence.text 或 output.text
    """
    output = data.get("output")
    if not isinstance(output, dict):
        raise ApiError(502, "语音识别失败：响应缺少 output 字段")

    # 结构 1：标准多模态
    choices = output.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0]
        if isinstance(first, dict):
            msg = first.get("message", {})
            if isinstance(msg, dict):
                content = msg.get("content")
                if isinstance(content, list) and content:
                    text = content[0].get("text")
                    if isinstance(text, str) and text:
                        return text

    # 结构 2：ASR 特化
    inner = output.get("output")
    if isinstance(inner, dict):
        sentence = inner.get("sentence")
        if isinstance(sentence, dict):
            text = sentence.get("text")
            if isinstance(text, str) and text:
                return text

    # 顶层 output.text
    text = output.get("text")
    if isinstance(text, str) and text:
        return text

    # 兜底：尝试从原始响应的 message / code 提取信息
    raw_msg = data.get("message", "") or data.get("code", "") or "未知错误"
    raise ApiError(502, f"语音识别失败：{raw_msg}")


# ── 协议基类 ──────────────────────────────────────────────────


class BaseTranscriber(ABC):
    """语音转写协议：所有引擎实现 transcribe_audio。"""

    @abstractmethod
    async def transcribe_audio(self, *, audio_bytes: bytes, filename: str) -> str:
        """将音频字节流转写为文本。"""
        ...


# ── DashScope 实现 ─────────────────────────────────────────────


class DashScopeTranscriber(BaseTranscriber):
    """阿里云百炼 DashScope 语音转写（qwen3-asr-flash / multimodal-generation）。"""

    def __init__(self, *, base_url: str, api_key: str, model: str) -> None:
        self._base_url = base_url
        self._api_key = api_key
        self._model = model

    async def transcribe_audio(self, *, audio_bytes: bytes, filename: str) -> str:
        if not self._api_key:
            raise ApiError(503, "语音识别未配置（缺少 TRANSCRIBE_API_KEY）")

        mime = _guess_mime(filename)
        b64 = base64.b64encode(audio_bytes).decode("ascii")
        url = f"{self._base_url}/services/aigc/multimodal-generation/generation"

        payload: dict = {
            "model": self._model,
            "input": {
                "messages": [
                    {"role": "system", "content": [{"text": ""}]},
                    {"role": "user", "content": [{"audio": f"data:{mime};base64,{b64}"}]},
                ]
            },
            "parameters": {"asr_options": {"enable_lid": True, "enable_itn": False}},
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
                message = body.get("message", "") or body.get("code", "") or ""
            except Exception:
                message = resp.text[:200]
            raise ApiError(502, f"语音识别失败（HTTP {resp.status_code}）：{message}")

        try:
            data = resp.json()
        except Exception:
            raise ApiError(502, "语音识别失败：无法解析响应")

        return _parse_response(data)


# ── OpenAI 兼容实现 ─────────────────────────────────────────────


class OpenAICompatTranscriber(BaseTranscriber):
    """OpenAI 兼容转写：POST {base}/audio/transcriptions（multipart file + model）。

    适用于自建 faster-whisper-server / 任何 OpenAI 兼容 STT 网关。
    """

    def __init__(self, *, base_url: str, api_key: str, model: str) -> None:
        self._base_url = base_url
        self._api_key = api_key
        self._model = model

    async def transcribe_audio(self, *, audio_bytes: bytes, filename: str) -> str:
        if not self._api_key:
            raise ApiError(503, "语音识别未配置（缺少 TRANSCRIBE_OPENAI_API_KEY）")

        mime = _guess_mime(filename)
        url = f"{self._base_url.rstrip('/')}/audio/transcriptions"

        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(
                url,
                headers={"Authorization": f"Bearer {self._api_key}"},
                files={"file": (filename, audio_bytes, mime)},
                data={"model": self._model},
            )

        if resp.status_code != 200:
            message = ""
            try:
                body = resp.json()
                message = body.get("message", "") or body.get("error", {}).get("message", "") or ""
            except Exception:
                message = resp.text[:200]
            raise ApiError(502, f"语音识别失败（HTTP {resp.status_code}）：{message}")

        try:
            body = resp.json()
        except Exception:
            raise ApiError(502, "语音识别失败：无法解析响应")

        text = body.get("text")
        if not isinstance(text, str) or not text:
            raise ApiError(502, "语音识别失败：响应缺少 text 字段")

        return text


# ── 工厂函数 ───────────────────────────────────────────────────


def create_transcriber(
    *,
    engine: str,
    dashscope_base_url: str,
    dashscope_api_key: str,
    dashscope_model: str,
    openai_base_url: str,
    openai_api_key: str,
    openai_model: str,
) -> BaseTranscriber:
    """根据 engine 创建对应的转写器实例。

    engine 取值：
      - "dashscope"（默认）：使用 DashScope multimodal-generation
      - "openai-compatible"：使用 OpenAI 兼容 audio/transcriptions 端点
    """
    if engine == "openai-compatible":
        if not openai_base_url:
            raise ApiError(503, "语音识别未配置（缺少 TRANSCRIBE_OPENAI_BASE_URL）")
        return OpenAICompatTranscriber(
            base_url=openai_base_url,
            api_key=openai_api_key,
            model=openai_model or "whisper-1",
        )
    return DashScopeTranscriber(
        base_url=dashscope_base_url,
        api_key=dashscope_api_key,
        model=dashscope_model,
    )
