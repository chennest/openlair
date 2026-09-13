"""业务 ORM 模型：导入全部模型以注册到 Base.metadata（create_all / 迁移用）。"""

from app.models.api_key import ApiKey
from app.models.assistant import AssistantMessage, AssistantPlan, AssistantSession
from app.models.book import Book, BookMember
from app.models.budget import Budget
from app.models.category import Category
from app.models.day import Day
from app.models.event import CalendarEvent
from app.models.habit import Habit
from app.models.note import Note
from app.models.revoked_token import RevokedToken
from app.models.setting import Setting
from app.models.todo import TodoItem
from app.models.transaction import Transaction
from app.models.user import User
from app.models.vocab import VocabBook, VocabBookWord, VocabPracticeLog, VocabPracticeSession, VocabWord, VocabWordProgress

__all__ = [
    "ApiKey",
    "AssistantMessage",
    "AssistantPlan",
    "AssistantSession",
    "Book",
    "BookMember",
    "Budget",
    "CalendarEvent",
    "Category",
    "Day",
    "Habit",
    "Note",
    "RevokedToken",
    "Setting",
    "TodoItem",
    "Transaction",
    "User",
    "VocabBook",
    "VocabBookWord",
    "VocabPracticeLog",
    "VocabPracticeSession",
    "VocabWord",
    "VocabWordProgress",
]
