"""词汇打字练习服务：智能排课（FSRS + 错次自动映射）、会话管理、生词管理、词书导入、统计。

调度语义（py-fsrs v6，空学习步 = 纯天级排课）：
- Rating 由作答质量自动推导，用户无感评分：答错=Again；答对但打错过=Hard；一次全对=Good
- 「是否掌握」不看 FSRS 的 stability，而看显式的连续答对次数（correct_streak / required_streak）：
  首次识词判断答对 → 需要连对 3 次；答错 / 不认识 → 需要连对 5 次。答错把连续次数清零。
  达标即自动置 status='mastered'，此后不再排课。未达标期间 due 被压到「最晚次日」，
  否则 FSRS 的 2→11→45 天曲线会让「再复习两遍」变成两个月。
- 进度按 (user, word) 全局唯一，跨词书不重复学；book_id 只记首次学习来源
- 复习池 = due <= now 且 learning；新词池 = 词书内无进度记录的词
词书可见性：owner_id 为 NULL 的系统级词书人人可见；用户级词书仅导入者可见。
"""

import hashlib
from datetime import UTC, datetime, timedelta

from fsrs import Card, Rating, Scheduler, State

from app.core.envelope import ApiError
from app.models.vocab import VocabBook, VocabDailyGoal, VocabPracticeSession, VocabWord, VocabWordProgress
from app.repositories.vocab import VocabRepository
from app.services import iso_z
from app.services.vocab_import import parse_import_text

MODES = ("follow", "dictation", "self_test", "spell")
SOURCES = ("book", "wrong", "collect")  # book 词书排课 / wrong 错词本 / collect 收藏
SCOPES = ("system", "user")  # 导入级别：system 系统级（仅站长）/ user 用户级
STATUSES = ("learning", "mastered")
STATUS_FILTERS = ("all", "unlearned", "learning", "mastered", "wrong", "collected")  # 详情页状态筛选
WORD_SORTS = ("order", "freq", "wrong", "recent")  # 详情页排序：词书顺序 / 词频 / 错次 / 最近练习

DEFAULT_NEW_LIMIT = 10  # 每日新词目标缺省值（也是「每次练习新词配额」的兜底）
DEFAULT_REVIEW_LIMIT = 30  # 每日复习目标缺省值（也是「每次练习复习配额」的兜底）
MAX_QUEUE_LIMIT = 100
MIN_DAILY_TARGET = 1  # 每日目标下限（0 个没有意义，想「今天只复习」请把新词练完即可）
MAX_DAILY_TARGET = MAX_QUEUE_LIMIT

# ── 「掌握」的判定：连续答对次数（跨会话累计，不依赖 FSRS 的 stability）──────────
# 首次识词判断答对 → 认为比较熟悉，本次算第 1 次，之后再连对 2 次即掌握。
STREAK_FAMILIAR = 3
# 首次识词判断答错 / 点「不认识」/ 没把握 → 视为不熟悉，要连对 5 次才掌握。
STREAK_UNFAMILIAR = 5
# 未掌握期间的复习间隔上限：FSRS 会把间隔拉到 2→11→45 天，那样「再连对 2 次」
# 要等两个月才能发生。所以没达标前一律「最晚次日再来」，达标后才交回 FSRS 曲线。
UNMASTERED_MAX_INTERVAL = timedelta(days=1)

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
        books = self._repo.list_visible_books(user_id)
        word_counts = self._repo.count_words_by_book()
        stats = self._repo.book_progress_stats(user_id, now)
        return {"books": [self._book_dto(b, word_counts, stats) for b in books]}

    def import_book(self, *, user_id: int, name: str, scope: str, lang: str = "en", text: str) -> dict:
        """导入词书：system 系统级（仅站长，人人可见）/ user 用户级（仅本人可见）。

        文本自动识别 ECDICT CSV 与简单行格式（每行一个单词，可选释义）。
        词条按小写拼写全局去重 upsert，同一词可属多本词书。
        """
        if scope not in SCOPES:
            raise ApiError(400, "不支持的导入级别")
        if scope == "system" and user_id != 1:
            raise ApiError(403, "只有站长（首位用户）可以导入系统级词书")
        name = (name or "").strip()
        try:
            fmt, words, deck_name = parse_import_text(text or "")
        except ValueError as e:
            raise ApiError(400, str(e))
        if not name:
            name = deck_name  # Anki #deck 头可自动命名
        if not name:
            raise ApiError(400, "词书名称不能为空")
        if not words:
            raise ApiError(400, "未解析到有效单词，请检查格式（每行一个单词，可选“单词,释义”）")

        now = self._utcnow()
        prefix = "sys" if scope == "system" else f"u{user_id}"
        slug = f"{prefix}-{hashlib.md5((name + now.isoformat()).encode()).hexdigest()[:12]}"
        book = self._repo.create_book(
            slug=slug,
            name=name,
            lang=lang or "en",
            emoji="📚" if scope == "system" else "📖",
            description=f"导入格式 {fmt}",
            owner_id=None if scope == "system" else user_id,
        )
        word_map, new_count = self._repo.upsert_words(words)
        self._repo.replace_book_words(book.id, [word_map[p.word] for p in words])
        self._repo.set_word_count(book.id, len(words))
        return {"book": self._book_dto(book, {book.id: len(words)}, {}), "imported": len(words), "newWords": new_count, "format": fmt}

    def delete_book(self, *, user_id: int, book_id: int) -> dict:
        """删除词书（系统级仅站长；用户级仅本人）。词条全局池与学习进度保留。"""
        book = self._repo.get_book(book_id)
        if book is None:
            raise ApiError(404, "词书不存在")
        if book.owner_id is None:
            if user_id != 1:
                raise ApiError(403, "只有站长可以删除系统级词书")
        elif book.owner_id != user_id:
            raise ApiError(404, "词书不存在")  # 他人词书按不存在处理，不暴露存在性
        self._repo.delete_book(book_id)
        return {"ok": True}

    # ---------- 词书单词（详情页） ----------

    def list_book_words(
        self,
        book_id: int,
        limit: int,
        offset: int,
        user_id: int | None = None,
        status: str = "all",
        keyword: str = "",
        sort: str = "order",
    ) -> dict:
        """词书内单词列表：每词带本人进度与练习模式覆盖，支持状态筛选 / 关键词 / 排序。

        进度按 (user, word) 全局唯一，跨词书共享——同一词在多本词书里看到的是同一份状态。
        total 是当前筛选条件下的条数，totalAll 是词书总词数。
        """
        book = self._repo.get_book(book_id)
        if book is None or (user_id is not None and not self._visible(book, user_id)):
            raise ApiError(404, "词书不存在")
        limit = max(1, min(limit, 500))
        offset = max(0, offset)
        if status not in STATUS_FILTERS:
            status = "all"
        if sort not in WORD_SORTS:
            sort = "order"
        keyword = (keyword or "").strip()[:50]
        words, total = self._repo.list_book_words_page(
            book_id, user_id or 0, status=status, keyword=keyword, sort=sort, limit=limit, offset=offset
        )
        word_ids = [w.id for w in words]
        progress_map = self._repo.list_progress_by_word_ids(user_id, word_ids) if user_id else {}
        mode_stats = self._repo.practice_mode_stats(user_id, word_ids) if user_id else {}
        items: list[dict] = []
        for w in words:
            item = self._word_dto(w)
            item["progress"] = self._progress_dto(progress_map.get(w.id))
            item["practice"] = self._practice_dto(mode_stats.get(w.id))
            items.append(item)
        return {"total": total, "totalAll": book.word_count, "words": items}

    def book_summary(self, *, book_id: int, user_id: int) -> dict:
        """词书详情页头部汇总：词书信息 + 各状态计数（未学 = 总词数 - 已学）。"""
        book = self._repo.get_book(book_id)
        if book is None or not self._visible(book, user_id):
            raise ApiError(404, "词书不存在")
        counts = self._repo.book_summary_counts(user_id, book_id, self._utcnow())
        dto = self._book_dto(
            book,
            {book.id: counts["total"]},
            {book.id: {"learning": counts["learning"], "mastered": counts["mastered"], "due": counts["due"]}},
        )
        return {
            "book": dto,
            "total": counts["total"],
            "learned": counts["learned"],
            "learning": counts["learning"],
            "mastered": counts["mastered"],
            "due": counts["due"],
            "wrong": counts["wrong"],
            "collected": counts["collected"],
            "unlearned": max(0, counts["total"] - counts["learned"]),
        }

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
        tz_offset: int = 0,
    ) -> dict:
        if mode not in MODES:
            raise ApiError(400, "不支持的练习模式")
        if source not in SOURCES:
            raise ApiError(400, "不支持的练习来源")
        now = self._utcnow()
        # 词书排课：未显式指定配额时按「每日目标剩余量」发新词/复习 —— 「每天记 N 个、复习 M 个」
        # 由此自动生效（两者都达标后再开课就发不出东西了）。显式传值仍优先（留给「今天想多学一轮」）。
        # 错词本 / 收藏复习是「纠错」通道，刻意不受每日目标限制（也不为此多打两次聚合查询）。
        remaining_new: int | None = None
        remaining_review: int | None = None
        if source == "book":
            remaining_new, remaining_review = self._remaining_quota(user_id, now, tz_offset)

        if new_limit is None:
            new_limit = remaining_new if remaining_new is not None else 0
        new_limit = max(0, min(int(new_limit), MAX_QUEUE_LIMIT))

        if review_limit is None:
            review_limit = remaining_review if remaining_review is not None else DEFAULT_REVIEW_LIMIT
        review_limit = max(0, min(int(review_limit), MAX_QUEUE_LIMIT))

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
            if book is None or not self._visible(book, user_id):
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
            if source == "book":
                if remaining_new == 0 and remaining_review == 0:
                    raise ApiError(400, "今日新词与复习目标均已完成")
                if remaining_new == 0:
                    raise ApiError(400, "今日新词目标已完成，暂无到期复习")
                # remaining_review == 0 且还有新词额度时队列不可能为空，无需单列文案
            raise ApiError(400, "暂无可练习的单词（到期复习与新词均为空）" if source == "book" else "暂无可练习的单词")

        session = self._repo.create_session(user_id=user_id, book_id=book.id if book else 0, mode=mode)
        return {"id": session.id, "bookId": session.book_id, "bookName": book_name, "source": source, "mode": mode, "queue": queue}

    def submit_answer(
        self,
        *,
        user_id: int,
        session_id: int,
        word_id: int,
        correct: bool,
        wrong_times: int,
        duration_ms: int,
        tz_offset: int = 0,
    ) -> dict:
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
            # 首次作答即「记住这个词」的时点，与进度行同时落库
            progress = self._repo.create_progress(
                user_id=user_id, word_id=word_id, book_id=session.book_id, first_learned_at=now
            )
        # 已存在但从未真正作答过的进度行（例如当初只点了收藏/标记已掌握）→ 本次补上首学时间
        first_learn_time = now if progress.first_learned_at is None else None

        # 错次自动映射 Rating：答错=Again；答对但打错过=Hard；一次全对=Good
        if not correct:
            rating = Rating.Again
        elif wrong_times > 0:
            rating = Rating.Hard
        else:
            rating = Rating.Good
        card, _ = self._scheduler.review_card(self._card_from(progress), rating, now)

        passed = correct and wrong_times == 0

        # ── 连续答对次数：掌握与否的唯一判据（跨会话累计）────────────────────────
        # required_streak == 0 表示这个词还没做过「首次识词判断」——就把本次当那次判断：
        # 判断对 → 认为眼熟，需再连对 2 次（合计 3）；判断错 / 不认识 → 视为不熟悉，需连对 5 次。
        required_streak = progress.required_streak
        identify_result = progress.identify_result
        if required_streak <= 0:
            required_streak = STREAK_FAMILIAR if passed else STREAK_UNFAMILIAR
            identify_result = "know" if passed else "unsure"
            correct_streak = 1 if passed else 0
        # 之后每次复习：答对 +1；答错清零（严格重来，宁可多记几遍）
        else:
            correct_streak = progress.correct_streak + 1 if passed else 0
        # 达标 → 自动置已记住，此后不再排课
        mastered = required_streak > 0 and correct_streak >= required_streak

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
            "correct_streak": correct_streak,
            "required_streak": required_streak,
            "identify_result": identify_result,
        }
        if mastered:
            # 达标 → 自动置已记住，此后不进复习池；due 保留 FSRS 的正常天级值（仅作记录）
            patch["status"] = "mastered"
        elif self._as_utc(card.due) is not None:
            # 没达标就「最晚次日再来」：否则一次 Hard/Good 就排到 11 天甚至 45 天后，
            # 「再连对 2 次」根本轮不到发生，体感就变成「答对一次 = 已掌握」。
            # 用客户端本地零点算「次日」，保证晚上练的词第二天一早就到期（UTC 零点会算成当天 08:00）。
            cap = self._day_start(now, tz_offset) + UNMASTERED_MAX_INTERVAL
            if self._as_utc(card.due) > cap:
                patch["due"] = cap
        if not passed:
            patch["last_wrong_at"] = now
        if first_learn_time is not None:
            patch["first_learned_at"] = first_learn_time
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
        # 注意：这里刻意不写 first_learned_at —— 只收藏/只标已掌握不算「记住这个词」，
        # 否则「今日已记」会被虚高的空进度行灌水。首学时间只由 submit_answer 落。
        clean: dict = {}
        if patch.get("status") in STATUSES:
            clean["status"] = patch["status"]
            # 手动「取消记住」= 重新开始计数，否则下次答对会立刻被自动标回已记住。
            if patch["status"] == "learning":
                clean["correct_streak"] = 0
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
        # “今日”边界按客户端本地零点算（见 _day_start）。直接用 UTC 零点会让 UTC+8
        # 用户早上 8 点前练的词算进“昨天”。
        day_start = self._day_start(now, tz_offset)
        today_sessions = self._repo.list_sessions_since(user_id, day_start)
        all_sessions = self._repo.list_sessions_since(user_id, datetime(2000, 1, 1, tzinfo=UTC))
        # 词数口径来自进度表（首次真正作答的时刻），不是会话的作答次数 —— 后者同一次会话里
        # 一个词可能答多次，拿来当「记了多少个词」会虚高。
        today_learned = self._repo.count_today_learned(user_id, day_start)
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

        return {
            "today": {**_sum(today_sessions), **today_learned},
            "total": {**_sum(all_sessions), "learned": learned, "mastered": mastered, "due": due},
        }

    # ---------- 每日背词目标 ----------

    def daily_goal(self, user_id: int, tz_offset: int = 0) -> dict:
        """当前目标 + 今日进度。未设过目标的用户不建行，直接回退缺省值。"""
        now = self._utcnow()
        goal = self._repo.get_daily_goal(user_id)
        counts = self._repo.count_today_learned(user_id, self._day_start(now, tz_offset))
        return self._daily_goal_dto(goal, counts)

    def set_daily_goal(self, *, user_id: int, patch: dict, tz_offset: int = 0) -> dict:
        """改每日目标（upsert）。只接受出现的字段，改完回读带今日进度的完整视图。

        对进行中的练习会话无影响：已排好的队列不重排，下一节课按新目标算剩余量。
        """
        clean: dict = {}
        # 请求体是 camelCase（与前端契约一致），这里映射到列名。与 update_progress 的
        # 「dismissWrong」同样沿用「schema 直传、服务层认 camelCase」的既有做法。
        #
        # 区间校验刻意放在这里而不是 Pydantic 的 Field(ge=, le=)：schema 层越界会走 FastAPI
        # 默认的 422 裸 {"detail":[...]}（core/envelope.py 不接管 RequestValidationError，
        # laircli 依赖这个形状），前端拿不到统一信封里的中文 message。放服务层则统一 400 + 信封，
        # 与 mock 的 err(400, ...) 完全一致。
        for field, column in (("newTarget", "new_target"), ("reviewTarget", "review_target")):
            value = patch.get(field)
            if value is None:
                continue
            try:
                value = int(value)
            except (TypeError, ValueError):
                raise ApiError(400, "每日目标必须是整数")
            if not (MIN_DAILY_TARGET <= value <= MAX_DAILY_TARGET):
                raise ApiError(400, f"每日目标需在 {MIN_DAILY_TARGET}-{MAX_DAILY_TARGET} 之间")
            clean[column] = value
        if not clean:
            raise ApiError(400, "没有需要更新的目标")
        self._repo.upsert_daily_goal(user_id=user_id, patch=clean)
        return self.daily_goal(user_id, tz_offset=tz_offset)

    # ---------- 内部：FSRS 卡片转换 ----------

    @staticmethod
    def _visible(book: VocabBook, user_id: int) -> bool:
        """系统级词书（owner_id 为 NULL）人人可见；用户级仅导入者本人。"""
        return book.owner_id is None or book.owner_id == user_id

    @staticmethod
    def _utcnow() -> datetime:
        return datetime.now(UTC)

    @staticmethod
    def _as_utc(value: datetime | None) -> datetime | None:
        """SQLite 读回的 datetime 无 tzinfo，统一按 UTC 归一化（服务端统一存取 UTC）。"""
        if value is None:
            return None
        return value if value.tzinfo is not None else value.replace(tzinfo=UTC)

    @staticmethod
    def _day_start(now: datetime, tz_offset: int) -> datetime:
        """客户端「今天零点」对应的 UTC 时刻。

        tz_offset 为本地相对 UTC 的分钟差（东区为正）：先平移到本地时间取零点，再平移回 UTC。
        直接用 UTC 零点会让 UTC+8 用户早上 8 点前做的事算进「昨天」。
        """
        offset = max(-840, min(840, int(tz_offset or 0)))
        local_midnight = (now + timedelta(minutes=offset)).replace(hour=0, minute=0, second=0, microsecond=0)
        return local_midnight - timedelta(minutes=offset)

    def _remaining_quota(self, user_id: int, now: datetime, tz_offset: int) -> tuple[int, int]:
        """今日剩余的新词 / 复习配额 = 各自目标 − 今日已完成量（下限 0）。

        一次聚合同时算出两者，避免为两个配额各打一遍 count_today_learned。
        """
        goal = self._repo.get_daily_goal(user_id)
        new_target = int(goal.new_target) if goal else DEFAULT_NEW_LIMIT
        review_target = int(goal.review_target) if goal else DEFAULT_REVIEW_LIMIT
        counts = self._repo.count_today_learned(user_id, self._day_start(now, tz_offset))
        return (
            max(0, new_target - counts["newLearned"]),
            max(0, review_target - counts["reviewed"]),
        )

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

    def _book_dto(self, b: VocabBook, word_counts: dict[int, int], stats: dict[int, dict]) -> dict:
        s = stats.get(b.id, {})
        return {
            "id": b.id,
            "slug": b.slug,
            "name": b.name,
            "lang": b.lang,
            "emoji": b.emoji,
            "description": b.description,
            "ownerId": b.owner_id,  # null=系统级词书；非空=用户级（导入者 id）
            "wordCount": word_counts.get(b.id, 0),
            "learning": s.get("learning", 0),
            "mastered": s.get("mastered", 0),
            "due": s.get("due", 0),
            "createdAt": iso_z(b.created_at),
        }

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
            # 掌握进度：required=0 表示还没做过首次识词判断；剩余次数给 UI 显示「还差 N 次」
            "correctStreak": p.correct_streak,
            "requiredStreak": p.required_streak,
            "identifyResult": p.identify_result,
            "due": iso_z(self._as_utc(p.due)) if p.due else None,
            "lastReview": iso_z(self._as_utc(p.last_review)) if p.last_review else None,
            "lastWrongAt": iso_z(self._as_utc(p.last_wrong_at)) if p.last_wrong_at else None,
            "state": p.state,
            "stability": p.stability,
            "difficulty": p.difficulty,
            "updatedAt": iso_z(self._as_utc(p.updated_at)),
        }

    def _practice_dto(self, stat: dict | None) -> dict:
        """练习模式覆盖 DTO：各模式的练习次数 + 累计次数 + 最近一次（无记录时全 0 / null）。"""
        s = stat or {}
        last_at = self._as_utc(s.get("lastAt"))
        return {
            "follow": int(s.get("follow", 0)),
            "dictation": int(s.get("dictation", 0)),
            "selfTest": int(s.get("self_test", 0)),
            "spell": int(s.get("spell", 0)),
            "totalCount": int(s.get("totalCount", 0)),
            "lastAt": iso_z(last_at) if last_at else None,
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

    def _daily_goal_dto(self, goal: VocabDailyGoal | None, counts: dict[str, int]) -> dict:
        """每日目标视图。goal 为 None = 从未改过目标，此时回缺省值且 updatedAt 为 null。

        新词 / 复习两侧字段完全对称（remaining/achieved 各有各的），前端可直接用。
        """
        new_target = int(goal.new_target) if goal else DEFAULT_NEW_LIMIT
        review_target = int(goal.review_target) if goal else DEFAULT_REVIEW_LIMIT
        today_new = int(counts.get("newLearned", 0))
        today_reviewed = int(counts.get("reviewed", 0))
        return {
            "newTarget": new_target,
            "reviewTarget": review_target,
            "todayNew": today_new,
            "todayReviewed": today_reviewed,
            "remaining": max(0, new_target - today_new),
            "achieved": today_new >= new_target,
            "reviewRemaining": max(0, review_target - today_reviewed),
            "reviewAchieved": today_reviewed >= review_target,
            "updatedAt": iso_z(self._as_utc(goal.updated_at)) if goal is not None else None,
        }

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
