import { defineMock } from 'vite-plugin-mock-dev-server'
import { store, type Habit, nextId, respond, ok, err, guard } from './store'


export default {
  // 列表
  list: defineMock({
    url: '/api/habits',
    method: 'GET',
    response: respond(
      guard(() => ok({ habits: store.habits })),
    ),
  }),

  // 新增
  create: defineMock({
    url: '/api/habits',
    method: 'POST',
    response: respond(
      guard((req) => {
        const { name } = req.body ?? {}
        const item: Habit = {
          id: nextId(store.habits),
          name: String(name || '新习惯'),
          streak: 0,
          done: false,
          week: Array.from({ length: 7 }, () => false),
        }
        store.habits.push(item)
        return ok({ id: item.id, item })
      }),
    ),
  }),

  // 打卡 / 更新
  update: defineMock({
    url: '/api/habits/:id',
    method: 'PUT',
    response: respond(
      guard((req) => {
        const id = String(req.params?.id)
        const index = store.habits.findIndex((h) => h.id === id)
        if (index < 0) return err(404, '习惯不存在')
        const patch = (req.body ?? {}) as Partial<Habit>
        const habit = store.habits[index]
        store.habits[index] = { ...habit, ...patch, id }
        return ok({ item: store.habits[index] })
      }),
    ),
  }),

  // 删除
  remove: defineMock({
    url: '/api/habits/:id',
    method: 'DELETE',
    response: respond(
      guard((req) => {
        const id = String(req.params?.id)
        const before = store.habits.length
        store.habits = store.habits.filter((h) => h.id !== id)
        if (store.habits.length === before) return err(404, '习惯不存在')
        return ok({ ok: true })
      }),
    ),
  }),
}
