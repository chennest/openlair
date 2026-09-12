"""初始数据（幂等）：与前端 mock 契约对齐。

- 3 个测试账号：test1/test2/test3@openlair.dev，密码统一 test123456
- 26 个系统预置分类（支出 18 / 收入 8）
- 2 个账本（个人 + 共享，成员 1/2/3）+ 当月预算
- 近 90 天流水：个人账本 85 条 + 共享账本 15 条（收入 ~25%）
- 待办 / 日程 / 笔记 / 习惯 演示数据
仅当 users 表为空时写入（重复启动不重复插入）。
"""

from datetime import UTC, date, datetime, timedelta
from random import Random

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.book import Book, BookMember
from app.models.budget import Budget
from app.models.category import Category
from app.models.day import Day
from app.models.event import CalendarEvent
from app.models.habit import Habit
from app.models.note import Note
from app.models.todo import TodoItem
from app.models.transaction import Transaction
from app.models.user import User

QUADRANTS = ["重要紧急", "重要不紧急", "紧急不重要", "不重要不紧急"]
NOTES_POOL = ["午饭", "地铁", "买书", "房租", "工资", "聚餐", "打车", "日用品", "电影票", "水电费"]
LOCATIONS = ["公司", "家", "健身房", "咖啡厅", "线上"]
DUES = ["今天", "明天", "本周", "下月", "无期限"]
TAGS = ["工作", "学习", "生活", "灵感", "会议", "备忘"]
HABIT_NAMES = ["早起打卡", "背单词", "跑步 3km", "阅读 30 分钟", "冥想", "记账"]
# 倒数日演示数据：(标题, emoji, 距今天数偏移或绝对日, 重复, 置顶)
SENTENCES = [
    "推进周报整理", "预约下周会议", "整理报销发票", "完成季度复盘", "更新学习计划",
    "排查线上告警", "审阅合同条款", "参加技术分享", "优化部署脚本", "补充接口文档",
]


def seed(session: Session) -> None:
    if session.scalar(select(User.id).limit(1)) is not None:
        return  # 已有数据，幂等跳过

    rng = Random(20260806)
    now = datetime.now(UTC)

    # ---------- 用户（测试账号） ----------
    users = [
        User(id=1, name="我", email="test1@openlair.dev", password_hash=hash_password("test123456"), avatar_color="#0071e3"),
        User(id=2, name="小明", email="test2@openlair.dev", password_hash=hash_password("test123456"), avatar_color="#30d158"),
        User(id=3, name="小美", email="test3@openlair.dev", password_hash=hash_password("test123456"), avatar_color="#ff6b00"),
    ]
    for u in users:
        u.created_at = now
        session.add(u)

    # ---------- 分类（系统预置 id 1-16 固定 + 17-26；支出 sortOrder 0-17 / 收入 18-25，「其他」各组兜底位） ----------
    exp: list[tuple[str, int]] = [
        ("餐饮", 1), ("交通", 2), ("购物", 3), ("居住", 4), ("娱乐", 5),
        ("医疗", 6), ("学习", 7), ("人情", 8), ("通讯", 9),
        ("数码", 17), ("宠物", 18), ("运动健身", 19), ("美妆", 20),
        ("旅行", 21), ("维修", 22), ("订阅服务", 23), ("汽车", 24),
        ("其他", 10),
    ]
    inc: list[tuple[str, int]] = [
        ("工资", 11), ("奖金", 12), ("理财", 13), ("礼金", 14), ("退款", 15),
        ("副业", 25), ("报销", 26),
        ("其他", 16),
    ]
    categories: list[Category] = [
        Category(id=cid, name=name, type="支出", sort_order=i, user_id=None, is_default=name == "其他")
        for i, (name, cid) in enumerate(exp)
    ]
    categories += [
        Category(id=cid, name=name, type="收入", sort_order=18 + i, user_id=None, is_default=name == "其他")
        for i, (name, cid) in enumerate(inc)
    ]
    for c in categories:
        c.created_at = now
        session.add(c)
    session.flush()  # 无依赖表（users/categories）先落库；无硬外键后为防御性步骤

    # ---------- 账本 + 成员 + 预算 ----------
    session.add(Book(id=1, name="我的账本", type="personal", created_at=now))
    session.add(Book(id=2, name="家庭共享账本", type="shared", created_at=now))
    for book_id, user_id, role in [
        (1, 1, "owner"),
        (2, 1, "owner"),
        (2, 2, "editor"),
        (2, 3, "editor"),
    ]:
        session.add(BookMember(book_id=book_id, user_id=user_id, role=role, joined_at=now))
    session.add(
        Budget(book_id=1, month=f"{now.year}-{now.month:02d}", expense_limit=5000, created_at=now, updated_at=now)
    )

    # ---------- 流水（近 90 天） ----------
    today = date.today()
    tx_id = 0

    def make_tx(book_id: int, user_id: int) -> Transaction:
        nonlocal tx_id
        tx_id += 1
        is_income = rng.random() < 0.25
        days_ago = rng.randint(0, 89)
        created = now - timedelta(days=days_ago, hours=rng.randint(0, 23))
        amount = round(rng.uniform(200, 15000), 2) if is_income else round(rng.uniform(5, 800), 2)
        note = rng.choice(["工资", "季度奖金", "理财收益", "红包"]) if is_income else rng.choice(NOTES_POOL)
        cid = rng.choice(range(11, 17)) if is_income else rng.choice(range(1, 11))
        return Transaction(
            id=tx_id,
            type="收入" if is_income else "支出",
            category_id=cid,
            book_id=book_id,
            user_id=user_id,
            amount=amount,
            date=today - timedelta(days=days_ago),
            note=note,
            created_at=created,
            updated_at=created,
        )

    for _ in range(85):
        session.add(make_tx(1, 1))
    for _ in range(15):
        session.add(make_tx(2, rng.choice([1, 2, 3])))

    # ---------- 待办 / 日程 / 笔记 / 习惯 ----------
    for i in range(8):
        created = now
        session.add(
            TodoItem(
                id=i + 1,
                user_id=1,
                text=rng.choice(SENTENCES),
                quadrant=rng.choice(QUADRANTS),
                done=rng.random() > 0.5,
                due=rng.choice(DUES),
                created_at=created,
                updated_at=created,
            )
        )
    for i in range(6):
        created = now
        session.add(
            CalendarEvent(
                id=i + 1,
                user_id=1,
                title=rng.choice(SENTENCES),
                date=today + timedelta(days=rng.randint(0, 6)),
                time=f"{rng.randint(8, 20)}:00",
                location=rng.choice(LOCATIONS),
                done=rng.random() > 0.5,
                created_at=created,
                updated_at=created,
            )
        )
    for i, title in enumerate(["本周复盘", "阅读摘录", "会议纪要", "灵感速记", "部署备忘"]):
        created = now
        session.add(
            Note(
                id=i + 1,
                user_id=1,
                title=title,
                summary=f"{rng.choice(SENTENCES)}，{rng.choice(SENTENCES)}。",
                tags=rng.sample(TAGS, rng.randint(1, 3)),
                created_at=created,
                updated_at=created,
            )
        )
    for i, name in enumerate(HABIT_NAMES):
        created = now
        session.add(
            Habit(
                id=i + 1,
                user_id=1,
                name=name,
                streak=rng.randint(0, 15),
                done=rng.random() > 0.5,
                week=[rng.random() > 0.5 for _ in range(7)],
                created_at=created,
                updated_at=created,
            )
        )

    # ---------- 倒数日 / 纪念日演示数据（覆盖一次性未来/今天/过去、每年、每月） ----------
    birthday = (today + timedelta(days=12)).replace(year=today.year - 2)
    anniversary = (today + timedelta(days=45)).replace(year=today.year - 5)
    demo_days = [
        ("考研初试", "📚", today + timedelta(days=3), "once", False),
        ("项目上线", "🚀", today, "once", False),
        ("宝宝生日", "🎂", birthday, "yearly", True),
        ("发工资", "💰", today.replace(day=1), "monthly", False),
        ("结婚纪念日", "💍", anniversary, "yearly", False),
        ("在一起", "💕", today - timedelta(days=1023), "once", False),
    ]
    for i, (title, emoji, day_date, repeat, pinned) in enumerate(demo_days):
        session.add(
            Day(
                id=i + 1,
                user_id=1,
                title=title,
                emoji=emoji,
                date=day_date,
                repeat=repeat,
                pinned=pinned,
                created_at=now,
                updated_at=now,
            )
        )

    session.commit()
