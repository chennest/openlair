from datetime import UTC, datetime

from sqlalchemy import case, func, select

from app.db.session import SessionFactory
from app.models.vocab import (
    VocabBook,
    VocabBookWord,
    VocabPracticeLog,
    VocabPracticeSession,
    VocabWord,
    VocabWordProgress,
)


class VocabRepository:
    """词汇模块唯一数据访问通道：词书/单词（全局共享）+ 进度/会话/明细（按用户隔离）。"""

    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    # ---------- 词书（系统级共享 + 用户级私有） ----------

    def list_visible_books(self, user_id: int) -> list[VocabBook]:
        """系统级（owner_id 为 NULL）+ 本人用户级词书，按 sort/id 排序。"""
        with self._session_factory() as session:
            stmt = (
                select(VocabBook)
                .where(
                    VocabBook.is_enabled.is_(True),
                    (VocabBook.owner_id.is_(None)) | (VocabBook.owner_id == user_id),
                )
                .order_by(VocabBook.sort, VocabBook.id)
            )
            return list(session.scalars(stmt))

    def get_book(self, book_id: int) -> VocabBook | None:
        with self._session_factory() as session:
            return session.get(VocabBook, book_id)

    def create_book(
        self, *, slug: str, name: str, lang: str = "en", emoji: str = "", description: str = "", sort: int = 0, owner_id: int | None = None
    ) -> VocabBook:
        with self._session_factory() as session:
            item = VocabBook(slug=slug, name=name, lang=lang, emoji=emoji, description=description, sort=sort, owner_id=owner_id)
            session.add(item)
            session.commit()
            session.refresh(item)
            return item

    def delete_book(self, book_id: int) -> bool:
        """删除词书及其单词映射（全局词条与学习进度保留）。"""
        with self._session_factory() as session:
            item = session.get(VocabBook, book_id)
            if item is None:
                return False
            for row in session.query(VocabBookWord).filter(VocabBookWord.book_id == book_id):
                session.delete(row)
            session.delete(item)
            session.commit()
            return True

    def count_words_by_book(self) -> dict[int, int]:
        with self._session_factory() as session:
            stmt = select(VocabBookWord.book_id, func.count(VocabBookWord.id)).group_by(VocabBookWord.book_id)
            return {book_id: count for book_id, count in session.execute(stmt)}

    def upsert_words(self, parsed: list) -> tuple[dict[str, int], int]:
        """按小写拼写全局去重 upsert 词条：已存在且字段为空的补齐，缺失的插入。

        返回 (word → id 映射, 新插入数量)。分块查询避免 SQLite IN 变量上限。
        """
        now = datetime.now(UTC)
        result: dict[str, int] = {}
        new_count = 0
        with self._session_factory() as session:
            all_words = [p.word for p in parsed]
            existing: dict[str, VocabWord] = {}
            for i in range(0, len(all_words), 500):
                chunk = all_words[i : i + 500]
                for w in session.query(VocabWord).filter(VocabWord.word.in_(chunk)):
                    existing[w.word] = w
            for p in parsed:
                row = existing.get(p.word)
                if row is None:
                    row = VocabWord(
                        word=p.word,
                        phonetic_uk=p.phonetic,
                        phonetic_us="",
                        translations=p.translations,
                        sentences=[],
                        phrases=[],
                        synos=[],
                        rel_words={},
                        freq=p.freq,
                        created_at=now,
                        updated_at=now,
                    )
                    session.add(row)
                    session.flush()
                    existing[p.word] = row
                    new_count += 1
                else:
                    # 补齐空字段（不覆盖已有释义）
                    if not row.phonetic_uk and p.phonetic:
                        row.phonetic_uk = p.phonetic
                    if not row.translations and p.translations:
                        row.translations = p.translations
                    if not row.freq and p.freq:
                        row.freq = p.freq
                result[p.word] = row.id
            session.commit()
        return result, new_count

    def replace_book_words(self, book_id: int, word_ids: list[int]) -> None:
        """重建词书↔单词映射（sort = 列表顺序）。"""
        with self._session_factory() as session:
            for row in session.query(VocabBookWord).filter(VocabBookWord.book_id == book_id):
                session.delete(row)
            session.flush()
            now = datetime.now(UTC)
            session.add_all(
                VocabBookWord(book_id=book_id, word_id=word_id, sort=sort, created_at=now)
                for sort, word_id in enumerate(word_ids)
            )
            session.commit()

    def set_word_count(self, book_id: int, count: int) -> None:
        with self._session_factory() as session:
            item = session.get(VocabBook, book_id)
            if item is not None:
                item.word_count = count
                session.commit()

    def book_progress_stats(self, user_id: int, now: datetime) -> dict[int, dict[str, int]]:
        """每本词书的学习统计（按词书成员资格归桶，而非进度行的来源 book_id）：
        {book_id: {learning, mastered, due}}。"""
        with self._session_factory() as session:
            stmt = (
                select(
                    VocabBookWord.book_id,
                    func.sum(case((VocabWordProgress.status == "learning", 1), else_=0)),
                    func.sum(case((VocabWordProgress.status == "mastered", 1), else_=0)),
                    func.sum(
                        case(
                            (
                                (VocabWordProgress.status == "learning")
                                & VocabWordProgress.due.is_not(None)
                                & (VocabWordProgress.due <= now),
                                1,
                            ),
                            else_=0,
                        )
                    ),
                )
                .join(VocabWordProgress, VocabWordProgress.word_id == VocabBookWord.word_id)
                .where(VocabWordProgress.user_id == user_id)
                .group_by(VocabBookWord.book_id)
            )
            return {
                book_id: {"learning": int(learning or 0), "mastered": int(mastered or 0), "due": int(due or 0)}
                for book_id, learning, mastered, due in session.execute(stmt)
            }

    def book_summary_counts(self, user_id: int, book_id: int, now: datetime) -> dict[str, int]:
        """词书维度汇总（按词书成员资格归桶）：总词数 / 已学 / 学习中 / 已掌握 / 到期 / 错词 / 收藏。

        与 book_progress_stats 的区别：这里额外给出「未学」（无进度行）与「错词/收藏」口径，
        供词书详情页头部一次拿全，避免前端自己求差。
        """
        with self._session_factory() as session:
            stmt = (
                select(
                    func.count(VocabBookWord.id),
                    func.sum(case((VocabWordProgress.id.is_not(None), 1), else_=0)),
                    func.sum(case((VocabWordProgress.status == "learning", 1), else_=0)),
                    func.sum(case((VocabWordProgress.status == "mastered", 1), else_=0)),
                    func.sum(
                        case(
                            (
                                (VocabWordProgress.status == "learning")
                                & VocabWordProgress.due.is_not(None)
                                & (VocabWordProgress.due <= now),
                                1,
                            ),
                            else_=0,
                        )
                    ),
                    func.sum(case((VocabWordProgress.wrong_active.is_(True), 1), else_=0)),
                    func.sum(case((VocabWordProgress.collected.is_(True), 1), else_=0)),
                )
                .select_from(VocabBookWord)
                .outerjoin(
                    VocabWordProgress,
                    (VocabWordProgress.word_id == VocabBookWord.word_id) & (VocabWordProgress.user_id == user_id),
                )
                .where(VocabBookWord.book_id == book_id)
            )
            total, learned, learning, mastered, due, wrong, collected = session.execute(stmt).one()
        return {
            "total": int(total or 0),
            "learned": int(learned or 0),
            "learning": int(learning or 0),
            "mastered": int(mastered or 0),
            "due": int(due or 0),
            "wrong": int(wrong or 0),
            "collected": int(collected or 0),
        }

    # ---------- 单词（全局共享） ----------

    def get_word(self, word_id: int) -> VocabWord | None:
        with self._session_factory() as session:
            return session.get(VocabWord, word_id)

    def list_words_by_book(self, book_id: int, *, limit: int, offset: int) -> list[VocabWord]:
        with self._session_factory() as session:
            stmt = (
                select(VocabWord)
                .join(VocabBookWord, VocabBookWord.word_id == VocabWord.id)
                .where(VocabBookWord.book_id == book_id)
                .order_by(VocabBookWord.sort, VocabWord.id)
                .limit(limit)
                .offset(offset)
            )
            return list(session.scalars(stmt))

    def _book_words_query(self, book_id: int, user_id: int, status: str, keyword: str):
        """词书内单词查询骨架：左连接本人进度 + 可选状态/关键词条件（分页与计数共用）。"""
        conds = [VocabBookWord.book_id == book_id]
        if keyword:
            conds.append(func.lower(VocabWord.word).like(f"%{keyword.lower()}%"))
        if status == "unlearned":
            conds.append(VocabWordProgress.id.is_(None))
        elif status == "learning":
            conds.append(VocabWordProgress.status == "learning")
        elif status == "mastered":
            conds.append(VocabWordProgress.status == "mastered")
        elif status == "wrong":
            conds.append(VocabWordProgress.wrong_active.is_(True))
        elif status == "collected":
            conds.append(VocabWordProgress.collected.is_(True))
        return (
            select(VocabWord)
            .join(VocabBookWord, VocabBookWord.word_id == VocabWord.id)
            .outerjoin(
                VocabWordProgress,
                (VocabWordProgress.word_id == VocabWord.id) & (VocabWordProgress.user_id == user_id),
            )
            .where(*conds)
        )

    def list_book_words_page(
        self,
        book_id: int,
        user_id: int,
        *,
        status: str = "all",
        keyword: str = "",
        sort: str = "order",
        limit: int,
        offset: int,
    ) -> tuple[list[VocabWord], int]:
        """词书内单词分页查询，返回 (当前页词条, 筛选后总数)。

        排序：order 词书顺序 / freq 词频 / wrong 错次最多 / recent 最近练习过。
        """
        base = self._book_words_query(book_id, user_id, status, keyword)
        if sort == "freq":
            ordered = base.order_by(VocabWord.freq.desc(), VocabBookWord.sort, VocabWord.id)
        elif sort == "wrong":
            ordered = base.order_by(
                func.coalesce(VocabWordProgress.wrong_count, 0).desc(), VocabBookWord.sort, VocabWord.id
            )
        elif sort == "recent":
            # last_review 为 NULL（从未练过）的排最后：先按 IS NULL 升序，再按时间倒序
            ordered = base.order_by(
                VocabWordProgress.last_review.is_(None),
                VocabWordProgress.last_review.desc(),
                VocabBookWord.sort,
                VocabWord.id,
            )
        else:
            ordered = base.order_by(VocabBookWord.sort, VocabWord.id)
        with self._session_factory() as session:
            total = session.scalar(select(func.count()).select_from(base.subquery()))
            rows = list(session.scalars(ordered.limit(limit).offset(offset)))
        return rows, int(total or 0)

    def list_new_words(self, book_id: int, user_id: int, *, limit: int) -> list[VocabWord]:
        """词书内该用户尚无进度记录的词（新词池），按词书顺序取。"""
        with self._session_factory() as session:
            stmt = (
                select(VocabWord)
                .join(VocabBookWord, VocabBookWord.word_id == VocabWord.id)
                .outerjoin(
                    VocabWordProgress,
                    (VocabWordProgress.word_id == VocabWord.id) & (VocabWordProgress.user_id == user_id),
                )
                .where(VocabBookWord.book_id == book_id, VocabWordProgress.id.is_(None))
                .order_by(VocabBookWord.sort, VocabWord.id)
                .limit(limit)
            )
            return list(session.scalars(stmt))

    def list_words_by_ids(self, word_ids: list[int]) -> list[VocabWord]:
        if not word_ids:
            return []
        with self._session_factory() as session:
            stmt = select(VocabWord).where(VocabWord.id.in_(word_ids))
            return list(session.scalars(stmt))

    # ---------- 学习进度（FSRS 卡片） ----------

    def get_progress(self, user_id: int, word_id: int) -> VocabWordProgress | None:
        with self._session_factory() as session:
            stmt = select(VocabWordProgress).where(
                VocabWordProgress.user_id == user_id, VocabWordProgress.word_id == word_id
            )
            return session.scalar(stmt)

    def list_progress(self, user_id: int) -> list[VocabWordProgress]:
        with self._session_factory() as session:
            stmt = select(VocabWordProgress).where(VocabWordProgress.user_id == user_id)
            return list(session.scalars(stmt))

    def list_progress_by_word_ids(self, user_id: int, word_ids: list[int]) -> dict[int, VocabWordProgress]:
        """按单词 id 批量取本人进度（词书详情列表用），返回 {word_id: progress}。"""
        if not word_ids:
            return {}
        out: dict[int, VocabWordProgress] = {}
        with self._session_factory() as session:
            for i in range(0, len(word_ids), 500):
                chunk = word_ids[i : i + 500]
                stmt = select(VocabWordProgress).where(
                    VocabWordProgress.user_id == user_id, VocabWordProgress.word_id.in_(chunk)
                )
                for p in session.scalars(stmt):
                    out[p.word_id] = p
        return out

    def list_due_progress(self, user_id: int, now: datetime, *, limit: int) -> list[VocabWordProgress]:
        """到期复习池：due <= now 且未标记已掌握，按 due 升序。"""
        with self._session_factory() as session:
            stmt = (
                select(VocabWordProgress)
                .where(
                    VocabWordProgress.user_id == user_id,
                    VocabWordProgress.status == "learning",
                    VocabWordProgress.due.is_not(None),
                    VocabWordProgress.due <= now,
                )
                .order_by(VocabWordProgress.due, VocabWordProgress.id)
                .limit(limit)
            )
            return list(session.scalars(stmt))

    def list_wrong_progress(self, user_id: int, *, limit: int) -> list[VocabWordProgress]:
        with self._session_factory() as session:
            stmt = (
                select(VocabWordProgress)
                .where(
                    VocabWordProgress.user_id == user_id,
                    VocabWordProgress.wrong_active.is_(True),
                    VocabWordProgress.status == "learning",
                )
                .order_by(VocabWordProgress.last_wrong_at.desc(), VocabWordProgress.id)
                .limit(limit)
            )
            return list(session.scalars(stmt))

    def list_collected_progress(self, user_id: int, *, limit: int) -> list[VocabWordProgress]:
        with self._session_factory() as session:
            stmt = (
                select(VocabWordProgress)
                .where(VocabWordProgress.user_id == user_id, VocabWordProgress.collected.is_(True))
                .order_by(VocabWordProgress.updated_at.desc(), VocabWordProgress.id)
                .limit(limit)
            )
            return list(session.scalars(stmt))

    def create_progress(self, *, user_id: int, word_id: int, book_id: int = 0) -> VocabWordProgress:
        with self._session_factory() as session:
            item = VocabWordProgress(user_id=user_id, word_id=word_id, book_id=book_id)
            session.add(item)
            session.commit()
            session.refresh(item)
            return item

    def update_progress(self, progress_id: int, patch: dict) -> VocabWordProgress | None:
        with self._session_factory() as session:
            item = session.get(VocabWordProgress, progress_id)
            if item is None:
                return None
            for key, value in patch.items():
                if hasattr(item, key):
                    setattr(item, key, value)
            session.commit()
            session.refresh(item)
            return item

    # ---------- 练习会话与明细 ----------

    def create_session(self, *, user_id: int, book_id: int, mode: str) -> VocabPracticeSession:
        with self._session_factory() as session:
            item = VocabPracticeSession(user_id=user_id, book_id=book_id, mode=mode)
            session.add(item)
            session.commit()
            session.refresh(item)
            return item

    def get_session(self, session_id: int) -> VocabPracticeSession | None:
        with self._session_factory() as session:
            return session.get(VocabPracticeSession, session_id)

    def update_session(self, session_id: int, patch: dict) -> VocabPracticeSession | None:
        with self._session_factory() as session:
            item = session.get(VocabPracticeSession, session_id)
            if item is None:
                return None
            for key, value in patch.items():
                if hasattr(item, key):
                    setattr(item, key, value)
            session.commit()
            session.refresh(item)
            return item

    def list_sessions_since(self, user_id: int, since: datetime) -> list[VocabPracticeSession]:
        with self._session_factory() as session:
            stmt = (
                select(VocabPracticeSession)
                .where(VocabPracticeSession.user_id == user_id, VocabPracticeSession.created_at >= since)
                .order_by(VocabPracticeSession.id)
            )
            return list(session.scalars(stmt))

    def create_log(
        self, *, user_id: int, session_id: int, word_id: int, mode: str, is_correct: bool, wrong_times: int, duration_ms: int
    ) -> VocabPracticeLog:
        with self._session_factory() as session:
            item = VocabPracticeLog(
                user_id=user_id,
                session_id=session_id,
                word_id=word_id,
                mode=mode,
                is_correct=is_correct,
                wrong_times=wrong_times,
                duration_ms=duration_ms,
            )
            session.add(item)
            session.commit()
            session.refresh(item)
            return item

    def practice_mode_stats(self, user_id: int, word_ids: list[int]) -> dict[int, dict]:
        """按 (word_id, mode) 聚合练习明细，返回 {word_id: {follow, dictation, self_test, spell, totalCount, lastAt}}。

        「这个字有没有被听写过」这类覆盖情况只能从明细表推（进度表不区分模式）。
        口径是全局的：不按词书或练习来源过滤——进度本身就是 (user, word) 全局唯一，
        且错词本/收藏练习的 session.book_id 记为 0，按词书过滤反而会漏。
        """
        if not word_ids:
            return {}
        out: dict[int, dict] = {}
        with self._session_factory() as session:
            for i in range(0, len(word_ids), 500):
                chunk = word_ids[i : i + 500]
                stmt = (
                    select(
                        VocabPracticeLog.word_id,
                        VocabPracticeLog.mode,
                        func.count(VocabPracticeLog.id),
                        func.max(VocabPracticeLog.created_at),
                    )
                    .where(VocabPracticeLog.user_id == user_id, VocabPracticeLog.word_id.in_(chunk))
                    .group_by(VocabPracticeLog.word_id, VocabPracticeLog.mode)
                )
                for word_id, mode, count, last_at in session.execute(stmt):
                    row = out.setdefault(
                        word_id,
                        {"follow": 0, "dictation": 0, "self_test": 0, "spell": 0, "totalCount": 0, "lastAt": None},
                    )
                    hits = int(count or 0)
                    if mode in ("follow", "dictation", "self_test", "spell"):
                        row[mode] = hits
                    row["totalCount"] += hits
                    if last_at is not None and (row["lastAt"] is None or last_at > row["lastAt"]):
                        row["lastAt"] = last_at
        return out
