"""词汇打字练习服务：智能排课（FSRS + 错次自动映射）、会话管理、生词管理、统计。

调度语义（py-fsrs v6，空学习步 = 纯天级排课）：
- Rating 由作答质量自动推导，用户无感评分：答错=Again；答对但打错过=Hard；一次全对=Good
- 进度按 (user, word) 全局唯一，跨词书不重复学；book_id 只记首次学习来源
- 复习池 = due <= now 且 learning；新词池 = 词书内无进度记录的词
"""

from datetime import UTC, datetime, timedelta

from fsrs import Card, Rating, Scheduler, State

from app.core.envelope import ApiError
from app.models.vocab import VocabBook, VocabPracticeSession, VocabWord, VocabWordProgress
from app.repositories.vocab import VocabRepository
from app.services import iso_z

MODES = ("follow", "dictation", "self_test", "spell")
SOURCES = ("book", "wrong", "collect")  # book 词书排课 / wrong 错词本 / collect 收藏
STATUSES = ("learning", "mastered")

DEFAULT_NEW_LIMIT = 10  # 每次练习的新词配额
DEFAULT_REVIEW_LIMIT = 30  # 每次练习的到期复习配额
MAX_QUEUE_LIMIT = 100

# 练习会话/进度记录允许更新的字段白名单
_SESSION_PATCH_KEYS = {"total_count", "correct_count", "wrong_count", "duration_sec", "finished_at"}


class VocabService:
    def __init__(self, repo: VocabRepository) -> None:
        self._repo = repo
        # 空学习步：作答后直接按天排课（分钟级巩固交给错词本的前端会话内重练）
        self._scheduler = Scheduler(learning_steps=(), relearning_steps=())

    # ---------- 词书 ----------

    def list_books(self, user_id: int) -> dict:
        now = self._utcnow()
        books = self._repo.list_books()
        word_counts = self._repo.count_words_by_book()
        stats = self._repo.book_progress_stats(user_id, now)
        dtos = []
        for b in books:
            s = stats.get(b.id, {})
            dtos.append(
                {
                    "id": b.id,
                    "slug": b.slug,
                    "name": b.name,
                    "lang": b.lang,
                    "emoji": b.emoji,
                    "description": b.description,
                    "wordCount": word_counts.get(b.id, 0),
                    "learning": s.get("learning", 0),
                    "mastered": s.get("mastered", 0),
                    "due": s.get("due", 0),
                    "createdAt": iso_z(b.created_at),
                }
            )
        return {"books": dtos}

    # ---------- 词书单词 ----------

    def list_book_words(self, book_id: int, limit: int, offset: int) -> dict:
        book = self._repo.get_book(book_id)
        if book is None:
            raise ApiError(404, "词书不存在")
        limit = max(1, min(limit, 500))
        offset = max(0, offset)
        words = self._repo.list_words_by_book(book_id, limit=limit, offset=offset)
        return {"total": book.word_count, "words": [self._word_dto(w) for w in words]}

    # ---------- 练习会话 ----------

    def start_session(
        self,
        *,
        user_id: int,
        book_id: int,
        mode: str,
        new_limit: int | None = None,
        review_limit: int | None = None,
        source: str = "book",
    ) -> dict:
        if mode not in MODES:
            raise ApiError(400, "不支持的练习模式")
        if source not in SOURCES:
            raise ApiError(400, "不支持的练习来源")
        now = self._utcnow()
        review_limit = max(1, min(review_limit or DEFAULT_REVIEW_LIMIT, MAX_QUEUE_LIMIT))
        new_limit = max(0, min(new_limit if new_limit is not None else DEFAULT_NEW_LIMIT, MAX_QUEUE_LIMIT))

        queue: list[dict] = []
        book = None
        if source == "wrong":
            # 错词本练习：全部来自当前错词（按最近错误倒序），答对自动移出错词本
            for p in self._repo.list_wrong_progress(user_id, limit=review_limit):
                w = self._repo.get_word(p.word_id)
                if w is not None:
                    queue.append(self._queue_item(w, p))
            book_name = "错词本"
        elif source == "collect":
            # 收藏复习
            for p in self._repo.list_collected_progress(user_id, limit=review_limit):
                w = self._repo.get_word(p.word_id)
                if w is not None:
                    queue.append(self._queue_item(w, p))
            book_name = "收藏复习"
        else:
            book = self._repo.get_book(book_id)
            if book is None:
                raise ApiError(404, "词书不存在")
            due_rows = self._repo.list_due_progress(user_id, now, limit=review_limit)
            due_words = {w.id: w for w in self._repo.list_words_by_ids([p.word_id for p in due_rows])}
            for p in due_rows:
                word = due_words.get(p.word_id)
                if word is not None:
                    queue.append(self._queue_item(word, p))
            if new_limit > 0:
                for w in self._repo.list_new_words(book_id, user_id, limit=new_limit):
                    queue.append(self._queue_item(w, None))
            book_name = book.name
        if not queue:
            raise ApiError(400, "暂无可练习的单词（到期复习与新词均为空）" if source == "book" else "暂无可练习的单词")

        session = self._repo.create_session(user_id=user_id, book_id=book.id if book else 0, mode=mode)
        return {"id": session.id, "bookId": session.book_id, "bookName": book_name, "source": source, "mode": mode, "queue": queue}

    def submit_answer(self, *, user_id: int, session_id: int, word_id: int, correct: bool, wrong_times: int, duration_ms: int) -> dict:
        session = self._repo.get_session(session_id)
        if session is None or session.user_id != user_id:
            raise ApiError(404, "练习会话不存在")
        if session.finished_at is not None:
            raise ApiError(400, "会话已结束")
        word = self._repo.get_word(word_id)
        if word is None:
            raise ApiError(404, "单词不存在")

        correct = bool(correct)
        # 失败作答错次至少记 1（自测选错时前端可能不报击键错误数）
        wrong_times = max(0, int(wrong_times)) if correct else max(1, int(wrong_times))
        now = self._utcnow()

        progress = self._repo.get_progress(user_id, word_id)
        if progress is None:
            progress = self._repo.create_progress(user_id=user_id, word_id=word_id, book_id=session.book_id)

        # 错次自动映射 Rating：答错=Again；答对但打错过=Hard；一次全对=Good
        if not correct:
            rating = Rating.Again
        elif wrong_times > 0:
            rating = Rating.Hard
        else:
            rating = Rating.Good
        card, _ = self._scheduler.review_card(self._card_from(progress), rating, now)

        passed = correct and wrong_times == 0
        patch: dict = {
            "due": card.due,
            "stability": card.stability,
            "difficulty": card.difficulty,
            "state": int(card.state.value),
            "step": card.step,
            "last_review": card.last_review,
            "right_count": progress.right_count + (1 if passed else 0),
            "wrong_count": progress.wrong_count + wrong_times,
            "wrong_active": not passed,
        }
        if not passed:
            patch["last_wrong_at"] = now
        self._repo.update_progress(progress.id, patch)

        self._repo.update_session(
            session_id,
            {
                "total_count": session.total_count + 1,
                "correct_count": session.correct_count + (1 if passed else 0),
                "wrong_count": session.wrong_count + (0 if passed else 1),
            },
        )
        self._repo.create_log(
            user_id=user_id,
            session_id=session_id,
            word_id=word_id,
            mode=session.mode,
            is_correct=passed,
            wrong_times=wrong_times,
            duration_ms=max(0, int(duration_ms or 0)),
        )
        return {"item": self._progress_dto(self._repo.get_progress(user_id, word_id))}

    def finish_session(self, *, user_id: int, session_id: int, duration_sec: int) -> dict:
        session = self._repo.get_session(session_id)
        if session is None or session.user_id != user_id:
            raise ApiError(404, "练习会话不存在")
        updated = self._repo.update_session(
            session_id, {"duration_sec": max(0, int(duration_sec or 0)), "finished_at": self._utcnow()}
        )
        return {"item": self._session_dto(updated)}

    # ---------- 生词管理 ----------

    def list_wrong_words(self, user_id: int, limit: int = 200) -> dict:
        rows = self._repo.list_wrong_progress(user_id, limit=min(limit, 500))
        return {"words": self._progress_word_dtos(rows)}

    def list_collected_words(self, user_id: int, limit: int = 200) -> dict:
        rows = self._repo.list_collected_progress(user_id, limit=min(limit, 500))
        return {"words": self._progress_word_dtos(rows)}

    def update_progress(self, *, user_id: int, word_id: int, patch: dict) -> dict:
        progress = self._repo.get_progress(user_id, word_id)
        if progress is None:
            # 从未学过的词也可直接标记（如收藏、标记已掌握）
            progress = self._repo.create_progress(user_id=user_id, word_id=word_id)
        clean: dict = {}
        if patch.get("status") in STATUSES:
            clean["status"] = patch["status"]
        if "collected" in patch and patch["collected"] is not None:
            clean["collected"] = bool(patch["collected"])
        if patch.get("dismissWrong"):
            clean["wrong_active"] = False
        if clean:
            self._repo.update_progress(progress.id, clean)
        return {"item": self._progress_dto(self._repo.get_progress(user_id, word_id))}

    # ---------- 统计 ----------

    def stats(self, user_id: int, tz_offset: int = 0) -> dict:
        now = self._utcnow()
        # “今日”边界按客户端本地零点算：tz_offset 为本地相对 UTC 的分钟差（东区为正）。
        # 直接用 UTC 零点会让 UTC+8 用户早上 8 点前练的词算进“昨天”。
        tz_offset = max(-840, min(840, int(tz_offset or 0)))
        local_midnight_utc = (now + timedelta(minutes=tz_offset)).replace(hour=0, minute=0, second=0, microsecond=0)
        day_start = local_midnight_utc - timedelta(minutes=tz_offset)
        today_sessions = self._repo.list_sessions_since(user_id, day_start)
        all_sessions = self._repo.list_sessions_since(user_id, datetime(2000, 1, 1, tzinfo=UTC))
        progress_rows = self._repo.list_progress(user_id)
        learned = len(progress_rows)
        mastered = sum(1 for p in progress_rows if p.status == "mastered")
        due = sum(1 for p in progress_rows if p.status == "learning" and self._as_utc(p.due) is not None and self._as_utc(p.due) <= now)

        def _sum(rows: list[VocabPracticeSession]) -> dict:
            return {
                "sessions": len(rows),
                "words": sum(r.total_count for r in rows),
                "correct": sum(r.correct_count for r in rows),
                "wrong": sum(r.wrong_count for r in rows),
                "durationSec": sum(r.duration_sec for r in rows),
            }

        return {"today": _sum(today_sessions), "total": {**_sum(all_sessions), "learned": learned, "mastered": mastered, "due": due}}

    # ---------- 内部：FSRS 卡片转换 ----------

    @staticmethod
    def _utcnow() -> datetime:
        return datetime.now(UTC)

    @staticmethod
    def _as_utc(value: datetime | None) -> datetime | None:
        """SQLite 读回的 datetime 无 tzinfo，统一按 UTC 归一化（服务端统一存取 UTC）。"""
        if value is None:
            return None
        return value if value.tzinfo is not None else value.replace(tzinfo=UTC)

    def _card_from(self, progress: VocabWordProgress) -> Card:
        """从进度行重建 py-fsrs Card（字段平铺的反向操作）。state=0 为未复习哨兵 → 全新卡。"""
        if progress.state in (State.Learning.value, State.Review.value, State.Relearning.value) and progress.due is not None:
            return Card(
                state=State(progress.state),
                step=progress.step,
                stability=progress.stability,
                difficulty=progress.difficulty,
                due=self._as_utc(progress.due),
                last_review=self._as_utc(progress.last_review),
            )
        return Card()  # 尚未形成记忆状态的新卡

    # ---------- 内部：DTO ----------

    def _word_dto(self, w: VocabWord) -> dict:
        return {
            "id": w.id,
            "word": w.word,
            "phoneticUs": w.phonetic_us,
            "phoneticUk": w.phonetic_uk,
            "translations": w.translations or [],
            "sentences": w.sentences or [],
            "phrases": w.phrases or [],
            "synos": w.synos or [],
            "relWords": w.rel_words or {},
            "freq": w.freq,
        }

    def _progress_dto(self, p: VocabWordProgress | None) -> dict | None:
        if p is None:
            return None
        return {
            "wordId": p.word_id,
            "bookId": p.book_id,
            "status": p.status,
            "collected": p.collected,
            "wrongCount": p.wrong_count,
            "rightCount": p.right_count,
            "wrongActive": p.wrong_active,
            "due": iso_z(self._as_utc(p.due)) if p.due else None,
            "lastReview": iso_z(self._as_utc(p.last_review)) if p.last_review else None,
            "lastWrongAt": iso_z(self._as_utc(p.last_wrong_at)) if p.last_wrong_at else None,
            "state": p.state,
            "stability": p.stability,
            "difficulty": p.difficulty,
            "updatedAt": iso_z(self._as_utc(p.updated_at)),
        }

    def _queue_item(self, word: VocabWord, progress: VocabWordProgress | None) -> dict:
        item = self._word_dto(word)
        item["progress"] = self._progress_dto(progress)
        return item

    def _progress_word_dtos(self, rows: list[VocabWordProgress]) -> list[dict]:
        words = {w.id: w for w in self._repo.list_words_by_ids([p.word_id for p in rows])}
        dtos: list[dict] = []
        for p in rows:
            word = words.get(p.word_id)
            if word is not None:
                dtos.append(self._queue_item(word, p))
        return dtos

    def _session_dto(self, s: VocabPracticeSession) -> dict:
        return {
            "id": s.id,
            "bookId": s.book_id,
            "mode": s.mode,
            "totalCount": s.total_count,
            "correctCount": s.correct_count,
            "wrongCount": s.wrong_count,
            "durationSec": s.duration_sec,
            "finishedAt": iso_z(self._as_utc(s.finished_at)) if s.finished_at else None,
            "createdAt": iso_z(self._as_utc(s.created_at)),
        }
