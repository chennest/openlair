"""配置读取：项目根 .env（lairservice/.env）+ 进程环境变量。

优先级：进程环境 → 项目根 .env → 默认值。
"""

from pathlib import Path
import os

# 项目根目录（src/lairservice/config.py → 上溯 2 层）
_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _strip_env_value(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _parse_dotenv(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue
        values[key] = _strip_env_value(value.strip())
    return values


def resolve_env_value(key: str, default: str | None = None) -> str | None:
    """按优先级读取配置值：进程环境 → 项目根 .env（lairservice/.env）→ 默认值。"""
    from_env = os.environ.get(key)
    if from_env:
        return from_env
    project_env = _parse_dotenv(_PROJECT_ROOT / ".env")
    if project_env.get(key):
        return project_env[key]
    return default
