import { get, post, del } from '../../api/request'

export interface ApiKeyItem {
  id: number
  name: string
  /** 明文前 12 位（ol_ 前缀 + 部分随机串），仅用于列表识别，非完整 Key */
  prefix: string
  createdAt: string
  lastUsedAt: string | null
}

export const apiKeyApi = {
  list: () => get<{ keys: ApiKeyItem[] }>('/api/keys'),
  create: (name: string) => post<{ apiKey: string; item: ApiKeyItem }>('/api/keys', { name }),
  remove: (id: number) => del<{ ok: boolean }>(`/api/keys/${id}`),
}
