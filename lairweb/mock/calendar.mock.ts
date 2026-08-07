import { defineMock } from 'vite-plugin-mock-dev-server'
import { store, type CalendarEvent, nextId, date, respond, ok, err, guard } from './store'


export default {
  // 列表
  list: defineMock({
    url: '/api/calendar',
    method: 'GET',
    response: respond(
      guard(() => ok({ events: store.events })),
    ),
  }),

  // 新增
  create: defineMock({
    url: '/api/calendar',
    method: 'POST',
    response: respond(
      guard((req) => {
        const { title, date: reqDate, time, location } = req.body ?? {}
        const item: CalendarEvent = {
          id: nextId(store.events),
          title: String(title || ''),
          date: String(reqDate || date()),
          time: String(time || '10:00'),
          location: String(location || ''),
          done: false,
        }
        store.events.push(item)
        return ok({ id: item.id, item })
      }),
    ),
  }),

  // 更新（完成状态 / 编辑）
  update: defineMock({
    url: '/api/calendar/:id',
    method: 'PUT',
    response: respond(
      guard((req) => {
        const id = String(req.params?.id)
        const index = store.events.findIndex((e) => e.id === id)
        if (index < 0) return err(404, '日程不存在')
        const patch = (req.body ?? {}) as Partial<CalendarEvent>
        store.events[index] = { ...store.events[index], ...patch, id }
        return ok({ item: store.events[index] })
      }),
    ),
  }),

  // 删除
  remove: defineMock({
    url: '/api/calendar/:id',
    method: 'DELETE',
    response: respond(
      guard((req) => {
        const id = String(req.params?.id)
        const before = store.events.length
        store.events = store.events.filter((e) => e.id !== id)
        if (store.events.length === before) return err(404, '日程不存在')
        return ok({ ok: true })
      }),
    ),
  }),
}
