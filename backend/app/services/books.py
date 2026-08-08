"""账本服务：列表 / 建账本 / 成员增删（owner 保护）。"""

from app.core.envelope import ApiError
from app.models.book import Book
from app.repositories.books import BookRepository
from app.repositories.users import UserRepository
from app.services import iso_z


def book_dto(book: Book, members: list) -> dict:
    return {
        "id": book.id,
        "name": book.name,
        "type": book.type,
        "members": members,
    }


class BookService:
    def __init__(self, books: BookRepository, users: UserRepository) -> None:
        self._books = books
        self._users = users

    def _members_dto(self, book_id: int) -> list[dict]:
        result = []
        for m in self._books.members_of(book_id):
            user = self._users.by_id(m.user_id)
            result.append(
                {
                    "bookId": m.book_id,
                    "userId": m.user_id,
                    "role": m.role,
                    "joinedAt": iso_z(m.joined_at),
                    "user": (
                        {"id": user.id, "name": user.name, "avatarColor": user.avatar_color}
                        if user is not None
                        else None
                    ),
                }
            )
        return result

    def list(self, user_id: int | None = None) -> list[dict]:
        """当前用户的账本列表（只返回我是成员的账本，多用户隔离）。"""
        return [book_dto(b, self._members_dto(b.id)) for b in self._books.list_all(user_id)]

    def create(self, *, user_id: int, name: str, type: str) -> dict:
        book = self._books.create(name=name or "共享账本", type=type if type == "shared" else "personal")
        self._books.add_member(book_id=book.id, user_id=user_id, role="owner")
        return {"book": book_dto(book, self._members_dto(book.id))}

    def add_member(self, *, book_id: int, user_id: int | None, name: str | None) -> dict:
        book = self._books.get(book_id)
        if book is None:
            raise ApiError(404, "账本不存在")
        uid = user_id
        if not uid:
            # 按名字新建用户（无登录账号，仅成员）
            if not name:
                raise ApiError(400, "缺少成员信息")
            member_user = self._users.create(
                name=name[:12],
                avatar_color="#30d158",
            )
            uid = member_user.id
        if self._books.member(book_id, uid) is not None:
            raise ApiError(409, "该成员已在账本中")
        self._books.add_member(book_id=book_id, user_id=uid, role="editor")
        return {"book": book_dto(book, self._members_dto(book_id))}

    def remove_member(self, *, book_id: int, user_id: int) -> dict:
        book = self._books.get(book_id)
        if book is None:
            raise ApiError(404, "账本不存在")
        member = self._books.member(book_id, user_id)
        if member is None:
            raise ApiError(404, "该成员不在账本中")
        if member.role == "owner":
            raise ApiError(400, "不能移除账本创建者")
        self._books.remove_member(book_id=book_id, user_id=user_id)
        return {"book": book_dto(book, self._members_dto(book_id))}

    # ---------- 回收站（软删除） ----------

    def _require_owner(self, book_id: int, user_id: int) -> None:
        book = self._books.get(book_id)
        if book is None:
            raise ApiError(404, "账本不存在")
        member = self._books.member(book_id, user_id)
        if member is None or member.role != "owner":
            raise ApiError(403, "只有账本创建者可以执行此操作")
        return None

    def trash(self, user_id: int | None = None) -> list[dict]:
        """回收站列表：只显示当前用户的回收站账本。"""
        return [book_dto(b, self._members_dto(b.id)) for b in self._books.list_trash(user_id)]

    def soft_delete(self, *, book_id: int, user_id: int) -> dict:
        """删除账本 → 移入回收站（软删除，数据保留）。"""
        self._require_owner(book_id, user_id)
        self._books.soft_delete(book_id)
        return {"ok": True}

    def restore(self, *, book_id: int, user_id: int) -> dict:
        """从回收站恢复账本。"""
        self._require_owner(book_id, user_id)
        self._books.restore(book_id)
        return {"ok": True}

    def purge(self, *, book_id: int, user_id: int) -> dict:
        """彻底删除：级联清流水/预算/成员后物理删除账本。"""
        self._require_owner(book_id, user_id)
        self._books.purge(book_id)
        return {"ok": True}
