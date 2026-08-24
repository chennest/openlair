import { defineMock } from 'vite-plugin-mock-dev-server'
import {
  store,
  respond,
  ok,
  err,
  guard,
  nextId,
  generateMockApiKey,
  hashApiKey,
} from './store'

/** API Key DTO：绝不回显明文 / keyHash（与真实后端一致，仅 prefix 用于识别） */
interface ApiKeyDTO {
  id: number
  name: string
  prefix: string
  createdAt: string
  lastUsedAt: string | null
}

function toDTO(k: {
  id: number
  name: string
  prefix: string
  createdAt: string
  lastUsedAt?: string
}): ApiKeyDTO {
  return {
    id: k.id,
    name: k.name,
    prefix: k.prefix,
    createdAt: k.createdAt,
    lastUsedAt: k.lastUsedAt ?? null,
  }
}

export default {
  // 列表：仅本人未撤销的 Key（创建时间倒序）
  list: defineMock({
    url: '/api/keys',
    method: 'GET',
    response: respond(
      guard((_req, auth) => {
        const keys = store.apiKeys
          .filter((k) => k.userId === Number(auth.userId) && !k.revokedAt)
          .sort((a, b) => b.createdAt.localeCompare(a.createdAt))
          .map(toDTO)
        return ok({ keys })
      }),
    ),
  }),

  // 创建：返回一次明文 apiKey（此后不再可得）
  create: defineMock({
    url: '/api/keys',
    method: 'POST',
    response: respond(
      guard((req, auth) => {
        const name = typeof req.body?.name === 'string' ? req.body.name.trim() : ''
        if (!name || name.length > 30) return err(400, '名称需为 1-30 个字符')
        const apiKey = generateMockApiKey()
        const row = {
          id: nextId(store.apiKeys),
          userId: Number(auth.userId),
          name,
          keyHash: hashApiKey(apiKey),
          prefix: apiKey.slice(0, 12),
          createdAt: new Date().toISOString(),
        }
        store.apiKeys.push(row)
        return ok({ apiKey, item: toDTO(row) }, '创建成功')
      }),
    ),
  }),

  // 撤销（软撤销：置 revokedAt，仅本人）
  revoke: defineMock({
    url: '/api/keys/:id',
    method: 'DELETE',
    response: respond(
      guard((req, auth) => {
        const id = Number(req.params?.id)
        const row = store.apiKeys.find((k) => k.id === id)
        if (!row || row.userId !== Number(auth.userId)) return err(404, 'API Key 不存在')
        row.revokedAt = new Date().toISOString()
        return ok({ ok: true }, '已撤销')
      }),
    ),
  }),
}
