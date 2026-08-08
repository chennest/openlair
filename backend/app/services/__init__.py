"""应用服务层：业务逻辑 + DTO 转换（路由只做 HTTP 薄层）。"""

from datetime import UTC, datetime


def iso_z(value: datetime) -> str:
    """datetime → 与 mock 一致的 ISO 8601 UTC（Z 结尾）字符串。"""
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
