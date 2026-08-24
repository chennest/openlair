"""截图识别真实模型集成测试（门控：SNAP_LIVE=1 才执行，避免日常 pytest 调用外部 LLM）。

用法：
  uv run pytest tests/test_snap_live.py -q                      # 默认 skip
  SNAP_LIVE=1 uv run pytest tests/test_snap_live.py -q          # 真实调用（需 .env 已配 SNAP_MODEL）
"""

import os
import pathlib

import pytest
from fastapi.testclient import TestClient

from app.main import create_app

ASSET_DIR = pathlib.Path(__file__).parent / "assets"

# (文件名, 期望金额, 期望类型, 期望分类)
CASES: list[tuple[str, float, str, str]] = [
    ("xiaoxiang-order.jpg", 55.02, "支出", "餐饮"),
    ("bill-tmall.jpg", 6.95, "支出", "餐饮"),
    ("bill-metro.jpg", 3.6, "支出", "交通"),
    # 后续的新截图按此格式追加即可
]

pytestmark = pytest.mark.skipif(
    os.environ.get("SNAP_LIVE") != "1",
    reason="真实 LLM 调用；设置环境变量 SNAP_LIVE=1 启用（需要 .env 已配置视觉模型）",
)


def make_client(tmp_path) -> TestClient:
    return TestClient(create_app(database_url=f"sqlite+pysqlite:///{tmp_path}/lair-live.db"))


def login(client: TestClient) -> str:
    r = client.post("/api/auth/login", json={"email": "test1@openlair.dev", "password": "test123456"})
    assert r.status_code == 200
    return r.json()["data"]["token"]


@pytest.mark.parametrize(
    "filename,expect_amount,expect_type,expect_category",
    CASES,
    ids=[f"{c[0]}:{c[1]}" for c in CASES],
)
def test_live_recognize_screenshot(
    tmp_path, filename: str, expect_amount: float, expect_type: str, expect_category: str
) -> None:
    """真实识别截图：金额/类型/分类应精确命中。"""
    asset = ASSET_DIR / filename
    assert asset.exists(), f"测试素材缺失：{asset}"
    client = make_client(tmp_path)
    token = login(client)
    with asset.open("rb") as f:
        r = client.post(
            "/api/snap/parse",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": (asset.name, f, "image/jpeg")},
        )
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["type"] == expect_type, f"类型识别偏差：{data}"
    assert abs(data["amount"] - expect_amount) < 0.01, f"金额识别偏差：{data}"
    assert data["category"] == expect_category, f"分类识别偏差：{data}"
    # date 允许为空串（前端兜底用当天）：非空时必须是 YYYY-MM-DD
    assert data["date"] == "" or len(data["date"]) == 10, f"日期格式异常：{data}"
    assert data["confidence"] > 0.5, f"置信度过低：{data}"
