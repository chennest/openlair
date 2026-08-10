"""AI 助手测试：会话 CRUD / 无 key 降级 / 安全确认全流程（fake loop 模拟 LLM，不调真实 API）。"""

import json
import re

from fastapi.testclient import TestClient

from app.main import create_app
from app.models.assistant import AssistantPlan
from app.services.assistant.loop.base import LoopEvent


class FakeLoopEngine:
    """模拟 LLM 推理循环：按脚本产出事件。

    steps: list of (kind, payload)
      ('text', '回复文本')          → 产出文本 delta
      ('tool', 'tool_name|{json}')  → 调用查询工具
      ('plan', '{json}')            → 结构化输出记账计划（LedgerPlan）
    """

    name = "fake"

    def __init__(self, steps: list[tuple[str, str]]) -> None:
        self.steps = steps

    async def stream(self, *, system_prompt, tools, history, prompt, output_schema=None):
        output = None
        for kind, payload in self.steps:
            if kind == "text":
                yield LoopEvent(kind="delta", text=payload)
            elif kind == "tool":
                tool_name, args_json = payload.split("|", 1)
                tool = next(t for t in tools if t.name == tool_name)
                yield LoopEvent(kind="tool_start", tool_name=tool_name)
                await tool.fn(**json.loads(args_json))
                yield LoopEvent(kind="tool_end", tool_name=tool_name, ok=True)
            elif kind == "plan":
                output = json.loads(payload)
        yield LoopEvent(kind="done", output=output)


def make_client(tmp_path, monkeypatch, llm_key: str = "") -> TestClient:
    monkeypatch.setenv("LLM_API_KEY", llm_key)
    return TestClient(create_app(database_url=f"sqlite+pysqlite:///{tmp_path}/lair-ai.db"))


def login(client: TestClient, email: str = "test1@openlair.dev") -> tuple[str, dict]:
    r = client.post("/api/auth/login", json={"email": email, "password": "test123456"})
    assert r.status_code == 200 and r.json()["code"] == 200
    return r.json()["data"]["token"], r.json()["data"]["user"]


def ah(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def new_session(client: TestClient, token: str) -> dict:
    r = client.post("/api/assistant/sessions", headers=ah(token))
    assert r.status_code == 200 and r.json()["code"] == 200
    data = r.json()["data"]
    assert "updatedAt" in data
    return data


# ---------- 会话 CRUD ----------

def test_sessions_crud_and_isolation(tmp_path, monkeypatch) -> None:
    client = make_client(tmp_path, monkeypatch)
    t1, _ = login(client)
    t2, _ = login(client, "test2@openlair.dev")

    sess = new_session(client, t1)
    assert sess["id"] > 0

    # 空会话不出现（尚未发消息）—— 列表为空
    assert client.get("/api/assistant/sessions", headers=ah(t1)).json()["data"] == []
    assert client.get("/api/assistant/sessions", headers=ah(t2)).json()["data"] == []

    # 发一条消息 → 列表出现
    r = client.post(
        "/api/assistant/chat", headers=ah(t1), json={"sessionId": sess["id"], "message": "hi"}
    )
    assert r.status_code == 200
    assert [s["id"] for s in client.get("/api/assistant/sessions", headers=ah(t1)).json()["data"]] == [sess["id"]]
    assert client.get("/api/assistant/sessions", headers=ah(t2)).json()["data"] == []

    # 别人的会话 → 404（消息 / 对话均隔离）
    r = client.get(f"/api/assistant/sessions/{sess['id']}/messages", headers=ah(t2))
    assert r.status_code == 404 and r.json()["code"] == 404
    r = client.post(
        "/api/assistant/chat", headers=ah(t2), json={"sessionId": sess["id"], "message": "hi"}
    )
    assert r.status_code == 200 and "会话不存在" in r.text


# ---------- 无 LLM key 降级 ----------

def test_chat_without_llm_key_returns_error(tmp_path, monkeypatch) -> None:
    client = make_client(tmp_path, monkeypatch)
    token, _ = login(client)
    sess = new_session(client, token)
    r = client.post(
        "/api/assistant/chat", headers=ah(token), json={"sessionId": sess["id"], "message": "记一笔"}
    )
    assert r.status_code == 200
    assert "LLM_API_KEY" in r.text
    # 用户消息已入库，助手侧没有回复消息
    msgs = client.get(f"/api/assistant/sessions/{sess['id']}/messages", headers=ah(token)).json()["data"]
    assert [m["role"] for m in msgs] == ["user"]


# ---------- 安全确认全流程 ----------

def test_confirm_execute_creates_transaction(tmp_path, monkeypatch) -> None:
    client = make_client(tmp_path, monkeypatch, llm_key="sk-fake")
    runtime = client.app.state.assistant_runtime
    runtime._engine = FakeLoopEngine(
        [
            ("plan", '{"action": "record", "type": "支出", "amount": 68.0, "category": "餐饮", "date": "昨天", "book": "AI测试账本"}'),
            ("text", "好的，将记一笔：支出 68.00 元 · 餐饮 · 昨天，请确认"),
        ]
    )
    token, _ = login(client)
    book = client.post("/api/books", headers=ah(token), json={"name": "AI测试账本", "type": "personal"}).json()["data"]["book"]
    sess = new_session(client, token)

    r = client.post(
        "/api/assistant/chat", headers=ah(token), json={"sessionId": sess["id"], "message": "昨天中午吃饭花了68"}
    )
    assert r.status_code == 200
    assert "confirm_request" in r.text
    plan_id = re.search(r'"planId": "([0-9a-f]+)"', r.text).group(1)

    # 确认 → 落库
    r = client.post("/api/assistant/confirm", headers=ah(token), json={"planId": plan_id, "approved": True})
    assert r.json()["code"] == 200
    assert "已记账" in r.json()["data"]["message"]

    ledger = client.get("/api/ledger", headers=ah(token), params={"bookId": book["id"]}).json()["data"]
    assert ledger["transactions"] and ledger["transactions"][0]["amount"] == 68.0
    assert ledger["transactions"][0]["type"] == "支出"

    msgs = client.get(f"/api/assistant/sessions/{sess['id']}/messages", headers=ah(token)).json()["data"]
    assert msgs[-1]["content"].startswith("已记账")


def test_confirm_reject_does_not_write(tmp_path, monkeypatch) -> None:
    client = make_client(tmp_path, monkeypatch, llm_key="sk-fake")
    runtime = client.app.state.assistant_runtime
    runtime._engine = FakeLoopEngine(
        [("plan", '{"action": "record", "type": "支出", "amount": 30.0, "category": "餐饮", "book": "AI测试账本"}')]
    )
    token, _ = login(client)
    book = client.post("/api/books", headers=ah(token), json={"name": "AI测试账本", "type": "personal"}).json()["data"]["book"]
    sess = new_session(client, token)

    r = client.post(
        "/api/assistant/chat", headers=ah(token), json={"sessionId": sess["id"], "message": "午饭30"}
    )
    plan_id = re.search(r'"planId": "([0-9a-f]+)"', r.text).group(1)

    r = client.post("/api/assistant/confirm", headers=ah(token), json={"planId": plan_id, "approved": False})
    assert r.json()["code"] == 200 and "已取消" in r.json()["data"]["message"]

    ledger = client.get("/api/ledger", headers=ah(token), params={"bookId": book["id"]}).json()["data"]
    assert ledger["transactions"] == []


def test_confirm_plan_belongs_to_user(tmp_path, monkeypatch) -> None:
    client = make_client(tmp_path, monkeypatch, llm_key="sk-fake")
    runtime = client.app.state.assistant_runtime
    runtime._engine = FakeLoopEngine(
        [("plan", '{"action": "record", "type": "支出", "amount": 10.0, "book": "AI测试账本"}')]
    )
    t1, _ = login(client)
    t2, _ = login(client, "test2@openlair.dev")
    client.post("/api/books", headers=ah(t1), json={"name": "AI测试账本", "type": "personal"})
    sess = new_session(client, t1)

    r = client.post(
        "/api/assistant/chat", headers=ah(t1), json={"sessionId": sess["id"], "message": "十块"}
    )
    plan_id = re.search(r'"planId": "([0-9a-f]+)"', r.text).group(1)

    # 别的用户确认 → 404（计划不属于他，get 校验失败）
    r = client.post("/api/assistant/confirm", headers=ah(t2), json={"planId": plan_id, "approved": True})
    assert r.status_code == 404

    # 原用户仍可确认
    r = client.post("/api/assistant/confirm", headers=ah(t1), json={"planId": plan_id, "approved": True})
    assert r.json()["code"] == 200


def test_confirm_unknown_plan_404(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LLM_API_KEY", "sk-fake")
    client = make_client(tmp_path, monkeypatch)
    token, _ = login(client)
    r = client.post("/api/assistant/confirm", headers=ah(token), json={"planId": "nope", "approved": True})
    assert r.status_code == 404


# ---------- plan 持久化：状态机 + 消息类型 + 隔离 ----------

def _db_plan(client: TestClient, plan_id: str) -> dict | None:
    """从 DB 直接查一条计划记录。"""
    runtime = client.app.state.assistant_runtime
    with runtime._sf() as s:
        plan = s.query(AssistantPlan).filter_by(plan_id=plan_id).first()
        if plan is None:
            return None
        return {
            "plan_id": plan.plan_id,
            "status": plan.status,
            "result": plan.result,
            "executed_at": plan.executed_at,
            "user_id": plan.user_id,
            "session_id": plan.session_id,
        }


def test_plan_lifecycle_persisted(tmp_path, monkeypatch) -> None:
    """chat 生成 plan → 落库 status=pending → confirm 后 status=executed → 再 confirm 404。"""
    client = make_client(tmp_path, monkeypatch, llm_key="sk-fake")
    runtime = client.app.state.assistant_runtime
    runtime._engine = FakeLoopEngine(
        [
            ("plan", '{"action": "record", "type": "支出", "amount": 55.0, "category": "餐饮", "book": "AI测试账本"}'),
            ("text", "好的，将记一笔支出 55 元，请确认"),
        ]
    )
    token, _ = login(client)
    client.post("/api/books", headers=ah(token), json={"name": "AI测试账本", "type": "personal"})
    sess = new_session(client, token)

    # chat：生成 plan
    r = client.post(
        "/api/assistant/chat", headers=ah(token), json={"sessionId": sess["id"], "message": "午饭55"}
    )
    assert r.status_code == 200
    plan_id = re.search(r'"planId": "([0-9a-f]+)"', r.text).group(1)

    # DB 有记录，status=pending
    plan = _db_plan(client, plan_id)
    assert plan is not None
    assert plan["status"] == "pending"
    assert plan["executed_at"] is None

    # confirm → executed
    r = client.post("/api/assistant/confirm", headers=ah(token), json={"planId": plan_id, "approved": True})
    assert r.json()["code"] == 200

    plan = _db_plan(client, plan_id)
    assert plan["status"] == "executed"
    assert plan["result"] is not None
    assert "已记账" in plan["result"].get("message", "")
    assert plan["executed_at"] is not None

    # 重复确认 → 404（幂等防重复）
    r = client.post("/api/assistant/confirm", headers=ah(token), json={"planId": plan_id, "approved": True})
    assert r.status_code == 404


def test_message_type_and_meta(tmp_path, monkeypatch) -> None:
    """chat AI 消息 type=confirm_request + meta.planId；confirm 后 tool_result 消息 type=tool_result + meta。"""
    client = make_client(tmp_path, monkeypatch, llm_key="sk-fake")
    runtime = client.app.state.assistant_runtime
    runtime._engine = FakeLoopEngine(
        [
            ("plan", '{"action": "record", "type": "支出", "amount": 42.0, "category": "餐饮", "book": "AI测试账本"}'),
            ("text", "确认记账：42 元餐饮"),
        ]
    )
    token, _ = login(client)
    client.post("/api/books", headers=ah(token), json={"name": "AI测试账本", "type": "personal"})
    sess = new_session(client, token)

    r = client.post(
        "/api/assistant/chat", headers=ah(token), json={"sessionId": sess["id"], "message": "午餐42"}
    )
    assert r.status_code == 200
    plan_id = re.search(r'"planId": "([0-9a-f]+)"', r.text).group(1)

    msgs = client.get(f"/api/assistant/sessions/{sess['id']}/messages", headers=ah(token)).json()["data"]
    # 用户消息 type=text
    assert msgs[0]["type"] == "text"
    # AI 消息 type=confirm_request 且 meta.planId 正确
    ai_msg = msgs[-1]
    assert ai_msg["type"] == "confirm_request"
    assert ai_msg["meta"]["planId"] == plan_id
    assert ai_msg["meta"]["tool"] == "LedgerPlan"

    # confirm
    client.post("/api/assistant/confirm", headers=ah(token), json={"planId": plan_id, "approved": True})

    msgs = client.get(f"/api/assistant/sessions/{sess['id']}/messages", headers=ah(token)).json()["data"]
    tool_msg = msgs[-1]
    assert tool_msg["type"] == "tool_result"
    assert tool_msg["meta"]["kind"] == "executed"
    assert tool_msg["meta"]["planId"] == plan_id
    assert tool_msg["role"] == "assistant"

    # get_messages 返回含 type 字段
    for m in msgs:
        assert "type" in m


def test_cancel_plan_status(tmp_path, monkeypatch) -> None:
    """approved=False → 计划 status='cancelled'，追加 tool_result 消息。"""
    client = make_client(tmp_path, monkeypatch, llm_key="sk-fake")
    runtime = client.app.state.assistant_runtime
    runtime._engine = FakeLoopEngine(
        [("plan", '{"action": "record", "type": "支出", "amount": 10.0, "book": "AI测试账本"}')]
    )
    token, _ = login(client)
    client.post("/api/books", headers=ah(token), json={"name": "AI测试账本", "type": "personal"})
    sess = new_session(client, token)

    r = client.post(
        "/api/assistant/chat", headers=ah(token), json={"sessionId": sess["id"], "message": "10块"}
    )
    plan_id = re.search(r'"planId": "([0-9a-f]+)"', r.text).group(1)

    r = client.post("/api/assistant/confirm", headers=ah(token), json={"planId": plan_id, "approved": False})
    assert r.json()["code"] == 200

    # DB 状态
    plan = _db_plan(client, plan_id)
    assert plan["status"] == "cancelled"
    assert plan["executed_at"] is not None

    # 消息 type=tool_result, kind=cancelled
    msgs = client.get(f"/api/assistant/sessions/{sess['id']}/messages", headers=ah(token)).json()["data"]
    tool_msg = msgs[-1]
    assert tool_msg["type"] == "tool_result"
    assert tool_msg["meta"]["kind"] == "cancelled"
    assert "已取消" in tool_msg["content"]


def test_plan_isolation(tmp_path, monkeypatch) -> None:
    """t2 确认 t1 的 plan_id → 404（越权隔离）。"""
    client = make_client(tmp_path, monkeypatch, llm_key="sk-fake")
    runtime = client.app.state.assistant_runtime
    runtime._engine = FakeLoopEngine(
        [("plan", '{"action": "record", "type": "支出", "amount": 5.0, "book": "AI测试账本"}')]
    )
    t1, _ = login(client)
    t2, _ = login(client, "test2@openlair.dev")
    client.post("/api/books", headers=ah(t1), json={"name": "AI测试账本", "type": "personal"})
    sess = new_session(client, t1)

    r = client.post(
        "/api/assistant/chat", headers=ah(t1), json={"sessionId": sess["id"], "message": "5块"}
    )
    plan_id = re.search(r'"planId": "([0-9a-f]+)"', r.text).group(1)

    # t2 确认 t1 的计划 → 404
    r = client.post("/api/assistant/confirm", headers=ah(t2), json={"planId": plan_id, "approved": True})
    assert r.status_code == 404

    # t1 仍可确认
    r = client.post("/api/assistant/confirm", headers=ah(t1), json={"planId": plan_id, "approved": True})
    assert r.json()["code"] == 200


# ---------- 草稿态：sessionId=None 自动创建 ----------

def test_chat_with_null_session_auto_creates(tmp_path, monkeypatch) -> None:
    """sessionId=None 时自动创建会话并发首条消息。"""
    client = make_client(tmp_path, monkeypatch)  # 无 LLM key
    token, _ = login(client)

    r = client.post(
        "/api/assistant/chat", headers=ah(token), json={"sessionId": None, "message": "记一笔午饭"}
    )
    assert r.status_code == 200
    assert "LLM_API_KEY" in r.text

    items = client.get("/api/assistant/sessions", headers=ah(token)).json()["data"]
    assert len(items) == 1
    assert items[0]["title"] == "记一笔午饭"
    assert "updatedAt" in items[0]

    msgs = client.get(
        f"/api/assistant/sessions/{items[0]['id']}/messages", headers=ah(token)
    ).json()["data"]
    assert [m["role"] for m in msgs] == ["user"]


# ---------- 删除会话 ----------

def test_delete_session_removes_session_and_messages(tmp_path, monkeypatch) -> None:
    """删除会话清空消息且他人操作该会话返回 404。"""
    client = make_client(tmp_path, monkeypatch)
    t1, _ = login(client)
    t2, _ = login(client, "test2@openlair.dev")

    # t1 创建会话并发一条消息
    sess = new_session(client, t1)
    r = client.post(
        "/api/assistant/chat", headers=ah(t1), json={"sessionId": sess["id"], "message": "hello"}
    )
    assert r.status_code == 200

    # t1 删除自己的会话
    r = client.delete(f"/api/assistant/sessions/{sess['id']}", headers=ah(t1))
    assert r.status_code == 200 and r.json()["code"] == 200

    # 列表不含该会话
    assert client.get("/api/assistant/sessions", headers=ah(t1)).json()["data"] == []

    # 消息返回 404
    r = client.get(f"/api/assistant/sessions/{sess['id']}/messages", headers=ah(t1))
    assert r.status_code == 404

    # t2 DELETE 同一会话 → 404
    r = client.delete(f"/api/assistant/sessions/{sess['id']}", headers=ah(t2))
    assert r.status_code == 404

    # t1 用已删除 id 聊天 → 404
    r = client.post(
        "/api/assistant/chat", headers=ah(t1), json={"sessionId": sess["id"], "message": "again"}
    )
    assert r.status_code == 200 and "会话不存在" in r.text
