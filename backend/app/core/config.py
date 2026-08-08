"""应用配置（pydantic-settings）：环境变量 → 项目根 .env（backend/.env）→ 默认值。

模板见 backend/.env.example；读取细节由 pydantic-settings 处理（引号/注释/类型校验）。
"""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# 项目根目录（backend/app/core/config.py → 上溯 2 层）
_PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """全部应用配置字段；env 文件缺失字段时落到默认值。"""

    # JWT 签名密钥：HS256 要求 >= 32 字节（生产必须配置，见 .env.example）
    jwt_secret: str = Field(
        default="openlair-dev-secret-key-0123456789ab", validation_alias="OPENLAIR_JWT_SECRET"
    )
    # 数据库连接串：SQLite / MySQL / PostgreSQL 均可（见 .env.example）
    database_url: str = Field(
        default="sqlite+pysqlite:///./data/lair.db", validation_alias="DATABASE_URL"
    )
    # CORS 允许来源（逗号分隔；开发默认本地 Vite，测试/生产按需配置）
    cors_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173", validation_alias="CORS_ORIGINS"
    )

    model_config = SettingsConfigDict(
        env_file=_PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


def get_settings() -> Settings:
    """每次新建实例：实时读取环境变量与 .env（测试可 monkeypatch 后重新调用）。"""
    return Settings()