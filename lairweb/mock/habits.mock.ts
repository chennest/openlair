import { defineMock } from 'vite-plugin-mock-dev-server'
import { store, type Habit, guid } from './store'


export default {
  // 列表
  list: defineMock({
    url: '/api/habits',
    method: 'GET',
    body: () => ({ habits: store.habits }),
  }),

  // 新增
  create: defineMock({
    url: '/api/habits',
    method: 'POST',
    body: (req) => {
      const { name } = req.body ?? {}
      const item: Habit = {
        id: guid(),
        name: String(name || '新习惯'),
        streak: 0,
        done: false,
        week: Array.from({ length: 7 }, () => false),
      }
      store.habits.push(item)
      return { ok: true, id: item.id, item }
    },
  }),

  // 打卡 / 更新
  update: defineMock({
    url: '/api/habits/:id',
    method: 'PUT',
    body: (req) => {
      const id = String(req.params?.id)
      const index = store.habits.findIndex((h) => h.id === id)
      if (index < 0) return { ok: false, error: 'not found' }
      const patch = (req.body ?? {}) as Partial<Habit>
      const habit = store.habits[index]
      store.habits[index] = { ...habit, ...patch, id }
      return { ok: true, item: store.habits[index] }
    },
  }),

  // 删除
  remove: defineMock({
    url: '/api/habits/:id',
    method: 'DELETE',
    body: (req) => {
      const id = String(req.params?.id)
      const before = store.habits.length
      store.habits = store.habits.filter((h) => h.id !== id)
      return { ok: before !== store.habits.length }
    },
  }),
}
