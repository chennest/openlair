import { defineMock } from 'vite-plugin-mock-dev-server'
import { store, type DayItem, nextId, respond, ok, err, guard } from './store'

// ---------- 重复规则展开（与后端 DayService._next_due 同构） ----------

const DAY_MS = 86400000
const startOfDay = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate())
const safeDay = (year: number, month1: number, day: number) =>
  new Date(year, month1 - 1, Math.min(day, new Date(year, month1, 0).getDate()))

/** 下一次日期：once=原日期；yearly=今年周年（已过取明年，2/29 平年落 2/28）；monthly=本月同日（已过取下月，月末截断） */
function nextDue(dateStr: string, repeat: DayItem['repeat']): Date {
  const [y, m, d] = dateStr.split('-').map(Number)
  const today = startOfDay(new Date())
  if (repeat === 'yearly') {
    let c = safeDay(today.getFullYear(), m, d)
    if (c.getTime() < today.getTime()) c = safeDay(today.getFullYear() + 1, m, d)
    return c
  }
  if (repeat === 'monthly') {
    let c = safeDay(today.getFullYear(), today.getMonth() + 1, d)
    if (c.getTime() < today.getTime()) {
      const ny = today.getMonth() === 11 ? today.getFullYear() + 1 : today.getFullYear()
      const nm = today.getMonth() === 11 ? 1 : today.getMonth() + 2
      c = safeDay(ny, nm, d)
    }
    return c
  }
  return new Date(y, m - 1, d)
}

/** 附加展示字段：daysUntil（负=已过累计）+ milestone（每年第 N 次） */
function withComputed(item: DayItem) {
  const today = startOfDay(new Date())
  const due = nextDue(item.date, item.repeat)
  const daysUntil = Math.round((due.getTime() - today.getTime()) / DAY_MS)
  const milestone = item.repeat === 'yearly' ? due.getFullYear() - Number(item.date.slice(0, 4)) + 1 : null
  return { ...item, daysUntil, milestone }
}

/** 与后端一致：置顶在前，其余按 |daysUntil| 升序 */
function sorted() {
  return store.days
    .map(withComputed)
    .sort((a, b) => Number(b.pinned) - Number(a.pinned) || Math.abs(a.daysUntil) - Math.abs(b.daysUntil) || a.id - b.id)
}

const REPEATS = ['once', 'yearly', 'monthly']

export default {
  // 列表
  list: defineMock({
    url: '/api/days',
    method: 'GET',
    response: respond(
      guard(() => ok({ days: sorted() })),
    ),
  }),

  // 新增
  create: defineMock({
    url: '/api/days',
    method: 'POST',
    response: respond(
      guard((req) => {
        const body = (req.body ?? {}) as Partial<DayItem>
        const item: DayItem = {
          id: nextId(store.days),
          title: String(body.title || '').trim() || '未命名日子',
          emoji: String(body.emoji || '').slice(0, 8),
          date: String(body.date || ''),
          repeat: REPEATS.includes(String(body.repeat)) ? (body.repeat as DayItem['repeat']) : 'once',
          pinned: Boolean(body.pinned),
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
        }
        store.days.push(item)
        return ok({ id: item.id, item: withComputed(item) })
      }),
    ),
  }),

  // 更新
  update: defineMock({
    url: '/api/days/:id',
    method: 'PUT',
    response: respond(
      guard((req) => {
        const id = Number(req.params?.id)
        const item = store.days.find((d) => d.id === id)
        if (!item) return err(404, '日子不存在')
        const patch = (req.body ?? {}) as Partial<DayItem>
        if (patch.title !== undefined) item.title = String(patch.title).trim() || '未命名日子'
        if (patch.emoji !== undefined) item.emoji = String(patch.emoji).slice(0, 8)
        if (patch.date !== undefined) item.date = String(patch.date)
        if (patch.repeat !== undefined) item.repeat = REPEATS.includes(String(patch.repeat)) ? (patch.repeat as DayItem['repeat']) : 'once'
        if (patch.pinned !== undefined) item.pinned = Boolean(patch.pinned)
        item.updatedAt = new Date().toISOString()
        return ok({ item: withComputed(item) })
      }),
    ),
  }),

  // 删除
  remove: defineMock({
    url: '/api/days/:id',
    method: 'DELETE',
    response: respond(
      guard((req) => {
        const id = Number(req.params?.id)
        const before = store.days.length
        store.days = store.days.filter((d) => d.id !== id)
        if (store.days.length === before) return err(404, '日子不存在')
        return ok({ ok: true })
      }),
    ),
  }),
}
