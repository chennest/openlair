"""API Key 服务：创建 / 列表 / 撤销。

契约要点：
- 创建时明文只返回一次（apiKey 字段），此后任何接口都不再下发明文。
- 列表只返回 DTO（含 prefix 供识别，无 key_hash / 明文）。
- 撤销按用户隔离：只能撤销自己的 Key。
"""

from app.core.envelope import ApiError
from app.core.security import generate_api_key, hash_api_key
from app.models.api_key import ApiKey
from app.repositories.api_keys import ApiKeyRepository
from app.services import iso_z


class ApiKeyService:
    def __init__(self, repo: ApiKeyRepository) -> None:
        self._repo = repo

    def create(self, *, user_id: int, name: str) -> dict:
        name = name.strip()
        if not name or len(name) > 30:
            raise ApiError(400, "名称需为 1-30 个字符")
        if len([k for k in self._repo.list_active(user_id)]) >= 20:
            raise ApiError(400, "API Key 数量已达上限（20 个）")
        api_key = generate_api_key()
        key = self._repo.create(
            user_id=user_id,
            name=name,
            key_hash=hash_api_key(api_key),
            prefix=api_key[:12],
        )
        return {"apiKey": api_key, "item": self._dto(key)}

    def list(self, *, user_id: int) -> dict:
        return {"keys": [self._dto(k) for k in self._repo.list_active(user_id)]}

    def revoke(self, *, user_id: int, key_id: int) -> None:
        key = self._repo.get(key_id)
        if key is None or key.user_id != user_id:
            raise ApiError(404, "API Key 不存在")
        self._repo.revoke(key_id)

    @staticmethod
    def _dto(key: ApiKey) -> dict:
        return {
            "id": key.id,
            "name": key.name,
            "prefix": key.prefix,
            "createdAt": iso_z(key.created_at),
            "lastUsedAt": iso_z(key.last_used_at) if key.last_used_at else None,
        }
