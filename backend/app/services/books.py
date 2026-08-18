"""账本服务：列表 / 建账本 / 成员增删（owner 保护）/ 邀请码分享 / 加入 / 退出。"""

import secrets

from app.core.envelope import ApiError
from app.models.book import Book
from app.repositories.books import BookRepository
from app.repositories.users import UserRepository
from app.services import iso_z

# 邀请码字母表：剔除易混字符 0/O/1/I/L，剩余 31 字符，8 位组合约 8.5e11，抗暴力枚举
_INVITE_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"
_INVITE_LENGTH = 8


def _generate_invite_code() -> str:
    return "".join(secrets.choice(_INVITE_ALPHABET) for _ in range(_INVITE_LENGTH))


def _normalize_invite_code(code: str) -> str:
    """忽略大小写、连字符、空格；只保留字母数字并转大写。"""
    return "".join(ch.upper() for ch in code if ch.isalnum())


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

    # ---------- 邀请码分享 / 加入 / 退出 ----------

    def _new_invite_code(self) -> str:
        """生成一个不与现有码冲突的新邀请码。"""
        for _ in range(5):
            code = _generate_invite_code()
            if self._books.by_invite_code(code) is None:
                return code
        raise ApiError(500, "生成邀请码失败，请重试")

    def _require_shared_book(self, book_id: int) -> Book:
        book = self._books.get(book_id)
        if book is None or book.deleted_at is not None:
            raise ApiError(404, "账本不存在")
        if book.type != "shared":
            raise ApiError(400, "请先转为共享账本")
        return book

    def get_invite(self, *, book_id: int, user_id: int) -> dict:
        """查看邀请码（仅 owner）。码不下发到账本列表 DTO，防成员转分享。"""
        self._require_owner(book_id, user_id)
        book = self._books.get(book_id)
        return {"code": book.invite_code if book else None}

    def generate_invite(self, *, book_id: int, user_id: int) -> dict:
        """生成/重置邀请码（仅 owner）：覆盖旧码，旧码立即失效。"""
        self._require_owner(book_id, user_id)
        self._require_shared_book(book_id)
        code = self._new_invite_code()
        self._books.set_invite_code(book_id, code)
        return {"code": code}

    def disable_invite(self, *, book_id: int, user_id: int) -> dict:
        """关闭邀请（仅 owner）：置空码，彻底停止新成员加入。"""
        self._require_owner(book_id, user_id)
        self._require_shared_book(book_id)
        self._books.set_invite_code(book_id, None)
        return {"ok": True}

    def join(self, *, code: str, user_id: int) -> dict:
        """输入邀请码加入共享账本（任意登录用户，成为 editor）。"""
        normalized = _normalize_invite_code(code or "")
        if len(normalized) != _INVITE_LENGTH:
            raise ApiError(404, "邀请码无效或已失效")
        book = self._books.by_invite_code(normalized)
        if book is None or book.type != "shared":
            raise ApiError(404, "邀请码无效或已失效")
        if self._books.member(book.id, user_id) is not None:
            raise ApiError(409, "你已在该账本中")
        self._books.add_member(book_id=book.id, user_id=user_id, role="editor")
        return {"book": book_dto(book, self._members_dto(book.id))}

    def leave(self, *, book_id: int, user_id: int) -> dict:
        """成员自助退出账本（owner 不可退出，需删除账本）。"""
        book = self._books.get(book_id)
        if book is None:
            raise ApiError(404, "账本不存在")
        member = self._books.member(book_id, user_id)
        if member is None:
            raise ApiError(404, "你不是该账本成员")
        if member.role == "owner":
            raise ApiError(400, "账本创建者不能退出，请删除账本")
        self._books.remove_member(book_id=book_id, user_id=user_id)
        return {"ok": True}

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

    def convert_to_shared(self, *, book_id: int, user_id: int) -> dict:
        """个人账本 → 共享账本（单向）：仅 owner，个人账本才能转；转成后自动生成邀请码。"""
        self._require_owner(book_id, user_id)
        book = self._books.get(book_id)
        if book is None:
            raise ApiError(404, "账本不存在")
        if book.type == "shared":
            raise ApiError(400, "已是共享账本")
        updated = self._books.update_type(book_id, "shared")
        if updated is None:
            raise ApiError(404, "账本不存在")
        # 转共享即生成邀请码，立即可分享
        self._books.set_invite_code(book_id, self._new_invite_code())
        return {"book": book_dto(updated, self._members_dto(book_id))}

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
