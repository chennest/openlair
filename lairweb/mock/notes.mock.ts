import { defineMock } from 'vite-plugin-mock-dev-server'
import { store, type Note, nextId, date, respond, ok, err, guard } from './store'


export default {
  // 列表
  list: defineMock({
    url: '/api/notes',
    method: 'GET',
    response: respond(
      guard(() => ok({ notes: store.notes })),
    ),
  }),

  // 新增
  create: defineMock({
    url: '/api/notes',
    method: 'POST',
    response: respond(
      guard((req) => {
        const { title, summary, tags } = req.body ?? {}
        const item: Note = {
          id: nextId(store.notes),
          title: String(title || '未命名'),
          summary: String(summary || ''),
          tags: Array.isArray(tags) ? tags.map(String) : [],
          updatedAt: date(),
        }
        store.notes.unshift(item)
        return ok({ id: item.id, item })
      }),
    ),
  }),

  // 更新
  update: defineMock({
    url: '/api/notes/:id',
    method: 'PUT',
    response: respond(
      guard((req) => {
        const id = String(req.params?.id)
        const index = store.notes.findIndex((n) => n.id === id)
        if (index < 0) return err(404, '笔记不存在')
        const patch = (req.body ?? {}) as Partial<Note>
        store.notes[index] = { ...store.notes[index], ...patch, id, updatedAt: date() }
        return ok({ item: store.notes[index] })
      }),
    ),
  }),

  // 删除
  remove: defineMock({
    url: '/api/notes/:id',
    method: 'DELETE',
    response: respond(
      guard((req) => {
        const id = String(req.params?.id)
        const before = store.notes.length
        store.notes = store.notes.filter((n) => n.id !== id)
        if (store.notes.length === before) return err(404, '笔记不存在')
        return ok({ ok: true })
      }),
    ),
  }),
}
