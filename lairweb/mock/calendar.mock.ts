import { defineMock } from 'vite-plugin-mock-dev-server'
import { store, type CalendarEvent, guid, date } from './store'


export default {
  // 列表
  list: defineMock({
    url: '/api/calendar',
    method: 'GET',
    body: () => ({ events: store.events }),
  }),

  // 新增
  create: defineMock({
    url: '/api/calendar',
    method: 'POST',
    body: (req) => {
      const { title, date: reqDate, time, location } = req.body ?? {}
      const item: CalendarEvent = {
        id: guid(),
        title: String(title || ''),
        date: String(reqDate || date()),
        time: String(time || '10:00'),
        location: String(location || ''),
        done: false,
      }
      store.events.push(item)
      return { ok: true, id: item.id, item }
    },
  }),

  // 更新（完成状态 / 编辑）
  update: defineMock({
    url: '/api/calendar/:id',
    method: 'PUT',
    body: (req) => {
      const id = String(req.params?.id)
      const index = store.events.findIndex((e) => e.id === id)
      if (index < 0) return { ok: false, error: 'not found' }
      const patch = (req.body ?? {}) as Partial<CalendarEvent>
      store.events[index] = { ...store.events[index], ...patch, id }
      return { ok: true, item: store.events[index] }
    },
  }),

  // 删除
  remove: defineMock({
    url: '/api/calendar/:id',
    method: 'DELETE',
    body: (req) => {
      const id = String(req.params?.id)
      const before = store.events.length
      store.events = store.events.filter((e) => e.id !== id)
      return { ok: before !== store.events.length }
    },
  }),
}
