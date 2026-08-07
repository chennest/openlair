"""初始数据（幂等）：与前端 mock 契约对齐。

- 3 个测试账号：test1/test2/test3@openlair.dev，密码统一 test123456
- 16 个分类（支出 1-10 / 收入 11-16）
- 2 个账本（个人 + 共享，成员 1/2/3）+ 当月预算
- 近 90 天流水：个人账本 85 条 + 共享账本 15 条（收入 ~25%）
- 待办 / 日程 / 笔记 / 习惯 演示数据
仅当 users 表为空时写入（重复启动不重复插入）。
"""

from datetime import UTC, date, datetime, timedelta
from random import Random

from sqlalchemy import select
from sqlalchemy.orm import Session

from lairservice.core.security import hash_password
from lairservice.models.book import Book, BookMember
from lairservice.models.budget import Budget
from lairservice.models.category import Category
from lairservice.models.event import CalendarEvent
from lairservice.models.habit import Habit
from lairservice.models.note import Note
from lairservice.models.todo import TodoItem
from lairservice.models.transaction import Transaction
from lairservice.models.user import User

QUADRANTS = ["重要紧急", "重要不紧急", "紧急不重要", "不重要不紧急"]
NOTES_POOL = ["午饭", "地铁", "买书", "房租", "工资", "聚餐", "打车", "日用品", "电影票", "水电费"]
LOCATIONS = ["公司", "家", "健身房", "咖啡厅", "线上"]
DUES = ["今天", "明天", "本周", "下月", "无期限"]
TAGS = ["工作", "学习", "生活", "灵感", "会议", "备忘"]
HABIT_NAMES = ["早起打卡", "背单词", "跑步 3km", "阅读 30 分钟", "冥想", "记账"]
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

    # ---------- 分类（固定 id 1-16；收入 sortOrder 偏移 10，全量排序 = 支出块 + 收入块） ----------
    exp = ["餐饮", "交通", "购物", "居住", "娱乐", "医疗", "学习", "人情", "通讯", "其他"]
    inc = ["工资", "奖金", "理财", "礼金", "退款", "其他"]
    categories: list[Category] = [
        Category(id=i + 1, name=name, type="支出", sort_order=i, is_default=name == "其他")
        for i, name in enumerate(exp)
    ]
    categories += [
        Category(id=11 + i, name=name, type="收入", sort_order=10 + i, is_default=name == "其他")
        for i, name in enumerate(inc)
    ]
    for c in categories:
        c.created_at = now
        session.add(c)

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

    session.commit()
