import { get, post, put, del } from '../../api/request'

export type DayRepeat = 'once' | 'yearly' | 'monthly'

/** 倒数日 DTO：daysUntil / milestone 由后端按重复规则展开计算（mock 同契约）
 *  daysUntil：正 = 倒数天数，0 = 就是今天，负 = 已过累计天数 */
export interface DayItem {
  id: number
  title: string
  emoji: string
  /** YYYY-MM-DD */
  date: string
  repeat: DayRepeat
  pinned: boolean
  daysUntil: number
  /** 每年重复时的第 N 次周年/生日（一次性为 null；≤1 无需展示） */
  milestone: number | null
  createdAt: string
  updatedAt: string
}

export interface CreateDayInput {
  title: string
  date: string
  emoji?: string
  repeat?: DayRepeat
  pinned?: boolean
}

export const daysApi = {
  list: () => get<{ days: DayItem[] }>('/api/days'),
  create: (input: CreateDayInput) => post<{ id: number; item: DayItem }>('/api/days', input),
  update: (id: number, patch: Partial<CreateDayInput>) => put<{ item: DayItem }>(`/api/days/${id}`, patch),
  remove: (id: number) => del<{ ok: boolean }>(`/api/days/${id}`),
}
