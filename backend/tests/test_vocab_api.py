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


# ---------- 词书导入（系统级 / 用户级） ----------

def test_user_import_visibility_and_delete(tmp_path) -> None:
    client = make_client(tmp_path)
    h1 = register(client, "imp1@openlair.dev")
    h2 = register(client, "imp2@openlair.dev")

    r = client.post(
        "/api/vocab/books/import",
        json={"name": "我的生词本", "scope": "user", "text": "serendipity\nubiquitous,无处不在\n### 注释行\n1234"},
        headers=h1,
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["imported"] == 2  # 注释与纯数字行被过滤
    book = data["book"]
    assert book["ownerId"] is not None and book["wordCount"] == 2

    book_id = book["id"]
    # 本人可见，他人不可见
    names1 = [b["name"] for b in client.get("/api/vocab/books", headers=h1).json()["data"]["books"]]
    names2 = [b["name"] for b in client.get("/api/vocab/books", headers=h2).json()["data"]["books"]]
    assert "我的生词本" in names1 and "我的生词本" not in names2
    # 他人访问单词/开课/删除都按不存在处理
    assert client.get(f"/api/vocab/books/{book_id}/words", headers=h2).status_code == 404
    r = client.post("/api/vocab/practice/sessions", json={"bookId": book_id, "mode": "follow"}, headers=h2)
    assert r.status_code == 404
    assert client.delete(f"/api/vocab/books/{book_id}", headers=h2).status_code == 404
    # 本人可删除
    assert client.delete(f"/api/vocab/books/{book_id}", headers=h1).json()["data"]["ok"] is True
    assert client.get(f"/api/vocab/books/{book_id}/words", headers=h1).status_code == 404


def test_system_import_permission(tmp_path) -> None:
    client = make_client(tmp_path)
    h_admin = login(client, "test1@openlair.dev")  # user 1 = 站长
    h_other = register(client, "imp3@openlair.dev")

    r = client.post(
        "/api/vocab/books/import",
        json={"name": "站长的精选词书", "scope": "system", "text": "ephemeral,短暂的"},
        headers=h_other,
    )
    assert r.status_code == 403

    r = client.post(
        "/api/vocab/books/import",
        json={"name": "站长的精选词书", "scope": "system", "text": "ephemeral,短暂的"},
        headers=h_admin,
    )
    assert r.status_code == 200
    book = r.json()["data"]["book"]
    assert book["ownerId"] is None  # 系统级

    # 系统词书人人可见
    names = [b["name"] for b in client.get("/api/vocab/books", headers=h_other).json()["data"]["books"]]
    assert "站长的精选词书" in names
    # 他人不能删系统词书，站长可以
    assert client.delete(f"/api/vocab/books/{book['id']}", headers=h_other).status_code == 403
    assert client.delete(f"/api/vocab/books/{book['id']}", headers=h_admin).json()["data"]["ok"] is True


def test_import_ecdict_and_dedup(tmp_path) -> None:
    client = make_client(tmp_path)
    headers = register(client, "imp4@openlair.dev")
    ecdict_text = (
        "word,phonetic,definition,translation,pos,collins,oxford,tag,bnc,frq,exchange,detail,audio\n"
        'flabbergast,"flæbəɡɑːst","",'
        '"vt. 使大吃一惊\\nn. 吃惊","",0,0,"",0,0,"0:","","",\n'
        'multi word phrase,"","",  "n. 词组","",0,0,"",0,0,"0:","","",\n'
    )
    r = client.post(
        "/api/vocab/books/import",
        json={"name": "ECDICT 测试书", "scope": "user", "text": ecdict_text},
        headers=headers,
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["imported"] == 1  # 词组被过滤
    assert data["format"] == "ecdict"
    book_id = data["book"]["id"]

    words = client.get(f"/api/vocab/books/{book_id}/words", headers=headers).json()["data"]["words"]
    assert words[0]["word"] == "flabbergast"
    assert words[0]["phoneticUk"] == "flæbəɡɑːst"
    assert words[0]["translations"][0]["pos"] == "vt."

    # 重复导入：全局词条去重，不新增词条
    r2 = client.post(
        "/api/vocab/books/import",
        json={"name": "ECDICT 测试书2", "scope": "user", "text": "flabbergast\nbrandnew,全新"},
        headers=headers,
    )
    assert r2.json()["data"]["newWords"] == 1  # 只有 brandnew 是新词条

    # 解析不到单词 → 400
    r3 = client.post(
        "/api/vocab/books/import",
        json={"name": "空书", "scope": "user", "text": "### 只有注释\n,,, "},
        headers=headers,
    )
    assert r3.status_code == 400


def test_import_anki_format(tmp_path) -> None:
    """Anki 导出文本（Notes in Plain Text）：#deck 自动命名 + <br> 拆释义 + 标签列忽略。"""
    client = make_client(tmp_path)
    headers = register(client, "imp5@openlair.dev")
    anki_text = (
        "#separator:tab\n"
        "#html:true\n"
        "#deck:我的 Anki 牌组\n"
        "obliterate\tvt. 抹掉<br>n. 毁灭者\t考研 雅思\n"
        "ephemeral\tadj. 短暂的\n"
    )
    r = client.post("/api/vocab/books/import", json={"scope": "user", "text": anki_text}, headers=headers)
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["format"] == "anki"
    assert data["book"]["name"] == "我的 Anki 牌组"  # 未填名称时自动取 #deck
    assert data["imported"] == 2
    book_id = data["book"]["id"]

    words = client.get(f"/api/vocab/books/{book_id}/words", headers=headers).json()["data"]["words"]
    by_word = {w["word"]: w for w in words}
    assert by_word["obliterate"]["translations"] == [
        {"pos": "vt.", "cn": "抹掉"},
        {"pos": "n.", "cn": "毁灭者"},
    ]
    assert by_word["ephemeral"]["translations"][0]["cn"] == "短暂的"  # 标签列没有混进释义


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
