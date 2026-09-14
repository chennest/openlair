"""词汇打字练习模块：词书 / 单词 / 关联 / 学习进度（FSRS）/ 练习会话 / 练习明细 / 每日目标。

词书与单词是全局共享数据（不带 user_id，由导入脚本维护）；
进度、会话、明细、每日目标按用户隔离。FSRS 字段平铺进 progress 表（排课需 WHERE due <= now 索引），
字段与 py-fsrs v6 的 Card 一一对应（state/step/stability/difficulty/due/last_review）。
"""

from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class VocabBook(Base):
    """vocab_books 表：词书（如 CET-4 / 考研），导入维护。

    owner_id 为 NULL = 系统级词书（所有用户可见，仅站长/首位用户可导入和删除）；
    非 NULL = 用户级词书（仅导入者本人可见，本人可删）。
    """

    __tablename__ = "vocab_books"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(50), unique=True)  # cet4 / cet6 / kaoyan
    name: Mapped[str] = mapped_column(String(100))
    lang: Mapped[str] = mapped_column(String(10), default="en")  # 预留多语言
    emoji: Mapped[str] = mapped_column(String(8), default="")
    description: Mapped[str] = mapped_column(String(255), default="")
    owner_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)  # NULL=系统级；非空=用户级（逻辑关联 users.id，无硬外键）
    word_count: Mapped[int] = mapped_column(Integer, default=0)  # 冗余计数，导入脚本维护
    sort: Mapped[int] = mapped_column(Integer, default=0)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )


class VocabWord(Base):
    """vocab_words 表：单词条（全局去重，word 唯一），释义/例句等离线数据随词入库。"""

    __tablename__ = "vocab_words"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    word: Mapped[str] = mapped_column(String(100), unique=True)
    phonetic_uk: Mapped[str] = mapped_column(String(100), default="")
    phonetic_us: Mapped[str] = mapped_column(String(100), default="")
    translations: Mapped[list] = mapped_column(JSON, default=list)  # [{pos: "v.", cn: "取消"}]
    sentences: Mapped[list] = mapped_column(JSON, default=list)  # [{en: "...", cn: "..."}]
    phrases: Mapped[list] = mapped_column(JSON, default=list)  # 短语搭配
    synos: Mapped[list] = mapped_column(JSON, default=list)  # 同义词组 [{pos, ws: [...]}]，自测干扰项用
    rel_words: Mapped[dict] = mapped_column(JSON, default=dict)  # {root, rels: [...]}，干扰项加权用
    freq: Mapped[int] = mapped_column(Integer, default=0)  # 词频等级（0=未知），新词排课冷启动优先
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )


class VocabBookWord(Base):
    """vocab_book_words 表：词书 ↔ 单词 多对多关联（同一词可入多本词书，进度仍全局唯一）。"""

    __tablename__ = "vocab_book_words"
    __table_args__ = (UniqueConstraint("book_id", "word_id", name="uq_vocab_book_words"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    book_id: Mapped[int] = mapped_column(Integer, index=True)  # 逻辑关联 vocab_books.id（无硬外键）
    word_id: Mapped[int] = mapped_column(Integer, index=True)  # 逻辑关联 vocab_words.id（无硬外键）
    sort: Mapped[int] = mapped_column(Integer, default=0)  # 词书内顺序
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class VocabWordProgress(Base):
    """vocab_word_progress 表：用户学习进度（FSRS 卡片，每用户每词一条，跨词书不重复学）。

    FSRS 字段平铺对齐 py-fsrs v6 Card：state 0=未复习（哨兵）1=Learning 2=Review 3=Relearning；
    due 是排课主查询列（<= now 即到期）；stability/difficulty 为 None 表示尚未形成记忆状态。
    SQLite 读取的 datetime 无 tzinfo，服务层统一按 UTC 归一化。
    """

    __tablename__ = "vocab_word_progress"
    __table_args__ = (UniqueConstraint("user_id", "word_id", name="uq_vocab_word_progress"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)  # 逻辑关联 users.id（无硬外键）
    word_id: Mapped[int] = mapped_column(Integer, index=True)  # 逻辑关联 vocab_words.id（无硬外键）
    book_id: Mapped[int] = mapped_column(Integer, default=0)  # 首次学习的来源词书
    status: Mapped[str] = mapped_column(String(20), default="learning")  # learning / mastered
    collected: Mapped[bool] = mapped_column(Boolean, default=False)  # 收藏（并行标记，不影响排课）
    wrong_count: Mapped[int] = mapped_column(Integer, default=0)  # 累计打错次数
    right_count: Mapped[int] = mapped_column(Integer, default=0)  # 累计打对次数
    wrong_active: Mapped[bool] = mapped_column(Boolean, default=False)  # 是否在错词本中
    last_wrong_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    due: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)  # FSRS 下次到期
    stability: Mapped[float | None] = mapped_column(Float, nullable=True)
    difficulty: Mapped[float | None] = mapped_column(Float, nullable=True)
    state: Mapped[int] = mapped_column(Integer, default=0)  # FSRS State：0 哨兵 / 1 / 2 / 3
    step: Mapped[int | None] = mapped_column(Integer, nullable=True)  # FSRS 学习步（Review 态为 None）
    last_review: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # 首次「真正作答」的时刻（submit_answer 在新建进度行时写入，之后不再覆盖）。
    # 这是「今日已记 N 个单词」的唯一计数依据：只认真正练过的词，
    # 不会被「仅点了收藏 / 标记已掌握但没做过题」的进度行污染（update_progress 不写本列）。
    first_learned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    # ── 「是否掌握」的显式计数（不依赖 FSRS 的 stability）─────────────────────
    # 连续答对次数：答对 +1，答错归零。用户手动「取消记住」也会清零。
    correct_streak: Mapped[int] = mapped_column(Integer, default=0)
    # 该词要求的连续答对次数：由「首次识词判断」决定 —— 判断对=3（再连对 2 次即掌握）、
    # 判断错/不认识=5。0 表示还没做过首次判断，下一次作答就充当那次判断。
    required_streak: Mapped[int] = mapped_column(Integer, default=0)
    # 首次识词判断的结果：'' 未判断 / 'know' 选对（眼熟）/ 'unsure' 选错或点了不认识
    identify_result: Mapped[str] = mapped_column(String(10), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )


class VocabPracticeSession(Base):
    """vocab_practice_sessions 表：练习会话（进练习页一趟一条，finish 时汇总）。"""

    __tablename__ = "vocab_practice_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)  # 逻辑关联 users.id（无硬外键）
    book_id: Mapped[int] = mapped_column(Integer, default=0)  # 练习的词书
    mode: Mapped[str] = mapped_column(String(20), default="follow")  # follow 跟打 / dictation 听写 / self_test 自测 / spell 默写
    total_count: Mapped[int] = mapped_column(Integer, default=0)
    correct_count: Mapped[int] = mapped_column(Integer, default=0)
    wrong_count: Mapped[int] = mapped_column(Integer, default=0)  # 答错的词数
    duration_sec: Mapped[int] = mapped_column(Integer, default=0)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )


class VocabPracticeLog(Base):
    """vocab_practice_logs 表：练习明细（每词一题一条，只插入不更新）。wrong_times 是错次→Rating 映射的输入。"""

    __tablename__ = "vocab_practice_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)  # 逻辑关联 users.id（无硬外键）
    session_id: Mapped[int] = mapped_column(Integer, index=True)  # 逻辑关联 vocab_practice_sessions.id
    word_id: Mapped[int] = mapped_column(Integer, index=True)  # 逻辑关联 vocab_words.id
    mode: Mapped[str] = mapped_column(String(20), default="follow")
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False)
    wrong_times: Mapped[int] = mapped_column(Integer, default=0)  # 本次作答打错次数
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class VocabDailyGoal(Base):
    """vocab_daily_goals 表：每人一条的背词每日目标（每用户每行，user_id 唯一）。

    不预先为每个用户建行——取不到时服务层回退到 DEFAULT_NEW_LIMIT / DEFAULT_REVIEW_LIMIT，
    这样「用户改过目标」才有痕迹，也省掉一次无意义的写。
    「今日已记」不落库，而是按 vocab_word_progress.first_learned_at 在本地零点后聚合，
    避免「计数列 + 明细」双写不一致。
    """

    __tablename__ = "vocab_daily_goals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)  # 逻辑关联 users.id（无硬外键）
    new_target: Mapped[int] = mapped_column(Integer, default=10)  # 每日新词目标（对齐 DEFAULT_NEW_LIMIT）
    review_target: Mapped[int] = mapped_column(Integer, default=30)  # 每日复习目标（对齐 DEFAULT_REVIEW_LIMIT）
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )
