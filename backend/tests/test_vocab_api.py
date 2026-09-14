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


def make_old_due_word(client: TestClient, word_id: int, days_ago: int = 3) -> None:
    """把一个词造成「几天前学过、现在到期」的状态。

    必须把 first_learned_at 也推到过去：后端「今日复习」的口径是
    `last_review >= 今日零点 且 首次学习更早`，只改 due 的话它仍会被算成今天新学的词。
    """
    now = datetime.now(UTC)
    with client.app.state.session_factory() as session:
        row = session.query(VocabWordProgress).filter(VocabWordProgress.word_id == word_id).one()
        row.status = "learning"
        row.first_learned_at = now - timedelta(days=days_ago)
        row.last_review = now - timedelta(days=days_ago)
        row.due = now - timedelta(hours=1)
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


# ---------- 词书详情（汇总 / 筛选 / 搜索 / 排序 / 模式覆盖） ----------

def test_book_detail_summary_filters_and_practice_coverage(tmp_path) -> None:
    client = make_client(tmp_path)
    headers = register(client, "vocab20@openlair.dev")

    # 初始汇总：8 个词全未学
    s = client.get(f"/api/vocab/books/{BOOK_ID}/summary", headers=headers).json()["data"]
    assert s["total"] == 8 and s["unlearned"] == 8
    assert s["learned"] == 0 and s["wrong"] == 0 and s["collected"] == 0
    assert s["book"]["slug"] == "demo"

    # 未学筛选 = 全部；每词带 progress(null) 与 practice(全 0)
    data = client.get(
        f"/api/vocab/books/{BOOK_ID}/words", params={"status": "unlearned", "limit": 50}, headers=headers
    ).json()["data"]
    assert data["total"] == 8 and data["totalAll"] == 8
    assert data["words"][0]["progress"] is None
    assert data["words"][0]["practice"] == {
        "follow": 0,
        "dictation": 0,
        "selfTest": 0,
        "spell": 0,
        "totalCount": 0,
        "lastAt": None,
    }

    # 跟打一轮：第一个词一次全对，第二个词错 2 次
    session = client.post(
        "/api/vocab/practice/sessions", json={"bookId": BOOK_ID, "mode": "follow"}, headers=headers
    ).json()["data"]
    session_id = session["id"]
    w1, w2 = session["queue"][0]["id"], session["queue"][1]["id"]
    client.post(
        f"/api/vocab/practice/sessions/{session_id}/answers",
        json={"wordId": w1, "correct": True, "wrongTimes": 0},
        headers=headers,
    )
    client.post(
        f"/api/vocab/practice/sessions/{session_id}/answers",
        json={"wordId": w2, "correct": False, "wrongTimes": 2},
        headers=headers,
    )

    # 听写一轮：练一个新词，验证「被听写过」这一维度
    dictation = client.post(
        "/api/vocab/practice/sessions", json={"bookId": BOOK_ID, "mode": "dictation"}, headers=headers
    ).json()["data"]
    w3 = dictation["queue"][0]["id"]
    client.post(
        f"/api/vocab/practice/sessions/{dictation['id']}/answers",
        json={"wordId": w3, "correct": True, "wrongTimes": 0},
        headers=headers,
    )

    # 状态筛选：学习中 3 个、错词 1 个（错词能看到错次）
    learning = client.get(
        f"/api/vocab/books/{BOOK_ID}/words", params={"status": "learning", "limit": 50}, headers=headers
    ).json()["data"]
    assert learning["total"] == 3
    wrong = client.get(
        f"/api/vocab/books/{BOOK_ID}/words", params={"status": "wrong", "limit": 50}, headers=headers
    ).json()["data"]
    assert wrong["total"] == 1 and wrong["words"][0]["id"] == w2
    assert wrong["words"][0]["progress"]["wrongCount"] == 2

    # 关键词搜索（大小写不敏感）
    hit = client.get(
        f"/api/vocab/books/{BOOK_ID}/words", params={"keyword": "CAN"}, headers=headers
    ).json()["data"]
    assert hit["total"] == 1 and hit["words"][0]["word"] == "cancel"

    # 排序：错次最多的排最前
    sorted_rows = client.get(
        f"/api/vocab/books/{BOOK_ID}/words", params={"sort": "wrong", "limit": 3}, headers=headers
    ).json()["data"]
    assert sorted_rows["words"][0]["id"] == w2

    # 模式覆盖：w1 跟打过 1 次、w3 听写过 1 次
    rows = client.get(f"/api/vocab/books/{BOOK_ID}/words", params={"limit": 50}, headers=headers).json()["data"]["words"]
    by_id = {w["id"]: w for w in rows}
    assert by_id[w1]["practice"]["follow"] == 1 and by_id[w1]["practice"]["totalCount"] == 1
    assert by_id[w1]["practice"]["lastAt"] is not None
    assert by_id[w2]["practice"]["follow"] == 1
    assert by_id[w3]["practice"]["dictation"] == 1 and by_id[w3]["practice"]["follow"] == 0

    # 汇总同步更新：已学 3、未学 5
    s2 = client.get(f"/api/vocab/books/{BOOK_ID}/summary", headers=headers).json()["data"]
    assert s2["learned"] == 3 and s2["learning"] == 3 and s2["wrong"] == 1 and s2["unlearned"] == 5

    # 收藏后可被 collected 筛选命中
    client.put(f"/api/vocab/progress/{w1}", json={"collected": True}, headers=headers)
    collected = client.get(
        f"/api/vocab/books/{BOOK_ID}/words", params={"status": "collected", "limit": 50}, headers=headers
    ).json()["data"]
    assert collected["total"] == 1 and collected["words"][0]["id"] == w1
    s3 = client.get(f"/api/vocab/books/{BOOK_ID}/summary", headers=headers).json()["data"]
    assert s3["collected"] == 1

    # 非法筛选/排序值回退默认，不报错
    fallback = client.get(
        f"/api/vocab/books/{BOOK_ID}/words", params={"status": "bogus", "sort": "bogus"}, headers=headers
    ).json()["data"]
    assert fallback["total"] == 8


# ---------- 每日背词目标 ----------

def test_daily_goal_defaults_then_update(tmp_path) -> None:
    """未设过目标时回缺省 10/30 且 updatedAt 为 null；PUT 后落库并回读。"""
    client = make_client(tmp_path)
    headers = register(client, "goal1@openlair.dev")

    r = client.get("/api/vocab/daily-goal", headers=headers)
    assert r.status_code == 200
    data = r.json()["data"]
    assert data == {
        "newTarget": 10,
        "reviewTarget": 30,
        "todayNew": 0,
        "todayReviewed": 0,
        "remaining": 10,
        "achieved": False,
        "reviewRemaining": 30,
        "reviewAchieved": False,
        "updatedAt": None,  # 从未改过 → 无行
    }

    r = client.put("/api/vocab/daily-goal", json={"newTarget": 20}, headers=headers)
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["newTarget"] == 20 and data["reviewTarget"] == 30  # 未传的字段保持
    assert data["remaining"] == 20 and data["achieved"] is False
    assert data["updatedAt"] is not None

    # 再改 reviewTarget：仍是一条行（user_id 唯一，upsert）
    data = client.put("/api/vocab/daily-goal", json={"reviewTarget": 40}, headers=headers).json()["data"]
    assert data["newTarget"] == 20 and data["reviewTarget"] == 40

    r = client.get("/api/vocab/daily-goal", headers=headers)
    assert r.json()["data"]["newTarget"] == 20 and r.json()["data"]["reviewTarget"] == 40


def test_daily_goal_rejects_bad_payload(tmp_path) -> None:
    client = make_client(tmp_path)
    headers = register(client, "goal2@openlair.dev")

    # 空请求体：没有需要更新的目标
    r = client.put("/api/vocab/daily-goal", json={}, headers=headers)
    assert r.status_code == 400
    assert r.json()["code"] == 400

    # 越界走统一信封的 400（区间校验在服务层，不是 Pydantic 的 422 裸 detail）——
    # 这样前端能和 mock 一样拿到 data.message 里的中文提示
    for payload in ({"newTarget": 0}, {"newTarget": 101}, {"reviewTarget": 0}, {"reviewTarget": 101}):
        r = client.put("/api/vocab/daily-goal", json=payload, headers=headers)
        assert r.status_code == 400, payload
        assert r.json()["code"] == 400
        assert r.json()["message"] == "每日目标需在 1-100 之间"

    # 被拒后目标不变
    assert client.get("/api/vocab/daily-goal", headers=headers).json()["data"]["newTarget"] == 10


def test_daily_goal_caps_new_words_and_blocks_when_achieved(tmp_path) -> None:
    """核心行为：目标改成 2 → 一节课只发 2 个新词；达标后再开课不再发新词。"""
    client = make_client(tmp_path)
    headers = register(client, "goal3@openlair.dev")
    client.put("/api/vocab/daily-goal", json={"newTarget": 2}, headers=headers)

    session = client.post(
        "/api/vocab/practice/sessions", json={"bookId": BOOK_ID, "mode": "follow"}, headers=headers
    ).json()["data"]
    assert len(session["queue"]) == 2  # 词书有 8 个词，但今日配额只有 2
    assert all(item["progress"] is None for item in session["queue"])

    for item in session["queue"]:
        client.post(
            f"/api/vocab/practice/sessions/{session['id']}/answers",
            json={"wordId": item["id"], "correct": True, "wrongTimes": 0},
            headers=headers,
        )

    data = client.get("/api/vocab/daily-goal", headers=headers).json()["data"]
    assert data["todayNew"] == 2 and data["remaining"] == 0 and data["achieved"] is True

    # 达标且没有到期复习 → 明确拒绝（而非含糊的「暂无可练习的单词」）
    r = client.post("/api/vocab/practice/sessions", json={"bookId": BOOK_ID, "mode": "follow"}, headers=headers)
    assert r.status_code == 400
    assert r.json()["message"] == "今日新词目标已完成，暂无到期复习"

    # stats 与目标口径一致
    stats = client.get("/api/vocab/stats", headers=headers).json()["data"]
    assert stats["today"]["newLearned"] == 2


def test_daily_goal_achieved_still_serves_due_reviews(tmp_path) -> None:
    """达标只挡新词，不挡到期复习。"""
    client = make_client(tmp_path)
    headers = register(client, "goal4@openlair.dev")
    client.put("/api/vocab/daily-goal", json={"newTarget": 1}, headers=headers)

    session = client.post(
        "/api/vocab/practice/sessions", json={"bookId": BOOK_ID, "mode": "follow"}, headers=headers
    ).json()["data"]
    assert len(session["queue"]) == 1
    word_id = session["queue"][0]["id"]
    client.post(
        f"/api/vocab/practice/sessions/{session['id']}/answers",
        json={"wordId": word_id, "correct": True, "wrongTimes": 0},
        headers=headers,
    )
    assert client.get("/api/vocab/daily-goal", headers=headers).json()["data"]["remaining"] == 0

    # 模拟时间流逝让这个词到期 → 仍能开课，且队列里只有复习词
    with client.app.state.session_factory() as db:
        row = db.query(VocabWordProgress).filter(VocabWordProgress.word_id == word_id).one()
        row.due = datetime.now(UTC) - timedelta(hours=1)
        db.commit()

    data = client.post(
        "/api/vocab/practice/sessions", json={"bookId": BOOK_ID, "mode": "follow"}, headers=headers
    ).json()["data"]
    assert [w["id"] for w in data["queue"]] == [word_id]
    assert data["queue"][0]["progress"] is not None  # 复习词带进度，不是新词

    goal = client.get("/api/vocab/daily-goal", headers=headers).json()["data"]
    assert goal["todayNew"] == 1 and goal["remaining"] == 0


def test_explicit_new_limit_overrides_daily_goal(tmp_path) -> None:
    """显式传 newLimit 时不受目标限制（留给「今天想多学一轮」）。"""
    client = make_client(tmp_path)
    headers = register(client, "goal5@openlair.dev")
    client.put("/api/vocab/daily-goal", json={"newTarget": 1}, headers=headers)

    session = client.post(
        "/api/vocab/practice/sessions", json={"bookId": BOOK_ID, "mode": "follow"}, headers=headers
    ).json()["data"]
    client.post(
        f"/api/vocab/practice/sessions/{session['id']}/answers",
        json={"wordId": session["queue"][0]["id"], "correct": True, "wrongTimes": 0},
        headers=headers,
    )
    assert client.get("/api/vocab/daily-goal", headers=headers).json()["data"]["remaining"] == 0

    # 目标已满，但显式要 5 个新词照样给
    forced = client.post(
        "/api/vocab/practice/sessions",
        json={"bookId": BOOK_ID, "mode": "follow", "newLimit": 5},
        headers=headers,
    ).json()["data"]
    assert len(forced["queue"]) == 5


def test_collect_only_progress_does_not_count_as_learned(tmp_path) -> None:
    """只收藏（没做过题）不该计入「今日已记」；真正作答后才计入。"""
    client = make_client(tmp_path)
    headers = register(client, "goal6@openlair.dev")

    client.put("/api/vocab/progress/5", json={"collected": True}, headers=headers)
    assert client.get("/api/vocab/daily-goal", headers=headers).json()["data"]["todayNew"] == 0

    # 通过收藏池真正练一次这个词
    session = client.post(
        "/api/vocab/practice/sessions", json={"bookId": 0, "mode": "follow", "source": "collect"}, headers=headers
    ).json()["data"]
    assert [w["id"] for w in session["queue"]] == [5]
    client.post(
        f"/api/vocab/practice/sessions/{session['id']}/answers",
        json={"wordId": 5, "correct": True, "wrongTimes": 0},
        headers=headers,
    )

    data = client.get("/api/vocab/daily-goal", headers=headers).json()["data"]
    assert data["todayNew"] == 1 and data["remaining"] == 9

    # 标记已掌握也不计入（同一个词第二次不会重复计数）
    client.put("/api/vocab/progress/6", json={"status": "mastered"}, headers=headers)
    assert client.get("/api/vocab/daily-goal", headers=headers).json()["data"]["todayNew"] == 1


def test_daily_goal_caps_due_reviews_per_day(tmp_path) -> None:
    """复习目标与新增目标对称：按「每日累计剩余量」发到期复习，两侧都达标后明确拒绝。"""
    client = make_client(tmp_path)
    headers = register(client, "goal10@openlair.dev")
    client.put("/api/vocab/daily-goal", json={"newTarget": 1, "reviewTarget": 2}, headers=headers)

    def start(**extra) -> dict:
        return client.post(
            "/api/vocab/practice/sessions",
            json={"bookId": BOOK_ID, "mode": "follow", **extra},
            headers=headers,
        ).json()["data"]

    def answer_all(session: dict) -> None:
        for item in session["queue"]:
            client.post(
                f"/api/vocab/practice/sessions/{session['id']}/answers",
                json={"wordId": item["id"], "correct": True, "wrongTimes": 0},
                headers=headers,
            )

    # ① 今天新学 1 个词并留着 —— 用它把「每日新词目标」用满（todayNew=1, 目标=1）
    first = start(newLimit=1)
    answer_all(first)

    # ② 再用显式 newLimit 学 3 个（绕过目标），然后把它们改造成「几天前学过、现在到期」
    session = start(newLimit=3)
    assert len(session["queue"]) == 3
    answer_all(session)
    for item in session["queue"]:
        make_old_due_word(client, item["id"])

    goal = client.get("/api/vocab/daily-goal", headers=headers).json()["data"]
    assert goal["todayNew"] == 1  # 那 3 个已被改造成「老词」，不再算今天新学
    assert goal["todayReviewed"] == 0
    assert goal["reviewRemaining"] == 2 and goal["reviewAchieved"] is False

    # ③ 到期 3 条，但复习目标只剩 2 → 只发 2 条复习，且没有新词（新词额度已满）
    data = start()
    assert len(data["queue"]) == 2
    assert all(w["progress"] is not None for w in data["queue"])  # 全是复习词，不是新词
    answer_all(data)

    goal = client.get("/api/vocab/daily-goal", headers=headers).json()["data"]
    assert goal["todayReviewed"] == 2 and goal["reviewAchieved"] is True and goal["reviewRemaining"] == 0

    # ④ 两侧都达标 → 明确拒绝（而不是含糊的「暂无可练习的单词」）；此时其实还剩 1 条到期
    r = client.post("/api/vocab/practice/sessions", json={"bookId": BOOK_ID, "mode": "follow"}, headers=headers)
    assert r.status_code == 400
    assert r.json()["message"] == "今日新词与复习目标均已完成"


def test_explicit_review_limit_zero_serves_new_words_only(tmp_path) -> None:
    """显式 reviewLimit=0 表示「只要新词，别给我复习」，且不因此报错。"""
    client = make_client(tmp_path)
    headers = register(client, "goal11@openlair.dev")

    session = client.post(
        "/api/vocab/practice/sessions",
        json={"bookId": BOOK_ID, "mode": "follow", "newLimit": 3},
        headers=headers,
    ).json()["data"]
    for item in session["queue"]:
        client.post(
            f"/api/vocab/practice/sessions/{session['id']}/answers",
            json={"wordId": item["id"], "correct": True, "wrongTimes": 0},
            headers=headers,
        )
    for item in session["queue"]:
        make_old_due_word(client, item["id"])

    data = client.post(
        "/api/vocab/practice/sessions",
        json={"bookId": BOOK_ID, "mode": "follow", "newLimit": 2, "reviewLimit": 0},
        headers=headers,
    ).json()["data"]
    assert len(data["queue"]) == 2
    assert all(w["progress"] is None for w in data["queue"])  # 只要新词


def test_wrong_and_collect_ignore_daily_goal(tmp_path) -> None:
    """错词本/收藏是纠错通道，不受每日目标限制（复习目标设成 1 也照样全给）。"""
    client = make_client(tmp_path)
    headers = register(client, "goal12@openlair.dev")
    client.put("/api/vocab/daily-goal", json={"newTarget": 1, "reviewTarget": 1}, headers=headers)

    session = client.post(
        "/api/vocab/practice/sessions",
        json={"bookId": BOOK_ID, "mode": "follow", "newLimit": 3},
        headers=headers,
    ).json()["data"]
    queue = session["queue"]
    # 前两个打错 → 进错词本；第三个答对
    for item in queue[:2]:
        client.post(
            f"/api/vocab/practice/sessions/{session['id']}/answers",
            json={"wordId": item["id"], "correct": False, "wrongTimes": 1},
            headers=headers,
        )
    client.post(
        f"/api/vocab/practice/sessions/{session['id']}/answers",
        json={"wordId": queue[2]["id"], "correct": True, "wrongTimes": 0},
        headers=headers,
    )

    wrong = client.post(
        "/api/vocab/practice/sessions", json={"bookId": 0, "mode": "follow", "source": "wrong"}, headers=headers
    ).json()["data"]
    assert len(wrong["queue"]) == 2  # 复习目标只有 1，错词本仍给全
    assert all(w["progress"]["wrongActive"] for w in wrong["queue"])

    # 收藏池同理
    client.put(f"/api/vocab/progress/{queue[2]['id']}", json={"collected": True}, headers=headers)
    collected = client.post(
        "/api/vocab/practice/sessions", json={"bookId": 0, "mode": "follow", "source": "collect"}, headers=headers
    ).json()["data"]
    assert len(collected["queue"]) == 1


def test_daily_goal_isolated_per_user(tmp_path) -> None:
    client = make_client(tmp_path)
    h1 = register(client, "goal7@openlair.dev")
    h2 = register(client, "goal8@openlair.dev")

    client.put("/api/vocab/daily-goal", json={"newTarget": 20}, headers=h1)
    session = client.post(
        "/api/vocab/practice/sessions", json={"bookId": BOOK_ID, "mode": "follow"}, headers=h1
    ).json()["data"]
    client.post(
        f"/api/vocab/practice/sessions/{session['id']}/answers",
        json={"wordId": session["queue"][0]["id"], "correct": True, "wrongTimes": 0},
        headers=h1,
    )

    g1 = client.get("/api/vocab/daily-goal", headers=h1).json()["data"]
    g2 = client.get("/api/vocab/daily-goal", headers=h2).json()["data"]
    assert (g1["newTarget"], g1["todayNew"], g1["remaining"]) == (20, 1, 19)
    assert (g2["newTarget"], g2["todayNew"], g2["remaining"]) == (10, 0, 10)


def test_daily_goal_requires_auth_and_accepts_tz_offset(tmp_path) -> None:
    client = make_client(tmp_path)
    assert client.get("/api/vocab/daily-goal").status_code == 401
    headers = register(client, "goal9@openlair.dev")
    r = client.get("/api/vocab/daily-goal", params={"tzOffset": 480}, headers=headers)
    assert r.status_code == 200
    assert r.json()["data"]["todayNew"] == 0
    # 越界 tzOffset 由 Query 校验拦下
    assert client.get("/api/vocab/daily-goal", params={"tzOffset": 9999}, headers=headers).status_code == 422
