"""词汇打字练习模块契约测试：排课 / 错次映射 / FSRS 调度 / 生词管理 / 统计。

每个用例独立 SQLite 文件；词汇演示词书由 seed 注入（8 个词，book_id=1）。
"""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.main import create_app
from app.models.vocab import VocabWordProgress

BOOK_ID = 1  # seed 的演示词书


def make_client(tmp_path) -> TestClient:
    app = create_app(database_url=f"sqlite+pysqlite:///{tmp_path}/lair-vocab.db")
    app.state.setting_repo.set("allow_register", "1")
    return TestClient(app)


def login(client: TestClient, email: str) -> dict:
    r = client.post("/api/auth/login", json={"email": email, "password": "test123456"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['data']['token']}"}


def register(client: TestClient, email: str) -> dict:
    client.post("/api/auth/register", json={"name": "词汇用户", "email": email, "password": "test123456"})
    return login(client, email)


def force_due(client: TestClient, progress_id: int, due: datetime) -> None:
    """直接改库把某条进度置为到期（模拟时间流逝）。"""
    with client.app.state.session_factory() as session:
        row = session.get(VocabWordProgress, progress_id)
        row.due = due
        session.commit()


# ---------- 词书与单词 ----------

def test_vocab_books_list_with_stats(tmp_path) -> None:
    client = make_client(tmp_path)
    headers = register(client, "vocab1@openlair.dev")
    r = client.get("/api/vocab/books", headers=headers)
    assert r.status_code == 200
    books = r.json()["data"]["books"]
    assert len(books) == 1
    book = books[0]
    assert book["slug"] == "demo"
    assert book["wordCount"] == 8
    assert book["learning"] == 0 and book["mastered"] == 0 and book["due"] == 0


def test_book_words_paging_and_fields(tmp_path) -> None:
    client = make_client(tmp_path)
    headers = register(client, "vocab2@openlair.dev")
    r = client.get(f"/api/vocab/books/{BOOK_ID}/words", params={"limit": 3, "offset": 0}, headers=headers)
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["total"] == 8
    assert len(data["words"]) == 3
    word = data["words"][0]
    assert word["word"] == "cancel"
    assert word["translations"][0]["pos"] == "v."
    assert word["sentences"][0]["en"].startswith("The customer")
    assert word["phoneticUs"] == "ˈkænsl"
    # offset 分页
    r2 = client.get(f"/api/vocab/books/{BOOK_ID}/words", params={"limit": 3, "offset": 3}, headers=headers)
    assert r2.json()["data"]["words"][0]["word"] != word["word"]


# ---------- 练习闭环 ----------

def test_practice_flow_correct_answer_and_finish(tmp_path) -> None:
    client = make_client(tmp_path)
    headers = register(client, "vocab3@openlair.dev")

    r = client.post("/api/vocab/practice/sessions", json={"bookId": BOOK_ID, "mode": "follow"}, headers=headers)
    assert r.status_code == 200
    data = r.json()["data"]
    session_id = data["id"]
    assert data["mode"] == "follow"
    assert len(data["queue"]) == 8  # 全部是新词
    assert all(item["progress"] is None for item in data["queue"])

    # 第一个词一次全对：Good → due ≈ 2 天后，进入 Review 态
    word_id = data["queue"][0]["id"]
    r = client.post(
        f"/api/vocab/practice/sessions/{session_id}/answers",
        json={"wordId": word_id, "correct": True, "wrongTimes": 0, "durationMs": 4200},
        headers=headers,
    )
    assert r.status_code == 200
    progress = r.json()["data"]["item"]
    assert progress["wordId"] == word_id
    assert progress["state"] == 2  # Review
    assert progress["rightCount"] == 1 and progress["wrongCount"] == 0
    assert progress["wrongActive"] is False
    due = datetime.fromisoformat(progress["due"].replace("Z", "+00:00"))
    assert due > datetime.now(UTC) + timedelta(days=1)

    # 结束会话
    r = client.post(f"/api/vocab/practice/sessions/{session_id}/finish", json={"durationSec": 66}, headers=headers)
    assert r.status_code == 200
    item = r.json()["data"]["item"]
    assert item["finishedAt"] is not None and item["durationSec"] == 66

    # 统计：今天练了 1 个词
    r = client.get("/api/vocab/stats", headers=headers)
    stats = r.json()["data"]
    assert stats["today"]["words"] == 1 and stats["total"]["learned"] == 1

    # 已结束的会话不能再作答
    r = client.post(
        f"/api/vocab/practice/sessions/{session_id}/answers",
        json={"wordId": word_id, "correct": True, "wrongTimes": 0},
        headers=headers,
    )
    assert r.status_code == 400


def test_wrong_answer_goes_to_wrong_book_then_resolved(tmp_path) -> None:
    client = make_client(tmp_path)
    headers = register(client, "vocab4@openlair.dev")
    r = client.post("/api/vocab/practice/sessions", json={"bookId": BOOK_ID, "mode": "spell"}, headers=headers)
    session_id = r.json()["data"]["id"]
    word_id = r.json()["data"]["queue"][0]["id"]

    # 打错两次：Again → 进错词本
    r = client.post(
        f"/api/vocab/practice/sessions/{session_id}/answers",
        json={"wordId": word_id, "correct": False, "wrongTimes": 2, "durationMs": 8000},
        headers=headers,
    )
    progress = r.json()["data"]["item"]
    assert progress["wrongActive"] is True
    assert progress["wrongCount"] == 2
    due = datetime.fromisoformat(progress["due"].replace("Z", "+00:00"))
    assert due < datetime.now(UTC) + timedelta(days=2)  # Again 间隔短

    r = client.get("/api/vocab/review/wrong", headers=headers)
    wrong_words = r.json()["data"]["words"]
    assert [w["id"] for w in wrong_words] == [word_id]
    assert wrong_words[0]["progress"]["wrongActive"] is True

    # 复习打对：自动移出错词本
    r = client.post("/api/vocab/practice/sessions", json={"bookId": BOOK_ID, "mode": "follow"}, headers=headers)
    session_id2 = r.json()["data"]["id"]
    client.post(
        f"/api/vocab/practice/sessions/{session_id2}/answers",
        json={"wordId": word_id, "correct": True, "wrongTimes": 0},
        headers=headers,
    )
    r = client.get("/api/vocab/review/wrong", headers=headers)
    assert r.json()["data"]["words"] == []


def test_review_queue_serves_due_words_before_new(tmp_path) -> None:
    client = make_client(tmp_path)
    headers = register(client, "vocab5@openlair.dev")
    r = client.post("/api/vocab/practice/sessions", json={"bookId": BOOK_ID, "mode": "follow"}, headers=headers)
    session_id = r.json()["data"]["id"]
    first_word = r.json()["data"]["queue"][0]["id"]
    r = client.post(
        f"/api/vocab/practice/sessions/{session_id}/answers",
        json={"wordId": first_word, "correct": True, "wrongTimes": 0},
        headers=headers,
    )
    progress_id = r.json()["data"]["item"]["wordId"]

    # 模拟时间流逝：due 置为过去 → 新会话的复习池应包含它且排在新词前
    force_due(client, 1, datetime.now(UTC) - timedelta(hours=1))
    r = client.post("/api/vocab/practice/sessions", json={"bookId": BOOK_ID, "mode": "follow"}, headers=headers)
    queue = r.json()["data"]["queue"]
    assert queue[0]["id"] == first_word
    assert queue[0]["progress"]["wordId"] == first_word


# ---------- 生词管理 ----------

def test_master_and_collect_on_unlearned_word(tmp_path) -> None:
    client = make_client(tmp_path)
    headers = register(client, "vocab6@openlair.dev")

    # 未学过的词直接标记已掌握：创建进度并跳过排课
    r = client.put("/api/vocab/progress/2", json={"status": "mastered"}, headers=headers)
    assert r.status_code == 200
    assert r.json()["data"]["item"]["status"] == "mastered"

    r = client.post("/api/vocab/practice/sessions", json={"bookId": BOOK_ID, "mode": "follow"}, headers=headers)
    queue_ids = [item["id"] for item in r.json()["data"]["queue"]]
    assert 2 not in queue_ids and len(queue_ids) == 7

    # 收藏 / 移出错词本
    r = client.put("/api/vocab/progress/3", json={"collected": True}, headers=headers)
    assert r.json()["data"]["item"]["collected"] is True
    r = client.get("/api/vocab/review/collect", headers=headers)
    assert [w["id"] for w in r.json()["data"]["words"]] == [3]

    client.put("/api/vocab/progress/3", json={"collected": False}, headers=headers)
    r = client.get("/api/vocab/review/collect", headers=headers)
    assert r.json()["data"]["words"] == []


# ---------- 错词本 / 收藏 直接练习 ----------

def test_wrong_book_practice(tmp_path) -> None:
    client = make_client(tmp_path)
    headers = register(client, "vocab8@openlair.dev")
    # 打错一个词进错词本
    r = client.post("/api/vocab/practice/sessions", json={"bookId": BOOK_ID, "mode": "follow"}, headers=headers)
    session_id = r.json()["data"]["id"]
    word_id = r.json()["data"]["queue"][0]["id"]
    client.post(
        f"/api/vocab/practice/sessions/{session_id}/answers",
        json={"wordId": word_id, "correct": False, "wrongTimes": 1},
        headers=headers,
    )
    # source=wrong 直接开练错词：bookId 忽略可为 0
    r = client.post(
        "/api/vocab/practice/sessions",
        json={"bookId": 0, "mode": "spell", "source": "wrong"},
        headers=headers,
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["bookName"] == "错词本" and data["source"] == "wrong" and data["bookId"] == 0
    assert [w["id"] for w in data["queue"]] == [word_id]
    assert data["queue"][0]["progress"]["wrongActive"] is True
    # 复习打对 → 自动移出错词本
    r = client.post(
        f"/api/vocab/practice/sessions/{data['id']}/answers",
        json={"wordId": word_id, "correct": True, "wrongTimes": 0},
        headers=headers,
    )
    assert r.status_code == 200
    r = client.get("/api/vocab/review/wrong", headers=headers)
    assert r.json()["data"]["words"] == []
    # 错词清空后再开 → 优雅拒绝
    r = client.post("/api/vocab/practice/sessions", json={"bookId": 0, "mode": "follow", "source": "wrong"}, headers=headers)
    assert r.status_code == 400


def test_collect_practice(tmp_path) -> None:
    client = make_client(tmp_path)
    headers = register(client, "vocab9@openlair.dev")
    client.put("/api/vocab/progress/4", json={"collected": True}, headers=headers)
    r = client.post(
        "/api/vocab/practice/sessions",
        json={"bookId": 0, "mode": "follow", "source": "collect"},
        headers=headers,
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["bookName"] == "收藏复习"
    assert [w["id"] for w in data["queue"]] == [4]


def test_start_session_returns_book_name_and_validates_source(tmp_path) -> None:
    client = make_client(tmp_path)
    headers = register(client, "vocab10@openlair.dev")
    r = client.post("/api/vocab/practice/sessions", json={"bookId": BOOK_ID, "mode": "follow"}, headers=headers)
    data = r.json()["data"]
    assert data["bookName"] == "演示词书" and data["source"] == "book"
    r = client.post("/api/vocab/practice/sessions", json={"bookId": BOOK_ID, "mode": "follow", "source": "bad"}, headers=headers)
    assert r.status_code == 400


def test_stats_accepts_tz_offset(tmp_path) -> None:
    client = make_client(tmp_path)
    headers = register(client, "vocab11@openlair.dev")
    r = client.get("/api/vocab/stats", params={"tzOffset": 480}, headers=headers)
    assert r.status_code == 200
    assert r.json()["data"]["today"]["sessions"] == 0


# ---------- 校验与鉴权 ----------

def test_session_validation_errors(tmp_path) -> None:
    client = make_client(tmp_path)
    headers = register(client, "vocab7@openlair.dev")

    r = client.post("/api/vocab/practice/sessions", json={"bookId": BOOK_ID, "mode": "bad"}, headers=headers)
    assert r.status_code == 400

    r = client.post("/api/vocab/practice/sessions", json={"bookId": 999, "mode": "follow"}, headers=headers)
    assert r.status_code == 404

    r = client.post(
        "/api/vocab/practice/sessions/999/answers",
        json={"wordId": 1, "correct": True, "wrongTimes": 0},
        headers=headers,
    )
    assert r.status_code == 404

    r = client.get("/api/vocab/books/999/words", headers=headers)
    assert r.status_code == 404


def test_vocab_requires_auth(tmp_path) -> None:
    client = make_client(tmp_path)
    r = client.get("/api/vocab/books")
    assert r.status_code == 401
    assert r.json()["code"] == 401
