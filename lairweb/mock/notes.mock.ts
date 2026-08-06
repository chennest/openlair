import { defineMock } from 'vite-plugin-mock-dev-server'
import { store, type Note, guid, date } from './store'


export default {
  // 列表
  list: defineMock({
    url: '/api/notes',
    method: 'GET',
    body: () => ({ notes: store.notes }),
  }),

  // 新增
  create: defineMock({
    url: '/api/notes',
    method: 'POST',
    body: (req) => {
      const { title, summary, tags } = req.body ?? {}
      const item: Note = {
        id: guid(),
        title: String(title || '未命名'),
        summary: String(summary || ''),
        tags: Array.isArray(tags) ? tags.map(String) : [],
        updatedAt: date(),
      }
      store.notes.unshift(item)
      return { ok: true, id: item.id, item }
    },
  }),

  // 更新
  update: defineMock({
    url: '/api/notes/:id',
    method: 'PUT',
    body: (req) => {
      const id = String(req.params?.id)
      const index = store.notes.findIndex((n) => n.id === id)
      if (index < 0) return { ok: false, error: 'not found' }
      const patch = (req.body ?? {}) as Partial<Note>
      store.notes[index] = { ...store.notes[index], ...patch, id, updatedAt: date() }
      return { ok: true, item: store.notes[index] }
    },
  }),

  // 删除
  remove: defineMock({
    url: '/api/notes/:id',
    method: 'DELETE',
    body: (req) => {
      const id = String(req.params?.id)
      const before = store.notes.length
      store.notes = store.notes.filter((n) => n.id !== id)
      return { ok: before !== store.notes.length }
    },
  }),
}
