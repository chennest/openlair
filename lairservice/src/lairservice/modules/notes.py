"""Agent 快速记录模块（早期 harness 能力）。

Note 模型已统一迁移至 `lairservice.models.note`；本模块只保留
agent 侧的提取逻辑与仓库适配（user_id 字符串 → int 用户 id）。
"""

from lairservice.modules.base import ModuleContext
from lairservice.models.note import Note
from lairservice.repositories.notes import NoteRepository
from lairservice.db.session import SessionFactory


def _resolve_user_id(user_id: str) -> int:
    """agent 上下文里的 user_id 是字符串；非数字 id（如 local-user/u1）映射到演示用户 1。"""
    if user_id.isdigit():
        return int(user_id)
    return 1


class NotesRepository:
    """agent 侧适配：委托给统一 NoteRepository。"""

    def __init__(self, session_factory: SessionFactory) -> None:
        self._repo = NoteRepository(session_factory)

    def create(self, *, user_id: str, content: str) -> Note:
        return self._repo.create_quick(user_id=_resolve_user_id(user_id), content=content, title=content[:40])

    def list_by_user(self, *, user_id: str) -> list[Note]:
        return self._repo.list_content_by_user(_resolve_user_id(user_id))


class NotesService:
    name = "notes"

    def __init__(self, repository: NotesRepository) -> None:
        self._repository = repository

    async def handle(self, *, message: str, context: ModuleContext) -> str:
        content = self._extract_note_content(message)
        note = self._repository.create(user_id=context.user_id, content=content)
        return f"已记录笔记 #{note.id}：{note.content}"

    def list_notes(self, *, user_id: str) -> list[Note]:
        return self._repository.list_by_user(user_id=user_id)

    def _extract_note_content(self, message: str) -> str:
        content = message.strip()
        prefixes = ("记录一下", "记一下", "记录", "笔记", "note", "notes")
        lowered = content.lower()
        for prefix in prefixes:
            if lowered.startswith(prefix):
                content = content[len(prefix) :].strip(" ：:，,。")
                break
        return content or message.strip()
